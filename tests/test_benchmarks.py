"""The measurement tab of the web page shows the recounted run logs, not typed-in figures.

Context: web/benchmarks.json feeds the charts of the measurement tab; it is exported from the
run logs and must agree with figures.json and MEASUREMENT.md. | Input: scripts/export_benchmarks.py,
data/evaluation/*, data/processed/corpus_report.json, web/benchmarks.json | Output: pass when the
web copy is current and every chart total adds up to the published figure.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture(scope="module")
def exporter(root: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "export_benchmarks", root / "scripts" / "export_benchmarks.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def benchmarks(root: Path) -> dict:
    return json.loads((root / "web" / "benchmarks.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def figures(root: Path) -> dict:
    return json.loads((root / "data" / "evaluation" / "figures.json").read_text(encoding="utf-8"))


def test_export_writes_the_web_copy_by_default_and_it_is_current(
    root: Path, exporter: ModuleType, tmp_path: Path
) -> None:
    assert exporter.parse_arguments([]).output == root / "web" / "benchmarks.json"
    fresh = tmp_path / "benchmarks.json"
    assert exporter.main(["--output", str(fresh)]) == 0
    assert fresh.read_bytes() == (root / "web" / "benchmarks.json").read_bytes()


def test_headline_agrees_with_the_published_figures(benchmarks: dict, figures: dict) -> None:
    assert benchmarks["matched"] == figures["matched"]
    assert benchmarks["total"] == figures["total"]
    assert benchmarks["average_steps"] == figures["avg_steps"]
    assert benchmarks["parity_runs"] == figures["parity"]


def test_every_example_is_one_cell_and_the_cells_add_up(benchmarks: dict) -> None:
    cells = benchmarks["examples"]
    assert [cell["index"] for cell in cells] == list(range(benchmarks["total"]))
    assert sum(cell["matched"] for cell in cells) == benchmarks["matched"]
    assert all((cell["group"] is None) == cell["matched"] for cell in cells)


def test_mismatch_groups_follow_the_measurement_report(benchmarks: dict) -> None:
    """MEASUREMENT.md: seven derogation examples name no area, three lack the decisive feature."""
    groups: dict[str, list[int]] = {}
    for cell in benchmarks["examples"]:
        if cell["group"]:
            groups.setdefault(cell["group"], []).append(cell["index"])
    assert groups == {
        "no_area": [2, 6, 13, 47, 48, 72, 114],
        "missing_feature": [108, 141, 187],
    }


def test_verdict_bars_add_up(benchmarks: dict) -> None:
    verdicts = benchmarks["verdicts"]
    assert [v["verdict"] for v in verdicts] == ["high_risk", "not_high_risk", "exemption_applies"]
    assert sum(v["total"] for v in verdicts) == benchmarks["total"]
    assert sum(v["matched"] for v in verdicts) == benchmarks["matched"]


def test_step_histogram_reproduces_the_average(benchmarks: dict) -> None:
    bins = benchmarks["steps"]
    runs = sum(b["count"] for b in bins)
    assert runs == benchmarks["total"]
    average = sum(b["steps"] * b["count"] for b in bins) / runs
    assert round(average, 1) == benchmarks["average_steps"]


def test_corpus_parts_add_up_to_the_report(root: Path, benchmarks: dict, figures: dict) -> None:
    report = json.loads(
        (root / "data" / "processed" / "corpus_report.json").read_text(encoding="utf-8")
    )
    parts = benchmarks["corpus"]
    assert sum(part["units"] for part in parts) == report["units"] == figures["corpus_units"]
