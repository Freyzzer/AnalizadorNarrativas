
import llm.cache as llm_cache
from repositories.analisis_repository import save_analisis
from repositories.continuidad_repository import registrar_hecho
from repositories.personaje_repository import upsert_personaje
from services import analysis_service
from services.story_bible_service import story_bible_resumen
from utils.html import html_a_texto


def _analizar_y_guardar(obra_id, capitulo_id, numero_cap, texto, genero, forzar=False):
    """Replica el pipeline de App.py.analizar_y_guardar_capitulo."""
    texto_plano = html_a_texto(texto)
    estructura = analysis_service.extraer_estructura(texto_plano, genero, forzar=forzar)

    for p in estructura.get("personajes", []):
        upsert_personaje(obra_id, p.get("nombre", ""), p.get("descripcion", ""), numero_cap, capitulo_id)

    nuevas_inconsistencias = []
    for h in estructura.get("hechos_continuidad", []):
        resultado = registrar_hecho(
            obra_id, h.get("entidad", ""), h.get("atributo", ""), h.get("valor", ""), capitulo_id, numero_cap
        )
        if resultado:
            nuevas_inconsistencias.append(resultado)

    resumen_bible = story_bible_resumen(obra_id)
    analisis = analysis_service.analizar_capitulo(texto_plano, resumen_bible, genero, forzar=forzar)
    desde_cache = llm_cache.ultima_fue_cache
    save_analisis(capitulo_id, analisis)
    return analisis, nuevas_inconsistencias, desde_cache