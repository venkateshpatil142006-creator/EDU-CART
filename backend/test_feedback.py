import re
from fastapi.testclient import TestClient
from backend.main import app
from backend.ai_service import generate_ai_feedback

client = TestClient(app)

def count_sentences(text: str) -> int:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    return len(sentences)

def test_api_ai_feedback_endpoint_success():
    payload = {
        "concept": "Mitochondria cellular respiration",
        "correct_answer": "Generates ATP through aerobic respiration",
        "learner_restatement": "It is where the cell creates energy using oxygen."
    }
    response = client.post("/api/ai/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "feedback" in data
    assert "what_was_right" in data
    assert "thing_to_refine" in data
    
    feedback = data["feedback"]
    assert count_sentences(feedback) <= 3, f"Feedback has more than 3 sentences: {feedback}"
    assert len(data["what_was_right"]) > 0
    assert len(data["thing_to_refine"]) > 0

def test_generate_ai_feedback_mock_fallback():
    result = generate_ai_feedback(
        concept="Photosynthesis",
        correct_answer="Converts sunlight into glucose",
        learner_restatement="Plants turn sun into food"
    )
    assert "feedback" in result
    assert "what_was_right" in result
    assert "thing_to_refine" in result
    
    assert count_sentences(result["feedback"]) <= 3
    assert result["what_was_right"].lower().startswith("you")

def test_api_ai_feedback_missing_fields_validation():
    res1 = client.post("/api/ai/feedback", json={
        "concept": "Gravity",
        "correct_answer": "Mass attracts mass"
    })
    assert res1.status_code == 422

    res2 = client.post("/api/ai/feedback", json={})
    assert res2.status_code == 422

def test_frontend_has_explain_it_back_and_skip_option():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="explain-it-back-container"' in html
    assert 'id="restatement-input-section"' in html
    assert 'id="learner-restatement"' in html
    assert 'id="btn-submit-restatement"' in html
    assert 'id="btn-skip-restatement"' in html
    assert "Skip this step" in html
    assert 'id="restatement-skipped-msg"' in html
    assert 'id="restatement-feedback-box"' in html
