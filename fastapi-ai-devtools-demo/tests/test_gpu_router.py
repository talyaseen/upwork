"""GpuRouter unit tests - GPU-or-OFFLINE selection, fail-safe, reclaim, lock.

GPU-ONLY demo (operator decision 2026-06-30): the router serves the 7B on the GPU
when it is available, otherwise it reports OFFLINE - there is NO CPU fallback. The
GPU path is MOCKED: a fake vLLM-health probe + a fake VRAM-ceiling foreign check
drive the decision; a fake client factory records the chosen (tier, model).

"Available" = vLLM healthy AND not yielded (no lock / not reclaimed) AND no foreign
process co-resident (by GPU usage, not the process table). The offline "fake"
backend simulates the GPU being online so the chat suite can run without a model.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from app.services.gpu_router import TIER_GPU, TIER_OFFLINE, GpuRouter
from app.services.model_catalog import ModelCatalog, ModelEntry

pytestmark = pytest.mark.asyncio

GPU = ModelEntry("gpu-7b", "GPU 7B", "gpu", "", True)


class _FakeClient:
    def __init__(self, model: str) -> None:
        self.model = model

    async def stream_chat(self, messages) -> AsyncIterator[str]:  # pragma: no cover
        yield ""


def _make_router(
    *, healthy=True, foreign=False, backend="openjarvis", health_exc=None,
) -> GpuRouter:
    def vllm_health():
        if health_exc is not None:
            raise health_exc
        return healthy

    monitor = SimpleNamespace(
        is_idle_cached=lambda: not foreign,
        foreign_over_ceiling=lambda ceiling_mb: foreign,
    )
    catalog = ModelCatalog([GPU], default_id="auto")
    return GpuRouter(
        settings=SimpleNamespace(
            llm_backend=backend,
            openai_model="gpu-7b",
            gpu_yield_lock_file="/nonexistent/openjarvis/gpu_off.lock",
            gpu_demo_mem_ceiling_mb=14336,
        ),
        monitor=monitor,
        catalog=catalog,
        client_factory=lambda tier, model: _FakeClient(f"{tier}:{model}"),
        vllm_health=vllm_health,
    )


async def test_serves_gpu_when_healthy():
    sel = await _make_router(healthy=True).select("auto")
    assert sel.backend_tier == TIER_GPU
    assert sel.model == "gpu-7b"
    assert sel.client is not None and sel.client.model == "gpu:gpu-7b"
    assert sel.is_offline is False
    assert sel.notice is None


async def test_offline_when_vllm_unhealthy():
    sel = await _make_router(healthy=False).select("auto")
    assert sel.backend_tier == TIER_OFFLINE
    assert sel.client is None and sel.is_offline is True
    assert sel.notice  # an offline notice for the UI


async def test_offline_when_foreign_co_resident():
    sel = await _make_router(foreign=True).select("auto")
    assert sel.backend_tier == TIER_OFFLINE
    assert sel.is_offline is True


async def test_offline_when_reclaimed_then_back_online():
    router = _make_router(healthy=True)
    router.reclaim_gpu()
    assert (await router.select("auto")).is_offline is True
    router.release_reclaim()
    assert (await router.select("auto")).backend_tier == TIER_GPU


async def test_fail_safe_offline_on_health_error():
    sel = await _make_router(health_exc=RuntimeError("nvidia-smi blew up")).select(
        "auto"
    )
    assert sel.backend_tier == TIER_OFFLINE


async def test_fake_backend_simulates_online_gpu():
    # The offline test backend serves the GPU tier so the chat suite produces
    # tokens (there is no CPU tier to fall back to).
    sel = await _make_router(healthy=True, backend="fake").select("auto")
    assert sel.backend_tier == TIER_GPU


async def test_gpu_served_with_resident_vllm_even_though_raw_idle_false():
    """Regression pin (2026-06-30): a resident demo vLLM makes the raw nvidia-smi
    idle gate read busy (its own VRAM), and host-namespace PIDs are unmatchable -
    yet the router MUST serve the GPU because vLLM is healthy and no FOREIGN
    process is co-resident. Decided by GPU USAGE (under the ceiling) + health, not
    the process table."""
    router = _make_router(healthy=True, foreign=False)
    router._monitor.is_idle_cached = lambda: False  # raw gate reads "busy"
    sel = await router.select("auto")
    assert sel.backend_tier == TIER_GPU


async def test_get_client_backcompat_returns_none_when_offline():
    client, tier = await _make_router(foreign=True).get_client()
    assert tier == TIER_OFFLINE and client is None


async def test_lock_file_forces_offline(tmp_path):
    lock = tmp_path / "gpu_off.lock"
    router = _make_router(healthy=True)
    router._settings.gpu_yield_lock_file = str(lock)

    assert (await router.select("auto")).backend_tier == TIER_GPU
    lock.write_text("yield")
    assert router.gpu_yielded() is True
    assert (await router.select("auto")).backend_tier == TIER_OFFLINE
    lock.unlink()
    assert (await router.select("auto")).backend_tier == TIER_GPU


async def test_router_lock_unlock_manages_file(tmp_path):
    lock = tmp_path / "sub" / "gpu_off.lock"
    router = _make_router()
    router._settings.gpu_yield_lock_file = str(lock)
    assert router.lock_present() is False
    router.lock()
    assert lock.exists() and router.lock_present() is True
    router.unlock()
    assert not lock.exists() and router.lock_present() is False
    router.unlock()  # idempotent
