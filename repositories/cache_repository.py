# pregunta antes (mismo prompt + mismo texto de entrada). Esto pasa seguido:
# re-abrir la app y volver a ver un capítulo, re-analizar sin haber cambiado el
# texto, o hacerle al chat la misma pregunta dos veces. La clave (`clave`) la
# arma llm_antiguo.py como un hash de (modelo, tipo de llamada, prompt, contenido).
from datetime import datetime

from database.connection import get_conn


def cache_get(clave: str):
    """Devuelve la respuesta cruda (texto) guardada para esta clave, o None si no existe."""
    with get_conn() as conn:
        row = conn.execute("SELECT respuesta FROM cache_llm WHERE clave = ?", (clave,)).fetchone()
        return row["respuesta"] if row else None


def cache_set(clave: str, respuesta: str):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO cache_llm (clave, respuesta, creado_en) VALUES (?, ?, ?)
            ON CONFLICT(clave) DO UPDATE SET respuesta = excluded.respuesta, creado_en = excluded.creado_en
            """,
            (clave, respuesta, datetime.utcnow().isoformat()),
        )


def cache_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as n FROM cache_llm").fetchone()
        return row["n"]


def cache_clear():
    with get_conn() as conn:
        conn.execute("DELETE FROM cache_llm")