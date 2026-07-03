"""Curated catalog of demo-selectable models.

Exposes a small, safe set of LOCAL models the user can pick from in the UI. This
demo is GPU-only: the single option is the 7B model served by vLLM when the
training GPUs are idle. There is deliberately NO CPU fallback - when the GPU is
busy serving training the demo is offline rather than serving a weaker,
more-jailbreakable small model. (Operator decision 2026-06-30.)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings

# Sentinel id meaning "let the router choose: GPU when idle, else CPU".
AUTO = "auto"


@dataclass(frozen=True, slots=True)
class ModelEntry:
    id: str
    label: str
    tier: str  # "gpu" or "cpu"
    description: str
    requires_gpu: bool


class ModelCatalog:
    """A small, ordered, curated set of selectable models."""

    def __init__(self, entries: list[ModelEntry], *, default_id: str) -> None:
        self._entries = entries
        self._by_id = {e.id: e for e in entries}
        self._default_id = default_id

    @classmethod
    def from_settings(cls, settings: Settings) -> ModelCatalog:
        # GPU-ONLY demo: the single selectable model is the 7B served on the GPU
        # via vLLM. There is deliberately NO CPU fallback - if the GPU is offline
        # (serving training, or yielded), the demo is offline rather than serving a
        # weaker, more-jailbreakable small model. (Operator decision 2026-06-30.)
        entries = [
            ModelEntry(
                id=settings.openai_model,
                label=f"{settings.openai_model} (GPU 7B)",
                tier="gpu",
                description=(
                    "High-quality 7B model served on the GPU via vLLM. Available "
                    "whenever the self-hosted GPUs are free; while they serve "
                    "training, the live demo is paused (no degraded fallback)."
                ),
                requires_gpu=True,
            ),
        ]
        return cls(entries, default_id=settings.default_chat_model)

    # -- access ----------------------------------------------------------

    @property
    def entries(self) -> list[ModelEntry]:
        return list(self._entries)

    @property
    def default_id(self) -> str:
        return self._default_id

    def gpu_default(self) -> ModelEntry | None:
        return next((e for e in self._entries if e.tier == "gpu"), None)

    def get(self, model_id: str) -> ModelEntry | None:
        return self._by_id.get(model_id)

    def is_auto(self, model_id: str | None) -> bool:
        return model_id is None or model_id == AUTO or model_id not in self._by_id
