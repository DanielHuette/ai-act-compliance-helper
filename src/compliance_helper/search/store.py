"""Files of a persisted search index per language, and the embeddings a rebuild can reuse.

Context: each language has its own index next to its corpus (German keeps the unsuffixed name,
English adds ``.en`` like ``corpus.en.jsonl``); embedding a unit costs seconds on a CPU, so a
rebuild takes over vectors whose unit id and index text are unchanged | Input: the index base path,
its gzipped JSON metadata and ``.npy`` vectors | Output: file paths, parsed metadata, text hashes
and reusable embeddings per unit id.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from compliance_helper import paths
from compliance_helper.i18n import DEFAULT_LANGUAGE, Language, t

logger = logging.getLogger(__name__)

INDEX_STEM = "search_index"
VECTORS_SUFFIX = ".vectors.npy"
METADATA_SUFFIX = ".meta.json.gz"
SUMMARY_SUFFIX = ".meta.json"
LEGACY_SUFFIX = ".meta.pkl"


def index_path(language: Language = DEFAULT_LANGUAGE, directory: Path | None = None) -> Path:
    """Return the base path of the index of ``language``; German keeps the unsuffixed name."""
    folder = directory or paths.processed_dir()
    if language is DEFAULT_LANGUAGE:
        return folder / INDEX_STEM
    return folder / f"{INDEX_STEM}.{language.value}"


def sibling(base: Path, suffix: str) -> Path:
    """Return ``base`` with ``suffix`` appended; ``with_suffix`` would eat the ``.en`` infix."""
    return base.with_name(base.name + suffix)


def index_files(base: Path) -> tuple[Path, ...]:
    """The three files an index consists of."""
    return tuple(
        sibling(base, suffix) for suffix in (VECTORS_SUFFIX, METADATA_SUFFIX, SUMMARY_SUFFIX)
    )


def exists(base: Path) -> bool:
    return sibling(base, METADATA_SUFFIX).exists() and sibling(base, VECTORS_SUFFIX).exists()


def text_hash(text: str) -> str:
    """Short fingerprint of an index text; 64 bits are ample for a few thousand units."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def stored_language(metadata: dict[str, Any]) -> Language:
    """Language recorded in the metadata; indexes from before the English one are German."""
    return Language(metadata.get("language", DEFAULT_LANGUAGE.value))


def read_metadata(base: Path, language: Language = DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Read the gzipped JSON metadata of the index at ``base``.

    Raises:
        FileNotFoundError: If no index is stored there, with the build command for ``language``.
        RuntimeError: For a legacy pickle index, which is never read.
    """
    metadata_path = sibling(base, METADATA_SUFFIX)
    legacy_path = sibling(base, LEGACY_SUFFIX)
    if metadata_path.exists():
        with gzip.open(metadata_path, "rt", encoding="utf-8") as file:
            metadata: dict[str, Any] = json.load(file)
        return metadata
    if legacy_path.exists():
        raise RuntimeError(
            f"The stored search index {legacy_path.name} uses the legacy pickle format. "
            "It is no longer read because a tampered file could execute code "
            f"on load. Rebuild the index: {build_command(language)}"
        )
    raise FileNotFoundError(
        t(
            "search.index_missing",
            path=base,
            language_name=t(f"search.language_{language.value}"),
            command=build_command(language),
        )
    )


def build_command(language: Language) -> str:
    """The command that builds the index of ``language``, wherever the tool is installed."""
    return f"compliance-helper build-index --language {language.value}"


def write_index(
    base: Path,
    vectors: np.ndarray,
    metadata: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    """Write vectors as ``.npy`` and metadata as gzipped JSON, never as pickle.

    The index ships via copies and forks; a tampered pickle would execute code on load, a
    tampered JSON file can only yield wrong hits.
    """
    base.parent.mkdir(parents=True, exist_ok=True)
    np.save(sibling(base, VECTORS_SUFFIX), vectors)
    with gzip.open(sibling(base, METADATA_SUFFIX), "wt", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, separators=(",", ":"))
    sibling(base, SUMMARY_SUFFIX).write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )


@dataclass(frozen=True)
class StoredEmbedding:
    """What one unit contributed to a stored index: text fingerprint, vector, sparse weights."""

    text_hash: str
    vector: np.ndarray
    sparse_weights: dict[str, float] | None


@dataclass
class ReusableEmbeddings:
    """Embeddings of a stored index, offered to a rebuild with the same model and language."""

    by_id: dict[str, StoredEmbedding] = field(default_factory=dict)

    def get(self, unit_id: str, current_hash: str) -> StoredEmbedding | None:
        """Return the stored embedding if the unit's index text is unchanged."""
        stored = self.by_id.get(unit_id)
        return stored if stored is not None and stored.text_hash == current_hash else None

    def __len__(self) -> int:
        return len(self.by_id)

    @classmethod
    def from_index(
        cls, base: Path, model: str, dimensions: int, language: Language
    ) -> ReusableEmbeddings:
        """Collect reusable embeddings of the index at ``base``; empty if none fit.

        An index of another model, dimension or language lives in a different space or was
        embedded from different text, and one without text hashes cannot prove a unit unchanged.
        """
        if not exists(base):
            return cls()
        metadata = read_metadata(base, language)
        reason = _incompatibility(metadata, model, dimensions, language)
        if reason:
            logger.info("Stored index %s not reused: %s", base.name, reason)
            return cls()
        vectors = np.load(sibling(base, VECTORS_SUFFIX))
        sparse = metadata.get("sparse_weights") or [None] * len(vectors)
        entries = zip(metadata["ids"], metadata["text_hashes"], vectors, sparse, strict=True)
        return cls(
            {
                unit_id: StoredEmbedding(text_hash, vector, weights)
                for unit_id, text_hash, vector, weights in entries
            }
        )


def _incompatibility(
    metadata: dict[str, Any], model: str, dimensions: int, language: Language
) -> str:
    if metadata.get("model") != model:
        return f"model {metadata.get('model')} instead of {model}"
    if metadata.get("dimensions") != dimensions:
        return f"{metadata.get('dimensions')} dimensions instead of {dimensions}"
    if stored_language(metadata) is not language:
        return f"language {stored_language(metadata).value} instead of {language.value}"
    if not metadata.get("text_hashes") or not metadata.get("ids"):
        return "no text hashes stored"
    return ""


@dataclass(frozen=True)
class Checkpoint:
    """Embeddings of one block of a running build, so an aborted build resumes there.

    The name carries the block's start offset and a fingerprint of its texts: a checkpoint of
    other texts is never picked up, so vectors cannot end up attached to the wrong units.
    """

    vectors_path: Path
    sparse_path: Path

    @classmethod
    def for_block(cls, directory: Path, start: int, text_hashes: list[str]) -> Checkpoint:
        fingerprint = text_hash("".join(text_hashes))[:12]
        stem = directory / f"part-{start:06d}-{fingerprint}"
        return cls(sibling(stem, ".vectors.npy"), sibling(stem, ".sparse.json.gz"))

    def read(self, expected_rows: int) -> tuple[np.ndarray, list[dict[str, float]]] | None:
        """Return the stored block, or ``None`` if it is missing or incomplete."""
        if not (self.vectors_path.exists() and self.sparse_path.exists()):
            return None
        dense = np.load(self.vectors_path)
        if len(dense) != expected_rows:
            logger.warning("Checkpoint %s is incomplete, recomputing", self.vectors_path.name)
            return None
        with gzip.open(self.sparse_path, "rt", encoding="utf-8") as file:
            weights: list[dict[str, float]] = json.load(file)
        return dense, weights

    def write(self, dense: np.ndarray, weights: list[dict[str, float]]) -> None:
        self.vectors_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self.vectors_path, dense)
        with gzip.open(self.sparse_path, "wt", encoding="utf-8") as file:
            json.dump(weights, file, separators=(",", ":"))
