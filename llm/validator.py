from config.generos import ANALYSIS_SECCIONES


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