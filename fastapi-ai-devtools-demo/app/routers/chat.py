"""Conversational, grounded (RAG) chat over the corpus.

POST /chat retrieves relevant corpus passages, serves the GPU 7B when the GPUs are
free for the demo (GPU-ONLY: no CPU fallback), grounds the model in the retrieved
passages, and STREAMS the answer as Server-Sent Events.

The endpoint is admission-controlled: a global concurrency limiter + FIFO queue
bounds RAM on the public demo. Requests that have to wait are streamed their queue
position; if the queue is full they get a clean "busy".

SSE contract (events; `queue`/`notice` are optional and conditional):

    event: queue    (0+ times, only while waiting)
    data: {"position": 2, "status": "waiting"}

    event: metadata (exactly once)
    data: {"model": "...", "retrieved": 4, "backend_tier": "primary-7b-gpu",
           "notice": null, "citations": [ {Citation}, ... ]}

    event: notice   (0+ times: the demo went OFFLINE - GPU yielded to training,
                     either at request start or mid-stream)
    data: {"message": "The live demo ... is paused right now ...", ...}

    event: token    (many)
    data: {"text": "Based "}

    event: done     (exactly once; finish_reason "stop", or "offline" when the GPU
                     is unavailable / yielded mid-stream, "blocked" when guarded)
    data: {"finish_reason": "stop"}

On a full queue: a single `busy` event then `done` (finish_reason "busy"). On an
LLM failure: an `error` event then `done` (finish_reason "error").
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import (
    ConversationDep,
    CurrentUser,
    GateDep,
    LearningDep,
    RouterDep,
    SearchDep,
)
from app.schemas.chat import ChatRequest
from app.services.chat_service import (
    ArtifactEvent,
    ChatService,
    DoneEvent,
    LearningEvent,
    MetadataEvent,
    NoticeEvent,
    TokenEvent,
)
from app.services.generation_gate import QueueFull

logger = logging.getLogger("app.chat")

router = APIRouter(tags=["chat"])


def _sse(event: str, payload: dict) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


# Documentation-only response model so /docs advertises the endpoint as an
# event-stream rather than an empty 200. The real body is the SSE byte stream.
class ChatStreamAck(BaseModel):
    detail: str = "Server-Sent Events stream (text/event-stream)."


@router.post(
    "/chat",
    summary="Conversational, grounded (RAG) chat - streamed",
    description=(
        "Retrieve the most relevant corpus passages, serve the GPU 7B when the "
        "GPUs are free for the demo (GPU-ONLY: no CPU fallback - the demo goes "
        "OFFLINE when the GPUs serve training, including a dynamic mid-stream "
        "yield), ground the model in the retrieved context, and STREAM a "
        "conversational answer as Server-Sent Events. Admission-controlled by a "
        "concurrency limiter + FIFO queue. Supports multi-turn via `history`. "
        "Requires authentication. The LLM runs locally (OpenJarvis: vLLM on GPU); "
        "no paid external API is contacted."
    ),
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "SSE stream of queue, metadata, notice, token, done.",
        }
    },
)
async def chat(
    payload: ChatRequest,
    search_service: SearchDep,
    llm_router: RouterDep,
    gate: GateDep,
    learning_store: LearningDep,
    conversation_store: ConversationDep,
    _: CurrentUser,
) -> StreamingResponse:
    settings = get_settings()
    service = ChatService(
        search_service=search_service,
        llm_router=llm_router,
        settings=settings,
        learning_store=learning_store,
        conversation_store=conversation_store,
    )

    async def event_stream() -> AsyncIterator[str]:
        # Admission control: bound concurrent generations.
        try:
            ticket = await gate.admit()
        except QueueFull:
            yield _sse(
                "busy",
                {
                    "message": (
                        "The demo is at capacity right now. Please try again in "
                        "a few seconds."
                    ),
                    "retry_after_seconds": 5,
                },
            )
            yield _sse("done", {"finish_reason": "busy"})
            # 2026-07-01 persistence audit: a full queue is real, operationally
            # useful signal (capacity pressure) - the operator wants EVERY
            # turn that reaches a response recorded, not just successful
            # answers. No model ever ran, so there is no answer text; the
            # store's own defaults ("unknown"/"qa") absorb the missing fields.
            # Guarded (store is always set in production - see main.py - but
            # the dependency type allows None, same defensive pattern as
            # ChatService._persist).
            if conversation_store is not None:
                await conversation_store.save(
                    user_message=payload.message,
                    assistant_response="",
                    model="unknown",
                    backend_tier="queue-full",
                    finish_reason="busy",
                    skill=payload.skill,
                    session_id=payload.session_id,
                )
            return

        # Accumulated across the loop so an LLM failure MID-STREAM (below) can
        # still persist whatever partial answer + model/tier info was already
        # observed, instead of silently dropping the turn (2026-07-01 audit).
        collected_text: list[str] = []
        last_model = "unknown"
        last_backend_tier = "unknown"
        try:
            # Stream the queue position while waiting for a slot (nothing is
            # emitted when a slot is free).
            queued = False
            async for position in ticket.wait_for_slot():
                queued = True
                yield _sse("queue", {"position": position, "status": "waiting"})

            async for event in service.stream(
                message=payload.message,
                history=payload.history,
                top_k=payload.top_k,
                requested_model=payload.model,
                skill=payload.skill,
                session_id=payload.session_id,
                queued=queued,
            ):
                if isinstance(event, MetadataEvent):
                    last_model = event.model
                    last_backend_tier = event.backend_tier
                    yield _sse(
                        "metadata",
                        {
                            "model": event.model,
                            "retrieved": event.retrieved,
                            "backend_tier": event.backend_tier,
                            "notice": event.notice,
                            # The skill the per-turn intent router chose for this
                            # message (may differ from the sticky selector) so the
                            # UI can reflect the mode that actually ran.
                            "skill": event.skill,
                            "citations": [
                                c.model_dump() for c in event.citations
                            ],
                        },
                    )
                elif isinstance(event, NoticeEvent):
                    yield _sse(
                        "notice",
                        {
                            "message": event.message,
                            "model": event.model,
                            "backend_tier": event.backend_tier,
                        },
                    )
                elif isinstance(event, TokenEvent):
                    collected_text.append(event.text)
                    yield _sse("token", {"text": event.text})
                elif isinstance(event, LearningEvent):
                    yield _sse(
                        "learning",
                        {
                            "session_id": event.session_id,
                            "observed_requests": event.observed_requests,
                            "proposals": event.proposals,
                        },
                    )
                elif isinstance(event, ArtifactEvent):
                    yield _sse(
                        "artifact",
                        {
                            "kind": event.kind,
                            "format": event.fmt,
                            "source": event.source,
                            "svg": event.svg,
                            # Download formats in priority order (PDF primary).
                            # PDF is generated client-side; the backend ships only
                            # canonical text/SVG (no server-side PDF exec).
                            "downloads": event.downloads,
                        },
                    )
                elif isinstance(event, DoneEvent):
                    yield _sse("done", {"finish_reason": event.finish_reason})
        except Exception as exc:  # noqa: BLE001 - surface as a stream error
            logger.exception("Chat generation failed")
            yield _sse(
                "error",
                {
                    "message": (
                        "The language model could not complete the response. "
                        "Check that the local LLM service is reachable."
                    ),
                    "type": exc.__class__.__name__,
                },
            )
            yield _sse("done", {"finish_reason": "error"})
            # 2026-07-01 persistence audit: ChatService.stream() already
            # persists every path that returns normally (success, guard-block,
            # offline). An exception raised WHILE iterating it (e.g. the LLM
            # backend dies mid-stream) previously skipped persistence
            # entirely - this was the one real gap. Record whatever partial
            # answer + model/tier were observed before the failure. Guarded
            # (store is always set in production - see main.py - but the
            # dependency type allows None; same defensive pattern as
            # ChatService._persist).
            if conversation_store is not None:
                await conversation_store.save(
                    user_message=payload.message,
                    assistant_response="".join(collected_text),
                    model=last_model,
                    backend_tier=last_backend_tier,
                    finish_reason="error",
                    skill=payload.skill,
                    session_id=payload.session_id,
                )
        finally:
            await ticket.release()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
