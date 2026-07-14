"""Generate charts for the trending repos report."""

import os
import io
import base64
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt


def generate_charts(repos, output_dir=None):
    """Generate chart images and return a dict of {chart_name: base64_png}.

    Charts produced:
    - top_stars: horizontal bar chart of top repos by total stars
    - language_pie: pie chart of language distribution
    - stars_today: bar chart of stars gained today
    """
    charts = {}

    if not repos:
        return charts

    # Chart 1: Top repos by total stars (horizontal bar)
    charts["top_stars"] = _chart_top_stars(repos)

    # Chart 2: Language distribution (pie)
    charts["language_pie"] = _chart_language_pie(repos)

    # Chart 3: Stars gained today (bar)
    charts["stars_today"] = _chart_stars_today(repos)

    # Save to disk if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for name, b64 in charts.items():
            img_data = base64.b64decode(b64)
            with open(os.path.join(output_dir, f"{name}.png"), "wb") as f:
                f.write(img_data)

    return charts


def _chart_top_stars(repos):
    """Horizontal bar chart of top repos by total stars."""
    top = sorted(repos, key=lambda r: r["stars"], reverse=True)[:15]

    fig, ax = plt.subplots(figsize=(10, 6))
    names = [r["name"].split("/")[-1] for r in top]
    stars = [r["stars"] for r in top]

    colors = plt.cm.viridis([i / len(top) for i in range(len(top))])
    bars = ax.barh(range(len(top)), stars, color=colors, edgecolor="white", height=0.7)

    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Total Stars", fontsize=11)
    ax.set_title("Top Trending Repositories by Stars", fontsize=14, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add value labels
    for bar, val in zip(bars, stars):
        if val >= 1000:
            label = f"{val/1000:.1f}k"
        else:
            label = str(val)
        ax.text(bar.get_width() + max(stars) * 0.01, bar.get_y() + bar.get_height()/2,
                label, va="center", fontsize=8, color="#555")

    plt.tight_layout()
    return _fig_to_base64(fig)


def _chart_language_pie(repos):
    """Pie chart of programming language distribution."""
    lang_counts = Counter(r["language"] or "Other" for r in repos)

    # Keep top 8, group rest as "Other"
    if len(lang_counts) > 8:
        top_langs = lang_counts.most_common(8)
        other_count = sum(c for _, c in lang_counts.most_common()[8:])
        labels = [l for l, _ in top_langs] + ["Other"]
        sizes = [c for _, c in top_langs] + [other_count]
    else:
        labels = list(lang_counts.keys())
        sizes = list(lang_counts.values())

    fig, ax = plt.subplots(figsize=(7, 7))
    colors = plt.cm.Set3(range(len(labels)))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=colors, startangle=90,
        textprops={"fontsize": 10},
    )
    ax.set_title("Language Distribution", fontsize=14, fontweight="bold")

    plt.tight_layout()
    return _fig_to_base64(fig)


def _chart_stars_today(repos):
    """Bar chart of stars gained today."""
    top = sorted(repos, key=lambda r: r["stars_today"], reverse=True)[:15]

    fig, ax = plt.subplots(figsize=(10, 6))
    names = [r["name"].split("/")[-1] for r in top]
    today = [r["stars_today"] for r in top]

    colors = plt.cm.plasma([i / len(top) for i in range(len(top))])
    bars = ax.bar(range(len(top)), today, color=colors, edgecolor="white", width=0.7)

    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Stars Today", fontsize=11)
    ax.set_title("Stars Gained Today", fontsize=14, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add value labels on top
    for bar, val in zip(bars, today):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(today) * 0.01,
                str(val), ha="center", va="bottom", fontsize=8, color="#555")

    plt.tight_layout()
    return _fig_to_base64(fig)


def _fig_to_base64(fig):
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
