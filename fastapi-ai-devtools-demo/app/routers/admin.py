"""Internal-only admin endpoints to control the GPU-yield lock.

POST /api/admin/gpu/lock   - create the lock file: force CPU (get off the GPU).
POST /api/admin/gpu/unlock - remove the lock file: allow the GPU again, used iff
                             nvidia-smi reports it idle (and no training process).
GET  /api/admin/gpu        - current state (lock present? gpu idle? served tier?).

The lock FILE is the single source of truth; the backend owns it (the operator
never touches files by hand). ``unlock`` only clears the MANUAL override - the
nvidia-smi check and training-process detection STILL force CPU whenever the GPU
is actually busy, so a stray ``unlock`` can never cause contention with training.

ACCESS CONTROL (THREE independent layers - all must hold):
  (a) the REAL socket peer IP is inside ``ADMIN_ALLOWED_CIDRS`` (localhost + the
      prod/dev NAT). X-Forwarded-For is NOT trusted, AND any request carrying a
      forwarding header (XFF / Forwarded / X-Real-IP) is REJECTED outright - a
      legitimate internal caller reaches the app DIRECTLY, so a forwarding header
      means the request was proxied (and is the exact vector that can spoof the
      peer IP if uvicorn is mis-run with --proxy-headers).
  (b) a shared secret ``X-Admin-Token`` (when ``ADMIN_TOKEN`` is set) - independent
      of IP, so it holds even if the IP gate is somehow defeated. Set it for
      go-live (constant-time compared).
  (c) the public reverse-proxy layers NEVER forward /api/admin to the app.

Public traffic reaches FastAPI as 127.0.0.1 (via the local mTLS reverse proxy),
which WOULD pass the localhost allow - so (b)+(c) are what keep the public out.
NEVER run uvicorn with --proxy-headers / a permissive --forwarded-allow-ips for
this service (it would let X-Forwarded-For rewrite the peer IP). The app must also
bind the internal interface with the host firewall restricting the port to
localhost + 10.0.0.0/24 so a 10.0.0.x box can reach it directly while the public
IP cannot.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import RouterDep
from app.core.internal_gate import require_internal

router = APIRouter(prefix="/api/admin", tags=["admin"])

InternalOnly = Depends(require_internal)


@router.post("/gpu/lock", summary="Force CPU: set the GPU-yield lock")
async def gpu_lock(llm_router: RouterDep, _: None = InternalOnly) -> dict:
    llm_router.lock()
    return await llm_router.status()


@router.post("/gpu/unlock", summary="Clear the manual GPU-yield lock")
async def gpu_unlock(llm_router: RouterDep, _: None = InternalOnly) -> dict:
    llm_router.unlock()
    return await llm_router.status()


@router.get("/gpu", summary="GPU lock + idle state and served tier")
async def gpu_status(llm_router: RouterDep, _: None = InternalOnly) -> dict:
    return await llm_router.status()
