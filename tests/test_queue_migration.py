import sqlite3
from app_queue import worker


def test_fresh_db_initialization(tmp_path):
    """Verifies that a brand new database is initialized with all target columns and indexes."""
    db_file = tmp_path / "fresh_cola.db"
    worker.init_db(db_file)

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(queue);")
        columns = {row["name"] for row in cursor.fetchall()}

        expected_columns = {
            "id",
            "recipient_id",
            "channel",
            "chat_id",
            "operacion",
            "payload_json",
            "estado",
            "reintentos",
            "next_retry",
            "creado_at",
        }
        assert expected_columns.issubset(columns)

        cursor.execute("PRAGMA index_list(queue);")
        indexes = {row["name"] for row in cursor.fetchall()}
        assert "idx_queue_estado_retry" in indexes
    finally:
        conn.close()


def test_migration_from_v1_legacy_schema(tmp_path):
    """Verifies that an existing v1 queue database is safely migrated with zero data loss."""
    db_file = tmp_path / "legacy_cola.db"

    # 1. Create table with legacy v1 schema (chat_id only, no recipient_id or channel)
    conn = sqlite3.connect(str(db_file))
    with conn:
        conn.execute("""
            CREATE TABLE queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                operacion TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'pendiente',
                reintentos INTEGER NOT NULL DEFAULT 0,
                next_retry INTEGER NOT NULL DEFAULT 0,
                creado_at INTEGER NOT NULL
            )
            """)
        conn.execute("""
            INSERT INTO queue (chat_id, operacion, payload_json, creado_at)
            VALUES (55555, 'op_vieja', '{"foo": "bar"}', 1600000000)
            """)
        conn.execute("""
            INSERT INTO queue (chat_id, operacion, payload_json, creado_at)
            VALUES (66666, 'op_otra', '{"num": 123}', 1600000050)
            """)
    conn.close()

    # 2. Run init_db migration
    worker.init_db(db_file)

    # 3. Verify columns and data migration
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(queue);")
        columns = {row["name"] for row in cursor.fetchall()}
        assert "recipient_id" in columns
        assert "channel" in columns

        cursor.execute("SELECT * FROM queue ORDER BY id ASC")
        rows = cursor.fetchall()
        assert len(rows) == 2

        # Row 1 check
        assert rows[0]["id"] == 1
        assert rows[0]["chat_id"] == 55555
        assert rows[0]["recipient_id"] == "55555"
        assert rows[0]["channel"] == "telegram"
        assert rows[0]["operacion"] == "op_vieja"

        # Row 2 check
        assert rows[1]["id"] == 2
        assert rows[1]["chat_id"] == 66666
        assert rows[1]["recipient_id"] == "66666"
        assert rows[1]["channel"] == "telegram"
        assert rows[1]["operacion"] == "op_otra"
    finally:
        conn.close()


def test_migration_is_idempotent(tmp_path):
    """Verifies that calling init_db multiple times is completely idempotent."""
    db_file = tmp_path / "idempotent_cola.db"

    # Call init_db three consecutive times
    worker.init_db(db_file)
    worker.init_db(db_file)
    worker.init_db(db_file)

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(queue);")
        columns = [row["name"] for row in cursor.fetchall()]
        assert columns.count("recipient_id") == 1
        assert columns.count("channel") == 1
    finally:
        conn.close()
