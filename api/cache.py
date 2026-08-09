from fastapi import Query

from main import app
from repositories.capitulo_repository import get_ultimo_numero_capitulo
from repositories.cache_repository import cache_clear, cache_count

@app.get("/api/cache")
def cache_count_api():
    return {"count": cache_count()}


@app.delete("/api/cache")
def cache_clear_api():
    cache_clear()
    return {"ok": True}


@app.get("/api/meta")
def meta(obra_id: int = Query(...)):
    return {"ultimo_numero": get_ultimo_numero_capitulo(obra_id)}


@app.get("/health")
def health():
    return {"status": "ok"}
