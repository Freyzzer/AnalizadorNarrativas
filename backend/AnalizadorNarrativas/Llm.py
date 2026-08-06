"""
Integración con Gemini (Google AI Studio, capa gratuita).

Requiere la variable de entorno GEMINI_API_KEY.
Consigue tu key gratis (sin tarjeta) en https://aistudio.google.com/apikey

Nota de privacidad: en la capa gratuita, Google puede usar los textos que envíes
para mejorar sus modelos. Si tus narrativas son muy sensibles/inéditas y eso te
preocupa, la alternativa es correr un modelo local con Ollama (ver README).
"""
import time
import os
import json
from google import genai
from google.genai import types

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta la variable de entorno GEMINI_API_KEY. "
                "Consigue una gratis en https://aistudio.google.com/apikey "
                "y configúrala antes de correr la app (ver README)."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _generar_json(system_prompt: str, user_content: str, max_output_tokens: int = 2000) -> dict:
    """Pide una respuesta en JSON puro (Gemini fuerza el formato con response_mime_type)."""
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

    data = json.loads(response.text)

    return _validar_json(data,[
        "personajes",
        "hechos_continuidad",
        "eventos_clave"
    ])


def _validar_json(data: dict, claves: list[str]) -> dict:
    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió un objeto JSON.")

    for clave in claves:
        data.setdefault(clave, [])

    return data


def _generar_texto(system_prompt: str, user_content: str, max_output_tokens: int = 1500) -> str:
    for intento in  range(3):
        try:
            client = get_client()
            response = client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_output_tokens,
                    temperature=0.5,
                ),
            )
            return json.loads(response.text)


        except Exception as e:

            if "429" in str(e):
                time.sleep(2 ** intento)

                continue

            raise



EXTRACTION_SYSTEM_PROMPT = """Eres un asistente que extrae información estructurada de capítulos \
de novelas para mantener una "story bible" (biblia de continuidad).

Devuelve ÚNICAMENTE un JSON válido con este esquema exacto:

{
  "personajes": [
    {"nombre": "string", "descripcion": "string breve de rasgos/rol relevantes en este capítulo"}
  ],
  "hechos_continuidad": [
    {"entidad": "nombre del personaje o lugar", "atributo": "ej: color_ojos, edad, ubicacion_actual, objeto_clave", "valor": "string"}
  ],
  "eventos_clave": [
    {"descripcion": "string breve del evento"}
  ]
}

Solo incluye hechos de continuidad que sean datos concretos y verificables (edad, apariencia física, \
lugar donde está, objetos importantes, relaciones familiares), no interpretaciones subjetivas. \
Si no hay datos de un tipo, devuelve una lista vacía para esa clave."""


def extraer_estructura(texto_capitulo: str) -> dict:
    return _generar_json(EXTRACTION_SYSTEM_PROMPT, texto_capitulo, max_output_tokens=2000)


ANALYSIS_SYSTEM_PROMPT = """Eres un editor literario experimentado. Analizas un capítulo de una \
narrativa y das retroalimentación honesta, específica y accionable — no genérica.

Devuelve ÚNICAMENTE un JSON válido con este esquema exacto:

{
  "personajes": {
    "fortalezas": "string",
    "problemas": "string",
    "sugerencias": "string"
  },
  "trama_y_ritmo": {
    "fortalezas": "string",
    "problemas": "string",
    "sugerencias": "string"
  },
  "prosa_y_estilo": {
    "fortalezas": "string",
    "problemas": "string",
    "sugerencias": "string",
    "ejemplos_mostrar_no_contar": ["fragmento textual corto del capítulo donde se cuenta en vez de mostrar"]
  },
  "dialogo": {
    "fortalezas": "string",
    "problemas": "string",
    "sugerencias": "string"
  },
  "resumen_general": "string de 2-3 frases con la evaluación global"
}

Sé específico: cita fragmentos reales del texto cuando sea relevante, evita frases vagas como \
"podría mejorar" sin decir cómo."""


def analizar_capitulo(texto_capitulo: str, story_bible_resumen: str) -> dict:
    user_content = (
        f"Contexto de la historia hasta ahora (story bible):\n{story_bible_resumen}\n\n"
        f"---\n\nCapítulo a analizar:\n\n{texto_capitulo}"
    )
    return _generar_json(ANALYSIS_SYSTEM_PROMPT, user_content, max_output_tokens=3000)


CHAT_SYSTEM_PROMPT = """Eres un asistente que conoces a fondo la narrativa del usuario porque tienes \
acceso a su story bible (personajes, hechos de continuidad) y a los capítulos recientes. \
Responde sus preguntas sobre su propia historia de forma concreta, citando capítulos o personajes \
específicos cuando sea posible. Si no tienes suficiente información para responder con certeza, dilo \
en vez de inventar datos."""


def preguntar_sobre_historia(pregunta: str, story_bible_resumen: str, capitulos_recientes: str) -> str:
    contexto = (
        f"Story bible:\n{story_bible_resumen}\n\n"
        f"Capítulos recientes (texto completo):\n{capitulos_recientes}\n\n"
        f"Pregunta del autor: {pregunta}"
    )
    return _generar_texto(CHAT_SYSTEM_PROMPT, contexto, max_output_tokens=1500)