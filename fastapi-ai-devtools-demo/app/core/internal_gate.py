"""Internal-only access gate.

Shared by the GPU admin routes (``/api/admin/*``) and the document-write routes
(``POST``/``DELETE`` ``/documents``). Both are operator/curator surfaces that must
NEVER be reachable by the public: admin controls the GPU-yield lock; document
writes mutate the SHARED corpus that the public ``/search`` and ``/ask`` serve to
everyone (an open write path is a corpus-poisoning vector).

ACCESS CONTROL (independent layers - all must hold):
  (a) the REAL socket peer IP is inside ``ADMIN_ALLOWED_CIDRS`` (localhost + the
      prod/dev NAT). X-Forwarded-For is NOT trusted, AND any request carrying a
      forwarding header (XFF / Forwarded / X-Real-IP / X-Forwarded-Host) is
      REJECTED outright - a legitimate internal caller reaches the app DIRECTLY,
      so a forwarding header means the request was proxied (the exact vector that
      can spoof the peer IP if uvicorn is mis-run with --proxy-headers).
  (b) a shared secret ``X-Admin-Token`` (when ``ADMIN_TOKEN`` is set) - independent
      of IP, so it holds even if the IP gate is somehow defeated. Set it for
      go-live (constant-time compared).
  (c) the public reverse-proxy layers NEVER forward these paths to the app.

Public traffic reaches FastAPI as 127.0.0.1 (via the local mTLS reverse proxy),
which WOULD pass the localhost allow - so (b)+(c) are what keep the public out.
NEVER run uvicorn with --proxy-headers / a permissive --forwarded-allow-ips for
this service (it would let X-Forwarded-For rewrite the peer IP).
"""

from __future__ import annotations

import hmac
import ipaddress

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

# Headers whose presence means the request was proxied (not a direct internal call).
_FORWARDING_HEADERS = (
    "x-forwarded-for",
    "forwarded",
    "x-real-ip",
    "x-forwarded-host",
)


def _peer_allowed(request: Request, cidrs: list[str]) -> bool:
    """True iff the REAL socket peer IP is inside one of the allowed CIDRs."""
    client = request.client
    if client is None or not client.host:
        return False
    try:
        ip = ipaddress.ip_address(client.host)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _forbid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This endpoint is restricted to the internal network.",
    )


def require_internal(request: Request) -> None:
    """Gate internal-only routes: reject proxied requests, require the peer IP
    allowlist, and (when configured) a shared admin token - all independent
    layers."""
    settings = get_settings()
    # 1. A direct internal call carries NO forwarding header. Its presence means
    #    the request was proxied -> reject (defeats peer-IP spoofing via XFF).
    if getattr(settings, "admin_reject_forwarded", True):
        for h in _FORWARDING_HEADERS:
            if h in request.headers:
                raise _forbid()
    # 2. Real socket peer IP must be in the allowlist.
    if not _peer_allowed(request, settings.admin_allowed_cidrs_list):
        raise _forbid()
    # 3. Shared admin token (defense-in-depth), required when configured.
    token = getattr(settings, "admin_token", "") or ""
    if token:
        provided = request.headers.get("x-admin-token", "")
        if not hmac.compare_digest(provided, token):
            raise _forbid()
