import os

from fastapi import HTTPException, Request, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from auth.deps import get_scope_optional
from auth.session import borrar_cookie_jwt, crear_cookie_jwt
from main import GoogleLoginBody, app
from repositories.user_repository import get_usuario_by_id, upsert_usuario_google

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


def _usuario_publico(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "nombre": row["nombre"],
        "avatar": row["avatar"],
    }


@app.post("/auth/google")
def login_google(body: GoogleLoginBody, response: Response):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "GOOGLE_CLIENT_ID no está configurado en el backend")

    try:
        info = id_token.verify_oauth2_token(
            body.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        raise HTTPException(401, f"Token de Google inválido: {e}") from e

    usuario = upsert_usuario_google(
        info["sub"], info.get("email"), info.get("name"), info.get("picture")
    )
    crear_cookie_jwt(response, usuario["id"])
    return {"usuario": _usuario_publico(usuario)}


@app.post("/auth/logout")
def logout(response: Response):
    borrar_cookie_jwt(response)
    return {"ok": True}


@app.get("/auth/me")
def me(request: Request):
    """Devuelve el usuario logueado o null (no exige autenticación)."""
    scope = get_scope_optional(request)
    if scope.usuario_id is None:
        return {"usuario": None}
    row = get_usuario_by_id(scope.usuario_id)
    return {"usuario": _usuario_publico(row) if row else None}
