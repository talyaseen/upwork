"""Authentication routes: register and login."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import Token, UserCreate, UserPublic
from app.services.auth_service import (
    authenticate,
    create_user,
    get_user_by_username,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    description=(
        "Create a user account. Usernames are unique. Passwords are hashed "
        "with bcrypt and never stored or returned in plaintext."
    ),
)
async def register(payload: UserCreate, session: DbSession) -> UserPublic:
    existing = await get_user_by_username(session, payload.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )
    try:
        user = await create_user(session, payload.username, payload.password)
    except IntegrityError:
        # TOCTOU: a concurrent request registered the same username between
        # the check above and this insert. The unique constraint is the real
        # arbiter; surface a clean 409 instead of an uncaught 500 (BH4).
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        ) from None
    return UserPublic.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Obtain a JWT access token",
    description=(
        "Exchange username and password (sent as OAuth2 form fields) for a "
        "signed JWT bearer token. Send the token as `Authorization: Bearer "
        "<token>` on protected endpoints."
    ),
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DbSession,
) -> Token:
    user = await authenticate(session, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.username)
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Return the current authenticated user",
)
async def read_me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)
