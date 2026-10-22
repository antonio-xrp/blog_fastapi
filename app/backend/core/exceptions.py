from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base de los errores de dominio; el handler la traduce a HTTP."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


# --- posts
class PostNotFoundError(NotFoundError):
    detail = "Post not found"


class NotPostOwnerError(ForbiddenError):
    def __init__(self, action: str = "update"):
        super().__init__(f"Not authorized to {action} this post")


# --- users
class UserNotFoundError(NotFoundError):
    detail = "User not found"


class UsernameAlreadyExistsError(BadRequestError):
    detail = "Username already exists"


class EmailAlreadyRegisteredError(BadRequestError):
    detail = "Email already registered"


# --- auth
class InvalidCredentialsError(UnauthorizedError):
    detail = "Incorrect email or password"


class InvalidResetTokenError(BadRequestError):
    detail = "Invalid or expired reset token"


class IncorrectPasswordError(BadRequestError):
    detail = "Current password is incorrect"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )