"""Embedding models for semantic search over the legal corpus.

Context: dense vectors (and bge-m3 sparse weights) let search match questions to provisions by
meaning; one fixed default model keeps answers reproducible | Input: text chunks and questions |
Output: L2-normalised embedding results and the selected embedder.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-m3"

#: Without these instruction prefixes, e5 retrieval quality drops measurably.
INSTRUCTION_PREFIXES = {
    "intfloat/multilingual-e5-small": {"query": "query: ", "passage": "passage: "},
    "intfloat/multilingual-e5-base": {"query": "query: ", "passage": "passage: "},
    "intfloat/multilingual-e5-large": {"query": "query: ", "passage": "passage: "},
}


@dataclass(frozen=True)
class EmbeddingResult:
    """Dense vectors and, for bge-m3, sparse lexical weights."""

    dense: np.ndarray
    sparse_weights: list[dict[str, float]] | None = None


class Embedder(ABC):
    """Interface the search index depends on."""

    name: str
    dimensions: int

    @abstractmethod
    def embed_passages(self, texts: list[str]) -> EmbeddingResult:
        """Embed corpus passages."""

    @abstractmethod
    def embed_queries(self, texts: list[str]) -> EmbeddingResult:
        """Embed questions; some models need a different instruction prefix for them."""

    def embed_query(self, text: str) -> np.ndarray:
        vector: np.ndarray = self.embed_queries([text]).dense[0]
        return vector


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """Scale rows to unit length so the dot product equals cosine similarity."""
    lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
    lengths[lengths == 0] = 1.0
    normalized: np.ndarray = (vectors / lengths).astype(np.float32)
    return normalized


class BgeM3(Embedder):
    """bge-m3: dense vectors and context-aware sparse weights in one pass."""

    name = "BAAI/bge-m3"
    dimensions = 1024

    def __init__(self, device: str | None = None, dense_only: bool = False) -> None:
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as error:
            raise RuntimeError(
                "bge-m3 requires the FlagEmbedding package. "
                "Install it with: pip install 'ai-act-compliance-helper[search]'"
            ) from error
        self._dense_only = dense_only
        self._model = BGEM3FlagModel(self.name, use_fp16=device != "cpu", devices=device)

    def _encode(self, texts: list[str]) -> EmbeddingResult:
        output: dict[str, Any] = self._model.encode(
            texts,
            return_dense=True,
            return_sparse=not self._dense_only,
            return_colbert_vecs=False,
            batch_size=8,
            max_length=1024,
        )
        dense = _l2_normalize(np.asarray(output["dense_vecs"], dtype=np.float32))
        weights = None
        if not self._dense_only and output.get("lexical_weights") is not None:
            weights = [
                {str(k): float(v) for k, v in entry.items()} for entry in output["lexical_weights"]
            ]
        return EmbeddingResult(dense=dense, sparse_weights=weights)

    def embed_passages(self, texts: list[str]) -> EmbeddingResult:
        return self._encode(texts)

    def embed_queries(self, texts: list[str]) -> EmbeddingResult:
        return self._encode(texts)


class SentenceTransformerEmbedder(Embedder):
    """Any sentence-transformers model; used only when named explicitly."""

    def __init__(self, name: str = DEFAULT_MODEL, device: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "The sentence-transformers package is missing. "
                "Install it with: pip install 'ai-act-compliance-helper[search]'"
            ) from error
        self.name = name
        self._model = SentenceTransformer(name, device=device)
        # Fail here rather than later as an opaque length mismatch in the search index.
        reported = self._model.get_sentence_embedding_dimension()
        if reported is None:
            raise RuntimeError(
                f"Model {name} does not report its embedding dimension; "
                "a search index cannot be built without it."
            )
        self.dimensions = int(reported)
        self._prefixes = INSTRUCTION_PREFIXES.get(name, {})

    def _encode(self, texts: list[str], input_role: str) -> EmbeddingResult:
        prefix = self._prefixes.get(input_role, "")
        prefixed = [prefix + t for t in texts] if prefix else texts
        vectors = self._model.encode(
            prefixed, batch_size=16, show_progress_bar=False, convert_to_numpy=True
        )
        return EmbeddingResult(dense=_l2_normalize(np.asarray(vectors, dtype=np.float32)))

    def embed_passages(self, texts: list[str]) -> EmbeddingResult:
        return self._encode(texts, "passage")

    def embed_queries(self, texts: list[str]) -> EmbeddingResult:
        return self._encode(texts, "query")


class HashingEmbedder(Embedder):
    """Dependency-free word-hashing embedder for tests; matches words, not meaning."""

    name = "hashing-fallback"
    dimensions = 256

    def _encode(self, texts: list[str]) -> EmbeddingResult:
        vectors = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in text.lower().split():
                position = int(hashlib.blake2b(word.encode("utf-8"), digest_size=4).hexdigest(), 16)
                vectors[row, position % self.dimensions] += 1.0
        return EmbeddingResult(dense=_l2_normalize(vectors))

    def embed_passages(self, texts: list[str]) -> EmbeddingResult:
        return self._encode(texts)

    def embed_queries(self, texts: list[str]) -> EmbeddingResult:
        return self._encode(texts)


def choose_embedder(name: str | None = None, device: str | None = None) -> Embedder:
    """Return the requested embedder, falling back to bge-m3, then to hashing.

    Every fallback is logged, because silently degraded search is worse than an error.

    Args:
        name: Explicit model name, or ``None`` for the default.
        device: Torch device such as ``"cpu"``; ``None`` lets the library decide.

    Returns:
        The first embedder that could be loaded.
    """
    if name == HashingEmbedder.name:
        return HashingEmbedder()
    attempts = [n for n in (name, DEFAULT_MODEL) if n]
    for candidate in attempts:
        try:
            if candidate == "BAAI/bge-m3":
                return BgeM3(device=device)
            return SentenceTransformerEmbedder(candidate, device=device)
        except Exception as error:
            logger.warning("Model %s unavailable: %s", candidate, error)
    logger.error(
        "No embedding model available, using the hashing fallback. "
        "Search quality is considerably worse."
    )
    return HashingEmbedder()


def model_cache_dir() -> Path:
    """Hugging Face model cache directory, honouring ``HF_HOME``."""
    import os

    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
