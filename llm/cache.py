import hashlib
import json
import logging
import os
import re
import time

from google.genai import types
from google.genai.errors import APIError

from llm.client import get_client
from llm.gemini_service import _generar_texto_sin_cache
from repositories.cache_repository import cache_get, cache_set, cache_delete
from repositories.usage_repository import usage_check, usage_increment, LIMIT_DIARIO

log = logging.getLogger(__name__)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

ultima_fue_cache: bool = False

# --- Cooldown global (Capa 3) ---
# Mínimo 6s entre llamadas → 10 RPM, igual al tier gratuito de Gemini Flash.
MIN_INTERVALO = float(os.getenv("LLM_MIN_INTERVAL", "6.0"))
_ultimo_llamada: float = 0.0


def _cooldown():
    """Espera si es necesario para respetar el cooldown global entre llamadas."""
    global _ultimo_llamada
    ahora = time.monotonic()
    espera = MIN_INTERVALO - (ahora - _ultimo_llamada)
    if espera > 0:
        log.info("Cooldown global: esperando %.1fs", espera)
        time.sleep(espera)
    _ultimo_llamada = time.monotonic()


def _clave_cache(*partes: str) -> str:
    """Hash estable de todas las partes que determinan la respuesta: si cambia
    cualquiera de ellas (el texto de entrada, el prompt del género, el modelo...),
    cambia la clave y ya no hay hit de caché."""
    m = hashlib.sha256()
    for p in partes:
        m.update(p.encode("utf-8"))
        m.update(b"\x1f")
    return m.hexdigest()


# --- Reparación de JSON truncado ---

def _reparar_json(texto: str) -> str:
    """Intenta reparar JSON truncado o malformado típico de LLMs."""
    t = texto.rstrip()

    # 1) Cerrar strings sin terminar
    en_string = False
    ultima_apertura = -1
    i = 0
    while i < len(t):
        c = t[i]
        if c == '"' and (i == 0 or t[i - 1] != '\\'):
            if en_string:
                en_string = False
            else:
                en_string = True
                ultima_apertura = i
        i += 1

    if en_string:
        t = t + '"'

    # 2) Cerrar llaves/corchetes abiertos
    stack = []
    for c in t:
        if c in '{[':
            stack.append(c)
        elif c == '}' and stack and stack[-1] == '{':
            stack.pop()
        elif c == ']' and stack and stack[-1] == '[':
            stack.pop()

    while stack:
        abierto = stack.pop()
        t += '}' if abierto == '{' else ']'

    # 3) Limpiar trailing commas
    t = re.sub(r",\s*([}\]])", r"\1", t)

    return t


def _parsear_json(texto: str) -> dict:
    """Intenta parsear el JSON; si falla, intenta repararlo."""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        log.warning("JSON inválido de Gemini, intentando reparar: %s", texto[:200])
        reparado = _reparar_json(texto)
        return json.loads(reparado)


# --- Llamada raw a Gemini con cooldown + backoff (Capa 2 + 3) ---

_MAX_REINTENTOS = 3


def _llamar_gemini(system_prompt: str, user_content: str, max_output_tokens: int,
                    response_mime_type: str = "application/json") -> str:
    """Llama a Gemini respetando cooldown global y reintentando en 429."""
    for intento in range(_MAX_REINTENTOS):
        _cooldown()
        try:
            client = get_client()
            response = client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_output_tokens,
                    response_mime_type=response_mime_type,
                    temperature=0.4 if response_mime_type == "application/json" else 0.5,
                ),
            )
            return response.text
        except APIError as e:
            if e.code == 429:
                espera = 2 ** intento
                log.warning("429 de Gemini (intento %d/%d), esperando %ds",
                            intento + 1, _MAX_REINTENTOS, espera)
                time.sleep(espera)
                continue
            raise
    raise RuntimeError(
        "Rate limit de Gemini agotado tras varios reintentos. "
        "Intentá de nuevo en unos minutos."
    )


# --- Funciones públicas ---

def _pedir_json_cacheado(system_prompt: str, user_content: str, max_output_tokens: int,
                          cache_tag: str, forzar: bool = False,
                          usuario_id: int | None = None, guest_id: str | None = None) -> dict:
    global ultima_fue_cache

    # Capa 1: límite diario por usuario
    if usuario_id or guest_id:
        restantes = usage_check(usuario_id, guest_id)
        if restantes <= 0:
            raise RuntimeError(
                f"Alcanzaste tu límite diario de uso ({LIMIT_DIARIO} llamadas). "
                "Intentá de nuevo mañana."
            )

    clave = _clave_cache(MODEL, cache_tag, system_prompt, user_content)

    if not forzar:
        cacheado = cache_get(clave)
        if cacheado is not None:
            ultima_fue_cache = True
            return _parsear_json(cacheado)

    # Capa 1: incrementar contador SOLO si vamos a hacer llamada real
    if usuario_id or guest_id:
        usage_increment(usuario_id, guest_id)

    raw = _llamar_gemini(system_prompt, user_content, max_output_tokens,
                         response_mime_type="application/json")

    cache_set(clave, raw)
    ultima_fue_cache = False

    try:
        return _parsear_json(raw)
    except json.JSONDecodeError:
        log.warning("JSON reparado falló, reintentando con forzar=True")
        cache_delete(clave)
        return _pedir_json_cacheado(
            system_prompt, user_content, max_output_tokens,
            cache_tag, forzar=True,
            usuario_id=usuario_id, guest_id=guest_id,
        )


def _pedir_texto_cacheado(system_prompt: str, user_content: str, max_output_tokens: int,
                            cache_tag: str, forzar: bool = False,
                            usuario_id: int | None = None, guest_id: str | None = None) -> str:
    global ultima_fue_cache

    # Capa 1
    if usuario_id or guest_id:
        restantes = usage_check(usuario_id, guest_id)
        if restantes <= 0:
            raise RuntimeError(
                f"Alcanzaste tu límite diario de uso ({LIMIT_DIARIO} llamadas). "
                "Intentá de nuevo mañana."
            )

    clave = _clave_cache(MODEL, cache_tag, system_prompt, user_content)

    if not forzar:
        cacheado = cache_get(clave)
        if cacheado is not None:
            ultima_fue_cache = True
            return cacheado

    # Capa 1: incrementar
    if usuario_id or guest_id:
        usage_increment(usuario_id, guest_id)

    texto = _llamar_gemini(system_prompt, user_content, max_output_tokens,
                           response_mime_type="text/plain")

    cache_set(clave, texto)
    ultima_fue_cache = False
    return texto
