from datetime import datetime
import json

from auth.deps import Scope
from database.connection import get_conn


def save_analisis(capitulo_id: int, contenido: dict, scope: Scope):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO analisis (capitulo_id, contenido_json, usuario_id, guest_id, creado_en) "
            "VALUES (?, ?, ?, ?, ?)",
            (capitulo_id, json.dumps(contenido, ensure_ascii=False),
             scope.usuario_id, scope.guest_id, datetime.utcnow().isoformat()),
        )


def get_analisis(capitulo_id: int, scope: Scope):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT * FROM analisis WHERE capitulo_id = ? AND {cond} ORDER BY id DESC LIMIT 1",
            [capitulo_id] + params,
        ).fetchone()
        return json.loads(row["contenido_json"]) if row else None
