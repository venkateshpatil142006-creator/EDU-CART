import json
import os
from typing import List, Optional
from backend.models import Deck, Material, Card

# On Vercel / Serverless, use /tmp for writable storage
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DATA_DIR = "/tmp"
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

DECKS_FILE = os.path.join(DATA_DIR, "decks.json")
MATERIALS_FILE = os.path.join(DATA_DIR, "materials.json")

def _ensure_data_dir():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass

def load_decks() -> List[Deck]:
    _ensure_data_dir()
    if not os.path.exists(DECKS_FILE):
        return []
    try:
        with open(DECKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Deck(**item) for item in data]
    except Exception:
        return []

def save_decks(decks: List[Deck]):
    _ensure_data_dir()
    try:
        with open(DECKS_FILE, "w", encoding="utf-8") as f:
            json.dump([d.model_dump() for d in decks], f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Could not save decks to {DECKS_FILE}: {e}")

def load_materials() -> List[Material]:
    _ensure_data_dir()
    if not os.path.exists(MATERIALS_FILE):
        return []
    try:
        with open(MATERIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Material(**item) for item in data]
    except Exception:
        return []

def save_materials(materials: List[Material]):
    _ensure_data_dir()
    try:
        with open(MATERIALS_FILE, "w", encoding="utf-8") as f:
            json.dump([m.model_dump() for m in materials], f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Could not save materials to {MATERIALS_FILE}: {e}")
