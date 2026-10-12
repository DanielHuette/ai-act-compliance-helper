"""Build the stored search index of one language from its corpus.

Context: embedding about 2,800 legal units takes an hour or more on a CPU, so it runs once and the
files ship with the repository; a rebuild embeds only units whose text changed and resumes from
checkpoints after an abort; the service only loads the result. Run through
``compliance-helper build-index --language de|en``. | Input: the corpus of the language, an
embedding model (or the hashing fallback for tests), the existing index of that language |
Output: search_index[.en].* under data/processed, a log in _index_build[.en].log, an exit code.
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from compliance_helper import paths
from compliance_helper.corpus.build import load
from compliance_helper.i18n import DEFAULT_LANGUAGE, Language, use_language
from compliance_helper.search import store
from compliance_helper.search.embedding import (
    DEFAULT_MODEL,
    Embedder,
    HashingEmbedder,
    choose_embedder,
)
from compliance_helper.search.index import SearchIndex

PROBE_QUERIES = {
    Language.DE: "Dürfen wir Bewerbungen mit einem Sprachmodell vorsortieren?",
    Language.EN: "May we pre-sort job applications with a language model?",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexBuildResult:
    """Outcome of one build: the stored index and the number of units it holds."""

    index_path: Path
    units: int
    model: str
    seconds: float


class ModelMissingError(RuntimeError):
    """The requested embedding model could not be loaded; no fallback-quality index is written."""


def _language_infix(language: Language) -> str:
    return "" if language is DEFAULT_LANGUAGE else f".{language.value}"


def checkpoint_dir(language: Language) -> Path:
    """Partial results of a running build; an aborted run resumes here. Deleted after saving."""
    return paths.processed_dir() / f"_index_checkpoints{_language_infix(language)}"


def log_file(language: Language) -> Path:
    return paths.processed_dir() / f"_index_build{_language_infix(language)}.log"


def attach_log_file(language: Language) -> logging.Handler:
    """Write the build log of ``language`` to its log file; the caller removes the handler."""
    log_path = log_file(language)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.setLevel(logging.INFO)
    package_logger = logging.getLogger("compliance_helper")
    package_logger.addHandler(handler)
    package_logger.setLevel(min(package_logger.getEffectiveLevel(), logging.INFO))
    return handler


def reusable_embeddings(
    target: Path, embedder: Embedder, language: Language, from_scratch: bool
) -> store.ReusableEmbeddings:
    if from_scratch:
        shutil.rmtree(checkpoint_dir(language), ignore_errors=True)
        logger.info("Stored index and checkpoints ignored")
        return store.ReusableEmbeddings()
    reusable = store.ReusableEmbeddings.from_index(
        target, embedder.name, embedder.dimensions, language
    )
    logger.info("Stored index offers %d units for reuse", len(reusable))
    return reusable


def log_probe(search_index: SearchIndex, target: Path) -> None:
    """Log the stored files and the top hits of a fixed probe query."""
    logger.info("Saved to %s", target.parent)
    for file in store.index_files(target):
        logger.info("  %-32s %7.1f MB", file.name, file.stat().st_size / 1048576)
    probe_query = PROBE_QUERIES[search_index.language]
    logger.info("Probe query %r", probe_query)
    with use_language(search_index.language):
        for hit in search_index.search(probe_query, count=3, rerank=False):
            logger.info("  %.4f %-34s %s", hit.score, hit.unit.citation, hit.unit.title[:60])


def build_index(
    language: Language,
    model: str | None = None,
    fallback: bool = False,
    from_scratch: bool = False,
) -> IndexBuildResult:
    """Embed the corpus of ``language`` and store the index next to it.

    Raises:
        FileNotFoundError: If the corpus of ``language`` has not been built.
        ModelMissingError: If ``model`` cannot be loaded and ``fallback`` was not requested.
    """
    started = time.time()
    units = load(language)
    logger.info("Corpus (%s): %d units", language.value, len(units))

    embedder = HashingEmbedder() if fallback else choose_embedder(model)
    logger.info("Model: %s with %d dimensions", embedder.name, embedder.dimensions)
    if isinstance(embedder, HashingEmbedder) and not fallback:
        raise ModelMissingError(model or DEFAULT_MODEL)

    target = store.index_path(language)
    search_index = SearchIndex(units, embedder, language)
    search_index.build(
        checkpoint_dir=checkpoint_dir(language),
        reusable=reusable_embeddings(target, embedder, language, from_scratch),
    )
    search_index.save(target)
    shutil.rmtree(checkpoint_dir(language), ignore_errors=True)
    log_probe(search_index, target)
    seconds = time.time() - started
    logger.info("Duration: %.0f s", seconds)
    return IndexBuildResult(target, len(units), embedder.name, seconds)
