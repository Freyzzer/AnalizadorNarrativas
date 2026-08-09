"""
API FastAPI del analizador de narrativas.
Envuelve db.py y llm_antiguo.py para que el front Next.js consuma el backend en Python.

Corre con:
  uvicorn main:app --reload --port 8000

Requiere: GEMINI_API_KEY en el entorno.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from database.migrations import init_db

init_db()

app = FastAPI(title="Analizador de narrativas", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción limita a tu dominio Next.js
    allow_credentials=False,
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


def _row_to_dict(row) -> dict[str, Any]:
    if row is None:
        return {}
    return dict(row)

# Registrar routers (los decoradores de api/* se ejecutan al importarlos)
from api import obras, capitulos, personajes, inconsistencias, generos, chat, cache  # noqa: F401


