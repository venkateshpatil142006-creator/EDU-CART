import base64
import io
import threading
import time
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backend.storage import analytics_cache_key, connect_analytics


_CACHE_TTL_SECONDS = 60
_cache: Dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_plot_lock = threading.Lock()


def _read_attempts() -> pd.DataFrame:
    connection = connect_analytics()
    try:
        return pd.read_sql(
            """
            SELECT a.user_id, a.deck_id, d.title AS deck_title, a.card_id, a.is_correct,
                   a.time_taken_ms, a.hints_used, a.points_awarded, a.created_at,
                   d.category AS subject,
                   c.difficulty, c.question
            FROM attempts a
            JOIN decks d ON d.id = a.deck_id
            JOIN cards c ON c.id = a.card_id
            """,
            connection,
        )
    finally:
        connection.close()


def _png_data_uri(figure) -> str:
    image = io.BytesIO()
    figure.savefig(image, format="png", dpi=110, bbox_inches="tight")
    plt.close(figure)
    return "data:image/png;base64," + base64.b64encode(image.getvalue()).decode("ascii")


def _chart(title: str, xlabel: str, ylabel: str, theme: str = "dark"):
    dark = theme == "dark"
    figure_bg = "#0b1117" if dark else "#f3f6f8"
    axes_bg = "#111b24" if dark else "#ffffff"
    text = "#dce6ef" if dark else "#0f172a"
    secondary = "#91a4b6" if dark else "#475569"
    grid = "#293a48" if dark else "#e2e8f0"
    figure, axis = plt.subplots(figsize=(7, 3.6))
    figure.patch.set_facecolor(figure_bg)
    axis.set_facecolor(axes_bg)
    axis.set_title(title, color=text, fontsize=12, weight="bold")
    axis.set_xlabel(xlabel, color=secondary)
    axis.set_ylabel(ylabel, color=secondary)
    axis.tick_params(colors=secondary)
    for spine in axis.spines.values():
        spine.set_color(grid)
    axis.grid(axis="y", color=grid, linewidth=0.8, alpha=0.8)
    return figure, axis


def _render_charts(
    accuracy_by_subject: pd.DataFrame,
    daily_activity: pd.DataFrame,
    learning_curve: pd.DataFrame,
    response_times: pd.Series,
    points: Optional[pd.Series] = None,
    theme: str = "dark",
) -> Dict[str, str]:
    charts = {}
    bar_color = "#37c9a5" if theme == "dark" else "#0d9488"
    figure, axis = _chart("Accuracy by subject", "Subject", "Accuracy (%)", theme)
    if not accuracy_by_subject.empty:
        axis.bar(
            accuracy_by_subject["subject"],
            accuracy_by_subject["accuracy"],
            color=bar_color,
        )
        axis.set_ylim(0, 100)
        axis.tick_params(axis="x", labelrotation=25)
    charts["accuracy_by_subject"] = _png_data_uri(figure)

    figure, axis = _chart("Learning curve", "Attempt", "Cumulative accuracy (%)", theme)
    if not learning_curve.empty:
        x = learning_curve["attempt"].to_numpy(dtype=float)
        y = learning_curve["accuracy"].to_numpy(dtype=float)
        axis.plot(x, y, color=bar_color, marker="o", markersize=3, label="Accuracy")
        if len(x) >= 2:
            slope, intercept = np.polyfit(x, y, 1)
            axis.plot(
                x, slope * x + intercept,
                color="#fb7185" if theme == "dark" else "#e11d48",
                linestyle="--", label="Trend",
            )
            axis.legend(
                frameon=False,
                labelcolor="#dce6ef" if theme == "dark" else "#0f172a",
            )
        axis.set_ylim(0, 100)
    charts["learning_curve"] = _png_data_uri(figure)

    figure, axis = _chart("Daily activity", "Day", "Attempts", theme)
    if not daily_activity.empty:
        axis.bar(
            daily_activity["day"].astype(str),
            daily_activity["attempts"],
            color=bar_color,
        )
        axis.tick_params(axis="x", labelrotation=25)
    charts["daily_activity"] = _png_data_uri(figure)

    figure, axis = _chart("Response time distribution", "Response time (seconds)", "Attempts", theme)
    if not response_times.empty:
        axis.hist(response_times / 1000, bins=min(12, max(3, len(response_times))), color=bar_color)
    charts["response_time_distribution"] = _png_data_uri(figure)

    if points is not None:
        figure, axis = _chart("Points distribution", "Points", "Learners", theme)
        if not points.empty:
            axis.hist(points, bins=min(12, max(3, len(points))), color=bar_color)
        charts["points_distribution"] = _png_data_uri(figure)
    return charts


def _make_charts(
    accuracy_by_subject: pd.DataFrame,
    daily_activity: pd.DataFrame,
    learning_curve: pd.DataFrame,
    response_times: pd.Series,
    points: Optional[pd.Series] = None,
    theme: str = "dark",
) -> Dict[str, str]:
    with _plot_lock:
        return _render_charts(
            accuracy_by_subject,
            daily_activity,
            learning_curve,
            response_times,
            points,
            theme,
        )


def _empty_personal_result(user_id: str, theme: str = "dark") -> dict:
    empty = pd.DataFrame()
    return {
        "user_id": user_id,
        "total_attempts": 0,
        "accuracy": 0.0,
        "rank": None,
        "accuracy_by_deck": [],
        "accuracy_by_subject": [],
        "accuracy_by_difficulty": [],
        "hint_usage_rate": 0.0,
        "daily_activity": [],
        "response_time_ms_percentiles": {"p50": None, "p90": None, "p95": None},
        "learning_curve_trend_slope": 0.0,
        "weak_cards": [],
        "charts": _make_charts(
            empty, empty, empty, pd.Series(dtype=float), theme=theme
        ),
    }


def analyze_personal_attempts(
    attempts: pd.DataFrame,
    user_id: str,
    all_attempts: Optional[pd.DataFrame] = None,
    theme: str = "dark",
) -> dict:
    personal = attempts.loc[attempts["user_id"] == user_id].copy()
    if personal.empty:
        return _empty_personal_result(user_id, theme)

    personal["created_at"] = pd.to_datetime(personal["created_at"], utc=True, errors="coerce")
    personal["day"] = personal["created_at"].dt.date.astype(str)
    personal["is_correct"] = personal["is_correct"].astype(int)
    personal["time_taken_ms"] = pd.to_numeric(personal["time_taken_ms"], errors="coerce")
    total = len(personal)
    accuracy = personal["is_correct"].mean() * 100

    def grouped_accuracy(column: str, label: str) -> list:
        grouped = personal.groupby(column, dropna=False).agg(
            attempts=("is_correct", "size"),
            correct=("is_correct", "sum"),
        ).reset_index()
        grouped["accuracy"] = (grouped["correct"] / grouped["attempts"] * 100).round(1)
        grouped = grouped.rename(columns={column: label})
        return grouped.to_dict(orient="records")

    if "deck_title" in personal.columns:
        by_deck = personal.groupby(["deck_id", "deck_title"], dropna=False).agg(
            attempts=("is_correct", "size"), correct=("is_correct", "sum")
        ).reset_index()
        by_deck["accuracy"] = (by_deck["correct"] / by_deck["attempts"] * 100).round(1)
        accuracy_by_deck = by_deck.to_dict(orient="records")
    else:
        accuracy_by_deck = grouped_accuracy("deck_id", "deck_id")

    daily = (
        personal.groupby("day").size().rename("attempts").reset_index()
        .rename(columns={"day": "day"})
        .sort_values("day")
    )
    daily_activity = daily.rename(columns={"day": "day"}).to_dict(orient="records")
    ordered = personal.sort_values("created_at").reset_index(drop=True)
    ordered["attempt"] = np.arange(1, total + 1)
    ordered["accuracy"] = (ordered["is_correct"].expanding().mean() * 100).round(1)
    learning_curve = ordered[["attempt", "accuracy"]]
    slope = float(np.polyfit(learning_curve["attempt"], learning_curve["accuracy"], 1)[0]) if total >= 2 else 0.0
    valid_times = personal["time_taken_ms"].dropna()
    percentiles = (
        np.percentile(valid_times, [50, 90, 95]).round(1).tolist()
        if not valid_times.empty else [None, None, None]
    )
    weak_group = personal.groupby(["card_id", "question"], dropna=False).agg(
        attempts=("is_correct", "size"), correct=("is_correct", "sum")
    ).reset_index()
    weak_group["accuracy"] = weak_group["correct"] / weak_group["attempts"] * 100
    weak_group["is_weak"] = np.where(
        (weak_group["accuracy"] < 50) & (weak_group["attempts"] >= 3),
        True,
        False,
    )
    weak_cards = weak_group.loc[weak_group["is_weak"]].sort_values(
        ["accuracy", "attempts"]
    ).drop(columns=["correct", "is_weak"]).to_dict(orient="records")

    rank = None
    if all_attempts is not None and not all_attempts.empty:
        totals = all_attempts.groupby("user_id")["points_awarded"].sum().rename("points").reset_index()
        totals["rank"] = totals["points"].rank(method="min", ascending=False).astype(int)
        row = totals.loc[totals["user_id"] == user_id, "rank"]
        rank = int(row.iloc[0]) if not row.empty else None

    subjects = personal.groupby("subject").agg(
        attempts=("is_correct", "size"), correct=("is_correct", "sum")
    ).reset_index()
    subjects["accuracy"] = (subjects["correct"] / subjects["attempts"] * 100).round(1)
    charts = _make_charts(
        subjects[["subject", "accuracy"]],
        daily,
        learning_curve,
        valid_times,
        theme=theme,
    )
    return {
        "user_id": user_id,
        "total_attempts": total,
        "accuracy": round(float(accuracy), 1),
        "rank": rank,
        "accuracy_by_deck": accuracy_by_deck,
        "accuracy_by_subject": grouped_accuracy("subject", "subject"),
        "accuracy_by_difficulty": grouped_accuracy("difficulty", "difficulty"),
        "hint_usage_rate": round(float((personal["hints_used"] > 0).mean() * 100), 1),
        "daily_activity": daily_activity,
        "response_time_ms_percentiles": dict(zip(("p50", "p90", "p95"), percentiles)),
        "learning_curve_trend_slope": round(slope, 3),
        "weak_cards": weak_cards,
        "charts": charts,
    }


def analyze_global_attempts(attempts: pd.DataFrame, theme: str = "dark") -> dict:
    if attempts.empty:
        empty = pd.DataFrame()
        return {
            "total_attempts": 0,
            "average_accuracy_by_subject": [],
            "hardest_questions": [],
            "most_active_days": [],
            "points_distribution": [],
            "charts": _make_charts(
                empty, empty, empty, pd.Series(dtype=float), pd.Series(dtype=float), theme
            ),
        }
    data = attempts.copy()
    data["created_at"] = pd.to_datetime(data["created_at"], utc=True, errors="coerce")
    data["day"] = data["created_at"].dt.date.astype(str)
    data["is_correct"] = data["is_correct"].astype(int)
    accuracy_by_subject = data.groupby("subject").agg(
        attempts=("is_correct", "size"), correct=("is_correct", "sum")
    ).reset_index()
    accuracy_by_subject["accuracy"] = (
        accuracy_by_subject["correct"] / accuracy_by_subject["attempts"] * 100
    ).round(1)
    hardest = data.groupby(["card_id", "question"]).agg(
        attempts=("is_correct", "size"), correct=("is_correct", "sum")
    ).reset_index()
    hardest["accuracy"] = (hardest["correct"] / hardest["attempts"] * 100).round(1)
    hardest = hardest[hardest["attempts"] >= 3].sort_values(
        ["accuracy", "attempts"], ascending=[True, False]
    ).head(10)
    daily = data.groupby("day").size().rename("attempts").reset_index().sort_values("day")
    points = data.groupby("user_id")["points_awarded"].sum()
    bins, edges = np.histogram(points, bins=min(12, max(3, len(points))))
    distribution = [
        {"range_start": round(float(edges[index]), 1), "range_end": round(float(edges[index + 1]), 1), "learners": int(count)}
        for index, count in enumerate(bins)
    ]
    return {
        "total_attempts": len(data),
        "average_accuracy_by_subject": accuracy_by_subject.to_dict(orient="records"),
        "hardest_questions": hardest.drop(columns=["correct"]).to_dict(orient="records"),
        "most_active_days": daily.sort_values("attempts", ascending=False).head(10).to_dict(orient="records"),
        "points_distribution": distribution,
        "charts": _make_charts(
            accuracy_by_subject[["subject", "accuracy"]],
            daily,
            pd.DataFrame(),
            pd.to_numeric(data["time_taken_ms"], errors="coerce").dropna(),
            points,
            theme,
        ),
    }


def _cached(key: str):
    with _cache_lock:
        now = time.monotonic()
        expired = [
            cached_key
            for cached_key, (created_at, _) in _cache.items()
            if now - created_at >= _CACHE_TTL_SECONDS
        ]
        for cached_key in expired:
            _cache.pop(cached_key, None)
        cached = _cache.get(key)
        if cached:
            return cached[1]
    return None


def get_personal_analytics(user_id: str, theme: str = "dark") -> dict:
    key = f"me:{analytics_cache_key()}:{user_id}:{theme}"
    cached = _cached(key)
    if cached is not None:
        return cached
    attempts = _read_attempts()
    result = analyze_personal_attempts(attempts, user_id, attempts, theme)
    with _cache_lock:
        _cache[key] = (time.monotonic(), result)
    return result


def get_global_analytics(theme: str = "dark") -> dict:
    key = f"global:{analytics_cache_key()}:{theme}"
    cached = _cached(key)
    if cached is not None:
        return cached
    result = analyze_global_attempts(_read_attempts(), theme)
    with _cache_lock:
        _cache[key] = (time.monotonic(), result)
    return result
