import time

from google.genai import types

from llm.client import get_client, MODEL


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