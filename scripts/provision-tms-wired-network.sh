#!/usr/bin/env bash
# Provision the fixed point-to-point TUSI wired link before the Dashboard runs.
set -euo pipefail

readonly PI_IP=${TMS_PI_IP:-192.168.0.214}
readonly LAPTOP_IP=${TMS_LAPTOP_IP:-192.168.0.213}
readonly CIDR_PREFIX=24
readonly SSH_USER=tms
readonly SSH_PASSWORD=tms
readonly SSH_PORT=22
readonly LAPTOP_PROFILE=TUSI-DAQ-Wired
readonly PI_PROFILE=TUSI-DAQ-Wired

nmcli_bin=${NMCLI_BIN:-nmcli}
ssh_bin=${SSH_BIN:-ssh}
sshpass_bin=${SSHPASS_BIN:-sshpass}

log() {
    printf 'tusi-network: %s\n' "$*" >&2
}

die() {
    log "ERROR: $*"
    exit 1
}

usage() {
    cat <<'EOF'
Usage: provision-tms-wired-network.sh

Configures the laptop Ethernet link as 192.168.0.213/24, provisions the Pi
Ethernet link as 192.168.0.214/24, makes a host route for the Pi over the
wired cable, and restarts tms-agent. Override the local interface only with
TMS_ETH_IFACE=<interface> when more than one cable is connected.
EOF
}

if [[ ${1:-} == --help ]]; then
    usage
    exit 0
fi

command -v "$nmcli_bin" >/dev/null || die "NetworkManager (nmcli) is required"
command -v "$ssh_bin" >/dev/null || die "ssh is required"
command -v "$sshpass_bin" >/dev/null || die "sshpass is required"

find_ethernet_interface() {
    if [[ -n ${TMS_ETH_IFACE:-} ]]; then
        [[ -d "/sys/class/net/$TMS_ETH_IFACE" ]] || die "unknown Ethernet interface: $TMS_ETH_IFACE"
        printf '%s\n' "$TMS_ETH_IFACE"
        return
    fi

    local device type fallback=""
    while IFS=: read -r device type _rest; do
        [[ $type == ethernet ]] || continue
        [[ -n $fallback ]] || fallback=$device
        if [[ -r "/sys/class/net/$device/carrier" ]] && [[ $(<"/sys/class/net/$device/carrier") == 1 ]]; then
            printf '%s\n' "$device"
            return
        fi
    done < <("$nmcli_bin" -t -f DEVICE,TYPE device status)
    [[ -n $fallback ]] || die "no Ethernet interface was found"
    printf '%s\n' "$fallback"
}

connection_exists() {
    "$nmcli_bin" -g NAME connection show | grep -Fxq "$1"
}

configure_laptop() {
    local interface=$1
    if ! connection_exists "$LAPTOP_PROFILE"; then
        "$nmcli_bin" connection add type ethernet ifname "$interface" con-name "$LAPTOP_PROFILE"
    fi
    "$nmcli_bin" connection modify "$LAPTOP_PROFILE" \
        connection.interface-name "$interface" \
        connection.autoconnect yes \
        connection.autoconnect-priority 100 \
        ipv4.method manual \
        ipv4.addresses "$LAPTOP_IP/$CIDR_PREFIX" \
        ipv4.never-default yes \
        ipv4.route-metric 700 \
        ipv4.routes "" \
        ipv6.method disabled
    "$nmcli_bin" connection up "$LAPTOP_PROFILE" ifname "$interface"
}

remote_sudo() {
    local command=$1 quoted
    printf -v quoted '%q' "$command"
    export SSHPASS="$SSH_PASSWORD"
    printf '%s\n' "$SSH_PASSWORD" | "$sshpass_bin" -e "$ssh_bin" \
        -o PreferredAuthentications=password \
        -o PubkeyAuthentication=no \
        -o StrictHostKeyChecking=accept-new \
        -o ConnectTimeout=10 \
        -p "$SSH_PORT" "$SSH_USER@$PI_IP" \
        "sudo -S -p '' /bin/bash -c $quoted"
}

remote_direct_sudo() {
    local command=$1 quoted
    printf -v quoted '%q' "$command"
    export SSHPASS="$SSH_PASSWORD"
    printf '%s\n' "$SSH_PASSWORD" | "$sshpass_bin" -e "$ssh_bin" \
        -b "$LAPTOP_IP" \
        -o PreferredAuthentications=password \
        -o PubkeyAuthentication=no \
        -o StrictHostKeyChecking=accept-new \
        -o ConnectTimeout=10 \
        -p "$SSH_PORT" "$SSH_USER@$PI_IP" \
        "sudo -S -p '' /bin/bash -c $quoted"
}

remote_configure_ethernet() {
    remote_sudo "
set -euo pipefail
profile='$PI_PROFILE'
if ! nmcli -g NAME connection show | grep -Fxq \"\$profile\"; then
    nmcli connection add type ethernet ifname eth0 con-name \"\$profile\"
fi
nmcli connection modify \"\$profile\" \\
    connection.interface-name eth0 \\
    connection.autoconnect yes \\
    connection.autoconnect-priority 100 \\
    ipv4.method manual \\
    ipv4.addresses '$PI_IP/$CIDR_PREFIX' \\
    ipv4.never-default yes \\
    ipv4.route-metric 700 \\
    ipv4.routes '' \\
    ipv6.method disabled
nmcli connection up \"\$profile\" ifname eth0
"
}

add_pi_host_route() {
    local interface=$1
    "$nmcli_bin" connection modify "$LAPTOP_PROFILE" \
        ipv4.routes "$PI_IP/32"
    "$nmcli_bin" connection up "$LAPTOP_PROFILE" ifname "$interface"
    ip route get "$PI_IP" | grep -Fq "dev $interface" || die "Pi route did not select $interface"
}

disable_pi_wifi_and_restart_agent() {
    remote_direct_sudo "
set -euo pipefail
while IFS=: read -r name type; do
    if [[ \"\$type\" == 802-11-wireless ]]; then
        nmcli connection modify \"\$name\" connection.autoconnect no
    fi
done < <(nmcli -t -f NAME,TYPE connection show --active)
nmcli radio wifi off
systemctl restart tms-agent.service
systemctl is-active --quiet tms-agent.service
"
}

interface=$(find_ethernet_interface)
log "configuring laptop $interface as $LAPTOP_IP/$CIDR_PREFIX"
configure_laptop "$interface"

# With the Ethernet route metric deliberately higher than Wi-Fi, this first
# SSH connection still reaches the Pi over its existing management link.
log "configuring Pi eth0 as $PI_IP/$CIDR_PREFIX"
remote_configure_ethernet

log "routing $PI_IP over $interface"
add_pi_host_route "$interface"

if [[ ${TMS_KEEP_PI_WIFI:-0} != 1 ]]; then
    log "verifying direct link, disabling Pi Wi-Fi, and restarting tms-agent"
    disable_pi_wifi_and_restart_agent
else
    log "direct link is ready; Pi Wi-Fi retained by TMS_KEEP_PI_WIFI=1"
fi

log "ready: $LAPTOP_IP -> $PI_IP via $interface"
