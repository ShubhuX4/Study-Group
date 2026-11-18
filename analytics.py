"""
analytics.py
------------
Unit III: Pandas (DataFrame, groupby, aggregation) and NumPy.
Unit V  : Matplotlib charts.
"""
import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # draw charts without opening a window (needed on servers)
import matplotlib.pyplot as plt

NAVY = "#1e2a5e"
PURPLE = "#7c3aed"
LAVENDER = "#c4b5fd"
COLORS = [NAVY, PURPLE, LAVENDER, "#a78bfa", "#4c5aa8", "#8b9bd6"]


def get_stats(groups, registrations):
    """groups = list of dictionaries (from StudyGroup.to_api_dict).
    Returns a dictionary with all dashboard numbers."""
    stats = {
        "total_groups": 0, "total_students": 0, "total_registrations": 0,
        "popular_subjects": [], "mode_counts": {"Online": 0, "Offline": 0},
        "total_capacity": 0, "filled_seats": 0, "available_seats": 0,
        "fill_percent": 0, "open_groups": 0, "full_groups": 0,
    }
    if len(groups) == 0:
        return stats

    df = pd.DataFrame(groups)
    stats["total_groups"] = int(len(df))

    # Registrations -> unique students (by email)
    if len(registrations) > 0:
        reg_df = pd.DataFrame(registrations)
        stats["total_registrations"] = int(len(reg_df))
        stats["total_students"] = int(reg_df["email"].nunique())

    # Group by subject and aggregate
    by_subject = df.groupby("subject").agg(
        groups=("id", "count"), members=("member_count", "sum")
    ).reset_index().sort_values(["groups", "members"], ascending=False)
    for _, row in by_subject.head(5).iterrows():
        stats["popular_subjects"].append(
            {"subject": row["subject"], "groups": int(row["groups"]), "members": int(row["members"])})

    # Group by study mode
    for mode, count in df.groupby("mode").size().items():
        stats["mode_counts"][mode] = int(count)

    # NumPy for the capacity calculations
    capacity = np.array(df["max_members"])
    filled = np.array(df["member_count"])
    stats["total_capacity"] = int(np.sum(capacity))
    stats["filled_seats"] = int(np.sum(filled))
    stats["available_seats"] = int(np.sum(capacity - filled))
    stats["fill_percent"] = round(float(np.sum(filled) / np.sum(capacity) * 100), 1)

    stats["open_groups"] = int((df["status"] == "Open").sum())
    stats["full_groups"] = int((df["status"] == "Full").sum())
    return stats


def _empty_chart(title):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, "No data yet", ha="center", va="center", fontsize=14, color="#6b7280")
    ax.set_title(title, color=NAVY, fontweight="bold")
    ax.axis("off")
    return fig


def _to_png(fig):
    """Convert a Matplotlib figure into PNG bytes in memory."""
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def subject_chart(groups):
    """Bar chart: number of groups per subject."""
    if len(groups) == 0:
        return _to_png(_empty_chart("Groups by Subject"))
    counts = pd.DataFrame(groups).groupby("subject").size().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(counts.index, counts.values, color=PURPLE)
    ax.set_title("Groups by Subject", color=NAVY, fontweight="bold")
    ax.set_ylabel("Number of groups")
    ax.set_yticks(range(0, int(counts.max()) + 2))
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    ax.spines[["top", "right"]].set_visible(False)
    return _to_png(fig)


def mode_chart(groups):
    """Pie chart: online vs offline groups."""
    if len(groups) == 0:
        return _to_png(_empty_chart("Online vs Offline Groups"))
    counts = pd.DataFrame(groups).groupby("mode").size()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%", startangle=90,
           colors=[NAVY, LAVENDER], textprops={"color": "black"})
    ax.set_title("Online vs Offline Groups", color=NAVY, fontweight="bold")
    return _to_png(fig)


def registration_chart(groups):
    """Bar chart: registered students in each group."""
    if len(groups) == 0:
        return _to_png(_empty_chart("Registrations per Group"))
    df = pd.DataFrame(groups).sort_values("member_count", ascending=False).head(8)
    names = [n if len(n) <= 22 else n[:20] + "..." for n in df["name"]]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(names, df["member_count"], color=NAVY)
    ax.invert_yaxis()
    ax.set_title("Registrations per Group", color=NAVY, fontweight="bold")
    ax.set_xlabel("Registered students")
    ax.spines[["top", "right"]].set_visible(False)
    return _to_png(fig)


# Dictionary that maps a chart name (URL) to its function
CHART_FUNCTIONS = {
    "subjects": subject_chart,
    "mode": mode_chart,
    "registrations": registration_chart,
}
