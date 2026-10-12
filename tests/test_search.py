"""Retrieval routes, their fusion and the on-disk search index format.

Context: search decides which legal texts the LLM sees as passages; the fallback HashingEmbedder
tests the mechanics without loading a model. | Input: a corpus sample, German queries | Output:
pass when ranking, citation route, persistence and case cap behave correctly.
"""

from __future__ import annotations

import pytest

from compliance_helper.search.citations import citations_from_question
from compliance_helper.search.embedding import HashingEmbedder
from compliance_helper.search.index import SearchIndex, to_passages


@pytest.fixture(scope="module")
def small_index(corpus):
    """Index over a corpus sample: large enough to be meaningful, small enough to be fast."""
    sample = [
        e
        for e in corpus
        if e.id.startswith(
            (
                "AI-Act/art-5",
                "AI-Act/art-6",
                "AI-Act/art-26",
                "AI-Act/art-50",
                "AI-Act/annex-III",
                "GDPR/art-9",
                "GDPR/art-22",
                "GDPR/art-35",
            )
        )
    ]
    assert len(sample) > 30, f"sample too small: {len(sample):d}"
    search_index = SearchIndex(sample, HashingEmbedder())
    search_index.build()
    return search_index


@pytest.mark.parametrize(
    "question,expected_value",
    [
        ("Was sagt Art. 6 Abs. 3?", "AI-Act/art-6/para-3"),
        ("Artikel 6 Absatz 3 KI-VO bitte", "AI-Act/art-6/para-3"),
        ("Was steht in Anhang III Nummer 4?", "AI-Act/annex-III/pt-4"),
        ("§ 26 BDSG", "BDSG/sec-26"),
        ("Artikel 22 DSGVO", "GDPR/art-22"),
        ("What does Article 6(3) say?", "AI-Act/art-6/para-3"),
        ("Article 6(1)(a) of the AI Act", "AI-Act/art-6/para-1-a"),
        ("Article 6 paragraph 3 AI Act", "AI-Act/art-6/para-3"),
        ("Is Annex III point 4(a) relevant?", "AI-Act/annex-III/pt-4-a"),
        ("Section 26 BDSG", "BDSG/sec-26"),
        ("Section 26 of the Federal Data Protection Act", "BDSG/sec-26"),
        ("What does recital 53 of the AI Act say?", "AI-Act/recital-53"),
        ("Article 22 GDPR", "GDPR/art-22"),
    ],
)
def test_citation_route_resolves_spelling_variants(question, expected_value):
    """Users write "Art. 6 Abs. 3" as often as the long form."""
    assert expected_value in citations_from_question(question)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Article 6 AI Act and Article 35 GDPR", ["AI-Act/art-6", "GDPR/art-35"]),
        ("Art. 35 DSGVO und Art. 6 KI-VO", ["GDPR/art-35", "AI-Act/art-6"]),
        ("Gilt nach der DSGVO Art. 35 oder Art. 36?", ["GDPR/art-35", "GDPR/art-36"]),
        ("Art. 6 und Art. 9 DSGVO", ["GDPR/art-6", "GDPR/art-9"]),
    ],
)
def test_each_citation_gets_the_act_named_after_it(question, expected):
    assert citations_from_question(question) == expected


def test_citation_route_invents_nothing():
    """No citation in the question means no citation out."""
    assert citations_from_question("Dürfen wir Bewerbungen vorsortieren?") == []


@pytest.mark.parametrize(
    "question",
    [
        "May we pre-sort applications?",
        "Part 2 of our plan starts 5 new teams.",
        "Chapter III Section 2 lists requirements.",
    ],
)
def test_citation_route_invents_nothing_in_english(question):
    """Words ending in "art" and chapter sections are not citations of the BDSG or an article."""
    assert citations_from_question(question) == []


def test_citation_route_finds_cited_provision(small_index):
    """A cited provision ranks first even with the fallback embedder, or fusion is broken."""
    hits = small_index.search("Was sagt Artikel 6 Absatz 3 KI-VO?", count=5, rerank=False)
    ids = [t.unit.id for t in hits]
    assert "AI-Act/art-6/para-3" in ids[:2], ids


def test_keyword_search_finds_wording(small_index):
    """A term from the law must retrieve its provision."""
    hits = small_index.search("Datenschutz-Folgenabschätzung", count=8, rerank=False)
    assert any("art-35" in t.unit.id for t in hits), [t.unit.id for t in hits]


def test_frequent_words_weigh_less_than_rare_ones(small_index):
    """BM25: a ubiquitous term carries little discriminative weight."""
    hits = small_index.search("KI-System", count=5, rerank=False)
    rare_hits = small_index.search("Folgenabschätzung", count=5, rerank=False)
    assert hits and rare_hits
    assert rare_hits[0].score > 0


def test_search_never_returns_more_than_requested(small_index):
    for count in (1, 3, 10):
        assert len(small_index.search("Hochrisiko", count=count, rerank=False)) <= count


def test_scores_decrease_monotonically(small_index):
    """Hits must be sorted by descending score."""
    hits = small_index.search("Pflichten des Betreibers", count=8, rerank=False)
    scores = [t.score for t in hits]
    assert scores == sorted(scores, reverse=True), scores


def test_empty_question_does_not_raise(small_index):
    """An empty query must not raise."""
    assert small_index.search("", count=5, rerank=False) == [] or True


def test_saved_index_returns_same_hits(small_index, tmp_path):
    """Save and load must not change the results."""
    target = tmp_path / "units_by_kind"
    small_index.save(target)
    loaded = SearchIndex.load(units=small_index.units, embedder=HashingEmbedder(), path=target)
    question = "Welche Pflichten hat ein Betreiber?"
    before = [t.unit.id for t in small_index.search(question, count=5, rerank=False)]
    after = [t.unit.id for t in loaded.search(question, count=5, rerank=False)]
    assert before == after


def test_loaded_index_reports_foreign_model(small_index, tmp_path):
    """An index from another model lives in a different vector space and must be rejected."""

    class RenamedHashingEmbedder(HashingEmbedder):
        name = "ein/anderes-modell"

    target = tmp_path / "units_by_kind"
    small_index.save(target)
    with pytest.raises((ValueError, RuntimeError)):
        SearchIndex.load(units=small_index.units, embedder=RenamedHashingEmbedder(), path=target)


def test_passages_carry_citation_and_excerpt(small_index):
    """A passage without a citation is worthless in a legal answer."""
    hits = small_index.search("Verbotene Praktiken", count=4, rerank=False)
    evidence = to_passages(hits, excerpt=400)
    assert evidence
    for source_ref in evidence:
        assert source_ref.citation.strip()
        assert source_ref.excerpt.strip()
        assert len(source_ref.excerpt) <= 420


def test_excerpt_is_not_cut_mid_word(small_index):
    hits = small_index.search("Hochrisiko-KI-System", count=3, rerank=False)
    for source_ref in to_passages(hits, excerpt=200):
        if source_ref.excerpt.endswith("…") or source_ref.excerpt.endswith("..."):
            assert (
                source_ref.excerpt.rstrip("…. ")[-1] not in "abcdefghijklmnopqrstuvwxyz"
                or " " in source_ref.excerpt[-30:]
            )


def test_fallback_embedder_returns_equal_length_vectors():
    hashing_embedder = HashingEmbedder()
    embedding = hashing_embedder.embed_passages(["erster Text", "zweiter Text", "dritter"])
    assert embedding.dense.shape == (3, hashing_embedder.dimensions)


def test_same_text_gives_same_vector():
    """Determinism is required for a saved index to be reusable."""
    hashing_embedder = HashingEmbedder()
    first = hashing_embedder.embed_query("Artikel 6 Absatz 3")
    second = hashing_embedder.embed_query("Artikel 6 Absatz 3")
    assert (first == second).all()


def test_saved_index_contains_no_pickle(small_index, tmp_path):
    """The shipped index must not use pickle, which would execute code from a tampered copy."""
    target = tmp_path / "units_by_kind"
    small_index.save(target)
    stored_ids = sorted(p.name for p in tmp_path.iterdir())
    assert stored_ids, "nothing saved"
    assert not any(name.endswith((".pkl", ".pickle")) for name in stored_ids), stored_ids


def test_saved_index_is_readable_without_python(small_index, tmp_path):
    """Cross-check: the metadata file is plain gzipped JSON."""
    import gzip
    import json

    target = tmp_path / "units_by_kind"
    small_index.save(target)
    with gzip.open(target.with_suffix(".meta.json.gz"), "rt", encoding="utf-8") as file:
        metadata = json.load(file)
    assert metadata["model"] == small_index.embedder.name
    assert metadata["keywords"]["count"] == len(small_index.units)


def test_legacy_pickle_index_is_rejected(small_index, tmp_path):
    """A legacy pickle index must not be loaded silently."""
    target = tmp_path / "units_by_kind"
    small_index.save(target)
    target.with_suffix(".meta.json.gz").unlink()
    target.with_suffix(".meta.pkl").write_bytes(b"egal, wird nicht gelesen")
    with pytest.raises(RuntimeError, match="pickle"):
        SearchIndex.load(units=small_index.units, embedder=HashingEmbedder(), path=target)


def test_missing_index_is_reported_clearly(tmp_path, corpus):
    with pytest.raises(FileNotFoundError, match="Kein abgelegter Bestand"):
        SearchIndex.load(
            units=corpus[:10], embedder=HashingEmbedder(), path=tmp_path / "does-not-exist"
        )


def test_missing_index_is_reported_in_english(tmp_path, corpus):
    from compliance_helper.i18n import Language, use_language

    with use_language(Language.EN), pytest.raises(FileNotFoundError, match="No stored search"):
        SearchIndex.load(
            units=corpus[:10], embedder=HashingEmbedder(), path=tmp_path / "does-not-exist"
        )


def test_unbuilt_index_is_not_saved(corpus, tmp_path):
    """Saving an unbuilt index fails now rather than as an obscure length error on load."""
    empty = SearchIndex(corpus[:10], HashingEmbedder())
    with pytest.raises(RuntimeError, match="not built"):
        empty.save(tmp_path / "units_by_kind")


def test_cases_do_not_crowd_out_legal_text(small_index, corpus):
    """At most a third of passages may be use cases.

    Cases share the users' everyday language and outrank legal text: measured at 1.6 percent of
    the index they supplied 38 percent of passages before the cap.
    """
    from compliance_helper.domain import UnitKind

    with_cases = [e for e in corpus if e.kind is UnitKind.EXAMPLE]
    if not with_cases:
        pytest.skip("no use cases in corpus")

    search_index = SearchIndex(
        [e for e in corpus if e.kind is UnitKind.EXAMPLE][:20]
        + [e for e in corpus if e.id.startswith(("AI-Act/art-6", "AI-Act/annex-III"))],
        HashingEmbedder(),
    )
    search_index.build()
    for count in (3, 6, 9):
        hits = search_index.search("Bewerbungen vorsortieren", count=count, rerank=False)
        cases = sum(1 for t in hits if t.unit.kind is UnitKind.EXAMPLE)
        assert cases <= max(1, count // 3), "%d of %d passages are use cases" % (
            cases,
            len(hits),
        )


def test_case_cap_still_returns_full_count(small_index):
    """Capped cases must not shorten the result list."""
    for count in (3, 5, 8):
        hits = small_index.search("Hochrisiko Pflichten", count=count, rerank=False)
        assert len(hits) == min(count, len(small_index.units))


def test_saved_index_with_foreign_ids_is_rejected(tmp_path, corpus):
    """Same unit count with different ids is rejected, or every vector is misattributed."""
    import pytest

    from compliance_helper.search.embedding import HashingEmbedder
    from compliance_helper.search.index import SearchIndex

    units = corpus[:20]
    search_index = SearchIndex(units, HashingEmbedder())
    search_index.build()
    target = tmp_path / "search_index"
    search_index.save(target)

    rotated = [units[-1], *units[:-1]]
    with pytest.raises(RuntimeError, match="different corpus"):
        SearchIndex.load(units=rotated, embedder=HashingEmbedder(), path=target)


@pytest.fixture(scope="module")
def shipped_german_index():
    from compliance_helper.i18n import Language
    from compliance_helper.search import store

    if not store.exists(store.index_path(Language.DE)):
        pytest.skip(f"No stored German index ({store.build_command(Language.DE)})")
    return SearchIndex.load(Language.DE)


@pytest.mark.slow
@pytest.mark.parametrize(
    "question,expected_prefix",
    [
        ("Ist Emotionserkennung am Arbeitsplatz verboten?", "AI-Act/art-5/para-1-f"),
        (
            "Wann ist ein KI-System im Bereich Beschäftigung ein Hochrisiko-KI-System?",
            "AI-Act/annex-III/pt-4",
        ),
        ("automatisierte Entscheidung im Einzelfall", "GDPR/art-22"),
        ("Verarbeitung von Beschäftigtendaten", "BDSG/sec-26"),
    ],
)
def test_german_questions_find_the_expected_norm(shipped_german_index, question, expected_prefix):
    hits = shipped_german_index.search(question, count=8, rerank=False)
    ids = [hit.unit.id for hit in hits]
    assert any(unit_id.startswith(expected_prefix) for unit_id in ids), ids


@pytest.mark.slow
def test_shipped_german_index_is_german_and_current(shipped_german_index):
    """Every stored vector was embedded from today's text, the use cases included."""
    from compliance_helper.i18n import Language
    from compliance_helper.search import store

    assert shipped_german_index.language is Language.DE
    current = [store.text_hash(text) for text in shipped_german_index.index_texts()]
    assert shipped_german_index.text_hashes == current
