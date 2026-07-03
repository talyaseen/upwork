"""Test configuration and fixtures.

The suite runs entirely offline: it forces the deterministic ``hash`` embedding
backend so no model weights are ever downloaded, and each test gets a fresh
temporary SQLite database for isolation. The application's real code paths
(routers, services, DB, JWT auth) are exercised end to end through an ASGI
transport with the lifespan events run.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest_asyncio

# Configure the environment BEFORE the application package is imported so that
# pydantic-settings and the engine factory pick up the test values.
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["HASH_EMBEDDING_DIM"] = "256"
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-production"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["SEED_ON_STARTUP"] = "true"
# Keep the suite HERMETIC: never inherit deploy secrets from a local .env. The
# internal-gate tests (admin + document writes) assume the token layer is OFF by
# default and exercise it explicitly where needed, so pin ADMIN_TOKEN empty here.
os.environ["ADMIN_TOKEN"] = ""
# Force the deterministic, network-free LLM backend so the /chat suite never
# loads a model or contacts a real OpenAI-compatible server (incl. Ollama).
os.environ["LLM_BACKEND"] = "fake"

from asgi_lifespan import LifespanManager  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db import database as db_module  # noqa: E402


@pytest_asyncio.fixture
async def app(tmp_path) -> AsyncIterator[FastAPI]:
    """Build a fresh app (own DB, lifespan run) and yield the app instance.

    Exposed so tests can install dependency overrides (e.g. swap in a
    recording LLM client). The ``client`` fixture is built on top of this.
    """
    db_file = tmp_path / f"test_{uuid.uuid4().hex}.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"

    # Reset cached settings and the engine singletons so this test's
    # DATABASE_URL takes effect.
    get_settings.cache_clear()
    db_module._engine = None
    db_module._session_factory = None

    # Import here so create_app() reads the freshly cleared settings cache.
    from app.main import create_app

    application = create_app()
    # 30s startup budget: the hash embedder + seeding is fast, but under
    # heavy test-suite load (many concurrent app fixtures) 5s is too tight.
    async with LifespanManager(application, startup_timeout=30, shutdown_timeout=10):
        yield application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Yield an HTTP client that models a PUBLIC visitor.

    The peer IP is a documentation-range address (203.0.113.x), so the
    internal-only gate treats it as external - exactly what an anonymous or
    self-registered visitor looks like. (ASGITransport otherwise defaults the
    peer to loopback, which the gate would wrongly admit.) Public read endpoints
    are unaffected; only the internal-only write/admin routes reject it.
    """
    transport = ASGITransport(app=app, client=("203.0.113.10", 5555))
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def internal_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Yield a client whose REAL socket peer is 127.0.0.1 (INTERNAL/curator).

    Document writes (POST/DELETE /documents) and the GPU admin routes are
    internal-only; they pass the peer-IP allowlist through this client. The test
    env leaves ADMIN_TOKEN unset, so the peer-IP layer alone admits it. Shares
    the same ``app`` instance (DB + index) as the public ``client`` fixture.
    """
    transport = ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register and log in a user, returning an Authorization header dict."""
    username = f"user_{uuid.uuid4().hex[:10]}"
    password = "supersecret123"
    reg = await client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
