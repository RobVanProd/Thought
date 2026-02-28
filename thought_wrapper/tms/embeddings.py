"""Embedding providers for the Thought Memory System."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """Embedding provider interface."""

    @property
    def dimension(self) -> int:  # pragma: no cover - protocol
        ...

    def embed(self, text: str) -> list[float]:  # pragma: no cover - protocol
        ...


@dataclass
class HashEmbedder:
    """Deterministic offline fallback embedder (no external model dependencies)."""

    dimension: int = 384

    def embed(self, text: str) -> list[float]:
        if self.dimension <= 0:
            raise ValueError("dimension must be positive")

        out = np.zeros(self.dimension, dtype=np.float32)
        seed = text.encode("utf-8")
        offset = 0

        while offset < self.dimension:
            block = hashlib.sha256(seed + offset.to_bytes(4, "little")).digest()
            ints = np.frombuffer(block, dtype=np.uint16).astype(np.float32)
            floats = (ints / 65535.0) * 2.0 - 1.0
            take = min(len(floats), self.dimension - offset)
            out[offset : offset + take] = floats[:take]
            offset += take

        norm = float(np.linalg.norm(out))
        if norm > 0:
            out /= norm
        return out.astype(np.float32).tolist()


class SentenceTransformerEmbedder:
    """Embedding provider backed by sentence-transformers."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 384,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:  # pragma: no cover - import path
            raise RuntimeError(
                "sentence-transformers is not installed. Install it or use HashEmbedder."
            ) from exc

        self._model = SentenceTransformer(model_name)
        self._dimension = int(dimension)
        if self._dimension <= 0:
            raise ValueError("dimension must be positive")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> list[float]:
        vec = self._model.encode(text, normalize_embeddings=True)
        arr = np.asarray(vec, dtype=np.float32).flatten()
        if arr.size == self._dimension:
            return arr.tolist()
        if arr.size > self._dimension:
            clipped = arr[: self._dimension]
            norm = float(np.linalg.norm(clipped))
            if norm > 0:
                clipped /= norm
            return clipped.tolist()
        # Pad smaller vectors to requested dimension.
        padded = np.zeros(self._dimension, dtype=np.float32)
        padded[: arr.size] = arr
        norm = float(np.linalg.norm(padded))
        if norm > 0:
            padded /= norm
        return padded.tolist()


def resolve_embedder(
    embedder: Embedder | None = None,
    *,
    prefer_sentence_transformers: bool = True,
    dimension: int = 384,
) -> Embedder:
    """Resolve an embedder with sentence-transformers preferred when available."""
    if embedder is not None:
        return embedder

    if prefer_sentence_transformers:
        try:
            return SentenceTransformerEmbedder(dimension=dimension)
        except Exception:
            pass

    return HashEmbedder(dimension=dimension)

