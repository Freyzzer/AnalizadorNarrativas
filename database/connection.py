import os
import sqlite3
from contextlib import contextmanager

# Postgres si hay DATABASE_URL (producción/Neon); SQLite local en desarrollo.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", "narrativa.db")

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row


def _sqlite_a_pg(sql: str) -> str:
    """Traduce placeholders '?' (sqlite) a '%s' (psycopg), sin tocar literales entre comillas."""
    out = []
    en_string = False
    for ch in sql:
        if ch == "'":
            en_string = not en_string
            out.append(ch)
        elif ch == "?" and not en_string:
            out.append("%s")
        else:
            out.append(ch)
    return "".join(out)


def _es_insert(sql: str) -> bool:
    return sql.strip().upper().startswith("INSERT")


def _dividir_stmts(sql: str):
    for stmt in sql.split(";"):
        if stmt.strip():
            yield stmt


class _PgCursor:
    """Envuelve un cursor psycopg para imitar la interfaz de sqlite3 (lastrowid, rowcount)."""

    def __init__(self, cur):
        self._cur = cur
        self._lastrowid = None

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


class _PgConn:
    """Envuelve una conexión psycopg para exponer execute()/executescript() estilo sqlite3."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        sql_pg = _sqlite_a_pg(sql)
        es_insert = _es_insert(sql_pg)
        if es_insert and " RETURNING " not in sql_pg.upper():
            sql_pg = sql_pg.rstrip().rstrip(";") + " RETURNING id"
        cur = self._conn.execute(sql_pg, params or ())
        cursor = _PgCursor(cur)
        if es_insert:
            fila = cur.fetchone()
            if fila:
                cursor._lastrowid = fila["id"] if isinstance(fila, dict) else fila[0]
        return cursor

    def executescript(self, sql):
        for stmt in _dividir_stmts(sql):
            self.execute(stmt)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _conectar_postgres():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _conectar_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    """Conexión a la DB con commit al finalizar. Usa Postgres si DATABASE_URL está definida."""
    if USE_POSTGRES:
        conn = _conectar_postgres()
        try:
            yield _PgConn(conn)
            conn.commit()
        finally:
            conn.close()
    else:
        conn = _conectar_sqlite()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
