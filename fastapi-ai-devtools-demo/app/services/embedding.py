"""Embedding backends.

Two interchangeable implementations behind a tiny Protocol:

- ``SentenceTransformerEmbedder`` loads a real local sentence-transformer
  model (default: all-MiniLM-L6-v2). The model is downloaded once to the
  local cache and then runs fully in-process on CPU. No network calls happen
  at inference time and no paid API is ever contacted.

- ``HashEmbedder`` is a deterministic, dependency-free embedder used by the
  test suite. It hashes tokens into a fixed-dimension vector so the suite is
  fast and never downloads model weights, while exercising the exact same
  application code paths as the real backend.

Embeddings are L2-normalised, so a plain dot product equals cosine
similarity in the search service.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

import numpy as np

from app.core.config import Settings


@runtime_checkable
class Embedder(Protocol):
    """Common interface for all embedding backends."""

    dimension: int

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, dimension) float32 array of unit-norm vectors."""
        ...


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """L2-normalise rows; zero rows are left as zeros (no divide-by-zero)."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return (matrix / norms).astype(np.float32)


class HashEmbedder:
    """Deterministic hashing embedder (offline, for tests and fallbacks)."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            # Use 4 bytes to pick an index and 1 byte for a signed weight.
            idx = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        matrix = np.vstack([self._embed_one(t) for t in texts])
        return _l2_normalize(matrix)


class SentenceTransformerEmbedder:
    """Real local sentence-transformer model (loaded once, CPU inference)."""

    def __init__(self, model_name: str) -> None:
        # Imported lazily so the test suite never needs the heavy dependency.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device="cpu")
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.astype(np.float32)


def build_embedder(settings: Settings) -> Embedder:
    """Construct the embedder selected by configuration."""
    if settings.embedding_backend == "hash":
        return HashEmbedder(dimension=settings.hash_embedding_dim)
    return SentenceTransformerEmbedder(model_name=settings.embedding_model_name)
