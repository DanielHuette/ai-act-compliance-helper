"""Export the measurement figures for the measurement tab of the web page.

Context: the charts must show the recounted run logs, so the page reads a file written from them
instead of figures typed into the markup. | Input: data/evaluation/figures.json, the run logs
answers-*.json and remeasurement.json, data/processed/corpus_report.json | Output:
web/benchmarks.json (path set by --output).

Usage:
    python scripts/export_benchmarks.py
    python scripts/export_benchmarks.py --output /tmp/benchmarks.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVALUATION = ROOT / "data" / "evaluation"
CORPUS_REPORT = ROOT / "data" / "processed" / "corpus_report.json"
FULL_RUN_FILES = ("answers-00-71", "answers-72-144", "answers-145-216")
VERDICT_ORDER = ("high_risk", "not_high_risk", "exemption_applies")
EXEMPTION = "exemption_applies"
#: Corpus report source keys in the order the page names the legal acts.
CORPUS_PARTS = (
    ("ai_act", "ai_act_official_journal_de.xhtml", "units"),
    ("gdpr", "gdpr_official_journal_de.xhtml", "units"),
    ("bdsg", "bdsg.html", "units"),
    ("cases", "cases", "examples"),
)

Record = dict[str, Any]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def full_run() -> list[Record]:
    """The first complete run over all official examples, in index order."""
    records: list[Record] = []
    for name in FULL_RUN_FILES:
        records += read_json(EVALUATION / f"{name}.json")
    return sorted(records, key=lambda record: int(record["index"]))


def final_results(first_run: list[Record]) -> list[Record]:
    """Each example's latest result: the remeasurement overrides the first run."""
    by_index = {int(record["index"]): record for record in first_run}
    for record in read_json(EVALUATION / "remeasurement.json"):
        by_index[int(record["index"])] = record
    return [by_index[index] for index in sorted(by_index)]


def mismatch_group(record: Record) -> str | None:
    """Group a mismatch as MEASUREMENT.md does.

    A derogation example the walkthrough misses names no Annex III area, so Article 6(3) never
    comes up; every other miss lacks a decisive feature in its description.
    """
    if record["matched"]:
        return None
    return "no_area" if record["expected"] == EXEMPTION else "missing_feature"


def verdict_bars(results: list[Record]) -> list[dict[str, Any]]:
    totals = Counter(str(record["expected"]) for record in results)
    matched = Counter(str(record["expected"]) for record in results if record["matched"])
    return [
        {"verdict": verdict, "total": totals[verdict], "matched": matched[verdict]}
        for verdict in VERDICT_ORDER
    ]


def step_histogram(first_run: list[Record]) -> list[dict[str, int]]:
    counts = Counter(int(record["steps"]) for record in first_run)
    return [{"steps": steps, "count": counts[steps]} for steps in sorted(counts)]


def corpus_parts() -> list[dict[str, Any]]:
    sources = read_json(CORPUS_REPORT)["sources"]
    return [
        {"part": part, "units": int(sources[source][field])} for part, source, field in CORPUS_PARTS
    ]


def build() -> dict[str, Any]:
    """Collect every figure the measurement tab draws."""
    figures = read_json(EVALUATION / "figures.json")
    first_run = full_run()
    results = final_results(first_run)
    return {
        "matched": sum(1 for record in results if record["matched"]),
        "total": len(results),
        "average_steps": figures["avg_steps"],
        "parity_runs": figures["parity"],
        "verdicts": verdict_bars(results),
        "steps": step_histogram(first_run),
        "examples": [
            {
                "index": int(record["index"]),
                "expected": record["expected"],
                "matched": bool(record["matched"]),
                "group": mismatch_group(record),
            }
            for record in results
        ],
        "corpus": corpus_parts(),
    }


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "web" / "benchmarks.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    target = parse_arguments(argv).output
    content = build()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{target} written — {content['matched']} of {content['total']} examples matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
