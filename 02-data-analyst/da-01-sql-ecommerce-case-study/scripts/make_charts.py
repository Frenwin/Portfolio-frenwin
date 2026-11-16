"""Draw the README charts from docs/answers.json (run scripts/run_queries.py first)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
SERIES_1, SERIES_2 = "#2a78d6", "#eb6834"  # validated pair (scripts in the dataviz method)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK_2, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def base(ax, title: str, subtitle: str) -> None:
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color=INK, pad=28)
    ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=10.5, color=INK_2)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def monthly_gmv(data: dict) -> None:
    rows = data["q01_monthly_trend"]["rows"]
    months = [r[0] for r in rows]
    gmv = [r[2] / 1e6 for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    base(ax, "GMV grew 6x during 2017, then plateaued near R$0.9M a month",
         "Monthly GMV of valid orders, millions of BRL, Jan 2017 - Aug 2018")
    x = range(len(months))
    ax.plot(x, gmv, color=SERIES_1, linewidth=2, marker="o", markersize=4)
    peak = months.index("2017-11")
    ax.annotate("Nov 2017: Black Friday\n+52% vs October", xy=(peak, gmv[peak]), xytext=(peak - 6.2, gmv[peak] + 0.02),
                fontsize=10, color=INK, arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.8})
    ax.axvspan(months.index("2018-01") - 0.3, len(months) - 0.7, color=GRID, alpha=0.45, linewidth=0)
    ax.text(months.index("2018-01"), 0.08, "2018: flat, 0.84-0.99M every month", fontsize=10, color=INK_2)
    ax.set_xticks(list(x)[::2], [m for m in months][::2], rotation=0, fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}M"))
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "monthly_gmv.png", facecolor=SURFACE)
    plt.close(fig)


def reviews_by_delivery(data: dict) -> None:
    rows = data["q07_late_delivery_vs_reviews"]["rows"]
    labels = [r[0].split(". ", 1)[1] for r in rows]
    reviews = [r[3] for r in rows]
    shares = [r[2] for r in rows]
    late = ["late" in l for l in labels]
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    base(ax, "Reviews fall from 4.0 to 3.3 when an order is 1-3 days late, and to 1.7 beyond a week",
         "Average review score (1-5) by delivery time versus the estimate shown at purchase")
    bars = ax.bar(range(len(labels)), reviews, width=0.62,
                  color=[SERIES_2 if is_late else SERIES_1 for is_late in late], edgecolor=SURFACE, linewidth=2)
    for i, (bar, value, share) in enumerate(zip(bars, reviews, shares)):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.07, f"{value:.2f}", ha="center", fontsize=10.5,
                color=INK, fontweight="bold")
        ax.text(bar.get_x() + bar.get_width() / 2, 0.12, f"{share:.0f}% of orders", ha="center", fontsize=8.5,
                color=SURFACE)
    ax.set_xticks(range(len(labels)), labels, fontsize=9.5)
    ax.set_ylim(0, 5)
    ax.text(1, 4.75, "On time or early", color=SERIES_1, fontsize=10.5, ha="center", fontweight="bold")
    ax.text(4, 4.75, "Late", color=SERIES_2, fontsize=10.5, ha="center", fontweight="bold")
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "reviews_by_delivery.png", facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    answers = json.loads((ROOT / "docs" / "answers.json").read_text(encoding="utf-8"))
    monthly_gmv(answers)
    reviews_by_delivery(answers)
    print("charts written to docs/")
