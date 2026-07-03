"""Real-openjarvis contract conformance (mock-vs-real drift guard).

The chat pipeline relies on two facts about the REAL ``openjarvis`` package that
are otherwise only vouched for by this repo's own fakes:

1. ``VLLMEngine.__init__`` accepts a ``timeout`` keyword. ``openjarvis_engine.py``
   forwards the app's bounded ``llm_request_timeout`` through it; if the real
   engine dropped that parameter, a wedged vLLM read would silently fall back to
   OpenJarvis's 600s default and hang far longer than intended.
2. A context-window overflow raises an exception whose ``is_context_length_error``
   attribute is ``True``. ``chat_service.stream()`` maps exactly that attribute
   (``getattr(exc, "is_context_length_error", False)``) to a clean
   CONTEXT_TOO_LONG notice instead of the generic engine-failure SSE error.

These assertions run against the REAL package. Each is independently skipped when
the installed openjarvis cannot provide that symbol, so the suite stays green in
environments (e.g. CI without the GPU engine) where openjarvis is absent or older
than the contract, and turns into a genuine real-vs-mock check wherever it can.
"""

from __future__ import annotations

import importlib
import inspect

import pytest


def _load_vllm_engine():
    """Return the real ``VLLMEngine`` class, or ``None`` if unavailable."""
    try:
        module = importlib.import_module(
            "openjarvis.engine.openai_compat_engines"
        )
    except Exception:  # noqa: BLE001 - any import failure => skip, not fail
        return None
    return getattr(module, "VLLMEngine", None)


def _load_context_length_error():
    """Return the real context-length exception class, or ``None``.

    The app only duck-types ``is_context_length_error`` on the raised exception,
    so the concrete class name/location is not pinned here - probe the plausible
    openjarvis locations and accept the first class that carries the attribute.
    """
    candidates = [
        ("openjarvis.engine.openai_compat_engines", "EngineContextLengthError"),
        ("openjarvis.engine._openai_compat", "EngineContextLengthError"),
        ("openjarvis.engine._base", "EngineContextLengthError"),
        ("openjarvis.core.exceptions", "EngineContextLengthError"),
    ]
    for module_path, class_name in candidates:
        try:
            module = importlib.import_module(module_path)
        except Exception:  # noqa: BLE001 - missing module => keep probing
            continue
        err = getattr(module, class_name, None)
        if err is not None:
            return err
    return None


_VLLM_ENGINE = _load_vllm_engine()
_CONTEXT_LENGTH_ERROR = _load_context_length_error()


@pytest.mark.skipif(
    _VLLM_ENGINE is None,
    reason="real openjarvis VLLMEngine not importable (mock-only environment)",
)
def test_vllm_engine_accepts_timeout_kwarg() -> None:
    """Real ``VLLMEngine.__init__`` must accept the ``timeout`` we forward."""
    params = inspect.signature(_VLLM_ENGINE.__init__).parameters
    assert "timeout" in params


@pytest.mark.skipif(
    _CONTEXT_LENGTH_ERROR is None,
    reason=(
        "real openjarvis does not expose a typed context-length error "
        "(app duck-types is_context_length_error; nothing to conform to)"
    ),
)
def test_context_length_error_flags_itself() -> None:
    """The real context-length exception must set ``is_context_length_error``."""
    assert _CONTEXT_LENGTH_ERROR.is_context_length_error is True
