import os
import random
import uuid
from typing import List, Literal, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.analytics import get_global_analytics, get_personal_analytics
from backend.ai_service import (
    generate_deck_overview,
    generate_ai_deck,
    generate_ai_explanation,
    generate_ai_feedback,
    generate_mindmap,
)
from backend.models import (
    AttemptCreate,
    Card,
    CardCreate,
    Deck,
    DeckCreate,
    DeckOverview,
    DeckOverviewRequest,
    DeckSessionCreate,
    ExplainRequest,
    ExplainResponse,
    FeedbackRequest,
    FeedbackResponse,
    GenerateRequest,
    Material,
    UserCreate,
)
from backend.rag import chunk_text, extract_text_from_file
from backend.seed import seed_decks
from backend.storage import (
    create_deck_session,
    create_user,
    delete_deck,
    finish_deck_session,
    get_deck_session_overview_data,
    get_leaderboard,
    get_user,
    get_user_profile,
    list_users,
    load_deck,
    load_decks,
    load_materials,
    record_attempt,
    save_deck,
    save_deck_session_overview,
    save_material,
)


seed_decks()

app = FastAPI(title="EduCards API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/decks", response_model=List[Deck])
def get_decks():
    return load_decks()


@app.post("/api/decks", response_model=Deck)
def create_deck(payload: DeckCreate):
    new_deck = Deck(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        creator=payload.creator,
        collaborators=payload.collaborators or [],
    )
    save_deck(new_deck)
    return new_deck


@app.get("/api/decks/{deck_id}", response_model=Deck)
def get_deck_by_id(deck_id: str):
    deck = load_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@app.delete("/api/decks/{deck_id}")
def remove_deck(deck_id: str):
    if delete_deck(deck_id):
        return {"message": "Deck deleted successfully", "deck_id": deck_id}
    raise HTTPException(status_code=404, detail="Deck not found")


@app.post("/api/decks/{deck_id}/cards", response_model=Card)
def add_card_to_deck(deck_id: str, card_data: CardCreate):
    deck = load_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    card = Card(deck_id=deck_id, type="mcq", **card_data.model_dump())
    deck.cards.append(card)
    save_deck(deck)
    random.shuffle(card.options)
    return card


@app.post("/api/decks/{deck_id}/mindmap")
def get_deck_mindmap(deck_id: str):
    deck = load_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return generate_mindmap(deck)


@app.get("/api/materials", response_model=List[Material])
def get_materials():
    return load_materials()


@app.post("/api/materials/upload", response_model=Material)
async def upload_material(file: UploadFile = File(...)):
    content_bytes = await file.read()
    text = extract_text_from_file(content_bytes, file.filename or "uploaded.txt")
    material = Material(
        filename=file.filename or "uploaded_syllabus.txt",
        content=text,
        chunk_count=len(chunk_text(text)),
    )
    save_material(material)
    return material


@app.post("/api/decks/generate", response_model=Deck)
def generate_deck(req: GenerateRequest):
    materials = load_materials()
    material_texts = [material.content for material in materials]
    if req.material_id:
        matched = [material.content for material in materials if material.id == req.material_id]
        if matched:
            material_texts = matched

    try:
        ai_data = generate_ai_deck(req.topic, "mcq", req.count, material_texts)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    cards = []
    for item in ai_data.get("cards", []):
        try:
            card = Card(
                deck_id="",
                id=item.get("id") or str(uuid.uuid4()),
                type="mcq",
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                options=item.get("options"),
                explanation=item.get("explanation"),
                difficulty=item.get("difficulty", "medium"),
            )
        except (ValueError, TypeError):
            continue
        cards.append(card)
    if not cards:
        raise HTTPException(
            status_code=502,
            detail="Question generation returned no valid MCQs. Check the Gemini key or try again.",
        )

    deck = Deck(
        title=ai_data.get("title", f"Study Deck: {req.topic}"),
        description=ai_data.get("description", "AI-generated multiple-choice practice deck"),
        category=ai_data.get("category", "General"),
        creator="EduCards AI",
        cards=[],
    )
    for card in cards:
        card.deck_id = deck.id
        deck.cards.append(card)
    save_deck(deck)
    return load_deck(deck.id)


@app.get("/api/users")
def get_users(username: Optional[str] = None):
    return list_users(username)


@app.post("/api/users", status_code=201)
def register_user(payload: UserCreate):
    try:
        return create_user(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/users/{user_id}")
def get_user_by_id(user_id: str):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/api/deck-sessions", status_code=201)
def start_deck_session(payload: DeckSessionCreate):
    try:
        return create_deck_session(payload.user_id, payload.deck_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/deck-sessions/{session_id}/finish")
def complete_deck_session(session_id: str, user_id: str = Query(...)):
    session = finish_deck_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Deck session not found")
    return session


@app.post("/api/decks/{deck_id}/overview", response_model=DeckOverview)
def deck_overview(deck_id: str, payload: DeckOverviewRequest):
    data = get_deck_session_overview_data(payload.session_id, deck_id)
    if not data:
        raise HTTPException(status_code=404, detail="Deck session not found")
    if not data["session"]["finished_at"]:
        raise HTTPException(status_code=409, detail="Finish the practice session before requesting its overview")

    cached = data["session"]["ai_overview"]
    if cached:
        try:
            return DeckOverview.model_validate_json(cached)
        except ValueError:
            pass

    overview = DeckOverview.model_validate(generate_deck_overview(data))
    try:
        return DeckOverview.model_validate(
            save_deck_session_overview(payload.session_id, overview)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/attempts")
def submit_attempt(payload: AttemptCreate):
    try:
        return record_attempt(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/leaderboard")
def leaderboard(
    period: Literal["all", "week"] = "all",
    limit: int = Query(default=10, ge=1, le=100),
):
    return get_leaderboard(period, limit)


@app.get("/api/users/{user_id}/profile")
def user_profile(user_id: str):
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@app.get("/api/analytics/me/{user_id}")
def personal_analytics(user_id: str):
    if not get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return get_personal_analytics(user_id)


@app.get("/api/analytics/global")
def global_analytics():
    return get_global_analytics()


@app.post("/api/ai/explain", response_model=ExplainResponse)
def explain_answer(req: ExplainRequest):
    return generate_ai_explanation(
        req.question,
        req.user_answer,
        req.correct_answer,
        req.understanding_level,
        hint_level=req.hint_level,
        learner_attempt=req.learner_attempt,
        history=req.history,
    )


@app.post("/api/ai/feedback", response_model=FeedbackResponse)
def get_ai_feedback(req: FeedbackRequest):
    return generate_ai_feedback(req.concept, req.correct_answer, req.learner_restatement)


frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
