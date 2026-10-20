
from pydantic import BaseModel

from schemas.common import Email, Password


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Password


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Password
