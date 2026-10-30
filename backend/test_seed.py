import json

import pytest
from pydantic import ValidationError

from backend.models import Card
from backend.seed import SEED_DECKS, seed_decks
from backend import storage


def test_seeded_decks_have_valid_mcqs_and_are_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("EDUCART_DB_PATH", str(tmp_path / "seed.sqlite3"))
    monkeypatch.setattr(storage, "LEGACY_DECKS_FILE", tmp_path / "missing-decks.json")
    monkeypatch.setattr(storage, "LEGACY_MATERIALS_FILE", tmp_path / "missing-materials.json")

    seed_decks()
    seed_decks()
    decks = storage.load_decks()

    assert len(decks) == 10
    for seed, deck in zip(SEED_DECKS, decks):
        assert deck.title == seed["title"]
        assert 15 <= len(deck.cards) <= 20
        for card in deck.cards:
            assert card.type == "mcq"
            assert len(card.options) == 4
            assert len(set(card.options)) == 4
            assert card.answer in card.options
            assert card.difficulty in {"easy", "medium", "hard"}
            assert card.explanation and len(card.explanation) <= 250
            assert not any("all of the above" in option.lower() for option in card.options)


def test_card_rejects_invalid_option_sets():
    base = {
        "deck_id": "deck",
        "type": "mcq",
        "question": "Which is correct?",
        "answer": "A",
    }
    for options in (["A", "B", "C"], ["A", "B", "B", "D"], ["A", "B", "C", "D"]):
        payload = {**base, "options": options}
        if options == ["A", "B", "C", "D"]:
            payload["answer"] = "a"
        with pytest.raises(ValidationError):
            Card(**payload)


def test_legacy_json_import_drops_flashcards_and_runs_once(tmp_path, monkeypatch):
    legacy_file = tmp_path / "decks.json"
    legacy_file.write_text(
        json.dumps(
            [
                {
                    "id": "legacy-deck",
                    "title": "Legacy",
                    "description": "Imported",
                    "category": "Test",
                    "creator": "Tester",
                    "cards": [
                        {
                            "id": "old-flashcard",
                            "type": "flashcard",
                            "question": "Old prompt",
                            "answer": "Old answer",
                        },
                        {
                            "id": "valid-mcq",
                            "type": "mcq",
                            "question": "Which option is valid?",
                            "answer": "Correct",
                            "options": ["Correct", "Wrong 1", "Wrong 2", "Wrong 3"],
                            "explanation": "It is the correct choice.",
                        },
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EDUCART_DB_PATH", str(tmp_path / "migration.sqlite3"))
    monkeypatch.setattr(storage, "LEGACY_DECKS_FILE", legacy_file)
    monkeypatch.setattr(storage, "LEGACY_MATERIALS_FILE", tmp_path / "missing-materials.json")

    first_read = storage.load_decks()
    legacy_file.write_text("[]", encoding="utf-8")
    second_read = storage.load_decks()

    assert len(first_read) == 1
    assert [card.id for card in first_read[0].cards] == ["valid-mcq"]
    assert len(second_read) == 1
    assert [card.id for card in second_read[0].cards] == ["valid-mcq"]
