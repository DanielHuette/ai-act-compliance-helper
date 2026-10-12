"""Worked examples on the start page must reach the Commission's verdict.

Context: the page replays official guideline examples with curated answers and shows the
Commission's verdict next to the helper's finding; a rule change must not silently turn one of
them into a disagreement. | Input: data/evaluation/showcase.yaml, official_examples.json,
web/showcase.json | Output: pass when every replay agrees and the browser copy is current.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from compliance_helper.classification.question_flow import NOT_APPLICABLE, Walkthrough
from compliance_helper.classification.showcase import (
    ShowcaseCase,
    ShowcaseError,
    agrees,
    export,
    load_cases,
    load_official_examples,
    replay,
)


@pytest.fixture(scope="module")
def walkthrough() -> Walkthrough:
    return Walkthrough.load()


@pytest.fixture(scope="module")
def evaluation(root: Path) -> Path:
    return root / "data" / "evaluation"


@pytest.fixture(scope="module")
def cases(evaluation: Path) -> tuple[ShowcaseCase, ...]:
    return load_cases(evaluation / "showcase.yaml")


@pytest.fixture(scope="module")
def examples(evaluation: Path) -> list[dict]:
    return load_official_examples(evaluation / "official_examples.json")


def _case(index: int = 0, **changes: object) -> ShowcaseCase:
    values: dict[str, object] = {
        "index": index,
        "title": {"de": "Titel", "en": "Title"},
        "topic": {"de": "Bereich", "en": "Area"},
        "yes": frozenset(),
        "unknown": frozenset(),
    }
    values.update(changes)
    return ShowcaseCase(**values)  # type: ignore[arg-type]


def test_selection_covers_every_verdict_and_twenty_examples(cases, examples) -> None:
    verdicts = {examples[case.index]["expected"] for case in cases}
    assert len(cases) == 20
    assert verdicts == {"high_risk", "not_high_risk", "exemption_applies"}


@pytest.mark.parametrize("position", range(20))
def test_every_worked_example_reaches_the_commission_verdict(
    position, cases, examples, walkthrough
) -> None:
    case = cases[position]
    finding, trace = replay(walkthrough, case)
    expected = examples[case.index]["expected"]
    assert agrees(expected, finding), (case.index, expected, finding.risk_class)
    assert trace, "the replay asked nothing"


def test_answer_defaults_to_no_and_honours_unknown() -> None:
    case = _case(yes=frozenset({"a"}), unknown=frozenset({"b"}))
    assert case.answer("a") is True
    assert case.answer("b") == NOT_APPLICABLE
    assert case.answer("c") is False


def test_replay_rejects_answers_the_flow_never_asks(walkthrough) -> None:
    case = _case(yes=frozenset({"is-ai-system", "no-such-question"}))
    with pytest.raises(ShowcaseError, match="never asked"):
        replay(walkthrough, case)


def test_export_rejects_a_replay_that_misses_the_verdict(walkthrough, examples) -> None:
    high_risk_index = next(i for i, e in enumerate(examples) if e["expected"] == "high_risk")
    with pytest.raises(ShowcaseError, match="the Commission high_risk"):
        export(walkthrough, [_case(high_risk_index)], examples)


def test_export_rejects_an_unknown_example(walkthrough, examples) -> None:
    with pytest.raises(ShowcaseError, match="does not exist"):
        export(walkthrough, [_case(len(examples))], examples)


def test_load_cases_rejects_duplicates_and_missing_languages(tmp_path) -> None:
    duplicate = tmp_path / "duplicate.yaml"
    entry = "{index: 1, title: {de: a, en: a}, topic: {de: b, en: b}}"
    duplicate.write_text(f"cases: [{entry}, {entry}]", encoding="utf-8")
    with pytest.raises(ShowcaseError, match="more than once"):
        load_cases(duplicate)
    german_only = tmp_path / "german_only.yaml"
    german_only.write_text(
        "cases: [{index: 1, title: {de: a}, topic: {de: b, en: b}}]", encoding="utf-8"
    )
    with pytest.raises(ShowcaseError, match="German and an English"):
        load_cases(german_only)


def test_load_cases_rejects_contradicting_answers(tmp_path) -> None:
    source = tmp_path / "contradiction.yaml"
    source.write_text(
        "cases: [{index: 1, title: {de: a, en: a}, topic: {de: b, en: b},"
        " yes_answers: [q], unknown_answers: [q]}]",
        encoding="utf-8",
    )
    with pytest.raises(ShowcaseError, match="both yes and unknown"):
        load_cases(source)


def test_export_writes_the_web_copy_by_default_and_it_is_current(root, tmp_path) -> None:
    spec = importlib.util.spec_from_file_location(
        "export_showcase", root / "scripts" / "export_showcase.py"
    )
    assert spec is not None and spec.loader is not None
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    assert exporter.parse_arguments([]).output == root / "web" / "showcase.json"
    fresh = tmp_path / "showcase.json"
    assert exporter.main(["--output", str(fresh)]) == 0
    assert fresh.read_bytes() == (root / "web" / "showcase.json").read_bytes()


def test_web_copy_carries_what_the_page_shows(root) -> None:
    data = json.loads((root / "web" / "showcase.json").read_text(encoding="utf-8"))
    assert data["official_examples"] == 217
    for record in data["cases"]:
        for field in ("title", "topic", "scenario"):
            assert record[field]["de"] and record[field]["en"], (record["index"], field)
        assert set(record["rationale"]) == {"de", "en"}, record["index"]
        assert record["source_ref"], record["index"]
