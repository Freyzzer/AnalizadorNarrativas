from repositories.analisis_repository import save_analisis
from repositories.capitulo_repository import (
    add_capitulo,
    delete_capitulo,
    get_capitulo,
    get_ultimo_numero_capitulo,
    list_capitulos,
    update_capitulo,
)
from repositories.continuidad_repository import registrar_hecho
from repositories.obra_repository import create_obra
from repositories.personaje_repository import upsert_personaje


def _obra_y_capitulo(scope):
    oid = create_obra("Obra", "", scope)
    cid = add_capitulo(oid, 1, "Texto 1", "Cap 1", scope)
    return oid, cid


def test_add_y_get_capitulo(scope_guest):
    oid, cid = _obra_y_capitulo(scope_guest)
    cap = get_capitulo(cid, scope_guest)
    assert cap["obra_id"] == oid
    assert cap["numero"] == 1
    assert cap["titulo"] == "Cap 1"
    assert cap["texto"] == "Texto 1"
    assert get_capitulo(99999, scope_guest) is None


def test_lista_ordenada_y_ultimo_numero(scope_guest):
    oid = create_obra("Obra", "", scope_guest)
    add_capitulo(oid, 1, "a", "", scope_guest)
    add_capitulo(oid, 3, "c", "", scope_guest)
    add_capitulo(oid, 2, "b", "", scope_guest)
    nums = [c["numero"] for c in list_capitulos(oid, scope_guest)]
    assert nums == [1, 2, 3]
    assert get_ultimo_numero_capitulo(oid, scope_guest) == 3
    assert get_ultimo_numero_capitulo(oid + 9999, scope_guest) == 0


def test_update_capitulo(scope_guest):
    oid, cid = _obra_y_capitulo(scope_guest)
    update_capitulo(cid, "nuevo texto", "nuevo titulo", numero=5, scope=scope_guest)
    cap = get_capitulo(cid, scope_guest)
    assert cap["texto"] == "nuevo texto"
    assert cap["titulo"] == "nuevo titulo"
    assert cap["numero"] == 5
    update_capitulo(cid, "solo texto", scope=scope_guest)
    assert get_capitulo(cid, scope_guest)["numero"] == 5


def test_eliminar_capitulo_limpia_datos_generados(scope_guest):
    oid, cid = _obra_y_capitulo(scope_guest)
    upsert_personaje(oid, "Ana", "heroína", 1, cid, scope_guest)
    registrar_hecho(oid, "Ana", "edad", "20", cid, 1, scope_guest)
    save_analisis(cid, {"resumen_general": "ok"}, scope_guest)

    delete_capitulo(cid, scope_guest)

    assert get_capitulo(cid, scope_guest) is None
    assert list_capitulos(oid, scope_guest) == []
    with __import__("database.connection", fromlist=["get_conn"]).get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM analisis").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM hechos_continuidad").fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM personaje_historial").fetchone()["n"] == 0


def test_capitulos_aislados_por_dueño(scope_guest, scope_otro_guest):
    oid, cid = _obra_y_capitulo(scope_guest)
    assert get_capitulo(cid, scope_otro_guest) is None
    assert list_capitulos(oid, scope_otro_guest) == []
