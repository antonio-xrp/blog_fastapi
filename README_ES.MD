# FastAPI Blog

Blog construido con **FastAPI**: API REST asíncrona con autenticación JWT, PostgreSQL/SQLite mediante SQLAlchemy y un frontend ligero renderizado en servidor (plantillas Jinja2 + archivos estáticos).

## Stack

- Python 3.13+, FastAPI, Pydantic v2 / pydantic-settings
- SQLAlchemy 2 (async) + migraciones con Alembic
- PostgreSQL (`psycopg`) o SQLite (`aiosqlite`)
- JWT (PyJWT) + hash de contraseñas con Argon2 (pwdlib)
- Pillow (imágenes de perfil), aiosmtplib (correos de recuperación)
- Herramientas: uv, pytest, Docker

## Inicio rápido

```bash
uv sync
cp .env.example .env      # luego edita los valores (ver Configuración)
alembic upgrade head
fastapi dev main.py
```

- App: http://localhost:8000
- Documentación interactiva de la API: http://localhost:8000/docs

## Configuración (`.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | – (obligatoria) | URL async de SQLAlchemy |
| `SECRET_KEY` | – (obligatoria) | Clave de firma JWT |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Duración del token de acceso |
| `RESET_TOKEN_EXPIRE_MINUTES` | `60` | Duración del token de recuperación |
| `POSTS_PER_PAGE` | `10` | Tamaño de página por defecto |
| `MAX_UPLOAD_SIZE_BYTES` | `5242880` | Tamaño máx. de imagen de perfil (5 MB) |
| `MAIL_SERVER` / `MAIL_PORT` | `localhost` / `587` | Servidor SMTP |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | – | Credenciales SMTP |
| `MAIL_FROM` / `MAIL_USE_TLS` | `noreply@example.com` / `true` | Remitente y TLS |
| `FRONTEND_URL` | `http://localhost:8000` | URL base para enlaces de recuperación |

## Resumen de la API

Prefijos base: `/api/users`, `/api/posts`. Referencia interactiva completa en `/docs`.

| Recurso | Prefijo | Funcionalidades |
|---|---|---|
| Usuarios | `/api/users` | Registro, login (devuelve JWT Bearer), ver/actualizar perfil, subir foto de perfil, cambiar contraseña, recuperar/restablecer contraseña |
| Publicaciones | `/api/posts` | Crear, leer, actualizar y eliminar posts; listado paginado (`skip`, `limit`) |

**Autenticación:** enviar `Authorization: Bearer <access_token>` en las rutas protegidas.

**Respuesta paginada:** `{ posts, total, skip, limit, has_more }`

**Errores:** `/api/*` responde JSON (`{"detail": ...}`, `422` en errores de validación).

## Modelo de datos

- **User** — `username` (único), `email` (único), `password_hash`, `image_file`
- **Post** — `title` (≤100), `content`, `user_id` → User, `date_posted`, `likes`
- **PasswordResetToken** — token hasheado con expiración, asociado a User

Relaciones: User 1—N Post; User 1—N PasswordResetToken (borrado en cascada).

## Estructura del proyecto

```
main.py          Configuración de la app, routers, manejo de errores
routers/         Rutas de la API (users, posts)
models.py        Modelos SQLAlchemy
schemas.py       Schemas Pydantic
auth.py          Utilidades JWT y contraseñas
config.py        Configuración (.env)
database.py      Motor / sesión async
alembic/         Migraciones
tests/           Pruebas
```

## Frontend

Renderizado en servidor con Jinja2 (`templates/`) y recursos estáticos (`static/`); las imágenes subidas se sirven desde `/media`.

## Pruebas

```bash
uv run pytest
```