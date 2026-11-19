"""
Telemetry — read Suricata eve.json and expose compact views to Blue. Raw pcap is NEVER
sent to the LLM; only summaries (token-cheap) are.
"""
import json
import os
from collections import Counter


class Telemetry:
    def __init__(self, eve_path):
        self.eve_path = eve_path

    def _records(self):
        if not os.path.exists(self.eve_path):
            return []
        out = []
        with open(self.eve_path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def alerts(self):
        recs = self._records()
        return [
            {
                "signature": r.get("alert", {}).get("signature"),
                "src_ip": r.get("src_ip"),
                "dest_ip": r.get("dest_ip"),
                "dest_port": r.get("dest_port"),
            }
            for r in recs if r.get("event_type") == "alert"
        ]

    def flow_summary(self):
        """Top talkers, per-IP connection counts, distinct ports, HTTP status mix."""
        recs = self._records()
        talkers = Counter()
        ports = Counter()
        statuses = Counter()
        for r in recs:
            if r.get("src_ip"):
                talkers[r["src_ip"]] += 1
            if r.get("dest_port"):
                ports[r["dest_port"]] += 1
            if r.get("event_type") == "http":
                statuses[r.get("http", {}).get("status")] += 1
        lines = ["Top talkers (src_ip: events):"]
        for ip, n in talkers.most_common(5):
            lines.append(f"  {ip}: {n}")
        lines.append("Top dest ports: " + ", ".join(f"{p}({n})" for p, n in ports.most_common(5)))
        lines.append("HTTP status mix: " + ", ".join(f"{s}:{n}" for s, n in statuses.most_common()))
        return "\n".join(lines)
