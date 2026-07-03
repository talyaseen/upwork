"""Unit tests for the OpenJarvis engine adapter (no GPU, no real vLLM).

Covers the two resource/config bugs in this adapter:
  - BC2: ``_make_engine`` must forward the app's bounded request timeout
    (``llm_request_timeout``, 180s) to ``VLLMEngine`` so a wedged read fails at
    180s, not OpenJarvis's 600s default.
  - BM5: the per-request client and the health-probe engine must be closeable so
    their httpx file descriptors are released deterministically (FD churn).

``VLLMEngine`` is replaced with a lightweight recorder so nothing constructs a
real engine or touches a server / the GPU.
"""

from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

from app.services.openjarvis_engine import (
    OpenJarvisEngineClient,
    _make_engine,
    vllm_healthy,
)


def _install_fake_vllm_engine(monkeypatch, engine_cls) -> None:
    """Provide a fake ``openjarvis.engine.openai_compat_engines.VLLMEngine``.

    The adapter imports it lazily inside each function, so a stub module on
    ``sys.modules`` is picked up without importing real OpenJarvis.
    """
    mod = types.ModuleType("openjarvis.engine.openai_compat_engines")
    mod.VLLMEngine = engine_cls
    monkeypatch.setitem(
        sys.modules, "openjarvis.engine.openai_compat_engines", mod
    )


def test_make_engine_forwards_request_timeout(monkeypatch) -> None:
    captured: dict = {}

    class _RecEngine:
        def __init__(self, host=None, *, timeout=600.0, **kwargs) -> None:
            captured["host"] = host
            captured["timeout"] = timeout

    _install_fake_vllm_engine(monkeypatch, _RecEngine)

    settings = SimpleNamespace(
        openjarvis_vllm_host="http://localhost:8000",
        llm_request_timeout=180.0,
    )
    _make_engine(settings, "gpu")

    # PIN (BC2): previously constructed WITHOUT timeout -> OpenJarvis default 600s.
    assert captured["timeout"] == 180.0
    assert captured["host"] == "http://localhost:8000"


def test_vllm_healthy_closes_probe_engine(monkeypatch) -> None:
    closed = {"n": 0}

    class _RecEngine:
        def __init__(self, host=None, **kwargs) -> None:
            pass

        def health(self) -> bool:
            return True

        def close(self) -> None:
            closed["n"] += 1

    _install_fake_vllm_engine(monkeypatch, _RecEngine)

    settings = SimpleNamespace(
        llm_backend="openjarvis",
        openjarvis_vllm_host="http://localhost:8000",
    )
    assert vllm_healthy(settings) is True
    # PIN (BM5): the probe engine's httpx client is closed after every probe.
    assert closed["n"] == 1


def test_vllm_healthy_closes_probe_engine_even_on_error(monkeypatch) -> None:
    closed = {"n": 0}

    class _RecEngine:
        def __init__(self, host=None, **kwargs) -> None:
            pass

        def health(self) -> bool:
            raise RuntimeError("probe blew up")

        def close(self) -> None:
            closed["n"] += 1

    _install_fake_vllm_engine(monkeypatch, _RecEngine)

    settings = SimpleNamespace(
        llm_backend="openjarvis",
        openjarvis_vllm_host="http://localhost:8000",
    )
    assert vllm_healthy(settings) is False
    assert closed["n"] == 1  # finally still closed it


def test_client_aclose_closes_engine() -> None:
    class _Engine:
        def __init__(self) -> None:
            self.closed = 0

        def close(self) -> None:
            self.closed += 1

    engine = _Engine()
    client = OpenJarvisEngineClient(
        engine=engine, model="m", temperature=0.7, max_tokens=16
    )
    asyncio.run(client.aclose())
    assert engine.closed == 1
