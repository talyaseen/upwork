"""INTERNAL-ONLY read access to the stored /chat conversation log.

GET /api/admin/conversations        - most-recent-first page of exchanges.
GET /api/admin/conversations/{id}   - a single stored exchange.

There is deliberately NO public read path for stored conversations. Both routes
are gated by ``require_internal`` - the SAME gate as the GPU admin routes:
  (a) the REAL socket peer IP is in ``ADMIN_ALLOWED_CIDRS`` (localhost + prod NAT),
  (b) an ``X-Admin-Token`` header when ``ADMIN_TOKEN`` is set (constant-time),
  (c) any request carrying a forwarding header (XFF / Forwarded / X-Real-IP) is
      rejected outright, and the public reverse-proxy layers never forward the
      ``/api/admin`` path prefix to the app.
This keeps the conversation log free of any IDOR / public-leak surface: an
anonymous visitor (non-loopback peer, or a proxied request) gets 403.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.internal_gate import require_internal
from app.schemas.conversation import ConversationList, ConversationRecord

router = APIRouter(prefix="/api/admin/conversations", tags=["admin"])

InternalOnly = Depends(require_internal)


def _store(request: Request):
    store = getattr(request.app.state, "conversation_store", None)
    if store is None:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation store is not ready.",
        )
    return store


@router.get(
    "",
    response_model=ConversationList,
    summary="List stored /chat conversations (internal-only)",
)
async def list_conversations(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: None = InternalOnly,
) -> ConversationList:
    store = _store(request)
    rows = await store.list_recent(limit=limit, offset=offset)
    total = await store.count()
    return ConversationList(
        total=total,
        count=len(rows),
        limit=limit,
        offset=offset,
        items=[ConversationRecord.model_validate(r) for r in rows],
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationRecord,
    summary="Fetch one stored /chat conversation (internal-only)",
)
async def get_conversation(
    conversation_id: int,
    request: Request,
    _: None = InternalOnly,
) -> ConversationRecord:
    store = _store(request)
    row = await store.get(conversation_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return ConversationRecord.model_validate(row)
