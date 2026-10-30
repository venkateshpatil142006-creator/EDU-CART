from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_mcq_options(options: List[str]) -> List[str]:
    if len(options) != 4:
        raise ValueError("An MCQ must have exactly four options")
    if any(not option.strip() for option in options):
        raise ValueError("MCQ options cannot be empty")
    if len(set(options)) != 4:
        raise ValueError("MCQ options must be unique")
    return options


def _validate_mcq_answer(answer: str, options: List[str]) -> None:
    if answer not in options:
        raise ValueError("The answer must exactly match one of the options")


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    deck_id: str
    type: Literal["mcq"] = "mcq"
    question: str
    answer: str
    options: List[str]
    explanation: Optional[str] = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @field_validator("options")
    @classmethod
    def validate_options(cls, options: List[str]) -> List[str]:
        return _validate_mcq_options(options)

    @model_validator(mode="after")
    def validate_answer(self):
        _validate_mcq_answer(self.answer, self.options)
        return self


class Deck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: str
    creator: str
    collaborators: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cards: List[Card] = Field(default_factory=list)


class DeckCreate(BaseModel):
    title: str
    description: str
    category: str
    creator: str
    collaborators: Optional[List[str]] = None


class CardCreate(BaseModel):
    question: str
    answer: str
    options: List[str]
    explanation: Optional[str] = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @field_validator("options")
    @classmethod
    def validate_options(cls, options: List[str]) -> List[str]:
        return _validate_mcq_options(options)

    @model_validator(mode="after")
    def validate_answer(self):
        _validate_mcq_answer(self.answer, self.options)
        return self


class Material(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content: str
    chunk_count: int = 0
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=32)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username: str) -> str:
        normalized = username.strip()
        if not normalized:
            raise ValueError("Username cannot be empty")
        return normalized


class DeckSessionCreate(BaseModel):
    user_id: str
    deck_id: str


class AttemptCreate(BaseModel):
    user_id: str
    session_id: str
    deck_id: str
    card_id: str
    selected: str
    time_taken_ms: int = Field(ge=0)
    hints_used: int = Field(default=0, ge=0, le=4)


class FeedbackRequest(BaseModel):
    concept: str
    correct_answer: str
    learner_restatement: str


class FeedbackResponse(BaseModel):
    feedback: str = Field(min_length=1, max_length=10000)
    what_was_right: str = Field(min_length=1, max_length=2000)
    thing_to_refine: str = Field(min_length=1, max_length=2000)


class GenerateRequest(BaseModel):
    topic: str
    # Older clients may still send these values; generation always returns MCQs.
    card_type: Literal["flashcard", "mcq", "mixed"] = "mcq"
    count: int = Field(default=5, ge=1, le=50)
    material_id: Optional[str] = None


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ExplainRequest(BaseModel):
    question: str
    user_answer: Optional[str] = None
    correct_answer: str
    understanding_level: Literal["ELI5", "Beginner", "Intermediate", "Advanced"] = "Beginner"
    hint_level: int = Field(default=4, ge=1, le=4)
    learner_attempt: Optional[str] = None
    history: Optional[List[ConversationTurn]] = None


class DeckOverviewRequest(BaseModel):
    session_id: str


class DeckOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    strengths: List[str] = Field(max_length=10)
    weak_areas: List[str] = Field(max_length=10)
    mistake_review: List[Dict[str, str]] = Field(max_length=100)
    next_steps: List[str] = Field(max_length=10)

    @field_validator("strengths", "weak_areas", "next_steps")
    @classmethod
    def validate_nonempty_strings(cls, values: List[str]) -> List[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Overview list items cannot be empty")
        return values

    @field_validator("mistake_review")
    @classmethod
    def validate_mistake_review(cls, values: List[Dict[str, str]]) -> List[Dict[str, str]]:
        required = {
            "question",
            "your_answer",
            "correct_answer",
            "why_you_may_have_erred",
            "tip",
        }
        for item in values:
            if set(item) != required or any(not value.strip() for value in item.values()):
                raise ValueError("Each mistake review must include all non-empty fields")
        return values


class ExplainResponse(BaseModel):
    explanation: str = Field(min_length=1, max_length=10000)
    is_full_explanation: bool = False
    turn_count: int = 0
