# Gateway: router + firewall + IDS sensor for the whole lab.
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        nftables \
        suricata \
        iproute2 \
        iptables \
        tcpdump \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY nftables.conf /etc/nftables.conf
COPY suricata.yaml /etc/suricata/suricata.yaml
COPY local.rules /etc/suricata/rules/local.rules
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Make sure the rules dir and a stub suricata.rules exist even without the ET ruleset.
RUN mkdir -p /etc/suricata/rules && touch /etc/suricata/rules/suricata.rules

ENTRYPOINT ["/entrypoint.sh"]
