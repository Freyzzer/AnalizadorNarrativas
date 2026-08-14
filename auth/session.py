import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Response

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-cambiar-en-produccion")
JWT_ALGORITHM = "HS256"
JWT_EXP_DIAS = int(os.getenv("JWT_EXP_DIAS", "7"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")  # "lax" en dev (mismo sitio localhost) o "none" en prod


def _hacer_jwt(usuario_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DIAS)
    return jwt.encode({"sub": usuario_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _leer_jwt(token: str):
    """Devuelve el usuario_id del JWT, o None si es inválido/expirado."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]).get("sub")
    except jwt.PyJWTError:
        return None


def crear_cookie_jwt(response: Response, usuario_id: int):
    response.set_cookie(
        key="session",
        value=_hacer_jwt(usuario_id),
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=JWT_EXP_DIAS * 86400,
        path="/",
    )


def borrar_cookie_jwt(response: Response):
    response.delete_cookie("session", path="/")
