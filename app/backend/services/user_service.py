from PIL import UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

import models
from core.config import settings
from core.exceptions import (
    BadRequestError,
    EmailAlreadyRegisteredError,
    ForbiddenError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from core.security import hash_password
from utils.image_utils import delete_profile_image, process_profile_image
from schemas.users import UserCreate, UserUpdate
from schemas.posts import PaginatedPostResponse
from services import post_service


# --- consultas (las reutiliza también auth_service)
async def get_user_by_id(db: AsyncSession, user_id: int) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.username) == username.lower()
        )
    )
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> models.User | None:
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == email.lower())
    )
    return result.scalars().first()


def _ensure_self(user_id: int, current_user: models.User, detail: str) -> None:
    if user_id != current_user.id:
        raise ForbiddenError(detail)


# --- casos de uso
async def get_user(db: AsyncSession, user_id: int) -> models.User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError()
    return user


async def create_user(db: AsyncSession, data: UserCreate) -> models.User:
    if await get_user_by_username(db, data.username):
        raise UsernameAlreadyExistsError()
    if await get_user_by_email(db, data.email):
        raise EmailAlreadyRegisteredError()

    user = models.User(
        username=data.username,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_posts(
    db: AsyncSession, user_id: int, skip: int, limit: int
) -> PaginatedPostResponse:
    await get_user(db, user_id)  # 404 si no existe
    return await post_service.list_posts(db, skip, limit, user_id=user_id)


async def update_user(
    db: AsyncSession, user_id: int, data: UserUpdate, current_user: models.User
) -> models.User:
    _ensure_self(user_id, current_user, "Not authorized to update this user")

    # Solo validamos unicidad si el cliente envió un valor distinto al actual
    if (
        data.username is not None
        and data.username.lower() != current_user.username.lower()
        and await get_user_by_username(db, data.username)
    ):
        raise UsernameAlreadyExistsError()

    if (
        data.email is not None
        and data.email.lower() != current_user.email.lower()
        and await get_user_by_email(db, data.email)
    ):
        raise EmailAlreadyRegisteredError()

    if data.username is not None:
        current_user.username = data.username
    if data.email is not None:
        current_user.email = data.email.lower()

    await db.commit()
    await db.refresh(current_user)
    return current_user


async def delete_user(
    db: AsyncSession, user_id: int, current_user: models.User
) -> None:
    _ensure_self(user_id, current_user, "Not authorized to delete this user")
    await db.delete(current_user)
    await db.commit()


async def upload_profile_picture(
    db: AsyncSession,
    user_id: int,
    content: bytes,
    current_user: models.User,
) -> models.User:
    _ensure_self(
        user_id, current_user, "Not authorized to update this user's picture"
    )

    if len(content) > settings.max_upload_size_bytes:
        raise BadRequestError(
            f"File too large. Maximum size is "
            f"{settings.max_upload_size_bytes // (1024 * 1024)}MB"
        )

    try:
        new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise BadRequestError(
            "Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP)."
        ) from err

    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return current_user


async def delete_profile_picture(
    db: AsyncSession, user_id: int, current_user: models.User
) -> models.User:
    _ensure_self(
        user_id, current_user, "Not authorized to delete this user's picture"
    )

    old_filename = current_user.image_file
    if old_filename is None:
        raise BadRequestError("No profile picture to delete")

    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)

    delete_profile_image(old_filename)
    return current_user
