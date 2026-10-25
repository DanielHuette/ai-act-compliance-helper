"""Classification of the stored cases from their English scenarios.

Context: English free text must reach the classification the German scenario reaches, through
the English vocabularies alone, with no German word helping. | Input: data/cases/*.yaml, English
side of each scenario, the rule set | Output: pass when every English scenario gets its expected
classification and the same risk classes as its German original.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from test_classification import classify

from compliance_helper.domain import RiskClass
from compliance_helper.i18n import Language, use_language


@pytest.fixture
def english() -> Iterator[Language]:
    with use_language(Language.EN) as language:
        yield language


def test_all_english_cases_match_their_classification(assessor, cases, english):
    """Every English scenario must receive the expected classification of its case."""
    mismatches = []
    for case in cases:
        classification = classify(assessor, case["scenario"], *case["roles"], language=english)
        received = [k.value for k in classification.risk_classes]
        if case["classification"] not in received:
            mismatches.append(f"{case['id']}: expected {case['classification']}, got {received}")
    assert not mismatches, "\n".join(mismatches)


def test_english_and_german_scenarios_share_risk_classes(assessor, cases, english):
    """Both language versions describe the same system, so they must land in the same classes."""
    differing = []
    for case in cases:
        german = classify(assessor, case["scenario"], *case["roles"], language=Language.DE)
        english_result = classify(assessor, case["scenario"], *case["roles"], language=english)
        if german.risk_classes != english_result.risk_classes:
            differing.append(
                f"{case['id']}: de {[k.value for k in german.risk_classes]}, "
                f"en {[k.value for k in english_result.risk_classes]}"
            )
    assert not differing, "\n".join(differing)


def test_english_exemption_and_annex_iii_never_coexist(assessor, cases, english):
    """Both classes at once would contradict each other, in English as in German."""
    for case in cases:
        risk_classes = set(
            classify(assessor, case["scenario"], *case["roles"], language=english).risk_classes
        )
        assert not (
            {RiskClass.HIGH_RISK_EXEMPTION, RiskClass.HIGH_RISK_ANNEX_III} <= risk_classes
        ), case["id"]
