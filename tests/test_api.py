import llm.cache as llm_cache
from fastapi.testclient import TestClient

import main
from auth.session import _hacer_jwt
from repositories.cache_repository import cache_set
from repositories.user_repository import upsert_usuario_google

client = TestClient(main.app)

G = {"X-Guest-Id": "guest-test"}
GA = {"X-Guest-Id": "guest-a"}
GB = {"X-Guest-Id": "guest-b"}


def _crear_obra(headers=G):
    r = client.post("/api/obras", json={"titulo": "Obra", "genero": "narrativo"}, headers=headers)
    assert r.status_code == 200
    return r.json()["id"]


def _crear_capitulo(oid, analizar=False, headers=G):
    r = client.post(
        "/api/capitulos", json={"obra_id": oid, "texto": "Texto", "analizar": analizar}, headers=headers
    )
    assert r.status_code == 200
    return r.json()["id"]


# ---------- Básicos ----------

def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_generos():
    data = client.get("/api/generos").json()
    assert "narrativo" in data["generos"]
    assert data["default_genero"] == "narrativo"
    assert "pendiente" in data["estados_inconsistencia"]


# ---------- Scope obligatorio ----------

def test_obras_requieren_scope():
    assert client.get("/api/obras").status_code == 401
    assert client.post("/api/obras", json={"titulo": "x"}).status_code == 401


# ---------- Obras ----------

def test_obras_crud():
    oid = _crear_obra()
    obras = client.get("/api/obras", headers=G).json()
    assert len(obras) == 1 and obras[0]["titulo"] == "Obra"
    assert client.get(f"/api/obras/{oid}", headers=G).status_code == 200
    assert client.get("/api/obras/99999", headers=G).status_code == 404


def test_obras_titulo_vacio():
    assert client.post("/api/obras", json={"titulo": "   "}, headers=G).status_code == 400


def test_obras_aislamiento():
    _crear_obra(GA)
    assert client.get("/api/obras", headers=GA).json()[0]["titulo"] == "Obra"
    assert client.get("/api/obras", headers=GB).json() == []
    oid = client.get("/api/obras", headers=GA).json()[0]["id"]
    assert client.get(f"/api/obras/{oid}", headers=GB).status_code == 404


# ---------- Capítulos ----------

def test_capitulos_crud_sin_analizar():
    oid = _crear_obra()
    cid = _crear_capitulo(oid)
    assert client.get(f"/api/capitulos/{cid}", headers=G).status_code == 200
    caps = client.get(f"/api/capitulos?obra_id={oid}", headers=G).json()
    assert len(caps) == 1 and caps[0]["analisis"] is None
    assert client.get(f"/api/meta?obra_id={oid}", headers=G).json()["ultimo_numero"] == 1

    r = client.put(f"/api/capitulos/{cid}", json={"texto": "nuevo"}, headers=G)
    assert r.status_code == 200
    assert client.get(f"/api/capitulos/{cid}", headers=G).json()["texto"] == "nuevo"

    assert client.delete(f"/api/capitulos/{cid}", headers=G).status_code == 200
    assert client.get(f"/api/capitulos/{cid}", headers=G).status_code == 404


def test_capitulos_analizar_con_mock(monkeypatch):
    oid = _crear_obra()

    def fake(obra_id, capitulo_id, numero, texto, genero, scope, forzar=False):
        return {"resumen_general": "ok"}, ["inc1"], True

    monkeypatch.setattr("api.capitulos._analizar_y_guardar", fake)
    r = client.post("/api/capitulos", json={"obra_id": oid, "texto": "cap"}, headers=G)
    assert r.status_code == 200
    data = r.json()
    assert data["analisis"]["resumen_general"] == "ok"
    assert data["nuevasInconsistencias"] == ["inc1"]
    assert data["desdeCache"] is True


def test_capitulos_obra_inexistente():
    r = client.post("/api/capitulos", json={"obra_id": 99999, "texto": "x", "analizar": False}, headers=G)
    assert r.status_code == 404


def test_capitulos_texto_vacio():
    oid = _crear_obra()
    r = client.post("/api/capitulos", json={"obra_id": oid, "texto": "  ", "analizar": False}, headers=G)
    assert r.status_code == 400


# ---------- Personajes ----------

def test_personajes_endpoint():
    from auth.deps import Scope
    from repositories.personaje_repository import upsert_personaje

    oid = _crear_obra()
    cid = _crear_capitulo(oid)
    upsert_personaje(oid, "Ana", "heroína", 1, cid, Scope(guest_id="guest-test"))
    personajes = client.get(f"/api/personajes?obra_id={oid}", headers=G).json()
    assert len(personajes) == 1 and personajes[0]["nombre"] == "Ana"
    assert len(personajes[0]["historial"]) == 1


# ---------- Inconsistencias ----------

def test_inconsistencias_estado_invalido():
    r = client.patch("/api/inconsistencias", json={"id": 1, "estado": "inventado"}, headers=G)
    assert r.status_code == 400


def test_inconsistencias_patch_ok():
    from auth.deps import Scope
    from repositories.capitulo_repository import add_capitulo
    from repositories.continuidad_repository import registrar_hecho
    from repositories.obra_repository import create_obra

    scope = Scope(guest_id="guest-test")
    oid = create_obra("O", "", scope)
    c1 = add_capitulo(oid, 1, "t", "", scope)
    c2 = add_capitulo(oid, 2, "t", "", scope)
    registrar_hecho(oid, "Ana", "edad", "20", c1, 1, scope)
    registrar_hecho(oid, "Ana", "edad", "30", c2, 2, scope)
    inc_id = client.get(f"/api/inconsistencias?obra_id={oid}", headers=G).json()[0]["id"]

    r = client.patch("/api/inconsistencias", json={"id": inc_id, "estado": "intencional"}, headers=G)
    assert r.status_code == 200
    incs = client.get(f"/api/inconsistencias?obra_id={oid}", headers=G).json()
    assert incs[0]["estado"] == "intencional"


# ---------- Chat ----------

def test_chat_endpoint(monkeypatch):
    oid = _crear_obra()

    def fake(pregunta, resumen, recientes, genero, forzar=False,
             usuario_id=None, guest_id=None):
        return "respuesta de prueba"

    monkeypatch.setattr("api.chat.preguntar_sobre_historia", fake)
    llm_cache.ultima_fue_cache = False

    r = client.post("/api/chat", json={"obra_id": oid, "pregunta": "¿quién?"}, headers=G)
    assert r.status_code == 200
    assert r.json()["respuesta"] == "respuesta de prueba"

    chats = client.get(f"/api/chats?obra_id={oid}", headers=G).json()
    assert len(chats) == 1 and chats[0]["pregunta"] == "¿quién?"

    assert client.post("/api/chat", json={"obra_id": oid, "pregunta": "  "}, headers=G).status_code == 400
    assert client.post("/api/chat", json={"obra_id": 99999, "pregunta": "x"}, headers=G).status_code == 404


# ---------- Caché ----------

def test_cache_api():
    cache_set("clave-api", "valor")
    assert client.get("/api/cache").json()["count"] == 1
    assert client.delete("/api/cache").status_code == 200
    assert client.get("/api/cache").json()["count"] == 0


# ---------- Autenticación ----------

def test_auth_me_sin_sesion():
    assert client.get("/auth/me").json() == {"usuario": None}


def test_auth_me_con_sesion():
    u = upsert_usuario_google("sub-1", "a@b.com", "Ana")
    r = client.get("/auth/me", cookies={"session": _hacer_jwt(u["id"])})
    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == "a@b.com"


def test_auth_me_token_invalido():
    r = client.get("/auth/me", cookies={"session": "token-malo"})
    assert r.json() == {"usuario": None}


def test_auth_me_via_authorization_header():
    u = upsert_usuario_google("sub-hdr", "h@x.com", "Hdr")
    token = _hacer_jwt(u["id"])
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == "h@x.com"


def test_auth_me_cookie_tiene_prioridad():
    u_cookie = upsert_usuario_google("sub-cook", "cook@x.com", "Cook")
    u_hdr = upsert_usuario_google("sub-hdr2", "hdr2@x.com", "Hdr2")
    r = client.get(
        "/auth/me",
        cookies={"session": _hacer_jwt(u_cookie["id"])},
        headers={"Authorization": f"Bearer {_hacer_jwt(u_hdr['id'])}"},
    )
    assert r.json()["usuario"]["email"] == "cook@x.com"  # cookie gana


def test_auth_google_ok(monkeypatch):
    import api.auth as auth_mod

    def fake_verify(token, req, client_id):
        return {"sub": "sub-g", "email": "g@x.com", "name": "G", "picture": None}

    monkeypatch.setattr(auth_mod.id_token, "verify_oauth2_token", fake_verify)
    r = client.post("/auth/google", json={"id_token": "fake-token"})
    assert r.status_code == 200
    body = r.json()
    assert body["usuario"]["email"] == "g@x.com"
    assert "session=" in r.headers.get("set-cookie", "")
    assert "token" in body and len(body["token"]) > 20  # JWT devuelto en el body


def test_auth_google_sin_client_id(monkeypatch):
    import api.auth as auth_mod

    monkeypatch.setattr(auth_mod, "GOOGLE_CLIENT_ID", "")
    r = client.post("/auth/google", json={"id_token": "fake-token"})
    assert r.status_code == 500


def test_auth_logout():
    r = client.post("/auth/logout")
    assert r.status_code == 200
    assert "session=" in r.headers.get("set-cookie", "")
