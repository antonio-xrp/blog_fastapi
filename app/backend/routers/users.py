from typing import Annotated

from fastapi import APIRouter, Query, UploadFile, status

from core.config import settings
from core.database import DbSession
from core.security import CurrentUser
from schemas.users import (
    UserCreate,
    UserPrivate,
    UserPublic,
    UserUpdate,
)

from schemas.posts import PaginatedPostResponse

from services import user_service

router = APIRouter()


@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: DbSession):
    return await user_service.create_user(db, user)


# /me va antes que /{user_id}, si no "me" se interpretaría como un id
@router.get("/me", response_model=UserPrivate)
async def read_current_user(current_user: CurrentUser):
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: DbSession):
    return await user_service.get_user(db, user_id)


@router.get("/{user_id}/posts", response_model=PaginatedPostResponse)
async def get_user_posts(
    user_id: int,
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
):
    return await user_service.get_user_posts(db, user_id, skip, limit)


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    return await user_service.update_user(db, user_id, user_update, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, current_user: CurrentUser, db: DbSession):
    await user_service.delete_user(db, user_id, current_user)


@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: DbSession,
):
    content = await file.read()
    return await user_service.upload_profile_picture(
        db, user_id, content, current_user
    )


@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_user_picture(
    user_id: int, current_user: CurrentUser, db: DbSession
):
    return await user_service.delete_profile_picture(db, user_id, current_user)