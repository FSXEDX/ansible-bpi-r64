#!/usr/bin/env bash
set -euo pipefail

# /bin/bash -c "/usr/local/bin/vpn_latency_metrics.sh | sponge /var/lib/prometheus/node-exporter/vpn_latency_metrics.prom"

get_metrics() {
    VPN_ADDRESS="172.30.0.9"
    if [[ -z ${VPN_ADDRESS} ]]; then
        LATENCY=0
    else
        set +e
        LATENCY=$(timeout 40 ping -c 10 -q ${VPN_ADDRESS} | awk -F '/' '/rtt min\/avg\/max\/mdev/ {print $5}')
        set -e
        [[ -z ${LATENCY} ]] && LATENCY=0
    fi
    {
        echo "# HELP vpn_latency_ms Average gateway icmp latency in milliseconds"
        echo "# TYPE vpn_latency_ms gauge"
        echo "vpn_latency_ms{vpn_ip_address=\"$VPN_ADDRESS\"} $LATENCY"
    } #>> "${TMPFILE}"
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then
    get_metrics
fi
