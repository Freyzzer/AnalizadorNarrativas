from database.connection import get_conn

ESTADOS_INCONSISTENCIA = ["pendiente", "intencional", "resuelta"]

def registrar_hecho(obra_id: int, entidad: str, atributo: str, valor: str, capitulo_id: int, capitulo_numero: int):
    """
    Guarda un hecho nuevo. Si ya existe un hecho previo para la misma
    entidad+atributo con un valor distinto, genera una inconsistencia.
    Devuelve la inconsistencia detectada (o None).
    """
    with get_conn() as conn:
        anterior = conn.execute(
            """
            SELECT hc.valor, c.numero as capitulo_numero
            FROM hechos_continuidad hc
            JOIN capitulos c ON c.id = hc.capitulo_id
            WHERE hc.obra_id = ? AND hc.entidad = ? AND hc.atributo = ?
            ORDER BY c.numero DESC LIMIT 1
            """,
            (obra_id, entidad, atributo),
        ).fetchone()

        conn.execute(
            "INSERT INTO hechos_continuidad (obra_id, entidad, atributo, valor, capitulo_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (obra_id, entidad, atributo, valor, capitulo_id),
        )

        if anterior and anterior["valor"].strip().lower() != valor.strip().lower():
            descripcion = (
                f'En el capítulo {anterior["capitulo_numero"]} se estableció que '
                f'{entidad} → {atributo} = "{anterior["valor"]}", pero en el capítulo '
                f'{capitulo_numero} aparece como "{valor}".'
            )
            conn.execute(
                """
                INSERT INTO inconsistencias
                (obra_id, capitulo_id, entidad, atributo, valor_anterior, valor_nuevo, capitulo_anterior_numero, descripcion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obra_id, capitulo_id, entidad, atributo,
                    anterior["valor"], valor, anterior["capitulo_numero"], descripcion,
                ),
            )
            return descripcion
        return None


def list_inconsistencias(obra_id: int, estado: str = None):
    with get_conn() as conn:
        if estado:
            return conn.execute(
                "SELECT * FROM inconsistencias WHERE obra_id = ? AND estado = ? ORDER BY id DESC",
                (obra_id, estado),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM inconsistencias WHERE obra_id = ? ORDER BY id DESC", (obra_id,)
        ).fetchall()


def actualizar_estado_inconsistencia(inconsistencia_id: int, nuevo_estado: str):
    if nuevo_estado not in ESTADOS_INCONSISTENCIA:
        raise ValueError(f"Estado inválido: {nuevo_estado}. Debe ser uno de {ESTADOS_INCONSISTENCIA}.")
    with get_conn() as conn:
        conn.execute(
            "UPDATE inconsistencias SET estado = ? WHERE id = ?", (nuevo_estado, inconsistencia_id)
        )
