import json
import uuid

from fastapi.testclient import TestClient
from backend import storage
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_material_upload_persists_to_sqlite():
    response = client.post(
        "/api/materials/upload",
        files={"file": ("lecture-notes.txt", b"SQLite material persistence test.", "text/plain")},
    )
    assert response.status_code == 200
    material = response.json()
    assert material["filename"] == "lecture-notes.txt"
    assert material["content"] == "SQLite material persistence test."
    assert any(item["id"] == material["id"] for item in client.get("/api/materials").json())


def test_frontend_has_mcq_and_progress_views_without_flashcards():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="mcq-options"' in html
    assert 'id="view-leaderboard"' in html
    assert 'id="view-profile"' in html
    assert 'id="flashcard-container"' not in html
    assert 'id="gen-type"' not in html


def test_deck_overview_is_fallback_validated_and_persisted(tmp_path, monkeypatch):
    database = tmp_path / "overview.sqlite3"
    monkeypatch.setenv("EDUCART_DB_PATH", str(database))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(storage, "LEGACY_DECKS_FILE", tmp_path / "missing-decks.json")
    monkeypatch.setattr(storage, "LEGACY_MATERIALS_FILE", tmp_path / "missing-materials.json")
    user = client.post("/api/users", json={"username": f"overview-{uuid.uuid4().hex[:8]}"}).json()
    deck = client.post(
        "/api/decks",
        json={
            "title": f"Overview {uuid.uuid4().hex[:8]}",
            "description": "Overview fixture",
            "category": "Testing",
            "creator": "Test",
        },
    ).json()
    card = client.post(
        f"/api/decks/{deck['id']}/cards",
        json={
            "question": "Which method appends one list item?",
            "answer": "append",
            "options": ["append", "pop", "sort", "clear"],
            "explanation": "append adds one item at the end of a list.",
        },
    ).json()
    session = client.post(
        "/api/deck-sessions",
        json={"user_id": user["id"], "deck_id": deck["id"]},
    ).json()
    attempt = client.post(
        "/api/attempts",
        json={
            "user_id": user["id"],
            "session_id": session["id"],
            "deck_id": deck["id"],
            "card_id": card["id"],
            "selected": "pop",
            "time_taken_ms": 18000,
            "hints_used": 1,
        },
    )
    assert attempt.status_code == 200
    assert client.post(
        f"/api/deck-sessions/{session['id']}/finish",
        params={"user_id": user["id"]},
    ).status_code == 200

    response = client.post(
        f"/api/decks/{deck['id']}/overview",
        json={"session_id": session["id"]},
    )
    second_response = client.post(
        f"/api/decks/{deck['id']}/overview",
        json={"session_id": session["id"]},
    )

    assert response.status_code == 200
    assert response.json() == second_response.json()
    assert response.json()["mistake_review"][0]["your_answer"] == "pop"
    cached = storage.get_deck_session_overview_data(session["id"], deck["id"])["session"]["ai_overview"]
    assert json.loads(cached) == response.json()

    personal = client.get(f"/api/analytics/me/{user['id']}")
    global_view = client.get("/api/analytics/global")
    assert personal.status_code == 200
    assert personal.json()["total_attempts"] == 1
    assert personal.json()["accuracy"] == 0
    assert personal.json()["charts"]["daily_activity"].startswith("data:image/png;base64,")
    assert global_view.status_code == 200
    assert global_view.json()["total_attempts"] == 1
    assert "selected" not in json.dumps(global_view.json())
