#!/usr/bin/env bash
# Prepare an Advantech USB-4704 before tms-agent starts.
#
# A previous version unbound/rebound every attached board on *every* agent
# start, then fell back to USBDEVFS_RESET.  The dashboard used to restart the
# agent during normal connection setup, so a healthy board was repeatedly
# reset and a wedged USB control request could hold service startup hostage.
# Keep the normal path non-destructive: do nothing when /dev/daq0 is already
# usable, and escalate only when that node is actually missing.
set -euo pipefail

readonly USB4704_VENDOR_ID="1809"
readonly USB4704_PRODUCT_ID="4704"

usb_devices_root=${USB4704_SYSFS_ROOT:-/sys/bus/usb/devices}
usb_driver_root=${USB4704_USB_DRIVER_ROOT:-/sys/bus/usb/drivers/usb}
reauthorize_settle_seconds=${USB4704_REAUTHORIZE_SETTLE_SECONDS:-1}
rebind_settle_seconds=${USB4704_REBIND_SETTLE_SECONDS:-2}
ready_timeout_seconds=${USB4704_READY_TIMEOUT_SECONDS:-8}
fallback_ready_timeout_seconds=${USB4704_FALLBACK_READY_TIMEOUT_SECONDS:-12}
daq_device=${1:-/dev/daq0}
udevadm_bin=${USB4704_UDEVADM_BIN:-udevadm}
modprobe_bin=${USB4704_MODPROBE_BIN:-modprobe}

log() {
    printf 'usb4704-startup-reset: %s\n' "$*" >&2
}

warn() {
    log "WARNING: $*"
}

ensure_usb4704_modules() {
    # This helper normally runs as systemd ExecStartPre=+ (root).  Keep the
    # script testable as an ordinary user with a fake sysfs tree.
    [[ ${EUID} -eq 0 ]] || return 0
    if ! command -v "$modprobe_bin" >/dev/null 2>&1; then
        warn "modprobe is unavailable; cannot ensure USB-4704 modules are loaded"
        return 0
    fi
    "$modprobe_bin" biokernbase || warn "failed to load biokernbase"
    "$modprobe_bin" bio4704 || warn "failed to load bio4704"
}

wait_for_daq() {
    local timeout_seconds=$1
    if [[ -e "$daq_device" ]]; then
        log "$daq_device is ready; leaving USB topology untouched"
        return 0
    fi

    local deadline=$((SECONDS + timeout_seconds))
    while (( SECONDS < deadline )); do
        if [[ -e "$daq_device" ]]; then
            log "$daq_device is ready"
            return 0
        fi
        sleep 0.2
    done
    return 1
}

trigger_udev() {
    if ! command -v "$udevadm_bin" >/dev/null 2>&1; then
        return 0
    fi
    "$udevadm_bin" trigger --subsystem-match=usb || warn "udev USB trigger failed"
    "$udevadm_bin" trigger --subsystem-match=daq || warn "udev DAQ trigger failed"
    "$udevadm_bin" settle --timeout="$fallback_ready_timeout_seconds" \
        || warn "udev settle timed out"
}

discover_usb4704_devices() {
    devices=()
    shopt -s nullglob
    for vendor_file in "$usb_devices_root"/*/idVendor; do
        local device_dir=${vendor_file%/idVendor}
        local product_file="$device_dir/idProduct"
        local device_name=${device_dir##*/}

        # USB interface entries (for example 1-1.1:1.0) are not physical USB
        # devices and must not be written to the USB core bind controls.
        [[ "$device_name" == *:* || ! -r "$product_file" ]] && continue

        local vendor_id product_id
        read -r vendor_id < "$vendor_file" || continue
        read -r product_id < "$product_file" || continue
        if [[ ${vendor_id,,} == "$USB4704_VENDOR_ID" && ${product_id,,} == "$USB4704_PRODUCT_ID" ]]; then
            devices+=("$device_name")
        fi
    done
}

reauthorize_devices() {
    local device_name device_dir authorized_file
    for device_name in "${devices[@]}"; do
        device_dir="$usb_devices_root/$device_name"
        authorized_file="$device_dir/authorized"
        if [[ ! -w "$authorized_file" ]]; then
            warn "cannot reauthorize $device_name; $authorized_file is unavailable"
            continue
        fi
        log "reauthorizing USB device $device_name"
        printf '0\n' > "$authorized_file" || {
            warn "failed to deauthorize $device_name"
            continue
        }
        sleep "$reauthorize_settle_seconds"
        printf '1\n' > "$authorized_file" || warn "failed to authorize $device_name"
    done
}

rebind_devices_as_last_resort() {
    local device_name
    if [[ ! -w "$usb_driver_root/unbind" || ! -w "$usb_driver_root/bind" ]]; then
        warn "cannot write USB driver bind controls under $usb_driver_root"
        return 0
    fi
    for device_name in "${devices[@]}"; do
        log "last-resort USB core rebind for $device_name"
        if ! printf '%s\n' "$device_name" > "$usb_driver_root/unbind"; then
            warn "failed to unbind $device_name"
            continue
        fi
        sleep "$rebind_settle_seconds"
        printf '%s\n' "$device_name" > "$usb_driver_root/bind" \
            || warn "failed to bind $device_name"
    done
}

if [[ ! -d "$usb_devices_root" ]]; then
    warn "USB sysfs directory is unavailable: $usb_devices_root"
    exit 0
fi

ensure_usb4704_modules
if wait_for_daq 0; then
    exit 0
fi

discover_usb4704_devices
if (( ${#devices[@]} == 0 )); then
    log "no USB-4704 ($USB4704_VENDOR_ID:$USB4704_PRODUCT_ID) is attached; continuing"
    exit 0
fi

log "$daq_device is absent; attempting non-destructive USB reauthorization"
reauthorize_devices
trigger_udev
if wait_for_daq "$ready_timeout_seconds"; then
    exit 0
fi

# Do not call USBDEVFS_RESET here. Some failed USB-4704 control transfers can
# become uninterruptible in the kernel; the explicit recovery button uses a
# bounded hub-port power cycle instead when this final logical recovery fails.
warn "$daq_device did not appear after reauthorization; attempting USB-core rebind"
rebind_devices_as_last_resort
trigger_udev
if wait_for_daq "$fallback_ready_timeout_seconds"; then
    exit 0
fi

warn "$daq_device did not appear after startup recovery; agent will report its DAQ status"
