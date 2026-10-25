"""Export the worked examples for the web page.

Context: the start page offers official Commission examples that replay through the walkthrough;
the export refuses to write a case whose replay misses the Commission's verdict. | Input:
data/evaluation/showcase.yaml, data/evaluation/official_examples.json, the question flow rules |
Output: web/showcase.json (path set by --output).

Usage:
    python scripts/export_showcase.py
    python scripts/export_showcase.py --output /tmp/showcase.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from compliance_helper.classification.question_flow import Walkthrough
from compliance_helper.classification.showcase import (
    ShowcaseError,
    export,
    load_cases,
    load_official_examples,
)

ROOT = Path(__file__).resolve().parents[1]
EVALUATION = ROOT / "data" / "evaluation"


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "web" / "showcase.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    target = parse_arguments(argv).output
    try:
        content = export(
            Walkthrough.load(),
            load_cases(EVALUATION / "showcase.yaml"),
            load_official_examples(EVALUATION / "official_examples.json"),
        )
    except ShowcaseError as error:
        print(f"Showcase not written: {error}")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{target} written — {len(content['cases'])} worked examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
