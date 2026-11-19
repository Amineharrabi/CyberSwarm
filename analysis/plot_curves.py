"""
plot_curves.py — turn runs/<run>/curve.json into the figures for the report.
Also builds the E2 ablation table if several runs exist (baseline vs no-learning etc.).

    python plot_curves.py ../runs/baseline ../runs/no_learning
"""
import sys
import os
import json
import matplotlib.pyplot as plt


def load(run_dir):
    with open(os.path.join(run_dir, "curve.json"), encoding="utf-8") as f:
        return json.load(f)


def main(run_dirs):
    plt.figure(figsize=(8, 5))
    table = []
    for rd in run_dirs:
        curve = load(rd)
        name = os.path.basename(rd.rstrip("/\\"))
        rounds = [c["round"] for c in curve]
        red = [c["red_score"] for c in curve]
        blue = [c["blue_score"] for c in curve]
        plt.plot(rounds, red, marker="o", label=f"{name} — Red")
        plt.plot(rounds, blue, marker="s", label=f"{name} — Blue")
        detect_rate = sum(c["detections"] > 0 for c in curve) / max(1, len(curve))
        flags = sum(c["flag_captured"] for c in curve)
        table.append((name, red[-1], blue[-1], round(detect_rate, 2), flags))

    plt.xlabel("Round"); plt.ylabel("Score")
    plt.title("Learning curves — Red vs Blue")
    plt.legend(); plt.grid(True, alpha=0.3)
    out = "learning_curves.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"wrote {out}")

    print("\nAblation table (E2):")
    print(f"{'config':<16}{'Red_final':>10}{'Blue_final':>11}{'detect_rate':>13}{'flags':>7}")
    for row in table:
        print(f"{row[0]:<16}{row[1]:>10}{row[2]:>11}{row[3]:>13}{row[4]:>7}")


if __name__ == "__main__":
    dirs = sys.argv[1:] or ["../runs/baseline"]
    main(dirs)
