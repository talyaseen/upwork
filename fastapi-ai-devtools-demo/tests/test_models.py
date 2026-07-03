"""GET /models + /chat serving (offline, fake backend simulates the GPU online).

GPU-ONLY demo: the catalog has a single GPU model and there is no CPU fallback.
The fake backend simulates the GPU being online so the chat path produces tokens.
The OFFLINE path (GPU unavailable) is unit-tested in test_gpu_router / test_preemption.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.test_chat import _parse_sse

pytestmark = pytest.mark.asyncio


async def test_models_endpoint_is_gpu_only(client: AsyncClient) -> None:
    resp = await client.get("/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["default"] == "auto"
    # The fake backend simulates the GPU being online for the test suite.
    assert body["gpu_available"] is True
    # GPU-only: a single model, requires_gpu, no CPU tier anywhere.
    assert len(body["models"]) == 1
    only = body["models"][0]
    assert only["requires_gpu"] is True
    assert only["tier"] == "gpu"
    assert only["available"] is True
    assert not any(m["tier"] == "cpu" for m in body["models"])


async def test_chat_serves_the_gpu_model(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/chat",
        json={"message": "what is semantic search"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    metadata = next(p for n, p in events if n == "metadata")
    assert metadata["backend_tier"] == "primary-7b-gpu"
    assert any(n == "token" for n, _ in events)
    assert events[-1][0] == "done"
    assert events[-1][1]["finish_reason"] == "stop"
