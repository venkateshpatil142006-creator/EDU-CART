import json
import os
import random
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError

from backend.models import Card, Deck, DeckOverview, Material


DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LEGACY_DECKS_FILE = DEFAULT_DATA_DIR / "decks.json"
LEGACY_MATERIALS_FILE = DEFAULT_DATA_DIR / "materials.json"


def database_path() -> str:
    configured = os.environ.get("EDUCART_DB_PATH")
    if configured:
        return configured
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/educards.sqlite3"
    return str(DEFAULT_DATA_DIR / "educards.sqlite3")


def _connect() -> sqlite3.Connection:
    path = database_path()
    if path != ":memory:":
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    _create_schema(connection)
    _import_legacy_decks(connection)
    _import_legacy_materials(connection)
    return connection


@contextmanager
def _connection():
    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            creator TEXT NOT NULL,
            collaborators TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            deck_id TEXT NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
            type TEXT NOT NULL DEFAULT 'mcq' CHECK (type = 'mcq'),
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            options TEXT NOT NULL,
            explanation TEXT,
            difficulty TEXT NOT NULL DEFAULT 'medium'
                CHECK (difficulty IN ('easy', 'medium', 'hard'))
        );
        CREATE INDEX IF NOT EXISTS cards_deck_id_idx ON cards(deck_id);
        CREATE TABLE IF NOT EXISTS deck_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            deck_id TEXT NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            score REAL NOT NULL DEFAULT 0,
            total_points REAL NOT NULL DEFAULT 0,
            ai_overview TEXT
        );
        CREATE INDEX IF NOT EXISTS sessions_user_idx
            ON deck_sessions(user_id, started_at);
        CREATE TABLE IF NOT EXISTS attempts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            deck_id TEXT NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
            card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            session_id TEXT NOT NULL REFERENCES deck_sessions(id) ON DELETE CASCADE,
            selected TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            time_taken_ms INTEGER NOT NULL,
            hints_used INTEGER NOT NULL DEFAULT 0,
            points_awarded REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS attempts_user_created_idx
            ON attempts(user_id, created_at);
        CREATE INDEX IF NOT EXISTS attempts_session_idx
                ON attempts(session_id, created_at);
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            content TEXT NOT NULL,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL
        );
        """
    )


def _serialize_deck(connection: sqlite3.Connection, deck: Deck) -> None:
    connection.execute(
        """
        INSERT INTO decks (id, title, description, category, creator, collaborators, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title, description=excluded.description,
            category=excluded.category, creator=excluded.creator, collaborators=excluded.collaborators,
            updated_at=excluded.updated_at
        """,
        (
            deck.id,
            deck.title,
            deck.description,
            deck.category,
            deck.creator,
            json.dumps(deck.collaborators),
            deck.created_at,
            deck.updated_at,
        ),
    )
    existing_ids = {
        row["id"]
        for row in connection.execute("SELECT id FROM cards WHERE deck_id = ?", (deck.id,))
    }
    new_ids = {card.id for card in deck.cards}
    for removed_id in existing_ids - new_ids:
        connection.execute("DELETE FROM cards WHERE id = ?", (removed_id,))
    for card in deck.cards:
        connection.execute(
            """
            INSERT INTO cards (id, deck_id, type, question, answer, options, explanation, difficulty)
            VALUES (?, ?, 'mcq', ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET deck_id=excluded.deck_id, question=excluded.question,
                answer=excluded.answer, options=excluded.options, explanation=excluded.explanation,
                difficulty=excluded.difficulty
            """,
            (
                card.id,
                deck.id,
                card.question,
                card.answer,
                json.dumps(card.options),
                card.explanation,
                card.difficulty,
            ),
        )


def _import_legacy_decks(connection: sqlite3.Connection) -> None:
    marker = connection.execute(
        "SELECT value FROM app_meta WHERE key = 'legacy_decks_imported'"
    ).fetchone()
    if marker or not LEGACY_DECKS_FILE.exists():
        return

    raw_decks = json.loads(LEGACY_DECKS_FILE.read_text(encoding="utf-8"))
    connection.execute("BEGIN IMMEDIATE")
    try:
        marker = connection.execute(
            "SELECT value FROM app_meta WHERE key = 'legacy_decks_imported'"
        ).fetchone()
        if marker:
            connection.commit()
            return
        for raw_deck in raw_decks:
            deck_id = str(raw_deck.get("id") or uuid.uuid4())
            valid_cards = []
            for raw_card in raw_deck.get("cards", []):
                if not isinstance(raw_card, dict) or raw_card.get("type") != "mcq":
                    continue
                try:
                    valid_cards.append(
                        Card(
                            id=str(raw_card.get("id") or uuid.uuid4()),
                            deck_id=deck_id,
                            type="mcq",
                            question=raw_card["question"],
                            answer=raw_card["answer"],
                            options=raw_card["options"],
                            explanation=raw_card.get("explanation"),
                            difficulty=raw_card.get("difficulty", "medium"),
                        )
                    )
                except (KeyError, ValidationError, TypeError):
                    continue
            deck = Deck(
                id=deck_id,
                title=raw_deck.get("title", "Imported study deck"),
                description=raw_deck.get("description", ""),
                category=raw_deck.get("category", "General"),
                creator=raw_deck.get("creator", "EduCards"),
                collaborators=raw_deck.get("collaborators", []),
                created_at=raw_deck.get("created_at") or datetime.now(timezone.utc).isoformat(),
                updated_at=raw_deck.get("updated_at") or datetime.now(timezone.utc).isoformat(),
                cards=valid_cards,
            )
            if not valid_cards:
                continue
            _serialize_deck(connection, deck)
        connection.execute(
            "INSERT INTO app_meta (key, value) VALUES ('legacy_decks_imported', '1')"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _import_legacy_materials(connection: sqlite3.Connection) -> None:
    marker = connection.execute(
        "SELECT value FROM app_meta WHERE key = 'legacy_materials_imported'"
    ).fetchone()
    if marker or not LEGACY_MATERIALS_FILE.exists():
        return
    raw_materials = json.loads(LEGACY_MATERIALS_FILE.read_text(encoding="utf-8"))
    connection.execute("BEGIN IMMEDIATE")
    try:
        marker = connection.execute(
            "SELECT value FROM app_meta WHERE key = 'legacy_materials_imported'"
        ).fetchone()
        if marker:
            connection.commit()
            return
        for raw in raw_materials:
            material = Material(**raw)
            connection.execute(
                """
                INSERT OR IGNORE INTO materials (id, filename, content, chunk_count, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (material.id, material.filename, material.content, material.chunk_count, material.uploaded_at),
            )
        connection.execute(
            "INSERT INTO app_meta (key, value) VALUES ('legacy_materials_imported', '1')"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _deck_from_row(connection: sqlite3.Connection, row: sqlite3.Row, shuffle: bool = True) -> Deck:
    cards = []
    for card_row in connection.execute(
        "SELECT * FROM cards WHERE deck_id = ? ORDER BY rowid", (row["id"],)
    ):
        options = json.loads(card_row["options"])
        if shuffle:
            random.shuffle(options)
        cards.append(
            Card(
                id=card_row["id"],
                deck_id=card_row["deck_id"],
                type=card_row["type"],
                question=card_row["question"],
                answer=card_row["answer"],
                options=options,
                explanation=card_row["explanation"],
                difficulty=card_row["difficulty"],
            )
        )
    return Deck(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        creator=row["creator"],
        collaborators=json.loads(row["collaborators"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        cards=cards,
    )


def load_decks() -> List[Deck]:
    with _connection() as connection:
        rows = connection.execute("SELECT * FROM decks ORDER BY created_at, rowid").fetchall()
        return [_deck_from_row(connection, row) for row in rows]


def load_deck(deck_id: str) -> Optional[Deck]:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
        return _deck_from_row(connection, row) if row else None


def save_deck(deck: Deck) -> None:
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _serialize_deck(connection, deck)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def save_decks(decks: List[Deck]) -> None:
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            deck_ids = {deck.id for deck in decks}
            existing_ids = {
                row["id"] for row in connection.execute("SELECT id FROM decks")
            }
            for removed_id in existing_ids - deck_ids:
                connection.execute("DELETE FROM decks WHERE id = ?", (removed_id,))
            for deck in decks:
                _serialize_deck(connection, deck)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def save_seed_deck(deck: Deck) -> None:
    with _connection() as connection:
        existing = connection.execute(
            "SELECT id FROM decks WHERE title = ? COLLATE NOCASE AND category = ? COLLATE NOCASE",
            (deck.title, deck.category),
        ).fetchone()
        if existing:
            deck.id = existing["id"]
            for card in deck.cards:
                card.deck_id = deck.id
        connection.execute("BEGIN IMMEDIATE")
        try:
            _serialize_deck(connection, deck)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def delete_deck(deck_id: str) -> bool:
    with _connection() as connection:
        cursor = connection.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
        return cursor.rowcount > 0


def save_material(material: Material) -> None:
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO materials (id, filename, content, chunk_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (material.id, material.filename, material.content, material.chunk_count, material.uploaded_at),
        )


def load_materials() -> List[Material]:
    with _connection() as connection:
        return [
            Material(**dict(row))
            for row in connection.execute("SELECT * FROM materials ORDER BY uploaded_at, rowid")
        ]


def save_materials(materials: List[Material]) -> None:
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM materials")
            for material in materials:
                connection.execute(
                    """
                    INSERT INTO materials (id, filename, content, chunk_count, uploaded_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (material.id, material.filename, material.content, material.chunk_count, material.uploaded_at),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def create_user(username: str) -> Dict[str, str]:
    user = {"id": str(uuid.uuid4()), "username": username, "created_at": datetime.now(timezone.utc).isoformat()}
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        if existing:
            connection.rollback()
            raise ValueError("That username is already taken")
        try:
            connection.execute(
                "INSERT INTO users (id, username, created_at) VALUES (?, ?, ?)",
                (user["id"], user["username"], user["created_at"]),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise ValueError("That username is already taken") from exc
    return user


def list_users(username: Optional[str] = None) -> List[Dict[str, str]]:
    with _connection() as connection:
        if username:
            rows = connection.execute(
                "SELECT id, username, created_at FROM users WHERE username = ? COLLATE NOCASE",
                (username,),
            )
        else:
            rows = connection.execute(
                "SELECT id, username, created_at FROM users ORDER BY created_at, username"
            )
        return [dict(row) for row in rows]


def get_user(user_id: str) -> Optional[Dict[str, str]]:
    with _connection() as connection:
        row = connection.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def create_deck_session(user_id: str, deck_id: str) -> Dict:
    session = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "deck_id": deck_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "score": 0,
        "total_points": 0,
        "ai_overview": None,
    }
    with _connection() as connection:
        try:
            connection.execute(
                """
                INSERT INTO deck_sessions (id, user_id, deck_id, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (session["id"], user_id, deck_id, session["started_at"]),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("User or deck not found") from exc
    return session


def finish_deck_session(session_id: str, user_id: str) -> Optional[Dict]:
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM deck_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not row:
            connection.rollback()
            return None
        stats = connection.execute(
            """
            SELECT COUNT(*) AS attempts, SUM(is_correct) AS correct, SUM(points_awarded) AS points
            FROM attempts WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        total_attempts = stats["attempts"] or 0
        correct = stats["correct"] or 0
        score = round((correct / total_attempts) * 100, 1) if total_attempts else 0
        points = stats["points"] or 0
        finished_at = row["finished_at"] or datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            UPDATE deck_sessions
            SET finished_at = ?, score = ?, total_points = ?
            WHERE id = ?
            """,
            (finished_at, score, points, session_id),
        )
        connection.commit()
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "deck_id": row["deck_id"],
            "started_at": row["started_at"],
            "finished_at": finished_at,
            "score": score,
            "total_points": points,
            "ai_overview": row["ai_overview"],
        }


def get_deck_session_overview_data(session_id: str, deck_id: str) -> Optional[Dict]:
    with _connection() as connection:
        session = connection.execute(
            """
            SELECT s.id, s.user_id, s.deck_id, s.started_at, s.finished_at,
                   s.total_points, s.ai_overview, d.category AS subject
            FROM deck_sessions s JOIN decks d ON d.id = s.deck_id
            WHERE s.id = ? AND s.deck_id = ?
            """,
            (session_id, deck_id),
        ).fetchone()
        if not session:
            return None
        attempts = connection.execute(
            """
            SELECT a.is_correct, a.selected, a.time_taken_ms, a.hints_used, a.created_at,
                   c.question, c.answer AS correct_answer, c.explanation,
                   d.category AS subject
            FROM attempts a
            JOIN cards c ON c.id = a.card_id
            JOIN decks d ON d.id = a.deck_id
            WHERE a.session_id = ? ORDER BY a.rowid
            """,
            (session_id,),
        ).fetchall()
        return {
            "session": dict(session),
            "attempts": [dict(row) for row in attempts],
        }


def save_deck_session_overview(session_id: str, overview: DeckOverview) -> Dict:
    overview_data = overview.model_dump()
    serialized = json.dumps(overview_data, ensure_ascii=False)
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT ai_overview FROM deck_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            connection.rollback()
            raise ValueError("Deck session not found")
        if row["ai_overview"] is not None:
            try:
                cached = DeckOverview.model_validate_json(row["ai_overview"])
                connection.commit()
                return cached.model_dump()
            except ValueError:
                pass
        connection.execute(
            "UPDATE deck_sessions SET ai_overview = ? WHERE id = ?",
            (serialized, session_id),
        )
        connection.commit()
        return overview_data


def record_attempt(payload: Dict) -> Dict:
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    today_start = datetime.combine(now.date(), time.min, timezone.utc).isoformat()
    attempt_id = str(uuid.uuid4())
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        session = connection.execute(
            """
            SELECT id FROM deck_sessions
            WHERE id = ? AND user_id = ? AND deck_id = ? AND finished_at IS NULL
            """,
            (payload["session_id"], payload["user_id"], payload["deck_id"]),
        ).fetchone()
        card = connection.execute(
            "SELECT answer FROM cards WHERE id = ? AND deck_id = ?",
            (payload["card_id"], payload["deck_id"]),
        ).fetchone()
        if not session or not card:
            connection.rollback()
            raise ValueError("Session or card not found for this user and deck")

        is_correct = payload["selected"] == card["answer"]
        prior_correct_today = connection.execute(
            """
            SELECT 1 FROM attempts
            WHERE user_id = ? AND card_id = ? AND is_correct = 1 AND created_at >= ?
            LIMIT 1
            """,
            (payload["user_id"], payload["card_id"], today_start),
        ).fetchone()
        streak_rows = connection.execute(
            "SELECT is_correct FROM attempts WHERE session_id = ? ORDER BY rowid DESC",
            (payload["session_id"],),
        ).fetchall()
        streak = 0
        for previous in streak_rows:
            if not previous["is_correct"]:
                break
            streak += 1
        current_streak = streak + 1 if is_correct else 0

        points = 0
        if is_correct:
            if prior_correct_today:
                points = 1
            else:
                elapsed = payload["time_taken_ms"]
                speed_bonus = 5 if elapsed <= 5000 else 0 if elapsed >= 20000 else 5 * (20000 - elapsed) / 15000
                unmultiplied = max(0, 10 + speed_bonus - 2 * payload["hints_used"])
                multiplier = 1.5 if current_streak >= 5 else 1
                points = round(unmultiplied * multiplier, 2)

        connection.execute(
            """
            INSERT INTO attempts
                (id, user_id, deck_id, card_id, session_id, selected, is_correct,
                 time_taken_ms, hints_used, points_awarded, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                payload["user_id"],
                payload["deck_id"],
                payload["card_id"],
                payload["session_id"],
                payload["selected"],
                int(is_correct),
                payload["time_taken_ms"],
                payload["hints_used"],
                points,
                created_at,
            ),
        )
        total_points = connection.execute(
            "SELECT COALESCE(SUM(points_awarded), 0) FROM attempts WHERE user_id = ?",
            (payload["user_id"],),
        ).fetchone()[0]
        session_points = connection.execute(
            "SELECT COALESCE(SUM(points_awarded), 0) FROM attempts WHERE session_id = ?",
            (payload["session_id"],),
        ).fetchone()[0]
        connection.commit()
    return {
        "id": attempt_id,
        "is_correct": is_correct,
        "points_awarded": points,
        "current_streak": current_streak,
        "total_points": total_points,
        "session_points": session_points,
        "created_at": created_at,
    }


def get_leaderboard(period: str = "all", limit: int = 10) -> List[Dict]:
    cutoff = None
    if period == "week":
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with _connection() as connection:
        rows = connection.execute("SELECT id, username FROM users").fetchall()
        rankings = []
        for user in rows:
            if cutoff:
                attempt_filter = "AND created_at >= ?"
                attempt_params = (user["id"], cutoff)
                session_filter = "AND finished_at >= ?"
                session_params = (user["id"], cutoff)
            else:
                attempt_filter = ""
                attempt_params = (user["id"],)
                session_filter = ""
                session_params = (user["id"],)
            stats = connection.execute(
                f"""
                SELECT COALESCE(SUM(points_awarded), 0) AS points,
                       COUNT(*) AS attempts, COALESCE(SUM(is_correct), 0) AS correct
                FROM attempts WHERE user_id = ? {attempt_filter}
                """,
                attempt_params,
            ).fetchone()
            sessions = connection.execute(
                f"""
                SELECT COUNT(DISTINCT deck_id) AS completed, MIN(finished_at) AS earliest_finish
                FROM deck_sessions WHERE user_id = ? AND finished_at IS NOT NULL {session_filter}
                """,
                session_params,
            ).fetchone()
            attempts = stats["attempts"]
            rankings.append(
                {
                    "user_id": user["id"],
                    "username": user["username"],
                    "total_points": stats["points"],
                    "accuracy": round(stats["correct"] / attempts * 100, 1) if attempts else 0,
                    "decks_completed": sessions["completed"],
                    "earliest_finish": sessions["earliest_finish"],
                }
            )
    rankings.sort(
        key=lambda item: (
            -item["total_points"],
            -item["accuracy"],
            item["earliest_finish"] or "9999",
            item["username"].casefold(),
        )
    )
    return [
        {**entry, "rank": rank}
        for rank, entry in enumerate(rankings[:limit], 1)
    ]


def get_user_profile(user_id: str) -> Optional[Dict]:
    with _connection() as connection:
        user = connection.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return None
        attempts = connection.execute(
            """
            SELECT a.*, d.title AS deck_title, d.category
            FROM attempts a JOIN decks d ON d.id = a.deck_id
            WHERE a.user_id = ? ORDER BY a.rowid
            """,
            (user_id,),
        ).fetchall()
        by_deck = {}
        by_topic = {}
        best_streak = 0
        streak_by_session = {}
        current_streak = 0
        for attempt in attempts:
            record = by_deck.setdefault(
                attempt["deck_id"],
                {"deck_id": attempt["deck_id"], "deck_title": attempt["deck_title"],
                 "topic": attempt["category"], "attempts": 0, "correct": 0},
            )
            record["attempts"] += 1
            record["correct"] += attempt["is_correct"]
            topic_record = by_topic.setdefault(
                attempt["category"],
                {"topic": attempt["category"], "attempts": 0, "correct": 0},
            )
            topic_record["attempts"] += 1
            topic_record["correct"] += attempt["is_correct"]
            streak = streak_by_session.get(attempt["session_id"], 0)
            streak = streak + 1 if attempt["is_correct"] else 0
            streak_by_session[attempt["session_id"]] = streak
            best_streak = max(best_streak, streak)
        latest_session = connection.execute(
            """
            SELECT id FROM deck_sessions WHERE user_id = ?
            ORDER BY started_at DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if latest_session:
            for attempt in reversed(attempts):
                if attempt["session_id"] != latest_session["id"]:
                    continue
                if not attempt["is_correct"]:
                    break
                current_streak += 1
        for item in by_deck.values():
            item["accuracy"] = round(item["correct"] / item["attempts"] * 100, 1)
        for item in by_topic.values():
            item["accuracy"] = round(item["correct"] / item["attempts"] * 100, 1)
        weakest_topics = sorted(
            by_topic.values(), key=lambda item: (item["accuracy"], -item["attempts"])
        )[:5]
        recent_sessions = [
            dict(row)
            for row in connection.execute(
                """
                SELECT s.id, s.deck_id, d.title AS deck_title, s.started_at, s.finished_at,
                       s.score, s.total_points, s.ai_overview
                FROM deck_sessions s JOIN decks d ON d.id = s.deck_id
                WHERE s.user_id = ? ORDER BY s.started_at DESC LIMIT 10
                """,
                (user_id,),
            )
        ]
        total = len(attempts)
        correct = sum(row["is_correct"] for row in attempts)
        total_points = sum(row["points_awarded"] for row in attempts)
    leaderboard = get_leaderboard("all", 100000)
    rank = next(
        (entry["rank"] for entry in leaderboard if entry["user_id"] == user_id),
        None,
    )
    return {
        "user": dict(user),
        "total_points": total_points,
        "rank": rank,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "accuracy": round(correct / total * 100, 1) if total else 0,
        "accuracy_per_deck": list(by_deck.values()),
        "weakest_topics": weakest_topics,
        "recent_sessions": recent_sessions,
    }
