"""Self-learning visibility through the API (SSE 'learning' + GET endpoint)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.test_chat import _parse_sse

pytestmark = pytest.mark.asyncio


async def test_learning_event_and_endpoint_surface_proposals(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    sid = "sess-test-1"
    # Three same-skill (qa) requests in one session -> a 'hot-skill-qa' proposal.
    last = None
    for _ in range(3):
        last = await client.post(
            "/chat",
            json={"message": "what is semantic search", "session_id": sid},
            headers=auth_headers,
        )
    events = _parse_sse(last.text)
    names = [n for n, _ in events]
    assert "learning" in names
    learning = next(p for n, p in events if n == "learning")
    assert learning["session_id"] == sid
    assert learning["observed_requests"] >= 1
    prop_ids = {p["id"] for p in learning["proposals"]}
    assert "hot-skill-qa" in prop_ids
    for p in learning["proposals"]:
        assert p["status"] == "proposed"
        assert p["requires_operator_approval"] is True

    # The GET endpoint reflects the same per-session state. The app serves
    # this at /learning/{sid} (status router, prefix=""); the live edge adds
    # /api via nginx, which strips it back to /learning before FastAPI.
    resp = await client.get(f"/learning/{sid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["observed_requests"] >= 3
    assert "hot-skill-qa" in {p["id"] for p in body["proposals"]}


async def test_no_learning_event_without_session_id(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/chat", json={"message": "what is semantic search"}, headers=auth_headers
    )
    names = [n for n, _ in _parse_sse(resp.text)]
    assert "learning" not in names  # opt-in only; existing clients unaffected
