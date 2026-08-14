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
