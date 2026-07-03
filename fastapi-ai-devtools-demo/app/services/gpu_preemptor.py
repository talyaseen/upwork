"""Background GPU preemptor: yields the GPU to training the instant it appears.

Training/dev/prod processes have ABSOLUTE priority on the 2x T4. This always-on
task polls nvidia-smi every few seconds. If a NON-DEMO compute process appears on
a GPU (or load rises) while we may be using it, it:

  1. Sets the router's reclaim flag so ALL new requests route to the CPU.
  2. Stops our vLLM server (``VllmController.stop()``) to RELEASE the VRAM so
     training gets the GPU back instantly.

(In-flight requests are migrated to the CPU by ``ChatService`` watching the same
reclaim flag.) When the GPU has been clear for ``gpu_hysteresis_count`` polls, the
reclaim flag is released and the GPU may serve new requests again.

The poll is mockable (``check_once`` runs one tick), so the whole behaviour is
unit-tested without a real GPU - the T4s stay dedicated to training.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings
from app.services.gpu_router import GpuRouter
from app.services.openjarvis_engine import VllmController

logger = logging.getLogger("app.preemptor")


class GpuPreemptor:
    def __init__(
        self,
        *,
        router: GpuRouter,
        settings: Settings,
        controller: VllmController | None = None,
    ) -> None:
        self._router = router
        self._settings = settings
        self._controller = controller
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._idle_streak = 0

    async def check_once(self) -> None:
        """One monitor tick. Reclaims or releases the GPU as appropriate.

        Yields the GPU when EITHER GPU USAGE shows a non-demo process co-resident
        (memory over the demo ceiling) OR the manual GPU-yield lock file exists.
        """
        # Detection is by GPU USAGE (VRAM ceiling), NOT the process table - usage
        # is all we need and is namespace-agnostic. The yield LOCK is the
        # authoritative coordination signal.
        foreign = await asyncio.to_thread(self._router.foreign_on_gpu)
        locked = self._router.lock_present()
        if foreign or locked:
            self._idle_streak = 0
            if not self._router.is_reclaimed():
                self._router.reclaim_gpu()
                if self._controller is not None:
                    # Release VRAM so training reclaims the GPU immediately.
                    self._controller.stop()
        else:
            self._idle_streak += 1
            if (
                self._router.is_reclaimed()
                and self._idle_streak >= self._settings.gpu_hysteresis_count
            ):
                self._router.release_reclaim()

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self.check_once()
            except Exception:  # noqa: BLE001 - a monitor blip must not kill the loop
                logger.exception("GPU preemptor tick failed")
            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self._settings.gpu_monitor_interval_seconds,
                )
            except TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None and not self._stop.is_set():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
