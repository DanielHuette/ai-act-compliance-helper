"""Check that the walkthrough behaves identically in Python and in the browser.

Context: the flow logic exists twice (classification/question_flow.py and web/walkthrough.js) and
two copies of the same logic drift apart. | Input: seeded random answer patterns (--runs, --seed),
every fourth one aimed at the Annex I path with many "don't know" answers, the web folder (--web),
Node.js | Output: per-run comparison of question order, risk class, citations, evidence, open
provisions, filter reason and closing text in German and English; exit code 1 on divergences.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compliance_helper.classification.question_flow import (  # noqa: E402
    NOT_APPLICABLE,
    Finding,
    Walkthrough,
)
from compliance_helper.i18n import Language, use_language  # noqa: E402

LANGUAGES = tuple(language.value for language in Language)
#: 200 runs in two languages take a few seconds; a hanging driver must not hold a CI job.
NODE_TIMEOUT_SECONDS = 300

#: Every fourth pattern exercises the Annex I path, where "don't know" once counted as yes.
ANNEX_I_PATTERN_EVERY = 4

JS_DRIVER = """
import {{Walkthrough}} from "{js}";
import {{readFileSync}} from "fs";
const data = JSON.parse(readFileSync({json}, "utf8"));
const patterns = JSON.parse(readFileSync({pattern}, "utf8"));
const out = [];
for (const m of patterns) {{
  const d = new Walkthrough(data);
  const a = {{}};
  const trace = [];
  let guard = 0;
  while (guard++ < 400) {{
    const g = d.nextGroup(a);
    if (!g.length) break;
    trace.push(g.map((f) => f.id));
    for (const f of g) a[f.id] = m[f.id] === undefined ? false : m[f.id];
  }}
  const run = {{trace}};
  for (const language of {languages}) {{
    const e = d.result(a, language);
    Object.assign(run, {{risk_class: e.risk_class,
      citations: e.matched_provisions.map((p) => p.citation),
      filter: e.filter_applies, evidence: e.evidence, open_provisions: e.open_provisions}});
    run["filter_reason_" + language] = e.filter_reason;
    run["closing_text_" + language] = e.closing_text;
  }}
  out.push(run);
}}
process.stdout.write(JSON.stringify(out));
"""


def _answer(rng: random.Random, yes: float, no: float) -> object:
    w = rng.random()
    return True if w < yes else (False if w < yes + no else NOT_APPLICABLE)


def annex_i_answers(d: Walkthrough, rng: random.Random) -> dict[str, object]:
    """Overlay that opens the Annex I path and answers it with many "don't know"."""
    overlay: dict[str, object] = {}
    if d.annex_i_gate:
        overlay[d.annex_i_gate.id] = True
    for f in d.annex_i_categories:
        overlay[f.id] = _answer(rng, 0.15, 0.55)
    for f in d.annex_i_questions.values():
        overlay[f.id] = _answer(rng, 0.35, 0.30)
    return overlay


def random_answers(d: Walkthrough, rng: random.Random) -> dict[str, object]:
    """One answer pattern covering every question in the flow."""
    all_items = [f.id for f in d.preliminary_questions]
    all_items += [f.id for f in d.area_questions]
    all_items += [p.main_question.id for p in d.provisions]
    all_items += [f.id for p in d.provisions for f in p.follow_up_questions]
    all_items += [f.id for f in d.filter_questions]
    if d.profiling_question:
        all_items.append(d.profiling_question.id)
    if d.annex_i_gate:
        all_items.append(d.annex_i_gate.id)
    all_items += [f.id for f in d.annex_i_categories]
    all_items += [f.id for f in d.annex_i_questions.values()]
    pattern = {k: _answer(rng, 0.35, 0.50) for k in all_items}
    # "No AI system" ends the walkthrough at once; keep that case rare so most runs go deep.
    if d.preliminary_questions:
        pattern[d.preliminary_questions[0].id] = rng.random() > 0.08
    return pattern


def _result_fields(e: Finding, language: str) -> dict[str, object]:
    return {
        "risk_class": e.risk_class,
        "citations": list(e.citations),
        "filter": e.filter_applies,
        "evidence": list(e.evidence),
        "open_provisions": list(e.open_provisions),
        f"filter_reason_{language}": e.filter_reason,
        f"closing_text_{language}": e.closing_text,
    }


def python_run(d: Walkthrough, pattern: dict[str, object]) -> dict:
    a: dict[str, object] = {}
    trace: list[list[str]] = []
    guard = 0
    while guard < 400:
        guard += 1
        g = d.next_group(a)
        if not g:
            break
        trace.append([f.id for f in g])
        for f in g:
            a[f.id] = pattern.get(f.id, False)
    run: dict[str, object] = {"trace": trace}
    for language in Language:
        with use_language(language):
            run.update(_result_fields(d.result(a), language.value))
    return run


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs", type=int, default=200)
    p.add_argument("--seed", type=int, default=20261004)
    p.add_argument(
        "--web",
        type=Path,
        default=ROOT / "web",
        help="folder with walkthrough.js and question_flow.json",
    )
    a = p.parse_args(argv)

    d = Walkthrough.load()
    rng = random.Random(a.seed)  # nosec B311
    pattern = [random_answers(d, rng) for _ in range(a.runs)]
    for m in pattern[::ANNEX_I_PATTERN_EVERY]:
        m.update(annex_i_answers(d, rng))

    tmp_dir = tempfile.TemporaryDirectory()
    directory = Path(tmp_dir.name)
    (directory / "patterns.json").write_text(json.dumps(pattern), encoding="utf-8")
    driver = directory / "driver.mjs"
    driver.write_text(
        JS_DRIVER.format(
            js=(a.web / "walkthrough.js").resolve().as_uri(),
            # JSON-encoded: Windows backslashes like "\\a" would be escape sequences in JS.
            json=json.dumps(str(a.web / "question_flow.json")),
            pattern=json.dumps(str(directory / "patterns.json")),
            languages=json.dumps(LANGUAGES),
        ),
        encoding="utf-8",
    )
    try:
        run = subprocess.run(  # nosec B603 B607
            ["node", str(driver)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=NODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(f"The browser walkthrough did not finish within {NODE_TIMEOUT_SECONDS} seconds.")
        return 2
    except FileNotFoundError:
        print("Node.js is not installed; the browser walkthrough cannot run.")
        return 2
    if run.returncode != 0:
        print("The browser walkthrough could not run:\n" + run.stderr[-2000:])
        return 2
    js = json.loads(run.stdout)

    error = 0
    for i, m in enumerate(pattern):
        py_result = python_run(d, m)
        if py_result == js[i]:
            continue
        error += 1
        if error <= 3:
            print(f"\n--- Run {i}: Python and browser differ ---")
            if py_result["trace"] != js[i]["trace"]:
                for s, (x, y) in enumerate(zip(py_result["trace"], js[i]["trace"], strict=False)):
                    if x != y:
                        print(f"  Step {s + 1} differs:")
                        print(f"    Python : {x[:6]}")
                        print(f"    Browser: {y[:6]}")
                        break
                else:
                    py_steps, js_steps = len(py_result["trace"]), len(js[i]["trace"])
                    print(f"  Step count: Python {py_steps}, browser {js_steps}")
                    k = min(len(py_result["trace"]), len(js[i]["trace"]))
                    longer = py_result if len(py_result["trace"]) > k else js[i]
                    print(f"    additional step: {longer['trace'][k][:6]}")
            for key in sorted(set(py_result) - {"trace"}):
                if py_result[key] != js[i].get(key):
                    print(f"  {key}: Python {py_result[key]!r}, browser {js[i][key]!r}")

    print(f"\n{a.runs - error} of {a.runs} runs identical.")
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
