import os
import tempfile

# Aislar los tests: base de datos SQLite temporal propia (nunca narrativa.db),
# sin DATABASE_URL (Postgres se prueba aparte) y sin redes al LLM.
os.environ["DB_PATH"] = os.path.join(
    tempfile.gettempdir(), f"analizador_test_{os.getpid()}.db"
)
os.environ.pop("DATABASE_URL", None)
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("COOKIE_SECURE", None)

import pytest

from auth.deps import Scope
from database.connection import get_conn
from database.migrations import init_db

TABLAS = [
    "chats",
    "analisis",
    "hechos_continuidad",
    "inconsistencias",
    "personaje_historial",
    "personajes",
    "capitulos",
    "obras",
    "usuarios",
    "cache_llm",
]


@pytest.fixture(autouse=True)
def _bd_limpia():
    """Esquema creado y tablas vacías antes de cada test."""
    init_db()
    with get_conn() as conn:
        for tabla in TABLAS:
            conn.execute(f"DELETE FROM {tabla}")
    yield


@pytest.fixture
def scope_guest() -> Scope:
    return Scope(guest_id="guest-test")


@pytest.fixture
def scope_otro_guest() -> Scope:
    return Scope(guest_id="guest-otro")


@pytest.fixture
def scope_usuario() -> Scope:
    return Scope(usuario_id=10)
