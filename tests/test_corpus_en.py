"""The English corpus cites exactly the units of the German one, in English wording.

Context: both languages share one citation id scheme, so every English unit must have the id,
kind, number and position of its German counterpart, and its text must be the English legal text
without page chrome. | Input: data/processed/corpus.jsonl and corpus.en.jsonl, small HTML samples |
Output: pass when ids, counts, positions and key wordings match.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from compliance_helper.corpus import build
from compliance_helper.corpus.eurlex import Selection, parse
from compliance_helper.corpus.german_sources import BDSG_TRANSLATOR, parse_bdsg_translation
from compliance_helper.domain import LegalAct, Unit, UnitKind
from compliance_helper.i18n import Language


@pytest.fixture(scope="module")
def english_corpus() -> list[Unit]:
    if not build.corpus_file(Language.EN).exists():
        pytest.skip("No English corpus (run compliance-helper build-corpus --language en)")
    return build.load(Language.EN)


@pytest.fixture(scope="module")
def english_by_id(english_corpus) -> dict[str, Unit]:
    return {unit.id: unit for unit in english_corpus}


def test_english_ids_equal_german_ids(corpus, english_corpus):
    german, english = {u.id for u in corpus}, {u.id for u in english_corpus}
    assert not german - english, sorted(german - english)[:15]
    assert not english - german, sorted(english - german)[:15]
    assert len(english) == len(english_corpus)


def test_counts_per_act_and_kind_equal_german(corpus, english_corpus):
    def counts(units: list[Unit]) -> Counter:
        return Counter((u.legal_act, u.kind, u.paragraph is None) for u in units)

    assert counts(english_corpus) == counts(corpus)


def test_number_and_position_equal_german(corpus, english_by_id):
    """``paragraph`` is a structured position ("2 Buchstabe a"), rendered per language later."""
    differing = [
        (u.id, (u.kind, u.number, u.paragraph), english_by_id[u.id].kind)
        for u in corpus
        if (u.kind, u.number, u.paragraph)
        != (english_by_id[u.id].kind, english_by_id[u.id].number, english_by_id[u.id].paragraph)
    ]
    assert not differing, differing[:10]


def test_no_text_is_empty_or_tiny(english_corpus):
    sparse = [(u.id, len(u.text)) for u in english_corpus if len(u.text.strip()) < 25]
    assert not sparse, sparse[:15]


def test_no_page_chrome_or_german_in_english_text(english_corpus):
    markers = (
        "table of contents",
        "Suitable Recitals",
        "Cookie settings",
        "Report error",
        "Copy link",
        "Version information",
        "Erwägungsgrund",
        "Absatz",
        "Anwendungsfall:",
    )
    leaks = [(u.id, m) for u in english_corpus for m in markers if m in u.text or m in u.title]
    assert not leaks, leaks[:10]


def test_recitals_are_titled_in_english(english_corpus):
    titles = {u.title for u in english_corpus if u.kind is UnitKind.RECITAL}
    assert "Recital 1" in titles
    assert not [t for t in titles if not t.startswith("Recital ")]


@pytest.mark.parametrize(
    ("unit_id", "wording"),
    [
        ("AI-Act/art-6/para-3", "shall not be considered to be high-risk"),
        ("AI-Act/art-5/para-1-f", "infer emotions of a natural person in the areas of workplace"),
        ("AI-Act/annex-III/pt-4-a", "recruitment or selection of natural persons"),
        ("AI-Act/art-3/pt-1", "‘AI system’ means a machine-based system"),
        (
            "GDPR/art-22/para-1",
            "decision based solely on automated processing, including profiling",
        ),
        ("GDPR/art-22/para-2-c", "explicit consent"),
        ("BDSG/sec-26/para-1", "processed for employment-related purposes"),
        ("case/application-screening-llm", "Use case: Pre-selection of job applications"),
    ],
)
def test_key_provisions_carry_their_english_wording(english_by_id, unit_id, wording):
    assert wording in english_by_id[unit_id].text


def test_sources_name_the_english_versions(english_by_id):
    assert english_by_id["AI-Act/art-6"].source.startswith("Regulation (EU) 2024/1689, OJ L")
    assert english_by_id["GDPR/art-22"].source.startswith("Regulation (EU) 2016/679, OJ L 119")
    assert BDSG_TRANSLATOR in english_by_id["BDSG/sec-26"].source


def test_english_list_markers_become_letter_and_definition_units():
    html = """
    <div id="art_3"><p class="oj-ti-art">Article 3</p><p class="oj-sti-art">Definitions</p>
      <table><tr><td><p>(1)</p></td><td><p>‘AI system’ means a machine-based system that
      infers from its input how to generate outputs;</p></td></tr></table></div>
    <div id="art_5"><p class="oj-ti-art">Article 5</p><p class="oj-sti-art">Prohibited</p>
      <div id="005.001"><p>1. The following AI practices shall be prohibited:</p>
        <table><tr><td><p>(a)</p></td><td><p>the placing on the market of an AI system that
        deploys subliminal techniques;</p></td></tr></table></div></div>
    """
    parsed = parse(html, LegalAct.AI_ACT, language=Language.EN)
    by_id = {unit.id: unit for unit in parsed.units}
    assert by_id["AI-Act/art-3/pt-1"].text.startswith("‘AI system’ means")
    assert by_id["AI-Act/art-5/para-1-a"].paragraph == "1 Buchstabe a"
    assert by_id["AI-Act/art-5/para-1-a"].text.startswith("the placing on the market")


def test_reference_ids_decide_instead_of_text_length():
    short = "(b) the free movement;"
    assert not Selection().keeps("AI-Act/art-1/para-2-b", short, 40)
    assert Selection(frozenset({"AI-Act/art-1/para-2-b"})).keeps("AI-Act/art-1/para-2-b", short, 40)
    assert not Selection(frozenset()).keeps("AI-Act/art-1/para-2-b", "x" * 500, 40)


def test_bdsg_translation_page_is_split_into_sections_and_paragraphs(tmp_path: Path):
    page = tmp_path / "bdsg.html"
    page.write_text(
        "<html><body><p>Version information: The English translation includes the amendments "
        "by Article 10 of the Act of 23 June 2021 (Federal Law Gazette I, p. 1858).</p>"
        '<p style="text-align: left; font-weight: normal"><a href="#">table of contents</a></p>'
        '<p style="text-align: center; font-weight: bold">Section 26<br/>Data processing for '
        "employment-related purposes</p>"
        "<p>(1) Personal data of employees may be processed for employment-related purposes "
        "where necessary for</p>"
        '<p class="Liste1">1. hiring decisions or</p>'
        "<p>(2) Consent shall be given in written or electronic form.</p>"
        '<p style="text-align: center; font-weight: bold">Section 27<br/>Research</p>'
        "<p>By derogation from Article 9 (1), processing for research purposes is permitted.</p>"
        "</body></html>",
        encoding="iso-8859-1",
    )
    units = {unit.id: unit for unit in parse_bdsg_translation(page)}

    assert set(units) == {"BDSG/sec-26", "BDSG/sec-26/para-1", "BDSG/sec-26/para-2", "BDSG/sec-27"}
    assert units["BDSG/sec-26"].title == "Data processing for employment-related purposes"
    assert units["BDSG/sec-26/para-1"].text.endswith("necessary for 1. hiring decisions or")
    assert "23 June 2021" in units["BDSG/sec-27"].source
    assert units["BDSG/sec-27"].as_of == date.fromtimestamp(page.stat().st_mtime)


def test_case_units_are_built_in_english(tmp_path, monkeypatch):
    (tmp_path / "cases.yaml").write_text(
        "cases:\n"
        "  - id: bilingual-example\n"
        "    title: {de: Bewerbervorauswahl, en: Applicant pre-selection}\n"
        "    scenario: {de: Ein System sortiert Bewerbungen., en: A system sorts applications.}\n"
        "    roles: [deployer, provider]\n"
        "    classification: high_risk_annex_iii\n"
        "    obligations:\n"
        "      - {de: Risikomanagement einrichten, en: Set up risk management}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build.paths, "root", lambda: tmp_path)
    [unit] = build.from_cases(tmp_path, Language.EN)
    assert unit.title == "Applicant pre-selection"
    assert "Scenario: A system sorts applications." in unit.text
    assert "Role: Deployer and Provider" in unit.text
    assert "To do: Set up risk management" in unit.text
    assert "Classification: High risk (Annex III)" in unit.text
    assert "high_risk" not in unit.text
    assert "Bewerb" not in unit.text


def test_translation_file_names_keep_german_names_unchanged():
    assert build.corpus_file(Language.DE).name == "corpus.jsonl"
    assert build.corpus_file(Language.EN).name == "corpus.en.jsonl"
    assert build.report_file(Language.EN).name == "corpus_report.en.json"
    assert build.raw_dir(Language.EN) == build.raw_dir(Language.DE) / "en"
