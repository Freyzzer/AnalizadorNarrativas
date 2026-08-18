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
