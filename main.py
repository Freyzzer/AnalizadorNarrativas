"""
API FastAPI del analizador de narrativas.
Envuelve db.py y llm_antiguo.py para que el front Next.js consuma el backend en Python.

Corre con:
  uvicorn main:app --reload --port 8000

Requiere: GEMINI_API_KEY en el entorno.
Opcionales: GOOGLE_CLIENT_ID, JWT_SECRET, ALLOWED_ORIGINS, COOKIE_SECURE, ...
"""

from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.migrations import init_db
from services.guest_service import purgar_datos_invitados


def _bucle_purga_invitados():
    intervalo_h = int(os.getenv("GUEST_PURGE_INTERVAL_HORAS", "6"))
    purgar_datos_invitados()
    while True:
        time.sleep(intervalo_h * 3600)
        try:
            purgar_datos_invitados()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_bucle_purga_invitados, daemon=True).start()
    yield


init_db()

app = FastAPI(title="Analizador de narrativas", version="2.0.0", lifespan=lifespan)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # necesario para la cookie HttpOnly de sesión
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Schemas ----------

class CrearObraBody(BaseModel):
    titulo: str
    genero: str = "narrativo"


class CrearCapituloBody(BaseModel):
    obra_id: int
    numero: Optional[int] = None
    texto: str
    titulo: str = ""
    genero: Optional[str] = None
    analizar: bool = True


class ActualizarCapituloBody(BaseModel):
    texto: Optional[str] = None
    titulo: Optional[str] = None
    reanalizar: bool = False
    obra_id: Optional[int] = None
    numero: Optional[int] = None
    genero: Optional[str] = None


class EstadoInconsistenciaBody(BaseModel):
    id: int
    estado: str


class ChatBody(BaseModel):
    obra_id: int
    pregunta: str
    genero: Optional[str] = None


class GoogleLoginBody(BaseModel):
    id_token: str


def _row_to_dict(row) -> dict[str, Any]:
    if row is None:
        return {}
    return dict(row)


# Registrar routers (los decoradores de api/* se ejecutan al importarlos)
from api import obras, capitulos, personajes, inconsistencias, generos, chat, cache, auth, chats  # noqa: F401
