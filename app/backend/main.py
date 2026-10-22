
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.templating import Jinja2Templates

from core.database import engine
from routers import pages, posts, users, auth
from core.exceptions import register_exception_handlers


# Directorio raíz del proyecto.
# main.py está en app/backend/, por eso subimos tres niveles
# contando el propio archivo y llegamos a la raíz del proyecto.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "app" / "frontend"

STATIC_DIR = FRONTEND_DIR / "static"
MEDIA_DIR = PROJECT_ROOT / "app" / "backend" / "media"
TEMPLATES_DIR = FRONTEND_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)


# Recursos estáticos y plantillas
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)
app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="media",
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Routers
app.include_router(auth.router, prefix="/api/users", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(pages.router)


# Manejo de errores HTTP
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


# Manejo de errores de validación
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(
            request,
            exception,
        )

    validation_status = status.HTTP_422_UNPROCESSABLE_CONTENT

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": validation_status,
            "title": validation_status,
            "message": (
                "Invalid request. Please check your input and try again."
            ),
        },
        status_code=validation_status,
    )
