
from datetime import datetime

from pydantic import BaseModel

from schemas.common import ORMModel, PostContent, PostTitle
from schemas.users import UserPublic


class PostBase(BaseModel):
    title: PostTitle
    content: PostContent


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: PostTitle | None = None
    content: PostContent | None = None


class PostResponse(PostBase, ORMModel):
    id: int
    user_id: int
    date_posted: datetime
    author: UserPublic


class PaginatedPostResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool