"""ft_comparison.py — the headline figure + table for the report.

Compares the 4 prompt-based learning methods against the 4th method (QLoRA
fine-tuning). The coarse IDS-alert scores saturate (single-vuln ceiling), so the
discriminating metric is DEFENSIVE COMPETENCE: in how many rounds did Blue actually
block the attacker, and how decisively (which step it blocked / patched on).

    python ft_comparison.py            # reads ../runs/<method>_r1

Finding: fine-tuning reaches top-tier block reliability (100%) with NO runtime
reflection/memory/debrief — the defensive policy is internalised in the weights.
"""
import json, glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDER = ["no_learning_r1", "reflect_r1", "reflect_mem_r1", "baseline_r1", "ft_r1"]
LABEL = {"no_learning_r1": "none", "reflect_r1": "reflect",
         "reflect_mem_r1": "+memory", "baseline_r1": "+debrief",
         "ft_r1": "FINE-TUNED"}
COLOR = {"none": "#8a8f98", "reflect": "#5b8def", "+memory": "#2bb673",
         "+debrief": "#e0a106", "FINE-TUNED": "#d7263d"}


def first_step(msgs, tool):
    s = 0
    for m in msgs:
        if m.get("role") == "assistant":
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if tc["function"]["name"] == tool:
                        return s
                s += 1
    return None


def collect(run):
    rounds = sorted(glob.glob(f"../runs/{run}/round_*/scores.json"))
    det, solved, blue, red, legit = [], [], [], [], 0
    for p in rounds:
        x = json.load(open(p))
        det.append(x["detections"]); solved.append(x["challenges_solved_round"])
        blue.append(x["blue_score"]); red.append(x["red_score"])
        legit += x["legit_blocked"]
    blocked = 0; bsteps = []; psteps = []; calls = []
    for p in sorted(glob.glob(f"../runs/{run}/round_*/blue_messages.json")):
        msgs = json.load(open(p, encoding="utf-8"))
        calls.append(sum(len(m.get("tool_calls") or []) for m in msgs
                         if m.get("role") == "assistant"))
        b = first_step(msgs, "block_ip"); pt = first_step(msgs, "patch_sqli")
        if b is not None:
            blocked += 1; bsteps.append(b)
        if pt is not None:
            psteps.append(pt)
    n = len(rounds) or 1
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    return dict(n=n, det=det, solved=solved, mean_blue=mean(blue), mean_red=mean(red),
                legit=legit, blocked=blocked, block_rate=100.0 * blocked / n,
                avg_block_step=mean(bsteps), avg_patch_step=mean(psteps),
                avg_calls=mean(calls))


def main():
    data = {LABEL[r]: collect(r) for r in ORDER if os.path.isdir(f"../runs/{r}")}
    names = [LABEL[r] for r in ORDER if LABEL[r] in data]
    cols = [COLOR[n] for n in names]

    fig = plt.figure(figsize=(14, 4.6))
    # Panel 1: block reliability (the headline)
    ax1 = fig.add_subplot(1, 3, 1)
    rates = [data[n]["block_rate"] for n in names]
    ax1.bar(names, rates, color=cols)
    ax1.set_title("Defensive reliability:\nrounds attacker was blocked")
    ax1.set_ylabel("% of rounds blocked"); ax1.set_ylim(0, 105)
    for i, v in enumerate(rates):
        ax1.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
    ax1.tick_params(axis="x", rotation=20)

    # Panel 2: decisiveness (lower = faster)
    ax2 = fig.add_subplot(1, 3, 2)
    import numpy as np
    x = np.arange(len(names)); w = 0.38
    ax2.bar(x - w / 2, [data[n]["avg_block_step"] for n in names], w, label="block step", color="#d7263d")
    ax2.bar(x + w / 2, [data[n]["avg_patch_step"] for n in names], w, label="patch step", color="#2bb673")
    ax2.set_title("Decisiveness:\nstep of first block / patch (lower=faster)")
    ax2.set_ylabel("Blue step index"); ax2.set_xticks(x); ax2.set_xticklabels(names, rotation=20)
    ax2.legend(fontsize=8)

    # Panel 3: per-round detections curve
    ax3 = fig.add_subplot(1, 3, 3)
    for n in names:
        ax3.plot(range(len(data[n]["det"])), data[n]["det"], marker="o", ms=3,
                 label=n, color=COLOR[n], lw=2 if n == "FINE-TUNED" else 1)
    ax3.set_title("IDS detections / round"); ax3.set_xlabel("round")
    ax3.set_ylabel("alerts"); ax3.legend(fontsize=7); ax3.grid(True, alpha=0.3)

    fig.suptitle("CyberSwarm — 4 learning methods vs. the fine-tuned defender (4th method)",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = "ft_comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"wrote {out}\n")

    # Table
    hdr = f"{'method':<12}{'block%':>8}{'blocked':>9}{'blk_step':>9}{'patch_step':>11}{'mean_det':>9}{'mean_blue':>10}{'legit_blk':>10}"
    print(hdr); print("-" * len(hdr))
    for n in names:
        d = data[n]
        print(f"{n:<12}{d['block_rate']:>7.0f}%{str(d['blocked'])+'/'+str(d['n']):>9}"
              f"{d['avg_block_step']:>9.2f}{d['avg_patch_step']:>11.2f}"
              f"{sum(d['det'])/d['n']:>9.2f}{d['mean_blue']:>10.2f}{d['legit']:>10}")


if __name__ == "__main__":
    main()
