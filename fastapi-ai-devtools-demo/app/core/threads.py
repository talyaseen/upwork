"""Thread caps for the LLM inference (and ONLY the LLM inference).

Operator policy: cap the OpenJarvis/Ollama LLM inference to at most
``MODEL_MAX_THREADS`` threads so it cannot monopolize the hub (56 threads). The
NON-MODEL serving layer (FastAPI/uvicorn, SSE streaming, embeddings/retrieval,
the queue and event loop) is deliberately LEFT UNCAPPED and runs on the box's
remaining threads. We therefore do NOT touch OMP/MKL/torch thread counts here.

The hard guarantee is a deploy-time cpuset on the Ollama process (see RUNBOOK);
this sets the env knob that an Ollama server inheriting this environment honors.
"""

from __future__ import annotations

import os

from app.core.config import Settings


def configure_model_thread_caps(settings: Settings) -> dict[str, str]:
    """Apply the LLM-only thread cap. Returns the env vars set (for logging/tests)."""
    n = max(1, int(settings.model_max_threads))
    applied = {"OLLAMA_NUM_THREAD": str(n)}
    os.environ["OLLAMA_NUM_THREAD"] = applied["OLLAMA_NUM_THREAD"]
    return applied
