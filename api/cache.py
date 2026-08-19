from fastapi import Depends, Query

from auth.deps import Scope, get_scope
from main import app
from repositories.capitulo_repository import get_ultimo_numero_capitulo
from repositories.cache_repository import cache_clear, cache_count
from repositories.usage_repository import usage_stats

@app.get("/api/cache")
def cache_count_api():
    return {"count": cache_count()}


@app.delete("/api/cache")
def cache_clear_api():
    cache_clear()
    return {"ok": True}


@app.get("/api/meta")
def meta(obra_id: int = Query(...), scope: Scope = Depends(get_scope)):
    return {"ultimo_numero": get_ultimo_numero_capitulo(obra_id, scope)}


@app.get("/api/usage")
def usage(scope: Scope = Depends(get_scope)):
    return usage_stats(scope.usuario_id, scope.guest_id)


@app.get("/health")
def health():
    return {"status": "ok"}
