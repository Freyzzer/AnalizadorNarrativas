from fastapi import HTTPException

from config.generos import GENEROS, DEFAULT_GENERO
from llm import cache as llm_cache
from main import ChatBody, app
from repositories.capitulo_repository import list_capitulos
from repositories.obra_repository import get_obra
from services.analysis_service import preguntar_sobre_historia
from services.story_bible_service import story_bible_resumen
from utils.html import html_a_texto


@app.post("/api/chat")
def chat(body: ChatBody):
    if not body.pregunta.strip():
        raise HTTPException(400, "obra_id y pregunta requeridos")

    obra = get_obra(body.obra_id)
    if not obra:
        raise HTTPException(404, "Obra no encontrada")

    genero = body.genero or obra["genero"] or DEFAULT_GENERO
    resumen_bible = story_bible_resumen(body.obra_id)
    capitulos = list_capitulos(body.obra_id)
    config = GENEROS.get(genero, GENEROS[DEFAULT_GENERO])
    unidad = config["unidad"]
    recientes = "\n\n".join(
        f'{unidad.capitalize()} {c["numero"]}:\n{html_a_texto(c["texto"])}' for c in capitulos[-3:]
    )
    try:
        respuesta = preguntar_sobre_historia(
            body.pregunta, resumen_bible, recientes, genero
        )
        return {"respuesta": respuesta, "desde_cache": llm_cache.ultima_fue_cache}
    except Exception as e:
        raise HTTPException(500, str(e)) from e