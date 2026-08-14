from datetime import datetime

from database.connection import get_conn


def upsert_usuario_google(google_sub: str, email: str = None, nombre: str = None, avatar: str = None):
    """Crea o actualiza un usuario a partir del perfil de Google. Devuelve la fila completa."""
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT * FROM usuarios WHERE google_sub = ?", (google_sub,)
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE usuarios SET email = ?, nombre = ?, avatar = ? WHERE id = ?",
                (email, nombre, avatar, existente["id"]),
            )
            return conn.execute(
                "SELECT * FROM usuarios WHERE id = ?", (existente["id"],)
            ).fetchone()

        cur = conn.execute(
            "INSERT INTO usuarios (google_sub, email, nombre, avatar, creado_en) VALUES (?, ?, ?, ?, ?)",
            (google_sub, email, nombre, avatar, datetime.utcnow().isoformat()),
        )
        return conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (cur.lastrowid,)
        ).fetchone()


def get_usuario_by_id(usuario_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
