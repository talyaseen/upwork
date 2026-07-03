"""Dynamic GPU preemption tests (mid-stream offline + background preemptor).

All MOCKED: no real GPU. GPU-ONLY demo: when training reclaims the GPU there is NO
CPU fallback - the in-flight request stops and the demo goes OFFLINE, and the
preemptor drops the GPU model (stops vLLM to release VRAM) and routes new requests
to offline until the GPU is free again.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from app.services.chat_service import (
    ChatService,
    DoneEvent,
    NoticeEvent,
    TokenEvent,
)
from app.services.gpu_preemptor import GpuPreemptor
from app.services.gpu_router import TIER_GPU, TIER_OFFLINE, GpuRouter, Selection
from app.services.model_catalog import ModelCatalog, ModelEntry
from app.services.openjarvis_engine import VllmController

pytestmark = pytest.mark.asyncio

GPU = ModelEntry("gpu-7b", "GPU 7B", "gpu", "", True)


class _ScriptedClient:
    def __init__(self, model: str, tokens: list[str]) -> None:
        self.model = model
        self._tokens = tokens

    async def stream_chat(self, messages) -> AsyncIterator[str]:
        for tok in self._tokens:
            yield tok


class _ReclaimRouter:
    """Router stub: serves GPU, then reports yielded after the first token."""

    def __init__(self, gpu_client) -> None:
        self._gpu = gpu_client
        self._checks = 0

    async def select(self, requested_model=None) -> Selection:
        return Selection(self._gpu, TIER_GPU, self._gpu.model, None)

    def gpu_yielded(self) -> bool:
        # False on the first check (one GPU token streams), True afterwards.
        self._checks += 1
        return self._checks > 1


async def test_mid_stream_goes_offline_with_notice():
    gpu_client = _ScriptedClient("gpu-7b", ["G1 ", "G2 ", "G3 "])
    router = _ReclaimRouter(gpu_client)
    service = ChatService(
        search_service=None,
        llm_router=router,
        settings=SimpleNamespace(
            chat_top_k=4, jailbreak_guard_enabled=False, mermaid_render_enabled=False
        ),
    )
    # Non-grounded skill so no retrieval is needed.
    events = [
        ev async for ev in service.stream("review this", skill="code-review")
    ]

    tokens = [e.text for e in events if isinstance(e, TokenEvent)]
    notices = [e for e in events if isinstance(e, NoticeEvent)]
    done = [e for e in events if isinstance(e, DoneEvent)]
    # One GPU token streamed, then the demo went OFFLINE (no CPU continuation).
    assert tokens == ["G1 "]
    assert len(notices) == 1
    assert notices[0].backend_tier == TIER_OFFLINE
    assert "paused" in notices[0].message.lower()
    assert done and done[-1].finish_reason == "offline"


def _preemptor_router(foreign: bool):
    monitor = SimpleNamespace(
        is_idle_cached=lambda: not foreign,
        # Foreign detection is by GPU USAGE (VRAM ceiling), not the process table.
        foreign_over_ceiling=lambda ceiling_mb: foreign,
    )
    catalog = ModelCatalog([GPU], default_id="auto")
    return GpuRouter(
        settings=SimpleNamespace(
            llm_backend="openjarvis",
            openai_model="gpu-7b",
            gpu_hysteresis_count=2,
            gpu_yield_lock_file="/nonexistent/openjarvis/gpu_off.lock",
            gpu_demo_mem_ceiling_mb=14336,
        ),
        monitor=monitor,
        catalog=catalog,
        client_factory=lambda tier, model: SimpleNamespace(model=f"{tier}:{model}"),
        vllm_health=lambda: True,
    )


async def test_preemptor_reclaims_and_releases_gpu():
    router = _preemptor_router(foreign=True)
    controller = VllmController()
    controller.mark_started()
    preemptor = GpuPreemptor(
        router=router, settings=router._settings, controller=controller
    )

    # Foreign process present -> reclaim GPU + stop vLLM to release VRAM.
    await preemptor.check_once()
    assert router.is_reclaimed() is True
    assert controller.stop_calls >= 1
    assert controller.is_running() is False

    # GPU clears: needs gpu_hysteresis_count (2) clear ticks before releasing.
    router._monitor.foreign_over_ceiling = lambda ceiling_mb: False
    await preemptor.check_once()
    assert router.is_reclaimed() is True   # 1 clear tick, not yet
    await preemptor.check_once()
    assert router.is_reclaimed() is False  # 2 clear ticks -> released
