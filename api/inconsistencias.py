from fastapi import Depends, Query, HTTPException

from auth.deps import Scope, get_scope
from main import app, _row_to_dict, EstadoInconsistenciaBody
from repositories.continuidad_repository import actualizar_estado_inconsistencia, list_inconsistencias


@app.get("/api/inconsistencias")
def lista(obra_id: int = Query(...), scope: Scope = Depends(get_scope)):
    return [_row_to_dict(i) for i in list_inconsistencias(obra_id, scope)]


@app.patch("/api/inconsistencias")
def update(body: EstadoInconsistenciaBody, scope: Scope = Depends(get_scope)):
    try:
        actualizar_estado_inconsistencia(body.id, body.estado, scope)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}
