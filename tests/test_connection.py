import sqlite3

from database.connection import DB_PATH, USE_POSTGRES, get_conn, _sqlite_a_pg


def test_usar_sqlite_sin_database_url():
    assert USE_POSTGRES is False
    assert "analizador_test_" in DB_PATH
    assert "narrativa.db" not in DB_PATH


def test_sqlite_a_pg_traduce_placeholders():
    assert _sqlite_a_pg("SELECT * FROM x WHERE a = ? AND b = ?") == \
        "SELECT * FROM x WHERE a = %s AND b = %s"
    # no toca literales entre comillas
    assert _sqlite_a_pg("INSERT INTO t (v) VALUES ('¿?', ?)") == \
        "INSERT INTO t (v) VALUES ('¿?', %s)"


def test_get_conn_commits_y_cierra():
    with get_conn() as conn:
        conn.execute("INSERT INTO obras (titulo, creado_en) VALUES (?, ?)", ("test", "2026-01-01"))
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM obras WHERE titulo = ?", ("test",)).fetchone()
        assert row["n"] == 1
        assert isinstance(row, (sqlite3.Row, dict))


def test_get_conn_filas_como_mapping():
    with get_conn() as conn:
        conn.execute("INSERT INTO obras (titulo, creado_en) VALUES (?, ?)", ("x", "y"))
        row = conn.execute("SELECT * FROM obras WHERE titulo = ?", ("x",)).fetchone()
        assert row["titulo"] == "x"
        assert dict(row)["titulo"] == "x"


def test_foreign_keys_activas():
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO capitulos (obra_id, numero, texto) VALUES (999, 1, 'huérfano')"
            )
            assert False, "debió fallar la FK"
        except Exception:
            pass
