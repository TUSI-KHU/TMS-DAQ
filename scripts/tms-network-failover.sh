#!/usr/bin/env bash
# Keep the Pi reachable on the router Wi-Fi when the dedicated TMS Ethernet
# link is unavailable. The wired TMS path uses 10.47.0.2 while Wi-Fi keeps
# its router address, so the two paths do not share an IPv4 subnet. Wi-Fi is
# still kept off while eth0 is active to make the dedicated wired path the
# sole live operator route.
set -u -o pipefail

readonly WIRED_INTERFACE=${TMS_WIRED_INTERFACE:-eth0}
readonly WIFI_INTERFACE=${TMS_WIFI_INTERFACE:-wlan0}
readonly WIFI_PROFILE=${TMS_WIFI_PROFILE:-TUSI_wifi}
readonly POLL_SECONDS=${TMS_NETWORK_FAILOVER_POLL_SECONDS:-2}

log() {
    logger -t tms-network-failover -- "$*"
}

wired_is_connected() {
    local state
    state=$(nmcli -g GENERAL.STATE device show "$WIRED_INTERFACE" 2>/dev/null || true)
    [[ "$state" == 100* ]]
}

wifi_profile_exists() {
    nmcli -g NAME connection show | grep -Fxq "$WIFI_PROFILE"
}

enable_wifi_fallback() {
    nmcli radio wifi on || log "could not enable Wi-Fi radio"
    if wifi_profile_exists; then
        nmcli connection up "$WIFI_PROFILE" ifname "$WIFI_INTERFACE" \
            || log "could not activate Wi-Fi profile ${WIFI_PROFILE}"
    else
        log "Wi-Fi profile ${WIFI_PROFILE} is not configured"
    fi
}

disable_wifi_fallback() {
    nmcli radio wifi off || log "could not disable Wi-Fi radio"
}

wifi_is_connected() {
    local state
    state=$(nmcli -g GENERAL.STATE device show "$WIFI_INTERFACE" 2>/dev/null || true)
    [[ "$state" == 100* ]]
}

last_link_state=unknown
wifi_retry_ticks=0
while :; do
    if wired_is_connected; then
        link_state=wired
    else
        link_state=wireless
    fi

    if [[ "$link_state" == wired ]]; then
        if [[ "$link_state" != "$last_link_state" ]]; then
            log "${WIRED_INTERFACE} connected; disabling Wi-Fi to avoid IP conflict"
            disable_wifi_fallback
        else
            :
        fi
        wifi_retry_ticks=0
    elif [[ "$link_state" != "$last_link_state" ]]; then
        log "${WIRED_INTERFACE} disconnected; enabling Wi-Fi fallback"
        enable_wifi_fallback
        wifi_retry_ticks=0
    elif ! wifi_is_connected; then
        # The radio can briefly report unavailable immediately after it is
        # enabled.  Retry at a controlled cadence until NetworkManager has
        # associated the saved router profile.
        wifi_retry_ticks=$((wifi_retry_ticks + 1))
        if (( wifi_retry_ticks >= 5 )); then
            log "Wi-Fi fallback is not connected; retrying ${WIFI_PROFILE}"
            enable_wifi_fallback
            wifi_retry_ticks=0
        fi
    else
        wifi_retry_ticks=0
    fi

    last_link_state=$link_state

    sleep "$POLL_SECONDS"
done
