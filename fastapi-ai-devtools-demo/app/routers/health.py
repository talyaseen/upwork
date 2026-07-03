"""Health and readiness route."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import SearchDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    embedding_backend: str
    embedding_dimension: int
    indexed_chunks: int


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness and readiness probe",
    description="Report process health, the active embedding backend and the "
    "current size of the in-memory vector index.",
)
async def health(search: SearchDep) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        embedding_backend=settings.embedding_backend,
        embedding_dimension=search.dimension,
        indexed_chunks=search.size,
    )
