from backend.storage import _postgres_query


def test_postgres_query_translates_sqlite_pragmas_and_placeholders():
    query = _postgres_query(
        "BEGIN IMMEDIATE; SELECT id FROM users WHERE username = ? COLLATE NOCASE"
    )

    assert query == "BEGIN; SELECT id FROM users WHERE LOWER(username) = LOWER(%s)"


def test_postgres_query_translates_rowid_with_table_alias():
    query = _postgres_query(
        "SELECT a.id FROM attempts a WHERE a.session_id = ? ORDER BY a.rowid"
    )

    assert query.endswith("ORDER BY a.created_at, a.id")


def test_postgres_query_makes_material_import_idempotent():
    query = _postgres_query(
        "INSERT OR IGNORE INTO materials (id, filename) VALUES (?, ?)"
    )

    assert query == (
        "INSERT INTO materials (id, filename) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING"
    )
