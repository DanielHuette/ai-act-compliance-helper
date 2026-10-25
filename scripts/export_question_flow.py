"""Export the question flow YAML files as one JSON file for the browser.

Context: the website and the installed program must classify identically, so both read the same
single source (data/rules/question_flow/*.yaml plus question_flow_layout.yaml). | Input: the
question flow rules | Output: web/question_flow.json (path set by --output).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from compliance_helper.classification.question_flow import Walkthrough

ROOT = Path(__file__).resolve().parents[1]


def bilingual(value: Any) -> Any:
    """Keep both languages of a data text, with line breaks folded like the Python side."""
    if isinstance(value, dict) and "de" in value:
        return {language: " ".join(str(text or "").split()) for language, text in value.items()}
    return " ".join(str(value or "").split())


def entries(items: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [dict(item) for item in items]


def export(d: Walkthrough) -> dict:
    def question(f) -> dict:
        return {
            "id": f.id,
            "text": bilingual(f.wording),
            "source_ref": f.source_ref,
            "stage": f.stage,
            "citation": f.citation,
            "title": bilingual(f.heading),
            "on_yes": f.on_yes,
            "on_no": f.on_no,
            "effect_note": bilingual(f.effect),
        }

    return {
        "as_of": d.layout.get("as_of", ""),
        "sources": [bilingual(source) for source in d.source_entries],
        "layout": d.layout,
        "preliminary_questions": [question(f) for f in d.preliminary_questions],
        "area_questions": [question(f) for f in d.area_questions],
        "notes": [question(f) for f in d.notes],
        "provisions": [
            {
                "citation": p.citation,
                "area": p.area,
                "title": bilingual(p.heading),
                "is_area_gate": p.is_area_gate,
                "main_question": question(p.main_question),
                "follow_up_questions": [question(f) for f in p.follow_up_questions],
                "covered": entries(p.covered_entries),
                "not_covered": entries(p.not_covered_entries),
                "examples": entries(p.example_entries),
            }
            for p in d.provisions
        ],
        "filter_questions": [question(f) for f in d.filter_questions],
        "profiling_question": question(d.profiling_question) if d.profiling_question else None,
        "annex_i": {
            "gate": question(d.annex_i_gate) if d.annex_i_gate else None,
            "categories": [question(f) for f in d.annex_i_categories],
            "questions": {k: question(f) for k, f in d.annex_i_questions.items()},
            "conditions": [dict(b) for b in d.annex_i_conditions],
        },
        "figures": d.figures(),
    }


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "web" / "question_flow.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    content = export(Walkthrough.load())
    target = parse_arguments(argv).output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(
        "%s written — %d provisions, %d questions, %d examples, %.0f KB"
        % (
            target,
            len(content["provisions"]),
            content["figures"]["questions"],
            content["figures"]["examples"],
            target.stat().st_size / 1024,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
