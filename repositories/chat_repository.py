from datetime import datetime

from auth.deps import Scope
from database.connection import get_conn


def save_chat(obra_id: int, pregunta: str, respuesta: str, scope: Scope):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chats (obra_id, usuario_id, guest_id, pregunta, respuesta, creado_en) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (obra_id, *scope.owner_insert(), pregunta, respuesta, datetime.utcnow().isoformat()),
        )


def list_chats(obra_id: int, scope: Scope):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        return conn.execute(
            f"SELECT * FROM chats WHERE obra_id = ? AND {cond} ORDER BY id ASC",
            [obra_id] + params,
        ).fetchall()


def delete_chat(chat_id: int, scope: Scope):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        conn.execute(f"DELETE FROM chats WHERE id = ? AND {cond}", [chat_id] + params)
