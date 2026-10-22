
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from core.config import settings
from core.database import get_db


router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = PROJECT_ROOT / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Página principal del blog
@router.get("/", include_in_schema=False, name="home")
@router.get("/posts", include_in_schema=False, name="posts")
async def home(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count_result = await db.execute(
        select(func.count()).select_from(models.Post)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .limit(settings.posts_per_page)
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "posts": posts,
            "title": "Home",
            "limit": settings.posts_per_page,
            "has_more": total > len(posts),
        },
    )


# Página de una publicación
@router.get("/posts/{post_id}", include_in_schema=False)
async def post_page(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return templates.TemplateResponse(
        request=request,
        name="post.html",
        context={
            "post": post,
            "title": post.title[:50],
        },
    )


# Publicaciones de un usuario
@router.get(
    "/users/{user_id}/posts",
    include_in_schema=False,
    name="user_posts",
)
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .limit(settings.posts_per_page)
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="user_posts.html",
        context={
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
            "limit": settings.posts_per_page,
            "has_more": total > len(posts),
        },
    )


# Páginas de autenticación y cuenta
@router.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"title": "Login"},
    )


@router.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"title": "Register"},
    )


@router.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="account.html",
        context={"title": "Account"},
    )


@router.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={"title": "Forgot Password"},
    )


@router.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
