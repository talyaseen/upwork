"""Streaming resource-cleanup + error-mapping tests (BM5, BM9).

All MOCKED: a scripted LLM client stands in for the engine (no GPU, no vLLM).
Covers:
  - BM5: on client DISCONNECT the per-request token generator is aclose()d (the
    upstream generation is stopped, not left running until GC) AND the per-request
    client's HTTP resources are released.
  - BM9: a context-window overflow (engine raises an error carrying
    ``is_context_length_error``) surfaces a clear NoticeEvent + a clean DoneEvent,
    not the generic engine-failure error path.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from app.services.chat_service import (
    CONTEXT_TOO_LONG_NOTICE,
    ChatService,
    DoneEvent,
    MetadataEvent,
    NoticeEvent,
    TokenEvent,
)
from app.services.gpu_router import TIER_GPU, Selection

pytestmark = pytest.mark.asyncio


class _StaticRouter:
    """Router stub that always serves the GPU and never yields mid-stream."""

    def __init__(self, client) -> None:
        self._client = client

    async def select(self, requested_model=None) -> Selection:
        return Selection(self._client, TIER_GPU, self._client.model, None)

    def gpu_yielded(self) -> bool:
        return False


class _TrackingClient:
    """Scripted client that records generator + client close."""

    def __init__(self, tokens: list[str]) -> None:
        self.model = "gpu-7b"
        self._tokens = tokens
        self.gen_closed = False
        self.client_closed = False

    async def stream_chat(self, messages) -> AsyncIterator[str]:
        try:
            for tok in self._tokens:
                yield tok
        finally:
            # Runs on exhaustion OR on aclose() (GeneratorExit) - i.e. the
            # upstream generation is torn down when the consumer stops early.
            self.gen_closed = True

    async def aclose(self) -> None:
        self.client_closed = True


class _ContextLengthClient:
    """Client whose stream raises a context-length error on first token."""

    def __init__(self) -> None:
        self.model = "gpu-7b"
        self.client_closed = False

    async def stream_chat(self, messages) -> AsyncIterator[str]:
        raise _ContextLengthError("prompt exceeds context window")
        yield ""  # pragma: no cover - marks this an async generator

    async def aclose(self) -> None:
        self.client_closed = True


class _ContextLengthError(Exception):
    is_context_length_error = True


def _service(client) -> ChatService:
    return ChatService(
        search_service=None,
        llm_router=_StaticRouter(client),
        settings=SimpleNamespace(
            chat_top_k=4,
            jailbreak_guard_enabled=False,
            mermaid_render_enabled=False,
        ),
    )


async def test_disconnect_closes_generation_and_client():
    client = _TrackingClient(["A", "B", "C", "D", "E"])
    service = _service(client)

    agen = service.stream("review this snippet", skill="code-review")
    # Consume up to the first streamed token, then stop iterating and close the
    # outer stream - exactly what an ASGI server does when the client disconnects.
    got_token = False
    async for ev in agen:
        if isinstance(ev, TokenEvent):
            got_token = True
            break
    assert got_token
    await agen.aclose()

    # PIN (BM5): the upstream generation was stopped, not left running until GC...
    assert client.gen_closed is True
    # ...and the per-request client's HTTP resources were released.
    assert client.client_closed is True


async def test_disconnect_at_metadata_frame_closes_client():
    # Regression pin: a client DISCONNECT at the LEADING metadata frame - before
    # a single token streams - must still release the per-request client. The
    # client-close finally previously started only at the streaming ``gen`` below
    # the metadata yield, so a GeneratorExit raised at that yield exited WITHOUT
    # closing the httpx client (FD leak under refresh-spam). Fails before the fix.
    client = _TrackingClient(["A", "B", "C"])
    service = _service(client)

    agen = service.stream("review this snippet", skill="code-review")
    first = await agen.__anext__()
    # The very first frame is metadata; the model has NOT been asked to stream yet.
    assert isinstance(first, MetadataEvent)
    await agen.aclose()

    # The client is released even though we never reached the streaming section.
    assert client.client_closed is True


async def test_client_closed_on_normal_completion():
    client = _TrackingClient(["A", "B"])
    service = _service(client)

    events = [
        ev
        async for ev in service.stream("review this snippet", skill="code-review")
    ]

    assert any(isinstance(e, DoneEvent) for e in events)
    assert client.gen_closed is True
    assert client.client_closed is True


async def test_context_length_error_maps_to_clear_notice():
    client = _ContextLengthClient()
    service = _service(client)

    events = [
        ev
        async for ev in service.stream("review this snippet", skill="code-review")
    ]

    notices = [e for e in events if isinstance(e, NoticeEvent)]
    done = [e for e in events if isinstance(e, DoneEvent)]
    # PIN (BM9): a clear, actionable notice instead of a generic engine error.
    assert any(n.message == CONTEXT_TOO_LONG_NOTICE for n in notices)
    assert done and done[-1].finish_reason == "error"
    # The per-request client is still released on the error path.
    assert client.client_closed is True
