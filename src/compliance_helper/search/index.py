"""Hybrid retrieval over the legal corpus of one language: four routes, rank fusion, reranking.

Context: legal questions are asked by meaning, by wording or by citation, so dense, keyword, sparse
and citation routes are fused with Reciprocal Rank Fusion and reranked by a cross-encoder; each
language has its own index, built from its corpus and rendered in its language | Input: corpus
units of one language and a question | Output: ranked hits and answer passages, plus a persisted
search index that a rebuild reuses for unchanged units.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from compliance_helper.domain import LegalAct, Passage, Unit, UnitKind
from compliance_helper.i18n import DEFAULT_LANGUAGE, Language, use_language
from compliance_helper.search import store
from compliance_helper.search.citations import citations_from_question
from compliance_helper.search.embedding import Embedder, choose_embedder
from compliance_helper.search.keywords import RESULTS_PER_ROUTE, KeywordIndex

logger = logging.getLogger(__name__)

#: 60 is the common value in the literature; it keeps one route from dominating the fusion.
RRF_K = 60
RERANK_TOP_N = 30
#: A cited provision is a fact, not a similarity estimate, so it outweighs the other routes.
CITATION_ROUTE_WEIGHT = 3.0
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_PASSAGE_CHARACTERS = 1800


@dataclass
class Hit:
    """A retrieved unit with the routes that found it and its rank per route."""

    unit: Unit
    score: float
    routes: set[str] = field(default_factory=set)
    ranks_by_route: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class _Embeddings:
    dense: np.ndarray
    sparse_weights: list[dict[str, float]] | None


def index_text(unit: Unit) -> str:
    """Citation, title and chapter prepended to the text, in the active language.

    Questions often name the citation; vector search only finds it if it is part of the embedded
    text.
    """
    header = [unit.citation, *(part for part in (unit.title, unit.chapter) if part)]
    return "{}\n{}".format(" — ".join(header), unit.text)


class SearchIndex:
    """All retrieval routes over the corpus of one language, buildable once and persisted.

    The persisted index records the embedding model and the language: querying with another
    model would silently produce meaningless hits, and another language's index would show
    passages in the wrong language.
    """

    def __init__(
        self,
        units: list[Unit],
        embedder: Embedder | None = None,
        language: Language = DEFAULT_LANGUAGE,
    ) -> None:
        self.units = units
        self.language = language
        self.embedder = embedder or choose_embedder()
        self.vectors: np.ndarray | None = None
        self.sparse_weights: list[dict[str, float]] | None = None
        self.text_hashes: list[str] = []
        self.keywords = KeywordIndex(language)
        self._position_by_id = {unit.id: number for number, unit in enumerate(units)}
        self.built_on: date | None = None

    def index_texts(self) -> list[str]:
        """The texts that are embedded and keyword-indexed, rendered in the index language."""
        with use_language(self.language):
            return [index_text(unit) for unit in self.units]

    def build(
        self,
        batch_size: int = 32,
        checkpoint_dir: Path | None = None,
        batches_per_checkpoint: int = 2,
        reusable: store.ReusableEmbeddings | None = None,
    ) -> None:
        """Compute vectors and the keyword index, reusing unchanged units and checkpoints.

        A full CPU build takes an hour or more. Units whose id and index text are unchanged in
        ``reusable`` keep their stored embeddings; only the rest is embedded, and with
        ``checkpoint_dir`` every ``batches_per_checkpoint`` batches are written to disk and
        picked up again by the next attempt.

        Args:
            batch_size: Texts per embedding call.
            checkpoint_dir: Directory for resumable checkpoints; ``None`` disables them.
            batches_per_checkpoint: Batches per checkpoint; small to limit lost work.
            reusable: Embeddings of a stored index of the same model and language.
        """
        texts = self.index_texts()
        self.text_hashes = [store.text_hash(text) for text in texts]
        reused = self._reused_embeddings(reusable or store.ReusableEmbeddings())
        pending = [number for number in range(len(texts)) if number not in reused]
        logger.info(
            "Building %s search index with %s: %d units, %d reused, %d to embed",
            self.language.value,
            self.embedder.name,
            len(texts),
            len(reused),
            len(pending),
        )
        computed = self._embed(
            [texts[number] for number in pending],
            [self.text_hashes[number] for number in pending],
            batch_size,
            checkpoint_dir,
            batches_per_checkpoint,
        )
        self.vectors, self.sparse_weights = self._assemble(reused, pending, computed)
        self.keywords.build(texts)
        self.built_on = date.today()

    def _reused_embeddings(
        self, reusable: store.ReusableEmbeddings
    ) -> dict[int, store.StoredEmbedding]:
        found: dict[int, store.StoredEmbedding] = {}
        for number, (unit, current_hash) in enumerate(
            zip(self.units, self.text_hashes, strict=True)
        ):
            stored = reusable.get(unit.id, current_hash)
            if stored is not None:
                found[number] = stored
        return found

    def _embed(
        self,
        texts: list[str],
        text_hashes: list[str],
        batch_size: int,
        checkpoint_dir: Path | None,
        batches_per_checkpoint: int,
    ) -> _Embeddings:
        block = max(1, batch_size * batches_per_checkpoint)
        dense_parts: list[np.ndarray] = []
        weights: list[dict[str, float]] = []
        for start in range(0, len(texts), block):
            block_texts = texts[start : start + block]
            checkpoint = (
                store.Checkpoint.for_block(
                    checkpoint_dir, start, text_hashes[start : start + block]
                )
                if checkpoint_dir is not None
                else None
            )
            stored = checkpoint.read(len(block_texts)) if checkpoint else None
            dense, block_weights = stored or self._embed_block(block_texts, batch_size)
            if checkpoint is not None and stored is None:
                checkpoint.write(dense, block_weights)
            dense_parts.append(dense)
            weights.extend(block_weights)
            logger.info("  %d of %d units embedded", start + len(block_texts), len(texts))
        empty = np.zeros((0, self.embedder.dimensions), dtype=np.float32)
        return _Embeddings(np.vstack(dense_parts) if dense_parts else empty, weights or None)

    def _embed_block(
        self, texts: list[str], batch_size: int
    ) -> tuple[np.ndarray, list[dict[str, float]]]:
        dense_parts: list[np.ndarray] = []
        weights: list[dict[str, float]] = []
        for start in range(0, len(texts), batch_size):
            embedding = self.embedder.embed_passages(texts[start : start + batch_size])
            dense_parts.append(embedding.dense)
            weights.extend(embedding.sparse_weights or [])
        return np.vstack(dense_parts), weights

    def _assemble(
        self,
        reused: dict[int, store.StoredEmbedding],
        pending: list[int],
        computed: _Embeddings,
    ) -> tuple[np.ndarray, list[dict[str, float]] | None]:
        """Merge reused and newly computed embeddings back into corpus order."""
        vectors = np.zeros((len(self.units), self.embedder.dimensions), dtype=np.float32)
        weights: list[dict[str, float] | None] = [None] * len(self.units)
        for number, stored in reused.items():
            vectors[number] = stored.vector
            weights[number] = stored.sparse_weights
        if pending:
            vectors[pending] = computed.dense
        for number, computed_weights in zip(pending, computed.sparse_weights or [], strict=False):
            weights[number] = computed_weights
        complete = [entry for entry in weights if entry is not None]
        if complete and len(complete) != len(weights):
            logger.warning("Sparse weights missing for some units; the sparse route is disabled")
        return vectors, complete if len(complete) == len(weights) and complete else None

    def _dense_route(self, question: str, count: int) -> list[tuple[int, float]]:
        if self.vectors is None or not len(self.vectors):
            return []
        similarity = self.vectors @ self.embedder.embed_query(question)
        top_indices = np.argsort(-similarity)[:count]
        return [(int(i), float(similarity[i])) for i in top_indices]

    def _sparse_route(self, question: str, count: int) -> list[tuple[int, float]]:
        """Match the model's sparse lexical weights (bge-m3 only)."""
        if not self.sparse_weights:
            return []
        embedding = self.embedder.embed_queries([question])
        if not embedding.sparse_weights:
            return []
        question_weights = embedding.sparse_weights[0]
        scores: list[tuple[int, float]] = []
        for number, passage_weights in enumerate(self.sparse_weights):
            total = sum(
                weight * passage_weights.get(marker, 0.0)
                for marker, weight in question_weights.items()
            )
            if total > 0:
                scores.append((number, float(total)))
        return sorted(scores, key=lambda item: -item[1])[:count]

    def _citation_route(self, question: str) -> list[tuple[int, float]]:
        """Return units cited in the question; a missing paragraph falls back to its article."""
        found: list[tuple[int, float]] = []
        for unit_id in citations_from_question(question):
            number = self._position_by_id.get(unit_id)
            if number is not None:
                found.append((number, 1.0))
                continue
            number = self._position_by_id.get(unit_id.rsplit("/", 1)[0])
            if number is not None:
                found.append((number, 0.9))
        return found

    def _fuse(self, routes: dict[str, list[tuple[int, float]]]) -> list[Hit]:
        scores: dict[int, float] = defaultdict(float)
        ranks: dict[int, dict[str, int]] = defaultdict(dict)
        for name, ranking in routes.items():
            weight = CITATION_ROUTE_WEIGHT if name == "citation" else 1.0
            for rank, (number, _) in enumerate(ranking, 1):
                scores[number] += weight / (RRF_K + rank)
                ranks[number][name] = rank
        return [
            Hit(
                unit=self.units[number],
                score=score,
                routes=set(ranks[number]),
                ranks_by_route=ranks[number],
            )
            for number, score in sorted(scores.items(), key=lambda item: -item[1])
        ]

    def search(
        self,
        question: str,
        count: int = 8,
        legal_acts_filter: tuple[LegalAct, ...] | None = None,
        rerank: bool = True,
    ) -> list[Hit]:
        """Query all routes, fuse them by rank and optionally rerank.

        Args:
            question: The user's question, in the language of the index.
            count: Maximum number of hits to return.
            legal_acts_filter: Restrict hits to these legal acts.
            rerank: Apply the cross-encoder to the fused candidates.

        Returns:
            At most ``count`` hits by descending score, at most a third of them use-case examples.
        """
        hits = self._fuse(
            {
                "citation": self._citation_route(question),
                "dense": self._dense_route(question, RESULTS_PER_ROUTE),
                "keyword": self.keywords.search(question, RESULTS_PER_ROUTE),
                "sparse": self._sparse_route(question, RESULTS_PER_ROUTE),
            }
        )
        if legal_acts_filter:
            hits = [hit for hit in hits if hit.unit.legal_act in legal_acts_filter]
        hits = hits[: max(count, RERANK_TOP_N)]
        if rerank and len(hits) > 1:
            hits = rerank_hits(question, hits, self.language)
        return cap_examples(hits, count)

    def save(self, path: Path | None = None) -> None:
        """Persist vectors as ``.npy`` and metadata as gzipped JSON at ``path``.

        Args:
            path: Base path; defaults to the index path of the index language.

        Raises:
            RuntimeError: If the index has not been built.
        """
        if self.vectors is None:
            raise RuntimeError("The search index is not built. Call build() before save().")
        built_on = (self.built_on or date.today()).isoformat()
        summary = {
            "model": self.embedder.name,
            "dimensions": self.embedder.dimensions,
            "language": self.language.value,
            "units": len(self.units),
            "built_on": built_on,
        }
        metadata = {
            **summary,
            "ids": [unit.id for unit in self.units],
            "text_hashes": self.text_hashes
            or [store.text_hash(text) for text in self.index_texts()],
            "sparse_weights": self.sparse_weights,
            "keywords": self.keywords.to_dict(),
        }
        store.write_index(path or store.index_path(self.language), self.vectors, metadata, summary)

    @classmethod
    def load(
        cls,
        language: Language = DEFAULT_LANGUAGE,
        units: list[Unit] | None = None,
        embedder: Embedder | None = None,
        path: Path | None = None,
    ) -> SearchIndex:
        """Load the persisted index of ``language`` and verify model, language and corpus.

        Args:
            language: Language of the index and its corpus.
            units: The corpus the index was built from; defaults to the corpus of ``language``.
            embedder: Embedder to use, e.g. one shared between languages; defaults to the model
                recorded in the index.
            path: Base path of the index; defaults to the index path of ``language``.

        Returns:
            The loaded search index.

        Raises:
            FileNotFoundError: If no index of ``language`` is stored, naming the build command.
            RuntimeError: For a legacy pickle index, another embedding model or language, or
                vectors and ids that do not match ``units``.
        """
        base = path or store.index_path(language)
        metadata = store.read_metadata(base, language)
        _check_language(metadata, language)
        if units is None:
            from compliance_helper.corpus.build import load as load_corpus

            units = load_corpus(language)
        index = cls(units, _matching_embedder(metadata, embedder), language)
        index.vectors = np.load(store.sibling(base, store.VECTORS_SUFFIX))
        index.sparse_weights = metadata.get("sparse_weights")
        index.text_hashes = metadata.get("text_hashes") or []
        index.keywords = KeywordIndex.from_dict(metadata["keywords"], language)
        index.built_on = date.fromisoformat(metadata["built_on"])
        _check_corpus(metadata, index.vectors, units, language)
        return index


def _check_language(metadata: dict[str, Any], language: Language) -> None:
    stored = store.stored_language(metadata)
    if stored is not language:
        raise RuntimeError(
            f"The search index was built for language {stored.value}, but {language.value} "
            f"was requested. Rebuild it: {store.build_command(language)}"
        )


def _matching_embedder(metadata: dict[str, Any], embedder: Embedder | None) -> Embedder:
    expected_model = metadata["model"]
    chosen = embedder or choose_embedder(expected_model)
    if chosen.name != expected_model:
        raise RuntimeError(
            f"The search index was built with {expected_model}, but {chosen.name} is loaded. "
            "Embeddings from different models are not comparable; rebuild the index."
        )
    return chosen


def _check_corpus(
    metadata: dict[str, Any], vectors: np.ndarray, units: list[Unit], language: Language
) -> None:
    """Reject an index of another corpus.

    Equal counts are not enough: a reordered or edited corpus would silently map every vector to
    the wrong provision, so the ids are compared one by one.
    """
    rebuild = f"Rebuild the index: {store.build_command(language)}"
    if len(vectors) != len(units):
        raise RuntimeError(
            f"Search index and corpus ({language.value}) do not match: {len(vectors)} vectors, "
            f"{len(units)} units. {rebuild}"
        )
    stored_ids = metadata.get("ids")
    current_ids = [unit.id for unit in units]
    if stored_ids is not None and stored_ids != current_ids:
        differing = [
            stored
            for stored, current in zip(stored_ids, current_ids, strict=False)
            if stored != current
        ]
        raise RuntimeError(
            f"The stored search index ({language.value}) belongs to a different corpus: "
            f"{len(differing)} ids differ, first {', '.join(differing[:3]) or '(order)'}. {rebuild}"
        )


def cap_examples(hits: list[Hit], count: int) -> list[Hit]:
    """Return at most ``count`` hits, at most a third of them use-case examples.

    Examples share the questions' everyday language and outrank the statute in semantic search:
    measured at 1.6 % of the index but 38 % of the passages. Skipped examples backfill the list
    if too few hits remain.
    """
    cap = max(1, count // 3)
    taken: list[Hit] = []
    skipped: list[Hit] = []
    examples = 0
    for hit in hits:
        if len(taken) == count:
            break
        if hit.unit.kind is UnitKind.EXAMPLE:
            if examples >= cap:
                skipped.append(hit)
                continue
            examples += 1
        taken.append(hit)
    taken.extend(skipped[: count - len(taken)])
    return taken


class _Reranker:
    """The bge cross-encoder, loaded on first use and shared by all indexes."""

    def __init__(self) -> None:
        self._model: Any = None
        self._attempted = False

    def model(self) -> Any:
        if not self._attempted:
            self._attempted = True
            try:
                from FlagEmbedding import FlagReranker

                self._model = FlagReranker(RERANKER_MODEL, use_fp16=True)
            except Exception as error:
                logger.info("Cross-encoder unavailable (%s), keeping the rank fusion order", error)
        return self._model


_reranker = _Reranker()


def shared_reranker() -> Any:
    """The process-wide cross-encoder, or None if it cannot be loaded; loaded once for all uses."""
    return _reranker.model()


def rerank_hits(question: str, hits: list[Hit], language: Language = DEFAULT_LANGUAGE) -> list[Hit]:
    """Rescore preselected hits with the bge cross-encoder.

    The cross-encoder reads question and passage together, which is more accurate than comparing
    embeddings but too slow for the whole index. Passages carry their citation in the index
    language. If the model is unavailable, the fusion order is kept.
    """
    model = shared_reranker()
    if model is None:
        return hits
    with use_language(language):
        pairs = [
            [question, f"{hit.unit.citation}\n{hit.unit.text[:RERANK_PASSAGE_CHARACTERS]}"]
            for hit in hits
        ]
    try:
        scores = model.compute_score(pairs, normalize=True)
    except Exception as error:
        logger.warning("Reranking failed: %s", error)
        return hits
    for hit, rerank_score in zip(
        hits, scores if isinstance(scores, list) else [scores], strict=False
    ):
        hit.score = float(rerank_score)
        hit.routes.add("reranked")
    return sorted(hits, key=lambda hit: -hit.score)


def to_passages(hits: list[Hit], excerpt: int = 700) -> tuple[Passage, ...]:
    """Convert hits into answer passages with an excerpt of ``excerpt`` characters."""
    return tuple(
        Passage(
            id=hit.unit.id,
            citation=hit.unit.citation,
            legal_act=hit.unit.legal_act,
            title=hit.unit.title,
            excerpt=hit.unit.text[:excerpt],
            score=round(hit.score, 4),
            routes=tuple(sorted(hit.routes)),
        )
        for hit in hits
    )
