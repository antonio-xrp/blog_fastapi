
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Username = Annotated[str, Field(min_length=1, max_length=50)]
Email = Annotated[EmailStr, Field(max_length=120)]
Password = Annotated[str, Field(min_length=8)]
PostTitle = Annotated[str, Field(min_length=1, max_length=100)]
PostContent = Annotated[str, Field(min_length=1)]


class ORMModel(BaseModel):
    """Base schema for SQLAlchemy ORM serialization."""

    model_config = ConfigDict(from_attributes=True)
