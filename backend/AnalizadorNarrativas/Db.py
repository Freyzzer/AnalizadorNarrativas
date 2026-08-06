"""
Capa de datos del analizador de narrativas.
Usa SQLite porque el prototipo corre en local para un solo usuario/escritor.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "narrativa.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS obras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                genero TEXT,
                creado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS capitulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                numero INTEGER NOT NULL,
                titulo TEXT,
                texto TEXT NOT NULL,
                creado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS personajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                nombre TEXT NOT NULL,
                descripcion_actual TEXT,
                primera_aparicion_cap INTEGER,
                UNIQUE(obra_id, nombre)
            );

            CREATE TABLE IF NOT EXISTS hechos_continuidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                entidad TEXT NOT NULL,
                atributo TEXT NOT NULL,
                valor TEXT NOT NULL,
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id)
            );

            CREATE TABLE IF NOT EXISTS inconsistencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
                entidad TEXT,
                atributo TEXT,
                valor_anterior TEXT,
                valor_nuevo TEXT,
                capitulo_anterior_numero INTEGER,
                descripcion TEXT
            );

            CREATE TABLE IF NOT EXISTS analisis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
                contenido_json TEXT NOT NULL,
                creado_en TEXT
            );
            """
        )


# ---------- Obras ----------

def create_obra(titulo: str, genero: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO obras (titulo, genero, creado_en) VALUES (?, ?, ?)",
            (titulo, genero, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def list_obras():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM obras ORDER BY id DESC").fetchall()


# ---------- Capítulos ----------

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


# ---------- Personajes ----------

def upsert_personaje(obra_id: int, nombre: str, descripcion: str, capitulo_numero: int):
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM personajes WHERE obra_id = ? AND nombre = ?",
            (obra_id, nombre),
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE personajes SET descripcion_actual = ? WHERE id = ?",
                (descripcion, existente["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO personajes (obra_id, nombre, descripcion_actual, primera_aparicion_cap) "
                "VALUES (?, ?, ?, ?)",
                (obra_id, nombre, descripcion, capitulo_numero),
            )


def list_personajes(obra_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM personajes WHERE obra_id = ? ORDER BY nombre ASC", (obra_id,)
        ).fetchall()


# ---------- Hechos de continuidad e inconsistencias ----------

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


def list_inconsistencias(obra_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM inconsistencias WHERE obra_id = ? ORDER BY id DESC", (obra_id,)
        ).fetchall()


# ---------- Análisis ----------

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


def story_bible_resumen(obra_id: int) -> str:
    """Genera un resumen compacto en texto de la story bible, para usar como contexto en prompts."""
    personajes = list_personajes(obra_id)
    if not personajes:
        return "Todavía no hay personajes registrados."
    lineas = ["Personajes establecidos hasta ahora:"]
    for p in personajes:
        lineas.append(f"- {p['nombre']}: {p['descripcion_actual']}")
    return "\n".join(lineas)