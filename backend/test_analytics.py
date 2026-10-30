import pandas as pd

from backend.analytics import analyze_global_attempts, analyze_personal_attempts


def _attempts():
    return pd.DataFrame(
        [
            {
                "user_id": "learner-a",
                "deck_id": "deck-a",
                "deck_title": "Python Basics",
                "card_id": "card-weak",
                "question": "Which method adds one item to a list?",
                "subject": "Python",
                "difficulty": "easy",
                "is_correct": 0,
                "time_taken_ms": 12000,
                "hints_used": 1,
                "points_awarded": 0,
                "created_at": "2026-10-28T10:00:00+00:00",
            },
            {
                "user_id": "learner-a",
                "deck_id": "deck-a",
                "deck_title": "Python Basics",
                "card_id": "card-weak",
                "question": "Which method adds one item to a list?",
                "subject": "Python",
                "difficulty": "easy",
                "is_correct": 0,
                "time_taken_ms": 18000,
                "hints_used": 0,
                "points_awarded": 0,
                "created_at": "2026-10-29T10:00:00+00:00",
            },
            {
                "user_id": "learner-a",
                "deck_id": "deck-a",
                "deck_title": "Python Basics",
                "card_id": "card-weak",
                "question": "Which method adds one item to a list?",
                "subject": "Python",
                "difficulty": "easy",
                "is_correct": 1,
                "time_taken_ms": 5000,
                "hints_used": 2,
                "points_awarded": 11,
                "created_at": "2026-10-30T10:00:00+00:00",
            },
            {
                "user_id": "learner-b",
                "deck_id": "deck-b",
                "deck_title": "SQL",
                "card_id": "card-sql",
                "question": "Which clause filters grouped rows?",
                "subject": "DBMS",
                "difficulty": "medium",
                "is_correct": 1,
                "time_taken_ms": 3000,
                "hints_used": 0,
                "points_awarded": 15,
                "created_at": "2026-10-30T11:00:00+00:00",
            },
        ]
    )


def test_personal_analytics_aggregates_and_creates_png_charts():
    attempts = _attempts()

    result = analyze_personal_attempts(attempts, "learner-a", attempts)

    assert result["total_attempts"] == 3
    assert result["accuracy"] == 33.3
    assert result["rank"] == 2
    assert result["hint_usage_rate"] == 66.7
    assert result["accuracy_by_deck"][0]["accuracy"] == 33.3
    assert result["response_time_ms_percentiles"] == {"p50": 12000.0, "p90": 16800.0, "p95": 17400.0}
    assert len(result["weak_cards"]) == 1
    assert result["daily_activity"]
    assert set(result["charts"]) == {
        "accuracy_by_subject",
        "learning_curve",
        "daily_activity",
        "response_time_distribution",
    }
    assert all(value.startswith("data:image/png;base64,") for value in result["charts"].values())


def test_global_analytics_returns_only_aggregates():
    result = analyze_global_attempts(_attempts())

    assert result["total_attempts"] == 4
    assert result["average_accuracy_by_subject"]
    assert result["hardest_questions"][0]["question"] == "Which method adds one item to a list?"
    assert result["most_active_days"][0]["attempts"] == 2
    assert result["points_distribution"]
    assert all("selected" not in item and "user_id" not in item for item in result["hardest_questions"])
    assert "points_distribution" in result["charts"]


def test_empty_personal_analytics_has_chart_output_and_no_stats():
    result = analyze_personal_attempts(_attempts(), "new-user", _attempts())

    assert result["total_attempts"] == 0
    assert result["rank"] is None
    assert result["response_time_ms_percentiles"]["p50"] is None
    assert all(value.startswith("data:image/png;base64,") for value in result["charts"].values())
