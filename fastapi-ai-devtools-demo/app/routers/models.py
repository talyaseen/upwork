"""Model picker endpoint: the curated set of demo-selectable models.

GET /models returns the curated model set the UI offers (GPU-only: a single 7B
served on the GPU), flagged with whether it is currently servable - the GPU model
is available only when the GPUs are free for the demo and the vLLM engine is
healthy. There is no CPU fallback: when the GPU is unavailable the demo is offline.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.dependencies import CatalogDep, RouterDep

router = APIRouter(tags=["models"])


class ModelInfo(BaseModel):
    id: str
    label: str
    tier: str
    description: str
    requires_gpu: bool
    available: bool


class ModelListResponse(BaseModel):
    default: str
    gpu_available: bool
    models: list[ModelInfo]


@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="List the curated, selectable LLM models",
)
async def list_models(
    llm_router: RouterDep,
    catalog: CatalogDep,
) -> ModelListResponse:
    gpu_ok = await llm_router.gpu_available()
    models = [
        ModelInfo(
            id=e.id,
            label=e.label,
            tier=e.tier,
            description=e.description,
            requires_gpu=e.requires_gpu,
            available=(gpu_ok if e.requires_gpu else True),
        )
        for e in catalog.entries
    ]
    return ModelListResponse(
        default=catalog.default_id, gpu_available=gpu_ok, models=models
    )
