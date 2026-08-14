from fastapi import Depends, HTTPException

from auth.deps import Scope, get_scope
from main import _row_to_dict, app, CrearObraBody
from repositories.obra_repository import list_obras, create_obra, get_obra


@app.get("/api/obras")
def lista(scope: Scope = Depends(get_scope)):
    return [_row_to_dict(o) for o in list_obras(scope)]


@app.post("/api/obras")
def create(body: CrearObraBody, scope: Scope = Depends(get_scope)):
    if not body.titulo.strip():
        raise HTTPException(400, "Título requerido")
    obra_id = create_obra(body.titulo.strip(), body.genero, scope)
    return {"id": obra_id}


@app.get("/api/obras/{obra_id}")
def get(obra_id: int, scope: Scope = Depends(get_scope)):
    obra = get_obra(obra_id, scope)
    if not obra:
        raise HTTPException(404, "No encontrada")
    return _row_to_dict(obra)
