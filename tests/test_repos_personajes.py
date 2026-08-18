from repositories.capitulo_repository import add_capitulo
from repositories.obra_repository import create_obra
from repositories.personaje_repository import (
    _recalcular_descripcion_actual,
    get_historial_personaje,
    list_personajes,
    upsert_personaje,
)


def _obra_y_capitulos(scope, n=2):
    oid = create_obra("Obra", "", scope)
    ids = []
    for i in range(1, n + 1):
        ids.append(add_capitulo(oid, i, f"texto {i}", f"Cap {i}", scope))
    return oid, ids


def test_upsert_crea_personaje_e_historial(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 1)
    pid = upsert_personaje(oid, "Ana", "heroína valiente", 1, ids[0], scope_guest)
    assert isinstance(pid, int)
    personajes = list_personajes(oid, scope_guest)
    assert len(personajes) == 1
    assert personajes[0]["descripcion_actual"] == "heroína valiente"
    assert personajes[0]["primera_aparicion_cap"] == 1
    hist = get_historial_personaje(pid, scope_guest)
    assert len(hist) == 1


def test_upsert_acumula_historial_sin_duplicar_personaje(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    pid1 = upsert_personaje(oid, "Ana", "v1", 1, ids[0], scope_guest)
    pid2 = upsert_personaje(oid, "Ana", "v2", 2, ids[1], scope_guest)
    assert pid1 == pid2
    assert len(list_personajes(oid, scope_guest)) == 1
    assert list_personajes(oid, scope_guest)[0]["descripcion_actual"] == "v2"
    assert len(get_historial_personaje(pid1, scope_guest)) == 2


def test_historial_incluye_titulo_y_orden(scope_guest):
    oid = create_obra("Obra", "", scope_guest)
    c1 = add_capitulo(oid, 3, "texto", "Tres", scope_guest)
    c2 = add_capitulo(oid, 1, "texto", "Uno", scope_guest)
    upsert_personaje(oid, "Ana", "v1", 3, c1, scope_guest)
    upsert_personaje(oid, "Ana", "v2", 1, c2, scope_guest)
    hist = get_historial_personaje(
        list_personajes(oid, scope_guest)[0]["id"], scope_guest
    )
    nums = [h["capitulo_numero"] for h in hist]
    assert nums == [1, 3]
    assert hist[0]["capitulo_titulo"] == "Uno"
    assert hist[1]["capitulo_titulo"] == "Tres"


def test_recalcular_descripcion_actual(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    pid = upsert_personaje(oid, "Ana", "v1", 1, ids[0], scope_guest)
    upsert_personaje(oid, "Ana", "v2", 2, ids[1], scope_guest)

    from database.connection import get_conn

    with get_conn() as conn:
        conn.execute("DELETE FROM personaje_historial WHERE personaje_id = ?", (pid,))

    _recalcular_descripcion_actual(pid, scope_guest)
    personajes = list_personajes(oid, scope_guest)
    assert "sin descripción" in personajes[0]["descripcion_actual"]


def test_personajes_aislados_por_dueño(scope_guest, scope_otro_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 1)
    upsert_personaje(oid, "Ana", "v1", 1, ids[0], scope_guest)
    assert list_personajes(oid, scope_otro_guest) == []
