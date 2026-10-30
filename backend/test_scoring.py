import uuid
import sqlite3

from fastapi.testclient import TestClient

from backend.main import app
from backend import storage
from backend.models import Card, Deck


client = TestClient(app)


def test_options_are_shuffled_when_deck_is_served(monkeypatch):
    monkeypatch.setattr("backend.storage.random.shuffle", lambda options: options.reverse())
    deck = client.post(
        "/api/decks",
        json={
            "title": f"Shuffle deck {uuid.uuid4().hex[:8]}",
            "description": "Option order test",
            "category": "Testing",
            "creator": "Test",
        },
    ).json()
    options = ["Correct", "Wrong A", "Wrong B", "Wrong C"]
    card = client.post(
        f"/api/decks/{deck['id']}/cards",
        json={
            "question": "Which option is correct?",
            "answer": "Correct",
            "options": options,
        },
    ).json()

    served_card = client.get(f"/api/decks/{deck['id']}").json()["cards"][0]

    assert card["options"] == list(reversed(options))
    assert served_card["options"] == list(reversed(options))
    assert served_card["options"][0] != served_card["answer"]


def test_attempt_scoring_profile_and_leaderboard():
    username = f"learner-{uuid.uuid4().hex[:8]}"
    user_response = client.post("/api/users", json={"username": username})
    assert user_response.status_code == 201
    user = user_response.json()
    assert client.get(f"/api/users/{user['id']}").json()["username"] == username
    assert client.post("/api/users", json={"username": username.upper()}).status_code == 409

    deck_response = client.post(
        "/api/decks",
        json={
            "title": f"Scoring deck {uuid.uuid4().hex[:8]}",
            "description": "Scoring integration test",
            "category": "Testing",
            "creator": "Test",
        },
    )
    deck = deck_response.json()
    cards = []
    for index in range(5):
        response = client.post(
            f"/api/decks/{deck['id']}/cards",
            json={
                "question": f"Question {index}",
                "answer": f"Correct {index}",
                "options": [
                    f"Correct {index}",
                    f"Wrong {index} A",
                    f"Wrong {index} B",
                    f"Wrong {index} C",
                ],
                "explanation": "The selected answer matches the question.",
                "difficulty": "easy",
            },
        )
        assert response.status_code == 200
        cards.append(response.json())

    session_response = client.post(
        "/api/deck-sessions",
        json={"user_id": user["id"], "deck_id": deck["id"]},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    for index, card in enumerate(cards):
        result = client.post(
            "/api/attempts",
            json={
                "user_id": user["id"],
                "session_id": session_id,
                "deck_id": deck["id"],
                "card_id": card["id"],
                "selected": card["answer"],
                "time_taken_ms": 20000 if index == 1 else 5000,
                "hints_used": 2 if index == 0 else 0,
            },
        )
        assert result.status_code == 200
        attempt = result.json()
        assert attempt["is_correct"] is True
        assert attempt["current_streak"] == index + 1
        if index == 0:
            assert attempt["points_awarded"] == 11
        if index == 1:
            assert attempt["points_awarded"] == 10
        if index == 4:
            assert attempt["points_awarded"] == 22.5

    repeat = client.post(
        "/api/attempts",
        json={
            "user_id": user["id"],
            "session_id": session_id,
            "deck_id": deck["id"],
            "card_id": cards[0]["id"],
            "selected": cards[0]["answer"],
            "time_taken_ms": 1000,
            "hints_used": 0,
        },
    ).json()
    assert repeat["points_awarded"] == 1
    assert repeat["current_streak"] == 6

    wrong_option = next(option for option in cards[1]["options"] if option != cards[1]["answer"])
    wrong = client.post(
        "/api/attempts",
        json={
            "user_id": user["id"],
            "session_id": session_id,
            "deck_id": deck["id"],
            "card_id": cards[1]["id"],
            "selected": wrong_option,
            "time_taken_ms": 2000,
            "hints_used": 0,
        },
    ).json()
    assert wrong["is_correct"] is False
    assert wrong["points_awarded"] == 0
    assert wrong["current_streak"] == 0

    finished = client.post(
        f"/api/deck-sessions/{session_id}/finish",
        params={"user_id": user["id"]},
    )
    assert finished.status_code == 200
    assert finished.json()["total_points"] == 74.5

    profile = client.get(f"/api/users/{user['id']}/profile")
    assert profile.status_code == 200
    assert profile.json()["total_points"] == 74.5
    assert profile.json()["best_streak"] == 6
    assert profile.json()["current_streak"] == 0
    assert profile.json()["recent_sessions"][0]["finished_at"]

    leaderboard = client.get("/api/leaderboard?period=all&limit=10")
    assert leaderboard.status_code == 200
    entry = next(row for row in leaderboard.json() if row["username"] == username)
    assert entry["total_points"] == 74.5
    assert entry["decks_completed"] == 1
    assert entry["accuracy"] == 85.7
    assert entry["rank"] >= 1
    assert client.get("/api/leaderboard?period=week&limit=10").status_code == 200


def test_leaderboard_orders_equal_points_by_accuracy_then_earliest_finish(tmp_path, monkeypatch):
    database = tmp_path / "leaderboard.sqlite3"
    monkeypatch.setenv("EDUCART_DB_PATH", str(database))
    monkeypatch.setattr(storage, "LEGACY_DECKS_FILE", tmp_path / "missing-decks.json")
    monkeypatch.setattr(storage, "LEGACY_MATERIALS_FILE", tmp_path / "missing-materials.json")
    users = [storage.create_user(f"rank-{uuid.uuid4().hex[:8]}") for _ in range(3)]
    cards = []
    deck = Deck(
        title=f"Ranking {uuid.uuid4().hex[:8]}",
        description="Ranking tie breaker fixture",
        category="Testing",
        creator="Test",
        cards=[],
    )
    for index in range(3):
        card = Card(
            deck_id=deck.id,
            question=f"Question {index}",
            answer=f"Correct {index}",
            options=[f"Correct {index}", f"Wrong {index} A", f"Wrong {index} B", f"Wrong {index} C"],
        )
        deck.cards.append(card)
        cards.append(card)
    storage.save_deck(deck)

    sessions = []
    for user in users:
        sessions.append(storage.create_deck_session(user["id"], deck.id))

    for index, (user, session) in enumerate(zip(users, sessions)):
        storage.record_attempt(
            {
                "user_id": user["id"],
                "session_id": session["id"],
                "deck_id": deck.id,
                "card_id": cards[index].id,
                "selected": cards[index].answer,
                "time_taken_ms": 20000,
                "hints_used": 0,
            }
        )
        if index == 2:
            storage.record_attempt(
                {
                    "user_id": user["id"],
                    "session_id": session["id"],
                    "deck_id": deck.id,
                    "card_id": cards[index].id,
                    "selected": "Wrong 2 A",
                    "time_taken_ms": 20000,
                    "hints_used": 0,
                }
            )
        storage.finish_deck_session(session["id"], user["id"])

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE deck_sessions SET finished_at = ? WHERE id = ?",
            ("2026-10-29T10:00:00+00:00", sessions[0]["id"]),
        )
        connection.execute(
            "UPDATE deck_sessions SET finished_at = ? WHERE id = ?",
            ("2026-10-28T10:00:00+00:00", sessions[1]["id"]),
        )
        connection.commit()

    leaderboard = storage.get_leaderboard(limit=10)

    assert [entry["user_id"] for entry in leaderboard[:3]] == [
        users[1]["id"],
        users[0]["id"],
        users[2]["id"],
    ]
