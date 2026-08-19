import os
from datetime import datetime, timezone

from database.connection import get_conn

LIMIT_DIARIO = int(os.getenv("LLM_DAILY_LIMIT", "200"))


def _owner_key(usuario_id: int | None, guest_id: str | None) -> str:
    if usuario_id:
        return f"u:{usuario_id}"
    return f"g:{guest_id}"


def usage_check(usuario_id: int | None, guest_id: str | None) -> int:
    """Devuelve las llamadas restantes hoy para este owner. Si no existe registro, crea uno."""
    owner = _owner_key(usuario_id, guest_id)
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT llamadas FROM usage_diaria WHERE owner_key = ? AND dia = ?",
            (owner, hoy),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO usage_diaria (owner_key, dia, llamadas) VALUES (?, ?, 0)",
                (owner, hoy),
            )
            return LIMIT_DIARIO
        return LIMIT_DIARIO - row["llamadas"]


def usage_increment(usuario_id: int | None, guest_id: str | None):
    """Incrementa el contador de llamadas para hoy."""
    owner = _owner_key(usuario_id, guest_id)
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO usage_diaria (owner_key, dia, llamadas) VALUES (?, ?, 1)
               ON CONFLICT(owner_key, dia) DO UPDATE SET llamadas = usage_diaria.llamadas + 1""",
            (owner, hoy),
        )


def usage_stats(usuario_id: int | None, guest_id: str | None) -> dict:
    owner = _owner_key(usuario_id, guest_id)
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT llamadas FROM usage_diaria WHERE owner_key = ? AND dia = ?",
            (owner, hoy),
        ).fetchone()
        usados = row["llamadas"] if row else 0
    return {"usados": usados, "limite": LIMIT_DIARIO, "restantes": LIMIT_DIARIO - usados}
