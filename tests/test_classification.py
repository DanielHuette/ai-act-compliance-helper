"""Classification by the rule-based assessor against stored cases and past regressions.

Context: a wrong classification makes the whole answer wrong in a way the user cannot detect. |
Input: data/cases/*.yaml, German system descriptions, the rule set | Output: pass when every case
gets its classification and no known regression returns.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from compliance_helper import paths
from compliance_helper.classification import assessor as assessor_module
from compliance_helper.classification.assessor import (
    RULE_FILES,
    Assessor,
    RuleFileError,
    description_from_text,
    roles_from_text,
    rule_set,
)
from compliance_helper.domain import Classification, RiskClass, Role, SystemDescription
from compliance_helper.i18n import Language, pick


def classify(
    assessor: Assessor, text: object, *roles: str, language: Language = Language.DE
) -> Classification:
    """Classify the ``language`` side of a bilingual text, with the stated roles if any."""
    description = description_from_text(pick(text, language))
    if roles:
        description = description.model_copy(update={"roles": tuple(Role(r) for r in roles)})
    return assessor.check(description)


def test_all_cases_match_their_classification(assessor, cases):
    """Every stored case must receive its expected classification."""
    mismatches = []
    for case in cases:
        expected_value = case.get("classification")
        if not expected_value:
            continue
        classification = classify(assessor, case["scenario"], *case["roles"])
        received = [k.value for k in classification.risk_classes]
        if expected_value not in received:
            mismatches.append(
                "{} ({}): expected {}, got {}".format(
                    case["id"], case["_file"], expected_value, received
                )
            )
    assert not mismatches, "\n".join(mismatches)


def test_every_case_states_valid_roles(cases):
    """Roles are a list of ``Role`` values; free text such as "anbieter und betreiber" is not."""
    valid = set(Role._value2member_map_)
    invalid = {
        c["id"]: c.get("roles") for c in cases if not c.get("roles") or set(c["roles"]) - valid
    }
    assert not invalid, invalid


def test_every_case_gets_at_least_one_obligation(assessor, cases):
    """Even a minimal-risk system carries the AI literacy obligation."""
    without = [
        f["id"] for f in cases if not classify(assessor, f["scenario"], *f["roles"]).obligations
    ]
    assert not without, f"cases without any obligation: {without}"


def test_case_citations_exist_in_corpus(cases, ids):
    """Every citation of a case must exist in the corpus."""
    missing: dict[str, list[str]] = {}
    for case in cases:
        positions = case.get("rechtsgrundlagen") or case.get("legal_basis") or []
        pending = [s for s in positions if s not in ids]
        if pending:
            missing[case["id"]] = pending
    assert not missing, missing


def test_application_filter_is_high_risk_not_minimal(assessor):
    """Regression: "Bewerbungen filtern" missed "Bewerbungen vorsortieren" (reported minimal)."""
    classification = classify(
        assessor,
        "Wir setzen ein Sprachmodell ein, um eingehende Bewerbungen "
        "vorzusortieren und eine Rangfolge der Kandidaten zu erstellen.",
    )
    assert RiskClass.HIGH_RISK_ANNEX_III in classification.risk_classes


def test_creditworthiness_is_not_classified_as_education(assessor):
    """Regression: "automatisch" from "note automatisch" matched every text."""
    classification = classify(
        assessor,
        "Wir prüfen die Kreditwürdigkeit von Antragstellern und "
        "berechnen automatisch einen Punktwert.",
    )
    rules = {h.rule for h in classification.indicators}
    assert "annex3-3-education" not in rules
    assert "annex3-5-essential-services" in rules


def test_conveyor_camera_is_not_administration_of_justice(assessor):
    """Regression: the stem "gericht" matched "gerichtet"."""
    classification = classify(
        assessor,
        "Ein Zulieferer prüft gestanzte Blechteile mit einer Kamera auf "
        "Risse. Geprüft werden Teile, nicht Menschen; die Kamera ist "
        "auf das Band gerichtet.",
    )
    assert {h.rule for h in classification.indicators} == {"minimal-risk"}


def test_emergency_brake_assistant_is_not_a_dialogue_system(assessor):
    """Regression: "assistent" was taken as a sign of a dialogue system."""
    classification = classify(
        assessor,
        "Ein Zulieferer entwickelt einen Notbremsassistenten. Das System "
        "erkennt Hindernisse aus Kamera- und Radardaten und löst eine "
        "Vollbremsung aus. Das Teil wird als Fahrzeugbauteil in Verkehr "
        "gebracht und unterliegt der Fahrzeugtypgenehmigung.",
        "provider",
    )
    assert RiskClass.TRANSPARENCY not in classification.risk_classes
    assert RiskClass.HIGH_RISK_ANNEX_I in classification.risk_classes


def test_manual_translation_is_not_an_annex_i_system(assessor):
    """Regression: "Maschine" alone was taken as integration into a product."""
    classification = classify(
        assessor,
        "Ein Maschinenbauer übersetzt seine Bedienungshandbücher mit "
        "einem KI-System ins Englische. Die Technische Redaktion prüft "
        "und gibt frei.",
        "provider",
    )
    assert RiskClass.HIGH_RISK_ANNEX_I not in classification.risk_classes


def test_intranet_learning_platform_stays_minimal(assessor):
    """Regression: the word "Beschäftigte" alone triggered Annex III point 4."""
    classification = classify(
        assessor,
        "Ein Industriebetrieb bietet seinen Beschäftigten eine "
        "Lernplattform. Ein KI-System schlägt Kurse vor. Die Vorschläge "
        "sind unverbindlich und spielen bei Beurteilung und Beförderung "
        "keine Rolle.",
        "deployer",
    )
    assert classification.risk_classes == (RiskClass.MINIMAL,)


def test_employee_performance_metric_is_high_risk(assessor):
    """Counterpart: no telltale keyword, but clearly Annex III point 4."""
    classification = classify(
        assessor,
        "Das System erzeugt für jeden Beschäftigten eine Kennzahl aus "
        "Gesprächsdauer und Abschlussquote und ordnet die Beschäftigten "
        "in drei Gruppen ein. Grundlage für die variable Vergütung.",
        "deployer",
    )
    assert RiskClass.HIGH_RISK_ANNEX_III in classification.risk_classes


def test_customer_free_text_is_not_prohibited_emotion_recognition(assessor):
    """Article 3(39) requires biometric data; text is not biometric."""
    classification = classify(
        assessor,
        "Wir werten die Stimmung in Freitextantworten unserer "
        "Kundenumfrage aus, um die Zufriedenheit zu messen.",
    )
    assert RiskClass.PROHIBITED not in classification.risk_classes


def test_emotion_recognition_from_facial_expressions_in_interviews_is_prohibited(assessor):
    """Counterpart: facial expressions and voice are biometric, Article 5(1)(f)."""
    classification = classify(
        assessor,
        "Ein KI-System wertet im aufgezeichneten Videointerview Mimik "
        "und Stimme aus und gibt Hinweise auf Begeisterung, Unsicherheit "
        "und Belastbarkeit des Bewerbers.",
        "deployer",
    )
    assert RiskClass.PROHIBITED in classification.risk_classes


def test_driver_fatigue_detection_is_not_prohibited(assessor):
    """Article 5(1)(f) exempts safety reasons."""
    classification = classify(
        assessor,
        "Eine Kamera im Führerhaus erkennt Müdigkeit des Fahrers und "
        "warnt ihn aus Sicherheitsgründen vor dem Einschlafen.",
        "deployer",
    )
    assert RiskClass.PROHIBITED not in classification.risk_classes


def test_exemption_is_not_assumed_by_default(assessor):
    """Article 6(3) applies only to a recognised narrow task without influence."""
    classification = classify(
        assessor,
        "Wir bewerten Bewerbungen und lehnen unter einem Schwellenwert automatisch ab.",
        "deployer",
    )
    assert RiskClass.HIGH_RISK_EXEMPTION not in classification.risk_classes
    assert RiskClass.HIGH_RISK_ANNEX_III in classification.risk_classes


def test_exemption_and_annex_iii_never_coexist(assessor, cases):
    """Both classes at once would contradict each other."""
    for case in cases:
        risk_classes = set(classify(assessor, case["scenario"], *case["roles"]).risk_classes)
        assert not (
            {RiskClass.HIGH_RISK_EXEMPTION, RiskClass.HIGH_RISK_ANNEX_III} <= risk_classes
        ), case["id"]


def test_application_filter_gets_no_biometric_obligations(assessor):
    """Article 26(10) requires biometrics and law enforcement."""
    classification = classify(
        assessor, "Wir sortieren Bewerbungen mit einem Sprachmodell vor.", "deployer"
    )
    ids = {p.id for p in classification.obligations}
    assert "high-risk-deployer-post-remote-biometric-authorisation" not in ids
    assert "prohibition-realtime-biometric-authorisation" not in ids


def test_access_control_gets_no_law_enforcement_obligation(assessor):
    """Biometrics alone is not enough for Article 26(10)."""
    classification = classify(
        assessor,
        "Gesichtserkennung zur Zutrittskontrolle am Werkstor für unsere Beschäftigten.",
        "deployer",
    )
    ids = {p.id for p in classification.obligations}
    assert "high-risk-deployer-post-remote-biometric-authorisation" not in ids


def test_trait_dependent_obligation_is_listed_with_caveat(assessor):
    """Undecidable obligations are listed with a caveat, not dropped."""
    classification = classify(
        assessor, "Wir sortieren Bewerbungen mit einem Sprachmodell vor.", "deployer"
    )
    with_caveat = [p for p in classification.obligations if p.caveat]
    assert with_caveat, "no obligation carries a caveat"
    for obligation in with_caveat:
        assert len(obligation.caveat) > 30


def test_empty_description_yields_open_questions_not_a_verdict(assessor):
    """Without information no classification may be claimed."""
    classification = assessor.check(SystemDescription())
    assert classification.open_questions


def test_without_role_both_perspectives_are_returned(assessor):
    """Without a stated role, provider and deployer obligations are both returned."""
    classification = classify(assessor, "Wir sortieren Bewerbungen vor.")
    roles = {r for p in classification.obligations for r in p.roles}
    assert {Role.PROVIDER, Role.DEPLOYER} <= roles


def test_every_obligation_cites_a_corpus_unit(assessor, cases, ids):
    """No obligation without a verifiable legal basis."""
    missing: set[str] = set()
    for case in cases:
        for obligation in classify(assessor, case["scenario"], *case["roles"]).obligations:
            missing |= {s for s in obligation.legal_basis if s and s not in ids}
    assert not missing, f"citations missing from corpus: {sorted(missing)}"


def test_role_detection_stays_conservative():
    """Buying means deployer, developing means provider, anything else no role."""
    assert roles_from_text("Wir entwickeln ein KI-System und bringen es in Verkehr.") == (
        Role.PROVIDER,
    )
    assert roles_from_text("Wir kaufen ein KI-System ein und setzen es ein.") == (Role.DEPLOYER,)
    assert roles_from_text("Guten Tag, eine Frage zur Verordnung.") == ()


@pytest.mark.parametrize("risk_class", [k for k in RiskClass if k is not RiskClass.UNCLEAR])
def test_every_risk_class_has_at_least_one_obligation(assessor, risk_class):
    """A class without obligations would be a gap in the matrix.

    ``UNCLEAR`` is excluded: it is not a legal state but "cannot classify from this
    description"; see ``test_empty_description_yields_open_questions_not_a_verdict``.
    """
    obligations = assessor._obligations({risk_class}, {Role.PROVIDER, Role.DEPLOYER})
    assert obligations, f"class without obligations: {risk_class.value}"


def test_unclear_yields_no_obligation_list(assessor):
    """Counterpart: nothing may be claimed for UNCLEAR."""
    assert assessor._obligations({RiskClass.UNCLEAR}, {Role.PROVIDER}) == []


def test_every_rule_citation_exists_in_corpus(assessor, ids):
    """No rule may cite a provision missing from the corpus."""
    missing: dict[str, list[str]] = {}
    for entry in list(assessor.rules.obligations) + list(assessor.rules.data_protection):
        positions = list(entry.get("legal_basis", [])) + list(entry.get("also_cited", []))
        pending = [s for s in positions if s and s not in ids]
        if pending:
            missing[entry["id"]] = pending
    assert not missing, missing


def test_every_reference_in_action_text_is_cited(assessor, corpus):
    """Every article named in an action text must also be cited.

    Regression: Article 26(5) refers to Article 72; the text named it, the citations did not,
    so ``unsupported_citations`` would flag it. Articles outside the corpus are excluded.
    """
    import re as _re

    ids = {e.id for e in corpus}
    gaps: dict[str, list[str]] = {}
    for file, sentences, stem in (
        ("ai_act_obligations", assessor.rules.obligations, "AI-Act"),
        ("gdpr_review_path", assessor.rules.data_protection, "GDPR"),
    ):
        for entry in sentences:
            covered_numbers = {
                t.split("art-")[1].split("/")[0]
                for t in (list(entry.get("legal_basis", [])) + list(entry.get("also_cited", [])))
                if "art-" in t
            }
            cited = set(_re.findall(r"Artikel (\d{1,3})", str(entry.get("action_required", ""))))
            pending = [
                n for n in sorted(cited - covered_numbers, key=int) if f"{stem}/art-{n}" in ids
            ]
            if pending:
                gaps["{}/{}".format(file, entry["id"])] = pending
    assert not gaps, gaps


@pytest.fixture
def rules_folder(tmp_path: Path, monkeypatch) -> Path:
    """A copy of data/rules that the rule loader reads instead of the real one."""
    folder = tmp_path / "rules"
    shutil.copytree(paths.rules_dir(), folder)
    monkeypatch.setattr(assessor_module.paths, "rules_dir", lambda: folder)
    rule_set.cache_clear()
    yield folder
    rule_set.cache_clear()


@pytest.mark.parametrize("name", sorted(RULE_FILES))
def test_missing_rule_file_stops_loading(rules_folder: Path, name: str) -> None:
    """Without a rule file every description used to come out as "minimal risk"."""
    (rules_folder / name).unlink()
    with pytest.raises(RuleFileError, match=name):
        Assessor()


def test_rule_file_without_its_entries_stops_loading(rules_folder: Path) -> None:
    """An emptied file fails open just like a missing one."""
    (rules_folder / "ai_act_risk_classes.yaml").write_text("as_of: 2026-10-04\n", encoding="utf-8")
    with pytest.raises(RuleFileError, match="high_risk_annex_iii"):
        rule_set()


@pytest.mark.parametrize(
    "field",
    [
        {"employee_count": -1},
        {"training_compute_flop": -1e26},
        {"training_compute_flop": float("inf")},
        {"training_compute_flop": float("nan")},
    ],
)
def test_counts_must_be_finite_and_not_negative(field: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        SystemDescription(**field)


def test_zero_counts_are_valid() -> None:
    description = SystemDescription(employee_count=0, training_compute_flop=0.0)
    assert (description.employee_count, description.training_compute_flop) == (0, 0.0)
