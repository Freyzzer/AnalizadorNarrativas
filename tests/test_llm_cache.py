import llm.cache as llm_cache
from repositories.cache_repository import cache_set


def test_clave_cache_determinista():
    assert llm_cache._clave_cache("a", "b", "c") == llm_cache._clave_cache("a", "b", "c")


def test_clave_cache_distingue_entradas():
    assert llm_cache._clave_cache("a", "b", "c") != llm_cache._clave_cache("a", "b", "d")
    # evita colisiones tipo "ab"+"c" vs "a"+"bc"
    assert llm_cache._clave_cache("ab", "c") != llm_cache._clave_cache("a", "bc")


def test_pedir_json_cacheado_hit(monkeypatch):
    sp, uc, tag = "system", "usuario", "extraccion:narrativo"
    clave = llm_cache._clave_cache(llm_cache.MODEL, tag, sp, uc)
    cache_set(clave, '{"personajes": []}')

    monkeypatch.setattr(llm_cache, "ultima_fue_cache", False)
    res = llm_cache._pedir_json_cacheado(sp, uc, 2000, tag)
    assert res == {"personajes": []}
    assert llm_cache.ultima_fue_cache is True


def test_pedir_json_cacheado_miss_sin_api_key():
    # forzar=True ignora la caché y get_client() falla sin GEMINI_API_KEY
    try:
        llm_cache._pedir_json_cacheado("sp", "uc", 2000, "tag", forzar=True)
        assert False, "debió lanzar RuntimeError por falta de GEMINI_API_KEY"
    except RuntimeError as e:
        assert "GEMINI_API_KEY" in str(e)


def test_pedir_texto_cacheado_hit(monkeypatch):
    sp, uc, tag = "system", "usuario", "chat"
    clave = llm_cache._clave_cache(llm_cache.MODEL, tag, sp, uc)
    cache_set(clave, "respuesta cacheada")

    monkeypatch.setattr(llm_cache, "ultima_fue_cache", False)
    res = llm_cache._pedir_texto_cacheado(sp, uc, 1500, tag)
    assert res == "respuesta cacheada"
    assert llm_cache.ultima_fue_cache is True


# ---------- _reparar_json ----------

def test_reparar_json_objeto_cerrado():
    assert llm_cache._parsear_json('{"a": 1}') == {"a": 1}


def test_reparar_json_trailing_comma():
    assert llm_cache._parsear_json('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_reparar_json_llave_faltante():
    assert llm_cache._parsear_json('{"a": 1') == {"a": 1}


def test_reparar_json_lista_incompleta():
    assert llm_cache._parsear_json('{"items": [1, 2,') == {"items": [1, 2]}


def test_reparar_json_string_truncado():
    r = llm_cache._reparar_json('{"msg": "hola mundo')
    assert llm_cache._parsear_json(r) == {"msg": "hola mundo"}


def test_reparar_json_profundo():
    raw = '{"a": {"b": [1, 2'
    assert llm_cache._parsear_json(raw) == {"a": {"b": [1, 2]}}


# ---------- Capa 1: límite diario ----------

def test_limite_diario_bloquea():
    """Si el usuario agotó su cuota, _pedir_json_cacheado lanza RuntimeError."""
    from repositories.usage_repository import usage_increment

    for _ in range(200):
        usage_increment(usuario_id=999, guest_id=None)

    try:
        llm_cache._pedir_json_cacheado(
            "sp", "uc", 2000, "tag", forzar=True,
            usuario_id=999, guest_id=None,
        )
        assert False, "Debió lanzar RuntimeError por límite diario"
    except RuntimeError as e:
        assert "límite diario" in str(e)


def test_limite_diario_cache_hit_no_cuenta():
    """Si hay cache hit, NO se incrementa el contador de uso."""
    from repositories.usage_repository import usage_check
    sp, uc, tag = "sys", "usr", "extraccion:narrativo"
    clave = llm_cache._clave_cache(llm_cache.MODEL, tag, sp, uc)
    cache_set(clave, '{"personajes": []}')

    antes = usage_check(usuario_id=888, guest_id=None)
    llm_cache._pedir_json_cacheado(sp, uc, 2000, tag, usuario_id=888, guest_id=None)
    despues = usage_check(usuario_id=888, guest_id=None)
    assert despues == antes  # no se incrementó


# ---------- Capa 2: backoff en 429 ----------

def test_backoff_429(monkeypatch):
    """Si Gemini devuelve 429, reintenta con backoff."""
    from google.genai.errors import ClientError
    from unittest.mock import MagicMock

    call_count = {"n": 0}

    def fake_generate_content(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ClientError(429, {"error": {"message": "rate limit", "status": "RESOURCE_EXHAUSTED"}})
        resp = MagicMock()
        resp.text = '{"ok": true}'
        return resp

    fake_client = MagicMock()
    fake_client.models.generate_content = fake_generate_content
    monkeypatch.setattr(llm_cache, "get_client", lambda: fake_client)
    monkeypatch.setattr(llm_cache, "_cooldown", lambda: None)  # saltar cooldown en test

    res = llm_cache._llamar_gemini("sp", "uc", 2000)
    assert res == '{"ok": true}'
    assert call_count["n"] == 3


def test_backoff_429_agotado(monkeypatch):
    """Si 429 persiste tras 3 intentos, lanza RuntimeError."""
    from google.genai.errors import ClientError
    from unittest.mock import MagicMock

    def fake_generate_content(**kwargs):
        raise ClientError(429, {"error": {"message": "rate limit", "status": "RESOURCE_EXHAUSTED"}})

    fake_client = MagicMock()
    fake_client.models.generate_content = fake_generate_content
    monkeypatch.setattr(llm_cache, "get_client", lambda: fake_client)
    monkeypatch.setattr(llm_cache, "_cooldown", lambda: None)

    try:
        llm_cache._llamar_gemini("sp", "uc", 2000)
        assert False, "Debió lanzar RuntimeError"
    except RuntimeError as e:
        assert "Rate limit" in str(e)


# ---------- Capa 3: cooldown global ----------

def test_cooldown_espera():
    """Si se llama dos veces seguidas, la segunda espera."""
    import time
    llm_cache._ultimo_llamada = time.monotonic()
    antes = time.monotonic()
    llm_cache._cooldown()
    despues = time.monotonic()
    assert despues - antes >= llm_cache.MIN_INTERVALO - 0.1
