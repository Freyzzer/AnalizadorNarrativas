from config.generos import ANALYSIS_SECCIONES, GENEROS

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