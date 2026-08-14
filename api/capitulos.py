from fastapi import Depends, Query, HTTPException

from auth.deps import Scope, get_scope
from config.generos import DEFAULT_GENERO
from main import app, _row_to_dict, CrearCapituloBody, ActualizarCapituloBody
from repositories.analisis_repository import get_analisis
from repositories.capitulo_repository import get_ultimo_numero_capitulo, add_capitulo, get_capitulo, update_capitulo, \
    limpiar_datos_generados_capitulo, delete_capitulo, list_capitulos
from repositories.obra_repository import get_obra
from services.capitulo_service import _analizar_y_guardar


@app.get("/api/capitulos")
def list_capitulo(obra_id: int = Query(...), scope: Scope = Depends(get_scope)):
    caps = list_capitulos(obra_id, scope)
    result = []
    for c in caps:
        d = _row_to_dict(c)
        d["analisis"] = get_analisis(c["id"], scope)
        result.append(d)
    return result


@app.post("/api/capitulos")
def create(body: CrearCapituloBody, scope: Scope = Depends(get_scope)):
    if not body.texto.strip():
        raise HTTPException(400, "obra_id y texto requeridos")
    obra = get_obra(body.obra_id, scope)
    if not obra:
        raise HTTPException(404, "Obra no encontrada")
    numero = body.numero
    if numero is None:
        numero = get_ultimo_numero_capitulo(body.obra_id, scope) + 1

    capitulo_id = add_capitulo(body.obra_id, int(numero), body.texto, body.titulo or "", scope)

    if body.analizar:
        genero = body.genero or obra["genero"] or DEFAULT_GENERO
        try:
            analisis, nuevas_inc, desde_cache = _analizar_y_guardar(
                body.obra_id, capitulo_id, int(numero), body.texto, genero, scope, forzar=False
            )
            return {
                "id": capitulo_id,
                "analisis": analisis,
                "nuevasInconsistencias": nuevas_inc,
                "desdeCache": desde_cache,
            }
        except Exception as e:
            raise HTTPException(500, f"Error al analizar: {e}") from e

    return {"id": capitulo_id}


@app.get("/api/capitulos/{capitulo_id}")
def get(capitulo_id: int, scope: Scope = Depends(get_scope)):
    cap = get_capitulo(capitulo_id, scope)
    if not cap:
        raise HTTPException(404, "No encontrado")
    d = _row_to_dict(cap)
    d["analisis"] = get_analisis(capitulo_id, scope)
    return d


@app.put("/api/capitulos/{capitulo_id}")
def update(capitulo_id: int, body: ActualizarCapituloBody, scope: Scope = Depends(get_scope)):
    cap = get_capitulo(capitulo_id, scope)
    if not cap:
        raise HTTPException(404, "No encontrado")

    if body.texto is not None:
        update_capitulo(capitulo_id, body.texto, body.titulo if body.titulo is not None else (cap["titulo"] or ""),
                        numero=body.numero, scope=scope)

    if body.reanalizar:
        try:
            limpiar_datos_generados_capitulo(capitulo_id, scope)
            cap = get_capitulo(capitulo_id, scope)
            obra_id = body.obra_id or cap["obra_id"]
            numero = body.numero or cap["numero"]
            texto = body.texto if body.texto is not None else cap["texto"]
            obra = get_obra(obra_id, scope)
            genero = body.genero or (obra["genero"] if obra else None) or DEFAULT_GENERO
            analisis, nuevas_inc, desde_cache = _analizar_y_guardar(
                obra_id, capitulo_id, int(numero), texto, genero, scope, forzar=True
            )
            return {
                "analisis": analisis,
                "nuevasInconsistencias": nuevas_inc,
                "desdeCache": desde_cache,
            }
        except Exception as e:
            raise HTTPException(500, f"Error al re-analizar: {e}") from e

    return {"ok": True}


@app.delete("/api/capitulos/{capitulo_id}")
def delete(capitulo_id: int, scope: Scope = Depends(get_scope)):
    delete_capitulo(capitulo_id, scope)
    return {"ok": True}
