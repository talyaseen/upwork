"""Health and OpenAPI metadata tests."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# Strings that must NEVER appear on the public API surface (owner identity, host
# infrastructure, provider/location, or on-box paths). Case-insensitive. These
# are representative placeholder tokens; a real deployment configures the actual
# sensitive tokens out-of-band via GUARD_REDACT_TERMS in the gitignored .env.
FORBIDDEN_PUBLIC_STRINGS = (
    "acme-owner",
    "example-operator",
    "host-user",
    "example-region",
    "example-datacenter",
    "203.0.113.10",
    "/home/",
    "example-host",
)


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["embedding_backend"] == "hash"
    assert data["embedding_dimension"] == 256
    # Seed corpus is loaded at startup, so the index is non-empty.
    assert data["indexed_chunks"] >= 14


async def test_openapi_schema_is_disabled(client: AsyncClient) -> None:
    """Public demo: the raw OpenAPI schema must not be reachable."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 404


async def test_interactive_docs_are_disabled(client: AsyncClient) -> None:
    """Public demo: /docs and /redoc must not be reachable."""
    for path in ("/docs", "/redoc"):
        resp = await client.get(path)
        assert resp.status_code == 404, f"{path} should be disabled"


async def test_app_metadata_has_no_personal_identity(app: FastAPI) -> None:
    """Regression pin: FastAPI auto-metadata (title/description/contact/schema)
    must not leak the owner's real identity or host infrastructure.

    Pins the red-team finding that /openapi.json previously exposed an owner
    name via info.contact.name and a "Built by ..." string in info.description.
    """
    # No contact block (it previously carried the real name).
    assert app.contact is None
    # Force-generate the schema even though the public HTTP route is disabled,
    # so the pin covers title/description/tags/contact regardless of exposure.
    schema_text = json.dumps(app.openapi()).lower()
    for needle in FORBIDDEN_PUBLIC_STRINGS:
        assert needle not in schema_text, (
            f"forbidden string {needle!r} present in generated OpenAPI schema"
        )
