"""OpenJarvis engine adapter.

Runs generation through the IN-PROCESS OpenJarvis engine API while presenting
the tiny ``LLMClient`` Protocol (``model`` + ``async stream_chat``) that the rest
of the app already speaks. This is the production inference path: the vLLM engine
serves the GPU (7B) model when the training GPUs are idle. This demo is GPU-only
- there is no CPU/Ollama fallback; when the GPU is busy the demo goes offline.

Why the in-process engine API (not proxying ``jarvis serve``): per-request engine
routing and DYNAMIC mid-stream preemption (yield the GPU to training instantly)
require explicit, fine-grained control over WHICH engine serves each request and
the ability to tear the GPU engine down on demand. The engine API gives exactly
that; ``jarvis serve`` hides engine selection behind its own logic.

OpenJarvis is imported LAZILY (only when this module is used, i.e. when
``llm_backend == "openjarvis"``), so the offline test suite never imports it.

SAFETY: the local vLLM (GPU) engine only. The cloud/litellm engines are never
constructed here, so no paid external API can be contacted.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
from collections.abc import AsyncIterator

from app.core.config import Settings
from app.services.llm_client import LLMClient

logger = logging.getLogger("app.openjarvis")


def _make_engine(settings: Settings, tier: str):
    """Construct the OpenJarvis engine for the request.

    GPU-only demo: the only engine is the vLLM (GPU) engine. The ``tier`` argument
    is accepted for signature compatibility but is always the GPU path - there is
    no CPU/Ollama fallback. Imports OpenJarvis lazily.
    """
    from openjarvis.engine.openai_compat_engines import VLLMEngine

    # Pass the app's bounded request timeout (llm_request_timeout, 180s) through to
    # the engine. Without it VLLMEngine falls back to OpenJarvis's 600s default, so
    # a wedged vLLM read would hang far longer than intended; the async stream path
    # now applies this timeout to inter-token reads too.
    return VLLMEngine(
        host=settings.openjarvis_vllm_host,
        timeout=settings.llm_request_timeout,
    )


class OpenJarvisEngineClient:
    """LLMClient Protocol implementation backed by an OpenJarvis engine."""

    def __init__(
        self,
        *,
        engine,
        model: str,
        temperature: float,
        max_tokens: int,
        num_thread: int | None = None,
        repetition_penalty: float | None = None,
    ) -> None:
        self._engine = engine
        self.model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._num_thread = num_thread
        # 2026-07-01 incident fix: forwarded as a top-level vLLM sampling
        # param on every request (vLLM's OpenAI-compatible server accepts it
        # directly in the request body, not nested under extra_body). None
        # omits the field entirely so callers who don't want it are unaffected.
        self._repetition_penalty = repetition_penalty

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        # Convert the OpenAI-style dicts into OpenJarvis Message objects.
        from openjarvis.core.types import Message, Role

        oj_messages = [
            Message(
                role=Role(m.get("role", "user")),
                content=m.get("content", "") or "",
            )
            for m in messages
        ]
        kwargs: dict = {}
        # num_thread is forwarded for engines that honor it; harmless otherwise.
        if self._num_thread:
            kwargs["num_thread"] = self._num_thread
        if self._repetition_penalty is not None:
            kwargs["repetition_penalty"] = self._repetition_penalty
        async for token in self._engine.stream(
            oj_messages,
            model=self.model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            **kwargs,
        ):
            if token:
                yield token

    async def aclose(self) -> None:
        """Release the per-request engine's HTTP resources.

        Called by the chat pipeline in a ``finally`` after each request so the
        underlying httpx client is closed deterministically instead of leaking a
        file descriptor until GC (FD churn under refresh-spam). ``engine.close()``
        is synchronous and safe to call more than once.
        """
        close = getattr(self._engine, "close", None)
        if close is not None:
            try:
                close()
            except Exception:  # noqa: BLE001 - closing must never break a response
                logger.debug("engine close failed", exc_info=True)


def build_openjarvis_client(
    settings: Settings, *, tier: str, model: str
) -> LLMClient:
    """Build an ``OpenJarvisEngineClient`` for a tier and model."""
    engine = _make_engine(settings, tier)
    return OpenJarvisEngineClient(
        engine=engine,
        model=model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        repetition_penalty=settings.llm_repetition_penalty,
    )


def vllm_healthy(settings: Settings) -> bool:
    """Return True only if the local vLLM (GPU) engine is reachable and healthy.

    FAIL SAFE: any import error, construction error, or network failure -> False
    (treated as "GPU not available", so the router stays on the CPU fallback).
    Never starts a server; only probes one that may already be running.
    """
    if settings.llm_backend == "fake":
        return False
    engine = None
    try:
        from openjarvis.engine.openai_compat_engines import VLLMEngine

        engine = VLLMEngine(host=settings.openjarvis_vllm_host)
        return bool(engine.health())
    except Exception as exc:  # noqa: BLE001 - any failure means "not healthy"
        logger.debug("vLLM health probe failed: %s", exc)
        return False
    finally:
        # Close the probe engine's httpx client so repeated health checks (one per
        # request via the router) do not leak a file descriptor each time.
        if engine is not None:
            try:
                engine.close()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                logger.debug("vLLM probe engine close failed", exc_info=True)


class VllmController:
    """Manages the lifecycle of OUR vLLM server so we can release the GPU.

    On dynamic preemption (training reclaims the GPU) we must DROP the GPU model
    and FULLY RELEASE its VRAM instantly. The VRAM-hygiene contract is that
    ``stop()`` does a FULL PROCESS EXIT of the vLLM server (terminate its process
    GROUP), so the CUDA context is destroyed and the NVIDIA driver reclaims and
    zeroes that VRAM before training reallocates it. This is NOT a pause/idle
    that keeps the model resident in VRAM. The demo never relies on residual VRAM
    across a yield (a fresh GPU stint starts a new vLLM process).

    When a real vLLM server is attached via ``attach(proc)``, ``stop()`` SIGTERMs
    (then SIGKILLs) its process group. In this build we do NOT launch a real vLLM
    server (the T4s are training; the operator validates the GPU path later), so
    with no process attached ``stop()`` is a safe recorded no-op.
    """

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._running = False  # used when no real process is attached (tests)
        self.stop_calls = 0

    def attach(self, proc: subprocess.Popen) -> None:  # pragma: no cover - deploy hook
        """Take ownership of a launched vLLM server process (its own pgroup)."""
        self._proc = proc
        self._running = True

    def mark_started(self) -> None:
        """Mark running without a real process (for tests / dry runs)."""
        self._running = True

    def is_running(self) -> bool:
        if self._proc is not None:
            return self._proc.poll() is None
        return self._running

    @staticmethod
    def _signal_group(pgid: int, sig: int) -> None:
        """Send ``sig`` to a process group, ignoring "already gone" errors."""
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def stop(self) -> None:
        """FULL PROCESS EXIT of vLLM to release + scrub VRAM (idempotent).

        VRAM-hygiene GUARANTEE: every member of the vLLM process group is killed,
        so NO straggler holds a CUDA context (which would keep VRAM resident).
        We SIGTERM the group for a graceful teardown, then ALWAYS escalate to
        SIGKILL of the whole group - a vLLM tensor-parallel WORKER can hang in
        NCCL/CUDA shutdown after the leader exits, and SIGKILL cannot be caught
        or deferred, so the kernel tears the context down and the driver reclaims
        the VRAM. (Validated on 2x T4, 2026-06-30: leader-only SIGTERM could leave
        a worker holding ~2 GiB; the unconditional group SIGKILL closes that gap.)
        """
        self.stop_calls += 1
        proc = self._proc
        if proc is not None and proc.poll() is None:
            logger.info("Preemption: killing vLLM process group to release VRAM.")
            try:
                pgid = os.getpgid(proc.pid)
            except OSError:
                pgid = None
            # 1. Graceful: SIGTERM the whole group (children begin CUDA teardown).
            if pgid is not None:
                self._signal_group(pgid, signal.SIGTERM)
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                pass
            # 2. GUARANTEE no straggler: SIGKILL the whole group unconditionally.
            if pgid is not None:
                self._signal_group(pgid, signal.SIGKILL)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        elif self._running:
            logger.info("Preemption: marking vLLM stopped (no attached process).")
        self._proc = None
        self._running = False
