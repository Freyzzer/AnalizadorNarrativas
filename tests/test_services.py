from auth.deps import Scope
from database.connection import get_conn
from repositories.analisis_repository import get_analisis
from repositories.capitulo_repository import add_capitulo
from repositories.obra_repository import create_obra, get_obra
from repositories.personaje_repository import list_personajes
from services import capitulo_service
from services.analysis_service import _validar_analisis, _validar_json
from services.guest_service import purgar_datos_invitados
from services.story_bible_service import story_bible_resumen


def test_validar_json_completa_claves():
    res = _validar_json({"personajes": []}, ["personajes", "hechos_continuidad", "eventos_clave"])
    assert res["hechos_continuidad"] == []
    assert res["eventos_clave"] == []


def test_validar_json_no_dict():
    try:
        _validar_json("no es dict", ["a"])
        assert False, "debió lanzar ValueError"
    except ValueError:
        pass


def test_validar_analisis_completa_secciones():
    data = _validar_analisis({}, "narrativo")
    assert "personajes" in data
    assert "trama_y_ritmo" in data
    assert data["trama_y_ritmo"]["fortalezas"] == "—"
    assert data["trama_y_ritmo"]["problemas"] == "—"
    assert data["trama_y_ritmo"]["sugerencias"] == "—"
    assert data["prosa_y_estilo"]["ejemplos_mostrar_no_contar"] == []
    assert data["resumen_general"] == "—"


def test_validar_analisis_no_dict():
    try:
        _validar_analisis("x", "narrativo")
        assert False
    except ValueError:
        pass


def test_story_bible_vacia(scope_guest):
    oid = create_obra("O", "", scope_guest)
    assert story_bible_resumen(oid, scope_guest) == "Todavía no hay elementos registrados."


def test_story_bible_con_personajes(scope_guest):
    from repositories.personaje_repository import upsert_personaje

    oid = create_obra("O", "", scope_guest)
    cid = add_capitulo(oid, 1, "t", "", scope_guest)
    upsert_personaje(oid, "Ana", "heroína", 1, cid, scope_guest)
    resumen = story_bible_resumen(oid, scope_guest)
    assert "Ana" in resumen and "heroína" in resumen


def test_analizar_y_guardar(monkeypatch, scope_guest):
    import llm.cache as llm_cache

    llm_cache.ultima_fue_cache = False
    oid = create_obra("O", "narrativo", scope_guest)
    cid = add_capitulo(oid, 1, "<p>texto</p>", "", scope_guest)

    monkeypatch.setattr(
        capitulo_service.analysis_service,
        "extraer_estructura",
        lambda *a, **k: {
            "personajes": [{"nombre": "Ana", "descripcion": "heroína"}],
            "hechos_continuidad": [{"entidad": "Ana", "atributo": "edad", "valor": "20"}],
            "eventos_clave": [],
        },
    )
    monkeypatch.setattr(
        capitulo_service.analysis_service,
        "analizar_capitulo",
        lambda *a, **k: {"resumen_general": "ok"},
    )

    analisis, incs, desde_cache = capitulo_service._analizar_y_guardar(
        oid, cid, 1, "<p>texto</p>", "narrativo", scope_guest
    )
    assert analisis["resumen_general"] == "ok"
    assert incs == []
    assert desde_cache is False
    assert get_analisis(cid, scope_guest)["resumen_general"] == "ok"
    assert len(list_personajes(oid, scope_guest)) == 1


def test_purgar_solo_invitados_viejos(scope_guest):
    from repositories.user_repository import upsert_usuario_google

    oid_viejo = create_obra("vieja", "", scope_guest)
    with get_conn() as conn:
        conn.execute("UPDATE obras SET creado_en = ? WHERE id = ?", ("2000-01-01T00:00:00", oid_viejo))
    oid_reciente = create_obra("reciente", "", scope_guest)

    usuario = upsert_usuario_google("sub", "u@x.com")
    scope_user = Scope(usuario_id=usuario["id"])
    oid_usuario = create_obra("del usuario", "", scope_user)

    total = purgar_datos_invitados(dias=1)

    assert total >= 1
    assert get_obra(oid_viejo, scope_guest) is None
    assert get_obra(oid_reciente, scope_guest) is not None
    assert get_obra(oid_usuario, scope_user) is not None
