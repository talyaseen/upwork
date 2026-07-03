"""GPU-idle router: picks GPU (7B) vs CPU (small) per request, fail-safe to CPU.

The 2x T4 are production training GPUs. This router decides, per request, whether
to serve the demo's 7B model on the GPU (only when the GPU is genuinely idle AND
our vLLM engine is healthy) or to use the small CPU fallback. It reconciles the
user's model choice with that guardrail and surfaces which backend actually
served the request.

It also carries the DYNAMIC PREEMPTION flag: when the background preemptor detects
training reclaiming the GPU, it sets ``reclaim_gpu()`` and every subsequent
selection routes to the CPU until the GPU is released again.

FAIL SAFE everywhere: any error in the decision path resolves to the CPU model.
We never assume the GPU is free and never contend with training.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

from app.core.config import Settings
from app.services.llm_client import LLMClient
from app.services.model_catalog import ModelCatalog

logger = logging.getLogger("app.router")

TIER_GPU = "primary-7b-gpu"
# GPU-only demo: when the GPU is not serving, the demo is OFFLINE (there is no CPU
# fallback - serving a weaker, more-jailbreakable small model was deliberately
# dropped, operator decision 2026-06-30).
TIER_OFFLINE = "offline"

OFFLINE_NOTICE = (
    "The live demo runs on self-hosted GPUs that are currently serving model "
    "training, so it is paused right now. Please try again shortly - it comes "
    "back automatically when the GPUs are free."
)


@dataclass(slots=True)
class Selection:
    """The router's per-request decision (``client`` is None when OFFLINE)."""

    client: LLMClient | None
    backend_tier: str
    model: str
    notice: str | None = None

    @property
    def is_offline(self) -> bool:
        return self.client is None or self.backend_tier == TIER_OFFLINE


def _default_factory(settings: Settings):
    def factory(tier: str, model: str) -> LLMClient:
        from app.services.llm_client import build_chat_client

        return build_chat_client(settings, tier=tier, model=model)

    return factory


def _default_vllm_health(settings: Settings):
    def health() -> bool:
        from app.services.openjarvis_engine import vllm_healthy

        return vllm_healthy(settings)

    return health


class GpuRouter:
    """Selects the LLM client for each request and exposes the GPU verdict."""

    def __init__(
        self,
        *,
        settings: Settings,
        primary: LLMClient | None = None,
        fallback: LLMClient | None = None,
        monitor=None,
        catalog: ModelCatalog | None = None,
        client_factory=None,
        vllm_health=None,
    ) -> None:
        # ``primary``/``fallback`` are accepted for backward compatibility but no
        # longer used: clients are built per-request via the factory, and there is
        # no CPU fallback (GPU-only demo).
        self._settings = settings
        # Lazy import keeps GpuMonitor optional for callers that inject one.
        if monitor is None:
            from app.services.gpu_monitor import GpuMonitor

            monitor = GpuMonitor(settings)
        self._monitor = monitor
        self._catalog = catalog or ModelCatalog.from_settings(settings)
        self._factory = client_factory or _default_factory(settings)
        self._vllm_health = vllm_health or _default_vllm_health(settings)
        # Set => the GPU has been reclaimed by training; route everything to CPU.
        self._reclaimed = asyncio.Event()

    # -- preemption flag (driven by the background preemptor) ------------

    def reclaim_gpu(self) -> None:
        """Mark the GPU as reclaimed by training: route all new requests to CPU."""
        if not self._reclaimed.is_set():
            logger.warning("GPU reclaimed by training: routing all requests to CPU.")
        self._reclaimed.set()

    def release_reclaim(self) -> None:
        """The GPU is idle again: allow GPU selection for new requests."""
        if self._reclaimed.is_set():
            logger.info("GPU released: GPU routing re-enabled.")
        self._reclaimed.clear()

    def is_reclaimed(self) -> bool:
        return self._reclaimed.is_set()

    # -- GPU-yield lock file (manual "get off GPU" override) -------------

    def lock_present(self) -> bool:
        """True if the GPU-yield lock file exists (demo goes offline regardless)."""
        try:
            return os.path.exists(self._settings.gpu_yield_lock_file)
        except OSError as exc:  # pragma: no cover - stat almost never raises
            logger.debug("lock_present check failed: %s", exc)
            return False

    def lock(self) -> None:
        """Create the GPU-yield lock (demo offline). The backend owns this file."""
        path = self._settings.gpu_yield_lock_file
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            fh.write("gpu yielded by admin\n")
        logger.warning("GPU-yield lock SET (%s): demo offline.", path)

    def unlock(self) -> None:
        """Remove the GPU-yield lock (allow GPU again iff it is free)."""
        path = self._settings.gpu_yield_lock_file
        try:
            os.remove(path)
            logger.info("GPU-yield lock CLEARED (%s).", path)
        except FileNotFoundError:
            pass

    def gpu_yielded(self) -> bool:
        """True if the GPU must be yielded: training reclaimed it OR the lock file
        is present. The demo then goes OFFLINE (no CPU fallback).

        nvidia-smi usage is handled separately in ``gpu_available``; this is the
        cheap, synchronous override checked between tokens for mid-stream
        preemption and at the per-request start gate.
        """
        return self._reclaimed.is_set() or self.lock_present()

    @property
    def catalog(self) -> ModelCatalog:
        return self._catalog

    @property
    def monitor(self):
        return self._monitor

    # -- GPU availability -----------------------------------------------

    def _foreign_on_gpu(self) -> bool:
        """True if a NON-demo process is co-resident on the GPU (best effort).

        Uses the namespace-robust VRAM-ceiling check. Tolerant of injected monitors
        that do not implement it (returns False => "no foreign detected"), since the
        authoritative yield signal is the lock file.
        """
        check = getattr(self._monitor, "foreign_over_ceiling", None)
        ceiling = getattr(self._settings, "gpu_demo_mem_ceiling_mb", None)
        if check is None or ceiling is None:
            return False
        return bool(check(ceiling))

    def foreign_on_gpu(self) -> bool:
        """Public wrapper around the foreign-co-resident check (preemptor uses it)."""
        return self._foreign_on_gpu()

    async def gpu_available(self) -> bool:
        """True iff the demo may serve its GPU model right now (else it is OFFLINE).

        The demo OWNS the GPU whenever its own vLLM server is healthy: that server
        legitimately holds the VRAM, so this is NOT a blanket "is the GPU empty?"
        check (which would misread our own resident vLLM - several GiB of VRAM and
        100%% util while generating - as "busy" and never serve the GPU). The GPU is
        served when ALL hold:
          - GPU routing is not force-disabled (no yield lock, not reclaimed),
          - our vLLM engine is healthy (the GPU model is actually loaded), and
          - no FOREIGN (non-demo) process is co-resident on the GPU (by USAGE).

        The offline test backend ("fake") simulates an ONLINE GPU so the suite can
        exercise the chat path without a real model. Foreign co-residence is
        detected by GPU USAGE (a VRAM ceiling), not the process table; the yield
        LOCK file is the authoritative training-coordination signal. FAIL SAFE: any
        error resolves to OFFLINE.
        """
        if self._settings.llm_backend == "fake":
            return True  # tests: simulate the GPU being online and serving
        # Manual lock or training reclaim => offline regardless of nvidia-smi.
        if self.gpu_yielded():
            return False
        try:
            # Our vLLM must be up to serve the GPU model at all.
            if not bool(await asyncio.to_thread(self._vllm_health)):
                return False
            # A healthy demo vLLM owns the VRAM; yield only to a foreign co-resident.
            if await asyncio.to_thread(self._foreign_on_gpu):
                return False
            return True
        except Exception as exc:  # noqa: BLE001 - any failure => not available
            logger.debug("gpu_available check failed: %s", exc)
            return False

    async def status(self) -> dict:
        """A cheap, CACHED snapshot for the public status banner.

        ``gpu_online`` drives the banner: GREEN when the 7B is serving on the GPU,
        otherwise the demo is OFFLINE. There is no "cpu" tier any more.
        """
        lock = self.lock_present()
        reclaimed = self._reclaimed.is_set()
        fake = self._settings.llm_backend == "fake"
        healthy = False
        foreign = False
        idle = False
        if not fake and not lock and not reclaimed:
            try:
                healthy = bool(await asyncio.to_thread(self._vllm_health))
                foreign = bool(await asyncio.to_thread(self._foreign_on_gpu))
                idle = bool(await asyncio.to_thread(self._monitor.is_idle_cached))
            except Exception as exc:  # noqa: BLE001 - display only, fail to offline
                logger.debug("status snapshot failed: %s", exc)
        # Online when our vLLM is healthy and owns the card (no foreign co-resident)
        # and we have not been told to yield. The fake backend simulates online.
        gpu_online = bool(
            (fake or healthy) and not foreign and not lock and not reclaimed
        )
        gpu_entry = self._catalog.gpu_default()
        model = gpu_entry.id if gpu_entry is not None else self._settings.openai_model
        return {
            "tier": "gpu" if gpu_online else TIER_OFFLINE,
            "gpu_online": gpu_online,
            "model": model,
            "lock_present": lock,
            "gpu_idle": idle,
            "reclaimed": reclaimed,
        }

    # -- selection -------------------------------------------------------

    def _gpu_model_id(self) -> str:
        entry = self._catalog.gpu_default()
        return entry.id if entry is not None else self._settings.openai_model

    def offline_selection(self, notice: str | None = None) -> Selection:
        """An OFFLINE selection (no client): the GPU is not serving right now."""
        return Selection(
            client=None,
            backend_tier=TIER_OFFLINE,
            model=self._gpu_model_id(),
            notice=notice or OFFLINE_NOTICE,
        )

    async def select(self, requested_model: str | None = None) -> Selection:
        """GPU-only: serve the 7B when the GPU is available, else go OFFLINE.

        There is no CPU fallback - any requested model resolves to the single GPU
        model, and when the GPU is unavailable the demo reports OFFLINE rather than
        serving a weaker model. FAIL SAFE: any error resolves to OFFLINE.
        """
        try:
            model_id = self._gpu_model_id()
            if await self.gpu_available():
                return Selection(
                    client=self._factory("gpu", model_id),
                    backend_tier=TIER_GPU,
                    model=model_id,
                )
            return self.offline_selection()
        except Exception as exc:  # noqa: BLE001 - FAIL SAFE to offline
            logger.warning("Router selection failed (%s); reporting offline.", exc)
            return self.offline_selection()

    async def get_client(self) -> tuple[LLMClient | None, str]:
        """Back-compat: return (client, tier) for the auto selection (client may be
        None when offline)."""
        sel = await self.select(None)
        return sel.client, sel.backend_tier
