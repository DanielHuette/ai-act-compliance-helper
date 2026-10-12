"""Purpose catalog shape and purpose-route accuracy.

Context: the purpose route is a second entrance to the rule set whose quality depends on sentence
form in both languages; shape checks always run, accuracy needs the models and is marked
``slow``. | Input: purpose catalog, rule set, corpus ids,
data/evaluation/company_questions.yaml | Output: pass when the catalog is well-formed and German
accuracy reaches the gate; ``measure_accuracy`` is shared with the English accuracy test.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from compliance_helper.classification import purposes
from compliance_helper.classification.assessor import rule_set
from compliance_helper.classification.purposes import (
    STRONG_COUNTER_PURPOSE,
    THRESHOLD,
    THRESHOLD_BY_CLASS,
    PurposeEntry,
    PurposeMatcher,
    catalog_path,
    read_catalog,
    sentences,
)
from compliance_helper.corpus.build import load
from compliance_helper.domain import RiskClass
from compliance_helper.i18n import Language, description_languages, use_language

COMPANY_QUESTIONS = (
    Path(__file__).resolve().parents[1] / "data" / "evaluation" / "company_questions.yaml"
)
ACCURACY_GATE = 95

CATALOG_ENTRIES = read_catalog()
CORPUS_IDS = {e.id for e in load()}


def _rule_ids() -> set[str]:
    """All rule ids defined by the rule set across every tier."""
    rules = rule_set().risk_classes_rules
    ids: set[str] = set()
    for rule in rules.get("prohibitions", []):
        ids.add(rule["id"])
    for api_key in ("high_risk_annex_i", "high_risk_exemption", "gpai", "minimal"):
        part = rules.get(api_key) or {}
        if part.get("id"):
            ids.add(part["id"])
    for area in (rules.get("high_risk_annex_iii") or {}).get("areas", []):
        ids.add(area["id"])
    for case in (rules.get("transparency") or {}).get("cases", []):
        ids.add(case["id"])
    return ids


def test_catalog_is_not_empty() -> None:
    assert len(CATALOG_ENTRIES) >= 100, "purpose catalog is too thin to be useful"


def test_every_citation_points_to_official_text() -> None:
    """A citation that does not exist would put an unverifiable legal basis into the answer."""
    missing = sorted({z.citation for z in CATALOG_ENTRIES if z.citation not in CORPUS_IDS})
    assert not missing, f"citations without corpus text: {missing}"


def test_every_rule_exists_in_rule_set() -> None:
    """An entry pointing to an unknown rule triggers nothing and fails silently."""
    known = _rule_ids()
    unexpected = sorted({z.rule for z in CATALOG_ENTRIES if z.rule not in known})
    assert not unexpected, f"rule ids unknown to the rule set: {unexpected}"


def test_every_class_is_a_valid_risk_class() -> None:
    valid = {k.value for k in RiskClass}
    unexpected = sorted({z.risk_class for z in CATALOG_ENTRIES if z.risk_class not in valid})
    assert not unexpected, f"unknown classes in catalog: {unexpected}"


def test_purpose_sentences_are_first_person() -> None:
    """Purpose sentences use the measured form: first-person plural statement, in each language.

    Measured scores: infinitive 0.036-0.447, third person 0.037-0.546, first person
    0.986-0.989, against a threshold of 0.50.
    """
    patterns = {
        Language.DE: re.compile(r"^(Wir|Unser(e|es)?)\b.*[.!]$"),
        Language.EN: re.compile(r"^(We|Our)\b.*[.!]$"),
    }
    wrong = [z.text for z in CATALOG_ENTRIES if not patterns[z.language].match(z.text)]
    assert not wrong, "purpose sentences not in the measured form:\n" + "\n".join(wrong[:10])


def test_every_purpose_is_stated_in_every_language() -> None:
    """A purpose missing in one language is invisible to descriptions in that language."""
    raw_data = yaml.safe_load(catalog_path().read_text(encoding="utf-8"))
    incomplete = [
        f"{entry['citation']}: {value}"
        for entry in raw_data["entries"]
        for key in ("purposes", "counter_purposes")
        for value in entry.get(key) or []
        if not (isinstance(value, dict) and all(value.get(lang.value) for lang in Language))
    ]
    assert not incomplete, "\n".join(incomplete[:10])


def test_required_words_exist_in_every_language() -> None:
    raw_data = yaml.safe_load(catalog_path().read_text(encoding="utf-8"))
    for entry in raw_data["entries"]:
        words = entry.get("required_words")
        if words:
            assert all(words.get(lang.value) for lang in Language), entry["citation"]


def test_purpose_sentences_are_sentences_not_keyword_lists() -> None:
    brief = [z.text for z in CATALOG_ENTRIES if len(z.text.split()) < 4]
    assert not brief, f"too short to be a purpose: {brief}"


def test_no_duplicate_purpose_sentences() -> None:
    """The same sentence under two citations would make the justification arbitrary."""
    seen: dict[tuple[Language, str], str] = {}
    duplicates: list[str] = []
    for z in CATALOG_ENTRIES:
        if z.counter_purpose:
            # One counter-purpose may relieve several rules, e.g. Annex III points 1 and 4.
            continue
        key = (z.language, z.text)
        if key in seen and seen[key] != z.citation:
            duplicates.append(f"{z.text!r} at {seen[key]} and {z.citation}")
        seen[key] = z.citation
    assert not duplicates, "\n".join(duplicates)


def test_every_entry_names_at_least_one_purpose() -> None:
    raw_data = yaml.safe_load(catalog_path().read_text(encoding="utf-8"))
    without = [e["citation"] for e in raw_data["entries"] if not e.get("purposes")]
    assert not without, f"entries without purpose: {without}"


def test_catalog_states_its_version() -> None:
    raw_data = yaml.safe_load(catalog_path().read_text(encoding="utf-8"))
    assert raw_data.get("as_of"), "catalog without as_of cannot be dated"


def test_prohibitions_have_higher_threshold() -> None:
    """A false prohibition shuts down a business, so it needs stronger evidence.

    Measured: an essay-grading platform scored 0.6297, an employee mood app 0.9974; the
    threshold lies between them.
    """
    assert THRESHOLD_BY_CLASS["prohibited"] > THRESHOLD
    assert 0.63 < THRESHOLD_BY_CLASS["prohibited"] < 0.99


def test_strong_counter_purpose_is_above_threshold() -> None:
    assert STRONG_COUNTER_PURPOSE > THRESHOLD


def test_follow_up_prompt_is_dropped() -> None:
    parts = sentences("Die KI liest Lebensläufe. Was müssen wir beachten?")
    assert not any("beachten" in s for s in parts)


def test_vendor_preamble_is_derived() -> None:
    """The purpose sits in the relative clause (measured 0.35 with preamble, 0.75 without)."""
    parts = sentences("Wir verkaufen eine Software, die Gesichter mit einer Liste abgleicht.")
    assert any(s.startswith("Wir Gesichter mit einer Liste") for s in parts)


def test_system_subject_sentence_is_derived() -> None:
    parts = sentences("Sie verteilt die Nachtschichten danach, wer wie oft krank war.")
    assert any(s.startswith("Wir verteilt die Nachtschichten") for s in parts)


def test_human_subject_is_not_rewritten_to_we() -> None:
    """A human actor must not be rewritten to "Wir": human review relieves under Article 6(3)."""
    parts = sentences("Eine Kollegin liest alles gegen, bevor es online geht.")
    assert all(not s.startswith("Wir liest") for s in parts)


def test_english_follow_up_prompt_is_dropped() -> None:
    parts = sentences("The AI reads CVs. What do we need to consider?")
    assert not any("consider" in s for s in parts)


def test_english_vendor_preamble_is_derived() -> None:
    parts = sentences("We sell a tool that compares faces with a list of visitors.")
    assert "We compares faces with a list of visitors." in parts


def test_english_system_subject_sentence_is_derived() -> None:
    parts = sentences("It assigns the night shifts according to who was off sick most often.")
    assert any(s.startswith("We assigns the night shifts") for s in parts)


def test_english_human_subject_is_not_rewritten_to_we() -> None:
    parts = sentences("A colleague proofreads everything before it goes online.")
    assert parts == ["A colleague proofreads everything before it goes online."]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Wir verkaufen eine Software, die Lebensläufe liest und Bewerber vorschlägt.",
            {Language.DE},
        ),
        (
            "We sell software that reads CVs and suggests the best applicants to the recruiter.",
            {Language.EN},
        ),
        ("Recruiting-Tool", set(Language)),
    ],
)
def test_description_language_selects_catalog_sentences(text: str, expected: set) -> None:
    """Clear German or English text is compared with its own language, anything else with both."""
    assert description_languages(text) == expected


def test_description_without_statement_is_kept() -> None:
    """A bare question is still scored; imprecise beats nothing."""
    parts = sentences("Was müssen wir beachten?")
    assert parts == ["Was müssen wir beachten?"]


def test_purpose_route_is_empty_without_models() -> None:
    """Offline container and mobile must still classify without models."""
    matcher = PurposeMatcher(lines=CATALOG_ENTRIES)
    matcher._reranker_attempted = True
    matcher._reranker = None
    assert matcher.find("Wir sichten Bewerbungen und sortieren sie vor.") == []


def _forbidden(*_: Any, **__: Any) -> Any:
    raise AssertionError("no model may be loaded here")


@pytest.mark.parametrize(
    ("switch", "value"),
    [
        ("COMPLIANCE_HELPER_RERANK", "0"),
        ("COMPLIANCE_HELPER_EMBEDDING", "hashing-fallback"),
    ],
)
def test_operator_switch_turns_purpose_matching_off(monkeypatch, switch: str, value: str) -> None:
    """The operator's "no cross-encoder" or "no model" also holds for purpose matching."""
    monkeypatch.delenv("COMPLIANCE_HELPER_RERANK", raising=False)
    monkeypatch.delenv("COMPLIANCE_HELPER_EMBEDDING", raising=False)
    monkeypatch.setenv(switch, value)
    monkeypatch.setattr(purposes, "_shared_reranker", _forbidden)
    matcher = PurposeMatcher(lines=CATALOG_ENTRIES)
    assert not matcher.load()
    assert switch in matcher.unavailable_reason
    assert matcher.find("Wir sichten Bewerbungen und sortieren sie vor.") == []


def test_purpose_matching_uses_the_search_index_models(monkeypatch) -> None:
    """One cross-encoder and one embedding model per process, not a second copy of each."""
    from compliance_helper.search import embedding
    from compliance_helper.search import index as search_index

    monkeypatch.delenv("COMPLIANCE_HELPER_RERANK", raising=False)
    monkeypatch.delenv("COMPLIANCE_HELPER_EMBEDDING", raising=False)
    cross_encoder = _RecordingReranker()
    monkeypatch.setattr(search_index, "shared_reranker", lambda: cross_encoder)
    monkeypatch.setattr(embedding, "choose_embedder", _forbidden)
    index_embedder = _UnitEmbedder()
    matcher = PurposeMatcher(lines=_bilingual_entries())
    matcher.share_embedder(index_embedder)
    assert matcher._get_reranker() is cross_encoder
    assert matcher._get_embedder() is index_embedder


class _RecordingReranker:
    """Scores every pair 0.9 and remembers which catalog sentences it saw."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def compute_score(self, pairs: list[list[str]], **_: Any) -> list[float]:
        self.seen += [purpose for _, purpose in pairs]
        return [0.9] * len(pairs)


class _UnitEmbedder:
    """Same vector for every text, so the shortlist depends on the candidates alone."""

    name = "unit-test"

    def __init__(self) -> None:
        self.embedded: list[list[str]] = []

    def embed_queries(self, texts: list[str]) -> Any:
        return type("Result", (), {"dense": np.ones((len(texts), 2), dtype=np.float32)})

    def embed_passages(self, texts: list[str]) -> Any:
        self.embedded.append(list(texts))
        return self.embed_queries(texts)


def _bilingual_entries() -> list[PurposeEntry]:
    wording = {"de": "Wir sichten Bewerbungen.", "en": "We screen job applications."}
    return [
        PurposeEntry(
            text=wording[language.value],
            citation="AI-Act/annex-III/pt-4-a",
            risk_class="high_risk_annex_iii",
            rule="annex3-4-employment",
            counter_purpose=False,
            language=language,
            wording=wording,
        )
        for language in Language
    ]


def test_english_description_is_scored_against_english_sentences_only() -> None:
    reranker = _RecordingReranker()
    matcher = PurposeMatcher(lines=_bilingual_entries())
    matcher._reranker_attempted, matcher._reranker = True, reranker
    matcher._embedder, matcher._vectors = _UnitEmbedder(), np.ones((2, 2), dtype=np.float32)

    with use_language(Language.DE):
        found = matcher.find("We sell a tool that screens job applications for the recruiter.")

    assert reranker.seen and set(reranker.seen) == {"We screen job applications."}
    assert found[0].purpose == "Wir sichten Bewerbungen.", "shown in the active language"
    assert found[0].confidence == "sicher"


def test_vector_cache_is_rebuilt_when_a_sentence_changes(tmp_path: Path) -> None:
    """A cache keyed only by count would keep vectors of a reworded sentence."""
    cache = tmp_path / "vectors.json.gz"
    first = PurposeMatcher(lines=_bilingual_entries())
    first._embedder = _UnitEmbedder()
    first._get_vectors(cache)
    reworded = [
        PurposeEntry(**{**vars(entry), "text": entry.text.replace("screen", "sift")})
        for entry in _bilingual_entries()
    ]
    second = PurposeMatcher(lines=reworded)
    second._embedder = embedder = _UnitEmbedder()
    second._get_vectors(cache)

    assert embedder.embedded == [[z.text for z in reworded]]
    with gzip.open(cache, "rt", encoding="utf-8") as file:
        assert json.load(file)["count"] == len(reworded)


def _company_questions() -> list[dict[str, Any]]:
    return list(yaml.safe_load(COMPANY_QUESTIONS.read_text(encoding="utf-8"))["questions"])


def _is_model_cached(model: str) -> bool:
    """Check the local Hugging Face cache without downloading (the reranker is about 2 GB)."""
    try:
        from huggingface_hub import try_to_load_from_cache
    except Exception:
        return False
    try:
        return isinstance(try_to_load_from_cache(model, "config.json"), str)
    except Exception:
        return False


def test_company_questions_are_complete_and_mixed() -> None:
    """The question set needs enough minimal cases, or calling everything high-risk would win."""
    questions = _company_questions()
    assert len(questions) >= 100
    harmless = [f for f in questions if f["classification"] == "minimal"]
    assert len(harmless) >= 25, "too few harmless cases; the rate would be meaningless"
    valid = {k.value for k in RiskClass}
    assert all(f["classification"] in valid for f in questions)
    assert all(f.get("expected_provision") for f in questions), (
        "every expected verdict needs its provision"
    )
    assert all(
        isinstance(f["question"], dict) and all(f["question"].get(lang.value) for lang in Language)
        for f in questions
    ), "every question is asked in German and English"


def measure_accuracy(language: Language) -> tuple[int, list[str]]:
    """Classify every company question in ``language`` with both models; return hits and misses.

    Skips when a model is not cached: the reranker alone is about 2 GB.
    """
    from compliance_helper.classification.assessor import Assessor, description_from_text
    from compliance_helper.domain import Role

    for model in ("BAAI/bge-reranker-v2-m3", "BAAI/bge-m3"):
        if not _is_model_cached(model):
            pytest.skip(f"{model} is not cached on this machine")

    assessor = Assessor()
    if assessor.purpose_matcher() is None or assessor.purpose_matcher()._get_reranker() is None:
        pytest.skip("accuracy cannot be measured without the reranker")

    correct = 0
    wrong: list[str] = []
    with use_language(language):
        for case in _company_questions():
            question = case["question"][language.value]
            description = description_from_text(question).model_copy(
                update={"roles": (Role(case["role"]),)}
            )
            actual = [k.value for k in assessor.check(description).risk_classes]
            if case["classification"] in actual:
                correct += 1
            else:
                wrong.append(
                    f"expected={case['classification']} got={','.join(actual)}: {question[:70]}"
                )
    return correct, wrong


@pytest.mark.slow
def test_accuracy_on_company_questions() -> None:
    """German accuracy with embedder and reranker; the gate is 95 of 100."""
    correct, wrong = measure_accuracy(Language.DE)
    assert correct >= ACCURACY_GATE, f"only {correct} of 100 correct:\n" + "\n".join(wrong)
