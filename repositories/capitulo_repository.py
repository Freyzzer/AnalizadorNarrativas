from datetime import datetime

from database.connection import get_conn
from repositories.personaje_repository import _recalcular_descripcion_actual


def add_capitulo(obra_id: int, numero: int, texto: str, titulo: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO capitulos (obra_id, numero, titulo, texto, creado_en) VALUES (?, ?, ?, ?, ?)",
            (obra_id, numero, titulo, texto, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_capitulos(obra_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM capitulos WHERE obra_id = ? ORDER BY numero ASC", (obra_id,)
        ).fetchall()


def get_ultimo_numero_capitulo(obra_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(numero) as n FROM capitulos WHERE obra_id = ?", (obra_id,)
        ).fetchone()
        return (row["n"] or 0)


def get_capitulo(capitulo_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM capitulos WHERE id = ?", (capitulo_id,)).fetchone()


def update_capitulo(capitulo_id: int, texto: str, titulo: str = "", numero: int = None):
    with get_conn() as conn:
        if numero is None:
            conn.execute(
                "UPDATE capitulos SET texto = ?, titulo = ? WHERE id = ?",
                (texto, titulo, capitulo_id),
            )
        else:
            conn.execute(
                "UPDATE capitulos SET texto = ?, titulo = ?, numero = ? WHERE id = ?",
                (texto, titulo, numero, capitulo_id),
            )


def limpiar_datos_generados_capitulo(capitulo_id: int):
    """
    Borra los hechos de continuidad, inconsistencias, análisis y entradas de
    historial de personajes que se generaron a partir de un capítulo. Se usa
    antes de re-analizarlo (para no duplicar datos) o antes de eliminarlo
    (para no dejar registros huérfanos apuntando a un capítulo que ya no existe).
    """
    with get_conn() as conn:
        personajes_afectados = [
            r["personaje_id"]
            for r in conn.execute(
                "SELECT DISTINCT personaje_id FROM personaje_historial WHERE capitulo_id = ?",
                (capitulo_id,),
            ).fetchall()
        ]
        conn.execute("DELETE FROM hechos_continuidad WHERE capitulo_id = ?", (capitulo_id,))
        conn.execute("DELETE FROM inconsistencias WHERE capitulo_id = ?", (capitulo_id,))
        conn.execute("DELETE FROM analisis WHERE capitulo_id = ?", (capitulo_id,))
        conn.execute("DELETE FROM personaje_historial WHERE capitulo_id = ?", (capitulo_id,))

    for personaje_id in personajes_afectados:
        _recalcular_descripcion_actual(personaje_id)


def delete_capitulo(capitulo_id: int):
    limpiar_datos_generados_capitulo(capitulo_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM capitulos WHERE id = ?", (capitulo_id,))