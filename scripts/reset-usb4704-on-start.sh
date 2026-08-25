#!/usr/bin/env bash
# Reset only Advantech USB-4704 devices before tms-agent starts.
#
# This is intentionally a USB-core rebind instead of a module unload/reload:
# it keeps the scope to the physical 1809:4704 device(s), lets udev recreate
# /dev/daq*, and avoids disrupting unrelated DAQ modules.
set -euo pipefail

readonly USB4704_VENDOR_ID="1809"
readonly USB4704_PRODUCT_ID="4704"

usb_devices_root=${USB4704_SYSFS_ROOT:-/sys/bus/usb/devices}
usb_driver_root=${USB4704_USB_DRIVER_ROOT:-/sys/bus/usb/drivers/usb}
settle_seconds=${USB4704_RESET_SETTLE_SECONDS:-2}
ready_timeout_seconds=${USB4704_READY_TIMEOUT_SECONDS:-8}
daq_device=${1:-/dev/daq0}

log() {
    printf 'usb4704-startup-reset: %s\n' "$*" >&2
}

warn() {
    log "WARNING: $*"
}

if [[ ! -d "$usb_devices_root" ]]; then
    warn "USB sysfs directory is unavailable: $usb_devices_root"
    exit 0
fi
if [[ ! -w "$usb_driver_root/unbind" || ! -w "$usb_driver_root/bind" ]]; then
    warn "cannot write USB driver bind controls under $usb_driver_root"
    exit 0
fi

shopt -s nullglob
devices=()
for vendor_file in "$usb_devices_root"/*/idVendor; do
    device_dir=${vendor_file%/idVendor}
    product_file="$device_dir/idProduct"
    device_name=${device_dir##*/}

    # USB interface entries (for example 1-1.1:1.0) are not USB devices and
    # must not be passed to the core USB driver's bind interface.
    [[ "$device_name" == *:* || ! -r "$product_file" ]] && continue

    read -r vendor_id < "$vendor_file" || continue
    read -r product_id < "$product_file" || continue
    vendor_id=${vendor_id,,}
    product_id=${product_id,,}
    if [[ "$vendor_id" == "$USB4704_VENDOR_ID" && "$product_id" == "$USB4704_PRODUCT_ID" ]]; then
        devices+=("$device_name")
    fi
done

if (( ${#devices[@]} == 0 )); then
    log "no USB-4704 ($USB4704_VENDOR_ID:$USB4704_PRODUCT_ID) is attached; continuing"
    exit 0
fi

for device_name in "${devices[@]}"; do
    log "rebinding USB device $device_name ($USB4704_VENDOR_ID:$USB4704_PRODUCT_ID)"
    if ! printf '%s\n' "$device_name" > "$usb_driver_root/unbind"; then
        warn "failed to unbind $device_name; continuing"
        continue
    fi
    sleep "$settle_seconds"
    if ! printf '%s\n' "$device_name" > "$usb_driver_root/bind"; then
        warn "failed to bind $device_name; continuing"
    fi
done

# A failed driver probe must not turn into a systemd restart loop: the agent
# still starts and exposes the exact NOT_FOUND/FAILED reason through telemetry.
# Wait briefly on success so its initial health snapshot normally sees daq0.
if [[ -e "$daq_device" ]]; then
    log "$daq_device is ready"
    exit 0
fi

deadline=$((SECONDS + ready_timeout_seconds))
while (( SECONDS < deadline )); do
    if [[ -e "$daq_device" ]]; then
        log "$daq_device is ready"
        exit 0
    fi
    sleep 0.2
done
warn "$daq_device did not appear after the USB rebind; agent will report its DAQ status"
