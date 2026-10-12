"""Worked examples: official Commission examples replayed through the walkthrough.

Context: the web page lets visitors watch the walkthrough answer real guideline examples and
compare the finding with the Commission's verdict; this module turns the curated answers into
that page data and proves each replay reaches the verdict. | Input: data/evaluation/showcase.yaml,
data/evaluation/official_examples.json, a Walkthrough | Output: ShowcaseCase records, replayed
Findings and the JSON structure written to web/showcase.json.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from compliance_helper.classification.question_flow import NOT_APPLICABLE, Finding, Walkthrough

#: Risk classes of the walkthrough that agree with each verdict the guidelines use.
AGREEING_RISK_CLASSES: Mapping[str, frozenset[str]] = {
    "high_risk": frozenset({"high_risk_annex_iii", "high_risk_annex_i", "high_risk_conditional"}),
    "not_high_risk": frozenset({"not_high_risk", "not_ai_system"}),
    "exemption_applies": frozenset({"high_risk_exemption"}),
}

#: Upper bound on question groups in one replay; the deepest real path has nine.
MAX_STEPS = 60


class ShowcaseError(ValueError):
    """The showcase selection is inconsistent with the official examples or the walkthrough."""


@dataclass(frozen=True)
class ShowcaseCase:
    """One official example together with the answers given to the walkthrough.

    Attributes:
        index: Position of the example in official_examples.json.
        title: Short card title by language code.
        topic: Area label by language code.
        yes: Question ids answered yes.
        unknown: Question ids answered "don't know".
    """

    index: int
    title: Mapping[str, str]
    topic: Mapping[str, str]
    yes: frozenset[str]
    unknown: frozenset[str]

    def answer(self, question_id: str) -> bool | str:
        """Return the answer to a question the walkthrough asks; unlisted questions are no."""
        if question_id in self.yes:
            return True
        if question_id in self.unknown:
            return NOT_APPLICABLE
        return False


def _bilingual(entry: Mapping[str, Any], key: str, index: int) -> dict[str, str]:
    value = entry.get(key)
    if not isinstance(value, Mapping) or not {"de", "en"} <= value.keys():
        raise ShowcaseError(
            f"Showcase example {index}: '{key}' needs a German and an English text."
        )
    return {"de": str(value["de"]), "en": str(value["en"])}


def _case(entry: Mapping[str, Any]) -> ShowcaseCase:
    index = entry.get("index")
    if not isinstance(index, int) or isinstance(index, bool):
        raise ShowcaseError(f"Showcase entry without a numeric index: {entry!r}")
    yes = frozenset(str(q) for q in entry.get("yes_answers") or ())
    unknown = frozenset(str(q) for q in entry.get("unknown_answers") or ())
    if yes & unknown:
        raise ShowcaseError(
            f"Showcase example {index}: answered both yes and unknown: {sorted(yes & unknown)}"
        )
    return ShowcaseCase(
        index=index,
        title=_bilingual(entry, "title", index),
        topic=_bilingual(entry, "topic", index),
        yes=yes,
        unknown=unknown,
    )


def load_cases(path: Path) -> tuple[ShowcaseCase, ...]:
    """Read the curated showcase selection.

    Args:
        path: The showcase YAML file.

    Returns:
        The cases in file order.

    Raises:
        ShowcaseError: If an entry is malformed or an example appears twice.
    """
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = tuple(_case(entry) for entry in document.get("cases") or ())
    indexes = [case.index for case in cases]
    duplicates = sorted({i for i in indexes if indexes.count(i) > 1})
    if duplicates:
        raise ShowcaseError(f"Showcase lists examples more than once: {duplicates}")
    return cases


def load_official_examples(path: Path) -> list[dict[str, Any]]:
    """Read the official guideline examples in their published order."""
    examples: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return examples


def replay(walkthrough: Walkthrough, case: ShowcaseCase) -> tuple[Finding, list[list[str]]]:
    """Answer the walkthrough group by group exactly as the browser replay does.

    Args:
        walkthrough: The loaded question flow.
        case: The example and its answers.

    Returns:
        The finding and the question ids of every group in the order asked.

    Raises:
        ShowcaseError: If a listed answer is never asked, which means the curated answers no
            longer match the question flow.
    """
    answers: dict[str, Any] = {}
    trace: list[list[str]] = []
    for _ in range(MAX_STEPS):
        group = walkthrough.next_group(answers)
        if not group:
            break
        trace.append([question.id for question in group])
        for question in group:
            answers[question.id] = case.answer(question.id)
    unasked = sorted((case.yes | case.unknown) - answers.keys())
    if unasked:
        raise ShowcaseError(
            f"Showcase example {case.index}: answers for questions never asked: {unasked}"
        )
    return walkthrough.result(answers), trace


def agrees(expected: str, finding: Finding) -> bool:
    """Tell whether a finding matches the Commission's verdict for an example."""
    return finding.risk_class in AGREEING_RISK_CLASSES.get(expected, frozenset())


def export(
    walkthrough: Walkthrough, cases: Sequence[ShowcaseCase], examples: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Build the browser data for the worked examples.

    Args:
        walkthrough: The loaded question flow, used to verify every replay.
        cases: The curated selection.
        examples: All official examples.

    Returns:
        Structure for web/showcase.json: the number of official examples and one record per case.

    Raises:
        ShowcaseError: If an index is out of range or a replay misses the Commission's verdict.
    """
    records = []
    for case in cases:
        if not 0 <= case.index < len(examples):
            raise ShowcaseError(f"Showcase example {case.index} does not exist.")
        example = examples[case.index]
        finding, trace = replay(walkthrough, case)
        if not agrees(example["expected"], finding):
            raise ShowcaseError(
                f"Showcase example {case.index}: walkthrough says {finding.risk_class}, "
                f"the Commission {example['expected']}."
            )
        records.append(
            {
                "index": case.index,
                "title": dict(case.title),
                "topic": dict(case.topic),
                "scenario": example["scenario"],
                "expected": example["expected"],
                "rationale": example.get("official_rationale") or {"de": "", "en": ""},
                "source_ref": example.get("source_ref", ""),
                "yes": sorted(case.yes),
                "unknown": sorted(case.unknown),
                "steps": len(trace),
            }
        )
    return {"official_examples": len(examples), "cases": records}
