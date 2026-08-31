#!/usr/bin/env bash
# Recover attached Advantech USB-4704 boards without rebooting the Pi.
#
# This runs over an independent root SSH session.  It deliberately does not
# use USBDEVFS_RESET: on this driver a failed control transfer can leave the
# reset caller stuck in the kernel long after its nominal timeout.  Instead it
# stops the user-space owner, logically detaches the board, and cycles the
# immediate upstream hub port.  For the deployed VIA hub this is the software
# equivalent of unplugging/replugging the USB-4704 (the hub advertises ganged
# power, so any other device on that hub is briefly power-cycled as well).
set -euo pipefail

readonly USB4704_VENDOR_ID="1809"
readonly USB4704_PRODUCT_ID="4704"

service_name=${USB4704_AGENT_SERVICE:-tms-agent.service}
daq_device=${1:-/dev/daq0}
usb_devices_root=${USB4704_SYSFS_ROOT:-/sys/bus/usb/devices}
systemctl_bin=${USB4704_SYSTEMCTL_BIN:-systemctl}
modprobe_bin=${USB4704_MODPROBE_BIN:-modprobe}
udevadm_bin=${USB4704_UDEVADM_BIN:-udevadm}
startup_reset_script=${USB4704_STARTUP_RESET_SCRIPT:-/opt/tusi-tms/bin/reset-usb4704-on-start.sh}
hub_power_cycle_bin=${USB4704_HUB_POWER_CYCLE_BIN:-/opt/tusi-tms/bin/usb-hub-power-cycle}
allow_hub_power_cycle=${USB4704_ALLOW_HUB_POWER_CYCLE:-1}
hub_power_off_ms=${USB4704_HUB_POWER_OFF_MS:-1000}
reauthorize_settle_seconds=${USB4704_RECOVERY_REAUTHORIZE_SETTLE_SECONDS:-1}
settle_seconds=${USB4704_RECOVERY_SETTLE_SECONDS:-3}
stop_timeout_seconds=${USB4704_STOP_TIMEOUT_SECONDS:-20}
post_power_stop_timeout_seconds=${USB4704_POST_POWER_STOP_TIMEOUT_SECONDS:-10}
ready_timeout_seconds=${USB4704_RECOVERY_READY_TIMEOUT_SECONDS:-15}
restart_agent_on_exit=0

log() {
    printf 'usb4704-recovery: %s\n' "$*" >&2
}

warn() {
    log "WARNING: $*"
}

warn_if_undervoltage_recorded() {
    if ! command -v journalctl >/dev/null 2>&1; then
        return 0
    fi
    if journalctl -k -b --no-pager -q 2>/dev/null | grep -q "Undervoltage detected"; then
        warn "Pi kernel recorded undervoltage; use a rated Pi supply and powered USB hub before retrying calibration"
    fi
}

start_agent_if_needed() {
    if (( restart_agent_on_exit )); then
        log "restoring $service_name after interrupted recovery"
        "$systemctl_bin" start --no-block "$service_name" \
            || warn "failed to restart $service_name"
    fi
}
trap start_agent_if_needed EXIT

command -v "$systemctl_bin" >/dev/null 2>&1 || {
    log "ERROR: systemctl is unavailable"
    exit 2
}

warn_if_undervoltage_recorded

service_main_pid() {
    "$systemctl_bin" show -p MainPID --value "$service_name" 2>/dev/null || true
}

service_is_stopped() {
    local pid
    pid=$(service_main_pid)
    [[ -z "$pid" || "$pid" == "0" ]]
}

wait_for_service_stop() {
    local timeout_seconds=$1
    local deadline=$((SECONDS + timeout_seconds))
    while ! service_is_stopped; do
        if (( SECONDS >= deadline )); then
            return 1
        fi
        sleep 0.2
    done
    return 0
}

stop_agent() {
    log "stopping $service_name without waiting on a potentially wedged USB ioctl"
    "$systemctl_bin" stop --no-block "$service_name" \
        || warn "service stop returned non-zero"
    restart_agent_on_exit=1

    if wait_for_service_stop "$stop_timeout_seconds"; then
        return 0
    fi

    # A calibration/start ioctl can be in uninterruptible sleep. Do not make
    # the recovery SSH command wait forever; queue SIGKILL, power-cycle the
    # device below, then give systemd one more bounded chance to reap it.
    warn "$service_name did not stop in ${stop_timeout_seconds}s; sending SIGKILL before USB power recovery"
    "$systemctl_bin" kill --kill-whom=all --signal=KILL "$service_name" \
        || warn "failed to send SIGKILL to $service_name"
    return 0
}

wait_for_daq() {
    local timeout_seconds=$1
    if [[ -e "$daq_device" ]]; then
        return 0
    fi
    local deadline=$((SECONDS + timeout_seconds))
    while (( SECONDS < deadline )); do
        [[ -e "$daq_device" ]] && return 0
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
    "$udevadm_bin" settle --timeout="$ready_timeout_seconds" \
        || warn "udev settle timed out"
}

ensure_usb4704_modules() {
    if ! command -v "$modprobe_bin" >/dev/null 2>&1; then
        warn "modprobe is unavailable; module check is skipped"
        return 0
    fi
    # Do not unload the driver: rmmod can wait on the same stuck driver path.
    # A USB disconnect/re-enumeration below invokes its normal disconnect and
    # probe callbacks, while these calls ensure the modules are present.
    "$modprobe_bin" biokernbase || warn "failed to load biokernbase"
    "$modprobe_bin" bio4704 || warn "failed to load bio4704"
}

discover_usb4704_topology() {
    device_names=()
    authorized_files=()
    hub_nodes=()
    hub_ports=()
    hub_power_cycled=()

    [[ -d "$usb_devices_root" ]] || return 0
    shopt -s nullglob
    for vendor_file in "$usb_devices_root"/*/idVendor; do
        local device_dir=${vendor_file%/idVendor}
        local product_file="$device_dir/idProduct"
        local device_name=${device_dir##*/}
        [[ "$device_name" == *:* || ! -r "$product_file" ]] && continue

        local vendor_id product_id
        read -r vendor_id < "$vendor_file" || continue
        read -r product_id < "$product_file" || continue
        [[ ${vendor_id,,} == "$USB4704_VENDOR_ID" && ${product_id,,} == "$USB4704_PRODUCT_ID" ]] || continue

        local parent_name=${device_name%.*}
        local port_number=${device_name##*.}
        local hub_node=""
        if [[ "$parent_name" != "$device_name" && "$port_number" =~ ^[0-9]+$ ]]; then
            local parent_dir="$usb_devices_root/$parent_name"
            if [[ -r "$parent_dir/busnum" && -r "$parent_dir/devnum" ]]; then
                local bus_number device_number
                read -r bus_number < "$parent_dir/busnum" || bus_number=""
                read -r device_number < "$parent_dir/devnum" || device_number=""
                if [[ "$bus_number" =~ ^[0-9]+$ && "$device_number" =~ ^[0-9]+$ ]]; then
                    printf -v hub_node '/dev/bus/usb/%03d/%03d' \
                        "$((10#$bus_number))" "$((10#$device_number))"
                fi
            fi
        fi
        device_names+=("$device_name")
        authorized_files+=("$device_dir/authorized")
        hub_nodes+=("$hub_node")
        hub_ports+=("$port_number")
    done
}

deauthorize_devices() {
    local index authorized_file
    for index in "${!device_names[@]}"; do
        authorized_file=${authorized_files[$index]}
        if [[ -w "$authorized_file" ]]; then
            log "logically disconnecting ${device_names[$index]}"
            printf '0\n' > "$authorized_file" \
                || warn "failed to deauthorize ${device_names[$index]}"
        else
            warn "cannot deauthorize ${device_names[$index]}; $authorized_file is unavailable"
        fi
    done
    sleep "$reauthorize_settle_seconds"
}

power_cycle_hub_ports() {
    local index hub_node port_number attempted=false
    if [[ "$allow_hub_power_cycle" != "1" ]]; then
        warn "hub-port power cycling is disabled by USB4704_ALLOW_HUB_POWER_CYCLE=$allow_hub_power_cycle"
        return 0
    fi
    if [[ ! -x "$hub_power_cycle_bin" ]]; then
        warn "hub-port helper is unavailable: $hub_power_cycle_bin"
        return 0
    fi
    for index in "${!device_names[@]}"; do
        hub_node=${hub_nodes[$index]}
        port_number=${hub_ports[$index]}
        if [[ -z "$hub_node" || ! "$port_number" =~ ^[0-9]+$ ]]; then
            warn "cannot determine parent hub port for ${device_names[$index]}"
            continue
        fi
        attempted=true
        log "power-cycling parent hub port $port_number for ${device_names[$index]} ($hub_node); ganged hubs briefly cycle all downstream ports"
        if "$hub_power_cycle_bin" "$hub_node" "$port_number" "$hub_power_off_ms"; then
            # A true port power cycle is a fresh physical enumeration. Linux
            # authorizes that new device by default, so do not race an old
            # sysfs authorized file while the hub is still re-enumerating.
            hub_power_cycled[$index]=1
        else
            warn "hub-port power cycle failed for ${device_names[$index]}"
        fi
    done
    [[ "$attempted" == true ]] || warn "no USB-4704 parent hub port was available for power recovery"
}

reauthorize_devices() {
    local index authorized_file
    for index in "${!device_names[@]}"; do
        if [[ ${hub_power_cycled[$index]:-0} == "1" ]]; then
            log "waiting for fresh enumeration of ${device_names[$index]} after hub power cycle"
            continue
        fi
        authorized_file=${authorized_files[$index]}
        # A hub power cycle can recreate the sysfs directory. Newly enumerated
        # devices are already authorized, so a missing old path is fine.
        if [[ -w "$authorized_file" ]]; then
            log "reauthorizing ${device_names[$index]}"
            printf '1\n' > "$authorized_file" \
                || warn "failed to authorize ${device_names[$index]}"
        fi
    done
}

start_agent() {
    log "starting $service_name"
    "$systemctl_bin" reset-failed "$service_name" || true
    "$systemctl_bin" start --no-block "$service_name" || {
        log "ERROR: failed to start $service_name"
        return 1
    }
    restart_agent_on_exit=0

    if "$systemctl_bin" is-active --quiet "$service_name"; then
        return 0
    fi
    local deadline=$((SECONDS + ready_timeout_seconds))
    while (( SECONDS < deadline )); do
        if "$systemctl_bin" is-active --quiet "$service_name"; then
            return 0
        fi
        sleep 0.2
    done
    log "ERROR: $service_name did not become active"
    return 1
}

stop_agent
discover_usb4704_topology
if (( ${#device_names[@]} == 0 )); then
    warn "no attached USB-4704 was found; recovery can only reload modules and restart the agent"
else
    deauthorize_devices
    power_cycle_hub_ports
    reauthorize_devices
fi

sleep "$settle_seconds"
ensure_usb4704_modules
trigger_udev

# If the old agent was blocked inside an ioctl, the port cycle should release
# it. Do not start a second service process while systemd still owns the old
# one; report a precise failure instead of making the dashboard wait 90 s.
if ! wait_for_service_stop "$post_power_stop_timeout_seconds"; then
    log "ERROR: $service_name remains stopped-pending after USB recovery"
    exit 4
fi

if [[ ! -e "$daq_device" && -x "$startup_reset_script" ]]; then
    log "daq node is still absent; using logical startup recovery fallback"
    "$startup_reset_script" "$daq_device" || warn "logical startup recovery failed"
fi

if ! start_agent; then
    exit 4
fi

if wait_for_daq "$ready_timeout_seconds"; then
    log "RECOVERY_RESULT=DAQ_READY"
    exit 0
fi

log "RECOVERY_RESULT=DAQ_MISSING"
exit 3
