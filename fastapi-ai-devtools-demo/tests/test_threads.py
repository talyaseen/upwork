"""Thread-cap tests: only the LLM inference is capped; serving stays uncapped."""

from __future__ import annotations

import os
from types import SimpleNamespace

from app.core.threads import configure_model_thread_caps


def test_caps_ollama_threads_to_configured_value(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_THREAD", raising=False)
    applied = configure_model_thread_caps(SimpleNamespace(model_max_threads=24))
    assert applied == {"OLLAMA_NUM_THREAD": "24"}
    assert os.environ["OLLAMA_NUM_THREAD"] == "24"


def test_default_cap_is_32(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_THREAD", raising=False)
    applied = configure_model_thread_caps(SimpleNamespace(model_max_threads=32))
    assert applied["OLLAMA_NUM_THREAD"] == "32"


def test_does_not_touch_omp_or_mkl(monkeypatch):
    # The serving layer / embeddings must NOT be capped here.
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    monkeypatch.delenv("MKL_NUM_THREADS", raising=False)
    configure_model_thread_caps(SimpleNamespace(model_max_threads=16))
    assert "OMP_NUM_THREADS" not in os.environ
    assert "MKL_NUM_THREADS" not in os.environ
