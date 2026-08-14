from fastapi import Depends, Query

from auth.deps import Scope, get_scope
from main import app, _row_to_dict
from repositories.personaje_repository import list_personajes, get_historial_personaje


@app.get("/api/personajes")
def lista(obra_id: int = Query(...), scope: Scope = Depends(get_scope)):
    personajes = list_personajes(obra_id, scope)
    result = []
    for p in personajes:
        d = _row_to_dict(p)
        hist = get_historial_personaje(p["id"], scope)
        d["historial"] = [_row_to_dict(h) for h in hist]
        result.append(d)
    return result
