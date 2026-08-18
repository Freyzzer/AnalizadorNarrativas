from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Response

from auth.session import (
    JWT_ALGORITHM,
    JWT_SECRET,
    _hacer_jwt,
    _leer_jwt,
    borrar_cookie_jwt,
    crear_cookie_jwt,
)


def test_jwt_roundtrip():
    token = _hacer_jwt(42)
    assert _leer_jwt(token) == 42


def test_jwt_invalido():
    assert _leer_jwt("basura") is None
    assert _leer_jwt("") is None
    assert _leer_jwt(jwt.encode({"sub": 1}, "otra-secret", algorithm=JWT_ALGORITHM)) is None


def test_jwt_expirado():
    exp = datetime.now(timezone.utc) - timedelta(hours=1)
    token = jwt.encode({"sub": 7, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert _leer_jwt(token) is None


def test_jwt_sin_sub():
    token = jwt.encode({"otro": "x"}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert _leer_jwt(token) is None


def test_crear_y_borrar_cookie():
    r = Response()
    crear_cookie_jwt(r, 3)
    assert "session=" in r.headers.get("set-cookie", "")
    assert "httponly" in r.headers.get("set-cookie", "").lower()
    borrar_cookie_jwt(r)
    assert "session=" in r.headers.get("set-cookie", "")
