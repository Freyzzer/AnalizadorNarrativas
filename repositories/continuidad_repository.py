from datetime import datetime

from auth.deps import Scope
from database.connection import get_conn

ESTADOS_INCONSISTENCIA = ["pendiente", "intencional", "resuelta"]

def registrar_hecho(obra_id: int, entidad: str, atributo: str, valor: str, capitulo_id: int,
                    capitulo_numero: int, scope: Scope):
    """
    Guarda un hecho nuevo. Si ya existe un hecho previo para la misma
    entidad+atributo con un valor distinto, genera una inconsistencia.
    Devuelve la inconsistencia detectada (o None).
    """
    cond, params = scope.owner_sql("hc")
    with get_conn() as conn:
        anterior = conn.execute(
            f"""
            SELECT hc.valor, c.numero as capitulo_numero
            FROM hechos_continuidad hc
            JOIN capitulos c ON c.id = hc.capitulo_id
            WHERE hc.obra_id = ? AND hc.entidad = ? AND hc.atributo = ? AND {cond}
            ORDER BY c.numero DESC LIMIT 1
            """,
            [obra_id, entidad, atributo] + params,
        ).fetchone()

        conn.execute(
            "INSERT INTO hechos_continuidad (obra_id, entidad, atributo, valor, capitulo_id, "
            "usuario_id, guest_id, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (obra_id, entidad, atributo, valor, capitulo_id,
             *scope.owner_insert(), datetime.utcnow().isoformat()),
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
                (obra_id, capitulo_id, entidad, atributo, valor_anterior, valor_nuevo,
                 capitulo_anterior_numero, descripcion, usuario_id, guest_id, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obra_id, capitulo_id, entidad, atributo,
                    anterior["valor"], valor, anterior["capitulo_numero"], descripcion,
                    *scope.owner_insert(), datetime.utcnow().isoformat(),
                ),
            )
            return descripcion
        return None


def list_inconsistencias(obra_id: int, scope: Scope, estado: str = None):
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        if estado:
            return conn.execute(
                f"SELECT * FROM inconsistencias WHERE obra_id = ? AND {cond} AND estado = ? ORDER BY id DESC",
                [obra_id] + params + [estado],
            ).fetchall()
        return conn.execute(
            f"SELECT * FROM inconsistencias WHERE obra_id = ? AND {cond} ORDER BY id DESC",
            [obra_id] + params,
        ).fetchall()


def actualizar_estado_inconsistencia(inconsistencia_id: int, nuevo_estado: str, scope: Scope):
    if nuevo_estado not in ESTADOS_INCONSISTENCIA:
        raise ValueError(f"Estado inválido: {nuevo_estado}. Debe ser uno de {ESTADOS_INCONSISTENCIA}.")
    cond, params = scope.owner_sql()
    with get_conn() as conn:
        conn.execute(
            f"UPDATE inconsistencias SET estado = ? WHERE id = ? AND {cond}",
            [nuevo_estado, inconsistencia_id] + params,
        )
