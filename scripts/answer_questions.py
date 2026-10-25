"""Feed the walkthrough step by step with answers, for measuring the official examples.

Context: a reader answers the questions of a guideline example as an employee would for their own
system; this tool hands out the next open questions and, with --result, the finding. | Input: JSON
file mapping question ids to true, false or "not_applicable" (leaves a question undecided; an
exclusion only applies on true or false) | Output: next open questions or the finding as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from compliance_helper.classification.question_flow import NOT_APPLICABLE, Walkthrough


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True, help="JSON file with the answers given so far")
    parser.add_argument("--result", action="store_true", help="print the finding")
    args = parser.parse_args(argv)

    path = Path(args.answers)
    answers = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cleaned: dict[str, object] = {}
    for question_id, value in answers.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip().lower() in (
            NOT_APPLICABLE,
            "trifft nicht zu",
            "not applicable",
            "?",
        ):
            cleaned[question_id] = NOT_APPLICABLE
        else:
            cleaned[question_id] = bool(value)
    answers = cleaned

    walkthrough = Walkthrough.load()
    if args.result:
        finding = walkthrough.result(answers)
        print(
            json.dumps(
                {
                    "risk_class": finding.risk_class,
                    "citations": list(finding.citations),
                    "filter_applies": finding.filter_applies,
                    "filter_reason": finding.filter_reason,
                    "open_provisions": list(finding.open_provisions),
                    "closing_text": finding.closing_text,
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        return 0

    group = walkthrough.next_group(answers)
    print(
        json.dumps(
            {
                "completed": not group,
                "questions": [
                    {
                        "id": question.id,
                        "question": question.text,
                        "stage": question.stage,
                        "citation": question.citation,
                        "source_ref": question.source_ref,
                    }
                    for question in group
                ],
                "allowed_answers": [True, False, NOT_APPLICABLE],
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
