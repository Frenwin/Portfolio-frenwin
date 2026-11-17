"""Draw the README charts from docs/answers.json (run scripts/run_queries.py first)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE = "#2a78d6"            # series 1 of the validated categorical palette
BLUE_SOFT = "#86b6ef"       # step 250 of the blue ramp (lightest ordinal step allowed on light)
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK_2, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def style(ax, grid_axis: str = "y") -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def titles(fig, title: str, subtitle: str) -> None:
    fig.text(0.012, 0.965, title, fontsize=14, fontweight="bold", color=INK, va="top")
    fig.text(0.012, 0.905, subtitle, fontsize=10.5, color=INK_2, va="top")


def save(fig, name: str) -> None:
    fig.savefig(DOCS / name, facecolor=SURFACE)
    plt.close(fig)


def funnel(data: dict) -> None:
    rows = sorted(r for r in data["q10_user_funnel"]["rows"] if r[0][0].isdigit())
    steps = [r[0].split(". ", 1)[1] for r in rows]
    users = [r[1] for r in rows]
    of_prev = [r[3] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=150)
    fig.subplots_adjust(left=0.2, right=0.97, top=0.8, bottom=0.08)
    titles(fig, "77% of visitors never open a product page",
           "Users reaching each step in order, across sessions, Nov 2020 - Jan 2021 (GA4 merchandise store)")
    y = list(range(len(steps)))[::-1]
    ax.barh(y, users, height=0.62, color=BLUE)
    for yi, n, p, i in zip(y, users, of_prev, range(len(steps))):
        label = f"{n:,}" if i == 0 else f"{n:,}  ·  {p:.0f}% of previous step"
        ax.text(n + 3000, yi, label, va="center", fontsize=10.5, color=INK)
    ax.set_yticks(y, steps, fontsize=11, color=INK)
    ax.set_xlim(0, 360_000)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    style(ax, "x")
    ax.spines["bottom"].set_visible(False)
    save(fig, "funnel.png")


def weekly_trend(data: dict) -> None:
    rows = data["q05_weekly_trend"]["rows"]
    weeks = [r[0][5:].replace("-", "/") for r in rows]
    sessions = [r[2] / 1000 for r in rows]
    conv = [r[4] for r in rows]
    x = list(range(len(weeks)))
    cut = [r[0] for r in rows].index("2020-12-21")
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 6), dpi=150, sharex=True,
                                      gridspec_kw={"height_ratios": [1, 1.25], "hspace": 0.35})
    fig.subplots_adjust(left=0.08, right=0.97, top=0.81, bottom=0.08)
    titles(fig, "Traffic recovered in January, conversion did not",
           "Weekly sessions (top) and share of sessions with a purchase (bottom), weeks starting Monday")
    for ax in (top, bottom):
        ax.axvspan(cut - 0.45, len(x) - 0.55, color=GRID, alpha=0.5, linewidth=0)
        style(ax)
    top.bar(x, sessions, width=0.7, color=BLUE_SOFT)
    top.set_ylim(0, 45)
    top.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}k" if v else "0"))
    top.set_title("Sessions", loc="left", fontsize=10.5, color=INK_2)
    bottom.plot(x, conv, color=BLUE, linewidth=2, marker="o", markersize=5)
    peak = conv.index(max(conv))
    low = conv.index(min(conv))
    bottom.annotate(f"{conv[peak]:.2f}%", (peak, conv[peak]), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=10, color=INK)
    bottom.annotate(f"{conv[low]:.2f}%", (low, conv[low]), xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=10, color=INK)
    bottom.text(cut - 0.3, 2.3, "From 21 Dec: after the holiday peak", fontsize=10, color=INK_2)
    bottom.set_ylim(0, 2.6)
    bottom.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
    bottom.set_title("Session conversion", loc="left", fontsize=10.5, color=INK_2)
    bottom.set_xticks(x, weeks, fontsize=9)
    save(fig, "weekly_trend.png")


def cohort_heatmap(data: dict) -> None:
    rows = data["q06_weekly_cohort_retention"]["rows"]
    cohorts = sorted({(r[0], r[1]) for r in rows if r[2] >= 1})  # the last cohort has no week 1 yet
    max_week = max(r[2] for r in rows)
    grid = [[None] * max_week for _ in cohorts]
    index = {c[0]: i for i, c in enumerate(cohorts)}
    for cohort, _, week, _, pct in rows:
        if week >= 1 and cohort in index:
            grid[index[cohort]][week - 1] = pct
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    cmap.set_bad(SURFACE)
    vmax = 6.0
    masked = [[float("nan") if v is None else min(v, vmax) for v in row] for row in grid]
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=150)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.83, bottom=0.08)
    titles(fig, "Holiday cohorts came back half as often as November cohorts",
           "Share of each weekly cohort (first visit) active again N weeks later, %")
    ax.imshow(masked, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            if v is not None:
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5,
                        color="#ffffff" if v >= 3.0 else INK)
    for k in range(len(cohorts) + 1):
        ax.axhline(k - 0.5, color=SURFACE, linewidth=2)
    for k in range(max_week + 1):
        ax.axvline(k - 0.5, color=SURFACE, linewidth=2)
    ax.set_xticks(range(max_week), [f"W{w}" for w in range(1, max_week + 1)], fontsize=9.5)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(cohorts)), [f"{c[0][5:].replace('-', '/')}  ({c[1]:,})" for c in cohorts],
                  fontsize=9.5)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.text(-0.02, 1.0, "Cohort week (new users)", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=9, color=MUTED)
    save(fig, "cohort_retention.png")


def by_source(data: dict) -> None:
    all_rows = data["q04_conversion_by_source"]["rows"]
    deleted = next(r for r in all_rows if r[0] == "(data deleted)")
    rows = sorted((r for r in all_rows if r is not deleted), key=lambda r: r[4])
    labels = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4.4), dpi=150)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.79, bottom=0.16)
    titles(fig, "Referral visitors convert twice as well as paid search visitors",
           "Share of users who bought, by first-touch medium; label shows users and revenue per user")
    ax.barh(range(len(rows)), [r[4] for r in rows], height=0.62, color=BLUE)
    for i, r in enumerate(rows):
        ax.text(r[4] + 0.03, i, f"{r[4]:.2f}%  ·  {r[1]:,} users  ·  ${r[6]:.2f}/user",
                va="center", fontsize=10, color=INK)
    ax.set_yticks(range(len(rows)), labels, fontsize=11, color=INK)
    ax.set_xlim(0, 3.6)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.5))
    fig.text(0.012, 0.03, f"Not shown: \"(data deleted)\", {deleted[1]:,} users whose source was erased on request "
             f"({deleted[4]:.2f}% conversion). <Other> is the dataset's obfuscation bucket.", fontsize=9, color=MUTED)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    style(ax, "x")
    ax.spines["bottom"].set_visible(False)
    save(fig, "conversion_by_source.png")


def main() -> None:
    data = json.loads((DOCS / "answers.json").read_text(encoding="utf-8"))
    funnel(data)
    weekly_trend(data)
    cohort_heatmap(data)
    by_source(data)
    print("charts written to docs/")


if __name__ == "__main__":
    main()
