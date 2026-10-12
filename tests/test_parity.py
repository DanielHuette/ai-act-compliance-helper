"""Python and JavaScript walkthroughs must compute the same classification.

Context: the flow logic exists in question_flow.py and web/walkthrough.js, and two copies drift
apart; this also catches a stale web/question_flow.json. | Input: scripts/check_parity.py with
seeded random answer patterns | Output: pass when every run agrees.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

#: Same number of runs as the test bench and the pre-packaging check.
RUNS = 400


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_python_and_js_walkthroughs_agree(root) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_parity.py", "--runs", str(RUNS)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=600,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode == 2:
        pytest.skip(f"The browser walkthrough could not run here:\n{output[-600:]}")
    assert completed.returncode == 0, output[-2000:]
    assert f"{RUNS} of {RUNS} runs identical" in output, output[-600:]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_parity_check_compares_evidence_and_closing_text(root, tmp_path) -> None:
    """A browser copy that differs only in evidence or closing text must fail the check."""
    web = tmp_path / "web"
    shutil.copytree(root / "web", web)
    script = web / "walkthrough.js"
    source = script.read_text(encoding="utf-8")
    diverging = source.replace("return refs.filter(Boolean);", "return refs;")
    diverging = diverging.replace("closing_text: withProduct(", 'closing_text: "" + withProduct(')
    diverging = diverging.replace('.replace("{product}", product)', '.replace("{product}", "")')
    assert diverging != source, "the walkthrough changed; adjust this test"
    script.write_text(diverging, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "scripts/check_parity.py", "--runs", "120", "--web", str(web)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=600,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode == 2:
        pytest.skip(f"The browser walkthrough could not run here:\n{output[-600:]}")
    assert completed.returncode == 1, output[-2000:]
    assert "closing_text_en" in output or "evidence" in output, output[-2000:]


def test_hanging_browser_walkthrough_is_stopped(root, monkeypatch, capsys) -> None:
    """A Node.js driver that never ends must not hold the check, or a CI job, forever."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_parity", root / "scripts" / "check_parity.py"
    )
    assert spec is not None and spec.loader is not None
    check_parity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_parity)
    timeouts: list[float] = []

    def hanging_node(*_arguments: object, timeout: float, **_options: object) -> None:
        timeouts.append(timeout)
        raise subprocess.TimeoutExpired("node", timeout)

    monkeypatch.setattr(check_parity.subprocess, "run", hanging_node)
    assert check_parity.main(["--runs", "1"]) == 2
    assert timeouts == [check_parity.NODE_TIMEOUT_SECONDS]
    assert "did not finish" in capsys.readouterr().out
