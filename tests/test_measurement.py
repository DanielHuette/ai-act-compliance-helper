"""Published figures are recounted from the measurement logs and the corpus.

Context: every figure in README, UI and presentation comes from data/evaluation/figures.json and
silently goes stale after a rule change; the method is documented in MEASUREMENT.md. | Input:
figures.json, answers-*.json, remeasurement.json, corpus, README.md | Output: pass when every
published figure matches its recount.
"""

from __future__ import annotations

import json

import pytest

from compliance_helper.i18n import pick

#: The full run over all 217 official examples.
FULL_RUN_FILES = ("answers-00-71", "answers-72-144", "answers-145-216")


@pytest.fixture(scope="module")
def evaluation_dir(root):
    return root / "data" / "evaluation"


@pytest.fixture(scope="module")
def figures(evaluation_dir) -> dict:
    return json.loads((evaluation_dir / "figures.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def full_run(evaluation_dir) -> list[dict]:
    records: list[dict] = []
    for name in FULL_RUN_FILES:
        records += json.loads((evaluation_dir / f"{name}.json").read_text(encoding="utf-8"))
    return records


@pytest.fixture(scope="module")
def remeasurement(evaluation_dir) -> dict[int, dict]:
    records = json.loads((evaluation_dir / "remeasurement.json").read_text(encoding="utf-8"))
    return {e["index"]: e for e in records}


def test_every_official_example_is_measured_exactly_once(evaluation_dir, full_run, figures) -> None:
    """A skipped example would inflate the hit rate."""
    examples = json.loads((evaluation_dir / "official_examples.json").read_text(encoding="utf-8"))
    assert len(examples) == figures["total"]
    numbers = [e["index"] for e in full_run]
    assert sorted(numbers) == list(range(len(examples))), "gap or duplicate in the measurement"


def test_hit_count_is_counted_not_claimed(full_run, remeasurement, figures) -> None:
    """Matched count recounted from the logs; the remeasurement overrides the first run."""
    by_index = {e["index"]: e for e in full_run}
    by_index.update(remeasurement)
    matched = sum(1 for e in by_index.values() if e["matched"])
    assert len(by_index) == figures["total"]
    assert matched == figures["matched"], f"{matched} matched, published {figures['matched']}"


def test_step_count_is_measured_average(full_run, figures) -> None:
    """Average step count computed from the full run."""
    steps = [e["steps"] for e in full_run]
    assert all(s > 0 for s in steps), "a run without steps cannot have been measured"
    average = round(sum(steps) / len(steps), 1)
    assert average == figures["avg_steps"], f"measured {average}, published {figures['avg_steps']}"


def test_every_mismatch_is_explained(full_run, remeasurement, figures) -> None:
    """An unexplained mismatch is an open bug, not a measurement."""
    by_index = {e["index"]: e for e in full_run}
    by_index.update(remeasurement)
    unexplained = [
        i
        for i, e in sorted(by_index.items())
        if not e["matched"] and not pick(e["mismatch_reason"])
    ]
    assert not unexplained, f"mismatches without reason: {unexplained}"
    misses = [i for i, e in by_index.items() if not e["matched"]]
    assert len(misses) == figures["total"] - figures["matched"]


def test_every_expected_value_is_a_known_verdict(full_run) -> None:
    """A typo in an expected verdict would look like a walkthrough mismatch."""
    known = {
        "not_ai_system",
        "not_high_risk",
        "high_risk",
        "high_risk_annex_i",
        "exemption_applies",
    }
    unexpected = sorted({e["expected"] for e in full_run} - known)
    assert not unexpected, f"unknown expected verdicts: {unexpected}"


def test_corpus_size_matches_published_figures(corpus, figures) -> None:
    """Corpus size and per-act counts match the published figures."""
    assert len(corpus) == figures["corpus_units"]
    count_by_act: dict[str, int] = {}
    for unit in corpus:
        count_by_act[unit.legal_act.value] = count_by_act.get(unit.legal_act.value, 0) + 1
    assert count_by_act.get("AI-Act") == figures["ai_act"]
    assert count_by_act.get("GDPR") == figures["gdpr"]


@pytest.mark.parametrize(("report", "of"), [("MEASUREMENT.md", "of"), ("MEASUREMENT.de.md", "von")])
def test_measurement_report_states_its_figures_verbatim(
    evaluation_dir, figures, report: str, of: str
) -> None:
    """The English and the German measurement report justify the figures and state the same."""
    text = (evaluation_dir / report).read_text(encoding="utf-8")
    assert f"{figures['matched']} {of} {figures['total']}" in text
    assert f"{figures['parity']} {of} {figures['parity']}" in text


@pytest.mark.parametrize(("readme", "of"), [("README.md", "of"), ("README.de.md", "von")])
def test_readme_states_the_same_figures(root, figures, readme: str, of: str) -> None:
    """Every figure in the English and the German README must match figures.json."""
    text = (root / readme).read_text(encoding="utf-8")
    missing: list[str] = []
    for trait in (
        "corpus_units",
        "ai_act",
        "gdpr",
        "questions",
        "provisions",
        "exclusions",
        "examples",
    ):
        if str(figures[trait]) not in text:
            missing.append(f"{trait}={figures[trait]}")
    if f"{figures['matched']} {of} {figures['total']}" not in text:
        missing.append(f"matched={figures['matched']} of {figures['total']}")
    if f"{figures['parity']} {of} {figures['parity']}" not in text:
        missing.append(f"parity={figures['parity']}")
    average = str(figures["avg_steps"])
    if average not in text and average.replace(".", ",") not in text:
        missing.append(f"avg_steps={average}")
    assert not missing, f"missing or different in {readme}: " + ", ".join(missing)
