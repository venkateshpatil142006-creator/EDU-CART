import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.ai_service import (
    _gemini_client_for_key,
    build_deck_overview,
    generate_ai_deck,
    generate_deck_overview,
)

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
    for card in data["cards"]:
        assert card["type"] == "mcq"
        assert len(card["options"]) == 4
        assert len(set(card["options"])) == 4
        assert card["answer"] in card["options"]


@pytest.mark.parametrize("topic", ["Python", "Linux", "Networking", "DBMS", "Operating Systems"])
def test_offline_question_banks_are_valid_mcqs(monkeypatch, topic):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    generated = generate_ai_deck(topic, "flashcard", 50, [])
    assert len(generated["cards"]) == 50
    for card in generated["cards"]:
        assert card["type"] == "mcq"
        assert len(card["options"]) == 4
        assert len(set(card["options"])) == 4
        assert card["answer"] in card["options"]


def test_offline_generation_does_not_invent_generic_questions(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="No curated offline questions"):
        generate_ai_deck("ABAP", "mcq", 5, [])


def test_gemini_invalid_mcqs_are_dropped(monkeypatch):
    _gemini_client_for_key.cache_clear()
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    response = MagicMock()
    response.text = json.dumps(
        {
            "title": "Validated",
            "cards": [
                {
                    "question": "What is the central purpose of Custom topic?",
                    "answer": "A",
                    "options": ["A", "B", "C", "D"],
                },
                {
                    "question": "Invalid answer",
                    "answer": "Missing",
                    "options": ["A", "B", "C", "D"],
                },
                {
                    "question": "Valid answer",
                    "answer": "Correct",
                    "options": ["Correct", "Wrong A", "Wrong B", "Wrong C"],
                    "explanation": "The answer matches an option.",
                    "difficulty": "easy",
                },
            ],
        }
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response
    monkeypatch.setattr("google.genai.Client", lambda api_key, **kwargs: mock_client)

    generated = generate_ai_deck("Custom topic", "flashcard", 10, [])

    assert len(generated["cards"]) == 1
    assert generated["cards"][0]["question"] == "Valid answer"
    assert generated["cards"][0]["answer"] in generated["cards"][0]["options"]
    prompt = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert "multiple-choice questions" in prompt
    assert "exactly four distinct" in prompt
    assert "Avoid generic questions" in prompt


def test_gemini_authentication_error_explains_how_to_fix_key(monkeypatch):
    class GeminiAuthError(Exception):
        code = 401

    monkeypatch.setenv("GEMINI_API_KEY", "invalid-test-key")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = GeminiAuthError(
        "401 UNAUTHENTICATED: API key not valid"
    )
    monkeypatch.setattr("backend.ai_service._gemini_client_for_key", lambda _: mock_client)

    with pytest.raises(RuntimeError, match="rejected the configured API key") as error:
        generate_ai_deck("photosynthesis", "mcq", 3, [])

    assert "invalid-test-key" not in str(error.value)


def test_aq_prefixed_google_key_is_passed_to_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-api-key")
    response = MagicMock()
    response.text = json.dumps({
        "title": "Photosynthesis",
        "description": "Photosynthesis MCQs",
        "category": "Biology",
        "cards": [{
            "question": "Which molecule donates electrons to photosystem II?",
            "answer": "Water",
            "options": ["Water", "Oxygen", "Glucose", "Carbon dioxide"],
            "explanation": "Water is split during the light-dependent reactions.",
            "difficulty": "medium",
        }],
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = response
    monkeypatch.setattr("backend.ai_service._gemini_client_for_key", lambda key: mock_client)

    result = generate_ai_deck("photosynthesis", "mcq", 1, [])

    assert result["cards"][0]["answer"] == "Water"
    mock_client.models.generate_content.assert_called_once()


def test_deck_overview_without_api_key_uses_valid_deterministic_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    data = {
        "session": {"total_points": 12},
        "attempts": [
            {
                "is_correct": False,
                "selected": "pop",
                "correct_answer": "append",
                "question": "Which method adds one item to a list?",
                "subject": "Python",
                "time_taken_ms": 18000,
                "hints_used": 1,
                "explanation": "append adds a single item at the end of a list.",
            },
            {
                "is_correct": True,
                "selected": "A table",
                "correct_answer": "A table",
                "question": "What does a DataFrame represent?",
                "subject": "pandas",
                "time_taken_ms": 5000,
                "hints_used": 0,
                "explanation": "A DataFrame is a two-dimensional labeled data structure.",
            },
        ],
    }

    overview = generate_deck_overview(data)

    assert overview == build_deck_overview(data)
    assert "1 of 2" in overview["summary"]
    assert overview["mistake_review"][0]["your_answer"] == "pop"
    assert overview["mistake_review"][0]["correct_answer"] == "append"
    assert overview["weak_areas"]
