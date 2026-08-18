from repositories.capitulo_repository import add_capitulo
from repositories.continuidad_repository import (
    ESTADOS_INCONSISTENCIA,
    actualizar_estado_inconsistencia,
    list_inconsistencias,
    registrar_hecho,
)
from repositories.obra_repository import create_obra


def _obra_y_capitulos(scope, n=2):
    oid = create_obra("Obra", "", scope)
    ids = []
    for i in range(1, n + 1):
        ids.append(add_capitulo(oid, i, f"texto {i}", f"Cap {i}", scope))
    return oid, ids


def test_primer_hecho_sin_inconsistencia(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 1)
    desc = registrar_hecho(oid, "Ana", "edad", "20", ids[0], 1, scope_guest)
    assert desc is None
    assert list_inconsistencias(oid, scope_guest) == []


def test_valor_repetido_sin_inconsistencia(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    registrar_hecho(oid, "Ana", "edad", "20", ids[0], 1, scope_guest)
    assert registrar_hecho(oid, "Ana", "edad", "20", ids[1], 2, scope_guest) is None
    assert list_inconsistencias(oid, scope_guest) == []


def test_valor_distinto_genera_inconsistencia(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    registrar_hecho(oid, "Ana", "edad", "20", ids[0], 1, scope_guest)
    desc = registrar_hecho(oid, "Ana", "edad", "30", ids[1], 2, scope_guest)
    assert desc is not None and "20" in desc and "30" in desc
    incs = list_inconsistencias(oid, scope_guest)
    assert len(incs) == 1
    assert incs[0]["valor_anterior"] == "20"
    assert incs[0]["valor_nuevo"] == "30"
    assert incs[0]["estado"] == "pendiente"
    assert incs[0]["capitulo_anterior_numero"] == 1


def test_listar_y_actualizar_estado(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    registrar_hecho(oid, "Ana", "edad", "20", ids[0], 1, scope_guest)
    registrar_hecho(oid, "Ana", "edad", "30", ids[1], 2, scope_guest)
    inc = list_inconsistencias(oid, scope_guest)[0]

    assert len(list_inconsistencias(oid, scope_guest, estado="pendiente")) == 1
    assert list_inconsistencias(oid, scope_guest, estado="resuelta") == []

    actualizar_estado_inconsistencia(inc["id"], "resuelta", scope_guest)
    assert list_inconsistencias(oid, scope_guest, estado="resuelta")[0]["id"] == inc["id"]
    assert list_inconsistencias(oid, scope_guest, estado="pendiente") == []


def test_estado_invalido_lanza_error(scope_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    registrar_hecho(oid, "Ana", "edad", "20", ids[0], 1, scope_guest)
    registrar_hecho(oid, "Ana", "edad", "30", ids[1], 2, scope_guest)
    inc = list_inconsistencias(oid, scope_guest)[0]
    try:
        actualizar_estado_inconsistencia(inc["id"], "inventado", scope_guest)
        assert False, "debió lanzar ValueError"
    except ValueError:
        pass


def test_estados_validos():
    assert ESTADOS_INCONSISTENCIA == ["pendiente", "intencional", "resuelta"]


def test_inconsistencias_aisladas_por_dueño(scope_guest, scope_otro_guest):
    oid, ids = _obra_y_capitulos(scope_guest, 2)
    registrar_hecho(oid, "Ana", "edad", "20", ids[0], 1, scope_guest)
    registrar_hecho(oid, "Ana", "edad", "30", ids[1], 2, scope_guest)
    assert list_inconsistencias(oid, scope_otro_guest) == []
