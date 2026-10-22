from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from core.exceptions import NotPostOwnerError,PostNotFoundError
from schemas.posts import PostCreate, PostUpdate, PaginatedPostResponse, PostResponse, PostUpdate


# Verfica propiedad
def _ensure_owner(
    post: models.Post,
    user: models.User,
    action: str
) -> None:
    if post.user_id != user.id:
        raise NotPostOwnerError(action)

#Get post by_id or 404
async def _get_post_or_404(
    db:AsyncSession,
    post_id:int
) -> models.Post:
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise PostNotFoundError
    return post


async def list_posts(
    db: AsyncSession, skip: int, limit: int, user_id: int | None = None
) -> PaginatedPostResponse:
    count_query = select(func.count()).select_from(models.Post)
    posts_query = select(models.Post).options(selectinload(models.Post.author))

    if user_id is not None:
        count_query = count_query.where(models.Post.user_id == user_id)
        posts_query = posts_query.where(models.Post.user_id == user_id)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        posts_query.order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()

    return PaginatedPostResponse(
        posts=[PostResponse.model_validate(p) for p in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(posts) < total,
    )

async def get_post(db: AsyncSession, post_id: int) -> models.Post:
    return await _get_post_or_404(db, post_id)


async def create_post(
    db: AsyncSession,
    data:PostCreate,
    user:models.User
) -> models.Post:
    new_post = models.Post(
        title=data.title,
        content=data.content,
        user_id=user.id
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post

 
async def replace_post(
    db: AsyncSession,
    post_id: int,
    data: PostCreate,
    user: models.User
) -> models.Post:
    
    post = await _get_post_or_404(db,post_id)
    _ensure_owner(post,user, "update")

    post.title = data.title
    post.content = data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

async def update_post(
    db: AsyncSession,
    post_id: int,
    data: PostUpdate, 
    user: models.User
) -> models.Post:
    post = await _get_post_or_404(db, post_id)
    _ensure_owner(post, user, "update")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


async def delete_post(db: AsyncSession, post_id: int, user: models.User) -> None:
    post = await _get_post_or_404(db, post_id)
    _ensure_owner(post, user, "delete")

    await db.delete(post)
    await db.commit()


