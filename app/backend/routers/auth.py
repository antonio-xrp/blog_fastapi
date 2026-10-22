from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from core.database import DbSession
from core.security import CurrentUser
from utils.email_utils import send_password_reset_email
from schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
)
from services import auth_service

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    return await auth_service.login(db, form_data.username, form_data.password)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    reset = await auth_service.create_password_reset(db, request_data.email)

    if reset:
        user, token = reset
        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )

    # Misma respuesta exista o no la cuenta
    return {
        "message": "If an account exists with this email, you will receive password reset instructions.",
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request_data: ResetPasswordRequest, db: DbSession):
    await auth_service.reset_password(
        db, request_data.token, request_data.new_password
    )
    return {
        "message": "Password reset successfully. You can now log in with your new password.",
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    await auth_service.change_password(
        db,
        current_user,
        password_data.current_password,
        password_data.new_password,
    )
    return {"message": "Password changed successfully"}