from datetime import datetime

from database.connection import get_conn


def create_obra(titulo: str, genero: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO obras (titulo, genero, creado_en) VALUES (?, ?, ?)",
            (titulo, genero, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_obras():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM obras ORDER BY id DESC").fetchall()


def get_obra(obra_id: int):
    """Devuelve la fila de una obra (incluye su campo 'genero'), o None si no existe."""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM obras WHERE id = ?", (obra_id,)).fetchone()