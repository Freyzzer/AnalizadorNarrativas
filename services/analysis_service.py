from config.generos import DEFAULT_GENERO, _genero_config, _CLAVES_EXTRACCION, GENEROS
from llm.cache import _pedir_json_cacheado, _pedir_texto_cacheado
from llm.prompts import ANALYSIS_PROMPTS
from llm.validator import _validar_json, _validar_analisis


def extraer_estructura(texto_capitulo: str, genero: str = DEFAULT_GENERO, forzar: bool = False,
                       usuario_id: int | None = None, guest_id: str | None = None) -> dict:
    config = _genero_config(genero)
    system_prompt = config["extraccion_instrucciones"] + """

Devuelve ÚNICAMENTE un JSON válido con este esquema exacto:

{
  "personajes": [
    {"nombre": "string", "descripcion": "string breve"}
  ],
  "hechos_continuidad": [
    {"entidad": "string", "atributo": "string", "valor": "string"}
  ],
  "eventos_clave": [
    {"descripcion": "string breve"}
  ]
}

Si no hay datos de un tipo, devuelve una lista vacía para esa clave."""

    data = _pedir_json_cacheado(
        system_prompt, texto_capitulo, 2000, cache_tag=f"extraccion:{genero}",
        forzar=forzar, usuario_id=usuario_id, guest_id=guest_id,
    )
    return _validar_json(data, _CLAVES_EXTRACCION)


def analizar_capitulo(texto_capitulo: str, story_bible_resumen: str, genero: str = DEFAULT_GENERO,
                       forzar: bool = False, usuario_id: int | None = None,
                       guest_id: str | None = None) -> dict:
    genero = genero if genero in GENEROS else DEFAULT_GENERO
    system_prompt = ANALYSIS_PROMPTS[genero]
    user_content = (
        f"Contexto de la obra hasta ahora:\n{story_bible_resumen}\n\n"
        f"---\n\nFragmento a analizar:\n\n{texto_capitulo}"
    )
    data = _pedir_json_cacheado(
        system_prompt, user_content, 4000, cache_tag=f"analisis:{genero}",
        forzar=forzar, usuario_id=usuario_id, guest_id=guest_id,
    )
    return _validar_analisis(data, genero)


CHAT_SYSTEM_PROMPT = """Eres un asistente que conoces a fondo la obra literaria del usuario porque tienes \
acceso a su story bible (personajes, símbolos, conceptos o elementos clave según el género) y a los \
fragmentos recientes. Responde sus preguntas sobre su propia obra de forma concreta, citando capítulos, \
secciones o elementos específicos cuando sea posible. Ten en cuenta el género literario de la obra al \
responder (por ejemplo, no hables de "trama" si la obra es un poemario lírico sin trama). Si no tienes \
suficiente información para responder con certeza, dilo en vez de inventar datos."""


def preguntar_sobre_historia(pregunta: str, story_bible_resumen: str, capitulos_recientes: str,
                              genero: str = DEFAULT_GENERO, forzar: bool = False,
                              usuario_id: int | None = None, guest_id: str | None = None) -> str:
    config = _genero_config(genero)
    contexto = (
        f"Género literario de la obra: {config['label']} — {config['descripcion']}\n\n"
        f"Story bible:\n{story_bible_resumen}\n\n"
        f"Fragmentos recientes (texto completo):\n{capitulos_recientes}\n\n"
        f"Pregunta del autor: {pregunta}"
    )
    return _pedir_texto_cacheado(
        CHAT_SYSTEM_PROMPT, contexto, 1500, cache_tag="chat", forzar=forzar,
        usuario_id=usuario_id, guest_id=guest_id,
    )