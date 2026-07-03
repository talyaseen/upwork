"""Public status endpoint for a site-wide UI banner.

GET /status -> { "tier": "gpu"|"offline", "gpu_online": bool, "model": "<name>" }

Browsers reach this via the nginx /api/ reverse-proxy location, which strips the
/api/ prefix before forwarding to FastAPI. The path arriving at FastAPI is therefore
/status (not /api/status). The Flutter client prefixes with baseUrl=/api to produce
/api/status on the wire; nginx strips it to /status here.

Only these safe fields are exposed (no internal details, no nvidia-smi dump, no
IPs). It is derived from the router's CACHED state (the ~12s nvidia-smi cache),
so polling it (every 10-30s) is cheap. This endpoint IS public - it intentionally
reveals only whether the GPU demo is online or offline (GPU serving training).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.dependencies import LearningDep, RouterDep

router = APIRouter(prefix="", tags=["status"])


class PublicStatus(BaseModel):
    tier: str
    gpu_online: bool
    model: str


@router.get(
    "/status",
    response_model=PublicStatus,
    summary="Public GPU/CPU banner state",
)
async def public_status(llm_router: RouterDep) -> PublicStatus:
    snap = await llm_router.status()
    return PublicStatus(
        tier=snap["tier"],
        gpu_online=snap["gpu_online"],
        model=snap["model"],
    )


@router.get(
    "/learning/{session_id}",
    summary="Per-session learning traces summary + improvement proposals",
)
async def session_learning(session_id: str, learning_store: LearningDep) -> dict:
    """What the agent observed in this session and what it PROPOSES (advisory).

    Per-session and ephemeral; proposals require operator approval and are never
    auto-applied. Returns an empty summary when learning is disabled or the
    session is unknown/expired.
    """
    if learning_store is None:
        return {
            "session_id": session_id,
            "observed_requests": 0,
            "proposals": [],
            "note": "Learning is disabled.",
        }
    return learning_store.summary(session_id)
