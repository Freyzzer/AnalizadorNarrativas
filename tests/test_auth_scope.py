from auth.deps import Scope


def test_owner_sql_usuario():
    sql, params = Scope(usuario_id=5).owner_sql()
    assert "usuario_id = ?" in sql and "guest_id = ?" in sql
    assert params == [5, None]


def test_owner_sql_guest():
    sql, params = Scope(guest_id="g-1").owner_sql()
    assert params == [None, "g-1"]


def test_owner_sql_alias():
    sql, params = Scope(usuario_id=1, guest_id="g").owner_sql("ph")
    assert "ph.usuario_id" in sql and "ph.guest_id" in sql
    assert params == [1, "g"]


def test_owner_sql_sin_dueno_no_matcheria():
    sql, params = Scope().owner_sql()
    assert params == [None, None]
