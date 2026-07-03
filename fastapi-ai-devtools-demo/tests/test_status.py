"""Public GET /api/status banner endpoint (GPU-only: tier is 'gpu' or 'offline')."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_public_status_safe_fields_only_and_online_under_fake(
    client: AsyncClient,
) -> None:
    resp = await client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    # Only the three safe fields are exposed (no internal details).
    assert set(body) == {"tier", "gpu_online", "model"}
    # The fake backend simulates the GPU being online for the suite.
    assert body["tier"] == "gpu"
    assert body["gpu_online"] is True
    assert isinstance(body["model"], str) and body["model"]


async def test_public_status_offline_while_locked(
    app: FastAPI, client: AsyncClient, tmp_path
) -> None:
    # While the yield lock is set, the banner reports the demo OFFLINE.
    app.state.llm_router._settings.gpu_yield_lock_file = str(tmp_path / "g.lock")
    app.state.llm_router.lock()
    resp = await client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "offline"
    assert body["gpu_online"] is False
    app.state.llm_router.unlock()
