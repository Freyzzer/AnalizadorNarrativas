from database.connection import get_conn, USE_POSTGRES

# Postgres no soporta AUTOINCREMENT: usa GENERATED ... IDENTITY.
PK_CLAUSE = (
    "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
    if USE_POSTGRES
    else "INTEGER PRIMARY KEY AUTOINCREMENT"
)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS usuarios (
    id {PK_CLAUSE},
    google_sub TEXT UNIQUE,
    email TEXT,
    nombre TEXT,
    avatar TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS obras (
    id {PK_CLAUSE},
    titulo TEXT NOT NULL,
    genero TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS capitulos (
    id {PK_CLAUSE},
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    numero INTEGER NOT NULL,
    titulo TEXT,
    texto TEXT NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS personajes (
    id {PK_CLAUSE},
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    nombre TEXT NOT NULL,
    descripcion_actual TEXT,
    primera_aparicion_cap INTEGER,
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT,
    UNIQUE(obra_id, nombre)
);

CREATE TABLE IF NOT EXISTS personaje_historial (
    id {PK_CLAUSE},
    personaje_id INTEGER NOT NULL REFERENCES personajes(id),
    capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
    capitulo_numero INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS hechos_continuidad (
    id {PK_CLAUSE},
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    entidad TEXT NOT NULL,
    atributo TEXT NOT NULL,
    valor TEXT NOT NULL,
    capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS inconsistencias (
    id {PK_CLAUSE},
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
    entidad TEXT,
    atributo TEXT,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    capitulo_anterior_numero INTEGER,
    descripcion TEXT,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS analisis (
    id {PK_CLAUSE},
    capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
    contenido_json TEXT NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS chats (
    id {PK_CLAUSE},
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    guest_id TEXT,
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    creado_en TEXT
);

CREATE TABLE IF NOT EXISTS cache_llm (
    id {PK_CLAUSE},
    clave TEXT NOT NULL UNIQUE,
    respuesta TEXT NOT NULL,
    creado_en TEXT
);

CREATE INDEX IF NOT EXISTS idx_obras_owner ON obras(usuario_id, guest_id);
CREATE INDEX IF NOT EXISTS idx_capitulos_obra ON capitulos(obra_id);
CREATE INDEX IF NOT EXISTS idx_personajes_obra ON personajes(obra_id);
CREATE INDEX IF NOT EXISTS idx_chats_obra ON chats(obra_id);
CREATE INDEX IF NOT EXISTS idx_inconsistencias_obra ON inconsistencias(obra_id);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(_SCHEMA)
