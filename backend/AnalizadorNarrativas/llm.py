"""
Integración con Gemini (Google AI Studio, capa gratuita).

Requiere la variable de entorno GEMINI_API_KEY.
Consigue tu key gratis (sin tarjeta) en https://aistudio.google.com/apikey

Nota de privacidad: en la capa gratuita, Google puede usar los textos que envíes
para mejorar sus modelos. Si tus narrativas son muy sensibles/inéditas y eso te
preocupa, la alternativa es correr un modelo local con Ollama (ver README).

---------------------------------------------------------------------------
Géneros literarios
---------------------------------------------------------------------------
La app trabaja con los 5 géneros literarios mayores. Cada uno tiene sus propias
características y por lo tanto su propio criterio de análisis: no tiene sentido
evaluar "diálogo" en un poema lírico, ni "musicalidad del verso" en un ensayo.

Se agrupan por género mayor (no por subgénero) porque los subgéneros de una misma
familia comparten casi los mismos criterios de análisis: un cuento y una novela
se leen igual (solo cambia la extensión); una oda y una elegía se leen igual
(ambas son poesía lírica). El género épico se trata como una variante que combina
narrativa (héroes, hazañas) y verso, ya que es el origen histórico de la
narrativa actual.

GENEROS es el registro central: de aquí sale el selector en la UI, el texto de
extracción (para la story bible) y el esquema + prompt de análisis de cada
género. Para agregar un género nuevo basta con añadir una entrada aquí.
"""
import time
import os
import json
import hashlib
from google import genai
from google.genai import types

import db

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

_client = None

# Se actualiza en cada llamada _pedir_json_cacheado / _pedir_texto_cacheado para que
# quien llamó (App.py) pueda mostrar un indicador de "esto vino de caché, no se
# llamó a la IA" justo después de pedir un análisis/extracción/respuesta de chat.
ultima_fue_cache = False


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


# ===========================================================================
# Configuración por género literario
# ===========================================================================

# Claves que SIEMPRE debe devolver la extracción, sin importar el género.
# Se mantiene un esquema único para no tener que tocar db.py/App.py: lo único
# que cambia entre géneros es qué cuenta como "personaje" y qué cuenta como
# "hecho de continuidad" dentro de ese género (ver los prompts abajo).
_CLAVES_EXTRACCION = ["personajes", "hechos_continuidad", "eventos_clave"]

GENEROS = {
    "narrativo": {
        "label": "📖 Narrativo",
        "descripcion": "Cuenta, en prosa, historias reales o inventadas (cuento, novela, fábula, leyenda, mito, crónica).",
        "unidad": "capítulo",
        "unidad_articulo": "un",
        "entidad_label": "Personajes establecidos",
        "extraccion_instrucciones": """Extraes información de un capítulo de una obra NARRATIVA en prosa (cuento, \
novela, fábula, leyenda, mito o crónica) para mantener una "story bible" (biblia de continuidad).

- "personajes": los personajes que aparecen o son mencionados, con una descripción breve de sus \
rasgos/rol relevantes en este capítulo.
- "hechos_continuidad": datos concretos y verificables (edad, apariencia física, lugar donde está, \
objetos importantes, relaciones familiares) que deben mantenerse consistentes entre capítulos. \
No incluyas interpretaciones subjetivas.
- "eventos_clave": eventos importantes de la trama que ocurren en este capítulo.""",
    },
    "lirico": {
        "label": "🎵 Lírico",
        "descripcion": "Poesía: muestra sentimientos, deseos y voz interior (poema, oda, elegía).",
        "unidad": "poema",
        "unidad_articulo": "un",
        "entidad_label": "Voces, símbolos y motivos establecidos",
        "extraccion_instrucciones": """Extraes información de un poema (obra LÍRICA: poema, oda o elegía) para \
llevar un registro de sus símbolos y motivos a lo largo del poemario.

- "personajes": la voz poética (el "yo lírico"), el destinatario del poema (si lo hay) y cualquier \
entidad o figura personificada relevante, con una descripción breve de cómo se presenta en este poema.
- "hechos_continuidad": símbolos, imágenes o motivos recurrentes y el significado o valor emocional \
que tienen EN ESTE poema (entidad=el símbolo/motivo, atributo="significado" o "asociación emocional", \
valor=qué representa aquí). Esto sirve para detectar si un mismo símbolo cambia de sentido de forma \
inconsistente entre poemas del mismo poemario.
- "eventos_clave": giros o momentos emocionales/temáticos importantes del poema (no eventos de trama, \
ya que la poesía no suele tener trama).""",
    },
    "dramatico": {
        "label": "🎭 Dramático",
        "descripcion": "Presenta un conflicto entre personas mediante diálogo, para ser actuado (tragedia, comedia, drama).",
        "unidad": "escena o acto",
        "unidad_articulo": "una",
        "entidad_label": "Personajes establecidos",
        "extraccion_instrucciones": """Extraes información de una escena o acto de una obra DRAMÁTICA (tragedia, \
comedia o drama, escrita para ser representada en teatro) para mantener una "story bible" de continuidad.

- "personajes": los personajes que aparecen o son mencionados en la escena, con su estado/descripción \
relevante en este punto de la obra (solo lo que se revela por diálogo y acotaciones, ya que no hay narrador).
- "hechos_continuidad": datos concretos de la puesta en escena o la trama (ubicación, objetos en escena, \
relaciones entre personajes, tiempo transcurrido) que deben mantenerse consistentes entre escenas.
- "eventos_clave": giros dramáticos o revelaciones importantes de esta escena/acto.""",
    },
    "didactico": {
        "label": "💡 Didáctico",
        "descripcion": "Busca enseñar, dejar una lección o defender una idea razonada (ensayo, fábula).",
        "unidad": "sección",
        "unidad_articulo": "una",
        "entidad_label": "Conceptos y tesis establecidos",
        "extraccion_instrucciones": """Extraes información de una sección de un texto DIDÁCTICO (ensayo o texto \
argumentativo) para llevar un registro de sus tesis y afirmaciones a lo largo del texto.

- "personajes": los conceptos, términos o tesis clave que se definen o defienden en esta sección \
(nombre=el concepto/tesis, descripcion=cómo se define o argumenta aquí).
- "hechos_continuidad": afirmaciones, datos o cifras concretas citadas como evidencia (entidad=el tema \
o concepto al que se refiere, atributo=qué se afirma sobre él, valor=la afirmación/dato concreto). \
Esto sirve para detectar contradicciones entre lo que se afirma en distintas secciones.
- "eventos_clave": los pasos o giros principales del argumento en esta sección.""",
    },
    "epico": {
        "label": "⚔️ Épico",
        "descripcion": "Narración antigua en verso sobre las hazañas de héroes, dioses o batallas míticas (epopeya).",
        "unidad": "canto",
        "unidad_articulo": "un",
        "entidad_label": "Héroes y figuras establecidas",
        "extraccion_instrucciones": """Extraes información de un canto de una obra ÉPICA (epopeya: narración en \
verso sobre las hazañas de héroes, dioses o batallas míticas) para mantener una "story bible" de continuidad.

- "personajes": héroes, dioses o figuras legendarias que aparecen o son mencionados, con sus rasgos, \
linaje o rol relevante en este canto.
- "hechos_continuidad": datos concretos (linajes, hazañas previas, objetos u armas legendarias, lugares) \
que deben mantenerse consistentes entre cantos.
- "eventos_clave": las hazañas o batallas clave narradas en este canto.""",
    },
}

DEFAULT_GENERO = "narrativo"


def _genero_config(genero: str) -> dict:
    """Devuelve la config del género, o la de narrativo si el valor es desconocido
    (por compatibilidad con obras creadas antes de que existiera este campo, o
    creadas con un valor de género libre que no coincide con ninguna clave)."""
    return GENEROS.get(genero, GENEROS[DEFAULT_GENERO])


# --- Esquemas de ANÁLISIS por género -------------------------------------
# Cada sección tiene: key, label (para la UI), y opcionalmente una lista de
# ejemplos textuales con su propia etiqueta (equivalente al viejo
# "ejemplos_mostrar_no_contar", pero adaptado a lo que interesa en cada género).

ANALYSIS_SECCIONES = {
    "narrativo": [
        {"key": "personajes", "label": "🧑 Personajes"},
        {"key": "trama_y_ritmo", "label": "📈 Trama y ritmo"},
        {
            "key": "prosa_y_estilo", "label": "🖋️ Prosa y estilo",
            "ejemplos_key": "ejemplos_mostrar_no_contar",
            "ejemplos_label": "Ejemplos de 'contar' en vez de 'mostrar'",
        },
        {"key": "dialogo", "label": "💬 Diálogo"},
    ],
    "lirico": [
        {"key": "voz_e_imagen", "label": "🌙 Voz e imagen"},
        {"key": "musicalidad_y_ritmo", "label": "🎶 Musicalidad y ritmo"},
        {"key": "emocion_y_sinceridad", "label": "❤️ Emoción y sinceridad"},
        {
            "key": "lenguaje_y_forma", "label": "🔤 Lenguaje y forma",
            "ejemplos_key": "ejemplos_imagenes_logradas",
            "ejemplos_label": "Imágenes o versos logrados",
        },
    ],
    "dramatico": [
        {
            "key": "dialogo_y_subtexto", "label": "💬 Diálogo y subtexto",
            "ejemplos_key": "ejemplos_subtexto_debil",
            "ejemplos_label": "Diálogos donde el subtexto es débil o inexistente",
        },
        {"key": "conflicto_dramatico", "label": "⚔️ Conflicto dramático"},
        {"key": "direccion_escenica", "label": "🎬 Acotaciones y dirección escénica"},
        {"key": "estructura_y_ritmo", "label": "📈 Estructura y ritmo escénico"},
    ],
    "didactico": [
        {"key": "argumento_y_tesis", "label": "🎯 Argumento y tesis"},
        {"key": "estructura_logica", "label": "🧩 Estructura lógica"},
        {
            "key": "evidencia_y_ejemplos", "label": "📊 Evidencia y ejemplos",
            "ejemplos_key": "ejemplos_afirmaciones_sin_sustento",
            "ejemplos_label": "Afirmaciones sin suficiente sustento",
        },
        {"key": "tono_y_claridad", "label": "🗣️ Tono y claridad"},
    ],
    "epico": [
        {"key": "personajes_heroicos", "label": "🛡️ Héroes y figuras"},
        {"key": "trama_y_hazanas", "label": "⚔️ Trama y hazañas"},
        {
            "key": "forma_y_verso", "label": "📜 Forma y verso",
            "ejemplos_key": "ejemplos_versos_logrados",
            "ejemplos_label": "Versos o pasajes logrados",
        },
        {"key": "tono_y_elevacion", "label": "🏛️ Tono y elevación épica"},
    ],
}

_ANALYSIS_PROMPT_HEADER = {
    "narrativo": "Eres un editor literario experimentado especializado en narrativa en prosa (cuento, "
                 "novela, fábula, leyenda, mito, crónica).",
    "lirico": "Eres un editor literario experimentado especializado en poesía lírica (poema, oda, elegía).",
    "dramatico": "Eres un editor literario/dramaturgista experimentado especializado en obras dramáticas "
                 "escritas para teatro (tragedia, comedia, drama).",
    "didactico": "Eres un editor experimentado especializado en textos didácticos y argumentativos "
                 "(ensayo, fábula con moraleja).",
    "epico": "Eres un editor literario experimentado especializado en poesía épica (epopeyas sobre "
             "héroes, dioses y hazañas míticas).",
}


def _construir_analysis_prompt(genero: str) -> str:
    header = _ANALYSIS_PROMPT_HEADER[genero]
    secciones = ANALYSIS_SECCIONES[genero]

    partes_esquema = []
    for s in secciones:
        campos = ['"fortalezas": "string"', '"problemas": "string"', '"sugerencias": "string"']
        if "ejemplos_key" in s:
            campos.append(f'"{s["ejemplos_key"]}": ["fragmento textual corto del texto que ilustra el problema"]')
        partes_esquema.append(f'  "{s["key"]}": {{\n    ' + ",\n    ".join(campos) + "\n  }")

    esquema_json = "{\n" + ",\n".join(partes_esquema) + ',\n  "resumen_general": "string de 2-3 frases con la evaluación global"\n}'

    return f"""{header} Analizas un fragmento y das retroalimentación honesta, específica y accionable — \
no genérica.

Devuelve ÚNICAMENTE un JSON válido con este esquema exacto:

{esquema_json}

Sé específico: cita fragmentos reales del texto cuando sea relevante, evita frases vagas como \
"podría mejorar" sin decir cómo."""


ANALYSIS_PROMPTS = {genero: _construir_analysis_prompt(genero) for genero in GENEROS}


# ===========================================================================
# Llamadas al modelo
# ===========================================================================

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
        cacheado = db.cache_get(clave)
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
    db.cache_set(clave, response.text)
    ultima_fue_cache = False
    return json.loads(response.text)


def _validar_json(data: dict, claves: list) -> dict:
    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió un objeto JSON.")

    for clave in claves:
        data.setdefault(clave, [])

    return data


def _validar_analisis(data: dict, genero: str) -> dict:
    """Asegura que el JSON de análisis tenga todas las secciones esperadas para
    este género, con sus sub-campos, incluso si el modelo omitió alguna."""
    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió un objeto JSON.")

    for seccion in ANALYSIS_SECCIONES[genero]:
        bloque = data.setdefault(seccion["key"], {})
        if not isinstance(bloque, dict):
            bloque = {}
            data[seccion["key"]] = bloque
        bloque.setdefault("fortalezas", "—")
        bloque.setdefault("problemas", "—")
        bloque.setdefault("sugerencias", "—")
        if "ejemplos_key" in seccion:
            bloque.setdefault(seccion["ejemplos_key"], [])

    data.setdefault("resumen_general", "—")
    return data


def _generar_texto_sin_cache(system_prompt: str, user_content: str, max_output_tokens: int = 1500) -> str:
    for intento in range(3):
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
            return response.text

        except Exception as e:
            if "429" in str(e):
                time.sleep(2 ** intento)
                continue
            raise

    raise RuntimeError("No se pudo obtener respuesta del modelo tras varios reintentos (rate limit).")


def _pedir_texto_cacheado(system_prompt: str, user_content: str, max_output_tokens: int,
                           cache_tag: str, forzar: bool = False) -> str:
    global ultima_fue_cache
    clave = _clave_cache(MODEL, cache_tag, system_prompt, user_content)

    if not forzar:
        cacheado = db.cache_get(clave)
        if cacheado is not None:
            ultima_fue_cache = True
            return cacheado

    texto = _generar_texto_sin_cache(system_prompt, user_content, max_output_tokens)
    db.cache_set(clave, texto)
    ultima_fue_cache = False
    return texto


# ===========================================================================
# Funciones públicas — todas reciben `genero` (una clave de GENEROS) para
# adaptar el prompt. Si se pasa un género desconocido, se usa "narrativo".
# ===========================================================================

def extraer_estructura(texto_capitulo: str, genero: str = DEFAULT_GENERO, forzar: bool = False) -> dict:
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
        system_prompt, texto_capitulo, 2000, cache_tag=f"extraccion:{genero}", forzar=forzar
    )
    return _validar_json(data, _CLAVES_EXTRACCION)


def analizar_capitulo(texto_capitulo: str, story_bible_resumen: str, genero: str = DEFAULT_GENERO,
                       forzar: bool = False) -> dict:
    genero = genero if genero in GENEROS else DEFAULT_GENERO
    system_prompt = ANALYSIS_PROMPTS[genero]
    user_content = (
        f"Contexto de la obra hasta ahora:\n{story_bible_resumen}\n\n"
        f"---\n\nFragmento a analizar:\n\n{texto_capitulo}"
    )
    data = _pedir_json_cacheado(
        system_prompt, user_content, 3000, cache_tag=f"analisis:{genero}", forzar=forzar
    )
    return _validar_analisis(data, genero)


CHAT_SYSTEM_PROMPT = """Eres un asistente que conoces a fondo la obra literaria del usuario porque tienes \
acceso a su story bible (personajes, símbolos, conceptos o elementos clave según el género) y a los \
fragmentos recientes. Responde sus preguntas sobre su propia obra de forma concreta, citando capítulos, \
secciones o elementos específicos cuando sea posible. Ten en cuenta el género literario de la obra al \
responder (por ejemplo, no hables de "trama" si la obra es un poemario lírico sin trama). Si no tienes \
suficiente información para responder con certeza, dilo en vez de inventar datos."""


def preguntar_sobre_historia(pregunta: str, story_bible_resumen: str, capitulos_recientes: str,
                              genero: str = DEFAULT_GENERO, forzar: bool = False) -> str:
    config = _genero_config(genero)
    contexto = (
        f"Género literario de la obra: {config['label']} — {config['descripcion']}\n\n"
        f"Story bible:\n{story_bible_resumen}\n\n"
        f"Fragmentos recientes (texto completo):\n{capitulos_recientes}\n\n"
        f"Pregunta del autor: {pregunta}"
    )
    return _pedir_texto_cacheado(
        CHAT_SYSTEM_PROMPT, contexto, 1500, cache_tag="chat", forzar=forzar
    )