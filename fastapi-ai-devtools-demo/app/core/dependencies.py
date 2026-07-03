"""Shared FastAPI dependencies: current-user auth and service access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import get_user_by_username
from app.services.search_service import SearchService

if TYPE_CHECKING:  # avoid importing heavy modules at runtime / import time
    from app.services.generation_gate import GenerationGate
    from app.services.gpu_router import GpuRouter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_search_service(request: Request) -> SearchService:
    """Return the process-wide SearchService stored on app state."""
    service: SearchService | None = getattr(
        request.app.state, "search_service", None
    )
    if service is None:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is not ready.",
        )
    return service


def get_llm_router(request: Request) -> GpuRouter:
    """Return the process-wide GPU router stored on app state.

    This is the override seam the /chat tests use (swap in a stub router).
    """
    router = getattr(request.app.state, "llm_router", None)
    if router is None:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM router is not ready.",
        )
    return router


def get_generation_gate(request: Request) -> GenerationGate:
    """Return the process-wide generation gate (concurrency + queue)."""
    gate = getattr(request.app.state, "generation_gate", None)
    if gate is None:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation gate is not ready.",
        )
    return gate


def get_model_catalog(request: Request):
    """Return the process-wide model catalog."""
    catalog = getattr(request.app.state, "model_catalog", None)
    if catalog is None:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model catalog is not ready.",
        )
    return catalog


def get_learning_store(request: Request):
    """Return the process-wide learning store, or None when disabled."""
    return getattr(request.app.state, "learning_store", None)


def get_conversation_store(request: Request):
    """Return the process-wide conversation store, or None when unavailable.

    Backs durable /chat persistence; None is treated as "persistence disabled"
    by ChatService so the chat path degrades gracefully if it is ever absent.
    """
    return getattr(request.app.state, "conversation_store", None)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DbSession,
) -> User:
    """Resolve the authenticated user from a bearer token."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = decode_access_token(token)
    if username is None:
        raise credentials_exc
    user = await get_user_by_username(session, username)
    if user is None:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
SearchDep = Annotated[SearchService, Depends(get_search_service)]
# Typed as Any to avoid importing GpuRouter / GenerationGate at module load.
RouterDep = Annotated[Any, Depends(get_llm_router)]
GateDep = Annotated[Any, Depends(get_generation_gate)]
CatalogDep = Annotated[Any, Depends(get_model_catalog)]
LearningDep = Annotated[Any, Depends(get_learning_store)]
ConversationDep = Annotated[Any, Depends(get_conversation_store)]
