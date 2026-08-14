from datetime import datetime

from database.connection import get_conn


def upsert_personaje(obra_id: int, nombre: str, descripcion: str, capitulo_numero: int, capitulo_id: int) -> int:
    """
    Registra la aparición de un personaje (o, según el género literario de la obra,
    una voz lírica, un concepto clave, etc. — ver llm.GENEROS) en un capítulo.
    No sobrescribe su historia: guarda esta descripción como una entrada nueva en
    personaje_historial y actualiza 'descripcion_actual' como un acceso rápido a
    su estado más reciente. Devuelve el id del personaje.
    """
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM personajes WHERE obra_id = ? AND nombre = ?",
            (obra_id, nombre),
        ).fetchone()
        if existente:
            personaje_id = existente["id"]
            conn.execute(
                "UPDATE personajes SET descripcion_actual = ? WHERE id = ?",
                (descripcion, personaje_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO personajes (obra_id, nombre, descripcion_actual, primera_aparicion_cap) "
                "VALUES (?, ?, ?, ?)",
                (obra_id, nombre, descripcion, capitulo_numero),
            )
            personaje_id = cur.lastrowid

        conn.execute(
            "INSERT INTO personaje_historial (personaje_id, capitulo_id, capitulo_numero, descripcion, creado_en) "
            "VALUES (?, ?, ?, ?, ?)",
            (personaje_id, capitulo_id, capitulo_numero, descripcion, datetime.utcnow().isoformat()),
        )
        return personaje_id


def get_historial_personaje(personaje_id: int):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT ph.*, c.titulo as capitulo_titulo
            FROM personaje_historial ph
            JOIN capitulos c ON c.id = ph.capitulo_id
            WHERE ph.personaje_id = ?
            ORDER BY ph.capitulo_numero ASC, ph.id ASC
            """,
            (personaje_id,),
        ).fetchall()


def _recalcular_descripcion_actual(personaje_id: int):
    """
    Recalcula 'descripcion_actual' a partir de la entrada de historial más reciente
    que quede. Se usa después de borrar el historial ligado a un capítulo eliminado
    o re-analizado, para que la descripción rápida no quede apuntando a datos borrados.
    """
    with get_conn() as conn:
        ultimo = conn.execute(
            """
            SELECT descripcion FROM personaje_historial
            WHERE personaje_id = ?
            ORDER BY capitulo_numero DESC, id DESC LIMIT 1
            """,
            (personaje_id,),
        ).fetchone()
        if ultimo:
            conn.execute(
                "UPDATE personajes SET descripcion_actual = ? WHERE id = ?",
                (ultimo["descripcion"], personaje_id),
            )
        else:
            conn.execute(
                "UPDATE personajes SET descripcion_actual = ? WHERE id = ?",
                ("(sin descripción — el/los capítulo(s) donde aparecía se eliminaron)", personaje_id),
            )


def list_personajes(obra_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM personajes WHERE obra_id = ? ORDER BY nombre ASC", (obra_id,)
        ).fetchall()
