"""Admin GPU-lock endpoints: internal-IP gating + lock/unlock/status."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


def _client_from(app: FastAPI, peer: tuple[str, int]) -> AsyncClient:
    """An ASGI client whose REAL socket peer IP is `peer` (host, port)."""
    transport = ASGITransport(app=app, client=peer)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_lock_unlock_status_from_localhost(app: FastAPI, tmp_path) -> None:
    lock = tmp_path / "gpu_off.lock"
    app.state.llm_router._settings.gpu_yield_lock_file = str(lock)

    async with _client_from(app, ("127.0.0.1", 5000)) as c:
        r = await c.post("/api/admin/gpu/lock")
        assert r.status_code == 200
        assert r.json()["lock_present"] is True
        assert r.json()["tier"] == "offline"
        assert lock.exists()

        s = await c.get("/api/admin/gpu")
        assert s.status_code == 200
        assert s.json()["lock_present"] is True

        r2 = await c.post("/api/admin/gpu/unlock")
        assert r2.status_code == 200
        assert r2.json()["lock_present"] is False
        assert not lock.exists()


async def test_admin_forbidden_from_public_ip(app: FastAPI) -> None:
    async with _client_from(app, ("203.0.113.9", 5555)) as c:
        for method, path in (
            ("post", "/api/admin/gpu/lock"),
            ("post", "/api/admin/gpu/unlock"),
            ("get", "/api/admin/gpu"),
        ):
            r = await getattr(c, method)(path)
            assert r.status_code == 403


async def test_admin_does_not_trust_x_forwarded_for(app: FastAPI) -> None:
    # A public peer cannot spoof an internal IP via X-Forwarded-For.
    async with _client_from(app, ("203.0.113.9", 5555)) as c:
        r = await c.post(
            "/api/admin/gpu/lock",
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        assert r.status_code == 403


async def test_admin_allows_nat_range(app: FastAPI, tmp_path) -> None:
    app.state.llm_router._settings.gpu_yield_lock_file = str(tmp_path / "g.lock")
    async with _client_from(app, ("10.0.0.42", 6000)) as c:
        r = await c.get("/api/admin/gpu")
        assert r.status_code == 200


async def test_admin_rejects_allowed_ip_when_request_is_proxied(app: FastAPI) -> None:
    # Even from an allowed peer IP, a request carrying a forwarding header is
    # rejected: a direct internal call never has one, so its presence means the
    # request was proxied (the exact peer-IP-spoofing vector).
    async with _client_from(app, ("127.0.0.1", 5000)) as c:
        for hdr in ("X-Forwarded-For", "Forwarded", "X-Real-IP"):
            r = await c.post("/api/admin/gpu/lock", headers={hdr: "10.0.0.1"})
            assert r.status_code == 403, hdr


async def test_admin_token_required_when_configured(app: FastAPI, tmp_path) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.admin_token = "s3cr3t-admin"
    app.state.llm_router._settings.gpu_yield_lock_file = str(tmp_path / "g.lock")
    try:
        async with _client_from(app, ("127.0.0.1", 5000)) as c:
            # Allowed IP but no/wrong token -> 403.
            assert (await c.get("/api/admin/gpu")).status_code == 403
            assert (
                await c.get(
                    "/api/admin/gpu", headers={"X-Admin-Token": "wrong"}
                )
            ).status_code == 403
            # Correct token -> 200.
            ok = await c.get(
                "/api/admin/gpu", headers={"X-Admin-Token": "s3cr3t-admin"}
            )
            assert ok.status_code == 200
    finally:
        settings.admin_token = ""
