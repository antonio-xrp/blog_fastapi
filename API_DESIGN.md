# Diseño de la API  — blog_fastapi

## 1. Stack tecnológico y el porqué de cada pieza

| Librería | Rol | Por qué se eligió | Alternativa descartada |
|---|---|---|---|
| **Python ≥ 3.13 + uv** | Runtime y gestor de entorno | `uv` resuelve y bloquea dependencias (`uv.lock`) de forma rápida y reproducible; un solo comando para entorno, scripts y build | pip + requirements.txt (sin lock real), Poetry |
| **FastAPI[standard]** | Framework web | Async nativo, validación con type hints, OpenAPI y `/docs` gratis (el contrato se vuelve ejecutable); el extra `standard` trae uvicorn y las utilidades de desarrollo | Flask (sin validación ni async nativos), Django (más pesado para una API + plantillas pequeñas) |
| **Pydantic v2** (vía FastAPI) | Schemas de entrada/salida (`schemas.py`) | Separa el contrato público del modelo de base de datos: nunca se expone `password_hash` | Devolver modelos SQLAlchemy directamente |
| **pydantic-settings** | Configuración (`config.py`) | Variables de entorno tipadas y validadas al arrancar; misma app en local, Docker y producción sin tocar código | `os.environ` suelto, `python-dotenv` en producción |
| **SQLAlchemy 2.x (asyncio)** | ORM (`models.py`, `database.py`) | `Mapped[]` tipado, sesiones async que no bloquean el event loop, mismo código sobre SQLite y PostgreSQL | SQL a mano, Tortoise/SQLModel |
| **aiosqlite** | Driver SQLite async | Desarrollo inicial y tests sin levantar servicios | — |
| **psycopg[binary] 3** | Driver PostgreSQL | Driver moderno con soporte async; `binary` evita compilar libpq | asyncpg, psycopg2 (sin async) |
| **Alembic** | Migraciones (`alembic/`) | El esquema deja de depender de `create_all`: queda versionado y se puede reproducir en Postgres desde cero (ver sección 3) | `Base.metadata.create_all` (no migra cambios) |
| **pwdlib[argon2]** | Hash de contraseñas (`auth.py`) | Argon2 es el algoritmo recomendado actualmente; `pwdlib` es la opción vigente frente a `passlib`, que quedó sin mantenimiento | bcrypt con passlib, SHA256 (inaceptable) |
| **PyJWT** | Tokens de acceso | Autenticación sin estado para la API; librería pequeña y mantenida | python-jose, sesiones en servidor |
| **aiosmtplib** | Envío de correo (`email_utils.py`) | SMTP async: enviar el correo de reset no bloquea otras peticiones | smtplib síncrono, servicios con SDK propio |
| **Pillow** | Imágenes (`image_utils.py`) | Validar, recortar y redimensionar fotos de perfil antes de guardarlas | Guardar el archivo tal cual (riesgo de peso y de archivos no-imagen) |
| **pytest** | Tests | Estándar, fixtures para override de dependencias (BD de prueba) | unittest |
| **moto[s3]** (dev) | Simular S3 en tests | Permite probar almacenamiento de objetos sin cuenta AWS. ⚠ Confirmar si hoy se usa S3 o disco (`media/profile_pics`) y registrarlo en un ADR | — |
| **Jinja2 + Bootstrap + fetch** | Frontend servido por FastAPI | Sin build de JS: páginas HTML renderizadas en servidor y modales que llaman a la API con `fetch` | SPA con React (más infraestructura para este alcance) |
| **Docker / compose** | Empaquetado | Mismo entorno local y producción; compose levanta app + PostgreSQL | — |

---

## 2. Arquitectura

```mermaid
flowchart LR
    subgraph Cliente
        B["Navegador<br/>Jinja2"]
    end

    subgraph App["FastAPI (main.py)"]
        MW["Middleware / handlers de error"]
        R["routers/<br/>users · posts · auth"]
        D["Dependencias<br/>get_db · current_user"]
        S["schemas.py<br/>(Pydantic)"]
        A["auth.py<br/>argon2 + JWT"]
        U1["email_utils.py"]
        U2["image_utils.py"]
        M["models.py<br/>(SQLAlchemy)"]
    end

    B -->|HTTP| MW --> R
    R --> D
    R --> S
    D --> A
    R --> M
    R --> U1
    R --> U2
    M --> DB[("PostgreSQL<br/>(SQLite en dev/tests)")]
    U1 --> SMTP["Servidor SMTP"]
    U2 --> FS["media/profile_pics"]
    AL["Alembic"] -.->|migra esquema| DB
```

```mermaid
flowchart LR
    U["👤 Usuario"] --> W["🌐 Página web del blog"]

    subgraph Docker["🐳 Docker (todo empaquetado junto)"]
        A["⚙️ Aplicación del blog"]
        D[("🗄️ Base de datos<br/>usuarios y posts")]
        F["🖼️ Fotos de perfil"]
        A <--> D
        A --> F
    end

    W <--> A
    A --> C["📧 Correo<br/>recuperar contraseña"]
```
```


**Reglas de dependencia** (lo que se debe respetar al programar):

1. Los routers dependen de `schemas`, `models`, `auth` y utilidades; **nunca al revés**.
2. `models.py` no importa nada de `routers` ni de `schemas`.
3. Toda ruta obtiene la sesión por `Depends(get_db)` y el usuario por `Depends(current_user)`; no se crean sesiones dentro de la función.
4. La autorización (¿es el autor?) se verifica en el router, la autenticación (¿quién eres?) en la dependencia.

---

## 3. Evolución de la base de datos: SQLite → PostgreSQL con Alembic

```mermaid
flowchart TD
    A["Fase 1 · Prototipo<br/>SQLite + aiosqlite<br/>create_all"] --> B["Fase 2 · Esquema versionado<br/>Alembic (autogenerate)"]
    B --> C["Fase 3 · Producción<br/>PostgreSQL + psycopg"]
    C --> D["alembic upgrade head<br/>(al iniciar el contenedor)"]
    A -.->|datos existentes| E["backup.sql → carga en Postgres"]
    E --> F["Reiniciar secuencias de id<br/>(setval)"]
    D --> G["App en producción"]
    F --> G
    A --> T["Tests: SQLite en memoria<br/>(siguen usando aiosqlite)"]
```

**Por qué Alembic fue la pieza clave del cambio:**

- Con SQLite, `create_all` bastaba, pero no modifica tablas existentes. Alembic convierte cada cambio de modelo (por ejemplo, `likes` con `server_default="0"`) en una revisión reproducible.
- La misma cadena de migraciones construye el esquema en Postgres desde cero: la fuente de verdad es `alembic/versions/`, no el estado de un archivo `.db`.
- `alembic.ini` + `env.py` deben leer la URL desde `config.py`, para que cambiar de motor sea cambiar una variable de entorno.

**Diferencias SQLite ↔ PostgreSQL a vigilar (checklist de la migración):**

| Tema | SQLite | PostgreSQL | Efecto en este proyecto |
|---|---|---|---|
| Longitud de `String(n)` | No se aplica | Se aplica | `title` (100), `username` (50), `email` (120) pueden fallar con datos que antes pasaban |
| Zona horaria en `DateTime(timezone=True)` | Se ignora | Se respeta (`timestamptz`) | `date_posted` y `expires_at` se guardan en UTC de forma consistente |
| Autoincrement | Implícito | Secuencias | Tras cargar `backup.sql`, reiniciar secuencias de `users.id`, `posts.id`, `password_reset_tokens.id` |
| `ALTER TABLE` | Limitado | Completo | En SQLite Alembic necesita `render_as_batch=True`; en Postgres no |
| Mayúsculas/minúsculas en `unique` | Según collation | Sensible a mayúsculas | `username`/`email` duplicados por mayúsculas: normalizar a minúsculas al guardar |

---

## 4. Modelo de datos

```mermaid
erDiagram
    USERS ||--o{ POSTS : "escribe"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "solicita"

    USERS {
        int id PK
        string username UK "max 50"
        string email UK "max 120"
        string password_hash "max 200"
        string image_file "nullable, max 200"
    }
    POSTS {
        int id PK
        string title "max 100"
        text content
        int user_id FK "index"
        datetime date_posted "tz-aware, UTC"
        int likes "default 0"
    }
    PASSWORD_RESET_TOKENS {
        int id PK
        int user_id FK
        string token_hash UK "64 chars (sha256)"
        datetime expires_at
        datetime created_at
    }
```

Reglas de negocio:

- Borrar un usuario elimina en cascada sus posts y sus tokens (`cascade="all, delete-orphan"`).
- Del token de reset solo se guarda el **hash**; el valor en claro viaja únicamente por correo.
- Si `image_file` es `NULL`, se usa la imagen por defecto.

---

## 5. Contrato de la API

### 5.1 Convenciones

| Tema | Decisión |
|---|---|
| Prefijo | `/api` para JSON. Las páginas HTML (Jinja2) quedan fuera de este contrato |
| Autenticación | `Authorization: Bearer <JWT>` |
| Formato de error | `{"detail": "mensaje"}`; en `422` FastAPI devuelve la lista de errores de Pydantic |
| Paginación | `?skip=0&limit=20` (límite máximo a definir) |
| Fechas | ISO 8601 en UTC |
| Códigos | 200 lectura/edición · 201 creación · 204 borrado · 400 regla de negocio · 401 sin/ mal token · 403 sin permiso · 404 no existe · 409 conflicto · 422 validación |

### 5.2 Resumen de endpoints

| Estado | Método | Ruta | Auth | Descripción |
|---|---|---|---|---|
| ⚠ | POST | `/api/users` | público | Registro de usuario |
| ⚠ | POST | `/api/users/token` | público | Login, devuelve JWT |
| ⚠ | GET | `/api/users/me` | 🔒 | Usuario autenticado |
| ⚠ | GET | `/api/users/{user_id}` | público | Perfil público |
| ⚠ | PATCH | `/api/users/{user_id}` | 🔒 propio | Editar username/email |
| ⚠ | PATCH | `/api/users/{user_id}/picture` | 🔒 propio | Subir foto de perfil |
| ⚠ | DELETE | `/api/users/{user_id}` | 🔒 propio | Eliminar cuenta (cascada) |
| ⚠ | GET | `/api/users/{user_id}/posts` | público | Posts de un usuario |
| ⚠ | POST | `/api/users/forgot-password` | público | Solicitar reset por correo |
| ⚠ | POST | `/api/users/reset-password` | público | Fijar nueva contraseña con token |
| ⚠ | GET | `/api/posts` | público | Listar posts (paginado) |
| ⚠ | POST | `/api/posts` | 🔒 | Crear post |
| ⚠ | GET | `/api/posts/{post_id}` | público | Detalle de post |
| ✅ en uso | PATCH | `/api/posts/{post_id}` | 🔒 autor | Editar post (modal Editar) |
| ✅ en uso | DELETE | `/api/posts/{post_id}` | 🔒 autor | Eliminar post (modal Eliminar) |
| ⚠ | POST | `/api/posts/{post_id}/like` | 🔒 | Sumar like (la columna `likes` existe; definir si se permite un like por usuario) |

### 5.3 Detalle de los endpoints principales

#### POST `/api/users/token`
- **Propósito:** autenticar y entregar un JWT.
- **Body:** formulario OAuth2 (`username`, `password`) — `application/x-www-form-urlencoded`.
- **Lógica:** buscar usuario → verificar hash Argon2 → firmar JWT con `sub=user.id` y `exp`.
- **Respuestas:**

| Código | Cuándo | Body |
|---|---|---|
| 200 | Credenciales válidas | `{"access_token": "...", "token_type": "bearer"}` |
| 401 | Usuario o clave incorrectos (mismo mensaje en ambos casos) | `{"detail": "..."}` |
| 422 | Formulario incompleto | errores Pydantic |

#### POST `/api/posts`
- **Auth:** 🔒 JWT. **Body (`PostCreate`):** `title` (1–100), `content` (≥1).
- **Efecto:** crea el post con `user_id` del token (nunca del body) y `date_posted` en UTC.

| Código | Cuándo | Body |
|---|---|---|
| 201 | Creado | `PostResponse` |
| 401 | Sin token o inválido | `{"detail": "..."}` |
| 422 | Título > 100 o vacío | errores Pydantic |

#### PATCH `/api/posts/{post_id}`
- **Auth:** 🔒 JWT + el usuario debe ser el autor.
- **Body (`PostUpdate`):** `title?` (1–100), `content?`. Los campos ausentes no se modifican.

| Código | Cuándo | Body |
|---|---|---|
| 200 | Actualizado | `PostResponse` |
| 401 | Token ausente o inválido | `{"detail": "..."}` |
| 403 | El usuario no es el autor | `{"detail": "..."}` |
| 404 | El post no existe | `{"detail": "..."}` |
| 422 | Validación | errores Pydantic |

#### DELETE `/api/posts/{post_id}`
- **Auth:** 🔒 JWT + autor. **Efecto:** elimina el post.

| Código | Cuándo |
|---|---|
| 204 | Eliminado (sin body) |
| 401 / 403 / 404 | Igual que PATCH |

#### POST `/api/users/forgot-password`
- **Body:** `{"email": "..."}`.
- **Regla de seguridad:** responde **siempre 200 con el mismo mensaje**, exista o no el correo (evita enumeración de usuarios).
- **Efecto:** genera token aleatorio, guarda `sha256(token)` con `expires_at`, envía el enlace por SMTP.

#### POST `/api/users/reset-password`
- **Body:** `{"token": "...", "new_password": "..."}`.
- **Efecto:** valida hash y expiración, actualiza `password_hash`, elimina el token (uso único).

| Código | Cuándo |
|---|---|
| 200 | Contraseña actualizada |
| 400 | Token inválido o expirado |
| 422 | Contraseña no cumple política |

---

## 6. Flujos principales

### 6.1 Login y acceso a un recurso protegido

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant A as auth.py
    participant DB as PostgreSQL

    U->>API: POST /api/users/token (username, password)
    API->>DB: SELECT user
    API->>A: verify(password, password_hash)
    A-->>API: ok
    API-->>U: 200 {access_token}
    U->>API: PATCH /api/posts/5 + Bearer token
    API->>A: decode JWT → user_id
    API->>DB: SELECT post 5
    alt post.user_id != user_id
        API-->>U: 403
    else autor
        API->>DB: UPDATE post
        API-->>U: 200 PostResponse
    end
```

### 6.2 Editar y eliminar desde la página (fetch)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant JS as utils.js
    participant API as FastAPI
    participant DB as PostgreSQL

    U->>JS: Guardar cambios (modal Editar)
    JS->>API: PATCH /api/posts/{id}
    API->>DB: UPDATE
    API-->>JS: 200 PostResponse
    JS-->>U: refresca el contenido
    U->>JS: Confirmar (modal Eliminar)
    JS->>API: DELETE /api/posts/{id}
    API->>DB: DELETE
    API-->>JS: 204
    JS-->>U: redirige a inicio
```

### 6.3 Recuperación de contraseña

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant DB as PostgreSQL
    participant M as SMTP

    U->>API: POST /forgot-password {email}
    API->>DB: buscar usuario
    opt usuario existe
        API->>DB: guardar sha256(token) + expires_at
        API->>M: enviar enlace con token en claro
    end
    API-->>U: 200 (mensaje genérico)
    U->>API: POST /reset-password {token, new_password}
    API->>DB: buscar por sha256(token)
    alt válido y no expirado
        API->>DB: actualizar password_hash, borrar token
        API-->>U: 200
    else inválido o expirado
        API-->>U: 400
    end
```

### 6.4 Registro con foto de perfil

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as FastAPI
    participant P as image_utils (Pillow)
    participant FS as media/profile_pics
    participant DB as PostgreSQL

    U->>API: POST /api/users {username, email, password}
    API->>DB: INSERT user (password_hash argon2)
    API-->>U: 201 UserResponse
    U->>API: PATCH /api/users/{id}/picture (multipart)
    API->>P: validar y redimensionar
    P->>FS: guardar archivo
    API->>DB: UPDATE image_file
    API-->>U: 200 UserResponse
```

---

## 7. Seguridad y calidad (criterios de aceptación)

- Contraseñas: solo hash Argon2; nunca se registran en logs ni se devuelven.
- JWT con expiración corta y clave en variable de entorno (`config.py`), no en el repo.
- Autorización por recurso: toda edición o borrado comprueba que el usuario sea el autor.
- Subida de imágenes: validar tipo real, límite de tamaño y nombre de archivo generado por el servidor.
- Respuestas de `forgot-password` indistinguibles entre correo existente y no existente.
- Tests mínimos por endpoint: caso feliz, 401, 403, 404 y 422.
- Base de datos de pruebas aislada (SQLite en memoria) con `dependency_overrides[get_db]`.

## 8. ADRs pendientes de redactar

| # | Decisión |
|---|---|
| 0001 | FastAPI async frente a Flask/Django |
| 0002 | JWT sin estado frente a sesiones |
| 0003 | Argon2 con pwdlib |
| 0004 | Guardar solo el hash del token de reset |
| 0005 | SQLite en desarrollo y tests, PostgreSQL en producción, migraciones con Alembic |
| 0006 | Imágenes: disco local frente a S3 |
| 0007 | Estructura del código: módulos en raíz frente a `src/fastapi_blog` |
