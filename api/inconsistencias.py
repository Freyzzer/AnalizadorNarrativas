from fastapi import Query, HTTPException


from main import app, _row_to_dict, EstadoInconsistenciaBody
from repositories.continuidad_repository import actualizar_estado_inconsistencia, list_inconsistencias


@app.get("/api/inconsistencias")
def lista(obra_id: int = Query(...)):
    return [_row_to_dict(i) for i in list_inconsistencias(obra_id)]


@app.patch("/api/inconsistencias")
def update(body: EstadoInconsistenciaBody):
    try:
        actualizar_estado_inconsistencia(body.id, body.estado)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}
