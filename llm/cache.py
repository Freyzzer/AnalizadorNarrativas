import hashlib
import json
import os

from google.genai import types

from llm.client import get_client
from llm.gemini_service import _generar_texto_sin_cache
from repositories.cache_repository import cache_get, cache_set

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
def _clave_cache(*partes: str) -> str:
    """Hash estable de todas las partes que determinan la respuesta: si cambia
    cualquiera de ellas (el texto de entrada, el prompt del género, el modelo...),
    cambia la clave y ya no hay hit de caché."""
    m = hashlib.sha256()
    for p in partes:
        m.update(p.encode("utf-8"))
        m.update(b"\x1f")  # separador de campo, para no mezclar "ab"+"c" con "a"+"bc"
    return m.hexdigest()


def _pedir_json_cacheado(system_prompt: str, user_content: str, max_output_tokens: int,
                          cache_tag: str, forzar: bool = False) -> dict:
    """Pide una respuesta en JSON puro (Gemini fuerza el formato con response_mime_type),
    usando la caché en SQLite salvo que forzar=True. `cache_tag` distingue distintos
    tipos de llamada (ej. 'extraccion:lirico' vs 'analisis:lirico') para no mezclar
    cachés de flujos distintos aunque el texto de entrada coincida por casualidad."""
    global ultima_fue_cache
    clave = _clave_cache(MODEL, cache_tag, system_prompt, user_content)

    if not forzar:
        cacheado = cache_get(clave)
        if cacheado is not None:
            ultima_fue_cache = True
            return json.loads(cacheado)

    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )
    cache_set(clave, response.text)
    ultima_fue_cache = False
    return json.loads(response.text)

def _pedir_texto_cacheado(system_prompt: str, user_content: str, max_output_tokens: int,
                           cache_tag: str, forzar: bool = False) -> str:
    global ultima_fue_cache
    clave = _clave_cache(MODEL, cache_tag, system_prompt, user_content)

    if not forzar:
        cacheado = cache_get(clave)
        if cacheado is not None:
            ultima_fue_cache = True
            return cacheado

    texto = _generar_texto_sin_cache(system_prompt, user_content, max_output_tokens)
    cache_set(clave, texto)
    ultima_fue_cache = False
    return texto