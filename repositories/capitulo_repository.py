from datetime import datetime

from auth.deps import Scope
from database.connection import get_conn
from repositories.personaje_repository import _recalcular_descripcion_actual


def add_capitulo(obra_id: int, numero: int, texto: str, titulo: str = "", scope: Scope = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO capitulos (obra_id, numero, titulo, texto, usuario_id, guest_id, creado_en) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (obra_id, numero, titulo, texto,
             *scope.owner_insert(), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_capitulos(obra_id: int, scope: Scope):
    cond, params = scope.owner_sql()
    params = [obra_id] + params
    with get_conn() as conn:
        return conn.execute(
            f"SELECT * FROM capitulos WHERE obra_id = ? AND {cond} ORDER BY numero ASC", params
        ).fetchall()


def get_ultimo_numero_capitulo(obra_id: int, scope: Scope) -> int:
    cond, params = scope.owner_sql()
    params = [obra_id] + params
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT MAX(numero) as n FROM capitulos WHERE obra_id = ? AND {cond}", params
        ).fetchone()
        return (row["n"] or 0)


def get_capitulo(capitulo_id: int, scope: Scope):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        return conn.execute(
            f"SELECT * FROM capitulos WHERE id = ? AND {cond}", [capitulo_id] + params
        ).fetchone()


def update_capitulo(capitulo_id: int, texto: str, titulo: str = "", numero: int = None, scope: Scope = None):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        if numero is None:
            conn.execute(
                f"UPDATE capitulos SET texto = ?, titulo = ? WHERE id = ? AND {cond}",
                [texto, titulo, capitulo_id] + params,
            )
        else:
            conn.execute(
                f"UPDATE capitulos SET texto = ?, titulo = ?, numero = ? WHERE id = ? AND {cond}",
                [texto, titulo, numero, capitulo_id] + params,
            )


def limpiar_datos_generados_capitulo(capitulo_id: int, scope: Scope):
    """
    Borra los hechos de continuidad, inconsistencias, análisis y entradas de
    historial de personajes que se generaron a partir de un capítulo. Se usa
    antes de re-analizarlo (para no duplicar datos) o antes de eliminarlo
    (para no dejar registros huérfanos apuntando a un capítulo que ya no existe).
    """
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        personajes_afectados = [
            r["personaje_id"]
            for r in conn.execute(
                f"SELECT DISTINCT personaje_id FROM personaje_historial WHERE capitulo_id = ? AND {cond}",
                [capitulo_id] + params,
            ).fetchall()
        ]
        conn.execute(
            f"DELETE FROM hechos_continuidad WHERE capitulo_id = ? AND {cond}", [capitulo_id] + params
        )
        conn.execute(
            f"DELETE FROM inconsistencias WHERE capitulo_id = ? AND {cond}", [capitulo_id] + params
        )
        conn.execute(
            f"DELETE FROM analisis WHERE capitulo_id = ? AND {cond}", [capitulo_id] + params
        )
        conn.execute(
            f"DELETE FROM personaje_historial WHERE capitulo_id = ? AND {cond}", [capitulo_id] + params
        )

    for personaje_id in personajes_afectados:
        _recalcular_descripcion_actual(personaje_id, scope)


def delete_capitulo(capitulo_id: int, scope: Scope):
    cond, params = scope.owner_sql()
    limpiar_datos_generados_capitulo(capitulo_id, scope)
    with get_conn() as conn:
        conn.execute(f"DELETE FROM capitulos WHERE id = ? AND {cond}", [capitulo_id] + params)
