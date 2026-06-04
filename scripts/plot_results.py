"""
Render the benchmark results to a PNG chart for the README / blog.
Reads results/benchmark_full_metrics.json, writes results/chart_bleu_comet.png.

Run: scripts/.venv-bench/bin/python scripts/plot_results.py   (any env with matplotlib)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "results" / "benchmark_full_metrics.json").read_text())
systems = data["systems"]

# sort by COMET ascending so highest is at top of horizontal bars
systems = sorted(systems, key=lambda s: s.get("term_acc_pct") or 0)
names = [s["system"] for s in systems]
comet = [s.get("comet") or 0 for s in systems]
term = [s.get("term_acc_pct") or 0 for s in systems]
is_prod = [s["type"] == "product" for s in systems]

PROD = "#1a4fb4"   # Anuvad product
RAW = "#9aa7bd"    # raw models

fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), sharey=True)

for ax, vals, title, lo in [
    (axes[0], term, "Legal-term accuracy (%)  -  higher is better", 84),
    (axes[1], comet, "Overall quality (AI-judge score)  -  higher is better", 76),
]:
    colors = [PROD if p else RAW for p in is_prod]
    bars = ax.barh(names, vals, color=colors)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlim(lo, max(vals) + (max(vals) - lo) * 0.18)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + (max(vals) - lo) * 0.01,
                b.get_y() + b.get_height() / 2, f"{v:.2f}",
                va="center", fontsize=9)
    ax.grid(axis="x", alpha=0.25)
    ax.tick_params(labelsize=9)

from matplotlib.patches import Patch  # noqa: E402
fig.legend(handles=[Patch(color=PROD, label="Anuvad (product)"),
                    Patch(color=RAW, label="Raw model")],
           loc="lower center", ncol=2, frameon=False, fontsize=10)
fig.suptitle("English→Hindi Legal Translation — WMT25 Legal Domain Test Suite "
             "(IIT Patna), 500 sentences",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0.05, 1, 0.95])

out = ROOT / "results" / "chart_bleu_comet.png"
fig.savefig(out, dpi=150)
print("wrote", out)
