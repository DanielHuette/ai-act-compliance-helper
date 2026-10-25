"""Classification, citations and question flow with English as the active language.

Context: English users must get English legal terms and citation style from the same rules, while
German output stays unchanged. | Input: the rule set, the question flow, hand-built bilingual rule
data | Output: pass when every text produced by code reads in English with no German leftovers.
"""

from __future__ import annotations

import re

import pytest

from compliance_helper.classification.assessor import (
    Assessor,
    RuleSet,
    description_from_text,
    roles_from_text,
)
from compliance_helper.classification.purposes import PurposeMatcher
from compliance_helper.classification.question_flow import (
    Provision,
    Question,
    Walkthrough,
)
from compliance_helper.domain import (
    LegalAct,
    RiskClass,
    Role,
    SystemDescription,
    Unit,
    UnitKind,
)
from compliance_helper.i18n import Language, use_language

GERMAN_LEFTOVER = re.compile(
    r"[äöüßÄÖÜ]|\b(?:der|die|das|und|oder|nicht|ist|Artikel|Absatz|Anhang|Nummer|Buchstabe)\b"
)

CV_SCREENING = (
    "Wir setzen ein Sprachmodell ein, um eingehende Bewerbungen "
    "vorzusortieren und eine Rangfolge der Kandidaten zu erstellen."
)


def _unit(unit_id: str, act: LegalAct, kind: UnitKind, number: str, paragraph: str | None) -> Unit:
    return Unit(id=unit_id, legal_act=act, kind=kind, number=number, paragraph=paragraph, text="x")


@pytest.fixture
def english():
    with use_language(Language.EN) as language:
        yield language


@pytest.fixture
def quiet_assessor() -> Assessor:
    return Assessor(purpose_matcher=PurposeMatcher(lines=[]))


@pytest.mark.parametrize(
    ("unit", "german", "english"),
    [
        (
            _unit("AI-Act/art-6/para-1-a", LegalAct.AI_ACT, UnitKind.ARTICLE, "6", "1 Buchstabe a"),
            "Artikel 6 Absatz 1 Buchstabe a KI-VO",
            "Article 6(1)(a) AI Act",
        ),
        (
            _unit("AI-Act/art-3/pt-39", LegalAct.AI_ACT, UnitKind.ARTICLE, "3", "Nummer 39"),
            "Artikel 3 Nummer 39 KI-VO",
            "Article 3(39) AI Act",
        ),
        (
            _unit(
                "AI-Act/art-43/para-1-sub2-a",
                LegalAct.AI_ACT,
                UnitKind.ARTICLE,
                "43",
                "1 Buchstabe ua2-a",
            ),
            "Artikel 43 Absatz 1 Unterabsatz 2 Buchstabe a KI-VO",
            "Article 43(1), subparagraph 2, point (a) AI Act",
        ),
        (
            _unit("AI-Act/annex-III/pt-4-a", LegalAct.AI_ACT, UnitKind.ANNEX, "III", "4-a"),
            "Anhang III Nummer 4 Buchstabe a KI-VO",
            "Annex III point 4(a) AI Act",
        ),
        (
            _unit("AI-Act/annex-I/pt-A-1", LegalAct.AI_ACT, UnitKind.ANNEX, "I", "A-1"),
            "Anhang I Abschnitt A Nummer 1 KI-VO",
            "Annex I Section A point 1 AI Act",
        ),
        (
            _unit("AI-Act/annex-XIII/pt-b", LegalAct.AI_ACT, UnitKind.ANNEX, "XIII", "b"),
            "Anhang XIII Buchstabe b KI-VO",
            "Annex XIII point (b) AI Act",
        ),
        (
            _unit("AI-Act/recital-53", LegalAct.AI_ACT, UnitKind.RECITAL, "53", None),
            "Erwägungsgrund 53 der KI-VO",
            "Recital 53 AI Act",
        ),
        (
            _unit("GDPR/art-6/para-1-a", LegalAct.GDPR, UnitKind.ARTICLE, "6", "1 Buchstabe a"),
            "Artikel 6 Absatz 1 Buchstabe a DSGVO",
            "Article 6(1)(a) GDPR",
        ),
        (
            _unit("BDSG/sec-26/para-1", LegalAct.BDSG, UnitKind.SECTION, "26", "1"),
            "§ 26 Absatz 1 BDSG",
            "Section 26(1) BDSG",
        ),
    ],
    ids=lambda value: value.id if isinstance(value, Unit) else None,
)
def test_citations_follow_the_style_of_each_language(unit, german, english):
    assert unit.citation == german
    with use_language(Language.EN):
        assert unit.citation == english


def test_legal_act_labels_and_names_are_english(english):
    assert [act.label for act in LegalAct] == ["AI Act", "GDPR", "BDSG", "Guidelines"]
    assert "2024/1689" in LegalAct.AI_ACT.full_name
    assert "General Data Protection Regulation" in LegalAct.GDPR.full_name
    assert "Federal Data Protection Act" in LegalAct.BDSG.full_name


def test_role_definitions_and_risk_class_explanations_are_english(english):
    texts = [role.definition for role in Role] + [risk.explanation for risk in RiskClass]
    leftovers = [text for text in texts if GERMAN_LEFTOVER.search(text)]
    assert not leftovers, leftovers
    assert "derogation under Article 6(3)" in RiskClass.HIGH_RISK_EXEMPTION.explanation
    assert "general-purpose AI model" in RiskClass.GPAI.explanation


def test_open_questions_are_english(english, quiet_assessor):
    classification = quiet_assessor.check(description_from_text(CV_SCREENING))
    assert RiskClass.HIGH_RISK_ANNEX_III in classification.risk_classes
    assert classification.open_questions
    assert any(
        q.startswith("Does a person review the result") for q in classification.open_questions
    )
    assert (
        quiet_assessor.check(SystemDescription())
        .open_questions[0]
        .startswith("Are you a provider or a deployer?")
    )
    leftovers = [q for q in classification.open_questions if GERMAN_LEFTOVER.search(q)]
    assert not leftovers, leftovers


def test_annex_iii_rationale_frame_is_english(english, quiet_assessor):
    classification = quiet_assessor.check(description_from_text(CV_SCREENING))
    rationale = next(
        h.rationale for h in classification.indicators if h.rule == "annex3-4-employment"
    )
    assert rationale.startswith("The described use falls within the area")
    assert "fällt in den Bereich" not in rationale


def test_model_provider_rationale_is_english(english, quiet_assessor):
    description = SystemDescription(
        roles=(Role.PROVIDER,), is_gpai_model=True, training_compute_flop=2e25
    )
    indicators = {h.risk_class: h.rationale for h in quiet_assessor.check(description).indicators}
    assert indicators[RiskClass.GPAI].startswith("You provide a general-purpose AI model")
    assert indicators[RiskClass.GPAI_SYSTEMIC_RISK].startswith(
        "The stated training compute of 2.0e+25 floating-point operations"
    )


def test_bilingual_rule_data_is_read_in_the_active_language():
    rules = RuleSet(
        risk_classes_rules={
            "minimal": {
                "id": "minimal-risk",
                "rationale": {"de": "Kein besonderes Risiko.", "en": "No particular risk."},
                "legal_basis": ["AI-Act/art-4"],
            },
            "deadlines": {"caveat": {"de": "Fristen können sich ändern.", "en": "May change."}},
        },
        obligations=[
            {
                "id": "ai-literacy",
                "title": {"de": "KI-Kompetenz", "en": "AI literacy"},
                "action_required": {"de": "Schulen Sie Ihr Personal.", "en": "Train your staff."},
                "legal_basis": ["AI-Act/art-4"],
                "citation_text": {"de": "Artikel 4 KI-VO", "en": "Article 4 AI Act"},
                "roles": ["provider", "deployer"],
                "risk_classes": ["minimal"],
            }
        ],
    )
    assessor = Assessor(rules=rules, purpose_matcher=PurposeMatcher(lines=[]))
    description = SystemDescription(
        free_text="Ein Werkzeug schlägt Rezepte vor.",
        roles=(Role.DEPLOYER,),
        processes_personal_data=False,
    )
    with use_language(Language.EN):
        classification = assessor.check(description)
        assert rules.deadline_caveat == "May change."
    obligation = classification.obligations[0]
    assert (obligation.title, obligation.action_required, obligation.citation_text) == (
        "AI literacy",
        "Train your staff.",
        "Article 4 AI Act",
    )
    assert classification.indicators[0].rationale == "No particular risk."
    assert assessor.check(description).obligations[0].title == "KI-Kompetenz"


def test_caveat_for_an_unstated_trait_is_english(english, quiet_assessor):
    include, caveat = quiet_assessor._trait_filter(
        {"only_when": ["biometrics", "law_enforcement_purpose"]}, SystemDescription(), {}
    )
    assert include
    assert caveat.startswith("This obligation applies only if your system has the trait")
    assert "biometrics or law enforcement purpose" in caveat


def test_question_wording_is_read_when_accessed_and_matched_in_german():
    question = Question(
        id="q",
        wording={"de": "Erkennt das System Gesichter?", "en": "Does the system recognise faces?"},
        source_ref="(1)",
        stage="provision",
        heading={"de": "Biometrie", "en": "Biometrics"},
    )
    provision = Provision(
        citation="AI-Act/annex-III/pt-1-a",
        area="AI-Act/annex-III/pt-1",
        heading={"de": "Biometrie", "en": "Biometrics"},
        main_question=question,
        follow_up_questions=(),
        covered_entries=(
            {"text": {"de": "Auch Stimmen.", "en": "Voices too."}, "source_ref": "(2)"},
        ),
        not_covered_entries=(),
        example_entries=(),
    )
    assert question.text == "Erkennt das System Gesichter?"
    with use_language(Language.EN):
        assert question.text == "Does the system recognise faces?"
        assert question.title == provision.title == "Biometrics"
        assert provision.covered == ({"text": "Voices too.", "source_ref": "(2)"},)
        assert question.german_text == "Erkennt das System Gesichter?"


def test_annex_i_closing_text_is_english(english):
    walkthrough = Walkthrough.load()
    answers = {
        "is-ai-system": True,
        "natural-persons": False,
        "on-behalf-of-authority": False,
        "annex-i:product-under-annex-i": True,
        "annex-i-category:machinery": True,
        "annex-i:ai-system-is-product": True,
        "annex-i:third-party-assessment-required": True,
    }
    given: dict[str, object] = {}
    while group := walkthrough.next_group(given):
        for question in group:
            given[question.id] = answers.get(question.id, False)
    finding = walkthrough.result(given)
    assert finding.risk_class == "high_risk_annex_i"
    assert finding.closing_text.startswith("High risk by way of product safety legislation: ")
    assert finding.closing_text.endswith(
        "The filter in Article 6(3) does not apply here — it concerns Annex III only."
    )


def _classify(assessor: Assessor, text: str, language: Language):
    with use_language(language):
        return assessor.check(description_from_text(text))


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("We do not use emotion recognition; the chatbot answers customer questions.", Language.EN),
        ("We don't score creditworthiness; the tool only formats PDFs.", Language.EN),
        ("Die Software bewertet nicht die Kreditwürdigkeit, sie formatiert nur PDFs.", Language.DE),
        ("Emotionserkennung nutzen wir nicht, der Bot beantwortet Kundenfragen.", Language.DE),
    ],
)
def test_negated_area_keyword_does_not_establish_the_area(quiet_assessor, text, language):
    """A keyword the description denies is no evidence for an Annex III area."""
    classification = _classify(quiet_assessor, text, language)
    assert RiskClass.HIGH_RISK_ANNEX_III not in classification.risk_classes, [
        i.rationale for i in classification.indicators
    ]


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("We don't only rank job applicants, we also onboard them.", Language.EN),
        ("Wir sichten nicht nur Bewerbungen, wir führen auch Gespräche.", Language.DE),
    ],
)
def test_not_only_keeps_the_area(quiet_assessor, text, language):
    """ "Not only X" affirms X."""
    classification = _classify(quiet_assessor, text, language)
    assert RiskClass.HIGH_RISK_ANNEX_III in classification.risk_classes


@pytest.mark.parametrize(
    "text",
    ["We rank applicants.", "Our software ranks applicants for open positions."],
)
def test_ranking_applicants_is_employment_in_english_as_in_german(quiet_assessor, text):
    """ "Wir ranken Bewerber." is point 4; the English sentence must not fall to minimal risk."""
    assert _classify(quiet_assessor, "Wir ranken Bewerber.", Language.DE).risk_classes == (
        RiskClass.HIGH_RISK_ANNEX_III,
    )
    classification = _classify(quiet_assessor, text, Language.EN)
    assert [i.rule for i in classification.indicators] == ["annex3-4-employment"]


def test_keywords_are_shown_as_written_in_the_description(quiet_assessor):
    """The user sees their own word, not a lower-case stem of the rule file."""
    classification = _classify(
        quiet_assessor, "Wir sortieren Bewerbungen mit zugekaufter Software vor.", Language.DE
    )
    (indicator,) = [i for i in classification.indicators if i.rule == "annex3-4-employment"]
    assert "Stichworte: Bewerbungen)" in indicator.rationale, indicator.rationale


@pytest.mark.parametrize(
    ("german", "english"),
    [
        (
            "Wir haben eine Software gekauft, die Bewerbungen vorsortiert.",
            "We bought software that pre-sorts job applications.",
        ),
        (
            "Wir setzen in der Personalabteilung ein KI-Tool ein, das Bewerbungen vorsortiert.",
            "Our HR department uses an AI tool that pre-sorts job applications.",
        ),
        (
            "Wir lassen eine KI die Schichtpläne schreiben.",
            "We have an AI write our shift schedules.",
        ),
        (
            "Wir verkaufen ein Tool, das Videointerviews von Bewerbern auswertet.",
            "We sell a tool that analyses video interviews with applicants.",
        ),
        (
            "Wir haben ein Tool gebaut, das aus Rechnungen die Beträge ausliest.",
            "We built a tool that extracts the amounts from invoices.",
        ),
    ],
)
def test_role_is_read_alike_in_german_and_english(german, english):
    """The same system description must yield the same role in both languages."""
    assert roles_from_text(german) == roles_from_text(english) != ()
