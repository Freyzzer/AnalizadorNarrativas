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


# ---------- owner_insert (aislamiento de datos) ----------

def test_owner_insert_usuario_solo():
    uid, gid = Scope(usuario_id=5, guest_id="g-1").owner_insert()
    assert uid == 5 and gid is None  # guest_id se descarta


def test_owner_insert_guest_solo():
    uid, gid = Scope(guest_id="g-1").owner_insert()
    assert uid is None and gid == "g-1"


def test_owner_insert_sin_dueno():
    uid, gid = Scope().owner_insert()
    assert uid is None and gid is None


def test_owner_insert_nunca_ambos():
    """Aunque el scope tenga ambos, owner_insert nunca retorna ambos."""
    uid, gid = Scope(usuario_id=3, guest_id="g-9").owner_insert()
    assert (uid is None) != (gid is None)  # exactamente uno es None
