from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_workflow():
    # 1. Create deck
    res = client.post("/api/decks", json={
        "title": "Math 101",
        "description": "Basic algebra",
        "category": "Math",
        "creator": "Alice"
    })
    assert res.status_code == 200
    deck = res.json()
    deck_id = deck["id"]

    # 2. Get deck
    res = client.get(f"/api/decks/{deck_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Math 101"
