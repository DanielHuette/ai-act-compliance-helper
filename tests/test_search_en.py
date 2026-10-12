"""English search: its own index, English citations and keywords, the same unit ids as German.

Context: English questions are answered from the English corpus and index; ids are
language-neutral, so a citation names the same unit in both languages. Fast tests use the
fallback embedder, ``slow`` tests the shipped indexes with bge-m3. | Input: English corpus,
English and German questions, data/processed/search_index[.en].* | Output: pass when English
questions find the expected provisions in the index of the active language.
"""

from __future__ import annotations

import pytest

from compliance_helper.corpus.build import load
from compliance_helper.domain import UnitKind
from compliance_helper.i18n import Language, use_language
from compliance_helper.search import store
from compliance_helper.search.citations import citations_from_question
from compliance_helper.search.embedding import HashingEmbedder
from compliance_helper.search.index import SearchIndex, to_passages
from compliance_helper.security import ServiceNotReadyError
from compliance_helper.service.app import ServiceState

CITATION_QUERIES = {Language.EN: "Article 6(3)", Language.DE: "Artikel 6 Absatz 3"}


@pytest.fixture(scope="module")
def english_corpus():
    try:
        return load(Language.EN)
    except FileNotFoundError:
        pytest.skip("No English corpus (run compliance-helper build-corpus --language en)")


@pytest.fixture(scope="module")
def english_sample_index(english_corpus):
    sample = [
        unit
        for unit in english_corpus
        if unit.id.startswith(
            ("AI-Act/art-5", "AI-Act/art-6", "AI-Act/annex-III", "GDPR/art-22", "BDSG/sec-26")
        )
    ]
    index = SearchIndex(sample, HashingEmbedder(), Language.EN)
    index.build()
    return index


@pytest.mark.parametrize(
    "question,expected",
    [
        ("point (f) of Article 5(1) AI Act", "AI-Act/art-5/para-1-f"),
        ("Article 5(1), point (f) of the AI Act", "AI-Act/art-5/para-1-f"),
        ("Art. 5 Abs. 1 lit. f KI-VO", "AI-Act/art-5/para-1-f"),
        ("Article 22(1) GDPR", "GDPR/art-22/para-1"),
        ("Annex III point 4", "AI-Act/annex-III/pt-4"),
    ],
)
def test_citation_route_reads_eu_citation_styles(question, expected):
    assert expected in citations_from_question(question)


def test_citation_route_maps_both_languages_to_the_same_ids():
    assert citations_from_question(CITATION_QUERIES[Language.EN]) == citations_from_question(
        CITATION_QUERIES[Language.DE]
    )


def test_english_index_has_the_ids_of_the_german_one(english_corpus, corpus):
    assert [unit.id for unit in english_corpus] == [unit.id for unit in corpus]


def test_cited_provision_ranks_first_in_english(english_sample_index):
    hits = english_sample_index.search("What does Article 6(3) say?", count=5, rerank=False)
    assert hits[0].unit.id == "AI-Act/art-6/para-3", [hit.unit.id for hit in hits]


def test_english_keywords_find_the_wording(english_sample_index):
    hits = english_sample_index.search(
        "automated individual decision-making", count=5, rerank=False
    )
    assert any(hit.unit.id.startswith("GDPR/art-22") for hit in hits), [h.unit.id for h in hits]


def test_english_search_never_returns_more_than_requested(english_sample_index):
    for count in (1, 3, 10):
        assert len(english_sample_index.search("high-risk", count=count, rerank=False)) <= count


def test_english_passages_cite_in_english(english_sample_index):
    hits = english_sample_index.search("Article 6(3)", count=3, rerank=False)
    with use_language(Language.EN):
        citations = [passage.citation for passage in to_passages(hits)]
    assert citations[0] == "Article 6(3) AI Act"


def test_service_answers_with_the_index_of_the_active_language(english_sample_index, small_german):
    state = ServiceState(indexes={Language.DE: small_german, Language.EN: english_sample_index})
    for language in Language:
        with use_language(language):
            assert state.search_index is not None
            assert state.search_index.language is language


def test_missing_english_index_is_a_clear_english_error(small_german):
    state = ServiceState(indexes={Language.DE: small_german})
    with use_language(Language.EN), pytest.raises(ServiceNotReadyError) as error:
        state.require_search_index()
    assert "English search index is missing" in str(error.value)
    assert "--language en" in str(error.value)


def test_rebuild_hint_of_a_foreign_english_index_names_the_language(english_sample_index, tmp_path):
    target = tmp_path / "search_index.en"
    english_sample_index.save(target)
    units = english_sample_index.units
    for mismatched in ([units[-1], *units[:-1]], units[:-1]):
        with pytest.raises(RuntimeError, match=r"build-index --language en$"):
            SearchIndex.load(Language.EN, mismatched, HashingEmbedder(), path=target)


@pytest.fixture(scope="module")
def small_german(corpus):
    index = SearchIndex(
        [unit for unit in corpus if unit.id.startswith("AI-Act/art-6")], HashingEmbedder()
    )
    index.build()
    return index


@pytest.fixture(scope="module")
def shipped_indexes() -> dict[Language, SearchIndex]:
    """Both shipped indexes, sharing one bge-m3 model as the service does."""
    for language in Language:
        if not store.exists(store.index_path(language)):
            pytest.skip(f"No stored {language.value} index ({store.build_command(language)})")
    german = SearchIndex.load(Language.DE)
    return {
        Language.DE: german,
        Language.EN: SearchIndex.load(Language.EN, embedder=german.embedder),
    }


@pytest.mark.slow
@pytest.mark.parametrize(
    "question,expected_prefix",
    [
        ("Is emotion recognition in the workplace prohibited?", "AI-Act/art-5/para-1-f"),
        ("When is an AI system in employment high-risk?", "AI-Act/annex-III/pt-4"),
        ("automated individual decision-making", "GDPR/art-22"),
        ("processing of employee data", "BDSG/sec-26"),
    ],
)
def test_english_questions_find_the_expected_norm(shipped_indexes, question, expected_prefix):
    with use_language(Language.EN):
        hits = shipped_indexes[Language.EN].search(question, count=8, rerank=False)
    ids = [hit.unit.id for hit in hits]
    assert any(unit_id.startswith(expected_prefix) for unit_id in ids), ids


@pytest.mark.slow
def test_shipped_english_index_is_english_with_english_text(shipped_indexes):
    english = shipped_indexes[Language.EN]
    assert english.language is Language.EN
    article = english.units[english._position_by_id["AI-Act/art-5/para-1-f"]]
    assert "emotions of a natural person" in article.text


@pytest.mark.slow
def test_shipped_english_search_never_returns_more_than_requested(shipped_indexes):
    with use_language(Language.EN):
        for count in (1, 4, 9):
            hits = shipped_indexes[Language.EN].search(
                "high-risk AI system", count=count, rerank=False
            )
            assert len(hits) <= count


@pytest.mark.slow
def test_explicit_citation_returns_the_same_units_in_both_languages(shipped_indexes):
    """Without a legal act both the AI Act and the GDPR article qualify, in either language."""
    cited: dict[Language, set[str]] = {}
    for language, question in CITATION_QUERIES.items():
        with use_language(language):
            hits = shipped_indexes[language].search(question, count=8, rerank=False)
        cited[language] = {hit.unit.id for hit in hits if "citation" in hit.routes}
    assert cited[Language.EN] == cited[Language.DE] == {"AI-Act/art-6/para-3", "GDPR/art-6/para-3"}


@pytest.mark.slow
@pytest.mark.parametrize(
    "language,question",
    [(Language.EN, "Article 6(3) AI Act"), (Language.DE, "Artikel 6 Absatz 3 KI-VO")],
)
def test_citation_naming_the_act_ranks_that_unit_first(shipped_indexes, language, question):
    with use_language(language):
        hits = shipped_indexes[language].search(question, count=8, rerank=False)
    assert hits[0].unit.id == "AI-Act/art-6/para-3", [hit.unit.id for hit in hits]


@pytest.mark.slow
def test_english_cases_do_not_crowd_out_legal_text(shipped_indexes):
    with use_language(Language.EN):
        hits = shipped_indexes[Language.EN].search(
            "May we pre-sort job applications with a language model?", count=6, rerank=False
        )
    assert sum(hit.unit.kind is UnitKind.EXAMPLE for hit in hits) <= 2


@pytest.mark.slow
def test_shipped_english_index_is_current(shipped_indexes):
    english = shipped_indexes[Language.EN]
    assert english.text_hashes == [store.text_hash(text) for text in english.index_texts()]
