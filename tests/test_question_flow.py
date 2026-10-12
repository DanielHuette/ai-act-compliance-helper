"""Question flow: sources, counted figures and complete walkthrough paths.

Context: the question flow decides the classification; every legal question must cite the
Commission's draft guidelines of 19 May 2026 and known wrong paths must stay fixed. | Input:
data/rules/question_flow/*.yaml, question_flow_layout.yaml, figures.json | Output: pass when
sources, counts and findings match.
"""

from __future__ import annotations

import dataclasses
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from compliance_helper import paths
from compliance_helper.classification.question_flow import (
    CONDITIONAL,
    CONTINUE,
    COVERED,
    NOT_APPLICABLE,
    NOT_COVERED,
    Provision,
    Question,
    RuleLayoutError,
    Walkthrough,
)
from compliance_helper.i18n import Language, use_language

#: Answers for a CV-screening and ranking tool. ``...:0:4`` (platform workers) and ``...:1:19``
#: (tender offers) must be NOT_APPLICABLE because a "no" there would exclude the case.
CV_SCREENING_ANSWERS: dict[str, object] = {
    "is-ai-system": True,
    "natural-persons": True,
    "on-behalf-of-authority": False,
    "area:AI-Act/annex-III/pt-4": True,
    "main:pt-4-employment:0": True,
    "main:pt-4-employment:1": True,
    "main:pt-4-employment:2": False,
    "follow-up:pt-4-employment:0:0": True,
    "follow-up:pt-4-employment:0:1": False,
    "follow-up:pt-4-employment:0:2": False,
    "follow-up:pt-4-employment:0:3": False,
    "follow-up:pt-4-employment:0:4": NOT_APPLICABLE,
    "follow-up:pt-4-employment:0:5": True,
    "follow-up:pt-4-employment:0:6": False,
    "follow-up:pt-4-employment:1:1": True,
    "follow-up:pt-4-employment:1:3": True,
    "follow-up:pt-4-employment:1:14": NOT_APPLICABLE,
    "follow-up:pt-4-employment:1:19": NOT_APPLICABLE,
}

#: Job-ad question (guidelines paragraph 251) where a forced "no" dropped a covered case.
JOB_AD_QUESTION_ID = "follow-up:pt-4-employment:1:14"

#: Tender-offer question (guidelines paragraph 250, footnote 44), same trap.
TENDER_QUESTION_ID = "follow-up:pt-4-employment:1:19"

#: A product under Annex I that meets every condition of Article 6(1).
ANNEX_I_PRODUCT: dict[str, object] = {
    "is-ai-system": True,
    "natural-persons": False,
    "on-behalf-of-authority": False,
    "annex-i:product-under-annex-i": True,
    "annex-i-category:medical-devices": True,
    "annex-i:part-of-regulated-product": True,
    "annex-i:safety-function": True,
    "annex-i:third-party-assessment-required": True,
}


@pytest.fixture(scope="module")
def walkthrough() -> Walkthrough:
    return Walkthrough.load()


@pytest.fixture(scope="module")
def figures(root) -> dict:
    return json.loads((root / "data" / "evaluation" / "figures.json").read_text(encoding="utf-8"))


def all_questions(d: Walkthrough) -> list[Question]:
    """Every question the walkthrough can ask."""
    questions: list[Question] = [
        *d.preliminary_questions,
        *d.notes,
        *d.filter_questions,
        *d.area_questions,
    ]
    questions += list(d.annex_i_categories) + list(d.annex_i_questions.values())
    if d.annex_i_gate is not None:
        questions.append(d.annex_i_gate)
    if d.profiling_question is not None:
        questions.append(d.profiling_question)
    for provision in d.provisions:
        questions.append(provision.main_question)
        questions += list(provision.follow_up_questions)
    return questions


def drive(d: Walkthrough, answers: dict[str, object]) -> tuple[dict[str, object], int]:
    """Run the walkthrough from the start, answering from ``answers`` and "no" otherwise.

    Returns:
        The given answers and the number of steps (one step is one page, not one question).
    """
    given: dict[str, object] = {}
    steps = 0
    while True:
        group = d.next_group(given)
        if not group:
            return given, steps
        steps += 1
        assert steps <= 40, "walkthrough does not terminate"
        for question in group:
            given[question.id] = answers.get(question.id, False)


def test_questions_name_their_source(walkthrough) -> None:
    """Without a source the origin of a question cannot be verified."""
    assert walkthrough.sources, "walkthrough names no source"
    for source in walkthrough.sources:
        assert "19.05.2026" in source, source


def test_every_legal_question_carries_its_paragraph_number(walkthrough) -> None:
    """Every deciding question cites a guidelines paragraph; area and main questions only sort."""
    sorting_questions = {f.id for f in walkthrough.area_questions}
    sorting_questions |= {p.main_question.id for p in walkthrough.provisions}
    without = [
        f.id
        for f in all_questions(walkthrough)
        if not f.source_ref and f.id not in sorting_questions
    ]
    assert not without, f"questions without source_ref ({len(without):d}): {without[:10]}"


def test_every_exclusion_and_example_carries_its_source_ref(walkthrough) -> None:
    """An exclusion without a source is an unsupported claim about the law."""
    without: list[str] = []
    for provision in walkthrough.provisions:
        for trait in ("covered", "not_covered", "examples"):
            for entry in getattr(provision, trait):
                if not entry.get("source_ref"):
                    without.append(f"{provision.citation}/{trait}: {entry.get('text', '')[:50]}")
    assert not without, "\n".join(without[:10])


def test_source_refs_are_guideline_paragraph_numbers(walkthrough) -> None:
    """A source_ref is a guidelines paragraph number such as ``(245)``."""
    pattern = re.compile(r"\(\d{1,4}\)")
    wrong = [
        (f.id, f.source_ref)
        for f in all_questions(walkthrough)
        if f.source_ref and not pattern.search(f.source_ref)
    ]
    # "(nach 293)" marks an unnumbered list that follows a paragraph in the official text.
    wrong = [p for p in wrong if not re.search(r"\(nach \d{1,4}\)", p[1])]
    assert not wrong, wrong[:8]


def test_every_provision_points_to_a_corpus_unit(walkthrough, ids) -> None:
    """Every provision except area gates must cite a corpus unit."""
    missing = sorted(
        {p.citation for p in walkthrough.provisions if not p.is_area_gate and p.citation not in ids}
    )
    assert not missing, f"citations without corpus text: {missing}"


def test_annex_iii_letters_are_separate_provisions(walkthrough) -> None:
    """Annex III letters are separate provisions, e.g. point 4(a) hiring vs 4(b) work conditions."""
    with_letter = {
        p.citation for p in walkthrough.provisions if re.search(r"/pt-\d+-[a-z]$", p.citation)
    }
    assert "AI-Act/annex-III/pt-4-a" in with_letter
    assert "AI-Act/annex-III/pt-4-b" in with_letter
    assert len(with_letter) >= 20, sorted(with_letter)


def test_no_question_makes_user_count_their_answers(walkthrough) -> None:
    """The walkthrough tracks prior answers itself; asking the user to recount adds errors."""
    self_referential = [
        f.id for f in all_questions(walkthrough) if f.text.lower().startswith("haben sie alle")
    ]
    assert not self_referential, self_referential


def test_no_question_is_empty(walkthrough) -> None:
    empty = [f.id for f in all_questions(walkthrough) if len(f.text.split()) < 3]
    assert not empty, empty[:10]


def test_walkthrough_counts_match_published_figures(walkthrough, figures) -> None:
    """Walkthrough counts must match the published ``figures.json``."""
    counted = walkthrough.figures()
    for trait in ("questions", "provisions", "exclusions", "examples", "preliminary_questions"):
        assert counted[trait] == figures[trait], (
            f"{trait}: {counted[trait]} instead of {figures[trait]}"
        )
    assert len(walkthrough.area_questions) == figures["area_questions"]
    assert len(walkthrough.annex_i_categories) == figures["annex_i_categories"]


def test_every_question_is_answered_exactly_once(walkthrough) -> None:
    """Question ids are unique; Annex III point 2 has four items under one citation."""
    all_items = [f.id for f in all_questions(walkthrough)]
    duplicates = sorted({k for k in all_items if all_items.count(k) > 1})
    assert not duplicates, duplicates


def test_walkthrough_ends_immediately_without_ai_system(walkthrough) -> None:
    """Article 3(1): if it is not an AI system, the regulation does not apply."""
    answers = {walkthrough.preliminary_questions[0].id: False}
    assert walkthrough.next_question(answers) is None
    finding = walkthrough.result(answers)
    assert finding.risk_class == "not_ai_system"
    assert finding.closing_text, "user is not told what this means for them"


def test_area_selection_is_one_step_not_eight(walkthrough) -> None:
    """All eight area questions are asked on a single page."""
    answers: dict[str, object] = {
        "is-ai-system": True,
        "natural-persons": True,
        "on-behalf-of-authority": False,
    }
    if walkthrough.annex_i_gate is not None:
        answers[walkthrough.annex_i_gate.id] = False
    group = walkthrough.next_group(answers)
    assert {f.id for f in group} == {f.id for f in walkthrough.area_questions}


def test_cv_screening_is_high_risk_under_point_4_letter_a(walkthrough) -> None:
    """The most-measured case: CV screening falls under Annex III point 4(a)."""
    answers, steps = drive(walkthrough, CV_SCREENING_ANSWERS)
    finding = walkthrough.result(answers)
    assert finding.risk_class == "high_risk_annex_iii", finding.risk_class
    assert "AI-Act/annex-III/pt-4-a" in finding.citations, finding.citations
    assert steps <= 10, f"{steps} steps; a lawyer would ask five to eight things"


def test_not_applicable_does_not_drop_case_from_classification(walkthrough) -> None:
    """NOT_APPLICABLE keeps a covered case."""
    with_open, _ = drive(walkthrough, CV_SCREENING_ANSWERS)
    assert walkthrough.result(with_open).risk_class == "high_risk_annex_iii"


def test_job_ad_and_tender_questions_do_not_exclude_cv_screening(walkthrough) -> None:
    """A CV ranker places no job ads and judges no tenders; "no" there must not drop point 4(a)."""
    forced = dict(CV_SCREENING_ANSWERS, **{JOB_AD_QUESTION_ID: False, TENDER_QUESTION_ID: False})
    answers, _ = drive(walkthrough, forced)
    finding = walkthrough.result(answers)
    assert finding.risk_class == "high_risk_annex_iii", finding.risk_class
    assert "AI-Act/annex-III/pt-4-a" in finding.citations


def _provision(walkthrough: Walkthrough, citation: str) -> Provision:
    return next(p for p in walkthrough.provisions if p.citation == citation)


def _question(provision: Provision, marker: str) -> Question:
    (found,) = [f for f in provision.follow_up_questions if marker in f.german_text]
    return found


def _provision_answers(
    provision: Provision, yes: tuple[str, ...], no: tuple[str, ...]
) -> dict[str, object]:
    """Main question affirmed; deciding questions open, the rest denied; then ``yes``/``no``."""
    answers: dict[str, object] = {provision.main_question.id: True}
    for f in provision.follow_up_questions:
        answers[f.id] = False if f.on_no == CONTINUE else NOT_APPLICABLE
    answers.update({_question(provision, marker).id: True for marker in yes})
    answers.update({_question(provision, marker).id: False for marker in no})
    return answers


#: (letter, affirmed, denied, expected): a question of one alternative never decides another.
ALTERNATIVES = [
    (
        "AI-Act/annex-III/pt-4-a",
        ("Sichtet Ihr System Lebensläufe",),
        ("konkrete offene Stelle", "Antworten auf Ausschreibungen"),
        COVERED,
    ),
    (
        "AI-Act/annex-III/pt-4-a",
        ("gezielten Platzierung von Stellenanzeigen auf Profilbildung",),
        ("konkrete offene Stelle", "Antworten auf Ausschreibungen"),
        NOT_COVERED,
    ),
    (
        "AI-Act/annex-III/pt-4-a",
        ("Substanz des Einstellungsverfahrens",),
        ("Platziert Ihr System Stellenanzeigen gezielt",),
        NOT_COVERED,
    ),
    (
        "AI-Act/annex-III/pt-4-b",
        ("regelmäßig und planmäßig", "Aufgabenzuweisung ausschließlich auf sachliche"),
        ("Entscheidet Ihr System selbst",),
        COVERED,
    ),
    (
        "AI-Act/annex-III/pt-4-b",
        ("Stützt sich die Aufgabenzuweisung", "Aufgabenzuweisung ausschließlich auf sachliche"),
        (),
        NOT_COVERED,
    ),
    (
        "AI-Act/annex-III/pt-5-b",
        ("Fähigkeit und Bereitschaft", "Bankkontozugang"),
        ("Bildet Ihr System eine Zahl",),
        COVERED,
    ),
    (
        "AI-Act/annex-III/pt-5-b",
        ("Bankkontozugang",),
        ("Fähigkeit und Bereitschaft", "Bildet Ihr System eine Zahl"),
        NOT_COVERED,
    ),
    (
        "AI-Act/annex-III/pt-5-c",
        ("Bewertet Ihr System das Risikoprofil", "Lebensversicherung oder um eine Kranken"),
        ("Legt Ihr System die Beiträge fest",),
        COVERED,
    ),
    (
        "AI-Act/annex-III/pt-5-c",
        ("Lebensversicherung oder um eine Kranken",),
        ("Bewertet Ihr System das Risikoprofil", "Legt Ihr System die Beiträge fest"),
        NOT_COVERED,
    ),
    (
        "AI-Act/annex-III/pt-8-a",
        (
            "Ermitteln und Auslegen",
            "aussergerichtlichen Streitbeilegung genutzt",
            "Rechtswirkungen",
        ),
        ("richterliche Aufgaben aus",),
        COVERED,
    ),
    (
        "AI-Act/annex-III/pt-8-a",
        ("Ermitteln und Auslegen",),
        ("richterliche Aufgaben aus", "aussergerichtlichen Streitbeilegung genutzt"),
        NOT_COVERED,
    ),
]


@pytest.mark.parametrize(("citation", "yes", "no", "expected"), ALTERNATIVES)
def test_alternative_decides_only_itself(walkthrough, citation, yes, no, expected) -> None:
    """Points 4(a), 4(b), 5(b), 5(c) and 8(a) list alternatives, each sufficient on its own."""
    provision = _provision(walkthrough, citation)
    answers = _provision_answers(provision, yes, no)
    assert walkthrough.provision_finding(provision, answers) == expected


def test_alternative_marker_must_name_exactly_one_question(tmp_path: Path) -> None:
    """A layout entry that matches no question must stop loading, not silently widen a letter."""
    rules = tmp_path / "rules"
    shutil.copytree(paths.rules_dir(), rules)
    layout_file = rules / "question_flow_layout.yaml"
    layout = yaml.safe_load(layout_file.read_text(encoding="utf-8"))
    layout["alternatives"][0]["branches"]["tender_offers"] = {"questions": ["no such wording"]}
    layout_file.write_text(yaml.safe_dump(layout, allow_unicode=True), encoding="utf-8")
    with pytest.raises(RuleLayoutError, match="no such wording"):
        Walkthrough.load(rules)


def test_annex_i_category_answered_dont_know_confirms_no_product(walkthrough) -> None:
    """ "Machinery? Don't know" is no regulated product; Annex I stays open, not high risk."""
    answers, _ = drive(
        walkthrough,
        {
            **ANNEX_I_PRODUCT,
            "annex-i-category:medical-devices": False,
            "annex-i-category:machinery": NOT_APPLICABLE,
            "annex-i:part-of-regulated-product": NOT_APPLICABLE,
            "annex-i:third-party-assessment-required": NOT_APPLICABLE,
        },
    )
    finding = walkthrough.result(answers)
    assert finding.risk_class == "not_high_risk", finding.risk_class
    assert "AI-Act/annex-I" in finding.open_provisions


def test_annex_i_condition_answered_dont_know_is_conditional(walkthrough) -> None:
    """A confirmed product whose conditions are only unknown is conditionally high risk."""
    answers, _ = drive(
        walkthrough,
        {
            **ANNEX_I_PRODUCT,
            "annex-i:part-of-regulated-product": NOT_APPLICABLE,
            "annex-i:safety-function": NOT_APPLICABLE,
            "annex-i:third-party-assessment-required": NOT_APPLICABLE,
        },
    )
    assert walkthrough.annex_i_finding(answers) == CONDITIONAL
    finding = walkthrough.result(answers)
    assert finding.risk_class == "high_risk_conditional", finding.risk_class
    assert "offen" in finding.closing_text, finding.closing_text


def test_annex_i_exclusion_answered_dont_know_does_not_exclude(walkthrough) -> None:
    """Only a yes to "comfort or efficiency only" excludes a safety component (paragraph 42)."""
    unknown, _ = drive(
        walkthrough, {**ANNEX_I_PRODUCT, "annex-i:comfort-or-efficiency-only": NOT_APPLICABLE}
    )
    assert walkthrough.result(unknown).risk_class == "high_risk_annex_i"
    affirmed, _ = drive(
        walkthrough, {**ANNEX_I_PRODUCT, "annex-i:comfort-or-efficiency-only": True}
    )
    assert walkthrough.result(affirmed).risk_class != "high_risk_annex_i"


def test_annex_i_closing_text_is_the_same_on_web_and_in_python(walkthrough, root) -> None:
    """Both walkthroughs read the closing text from the rule data, in both languages."""
    answers, _ = drive(walkthrough, ANNEX_I_PRODUCT)
    layout = yaml.safe_load(
        (root / "data" / "rules" / "question_flow_layout.yaml").read_text(encoding="utf-8")
    )
    for language in Language:
        with use_language(language):
            text = walkthrough.result(answers).closing_text
        expected_start = layout["annex_i"]["closing_text"][language.value].split("{product}")[0]
        assert text.startswith(expected_start), text


def test_profiling_is_not_asked_after_an_unknown_filter_condition(walkthrough) -> None:
    """Profiling only matters once a filter condition is affirmed; "don't know" affirms none."""
    unknown = {f.id: NOT_APPLICABLE for f in walkthrough.filter_questions}
    answers, _ = drive(walkthrough, {**CV_SCREENING_ANSWERS, **unknown})
    assert walkthrough.profiling_question.id not in answers


def test_findings_cite_no_empty_paragraph(walkthrough) -> None:
    """An empty reference renders as a stray comma in the list of paragraphs."""
    answers, _ = drive(walkthrough, CV_SCREENING_ANSWERS)
    assert "" not in walkthrough.result(answers).evidence


def test_compound_without_special_case_marker_keeps_its_provisions(walkthrough) -> None:
    """An empty marker excludes nothing; Python used to drop every provision of the area."""
    area = "AI-Act/annex-III/pt-2"
    answers: dict[str, object] = {}
    for provision in walkthrough.provisions:
        if provision.area != area:
            continue
        answers[provision.main_question.id] = True
        for f in provision.follow_up_questions:
            answers[f.id] = f.on_yes != NOT_COVERED
    layout = dict(walkthrough.layout)
    layout["compounds"] = [
        {**compound, "special_case_main_question_contains": ""}
        for compound in walkthrough.layout["compounds"]
    ]
    without_marker = dataclasses.replace(walkthrough, layout=layout)
    assert without_marker.compound_finding(area, answers) == COVERED


def test_unanswered_exclusion_does_not_apply(walkthrough) -> None:
    """Same rule one level down, on the provision finding itself."""
    provision = next(p for p in walkthrough.provisions if p.citation == "AI-Act/annex-III/pt-4-a")
    exclusion = next(f for f in provision.follow_up_questions if f.on_yes == NOT_COVERED)
    carriers = _question(provision, "Sichtet Ihr System Lebensläufe")

    # Baseline: provision affirmed, no exclusion applies; exclude-on-no questions stay open.
    reason: dict[str, object] = {}
    for question in provision.follow_up_questions:
        reason[question.id] = NOT_APPLICABLE if question.on_no == NOT_COVERED else False
    reason[provision.main_question.id] = True
    reason[carriers.id] = True

    reason[exclusion.id] = NOT_APPLICABLE
    assert walkthrough.provision_finding(provision, reason) == COVERED
    reason[exclusion.id] = True
    assert walkthrough.provision_finding(provision, reason) == NOT_COVERED


def test_no_area_means_not_high_risk(walkthrough) -> None:
    """Denying all eight areas means not covered by Annex III."""
    answers, _ = drive(walkthrough, {"is-ai-system": True, "natural-persons": True})
    finding = walkthrough.result(answers)
    assert finding.risk_class == "not_high_risk", finding.risk_class
    assert not finding.matched_provisions


def test_filter_is_asked_only_after_a_covered_provision(walkthrough) -> None:
    """Article 6(3) only exempts what Annex III covers, so the filter needs a covered provision."""
    without_area, _ = drive(walkthrough, {"is-ai-system": True, "natural-persons": True})
    assert not any(k.startswith("filter:") for k in without_area)

    with_area, _ = drive(walkthrough, CV_SCREENING_ANSWERS)
    assert [k for k in with_area if k.startswith("filter:")], "filter was never asked"


def test_exemption_applies_only_without_profiling(walkthrough) -> None:
    """With profiling the system stays high-risk despite a fulfilled filter condition."""
    condition = walkthrough.filter_questions[0].id
    profiling = walkthrough.profiling_question.id

    with_exemption, _ = drive(walkthrough, dict(CV_SCREENING_ANSWERS, **{condition: True}))
    finding = walkthrough.result(with_exemption)
    assert finding.risk_class == "high_risk_exemption", finding.risk_class
    assert finding.filter_applies
    assert finding.filter_reason, "user is not told which condition exempts them"

    with_profiling, _ = drive(
        walkthrough, dict(CV_SCREENING_ANSWERS, **{condition: True, profiling: True})
    )
    assert walkthrough.result(with_profiling).risk_class == "high_risk_annex_iii"


def test_exemption_and_annex_iii_never_coexist(walkthrough) -> None:
    """Both classes at once would contradict each other."""
    condition = walkthrough.filter_questions[0].id
    answers, _ = drive(walkthrough, dict(CV_SCREENING_ANSWERS, **{condition: True}))
    risk_class = walkthrough.result(answers).risk_class
    assert risk_class in {"high_risk_exemption", "high_risk_annex_iii"}
    assert risk_class != "high_risk_annex_iii" or not answers.get(condition)


def test_annex_i_takes_precedence_over_annex_iii(walkthrough) -> None:
    """Article 6(1) precedes 6(2) and the filter does not apply.

    Requires a regulated product, the AI system's role in it and third-party assessment.
    """
    answers, _ = drive(
        walkthrough,
        {
            "is-ai-system": True,
            "natural-persons": False,
            "on-behalf-of-authority": False,
            "annex-i:product-under-annex-i": True,
            "annex-i-category:machinery": True,
            "annex-i:ai-system-is-product": True,
            "annex-i:third-party-assessment-required": True,
        },
    )
    finding = walkthrough.result(answers)
    assert finding.risk_class == "high_risk_annex_i", finding.risk_class
    assert "Anhang III" in finding.closing_text, "closing text must state the filter does not apply"
    assert not any(k.startswith("filter:") for k in answers)


def test_negated_annex_i_condition_ends_the_path(walkthrough) -> None:
    """Missing any one of the three Annex I conditions ends the path."""
    answers, _ = drive(
        walkthrough,
        {
            "is-ai-system": True,
            "natural-persons": False,
            "on-behalf-of-authority": False,
            "annex-i:product-under-annex-i": True,
            "annex-i-category:machinery": True,
            "annex-i:ai-system-is-product": True,
        },
    )
    assert walkthrough.annex_i_finding(answers) == NOT_COVERED
    assert walkthrough.result(answers).risk_class != "high_risk_annex_i"


def test_every_finding_is_a_known_class(walkthrough) -> None:
    """An unknown class would render as an empty result in the UI."""
    known = {
        "not_ai_system",
        "not_high_risk",
        "high_risk_annex_i",
        "high_risk_annex_iii",
        "high_risk_exemption",
        "high_risk_conditional",
    }
    for answers in (
        {},
        {"is-ai-system": False},
        CV_SCREENING_ANSWERS,
        dict(CV_SCREENING_ANSWERS, **{walkthrough.filter_questions[0].id: True}),
    ):
        given, _ = drive(walkthrough, answers)
        assert walkthrough.result(given).risk_class in known


def test_condition_unknowable_to_user_stays_open(walkthrough) -> None:
    """A condition the provider cannot know yields "conditional", not a guess.

    Annex III point 2 requires formal designation as critical infrastructure, which the
    provider need not learn of (guidelines paragraph 191).
    """
    answers, _ = drive(
        walkthrough,
        {
            "is-ai-system": True,
            "natural-persons": False,
            "on-behalf-of-authority": False,
            "main:pt-2-critical-infrastructure:0": True,
            "follow-up:pt-2-critical-infrastructure:0:2": True,
            "main:pt-2-critical-infrastructure:2": True,
            "follow-up:pt-2-critical-infrastructure:2:0": True,
            "main:pt-2-critical-infrastructure:1": NOT_APPLICABLE,
            "follow-up:pt-2-critical-infrastructure:1:0": NOT_APPLICABLE,
            "area:AI-Act/annex-III/pt-2": True,
        },
    )
    assert walkthrough.compound_finding("AI-Act/annex-III/pt-2", answers) == CONDITIONAL
    finding = walkthrough.result(answers)
    assert finding.risk_class == "high_risk_conditional", finding.risk_class
    assert finding.closing_text, "user is not told what it still depends on"
    assert finding.evidence, "caveat has no citation"


def test_export_writes_the_web_copy_by_default_and_it_is_current(root, tmp_path):
    """The browser reads web/question_flow.json; the export writes there unless told otherwise."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "export_question_flow", root / "scripts" / "export_question_flow.py"
    )
    assert spec is not None and spec.loader is not None
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    assert exporter.parse_arguments([]).output == root / "web" / "question_flow.json"
    fresh = tmp_path / "question_flow.json"
    assert exporter.main(["--output", str(fresh)]) == 0
    assert fresh.read_bytes() == (root / "web" / "question_flow.json").read_bytes()
