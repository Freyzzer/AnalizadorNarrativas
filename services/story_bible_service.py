from auth.deps import Scope
from repositories.personaje_repository import list_personajes


def story_bible_resumen(obra_id: int, scope: Scope) -> str:
    """Genera un resumen compacto en texto de la story bible, para usar como contexto en prompts."""
    personajes = list_personajes(obra_id, scope)
    if not personajes:
        return "Todavía no hay elementos registrados."
    lineas = ["Elementos establecidos hasta ahora:"]
    for p in personajes:
        lineas.append(f"- {p['nombre']}: {p['descripcion_actual']}")
    return "\n".join(lineas)
