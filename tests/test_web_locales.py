"""German and English catalogs of the static web page stay complete and in step with the markup.

Context: index.html carries German as the no-JavaScript fallback and page.js swaps it for the
catalog text of the chosen language. | Input: scripts/check_web_locales.py on web/ and on a
deliberately broken copy | Output: pass when the real page is clean and the broken copy fails.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_check(root: Path, web: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/check_web_locales.py", "--web", str(web)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_web_catalogs_match_markup_and_script(root: Path) -> None:
    completed = run_check(root, root / "web")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "0 problems" in completed.stdout


def test_check_reports_missing_key_and_stale_fallback(root: Path, tmp_path: Path) -> None:
    web = tmp_path / "web"
    shutil.copytree(root / "web", web, ignore=shutil.ignore_patterns("images", "*.jpg"))
    english_path = web / "locales" / "en.json"
    english = json.loads(english_path.read_text(encoding="utf-8"))
    del english["nav.next"]
    english_path.write_text(json.dumps(english), encoding="utf-8")
    index = web / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8").replace(">Einsatzgebiet<", ">Einsatz<"), encoding="utf-8"
    )

    completed = run_check(root, web)

    assert completed.returncode == 1
    assert "en: 'nav.next' missing" in completed.stdout
    assert "fallback text of 'phase.2' differs" in completed.stdout


def _measured_figures(root: Path) -> dict[str, int]:
    """Passage counts recounted from the corpus, question counts from the measurement record."""
    from collections import Counter

    from compliance_helper.corpus.build import load
    from compliance_helper.i18n import Language

    per_act = {
        language: Counter(unit.legal_act.value for unit in load(language)) for language in Language
    }
    assert per_act[Language.DE] == per_act[Language.EN]
    recorded = json.loads((root / "data" / "evaluation" / "figures.json").read_text("utf-8"))
    return {
        "ai_act": per_act[Language.DE]["AI-Act"],
        "gdpr": per_act[Language.DE]["GDPR"],
        "questions": recorded["questions"],
        "exclusions": recorded["exclusions"],
        "examples": recorded["examples"],
    }


def _numbers(text: str) -> set[int]:
    import re

    return {int(number.replace(",", "")) for number in re.findall(r"\d[\d,]*\d|\d", text)}


def test_published_figures_are_measured_from_the_data(root: Path) -> None:
    """The page once said 1202 and 995 passages and llms.txt 378 questions; the data said else."""
    figures = _measured_figures(root)
    sources = {
        f"locales/{language}.json": " ".join(
            text
            for key, text in json.loads(
                (root / "web" / "locales" / f"{language}.json").read_text("utf-8")
            ).items()
            if key.startswith("sources.")
        )
        for language in ("de", "en")
    }
    sources["index.html"] = (root / "web" / "index.html").read_text("utf-8")
    sources["llms.txt"] = (root / "web" / "llms.txt").read_text("utf-8")
    for name, text in sources.items():
        missing = {key: value for key, value in figures.items() if value not in _numbers(text)}
        assert not missing, (name, missing)
    for stale in (1202, 995, 378):
        assert all(stale not in _numbers(text) for text in sources.values()), stale


def test_english_page_does_not_call_the_sources_german_only(root: Path) -> None:
    english = json.loads((root / "web" / "locales" / "en.json").read_text("utf-8"))
    assert "German-language" not in english["sources.aiAct.text"]
    assert "German-language" not in english["sources.gdpr.text"]


def test_check_reads_every_script_of_the_page(root: Path, tmp_path: Path) -> None:
    """The tab modules translate too; a key typo there must fail like one in page.js."""
    web = tmp_path / "web"
    shutil.copytree(root / "web", web, ignore=shutil.ignore_patterns("images", "*.jpg", "fonts"))
    script = web / "benchmarks.js"
    script.write_text(
        script.read_text(encoding="utf-8").replace('"bench.error"', '"bench.errorr"'),
        encoding="utf-8",
    )

    completed = run_check(root, web)

    assert completed.returncode == 1
    assert "benchmarks.js: key 'bench.errorr' not in the catalog" in completed.stdout


def test_masthead_names_the_measured_hit_rate(root: Path) -> None:
    """The strongest figure of the project stands in the first view, recounted from the logs."""
    recorded = json.loads((root / "data" / "evaluation" / "figures.json").read_text("utf-8"))
    for language in ("de", "en"):
        catalog = json.loads((root / "web" / "locales" / f"{language}.json").read_text("utf-8"))
        figure = catalog["hero.measuredFigure"]
        assert _numbers(figure) == {recorded["matched"], recorded["total"]}, (language, figure)
