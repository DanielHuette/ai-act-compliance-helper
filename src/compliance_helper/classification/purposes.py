"""Semantic purpose matching: which AI Act provision does a described use case hit?

Context: keyword lists only catch phrasings someone wrote down, so descriptions are compared
sentence by sentence against business-language purpose sentences (German and English) with an
embedder shortlist and a cross-encoder; it points to provisions to check, the RuleSet still
decides. | Input: free-text system description in German or English,
data/rules/ai_act_purpose_catalog.yaml, the operator switches COMPLIANCE_HELPER_RERANK and
COMPLIANCE_HELPER_EMBEDDING | Output: ranked PurposeMatch list (empty when the models are
unavailable or switched off).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from compliance_helper import paths
from compliance_helper.i18n import (
    DEFAULT_LANGUAGE,
    Language,
    all_languages,
    description_languages,
    pick,
    t,
)

logger = logging.getLogger(__name__)

#: Reranker score from which a citation counts as matched; measured hits lay at 0.75-0.999,
#: misses below 0.05.
THRESHOLD = 0.50

#: Stricter bar for prohibited practices: a false "prohibited" makes a user shut down a business.
THRESHOLD_BY_CLASS = {"prohibited": 0.85}

#: Citations per sentence sent to the reranker; the embedder can shortlist but not decide.
SHORTLIST_SIZE = 5

#: A counter-purpose scoring at least this vetoes every rule, not only its own.
STRONG_COUNTER_PURPOSE = 0.90

#: Per-rule cap so the 17 near-identical Annex I entries cannot fill the shortlist.
MAX_CITATIONS_PER_RULE = 2

#: Reranker cost is quadratic in length; 128 tokens cut 10-35 s to under 3 s per question.
MAX_RERANK_TOKENS = 128

MAX_MATCHES = 4

#: Operator switches shared with the search service: the cross-encoder, and the embedding model
#: (a fallback value means: load no model at all).
RERANK_SWITCH = "COMPLIANCE_HELPER_RERANK"
EMBEDDING_SWITCH = "COMPLIANCE_HELPER_EMBEDDING"
_SWITCHED_OFF = frozenset({"0", "false", "no", "off", "nein", "aus"})
_NO_MODEL = frozenset({"fallback", "hashing", "hashing-fallback"})

#: "Wir verkaufen eine Software, die …": the purpose sits in the relative clause.
_VENDOR_PREAMBLE = re.compile(
    r"^(?:wir|unser\w*|die|das)\b[^,]{0,90},\s+(?:die|das|der|welche[rs]?)\s+(?P<purpose>.{15,})$",
    re.IGNORECASE | re.DOTALL,
)

#: "We sell a tool that analyses …": the purpose sits in the relative clause. Its verb must
#: follow the pronoun ("that sorts", "which quickly assesses"); "so that HR can …" or
#: "decide which applications …" introduce no purpose.
_VENDOR_PREAMBLE_EN = re.compile(
    r"^(?:we|our\w*|the)\b[^,.;:]{0,90}?(?<!\bso)\s(?:that|which)\s+"
    r"(?P<purpose>(?:\w+ly\s+)?[a-z-]+(?<!s)s\b.{12,})$",
    re.IGNORECASE | re.DOTALL,
)

#: Only system subjects: a human reviewer ("Eine Kollegin …") is relevant for Art. 6(3).
_SYSTEM_SUBJECT_SENTENCE = re.compile(
    r"^(?:sie|es|die\s+ki|das\s+ki[\s-]?system|das\s+system|das\s+tool|das\s+modul|"
    r"das\s+modell|das\s+programm|die\s+software|die\s+anwendung|die\s+app|"
    r"die\s+ki[\s-]?kamera|der\s+bot|der\s+chatbot|der\s+assistent|"
    r"unser(?:e|es)?\s+(?:system|tool|modul|modell|programm|software|anwendung|app|ki))"
    r"\s+(?P<purpose>.{15,})$",
    re.IGNORECASE | re.DOTALL,
)

#: Only system subjects: "A colleague proofreads …" must stay a human actor (Art. 6(3)).
_SYSTEM_SUBJECT_SENTENCE_EN = re.compile(
    r"^(?:it|the\s+ai|the\s+ai[\s-]?system|the\s+system|the\s+tool|the\s+module|"
    r"the\s+model|the\s+program(?:me)?|the\s+software|the\s+application|the\s+app|"
    r"the\s+ai[\s-]?camera|the\s+bot|the\s+chatbot|the\s+assistant|"
    r"our\s+(?:system|tool|module|model|program(?:me)?|software|application|app|ai))"
    r"\s+(?P<purpose>.{15,})$",
    re.IGNORECASE | re.DOTALL,
)

#: Derived first-person sentences, per pattern: (pattern, subject to put in front).
_FIRST_PERSON_REWRITES = (
    (_VENDOR_PREAMBLE, "Wir"),
    (_SYSTEM_SUBJECT_SENTENCE, "Wir"),
    (_VENDOR_PREAMBLE_EN, "We"),
    (_SYSTEM_SUBJECT_SENTENCE_EN, "We"),
)

#: Follow-up prompts name no purpose and dilute every comparison.
_FOLLOW_UP_PROMPT_PATTERN = re.compile(
    r"was (muessen|müssen|gilt|kommt|ist)|fallen wir|f(ae|ä)llt das|d(ue|ü)rfen wir|"
    r"brauchen wir|betrifft uns|ist das (zul(ae|ä)ssig|erlaubt|ein problem)|gibt es da|"
    r"z(ae|ä)hlt das|etwas melden|auf uns zu|welche pflichten|wie sieht|"
    r"k(oe|ö)nnen wir das|haben wir|sind wir|"
    r"what (do|does|must|should|applies|happens|obligations|rules)|"
    r"which (obligations|rules)|do we (fall|need|have|must)|"
    r"does (that|this|it|the ai act) (fall|count|apply|affect|mean)|"
    r"are we (allowed|affected|covered|subject)|"
    r"is (that|this|it) (allowed|permitted|legal|lawful|ok|a problem|high)|"
    r"is there anything|are there any|can we|how do we|anything to (report|consider)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PurposeMatch:
    """A citation whose purpose matches the description; ``purpose`` is in the active language."""

    citation: str
    risk_class: str
    rule: str
    value: float
    purpose: str
    sentence: str

    @property
    def confidence(self) -> str:
        """Confidence label shown in the answer, in the active language."""
        if self.value >= 0.90:
            return t("purposes.confidence_certain")
        if self.value >= 0.70:
            return t("purposes.confidence_likely")
        return t("purposes.confidence_needs_review")


def sentences(description: str) -> list[str]:
    """Split a description into sentences that may state a purpose.

    Follow-up prompts are dropped unless nothing else remains. For each vendor-preamble or
    system-subject sentence a first-person variant ("Wir …" / "We …") is appended, not
    substituted; since the best score wins, it can only help. Its broken grammar is accepted: the
    grammatical person drives the score (0.86 with "Wir", 0.02 correctly inflected).
    """
    text = re.sub(r"\s+", " ", description).strip()
    raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not raw:
        return []
    kept = [s for s in raw if not (s.endswith("?") and _FOLLOW_UP_PROMPT_PATTERN.search(s))]
    kept = kept or raw

    result = list(kept)
    for sentence in kept:
        for pattern, subject in _FIRST_PERSON_REWRITES:
            matches = pattern.match(sentence)
            if matches is None:
                continue
            derived = f"{subject} {matches.group('purpose').strip()}"
            if derived not in result:
                result.append(derived)
            break
    return result


def _required_wording_present(row: PurposeEntry, description: str) -> bool:
    """Check that a word the provision explicitly requires appears in the description.

    Some elements cannot be matched semantically: Art. 5(1)(d) prohibits crime prediction only
    when based *solely* on profiling; otherwise the case is high risk under Annex III point 6(d).
    """
    if not row.required_words:
        return True
    folded = description.lower()
    return any(word.lower() in folded for word in row.required_words)


def switched_off_by() -> str:
    """Return the operator setting that switches purpose matching off, or an empty string.

    Purpose matching cannot work without the cross-encoder, so an explicit
    ``COMPLIANCE_HELPER_RERANK=0`` or a request for no embedding model switches it off. Left
    unset, it stays on: it scores short sentence pairs, not the long passages that make
    search reranking slow.
    """
    rerank = os.environ.get(RERANK_SWITCH, "").strip().lower()
    if rerank in _SWITCHED_OFF:
        return f"{RERANK_SWITCH}={rerank}"
    embedding = os.environ.get(EMBEDDING_SWITCH, "").strip().lower()
    if embedding in _NO_MODEL:
        return f"{EMBEDDING_SWITCH}={embedding}"
    return ""


def _shared_reranker() -> Any:
    """The cross-encoder of the search index, loaded once per process for both uses."""
    from compliance_helper.search import index as search_index

    return search_index.shared_reranker()


def catalog_path() -> Path:
    return paths.rules_dir() / "ai_act_purpose_catalog.yaml"


@dataclass(frozen=True)
class PurposeEntry:
    """A catalog purpose sentence in one language, with its citation.

    ``wording`` holds the same purpose in every language, for display in the active one.
    """

    text: str
    citation: str
    risk_class: str
    rule: str
    counter_purpose: bool
    required_words: tuple[str, ...] = ()
    language: Language = DEFAULT_LANGUAGE
    wording: Mapping[str, str] = field(default_factory=dict, compare=False)


def _wording(value: Any) -> dict[str, str]:
    """Return a catalog sentence as ``{language: text}``; a plain string counts as German."""
    if isinstance(value, Mapping):
        return {str(language): str(text) for language, text in value.items() if text}
    return {DEFAULT_LANGUAGE.value: str(value)}


def read_catalog(path: Path | None = None) -> list[PurposeEntry]:
    """Load the purpose catalog and validate required fields."""
    path = path or catalog_path()
    raw_data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    lines: list[PurposeEntry] = []
    for entry in raw_data.get("entries", []):
        for trait in ("citation", "risk_class", "rule"):
            if not entry.get(trait):
                raise ValueError(f"{path.name}: entry without {trait}: {entry}")
        if not entry.get("purposes"):
            raise ValueError(f"{path.name}: {entry['citation']} lists no purpose")
        required_words = tuple(all_languages(entry.get("required_words")))
        for counter_purpose, catalog_key in ((False, "purposes"), (True, "counter_purposes")):
            for value in entry.get(catalog_key) or []:
                wording = _wording(value)
                for language in Language:
                    text = wording.get(language.value)
                    if not text:
                        continue
                    lines.append(
                        PurposeEntry(
                            text=text,
                            citation=entry["citation"],
                            risk_class=entry["risk_class"],
                            rule=entry["rule"],
                            counter_purpose=counter_purpose,
                            required_words=required_words,
                            language=language,
                            wording=wording,
                        )
                    )
    return lines


@dataclass
class PurposeMatcher:
    """Finds the provisions whose purpose a description matches.

    Uses the search index's cross-encoder and, once the service hands it over, the search
    index's embedding model, so no model is loaded twice.
    """

    lines: list[PurposeEntry] = field(default_factory=list)
    threshold: float = THRESHOLD
    unavailable_reason: str = ""
    _vectors: np.ndarray | None = None
    _embedder: Any = None
    _reranker: Any = None
    _reranker_attempted: bool = False

    @classmethod
    def from_catalog(cls, path: Path | None = None, threshold: float = THRESHOLD) -> PurposeMatcher:
        return cls(lines=read_catalog(path), threshold=threshold)

    def _catalog_fingerprint(self, model: str) -> str:
        """Identify the embedded sentences and model; any change invalidates the cache."""
        digest = hashlib.sha256(model.encode("utf-8"))
        for line in self.lines:
            digest.update(b"\0" + line.text.encode("utf-8"))
        return digest.hexdigest()

    def _get_vectors(self, cache_file: Path | None = None) -> np.ndarray | None:
        """Embedded catalog sentences of all languages, computed once and cached on disk.

        The cache is keyed by model and sentence text: a changed sentence, a new language or a
        fallback embedder with other dimensions would otherwise reuse stale vectors.
        """
        if self._vectors is not None:
            return self._vectors
        embedder = self._get_embedder()
        if embedder is None:
            return None
        fingerprint = self._catalog_fingerprint(str(getattr(embedder, "name", "")))
        cache_file = cache_file or (catalog_path().parent / "_purpose_vectors.json.gz")
        if cache_file.exists():
            try:
                with gzip.open(cache_file, "rt", encoding="utf-8") as file:
                    stored = json.load(file)
                if stored.get("fingerprint") == fingerprint:
                    self._vectors = np.asarray(stored["vectors"], dtype=np.float32)
                    return self._vectors
                logger.info("Cached purpose vectors are stale, recomputing")
            except Exception as error:
                logger.warning("Cached purpose vectors unreadable (%s), recomputing", error)
        self._vectors = np.asarray(
            embedder.embed_passages([z.text for z in self.lines]).dense, dtype=np.float32
        )
        try:
            with gzip.open(cache_file, "wt", encoding="utf-8") as file:
                json.dump(
                    {
                        "fingerprint": fingerprint,
                        "count": len(self.lines),
                        "vectors": self._vectors.tolist(),
                    },
                    file,
                )
        except Exception as error:
            logger.info("Could not cache purpose vectors: %s", error)
        return self._vectors

    def share_embedder(self, embedder: Any) -> None:
        """Use an embedding model that is already loaded, such as the search index's."""
        if self._embedder is None:
            self._embedder = embedder

    def load(self) -> bool:
        """Load the models and the catalog vectors now, e.g. at service start.

        Returns:
            Whether purpose matching is available; if not, ``unavailable_reason`` says why.
        """
        return self._get_reranker() is not None and self._get_vectors() is not None

    def _get_embedder(self) -> Any:
        if self._embedder is None and not switched_off_by():
            try:
                from compliance_helper.search.embedding import choose_embedder

                self._embedder = choose_embedder(
                    os.environ.get(EMBEDDING_SWITCH, "").strip() or None
                )
            except Exception as error:
                logger.warning("No embedder for purpose matching: %s", error)
        return self._embedder

    def _get_reranker(self) -> Any:
        if not self._reranker_attempted:
            self._reranker_attempted = True
            self.unavailable_reason = switched_off_by()
            if not self.unavailable_reason:
                self._reranker = _shared_reranker()
                self.unavailable_reason = "" if self._reranker is not None else "no cross-encoder"
            if self.unavailable_reason:
                logger.warning(
                    "Purpose matching off (%s); classification uses the rule keywords only",
                    self.unavailable_reason,
                )
        return self._reranker

    def find(self, description: str) -> list[PurposeMatch]:
        """Return up to MAX_MATCHES citations whose purpose the description matches.

        Per citation the best purpose sentence counts; per rule the best counter-purpose
        counts and vetoes the whole rule (a counter-purpose hit under Annex I point 1 must also
        block point 11). A counter-purpose above STRONG_COUNTER_PURPOSE vetoes all rules. Only
        catalog sentences in the description's language take part (both when undecided).
        """
        parts = sentences(description)
        if not parts or not self.lines:
            return []
        reranker = self._get_reranker()
        if reranker is None:
            return []

        languages = description_languages(description)
        candidates = [i for i, row in enumerate(self.lines) if row.language in languages]
        shortlisted_pairs = self._shortlist(parts, candidates)
        pairs = [[parts[s], self.lines[i].text] for s, i in shortlisted_pairs]
        logger.debug("Purpose matching: %d sentences, %d pairs", len(parts), len(pairs))
        if not pairs:
            return []
        try:
            values = reranker.compute_score(
                pairs, normalize=True, max_length=MAX_RERANK_TOKENS, batch_size=len(pairs)
            )
        except Exception as error:
            logger.warning("Purpose scoring failed: %s", error)
            return []
        if not isinstance(values, list):
            values = [values]

        best_by_citation: dict[str, tuple[float, PurposeEntry, str]] = {}
        counter_scores: dict[str, float] = {}
        strong_counter_score = 0.0
        for (s, i), raw_score in zip(shortlisted_pairs, values, strict=False):
            row = self.lines[i]
            value = float(raw_score)
            if row.counter_purpose:
                if value > counter_scores.get(row.rule, -1.0):
                    counter_scores[row.rule] = value
                if value >= STRONG_COUNTER_PURPOSE:
                    strong_counter_score = max(strong_counter_score, value)
            elif value > best_by_citation.get(row.citation, (-1.0,))[0]:
                best_by_citation[row.citation] = (value, row, parts[s])

        matches = [
            PurposeMatch(
                citation=citation,
                risk_class=row.risk_class,
                rule=row.rule,
                value=round(value, 4),
                purpose=pick(row.wording) or row.text,
                sentence=sentence,
            )
            for citation, (value, row, sentence) in best_by_citation.items()
            if value >= THRESHOLD_BY_CLASS.get(row.risk_class, self.threshold)
            and value > max(counter_scores.get(row.rule, -1.0), strong_counter_score)
            and _required_wording_present(row, description)
        ]
        return sorted(matches, key=lambda t: -t.value)[:MAX_MATCHES]

    def _shortlist(self, parts: list[str], candidates: list[int]) -> list[tuple[int, int]]:
        """Select (sentence, catalog line) index pairs among ``candidates`` for the reranker.

        Without an embedder all candidate pairs are returned: slower, but not wrong.
        """
        all_items = [(s, i) for s in range(len(parts)) for i in candidates]
        vectors = self._get_vectors()
        embedder = self._get_embedder()
        if vectors is None or embedder is None:
            return all_items
        try:
            questions = np.asarray(embedder.embed_queries(parts).dense, dtype=np.float32)
        except Exception as error:
            logger.warning("Shortlisting failed: %s", error)
            return all_items
        similarity = vectors @ questions.T

        pairs: list[tuple[int, int]] = []
        allowed = set(candidates)
        for s in range(len(parts)):
            column = similarity[:, s]
            vector = sorted(candidates, key=lambda i: -float(column[i]))
            # Shortlist whole citations, not lines, so their counter-purposes are scored too.
            citations: list[str] = []
            count_by_rule: dict[str, int] = {}
            for i in vector:
                row = self.lines[i]
                if row.citation in citations:
                    continue
                if count_by_rule.get(row.rule, 0) >= MAX_CITATIONS_PER_RULE:
                    continue
                citations.append(row.citation)
                count_by_rule[row.rule] = count_by_rule.get(row.rule, 0) + 1
                if len(citations) >= SHORTLIST_SIZE:
                    break
            chosen = set(citations)
            pairs += [
                (s, i) for i, z in enumerate(self.lines) if z.citation in chosen and i in allowed
            ]
        return pairs


@lru_cache(maxsize=1)
def purpose_matcher() -> PurposeMatcher:
    """Process-wide PurposeMatcher, sharing its models with the search index."""
    return PurposeMatcher.from_catalog()
