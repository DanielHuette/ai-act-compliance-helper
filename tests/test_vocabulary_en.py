"""English matching vocabulary of the risk-class rules against German counterparts.

Context: an English description must reach the same risk indicators and GDPR sections as the
same description in German, and the English words must never change a German result. |
Input: data/rules/ai_act_risk_classes.yaml, German and English system descriptions, German
cases, company questions and official examples | Output: pass when both languages classify alike
and the German corpora classify identically with and without the English vocabulary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from compliance_helper.classification import vocabulary
from compliance_helper.classification.assessor import (
    Assessor,
    RuleSet,
    compute_from_text,
    description_from_text,
    roles_from_text,
    rule_set,
    traits_from_free_text,
)
from compliance_helper.classification.purposes import PurposeMatcher
from compliance_helper.domain import Classification, Role, SystemDescription
from compliance_helper.i18n import Language, pick

ROOT = Path(__file__).resolve().parent.parent
VOCABULARY_KEYS = frozenset(
    {
        "keywords",
        "strong_keywords",
        "exoneration_phrases",
        "carriers",
        "actions",
        "required_wording",
    }
)


def _assessor(risk_rules: dict[str, Any]) -> Assessor:
    rules = rule_set()
    return Assessor(
        RuleSet(
            risk_classes_rules=risk_rules,
            obligations=rules.obligations,
            data_protection=rules.data_protection,
            as_of=rules.as_of,
        ),
        PurposeMatcher(lines=[]),
    )


def _german_only(node: Any) -> Any:
    if isinstance(node, dict):
        if set(node) == {"de", "en"} and isinstance(node["de"], list):
            return {"de": node["de"]}
        return {key: _german_only(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_german_only(value) for value in node]
    return node


def _outcome(classification: Classification) -> tuple[list[str], list[str], list[str]]:
    return (
        sorted(k.value for k in classification.risk_classes),
        sorted(h.rule for h in classification.indicators),
        [section.id for section in classification.data_protection],
    )


def _vocabularies(node: Any, path: str = "") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in VOCABULARY_KEYS:
                found.append((f"{path}/{key}", value))
            else:
                found.extend(_vocabularies(value, f"{path}/{node.get('id', key)}"))
    elif isinstance(node, list):
        for value in node:
            found.extend(_vocabularies(value, path))
    return found


def _german_corpus() -> list[str]:
    texts: list[str] = []
    for file in sorted((ROOT / "data" / "cases").glob("*.yaml")):
        for case in (yaml.safe_load(file.read_text(encoding="utf-8")) or {}).get("cases", []):
            texts.append(str(pick(case["scenario"], Language.DE)))
    questions = yaml.safe_load(
        (ROOT / "data" / "evaluation" / "company_questions.yaml").read_text(encoding="utf-8")
    )
    texts.extend(str(pick(q["question"], Language.DE)) for q in questions["questions"])
    examples = json.loads(
        (ROOT / "data" / "evaluation" / "official_examples.json").read_text(encoding="utf-8")
    )
    texts.extend(str(pick(e["scenario"], Language.DE)) for e in examples)
    return texts


@pytest.fixture(scope="module")
def bilingual() -> Assessor:
    return _assessor(rule_set().risk_classes_rules)


@pytest.mark.parametrize(
    ("german", "english", "expected_rule"),
    [
        (
            "Wir setzen ein Sprachmodell ein, um eingehende Bewerbungen vorzusortieren und "
            "eine Rangfolge der Kandidaten zu erstellen.",
            "We use a language model to pre-screen incoming job applications and rank the "
            "candidates.",
            "annex3-4-employment",
        ),
        (
            "Das System ordnet die Belegschaft im Vertriebsinnendienst nach Kennzahlen in "
            "Gruppen ein.",
            "The system sorts the workforce in inside sales into groups based on KPIs.",
            "annex3-4-employment",
        ),
        (
            "Wir prüfen die Kreditwürdigkeit von Antragstellern und berechnen automatisch "
            "einen Punktwert.",
            "We assess the creditworthiness of applicants and automatically calculate a score.",
            "annex3-5-essential-services",
        ),
        (
            "Wir berechnen per Scoring die Bonität von Kunden und lehnen Kreditanträge "
            "automatisch ab.",
            "We use scoring to compute the credit rating of customers and automatically reject "
            "loan applications.",
            "art6-3-profiling",
        ),
        (
            "Das System bewertet Klausuren an unserer Hochschule und vergibt Noten.",
            "The system marks written exams at our university and assigns grades.",
            "annex3-3-education",
        ),
        (
            "Die Software steuert das Stromnetz unserer Stadtwerke.",
            "The software controls the power grid of our municipal utility.",
            "annex3-2-critical-infrastructure",
        ),
        (
            "Die Kamera erkennt Besucher per Gesichtserkennung am Eingang.",
            "The camera identifies visitors by facial recognition at the entrance.",
            "annex3-1-biometrics",
        ),
        (
            "Das System unterstützt die Polizei bei der Beweiswürdigung im Ermittlungsverfahren.",
            "The system supports the police force in the evaluation of evidence in criminal "
            "investigations.",
            "annex3-6-law-enforcement",
        ),
        (
            "Das System prüft Asylanträge und Anträge auf ein Visum.",
            "The system examines asylum applications and visa applications.",
            "annex3-7-migration",
        ),
        (
            "Das System schlägt Richtern einen Urteilsvorschlag im Gerichtsverfahren vor.",
            "The system suggests a draft judgment to the presiding judge in court proceedings.",
            "annex3-8-justice",
        ),
        (
            "Das System bewertet Bewerbungen, das Ergebnis ist aber unverbindlich.",
            "The system evaluates job applications, but the result is non-binding.",
            "minimal-risk",
        ),
        (
            "Ein Chatbot beantwortet Fragen unserer Kunden zu Bestellungen.",
            "A chatbot answers our customers' questions about orders.",
            "art50-1-interaction",
        ),
    ],
    ids=[
        "cv-screening",
        "staff-kpis",
        "creditworthiness",
        "credit-scoring-profiling",
        "exam-grading",
        "power-grid",
        "facial-recognition",
        "police-evidence",
        "asylum-visa",
        "court-draft-judgment",
        "non-binding-exoneration",
        "chatbot",
    ],
)
def test_english_description_matches_german_counterpart(
    bilingual: Assessor, german: str, english: str, expected_rule: str
) -> None:
    german_outcome = _outcome(bilingual.check(description_from_text(german)))
    english_outcome = _outcome(bilingual.check(description_from_text(english)))
    assert expected_rule in german_outcome[1]
    assert english_outcome == german_outcome


@pytest.mark.parametrize(
    ("german", "english", "traits", "expected_rule"),
    [
        (
            "Die Software ist ein Medizinprodukt zur Auswertung von Röntgenbildern.",
            "The software is a medical device that analyses X-ray images.",
            {"embedded_in_product": True},
            "art6-1-product-safety",
        ),
        (
            "Wir trainieren ein Basismodell und bieten es anderen Unternehmen an.",
            "We train a foundation model and offer it to other companies.",
            {"is_gpai_model": True, "roles": (Role.PROVIDER,)},
            "art51-gpai-model",
        ),
        (
            "Wir trainieren ein Basismodell, das nur zur Forschung dient.",
            "We train a foundation model that is used only for research.",
            {"is_gpai_model": True, "roles": (Role.PROVIDER,)},
            "minimal-risk",
        ),
        (
            "Wir trainieren ein Basismodell, es bleibt im Unternehmen.",
            "We train a foundation model; it stays within the company.",
            {"is_gpai_model": True, "roles": (Role.PROVIDER,)},
            "minimal-risk",
        ),
    ],
    ids=["annex-i-medical-device", "gpai-offered", "gpai-research-only", "gpai-in-house"],
)
def test_declared_trait_routes_match_in_both_languages(
    bilingual: Assessor, german: str, english: str, traits: dict[str, Any], expected_rule: str
) -> None:
    german_rules = _outcome(
        bilingual.check(description_from_text(german).model_copy(update=traits))
    )
    english_rules = _outcome(
        bilingual.check(description_from_text(english).model_copy(update=traits))
    )
    assert expected_rule in german_rules[1]
    assert english_rules[:2] == german_rules[:2]


@pytest.mark.parametrize(
    ("text", "present"),
    [
        ("Das System sagt allein aus dem Profiling vorher, ob eine Person rückfällig wird.", True),
        ("The system predicts solely from profiling whether a person will reoffend.", True),
        ("The system predicts on the basis of profiling whether a person will reoffend.", False),
    ],
)
def test_crime_prediction_requires_explicit_sole_basis_in_either_language(
    text: str, present: bool
) -> None:
    prohibition = next(
        rule
        for rule in rule_set().risk_classes_rules["prohibitions"]
        if rule["id"] == "art5-1d-crime-prediction"
    )
    assert Assessor._required_wording_present(prohibition, SystemDescription(free_text=text)) is (
        present
    )


def test_english_vocabulary_does_not_fire_on_german_text(bilingual: Assessor) -> None:
    german_only = _assessor(_german_only(rule_set().risk_classes_rules))
    changed = [
        text[:100]
        for text in _german_corpus()
        if _outcome(bilingual.check(description_from_text(text)))[1]
        != _outcome(german_only.check(description_from_text(text)))[1]
    ]
    assert not changed, changed


def test_every_matching_vocabulary_has_an_english_side() -> None:
    missing = [
        path
        for path, value in _vocabularies(rule_set().risk_classes_rules)
        if not (isinstance(value, dict) and set(value) == {"de", "en"} and value["en"])
    ]
    assert not missing, missing


@pytest.mark.parametrize(
    ("text", "trait"),
    [
        ("A dashboard camera detects drowsiness of our truck drivers.", "emotion_recognition"),
        ("Our webcam tool measures the stress level of call centre agents.", "emotion_recognition"),
        ("The platform renders AI-generated images for advertising.", "generates_content"),
        ("A virtual assistant talks with customers on our website.", "interacts_with_people"),
        ("The app swaps faces of celebrities into user videos.", "generates_deepfakes"),
        (
            "The software is a safety component built into packaging machines.",
            "embedded_in_product",
        ),
        (
            "We collect profile pictures from social media to train a matcher.",
            "untargeted_facial_image_scraping",
        ),
        ("Cameras at the train station identify people in real time.", "publicly_accessible_space"),
        ("The model decides whether a loan applicant is rejected.", "makes_decisions_about_people"),
    ],
)
def test_english_free_text_suggests_traits(text: str, trait: str) -> None:
    assert traits_from_free_text(description_from_text(text)).get(trait) is True


@pytest.mark.parametrize(
    ("text", "trait"),
    [
        ("We sell personal finance software for households.", "employee_data"),
        ("The system does not generate content for customers.", "generates_content"),
        ("The tool evaluates no people, only invoices.", "makes_decisions_about_people"),
        ("We built a new user interface for the invoice archive.", "biometrics"),
        ("Customer feedback forms are scored for sentiment.", "emotion_recognition"),
    ],
)
def test_english_free_text_does_not_suggest_traits(text: str, trait: str) -> None:
    """German stems ("personal"), negations and stems inside words must not set a trait."""
    assert trait not in traits_from_free_text(description_from_text(text))


@pytest.mark.parametrize(
    ("text", "unexpected_rule"),
    [
        ("The assistant summarises meeting notes for our sales team.", "annex3-3-education"),
        ("The tool automates the data migration to our new ERP system.", "annex3-7-migration"),
    ],
)
def test_german_and_ambiguous_stems_do_not_classify_english_text(
    bilingual: Assessor, text: str, unexpected_rule: str
) -> None:
    rules = _outcome(bilingual.check(description_from_text(text)))[1]
    assert unexpected_rule not in rules


@pytest.mark.parametrize(
    ("text", "roles"),
    [
        ("We develop an AI system and sell it under our own brand.", (Role.PROVIDER,)),
        ("We purchased a scheduling tool and use it for our staff.", (Role.DEPLOYER,)),
        ("We use a model that our vendor develops and hosts.", (Role.DEPLOYER,)),
        ("Hello, a question about the regulation.", ()),
    ],
)
def test_english_role_detection_stays_conservative(text: str, roles: tuple[Role, ...]) -> None:
    assert roles_from_text(text) == roles


@pytest.mark.parametrize(
    ("text", "flop"),
    [
        ("Training used 3 x 10^25 floating-point operations.", 3e25),
        ("The training compute was about 2.5e25 FLOP.", 2.5e25),
        ("We needed 10 to the power of 26 floating point operations.", 1e26),
        ("Our compute budget is 4 times 10^24 FLOPs.", 4e24),
        ("In 2025 we trained 3 models.", None),
    ],
)
def test_english_compute_notations_are_parsed(text: str, flop: float | None) -> None:
    expected = None if flop is None else pytest.approx(flop)
    assert compute_from_text(text) == expected


@pytest.mark.parametrize(
    ("text", "case"),
    [
        (
            "Our HR software reads CVs and transfers the details into fixed fields. It does "
            "not assess the applicants.",
            "art6-3-a-narrow-task",
        ),
        (
            "The tool checks spelling and grammar of finished decisions. It changes nothing "
            "about the content.",
            "art6-3-b-improvement",
        ),
    ],
)
def test_english_exemption_cases_need_a_stated_lack_of_influence(text: str, case: str) -> None:
    description = description_from_text(text)
    assert Assessor._detect_exemption_case(description) == case
    assert Assessor._no_decision_influence(description)


def test_every_code_vocabulary_has_both_languages() -> None:
    lists = [
        *vocabulary.TRAIT_KEYWORDS.values(),
        *vocabulary.EXEMPTION_CASES.values(),
        vocabulary.NO_DECISION_INFLUENCE,
        vocabulary.BIOMETRIC_CARRIERS,
        vocabulary.SAFETY_OR_MEDICAL_EXEMPTION,
        vocabulary.TRAINING_ON_OWN_DATA,
        vocabulary.PROCURED,
        vocabulary.PROVIDER_PHRASES,
        vocabulary.DEPLOYER_PHRASES,
        vocabulary.COMPUTE_MENTIONS,
    ]
    assert all(set(words) == {"de", "en"} and words["de"] and words["en"] for words in lists)
