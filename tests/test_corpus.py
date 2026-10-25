"""Completeness, id format and cleanliness of the processed legal corpus.

Context: every obligation, citation and passage points to a corpus unit, so gaps or duplicates
lead to silent miscitation; expected counts are measured, not estimated. | Input: processed corpus,
strip_boilerplate | Output: pass when counts, ids, citations and texts are valid.
"""

from __future__ import annotations

import re
from collections import Counter

import pytest

from compliance_helper.corpus.german_sources import strip_boilerplate
from compliance_helper.domain import LegalAct, UnitKind, citation_from_id
from compliance_helper.i18n import Language, use_language

#: Measured unit counts of a complete corpus.
EXPECTED_COUNTS = {
    (LegalAct.AI_ACT, UnitKind.ARTICLE): 113,
    (LegalAct.AI_ACT, UnitKind.ANNEX): 13,
    (LegalAct.AI_ACT, UnitKind.RECITAL): 180,
    (LegalAct.GDPR, UnitKind.ARTICLE): 99,
    (LegalAct.GDPR, UnitKind.RECITAL): 173,
}


def _counts_by_kind(corpus) -> Counter:
    """Count top-level units only, not their paragraphs."""
    return Counter((e.legal_act, e.kind) for e in corpus if e.paragraph is None)


@pytest.mark.parametrize(
    "act_and_kind,count",
    sorted(EXPECTED_COUNTS.items(), key=lambda p: (p[0][0].value, p[0][1].value)),
)
def test_corpus_is_complete(corpus, act_and_kind, count):
    """Every count must match, otherwise a missing provision goes unnoticed."""
    counted = _counts_by_kind(corpus)[act_and_kind]
    assert counted == count, (
        f"{act_and_kind[0].value} {act_and_kind[1].value}: {counted:d} instead of {count:d}"
    )


def test_no_duplicate_ids(corpus):
    """An id must denote exactly one unit, or a citation would resolve by load order."""
    duplicates = [k for k, n in Counter(e.id for e in corpus).items() if n > 1]
    assert not duplicates, f"duplicate ids ({len(duplicates):d}): {sorted(duplicates)[:20]}"


def test_ids_follow_agreed_format(corpus):
    """Ids like ``AI-Act/art-6/para-3``, which the rules and the citation route rely on.

    Annex points may carry a section (``AI-Act/annex-I/pt-A-11``) because numbering restarts
    per section; ``para-1-sub2-a`` marks Article 43(1)'s second subparagraph.
    """
    part = r"(?:[0-9]{1,3}|[A-Z]|[a-z]{1,2}|sub[0-9])"
    id_format = re.compile(
        r"^((AI-Act|GDPR|BDSG|Guidelines)/"
        r"(art|annex|recital|sec)-[0-9A-Za-z]+"
        rf"(/(para|pt)-{part}(-{part}){{0,3}})?"
        r"|case/[a-z0-9\-]+)$"
    )
    violations = [e.id for e in corpus if not id_format.match(e.id)]
    assert not violations, f"ids in unexpected format ({len(violations):d}): {violations[:15]}"


def test_no_text_is_empty_or_tiny(corpus):
    """A unit without content would be an empty passage in an answer."""
    sparse = [(e.id, len(e.text)) for e in corpus if len(e.text.strip()) < 25]
    assert not sparse, sparse[:15]


def test_no_page_boilerplate_in_legal_text(corpus):
    """Website boilerplate must not leak into the legal text."""
    leak_marker = (
        "Fehler melden",
        "Passende Erwägungsgründe",
        "Cookies",
        "Diese Website verwendet",
        "Inhaltsverzeichnis",
        "Zum Inhalt springen",
    )
    matched = [(e.id, w) for e in corpus for w in leak_marker if w in e.text]
    assert not matched, matched[:10]


def test_every_unit_names_its_source(corpus):
    """Without a source a statement cannot be verified."""
    without = [e.id for e in corpus if not e.source]
    assert not without, f"units without source ({len(without):d}): {without[:10]}"


def test_paragraphs_belong_to_existing_parent(corpus):
    """A paragraph without its parent article would be a dangling citation."""
    ids = {e.id for e in corpus}
    orphaned = [
        e.id for e in corpus if e.paragraph is not None and e.id.rsplit("/", 1)[0] not in ids
    ]
    assert not orphaned, orphaned[:15]


def test_citation_is_formatted_for_quoting(corpus):
    """Citations must be in a form a lawyer can look up."""
    by_id = {e.id: e for e in corpus}
    samples = {
        "AI-Act/art-6/para-3": "Artikel 6 Absatz 3 KI-VO",
        "AI-Act/annex-III": "Anhang III KI-VO",
        "GDPR/art-9": "Artikel 9 DSGVO",
    }
    for unit_id, expected_value in samples.items():
        unit = by_id.get(unit_id)
        if unit is None:
            pytest.skip(f"sample {unit_id} missing from corpus")
        assert unit.citation == expected_value


def test_recital_is_not_cited_as_article(corpus):
    """A recital must never be cited as an article."""
    for unit in corpus:
        if unit.kind is UnitKind.RECITAL:
            assert unit.citation.startswith("Erwägungsgrund")


def test_annex_points_are_numbered_as_points_not_paragraphs(corpus):
    """Annex points are cited as "Nummer" or "Buchstabe", never as "Absatz"."""
    points = [e for e in corpus if e.kind is UnitKind.ANNEX and e.paragraph]
    if not points:
        pytest.skip("no annex points in corpus")
    for unit in points:
        assert "Nummer" in unit.citation or "Buchstabe" in unit.citation
        assert "Absatz" not in unit.citation


def test_key_provisions_exist_with_content(corpus):
    """Core provisions must exist and contain their key term."""
    by_id = {e.id: e for e in corpus}
    samples = {
        "AI-Act/art-5": "verboten",
        "AI-Act/art-6": "hochrisiko",
        "AI-Act/art-50": "transparenz",
        "AI-Act/annex-III": "",
        "GDPR/art-22": "automatisierten",
        "GDPR/art-35": "folgenabschätzung",
    }
    for unit_id, word in samples.items():
        assert unit_id in by_id, f"missing from corpus: {unit_id}"
        if word:
            assert word in by_id[unit_id].text.lower(), unit_id


def test_boilerplate_is_cut_at_first_match():
    """The cut must happen before the boilerplate, not inside it."""
    text = (
        "(1) Dies ist der Normtext.\n\nPassende Erwägungsgründe\nErwägungsgrund 42\nFehler melden"
    )
    assert strip_boilerplate(text) == "(1) Dies ist der Normtext."


def test_navigation_lines_are_removed():
    """A trailing "← Art. 21 DSGVO" is navigation, not legal text."""
    text = "(1) Der Normtext steht hier.\n← Art. 21 DSGVO\n"
    assert "Art. 21" not in strip_boilerplate(text)


def test_legal_text_without_boilerplate_is_untouched():
    """Text without boilerplate must stay untouched."""
    text = "(1) Die Verarbeitung ist rechtmäßig, wenn eine Bedingung erfüllt ist."
    assert strip_boilerplate(text) == text


@pytest.mark.parametrize(
    ("language", "expected"),
    [("de", "^Korpus fehlt \\(Deutsch\\)"), ("en", "^The corpus is missing \\(English\\)")],
)
def test_missing_corpus_is_reported_in_the_active_language(
    language, expected, tmp_path, monkeypatch
):
    from compliance_helper import paths
    from compliance_helper.corpus import build
    from compliance_helper.i18n import Language, use_language

    monkeypatch.setattr(paths, "processed_dir", lambda: tmp_path)
    with use_language(Language(language)), pytest.raises(FileNotFoundError, match=expected):
        build.load(Language(language))


@pytest.mark.parametrize("language", ["de", "en"])
def test_missing_corpus_names_the_installed_build_command(language, tmp_path, monkeypatch):
    """The hint must run wherever the tool is installed, the container included."""
    from compliance_helper import paths
    from compliance_helper.corpus import build
    from compliance_helper.i18n import Language

    monkeypatch.setattr(paths, "processed_dir", lambda: tmp_path)
    with pytest.raises(FileNotFoundError) as error:
        build.load(Language(language))
    assert f"compliance-helper build-corpus --language {language}" in str(error.value)
    assert str(tmp_path) in str(error.value)


def test_bilingual_case_fields_are_indexed_in_german(tmp_path, monkeypatch):
    """The search index is German, so a case written in both languages contributes German."""
    from compliance_helper.corpus import build

    (tmp_path / "cases.yaml").write_text(
        "cases:\n"
        "  - id: bilingual-example\n"
        "    title: {de: Bewerbervorauswahl, en: Applicant pre-selection}\n"
        "    scenario: {de: Ein System sortiert Bewerbungen., en: A system sorts applications.}\n"
        "    classification: high_risk_annex_iii\n"
        "    obligations:\n"
        "      - {de: Risikomanagement einrichten, en: Set up risk management}\n"
        "      - title: {de: Protokollierung, en: Logging}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build.paths, "root", lambda: tmp_path)
    [unit] = build.from_cases(tmp_path)
    assert unit.title == "Bewerbervorauswahl"
    assert "Ausgangslage: Ein System sortiert Bewerbungen." in unit.text
    assert "Zu tun: Risikomanagement einrichten; Protokollierung" in unit.text
    assert "Einstufung: Hochrisiko (Anhang III)" in unit.text
    assert "high_risk" not in unit.text
    assert "Applicant" not in unit.text


@pytest.mark.parametrize("language", list(Language))
def test_citation_from_id_matches_the_unit_citation(corpus, language):
    """A citation rendered from a bare id reads exactly like the one rendered from the unit."""
    with use_language(language):
        differing = [
            (unit.id, unit.citation, citation_from_id(unit.id))
            for unit in corpus
            if unit.kind not in (UnitKind.EXAMPLE, UnitKind.GUIDELINES)
            and citation_from_id(unit.id) != unit.citation
        ]
    assert not differing, differing[:5]


def test_ids_that_are_not_statutory_citations_stay_unchanged():
    assert citation_from_id("case/application-screening-llm") == "case/application-screening-llm"
    assert citation_from_id("AI-Act/art-6/unknown-tail") == "AI-Act/art-6/unknown-tail"
