#!/usr/bin/env bash
# Provision the fixed point-to-point TUSI wired link before the Dashboard runs.
set -euo pipefail

readonly PI_IP=${TMS_PI_IP:-10.47.0.2}
readonly LAPTOP_IP=${TMS_LAPTOP_IP:-10.47.0.1}
readonly CIDR_PREFIX=24
readonly SSH_USER=tms
readonly SSH_PASSWORD=tms
readonly SSH_PORT=22
readonly LAPTOP_PROFILE=TUSI-DAQ-Wired
readonly PI_PROFILE=TUSI-DAQ-Wired
readonly PI_WIFI_PROFILE=${TMS_PI_WIFI_PROFILE:-TUSI_wifi}

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

Configures the laptop Ethernet link as 10.47.0.1/24, provisions the Pi
Ethernet link as 10.47.0.2/24, makes a host route for the Pi over the
wired cable, arms the Pi Ethernet-to-Wi-Fi fallback, and ensures tms-agent
is active without resetting a healthy USB-4704.
Override the local interface only with TMS_ETH_IFACE=<interface> when more
than one cable is connected.
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
    remote_direct_sudo "
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
current_connection=\$(nmcli -g GENERAL.CONNECTION device show eth0 || true)
current_address=\$(ip -4 -o addr show dev eth0 | awk '{print \$4}' | grep -Fx '$PI_IP/$CIDR_PREFIX' || true)
if [[ \"\$current_connection\" != \"\$profile\" || -z \"\$current_address\" ]]; then
    nmcli connection up \"\$profile\" ifname eth0
fi
"
}

add_pi_host_route() {
    local interface=$1
    "$nmcli_bin" connection modify "$LAPTOP_PROFILE" \
        ipv4.routes "$PI_IP/32"
    "$nmcli_bin" connection up "$LAPTOP_PROFILE" ifname "$interface"
    ip route get "$PI_IP" | grep -Fq "dev $interface" || die "Pi route did not select $interface"
}

wait_for_direct_ssh() {
    local attempts=0
    local maximum_attempts=15
    while (( attempts < maximum_attempts )); do
        if remote_direct_sudo "true" >/dev/null 2>&1; then
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 1
    done
    die "Pi wired SSH is unreachable on ${PI_IP}; check the Ethernet cable and Pi eth0"
}

arm_pi_wifi_fallback_and_ensure_agent() {
    remote_direct_sudo "
set -euo pipefail
wifi_profile='$PI_WIFI_PROFILE'
if nmcli -g NAME connection show | grep -Fxq \"\$wifi_profile\"; then
    nmcli connection modify \"\$wifi_profile\" \\
        connection.autoconnect yes \\
        connection.autoconnect-priority 50
fi
systemctl enable --now tms-network-failover.service
# Networking changes do not require restarting the loopback-only agent.
# Restarting it on every dashboard launch ran the USB reset hook repeatedly,
# including while a previously healthy USB-4704 was still enumerated.
systemctl enable --now tms-agent.service
systemctl is-active --quiet tms-agent.service
"
}

interface=$(find_ethernet_interface)
log "configuring laptop $interface as $LAPTOP_IP/$CIDR_PREFIX"
configure_laptop "$interface"

# The dashboard target is on a dedicated 10.47.0.0/24 subnet.  Keep an
# explicit /32 route as a guard against any future overlapping host route.
log "routing $PI_IP over $interface"
add_pi_host_route "$interface"

log "waiting for direct Pi SSH over $interface"
wait_for_direct_ssh

log "configuring Pi eth0 as $PI_IP/$CIDR_PREFIX"
remote_configure_ethernet

log "arming Pi Wi-Fi fallback and ensuring tms-agent is active over the direct link"
arm_pi_wifi_fallback_and_ensure_agent

log "ready: $LAPTOP_IP -> $PI_IP via $interface"
