from datetime import datetime

from database.connection import get_conn
import json

def save_analisis(capitulo_id: int, contenido: dict):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO analisis (capitulo_id, contenido_json, creado_en) VALUES (?, ?, ?)",
            (capitulo_id, json.dumps(contenido, ensure_ascii=False), datetime.utcnow().isoformat()),
        )


def get_analisis(capitulo_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM analisis WHERE capitulo_id = ? ORDER BY id DESC LIMIT 1",
            (capitulo_id,),
        ).fetchone()
        return json.loads(row["contenido_json"]) if row else None
