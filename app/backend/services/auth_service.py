from datetime import UTC, datetime, timedelta

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
from core.config import settings
from core.exceptions import (
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidResetTokenError,
)
from core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from schemas.auth import Token
from services import user_service


async def _delete_reset_tokens(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user_id,
        ),
    )


async def login(db: AsyncSession, email: str, password: str) -> Token:
    # OAuth2PasswordRequestForm usa el campo "username", pero aquí es el email
    user = await user_service.get_user_by_email(db, email)

    # No revelamos cuál de los dos falló
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(access_token=access_token, token_type="bearer")


async def create_password_reset(
    db: AsyncSession, email: str
) -> tuple[models.User, str] | None:
    """Devuelve (usuario, token en claro) o None si el email no existe.
    El envío del correo lo decide el router (background task)."""
    user = await user_service.get_user_by_email(db, email)
    if not user:
        return None

    await _delete_reset_tokens(db, user.id)

    token = generate_reset_token()
    db.add(
        models.PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.reset_token_expire_minutes),
        )
    )
    await db.commit()
    return user, token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == hash_reset_token(token),
        ),
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise InvalidResetTokenError()

    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise InvalidResetTokenError()

    user = await user_service.get_user_by_id(db, reset_token.user_id)
    if not user:
        raise InvalidResetTokenError()

    user.password_hash = hash_password(new_password)
    await _delete_reset_tokens(db, user.id)
    await db.commit()


async def change_password(
    db: AsyncSession,
    user: models.User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise IncorrectPasswordError()

    user.password_hash = hash_password(new_password)
    await _delete_reset_tokens(db, user.id)
    await db.commit()