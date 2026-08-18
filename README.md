<div align="center">

# 📚 Cuaderno de Obra · Analizador de Narrativas con IA

**Una webapp para escritores que mantiene sola la "biblia de continuidad" de tu obra y detecta inconsistencias mientras escribes.**

<sub>Backend · FastAPI · Gemini · PostgreSQL/SQLite &nbsp;|&nbsp; Frontend · Next.js · React 19 · TipTap</sub>

</div>

---

## 🪶 ¿Qué hace?

Cuando escribes una novela larga es fácil que Ana pase de tener 20 años en el capítulo 3 a 30 en el capítulo 12, o que un símbolo cambie de significado entre poemas. Este proyecto **lee cada capítulo con IA**, extrae personajes, hechos de continuidad y eventos clave, y los guarda en una *story bible* viva. Luego:

- **Detecta inconsistencias** automáticamente ("En el capítulo 3 se estableció que Ana → edad = 20, pero en el capítulo 12 aparece como 30").
- Genera un **análisis editorial por capítulo** adaptado al género literario (trama, prosa, diálogo, ritmo…).
- Permite **conversar con tu propia obra** (chat con contexto de la story bible y los últimos fragmentos).
- Guarda todo bajo tu cuenta de Google o como **invitado** sin registro.

Está pensado para **5 géneros** y adapta su extracción y su análisis a cada uno:

| Género | Unidad | Qué vigila la continuidad |
|---|---|---|
| 📖 Narrativo | capítulo | personajes y datos concretos (edad, apariencia, objetos…) |
| 🎵 Lírico | poema | símbolos, motivos y su significado emocional |
| 🎭 Dramático | escena o acto | puesta en escena y datos revelados por diálogo/acotaciones |
| 💡 Didáctico | sección | tesis y afirmaciones/cifras citadas |
| ⚔️ Épico | canto | linajes, hazañas y objetos legendarios |

## ✨ Características

- 🤖 **Análisis por capítulo con Google Gemini** (JSON forzado y validado): personajes, hechos de continuidad, eventos clave + informe editorial por género.
- 🗂️ **Story bible automática**: historial por personaje con la descripción más reciente y su primera aparición.
- ⚠️ **Detección de inconsistencias** con estados (`pendiente` / `intencional` / `resuelta`).
- 💬 **Chat contextual** con la obra (story bible + últimos capítulos).
- 🔑 **Autenticación con Google** (OAuth + cookie HttpOnly + JWT) **y modo invitado** (X-Guest-Id del navegador, sin registro).
- 🧠 **Caché de respuestas del LLM** por hash determinista (mismo texto + prompt = misma respuesta, sin re-llamar a la API → ahorro de costes y latencia).
- 🔄 **Doble base de datos**: SQLite para desarrollo, **PostgreSQL (Neon) en producción**, con una capa de conexión que traduce `?`→`%s` y `AUTOINCREMENT`→`IDENTITY` (los repos no cambian).
- 🧹 **Limpieza automática** de datos de invitados caducados (fondo, configurable).
- 📝 **Editor de texto enriquecido** (TipTap) que se convierte a texto plano para el LLM.
- 🧪 **77 tests** sobre repos, servicios, auth, caché LLM y la API completa.

## 🏗️ Arquitectura

```
Navegador (Next.js)
   │  /api/*  y  /auth/*  (mismo origen vía rewrites de Vercel)
   ▼
FastAPI (Railway / Docker)
   ├── api/        → rutas HTTP (obras, capítulos, personajes, inconsistencias, chat, auth…)
   ├── services/   → lógica: pipeline de análisis, story bible, purga de invitados
   ├── repositories/ → acceso a datos (todas usan `?` y funcionan en SQLite y Postgres)
   ├── llm/        → cliente Gemini, prompts, validación de JSON, caché
   ├── auth/       → Scope (usuario/invitado), JWT + cookie
   └── database/   → connection.py (doble driver) + migrations.py
                    ├── SQLite (dev)  ──►  narrativa.db
                    └── PostgreSQL    ──►  Neon (prod)
```

**Flujo al guardar un capítulo** (`services/capitulo_service.py`):

1. HTML del editor → texto plano (`utils/html.py`).
2. `extraer_estructura()` → personajes, hechos de continuidad, eventos clave.
3. Cada personaje se guarda con su historial (`upsert_personaje`).
4. Cada hecho se registra; si contradice uno anterior → se crea una **inconsistencia**.
5. `analizar_capitulo()` genera el informe editorial con la story bible como contexto.
6. Todo se guarda y se devuelve al front (con `desdeCache` para saber si vino de caché).

## 📁 Estructura del backend

```
├── main.py                 # App FastAPI, CORS, arranque
├── api/                    # Rutas HTTP
├── auth/                   # deps.py (Scope) y session.py (JWT/cookies)
├── config/generos.py       # Definición de los 5 géneros y sus esquemas de análisis
├── database/               # connection.py (SQLite/Postgres) y migrations.py
├── llm/                    # client, prompts, validator, cache
├── repositories/           # Capa de datos
├── services/               # analysis, capitulo, story_bible, guest
├── utils/                  # html_a_texto
└── tests/                  # Suite pytest (77 tests)
```

## 🚀 Empezar a usar

### Requisitos
- Python 3.12+
- Node.js 20+ (para el frontend)
- Una [API key de Gemini](https://aistudio.google.com/apikey) (gratis)

### 1. Backend

```bash
git clone https://github.com/Freyzzer/AnalizadorNarrativas.git
cd AnalizadorNarrativas

python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# Copia las variables y completa GEMINI_API_KEY
cp .env.example .env

uvicorn main:app --reload --port 8000
```

API en `http://localhost:8000` · Docs interactivos en `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend            # repositorio separado (Next.js)
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Abre `http://localhost:3000`.

### 3. Tests

```bash
pip install -r requirements.txt   # incluye pytest
pytest
```

> Los tests usan una base SQLite temporal aislada (`analizador_test_*.db`) y **no** llaman a Gemini: el LLM se mockea.

## 🔐 Variables de entorno

**Backend** (`.env`): mira [`.env.example`](.env.example)

| Variable | Uso |
|---|---|
| `GEMINI_API_KEY` | API key de Gemini (**requerida**) |
| `DATABASE_URL` | Cadena Postgres (ej. Neon). Sin ella → SQLite local |
| `GOOGLE_CLIENT_ID` | OAuth de Google (mismo valor que en el frontend) |
| `JWT_SECRET` | Secreto para firmar sesiones (genera uno: `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ALLOWED_ORIGINS` | Orígenes CORS separados por coma |
| `COOKIE_SECURE` | `true` en producción (requiere HTTPS) |
| `COOKIE_SAMESITE` | `lax` con rewrites del mismo origen |
| `GUEST_TTL_DIAS` / `GUEST_PURGE_INTERVAL_HORAS` | Limpieza de datos de invitados |
| `GEMINI_MODEL` | Modelo (por defecto `gemini-3.6-flash`) |

**Frontend** (`.env.local`): mira el `.env.local.example` del proyecto Next.js

| Variable | Uso |
|---|---|
| `NEXT_PUBLIC_API_URL` | Solo en dev local (`http://localhost:8000`). En Vercel **no** se define: los rewrites de `vercel.json` enrutan `/api/*` y `/auth/*` al backend |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Mismo valor que `GOOGLE_CLIENT_ID` del backend |

## 🔌 API (resumen)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/generos` | Metadatos de géneros y esquemas de análisis |
| `GET` / `POST` | `/api/obras` | Listar / crear obras |
| `GET` | `/api/obras/{id}` | Detalle de obra |
| `GET` / `POST` | `/api/capitulos` | Listar / crear (y analizar) capítulos |
| `GET` / `PUT` / `DELETE` | `/api/capitulos/{id}` | Detalle / editar / eliminar |
| `GET` | `/api/meta?obra_id=` | Último número de capítulo |
| `GET` | `/api/personajes?obra_id=` | Personajes con historial |
| `GET` | `/api/inconsistencias?obra_id=` | Inconsistencias de la obra |
| `PATCH` | `/api/inconsistencias` | Cambiar estado de una inconsistencia |
| `POST` | `/api/chat` | Preguntar sobre la obra |
| `GET` | `/api/chats?obra_id=` | Historial de chats |
| `GET` / `DELETE` | `/api/cache` | Estado / vaciado de la caché del LLM |
| `POST` | `/auth/google` | Login con Google (id_token) → cookie de sesión |
| `POST` | `/auth/logout` | Cerrar sesión |
| `GET` | `/auth/me` | Usuario actual o `null` |

**Identidad**: las rutas de datos exigen `X-Guest-Id` (invitado) o la cookie `session` (usuario autenticado). Los datos de invitados y usuarios están **aislados por dueño** (filtros `Scope` en cada consulta).

## ☁️ Deploy

**Backend** — Railway (Dockerfile incluido):
```dockerfile
# El contenedor expone 8000; en Railway el target port se define en el panel.
# Si quieres respetar el $PORT dinámico, cambia el CMD a:
# CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
```
Configura en Railway las variables de `.env.example` (`DATABASE_URL` de Neon, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `JWT_SECRET`, `COOKIE_SECURE=true`).

**Frontend** — Vercel (Next.js):
- Deja `NEXT_PUBLIC_API_URL` **sin definir**.
- Define `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.
- `vercel.json` ya enruta `/api/:path*` y `/auth/:path*` a la URL del backend, manteniendo el **mismo origen** para que la cookie HttpOnly funcione.

**Google OAuth**: crea un cliente OAuth tipo *Web app* en [Google Cloud Console](https://console.cloud.google.com) con URI de redirección `https://TU-FRONTEND.vercel.app` y `http://localhost:3000`, y usa el mismo Client ID en backend y frontend.

## 🛣️ Roadmap / ideas

- Migraciones versionadas de esquema (hoy `CREATE TABLE IF NOT EXISTS`).
- Backups y exportación de la story bible (Markdown).
- Resumen y "ficha" de la obra generado por IA.
- Modo multiusuario con roles de colaboración.
- CI/CD con los tests corriendo en cada PR.

## 📄 Licencia

Proyecto personal de aprendizaje; sin licencia definida por el momento.
