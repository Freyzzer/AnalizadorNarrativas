import os
from google import genai

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