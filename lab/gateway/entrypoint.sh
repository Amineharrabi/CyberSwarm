#!/bin/sh
# Gateway startup: enable forwarding, load the firewall, start the IDS, keep running.
set -e

echo "[gateway] enabling IPv4 forwarding"
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || echo 1 > /proc/sys/net/ipv4/ip_forward

echo "[gateway] loading nftables ruleset"
nft -f /etc/nftables.conf

# Masquerade so return traffic finds its way back across segments.
nft add table ip nat 2>/dev/null || true
nft add chain ip nat postrouting '{ type nat hook postrouting priority 100 ; }' 2>/dev/null || true
nft add rule ip nat postrouting ip saddr 10.10.1.0/24 ip daddr 10.10.2.0/24 counter 2>/dev/null || true

echo "[gateway] starting Suricata on all interfaces (IDS mode)"
# -i any: watch every segment the gateway bridges. eve.json is mounted to the host.
suricata -c /etc/suricata/suricata.yaml -i any -v &

echo "[gateway] up. Blocking is Blue-controlled via nft from the orchestrator."
# Keep PID 1 alive; tcpdump here is handy for the Wireshark screenshot:
#   docker exec cs_gateway tcpdump -i any -w /var/log/suricata/capture.pcap
tail -f /dev/null
