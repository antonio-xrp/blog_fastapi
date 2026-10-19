# 1. Elegir la imagen base
FROM python:3.13-slim

# 2. Definir el directorio de trabajo
WORKDIR /fastapi_blog

# 3. Instalar la herramienta uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 4. Configurar Python y el entorno virtual
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/fastapi_blog/.venv \
    PATH="/fastapi_blog/.venv/bin:$PATH"

# 5. Instalar dependencias del sistema
# Necesario si tu proyecto utiliza PostgreSQL mediante psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 6. Copiar los archivos de dependencias
COPY pyproject.toml uv.lock ./

# 7. Instalar dependencias sin instalar el proyecto como paquete
RUN uv sync --frozen --no-dev --no-install-project

# 8. Copiar el código y los recursos del proyecto
COPY . .

# 9. Exponer el puerto de la aplicación
EXPOSE 80

# 10. Iniciar FastAPI
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "80"]