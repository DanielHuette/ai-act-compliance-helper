"""Smoke test of the rule set: expected counts, one Annex III probe and legal bases in the corpus.

Context: an accidental deletion in a rule file, or a legal basis the corpus lacks, changes answers
without failing a unit test; CI and scripts/check_all.sh run this check alike. The expected
counts are spelled out on purpose and change only with a deliberate change of the rule set. |
Input: data/rules, data/processed/corpus.jsonl | Output: a short report, exit code 1 on a
deviation (a missing legal basis only warns, because the obligation is still shown).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from compliance_helper.classification.assessor import (  # noqa: E402
    Assessor,
    RuleSet,
    description_from_text,
    rule_set,
)
from compliance_helper.corpus.build import load  # noqa: E402

EXPECTED_COUNTS = {"obligations": 57, "data_protection": 26, "deadlines": 5}
PROBE = "Wir setzen eine zugekaufte Software ein, die Bewerbungen automatisch vorsortiert."


def count_deviations(rules: RuleSet) -> list[str]:
    deviations = [
        f"{name}: {len(getattr(rules, name))} instead of {expected}"
        for name, expected in EXPECTED_COUNTS.items()
        if len(getattr(rules, name)) != expected
    ]
    if rules.as_of is None:
        deviations.append("the rule set has no as_of date")
    return deviations


def probe_deviations() -> list[str]:
    classification = Assessor().check(description_from_text(PROBE))
    risk_classes = [risk_class.value for risk_class in classification.risk_classes]
    print("Probe:", risk_classes, "-", len(classification.obligations), "obligations")
    if "high_risk_annex_iii" not in risk_classes:
        return [f"the probe is not classified as Annex III high risk: {risk_classes}"]
    if not classification.obligations:
        return ["the probe gets no obligations"]
    return []


def missing_legal_bases(rules: RuleSet) -> list[str]:
    known_ids = {unit.id for unit in load()}
    print(len(known_ids), "legal units in the German corpus")
    cited = {
        citation_id
        for entry in (*rules.obligations, *rules.data_protection)
        for citation_id in entry.get("legal_basis", [])
    }
    return sorted(cited - known_ids)


def main() -> int:
    rules = rule_set()
    print(
        "Rule set as of",
        rules.as_of,
        "-",
        ", ".join(f"{len(getattr(rules, name))} {name}" for name in EXPECTED_COUNTS),
    )
    deviations = count_deviations(rules) + probe_deviations()
    for citation_id in missing_legal_bases(rules):
        print(f"::warning title=Legal basis not in corpus::{citation_id}")
    for deviation in deviations:
        print(f"::error title=Rule set::{deviation}")
    return 1 if deviations else 0


if __name__ == "__main__":
    raise SystemExit(main())
