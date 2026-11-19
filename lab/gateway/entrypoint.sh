#!/bin/sh
# Gateway startup: enable forwarding, load the firewall, start the IDS, keep running.
set -e

echo "[gateway] enabling IPv4 forwarding"
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || echo 1 > /proc/sys/net/ipv4/ip_forward

echo "[gateway] loading nftables ruleset"
nft -f /etc/nftables.conf

# No NAT: cross-segment routing works with source IPs intact (see docker VM bridge-nf
# note in README). Preserving the real source IP is what lets Blue detect and block the
# attacker by address. Return paths work because every container's default route is the
# gateway.

echo "[gateway] starting Suricata on eth0 (attacker-facing segment, IDS mode, libpcap)"
# Sniff eth0 only (attacker_net side). All client traffic — legit users AND the attacker —
# enters the dmz through here, so Suricata sees complete bidirectional HTTP streams with
# real source IPs. Sniffing 'any' would double-count each forwarded packet (ingress+egress)
# and break TCP reassembly, so HTTP never parses. eve.json is mounted to the host.
# -k none: skip checksum validation. In Docker/VMs, checksum offload leaves captured
# packets with "invalid" checksums; without this Suricata drops them from stream
# reassembly, so HTTP never parses and content rules (SQLi, traversal) never fire.
suricata -c /etc/suricata/suricata.yaml --pcap=eth0 -k none -v &

echo "[gateway] up. Blocking is Blue-controlled via nft from the orchestrator."
# Keep PID 1 alive; tcpdump here is handy for the Wireshark screenshot:
#   docker exec cs_gateway tcpdump -i any -w /var/log/suricata/capture.pcap
tail -f /dev/null
