from config.generos import GENEROS, ANALYSIS_SECCIONES, DEFAULT_GENERO
from main import app
from repositories.continuidad_repository import ESTADOS_INCONSISTENCIA


@app.get("/api/generos")
def get_generos_meta():
    generos_meta = {}
    for clave, config in GENEROS.items():
        generos_meta[clave] = {
            "label": config["label"],
            "descripcion": config["descripcion"],
            "unidad": config["unidad"],
            "unidad_articulo": config["unidad_articulo"],
            "entidad_label": config["entidad_label"],
            "secciones": ANALYSIS_SECCIONES[clave],
        }
    return {
        "generos": generos_meta,
        "default_genero": DEFAULT_GENERO,
        "estados_inconsistencia": ESTADOS_INCONSISTENCIA,
    }
