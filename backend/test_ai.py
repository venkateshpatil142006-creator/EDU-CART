from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_generate_deck_mock():
    response = client.post("/api/decks/generate", json={
        "topic": "Photosynthesis",
        "card_type": "flashcard",
        "count": 3
    })
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert len(data["cards"]) == 3
