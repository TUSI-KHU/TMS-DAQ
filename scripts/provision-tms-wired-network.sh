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

Configures the laptop Ethernet link as 10.47.0.1/24 and supplies the Pi
10.47.0.2/24 through a fixed DHCP pool when supported by NetworkManager.
Supports Pi NetworkManager and systemd-networkd, keeps the Pi host route
on the wired cable, and ensures the installed tms-agent is active without
resetting a healthy USB-4704. Wi-Fi fallback is NetworkManager-only.
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
command -v timeout >/dev/null || die "timeout is required"

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
    local interface=$1 ipv4_method=manual
    local -a dhcp_settings=()
    if ! connection_exists "$LAPTOP_PROFILE"; then
        "$nmcli_bin" connection add type ethernet ifname "$interface" con-name "$LAPTOP_PROFILE"
    fi
    # Bootstrap a fresh Pi which only has DHCP, before attempting SSH. Keep
    # the single-address pool fixed so the dashboard endpoint stays stable.
    if "$nmcli_bin" -g ipv4.shared-dhcp-range connection show "$LAPTOP_PROFILE" >/dev/null 2>&1; then
        ipv4_method=shared
        dhcp_settings=(ipv4.shared-dhcp-range "$PI_IP,$PI_IP" ipv4.shared-dhcp-lease-time 86400)
    else
        log "NetworkManager has no fixed DHCP range support; Pi must already use $PI_IP"
    fi
    "$nmcli_bin" connection modify "$LAPTOP_PROFILE" \
        connection.interface-name "$interface" \
        connection.autoconnect yes \
        connection.autoconnect-priority 100 \
        ipv4.method "$ipv4_method" \
        ipv4.addresses "$LAPTOP_IP/$CIDR_PREFIX" \
        ipv4.never-default yes \
        ipv4.route-metric 700 \
        ipv4.routes "$PI_IP/32" \
        ipv6.method disabled "${dhcp_settings[@]}"
    "$nmcli_bin" connection up "$LAPTOP_PROFILE" ifname "$interface"
}

remote_direct_sudo() {
    local command=$1 quoted
    printf -v quoted '%q' "$command"
    export SSHPASS="$SSH_PASSWORD"
    printf '%s\n' "$SSH_PASSWORD" | timeout -k 2s 100s "$sshpass_bin" -e "$ssh_bin" \
        -b "$LAPTOP_IP" \
        -o PreferredAuthentications=password \
        -o PubkeyAuthentication=no \
        -o StrictHostKeyChecking=accept-new \
        -o ConnectTimeout=10 \
        -o ConnectionAttempts=1 \
        -o NumberOfPasswordPrompts=1 \
        -o ServerAliveInterval=3 \
        -o ServerAliveCountMax=2 \
        -p "$SSH_PORT" "$SSH_USER@$PI_IP" \
        "sudo -S -p '' /bin/bash -c $quoted"
}

remote_configure_ethernet() {
    remote_direct_sudo "
set -euo pipefail
if ! command -v nmcli >/dev/null || ! systemctl is-active --quiet NetworkManager; then
    # Ubuntu Server uses networkd/netplan. Its DHCP configuration is already
    # persistent, and the laptop reserves the operator address for this link.
    if systemctl is-active --quiet systemd-networkd && \\
       ip -4 -o addr show dev eth0 | awk '{print \$4}' | grep -Fxq '$PI_IP/$CIDR_PREFIX'; then
        echo 'Pi eth0: systemd-networkd, using the wired DHCP reservation $PI_IP'
        exit 0
    fi
    echo 'Pi has no active supported Ethernet manager or expected eth0 address' >&2
    exit 1
fi
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

check_pi_host_route() {
    local interface=$1
    ip route get "$PI_IP" | grep -Fq "dev $interface" || die "Pi route did not select $interface"
}

wait_for_direct_ssh() {
    local deadline=$((SECONDS + 90)) last_report=$SECONDS error status
    export SSHPASS="$SSH_PASSWORD"
    while (( SECONDS < deadline )); do
        if error=$(timeout -k 1s 6s "$sshpass_bin" -e "$ssh_bin" -n \
            -b "$LAPTOP_IP" -o PreferredAuthentications=password \
            -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new \
            -o ConnectTimeout=3 -o ConnectionAttempts=1 \
            -o NumberOfPasswordPrompts=1 \
            -p "$SSH_PORT" "$SSH_USER@$PI_IP" true 2>&1); then
            return 0
        else
            status=$?
        fi
        if [[ $status == 5 ]]; then
            die "Pi SSH answered, but $SSH_USER password authentication was rejected"
        fi
        if [[ $error == *'REMOTE HOST IDENTIFICATION HAS CHANGED'* || $error == *'Host key verification failed'* ]]; then
            die "Pi SSH host key changed after reinstall; verify the new Pi key before updating known_hosts"
        fi
        if (( SECONDS - last_report >= 10 )); then
            log "still waiting for $PI_IP:22 over Ethernet (DHCP/SSH)"
            last_report=$SECONDS
        fi
        sleep 1
    done
    ip neigh show to "$PI_IP" >&2 || true
    die "Pi wired SSH is unreachable on ${PI_IP}: ${error:-no response}"
}

arm_pi_wifi_fallback_and_ensure_agent() {
    remote_direct_sudo "
set -euo pipefail
wifi_profile='$PI_WIFI_PROFILE'
if command -v nmcli >/dev/null && systemctl is-active --quiet NetworkManager; then
    if nmcli -g NAME connection show | grep -Fxq \"\$wifi_profile\"; then
        nmcli connection modify \"\$wifi_profile\" \\
            connection.autoconnect yes \\
            connection.autoconnect-priority 50
    fi
    if systemctl cat tms-network-failover.service >/dev/null 2>&1; then
        systemctl enable --now tms-network-failover.service
    fi
fi
if ! systemctl cat tms-agent.service >/dev/null 2>&1; then
    echo 'tms-agent is not installed on this Pi; deploy scripts/install-tms-agent.sh first' >&2
    exit 1
fi
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
check_pi_host_route "$interface"

log "waiting for direct Pi SSH over $interface"
wait_for_direct_ssh

log "configuring Pi eth0 as $PI_IP/$CIDR_PREFIX"
remote_configure_ethernet

log "ensuring tms-agent is active over the direct link"
arm_pi_wifi_fallback_and_ensure_agent

log "ready: $LAPTOP_IP -> $PI_IP via $interface"
