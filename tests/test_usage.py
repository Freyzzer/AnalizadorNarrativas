from repositories.usage_repository import usage_check, usage_increment, usage_stats, LIMIT_DIARIO


def test_usage_check_crea_registro():
    restantes = usage_check(usuario_id=100, guest_id=None)
    assert restantes == LIMIT_DIARIO


def test_usage_increment():
    usage_increment(usuario_id=101, guest_id=None)
    usage_increment(usuario_id=101, guest_id=None)
    restantes = usage_check(usuario_id=101, guest_id=None)
    assert restantes == LIMIT_DIARIO - 2


def test_usage_stats():
    usage_increment(usuario_id=102, guest_id=None)
    stats = usage_stats(usuario_id=102, guest_id=None)
    assert stats["usados"] == 1
    assert stats["restantes"] == LIMIT_DIARIO - 1
    assert stats["limite"] == LIMIT_DIARIO


def test_usage_guest_separado():
    usage_increment(usuario_id=None, guest_id="g1")
    usage_increment(usuario_id=None, guest_id="g1")
    usage_increment(usuario_id=None, guest_id="g2")
    assert usage_check(usuario_id=None, guest_id="g1") == LIMIT_DIARIO - 2
    assert usage_check(usuario_id=None, guest_id="g2") == LIMIT_DIARIO - 1


def test_usage_limite():
    for _ in range(LIMIT_DIARIO):
        usage_increment(usuario_id=103, guest_id=None)
    restantes = usage_check(usuario_id=103, guest_id=None)
    assert restantes == 0
