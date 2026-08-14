from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass
class Scope:
    """Dueño de los datos: un usuario autenticado (usuario_id) o un invitado (guest_id)."""
    usuario_id: int | None = None
    guest_id: str | None = None

    def owner_sql(self, alias: str = "") -> tuple:
        """Fragmento SQL para filtrar por dueño, con sus parámetros.
        Si una de las dos claves es None, su comparación no matchea nada (NULL), así
        que funciona como OR simple para usuarios autenticados o invitados."""
        prefijo = f"{alias}." if alias else ""
        return (
            f"({prefijo}usuario_id = ? OR {prefijo}guest_id = ?)",
            [self.usuario_id, self.guest_id],
        )


def get_scope_optional(request: Request) -> Scope:
    """Resuelve el dueño de la petición: cookie de sesión (usuario) o header X-Guest-Id (invitado)."""
    from auth.session import _leer_jwt

    usuario_id = None
    token = request.cookies.get("session")
    if token:
        usuario_id = _leer_jwt(token)

    guest_id = request.headers.get("x-guest-id") or None
    return Scope(usuario_id=usuario_id, guest_id=guest_id)


def get_scope(request: Request) -> Scope:
    scope = get_scope_optional(request)
    if scope.usuario_id is None and not scope.guest_id:
        raise HTTPException(401, "Inicia sesión o envía un X-Guest-Id")
    return scope
