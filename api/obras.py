from fastapi import HTTPException

from main import _row_to_dict, app, CrearObraBody
from repositories.obra_repository import list_obras, create_obra, get_obra


@app.get("/api/obras")
def lista():
    return [_row_to_dict(o) for o in list_obras()]


@app.post("/api/obras")
def create(body: CrearObraBody):
    if not body.titulo.strip():
        raise HTTPException(400, "Título requerido")
    obra_id = create_obra(body.titulo.strip(), body.genero)
    return {"id": obra_id}


@app.get("/api/obras/{obra_id}")
def get(obra_id: int):
    obra = get_obra(obra_id)
    if not obra:
        raise HTTPException(404, "No encontrada")
    return _row_to_dict(obra)