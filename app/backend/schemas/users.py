
from pydantic import BaseModel

from schemas.common import Email, ORMModel, Username


class UserBase(BaseModel):
    username: Username
    email: Email


class UserCreate(UserBase):
    password: str


class UserPublic(ORMModel):
    id: int
    username: str
    image_file: str | None = None
    image_path: str


class UserPrivate(UserPublic):
    email: Email


class UserUpdate(BaseModel):
    username: Username | None = None
    email: Email | None = None
