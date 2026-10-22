# Arquitectura por capas de la API

```mermaid

flowchart TB
    U["Usuario / Navegador"]

    subgraph PRESENTATION["1. Capa de presentación"]
        direction TB
        FE["Frontend<br/>Jinja2 · HTML · CSS · JavaScript"]
        ROUTERS["Routers FastAPI<br/>pages.py · auth.py · users.py · posts.py"]
        SCHEMAS["Schemas Pydantic<br/>Validación de entrada y salida"]
    end

    subgraph BUSINESS["2. Capa de negocio"]
        direction TB
        AS["AuthService"]
        US["UserService"]
        PS["PostService"]
    end

    subgraph INFRA["3. Capa de infraestructura y acceso a datos"]
        direction TB
        ORM["Models SQLAlchemy<br/>user.py · post.py · password_reset_token.py"]
        DBSESSION["Database<br/>Engine · sesiones · conexiones"]
        DB[("PostgreSQL")]
    end

    subgraph CROSS["4. Componentes transversales"]
        direction TB
        SEC["Security<br/>Hash de contraseñas · JWT"]
        CFG["Config<br/>Variables de entorno"]
        EX["Exceptions<br/>Manejo de errores"]
        UTILS["Utils<br/>Correo electrónico · imágenes"]
    end

    U <--> FE
    FE <--> ROUTERS
    ROUTERS <--> SCHEMAS
    ROUTERS --> AS
    ROUTERS --> US
    ROUTERS --> PS

    AS --> ORM
    US --> ORM
    PS --> ORM

    ORM --> DBSESSION
    DBSESSION <--> DB

    ROUTERS -.-> SEC
    AS -.-> SEC
    AS -.-> UTILS
    US -.-> UTILS
    ROUTERS -.-> EX
    DBSESSION -.-> CFG

```


### Stack tecnológico

- **Lenguaje:** Python 3.13
- **Backend:** FastAPI, Uvicorn
- **Base de datos:** PostgreSQL 17
- **ORM y migraciones:** SQLAlchemy, Alembic
- **Frontend:** HTML5, CSS3, JavaScript, Jinja2
- **Contenedores:** Docker, Docker Compose
- **Gestión de dependencias:** uv
- **Validación de datos:** Pydantic
- **Autenticación:** OAuth2, JWT, pwdlib
- **Testing:** pytest, HTTPX, AnyIO

