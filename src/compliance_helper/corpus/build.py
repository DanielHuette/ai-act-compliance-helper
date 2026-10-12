"""Build the legal corpus JSONL from the raw sources, in German or English.

Context: every citation and passage the app shows points to a unit of this corpus, built from the
Official Journal texts (article-wise fallback for German), the BDSG and the use-case examples; the
English corpus reproduces exactly the ids of the German one, so both languages cite the same units;
run through ``compliance-helper build-corpus --language de|en`` | Input: files under data/raw
(German) or data/raw/en, data/cases | Output:
data/processed/corpus.jsonl and corpus_report.json, or corpus.en.jsonl and corpus_report.en.json.
"""

from __future__ import annotations

import json
import re
import warnings
from collections import Counter
from datetime import date
from operator import attrgetter
from pathlib import Path

import yaml
from bs4 import XMLParsedAsHTMLWarning

from compliance_helper import paths
from compliance_helper.corpus.eurlex import from_file as parse_eurlex_file
from compliance_helper.corpus.german_sources import (
    article_files,
    parse_bdsg,
    parse_bdsg_translation,
)
from compliance_helper.domain import LegalAct, RiskClass, Unit, UnitKind
from compliance_helper.i18n import DEFAULT_LANGUAGE, Language, pick, t, use_language

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

CORPUS_NAME = "corpus.jsonl"
REPORT_NAME = "corpus_report.json"

#: Fetched by scripts/fetch_official_journal.py as ``<stem>_<language>.xhtml``; the source names
#: the Official Journal citation, not the download URL, because that is where readers verify it.
OFFICIAL_JOURNAL_SOURCES = {
    "ai_act_official_journal": (
        LegalAct.AI_ACT,
        {
            Language.DE: "Verordnung (EU) 2024/1689, ABl. L vom 12.7.2024",
            Language.EN: "Regulation (EU) 2024/1689, OJ L, 12.7.2024",
        },
        1_000_000,
    ),
    "gdpr_official_journal": (
        LegalAct.GDPR,
        {
            Language.DE: "Verordnung (EU) 2016/679, ABl. L 119 vom 4.5.2016, S. 1",
            Language.EN: "Regulation (EU) 2016/679, OJ L 119, 4.5.2016, p. 1",
        },
        700_000,
    ),
}

#: Labels of the parts of a case unit, in the order they appear.
CASE_LABELS = {
    Language.DE: {
        "title": "Anwendungsfall",
        "scenario": "Ausgangslage",
        "roles": "Rolle",
        "classification": "Einstufung",
        "rationale": "Begründung",
        "obligations": "Zu tun",
        "learning_note": "Worauf es ankommt",
        "pitfall": "Häufiger Fehler",
        "and": "und",
    },
    Language.EN: {
        "title": "Use case",
        "scenario": "Scenario",
        "roles": "Role",
        "classification": "Classification",
        "rationale": "Rationale",
        "obligations": "To do",
        "learning_note": "What matters",
        "pitfall": "Common mistake",
        "and": "and",
    },
}


def build_command(language: Language) -> str:
    """The command that builds the corpus of ``language``, wherever the tool is installed."""
    return f"compliance-helper build-corpus --language {language.value}"


def fetch_command(language: Language) -> str:
    """The command, run in the source tree, that fetches the Official Journal texts."""
    return f"python scripts/fetch_official_journal.py --language {language.value}"


def has_official_text(units: list[Unit]) -> bool:
    """True if the build found regulation text, not only the use-case examples."""
    return any(unit.legal_act is not LegalAct.GUIDELINES for unit in units)


def corpus_file(language: Language = DEFAULT_LANGUAGE) -> Path:
    """Return the corpus of ``language``; German keeps the unsuffixed name it always had."""
    if language is DEFAULT_LANGUAGE:
        return paths.processed_dir() / CORPUS_NAME
    return paths.processed_dir() / f"corpus.{language.value}.jsonl"


def report_file(language: Language = DEFAULT_LANGUAGE) -> Path:
    if language is DEFAULT_LANGUAGE:
        return paths.processed_dir() / REPORT_NAME
    return paths.processed_dir() / f"corpus_report.{language.value}.json"


def raw_dir(language: Language = DEFAULT_LANGUAGE) -> Path:
    """German raw files sit at the top of data/raw, other languages in a subfolder."""
    return paths.raw_dir() if language is DEFAULT_LANGUAGE else paths.raw_dir() / language.value


def _clean(text: str) -> str:
    text = text.replace(" ", " ").replace("‑", "-")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _side(value: object, language: Language) -> str:
    """Return one language's side of a bilingual case field."""
    chosen = pick(value, language)
    return "" if chosen is None else str(chosen)


def _risk_class_label(value: object, language: Language) -> str:
    """Return the risk class of a case as the reader sees it, never its internal id."""
    if not value:
        return ""
    with use_language(language):
        return RiskClass(str(value)).label


def _roles(roles: list[str], language: Language) -> str:
    joiner = f" {CASE_LABELS[language]['and']} "
    return joiner.join(t(f"webui.role.{role}", language) for role in roles)


def _obligation_text(item: object, language: Language) -> str:
    chosen = pick(item, language)
    if isinstance(chosen, dict):
        return " ".join(
            _side(value, language)
            for key, value in chosen.items()
            if key != "legal_basis" and value
        )
    return _side(chosen, language)


def from_cases(directory: Path, language: Language = DEFAULT_LANGUAGE) -> list[Unit]:
    """Read the use-case examples as searchable corpus units in ``language``."""
    labels = CASE_LABELS[language]
    units: list[Unit] = []
    if not directory.exists():
        return units
    for file in sorted(directory.glob("*.yaml")):
        try:
            content = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        for case in content.get("cases", []):
            case_id = case.get("id")
            if not case_id:
                continue
            parts = [
                "{}: {}".format(labels["title"], _side(case.get("title", ""), language)),
                "{}: {}".format(labels["scenario"], _side(case.get("scenario", ""), language)),
                "{}: {}".format(labels["roles"], _roles(case.get("roles") or [], language)),
                "{}: {}".format(
                    labels["classification"],
                    _risk_class_label(case.get("classification"), language),
                ),
                "{}: {}".format(labels["rationale"], _side(case.get("rationale", ""), language)),
            ]
            if case.get("obligations"):
                items = [_obligation_text(item, language) for item in case["obligations"]]
                parts.append(
                    labels["obligations"] + ": " + "; ".join(item for item in items if item)
                )
            if case.get("learning_note"):
                parts.append(
                    "{}: {}".format(labels["learning_note"], _side(case["learning_note"], language))
                )
            if case.get("pitfall"):
                parts.append("{}: {}".format(labels["pitfall"], _side(case["pitfall"], language)))
            units.append(
                Unit(
                    id=f"case/{case_id}",
                    legal_act=LegalAct.GUIDELINES,
                    kind=UnitKind.EXAMPLE,
                    number=case_id,
                    paragraph=None,
                    title=_side(case.get("title", case_id), language),
                    text=_clean("\n\n".join(part for part in parts if part.split(": ", 1)[-1])),
                    source=str(file.relative_to(paths.root())),
                    references=tuple(case.get("legal_basis", [])),
                )
            )
    return units


def _reference_ids(language: Language) -> frozenset[str] | None:
    """Return the German ids a translation must reproduce; German itself has none.

    Raises:
        FileNotFoundError: If a translation is built before the German corpus.
    """
    if language is DEFAULT_LANGUAGE:
        return None
    return frozenset(unit.id for unit in load(DEFAULT_LANGUAGE))


def collect(language: Language = DEFAULT_LANGUAGE) -> tuple[list[Unit], dict]:
    """Parse all sources into units and a build report with per-source stats and warnings."""
    units: list[Unit] = []
    report: dict = {"sources": {}, "warnings": []}
    source_dir = raw_dir(language)
    reference_ids = _reference_ids(language)

    for stem, (legal_act, addresses, min_size) in OFFICIAL_JOURNAL_SOURCES.items():
        name = f"{stem}_{language.value}.xhtml"
        path = source_dir / name
        if not path.exists() or path.stat().st_size < min_size:
            report["warnings"].append(
                f"OFFICIAL FULL TEXT MISSING: {name} — falling back to the article-wise "
                "text from a secondary source. It is incomplete: a comparison on "
                "2026-10-04 found 51 percent of the units differing, Article 13 GDPR had "
                f"909 instead of 3374 characters. Fetch it first: {fetch_command(language)}"
            )
            continue
        parsed = parse_eurlex_file(
            path,
            legal_act,
            source=addresses[language],
            language=language,
            reference_ids=reference_ids,
        )
        units.extend(parsed.units)
        report["sources"][name] = parsed.report
        report["warnings"].extend(f"{name}: {issue}" for issue in parsed.issues)

    existing = {unit.id for unit in units}

    # Fallback only per whole legal act: mixed with the official text, its differing
    # definition numbering ("para-14" vs "pt-14") duplicated content under two ids.
    # The secondary sources exist for German only.
    official_acts = {unit.legal_act for unit in units}
    for directory, legal_act in (
        (paths.raw_dir() / "ai_act", LegalAct.AI_ACT),
        (paths.raw_dir() / "gdpr", LegalAct.GDPR),
    ):
        if legal_act in official_acts or language is not DEFAULT_LANGUAGE:
            continue
        supplemented = [
            unit for unit in article_files(directory, legal_act) if unit.id not in existing
        ]
        units.extend(supplemented)
        existing.update(unit.id for unit in supplemented)
        if supplemented:
            report["sources"][directory.name + " (fallback)"] = {"supplemented": len(supplemented)}

    bdsg_path = source_dir / "bdsg.html"
    if language is DEFAULT_LANGUAGE:
        bdsg_units = parse_bdsg(bdsg_path)
        report["sources"]["bdsg.html"] = {"units": len(bdsg_units)}
    else:
        bdsg_units = parse_bdsg_translation(bdsg_path, reference_ids)
        report["sources"]["bdsg.html"] = {
            "units": len(bdsg_units),
            "source": bdsg_units[0].source if bdsg_units else "",
        }
    if not bdsg_units:
        report["warnings"].append(
            f"BDSG MISSING: {bdsg_path} — fetch it first: "
            f"python scripts/fetch_bdsg.py --language {language.value}"
        )
    units.extend(bdsg_units)

    cases = from_cases(paths.cases_dir(), language)
    units.extend(cases)
    report["sources"]["cases"] = {"examples": len(cases)}

    counter = Counter(f"{unit.legal_act.value}/{unit.kind.value}" for unit in units)
    report["units_by_kind"] = dict(sorted(counter.items()))
    report["units"] = len(units)
    report["characters"] = sum(len(unit.text) for unit in units)
    report["built_on"] = date.today().isoformat()
    if reference_ids is not None:
        built = {unit.id for unit in units}
        missing, extra = sorted(reference_ids - built), sorted(built - reference_ids)
        if missing or extra:
            report["warnings"].append(
                "IDS DIFFER FROM THE GERMAN CORPUS: %d missing %s, %d extra %s"
                % (len(missing), missing[:10], len(extra), extra[:10])
            )
    return units, report


def write(
    units: list[Unit],
    report: dict,
    corpus: Path | None = None,
    corpus_report: Path | None = None,
) -> None:
    """Write the units sorted by id as JSONL, plus the report as JSON (German paths by default)."""
    corpus = corpus or corpus_file()
    corpus_report = corpus_report or report_file()
    corpus.parent.mkdir(parents=True, exist_ok=True)
    with corpus.open("w", encoding="utf-8") as file:
        for unit in sorted(units, key=attrgetter("id")):
            file.write(unit.model_dump_json() + "\n")
    corpus_report.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


def load(language: Language = DEFAULT_LANGUAGE) -> list[Unit]:
    """Load the built corpus of ``language``.

    Raises:
        FileNotFoundError: If the corpus has not been built yet.
    """
    corpus = corpus_file(language)
    if not corpus.exists():
        raise FileNotFoundError(
            t(
                "corpus.missing",
                language_name=t(f"search.language_{language.value}"),
                path=corpus,
                command=build_command(language),
            )
        )
    return [
        Unit.model_validate_json(row)
        for row in corpus.read_text(encoding="utf-8").splitlines()
        if row.strip()
    ]
