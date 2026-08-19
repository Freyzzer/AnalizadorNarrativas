from database.connection import get_conn

tables = ["obras", "capitulos", "personajes", "personaje_historial", "hechos_continuidad", "inconsistencias", "analisis", "chats"]
with get_conn() as conn:
    for t in tables:
        row = conn.execute(f"SELECT COUNT(*) as n FROM {t} WHERE usuario_id IS NOT NULL AND guest_id IS NOT NULL").fetchone()
        n = row["n"]
        print(f"  {t}: {n} filas con ambos" if n else f"  {t}: limpio")
