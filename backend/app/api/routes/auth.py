from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AppSettings, CurrentAnalyst, DbSession, limit_login_attempts
from app.api.responses import problem_responses
from app.core.retry import read_with_retry
from app.core.tokens import create_access_token
from app.schemas.auth import AnalystOut, TokenResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    responses=problem_responses(401, 422, 429),
    dependencies=[Depends(limit_login_attempts)],
    summary="Log in with username and password (OAuth2 password flow)",
    description="Limited to 5 attempts per minute per IP.",
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession, settings: AppSettings
) -> TokenResponse:
    analyst = read_with_retry(
        db, lambda: auth_service.authenticate(db, form.username, form.password)
    )
    if analyst is None:
        # Same message whether the user exists or not.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(analyst.id, settings),
        expires_in=settings.jwt_expires_minutes * 60,
        analyst=AnalystOut.model_validate(analyst),
    )


@router.get("/me", response_model=AnalystOut, responses=problem_responses(401))
def me(analyst: CurrentAnalyst) -> AnalystOut:
    return AnalystOut.model_validate(analyst)
