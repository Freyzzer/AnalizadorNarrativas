from datetime import datetime

from auth.deps import Scope
from database.connection import get_conn


def create_obra(titulo: str, genero: str = "", scope: Scope = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO obras (titulo, genero, usuario_id, guest_id, creado_en) VALUES (?, ?, ?, ?, ?)",
            (titulo, genero, *scope.owner_insert(), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_obras(scope: Scope):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        return conn.execute(f"SELECT * FROM obras WHERE {cond} ORDER BY id DESC", params).fetchall()


def get_obra(obra_id: int, scope: Scope):
    """Devuelve la fila de una obra (incluye su campo 'genero'), o None si no existe o no es del dueño."""
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        return conn.execute(
            f"SELECT * FROM obras WHERE id = ? AND {cond}", [obra_id] + params
        ).fetchone()
