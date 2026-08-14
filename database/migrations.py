from database.connection import get_conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS obras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                genero TEXT,
                creado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS capitulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                numero INTEGER NOT NULL,
                titulo TEXT,
                texto TEXT NOT NULL,
                creado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS personajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                nombre TEXT NOT NULL,
                descripcion_actual TEXT,
                primera_aparicion_cap INTEGER,
                UNIQUE(obra_id, nombre)
            );

            CREATE TABLE IF NOT EXISTS personaje_historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personaje_id INTEGER NOT NULL REFERENCES personajes(id),
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
                capitulo_numero INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                creado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS hechos_continuidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                entidad TEXT NOT NULL,
                atributo TEXT NOT NULL,
                valor TEXT NOT NULL,
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id)
            );

            CREATE TABLE IF NOT EXISTS inconsistencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id INTEGER NOT NULL REFERENCES obras(id),
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
                entidad TEXT,
                atributo TEXT,
                valor_anterior TEXT,
                valor_nuevo TEXT,
                capitulo_anterior_numero INTEGER,
                descripcion TEXT,
                estado TEXT NOT NULL DEFAULT 'pendiente'
            );

            CREATE TABLE IF NOT EXISTS analisis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
                contenido_json TEXT NOT NULL,
                creado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS cache_llm (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave TEXT NOT NULL UNIQUE,
                respuesta TEXT NOT NULL,
                creado_en TEXT
            );
            """
        )
        _migrar_esquema(conn)


def _migrar_esquema(conn):
    """
    Agrega columnas nuevas a bases de datos creadas con una versión anterior del
    esquema. CREATE TABLE IF NOT EXISTS no modifica tablas que ya existen, así que
    los cambios de esquema posteriores al primer lanzamiento se manejan aquí.
    """
    columnas_inconsistencias = [
        r["name"] for r in conn.execute("PRAGMA table_info(inconsistencias)").fetchall()
    ]
    if "estado" not in columnas_inconsistencias:
        conn.execute(
            "ALTER TABLE inconsistencias ADD COLUMN estado TEXT NOT NULL DEFAULT 'pendiente'"
        )
