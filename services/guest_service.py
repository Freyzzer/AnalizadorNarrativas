import os
from datetime import datetime, timedelta

from database.connection import get_conn

TABLAS_CON_DUENO = [
    "chats",
    "analisis",
    "hechos_continuidad",
    "inconsistencias",
    "personaje_historial",
    "personajes",
    "capitulos",
    "obras",
]


def purgar_datos_invitados(dias: int = None) -> int:
    """Borra filas de invitados (guest_id) más antiguas que 'dias'. Devuelve cuántas borró."""
    if dias is None:
        dias = int(os.getenv("GUEST_TTL_DIAS", "7"))
    corte = (datetime.utcnow() - timedelta(days=dias)).isoformat()
    total = 0
    with get_conn() as conn:
        for tabla in TABLAS_CON_DUENO:
            cur = conn.execute(
                f"DELETE FROM {tabla} WHERE guest_id IS NOT NULL AND creado_en < ?", (corte,)
            )
            total += cur.rowcount
    return total
