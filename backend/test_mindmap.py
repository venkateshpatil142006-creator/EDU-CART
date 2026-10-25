from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_mindmap_missing_deck():
    response = client.post("/api/decks/non-existent-id/mindmap")
    assert response.status_code == 404
    assert response.json()["detail"] == "Deck not found"

def test_mindmap_fallback_no_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    res = client.post("/api/decks", json={
        "title": "Data Structures",
        "description": "Core CS concepts",
        "category": "Computer Science",
        "creator": "Tester"
    })
    assert res.status_code == 200
    deck_id = res.json()["id"]

    card_res = client.post(f"/api/decks/{deck_id}/cards", json={
        "type": "flashcard",
        "question": "What is a Binary Search Tree?",
        "answer": "A node-based binary tree data structure."
    })
    assert card_res.status_code == 200

    response = client.post(f"/api/decks/{deck_id}/mindmap")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "Data Structures"
    assert "nodes" in data and len(data["nodes"]) >= 1
    assert data["nodes"][0]["label"] == "What is a Binary Search Tree?"
    assert "edges" in data and len(data["edges"]) >= 1
    assert data["edges"][0]["from"] == "root"
    assert data["edges"][0]["to"] == data["nodes"][0]["id"]

def test_mindmap_groq_mocked(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")

    mock_json = '{"root": "Operating Systems", "nodes": [{"id": "n1", "label": "Processes"}, {"id": "n2", "label": "Threads"}], "edges": [{"from": "n1", "to": "n2"}]}'
    mock_choice = MagicMock()
    mock_choice.message.content = mock_json
    mock_response = MagicMock(choices=[mock_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    monkeypatch.setattr("groq.Groq", lambda api_key: mock_client)

    res = client.post("/api/decks", json={
        "title": "Operating Systems",
        "description": "OS deck",
        "category": "CS",
        "creator": "Tester"
    })
    assert res.status_code == 200
    deck_id = res.json()["id"]

    response = client.post(f"/api/decks/{deck_id}/mindmap")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "Operating Systems"
    assert len(data["nodes"]) == 2
    assert data["nodes"][0]["id"] == "n1"
    assert data["nodes"][1]["id"] == "n2"
    assert len(data["edges"]) == 1
    assert data["edges"][0]["from"] == "n1"
    assert data["edges"][0]["to"] == "n2"

def test_mindmap_groq_failure_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Groq rate limit exceeded")
    monkeypatch.setattr("groq.Groq", lambda api_key: mock_client)

    res = client.post("/api/decks", json={
        "title": "Network Protocols",
        "description": "Networking basics",
        "category": "Networks",
        "creator": "Tester"
    })
    assert res.status_code == 200
    deck_id = res.json()["id"]

    response = client.post(f"/api/decks/{deck_id}/mindmap")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "Network Protocols"
    assert "nodes" in data and "edges" in data
