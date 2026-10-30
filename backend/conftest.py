import os

import pytest

os.environ["GEMINI_API_KEY"] = ""


@pytest.fixture(autouse=True)
def isolate_application_database(tmp_path, monkeypatch):
    from backend import storage
    from backend.seed import seed_decks

    monkeypatch.setenv("EDUCART_DB_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setattr(storage, "LEGACY_DECKS_FILE", tmp_path / "missing-decks.json")
    monkeypatch.setattr(storage, "LEGACY_MATERIALS_FILE", tmp_path / "missing-materials.json")
    seed_decks()
