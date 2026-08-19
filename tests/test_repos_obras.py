from repositories.obra_repository import create_obra, list_obras, get_obra


def test_crear_y_listar_obra(scope_guest):
    oid = create_obra("Mi novela", "narrativo", scope_guest)
    assert isinstance(oid, int)
    obras = list_obras(scope_guest)
    assert len(obras) == 1
    assert obras[0]["titulo"] == "Mi novela"
    assert obras[0]["genero"] == "narrativo"
    assert obras[0]["guest_id"] == "guest-test"


def test_listar_obras_con_multiples_duenos(scope_guest, scope_otro_guest):
    create_obra("De A", "", scope_guest)
    create_obra("De B", "", scope_otro_guest)
    assert len(list_obras(scope_guest)) == 1
    assert list_obras(scope_guest)[0]["titulo"] == "De A"
    assert len(list_obras(scope_otro_guest)) == 1


def test_get_obra_respeta_dueño(scope_guest, scope_otro_guest):
    oid = create_obra("Privada", "", scope_guest)
    assert get_obra(oid, scope_guest) is not None
    assert get_obra(oid, scope_otro_guest) is None
    assert get_obra(99999, scope_guest) is None


def test_usuario_crea_y_ve_sus_obras(scope_otro_guest):
    from repositories.user_repository import upsert_usuario_google
    from auth.deps import Scope

    usuario = upsert_usuario_google("sub-x", "u@x.com", "User")
    scope_usuario = Scope(usuario_id=usuario["id"])
    oid = create_obra("Del usuario", "", scope_usuario)
    obras = list_obras(scope_usuario)
    assert len(obras) == 1 and obras[0]["usuario_id"] == usuario["id"]
    assert list_obras(scope_otro_guest) == []
    assert get_obra(oid, scope_otro_guest) is None


def test_usuario_con_guest_id_no_contamina():
    """Si un usuario logueado envía X-Guest-Id, la obra NO se puede ver como invitado."""
    from repositories.user_repository import upsert_usuario_google
    from auth.deps import Scope

    usuario = upsert_usuario_google("sub-y", "y@x.com", "Y")
    # Scope con AMBOS:模拟 el caso real donde el frontend envía X-Guest-Id + cookie
    scope_both = Scope(usuario_id=usuario["id"], guest_id="g-leak")
    oid = create_obra("No leak", "", scope_both)

    # El usuario la ve
    assert get_obra(oid, scope_both) is not None

    # Un invitado con ese mismo guest_id NO la ve (owner_insert puso guest_id=None)
    scope_guest_only = Scope(guest_id="g-leak")
    assert get_obra(oid, scope_guest_only) is None
    assert list_obras(scope_guest_only) == []
