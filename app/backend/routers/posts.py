from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

import models
from core.security import CurrentUser
from core.config import settings
from core.database import get_db
from schemas.posts import PostCreate, PostResponse, PostUpdate, PaginatedPostResponse
from services import post_service

from core.database import DbSession
router = APIRouter()


@router.get("",response_model=PaginatedPostResponse)
async def get_posts(
    db:DbSession,
    skip: Annotated[int, Query(ge=0)] =0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
):
    return await post_service.list_posts(db,skip,limit)



@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    current_user: CurrentUser,
    db:DbSession
):
    return await post_service.create_post(db,post,current_user)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id:int, db:DbSession):
    return await post_service.get_post(db, post_id)


@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
    post_id:int,
    post_data:PostCreate,
    current_user:CurrentUser,
    db:DbSession
):
    return await post_service.replace_post(db, post_id, post_data,current_user)



@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int, post_data: PostUpdate, current_user: CurrentUser, db: DbSession
):
    return await post_service.update_post(db, post_id, post_data, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: CurrentUser, db: DbSession):
    await post_service.delete_post(db, post_id, current_user)








