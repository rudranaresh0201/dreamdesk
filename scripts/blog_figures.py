"""Figures for the DreamDesk blog post. Numbers are copied from the results files named on each figure.

    python3 scripts/blog_figures.py OUTDIR      (needs matplotlib)
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/blog"); OUT.mkdir(parents=True, exist_ok=True)
INK, DIM, FAINT, ACCENT, GREY, BG, SAND = "#1c1a17", "#6b6559", "#b9b1a2", "#c2410c", "#8a8375", "#fffdf8", "#d9cfbd"
plt.rcParams.update({
    "font.family": "Ubuntu Sans", "font.size": 11, "axes.edgecolor": FAINT, "axes.labelcolor": DIM,
    "xtick.color": DIM, "ytick.color": DIM, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "axes.titlesize": 12,
    "axes.titlecolor": INK, "axes.titlelocation": "left", "legend.frameon": False,
})


def bars(ax, labels, series, colors, width=0.8):
    n = len(series); w = width / n; x = np.arange(len(labels))
    for i, (name, vals) in enumerate(series.items()):
        ax.bar(x + (i - (n - 1) / 2) * w, vals, w * 0.92, label=name, color=colors[i])
    ax.set_xticks(x, labels)


def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / name, dpi=200); plt.close(fig); print("wrote", OUT / name)


# 1. world model vs memorising, horizon 5, unvisited windows (experiments/world_model_results.md)
apps = ["calculator", "clocks", "files", "logs", "resources", "text-editor"]
fig, ax = plt.subplots(figsize=(7.2, 3.4))
bars(ax, apps, {"Memo (replay what happened before)": [0.288, 0.441, 0.363, 0.594, 0.373, 0.236],
                "world model (5-network ensemble)": [0.483, 0.637, 0.585, 0.699, 0.625, 0.588]}, [SAND, ACCENT])
ax.set(ylabel="delta F1, 5 steps ahead", ylim=(0, 0.9)); ax.legend(loc="upper left", ncol=2)
ax.set_title("Predicting what changes on screen, in situations not seen while exploring")
save(fig, "fig_wm.png")

# 2. seen vs combo goals at 100 clicks (experiments/generalise_results.md)
fig, ax = plt.subplots(figsize=(7.2, 3.4))
bars(ax, ["seen goals (n = 60)", "combo goals (n = 32)"],
     {"random clicking": [26.7, 11.5], "map of memorised screens": [39.4, 4.2], "planning in the dream": [47.2, 19.8]},
     [SAND, GREY, ACCENT], width=0.6)
ax.set(ylabel="real success (%)", ylim=(0, 55)); ax.legend(loc="upper right")
ax.set_title("Files app, after 100 clicks of exploring")
save(fig, "fig_combo.png")

# 3. Test 1: priors on 8 held-out apps, B = 100 (experiments/scale_results.md)
apps = ["disk-usage", "files", "logs", "web-chat", "web-fitness", "web-quiz", "web-todo", "web-weather"]
fig, ax = plt.subplots(figsize=(8, 3.8))
bars(ax, apps, {"from scratch": [0.422, 0.281, 0.416, 0.721, 0.685, 0.538, 0.681, 0.538],
                "prior: 7 apps": [0.634, 0.397, 0.521, 0.738, 0.749, 0.597, 0.741, 0.573],
                "prior: 15 apps": [0.576, 0.416, 0.536, 0.742, 0.802, 0.793, 0.768, 0.634],
                "prior: 23 apps": [0.534, 0.414, 0.549, 0.746, 0.807, 0.834, 0.778, 0.704]},
     [SAND, "#e8b79a", "#d9774a", ACCENT])
ax.axvline(2.5, color=FAINT, lw=1, ls="--"); ax.text(0.9, 0.93, "desktop", color=DIM, ha="center"); ax.text(5, 0.93, "web", color=DIM, ha="center")
ax.set(ylabel="delta F1, 5 steps ahead", ylim=(0, 1)); ax.legend(loc="upper left", ncol=4, bbox_to_anchor=(0, 1.13))
plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
ax.set_title("New app, 100 clicks of exploring, then fine-tune", pad=30)
save(fig, "fig_scale.png")
