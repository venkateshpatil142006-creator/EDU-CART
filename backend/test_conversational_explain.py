from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_conversational_turn_limits_and_full_explanation():
    question = "What is the powerhouse of the cell?"
    user_answer = "Nucleus"
    correct_answer = "Mitochondria"

    # Turn 0: Initial explanation request (0 user replies)
    res0 = client.post("/api/ai/explain", json={
        "question": question,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "understanding_level": "Beginner",
        "history": []
    })
    assert res0.status_code == 200
    d0 = res0.json()
    assert d0["is_full_explanation"] is False
    assert d0["turn_count"] == 0
    assert "?" in d0["explanation"]  # AI asks one short question

    # Turn 1: 1 user reply in history
    history1 = [
        {"role": "assistant", "content": d0["explanation"]},
        {"role": "user", "content": "I think it has to do with making energy"}
    ]
    res1 = client.post("/api/ai/explain", json={
        "question": question,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "understanding_level": "Beginner",
        "history": history1
    })
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["is_full_explanation"] is False
    assert d1["turn_count"] == 1
    assert "?" in d1["explanation"]

    # Turn 2: 2 user replies in history
    history2 = history1 + [
        {"role": "assistant", "content": d1["explanation"]},
        {"role": "user", "content": "Maybe ATP synthesis?"}
    ]
    res2 = client.post("/api/ai/explain", json={
        "question": question,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "understanding_level": "Beginner",
        "history": history2
    })
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["is_full_explanation"] is False
    assert d2["turn_count"] == 2
    assert "?" in d2["explanation"]

    # Turn 3: 3 user replies in history -> turn limit reached! Full explanation given
    history3 = history2 + [
        {"role": "assistant", "content": d2["explanation"]},
        {"role": "user", "content": "Does it use oxygen in cellular respiration?"}
    ]
    res3 = client.post("/api/ai/explain", json={
        "question": question,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "understanding_level": "Beginner",
        "history": history3
    })
    assert res3.status_code == 200
    d3 = res3.json()
    # Acceptance criteria: no more than 3 rounds before giving full explanation
    assert d3["is_full_explanation"] is True
    assert d3["turn_count"] == 3
    assert correct_answer in d3["explanation"]

def test_frontend_has_learner_reply_elements():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="learner-reply-input"' in html
    assert 'id="btn-send-reply"' in html
    assert 'id="tutor-dialogue-container"' in html
