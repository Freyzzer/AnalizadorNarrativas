from repositories.cache_repository import cache_clear, cache_count, cache_get, cache_set
from repositories.chat_repository import delete_chat, list_chats, save_chat
from repositories.obra_repository import create_obra
from repositories.user_repository import get_usuario_by_id, upsert_usuario_google


def test_upsert_usuario_crea_y_actualiza():
    u = upsert_usuario_google("sub-123", "a@b.com", "Ana", "http://avatar")
    assert u["google_sub"] == "sub-123"
    assert u["email"] == "a@b.com"
    assert u["nombre"] == "Ana"
    uid = u["id"]
    assert get_usuario_by_id(uid)["email"] == "a@b.com"

    u2 = upsert_usuario_google("sub-123", "nuevo@b.com", "Ana 2", None)
    assert u2["id"] == uid  # mismo usuario, no duplica
    assert u2["email"] == "nuevo@b.com"
    assert u2["nombre"] == "Ana 2"
    assert get_usuario_by_id(uid)["nombre"] == "Ana 2"


def test_get_usuario_inexistente():
    assert get_usuario_by_id(999) is None


def test_chat_save_list_delete(scope_guest, scope_otro_guest):
    oid = create_obra("Obra", "", scope_guest)
    save_chat(oid, "P1", "R1", scope_guest)
    save_chat(oid, "P2", "R2", scope_guest)

    chats = list_chats(oid, scope_guest)
    assert [c["pregunta"] for c in chats] == ["P1", "P2"]
    assert list_chats(oid, scope_otro_guest) == []

    delete_chat(chats[0]["id"], scope_guest)
    assert [c["pregunta"] for c in list_chats(oid, scope_guest)] == ["P2"]


def test_cache_set_get_upsert_y_clear():
    assert cache_count() == 0
    cache_set("k", "v1")
    assert cache_get("k") == "v1"
    cache_set("k", "v2")  # upsert sobre la misma clave
    assert cache_get("k") == "v2"
    assert cache_count() == 1
    assert cache_get("inexistente") is None
    cache_clear()
    assert cache_count() == 0
