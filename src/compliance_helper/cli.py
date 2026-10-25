"""Command-line interface: classify, ask, search, serve, status and the two data builds.

Context: Human-readable terminal access to the same classification, answer and search logic
as the web service, in German or English (``--lang``), with ``--json`` for machine output and
colour only on a TTY; developer logging stays hidden unless ``--verbose``. | Input: command-line
arguments and environment | Output: formatted text or JSON on stdout, notices on stderr, an
exit code.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import textwrap
from collections.abc import Callable, Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from compliance_helper import paths
from compliance_helper.domain import Classification, LegalAct, Passage, RiskClass, Role, Unit
from compliance_helper.i18n import Language, current_language, t, use_language
from compliance_helper.security import (
    InputError,
    install_log_redaction,
    validate_description,
    validate_question,
)

if TYPE_CHECKING:
    from compliance_helper.service.app import ServiceState

WIDTH = 78
LANGUAGE_VARIABLE = "COMPLIANCE_HELPER_LANG"
ROOT_VARIABLE = "COMPLIANCE_HELPER_ROOT"
MAX_ASK_COUNT = 20
MAX_SEARCH_COUNT = 30
SILENT = logging.CRITICAL + 1
MODEL_CHOICES = ("auto", "anthropic", "openai", "none")
COMMANDS_WITHOUT_DATA = frozenset({"status"})

_log_handler: logging.Handler | None = None


class DataMissingError(Exception):
    """The data directory with rules, cases and corpus is not where the tool looks for it."""


class Colors:
    """ANSI colour helpers that return plain text when colour is disabled."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _ansi(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return self._ansi("1", text)

    def dim(self, text: str) -> str:
        return self._ansi("2", text)

    def red(self, text: str) -> str:
        return self._ansi("1;31", text)

    def orange(self, text: str) -> str:
        return self._ansi("1;33", text)

    def blue(self, text: str) -> str:
        return self._ansi("1;34", text)

    def green(self, text: str) -> str:
        return self._ansi("1;32", text)

    def by_risk_class(self, risk_class: RiskClass, text: str) -> str:
        """Colour by risk class, matching the four colours of the web UI."""
        if risk_class is RiskClass.PROHIBITED:
            return self.red(text)
        if risk_class.value.startswith("high_risk"):
            return self.orange(text)
        if risk_class.value.startswith("gpai") or risk_class is RiskClass.TRANSPARENCY:
            return self.blue(text)
        if risk_class is RiskClass.MINIMAL:
            return self.green(text)
        return text


def choose_colors(no_color: bool) -> Colors:
    if no_color or os.environ.get("NO_COLOR") is not None:
        return Colors(enabled=False)
    return Colors(enabled=sys.stdout.isatty())


def requested_language(argv: list[str]) -> Language:
    """Return the language named by ``--lang``, else by ``COMPLIANCE_HELPER_LANG``, else German.

    Read before the full parser exists, because its help texts depend on the language.
    """
    pre_parser = argparse.ArgumentParser(
        prog="compliance-helper", add_help=False, allow_abbrev=False
    )
    pre_parser.add_argument("--lang")
    known, _ = pre_parser.parse_known_args(argv)
    return Language.parse(known.lang or os.environ.get(LANGUAGE_VARIABLE))


def configure_logging(verbose: bool, command: str) -> None:
    """Route developer logging to stderr: shown with ``--verbose``, by ``serve`` from WARNING."""
    global _log_handler
    install_log_redaction()
    root_logger = logging.getLogger()
    if _log_handler is not None:
        root_logger.removeHandler(_log_handler)
    _log_handler = logging.StreamHandler(sys.stderr)
    _log_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    if verbose:
        _log_handler.setLevel(logging.INFO)
        logging.getLogger("compliance_helper").setLevel(logging.INFO)
    else:
        _log_handler.setLevel(logging.WARNING if command == "serve" else SILENT)
    root_logger.addHandler(_log_handler)
    logging.captureWarnings(not verbose)


def bounded_count(maximum: int) -> Callable[[str], int]:
    """Return an argparse type that accepts whole numbers from 1 to ``maximum``."""

    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError:
            number = 0
        if not 1 <= number <= maximum:
            raise argparse.ArgumentTypeError(
                t("cli.count_out_of_range", value=value, maximum=maximum)
            )
        return number

    return parse


def _date(value: date) -> str:
    return value.strftime(t("cli.date_format"))


def _count_label(count: int) -> str:
    return t("cli.count_one") if count == 1 else t("cli.count_many", count=count)


def _language_name(language: Language) -> str:
    return t(f"search.language_{language.value}")


def corpus_as_of(units: Iterable[Unit]) -> date | None:
    """Return the most recent ``as_of`` date of ``units``, the date the corpus reflects."""
    return max((unit.as_of for unit in units if unit.as_of), default=None)


def _wrap(text: str, indent: str = "  ") -> str:
    lines = []
    for paragraph in str(text).split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                paragraph,
                width=WIDTH,
                initial_indent=indent,
                subsequent_indent=indent,
                # Ids like AI-Act/art-6/para-2 must stay copyable into the search.
                break_on_hyphens=False,
                break_long_words=False,
            )
            or [indent]
        )
    return "\n".join(lines)


def _print_heading(colors: Colors, text: str) -> None:
    print()
    print(colors.bold(text))
    print(colors.dim("─" * min(len(text), WIDTH)))


def _print_notices(colors: Colors, notices: Iterable[str]) -> None:
    for notice in notices:
        print(_wrap(colors.orange(t("cli.note")) + " " + notice, indent=""), file=sys.stderr)


def _print_risk_class(colors: Colors, classification: Classification) -> None:
    most_severe = classification.most_severe
    _print_heading(colors, t("cli.heading_classification"))
    print("  " + colors.by_risk_class(most_severe, most_severe.label))
    print(_wrap(most_severe.explanation))
    if len(classification.risk_classes) > 1:
        others = ", ".join(
            risk_class.label
            for risk_class in classification.risk_classes
            if risk_class is not most_severe
        )
        print(_wrap(t("cli.other_classes", classes=others)))
    print()
    if not classification.roles:
        print(_wrap(t("cli.role_missing")))
    for role in classification.roles:
        print(_wrap(t("cli.role_line", role=role.label, definition=role.definition)))


def _print_indicators(colors: Colors, classification: Classification) -> None:
    _print_heading(colors, t("cli.heading_why"))
    for indicator in classification.indicators:
        print(_wrap(f"• {indicator.rationale}"))
        details = t(
            "cli.indicator_details",
            confidence=indicator.confidence_label,
            citations=", ".join(indicator.citations) or t("cli.none"),
        )
        print(colors.dim(_wrap(details, indent="    ")))


def _print_obligations(colors: Colors, classification: Classification) -> None:
    if classification.obligations:
        count = _count_label(len(classification.obligations))
        _print_heading(colors, t("cli.heading_ai_act_obligations", count=count))
    for number, obligation in enumerate(classification.obligations, 1):
        severity = (
            "" if obligation.severity.value == "obligation" else f" [{obligation.severity.label}]"
        )
        print("  %2d. %s%s" % (number, colors.bold(obligation.title), severity))
        print(_wrap(obligation.action_required, indent="      "))
        deadline = (
            " · " + t("cli.applies_from", date=_date(obligation.applies_from))
            if obligation.applies_from
            else ""
        )
        print(colors.dim(_wrap(f"{obligation.citation_text}{deadline}", indent="      ")))

    if classification.data_protection:
        count = _count_label(len(classification.data_protection))
        _print_heading(colors, t("cli.heading_data_protection", count=count))
    for number, section in enumerate(classification.data_protection, 1):
        print("  %2d. %s" % (number, colors.bold(section.title)))
        print(_wrap(section.action_required, indent="      "))
        print(colors.dim(_wrap(section.citation_text, indent="      ")))


def print_classification(colors: Colors, classification: Classification) -> None:
    _print_risk_class(colors, classification)
    _print_indicators(colors, classification)
    _print_obligations(colors, classification)
    if classification.open_questions:
        _print_heading(colors, t("cli.heading_open_questions"))
        for question in classification.open_questions:
            print(_wrap(f"? {question}"))


def print_evidence(colors: Colors, evidence: Sequence[Passage], show_wording: bool) -> None:
    _print_heading(colors, t("cli.heading_evidence", count=len(evidence)))
    for number, passage in enumerate(evidence, 1):
        title = colors.dim(f"— {passage.title}" if passage.title else "")
        print("  %2d. %s %s" % (number, colors.bold(passage.citation), title))
        details = t(
            "cli.passage_details",
            id=passage.id,
            score=passage.score,
            routes=", ".join(passage.routes) or t("cli.unknown"),
        )
        print(colors.dim(_wrap(details, indent="      ")))
        if show_wording:
            print(_wrap(passage.excerpt, indent="      "))
            print()


def _print_footer(colors: Colors) -> None:
    """Print the no-legal-advice disclaimer and rule-set version under every answer."""
    from compliance_helper.classification.assessor import rule_set

    rules = rule_set()
    print()
    print(colors.dim("─" * WIDTH))
    disclaimer = colors.bold(t("cli.disclaimer_title")) + " " + t("cli.disclaimer_text")
    print(_wrap(disclaimer, indent=""))
    if rules.as_of:
        print(colors.dim(t("cli.rules_as_of", date=_date(rules.as_of))))
    if rules.deadline_caveat:
        caveat = " ".join(rules.deadline_caveat.split())
        print(colors.dim(_wrap(t("cli.deadline_caveat", caveat=caveat), indent="")))


def _parse_roles(values: list[str] | None) -> tuple[Role, ...]:
    """Convert ``--role`` values to ``Role`` members.

    Raises:
        InputError: For an unknown role.
    """
    allowed = {role.value for role in Role}
    found: list[Role] = []
    for value in values or ():
        word = value.strip().lower()
        if word not in allowed:
            raise InputError(t("cli.unknown_role", value=value, allowed=", ".join(sorted(allowed))))
        found.append(Role(word))
    return tuple(found)


def _parse_legal_acts(values: list[str] | None) -> tuple[LegalAct, ...] | None:
    """Convert ``--legal-act`` values to ``LegalAct`` members; ``None`` means no filter.

    Raises:
        InputError: For an unknown legal act.
    """
    if not values:
        return None
    allowed = {act.value.lower(): act for act in LegalAct}
    found: list[LegalAct] = []
    for value in values:
        act = allowed.get(value.strip().lower())
        if act is None:
            names = ", ".join(act.value for act in LegalAct)
            raise InputError(t("cli.unknown_legal_act", value=value, allowed=names))
        found.append(act)
    return tuple(found)


def _classify(text: str, role_values: list[str] | None) -> Classification:
    from compliance_helper.classification.assessor import Assessor, description_from_text

    description = description_from_text(text)
    if role_values:
        description = description.model_copy(update={"roles": _parse_roles(role_values)})
    return Assessor().check(description)


def _load_service_state(
    args: argparse.Namespace, with_llm: bool = True, with_purposes: bool = True
) -> ServiceState:
    """Load corpus and search index of the active language and show its notices on stderr."""
    from compliance_helper.service.app import load_service_state

    if not args.json:
        print(t("cli.loading"), file=sys.stderr)
    service_state = load_service_state(
        with_llm=with_llm, languages=(current_language(),), with_purposes=with_purposes
    )
    _print_notices(args.colors, (notice.text() for notice in service_state.notices))
    if service_state.search_index is None:
        print(t("cli.index_unavailable"), file=sys.stderr)
    return service_state


def command_classify(args: argparse.Namespace) -> int:
    text = validate_description(args.description)
    if not text:
        raise InputError(t("cli.description_missing"))
    result = _classify(text, args.role)
    if args.json:
        print(result.model_dump_json(indent=1))
        return 0
    print_classification(args.colors, result)
    _print_footer(args.colors)
    return 0


def command_ask(args: argparse.Namespace) -> int:
    from compliance_helper.answer.compose import choose_model, compose
    from compliance_helper.search.index import to_passages
    from compliance_helper.service.app import _learning_note_and_cases, reranking_enabled

    question = validate_question(args.question)
    description_text = validate_description(args.description)
    requested_model = (args.model or os.environ.get("COMPLIANCE_HELPER_MODEL", "auto")).lower()
    without_model = requested_model in ("none", "rules")
    service_state = _load_service_state(args, with_llm=not without_model)
    if service_state.search_index is None:
        return 2

    result = _classify(description_text or question, args.role)
    search_text = f"{question}\n{description_text}" if description_text else question
    hits = service_state.search_index.search(
        search_text[:4000],
        count=args.count,
        legal_acts_filter=_parse_legal_acts(args.legal_act),
        rerank=reranking_enabled(),
    )
    learning_note, cases = _learning_note_and_cases([hit.unit for hit in hits])
    if without_model:
        model = None
    elif requested_model == "auto":
        model = service_state.llm
    else:
        model = choose_model(requested_model)
    answer = compose(
        question,
        description_text,
        result,
        to_passages(hits),
        model=model,
        learning_note=learning_note,
        example_cases=cases,
    )

    if args.json:
        print(answer.model_dump_json(indent=1))
        return 0
    colors = args.colors
    print_classification(colors, result)
    # Without a model the answer text only restates the classification printed above.
    if not answer.without_model:
        _print_heading(colors, t("cli.heading_answer"))
        print(_wrap(answer.text))
        print(colors.dim(_wrap(t("cli.composed_by_model", model=answer.model))))
    if answer.learning_note:
        _print_heading(colors, t("cli.heading_learning_note"))
        print(_wrap(answer.learning_note))
        if answer.example_cases:
            listed = " · ".join(answer.example_cases)
            print(colors.dim(_wrap(t("cli.comparable_cases", cases=listed))))
    print_evidence(colors, answer.evidence, show_wording=args.show_wording)
    if answer.without_model:
        print()
        print(colors.dim(_wrap(t("cli.composed_without_model"), indent="")))
    for warning in answer.warnings:
        if answer.without_model and warning == t("answer.warning_without_model"):
            continue
        print()
        print(_wrap(colors.orange(t("cli.note") + " ") + warning, indent=""))
    _print_footer(colors)
    return 0


def command_search(args: argparse.Namespace) -> int:
    from compliance_helper.search.index import to_passages
    from compliance_helper.service.app import reranking_enabled

    question = validate_question(args.query)
    service_state = _load_service_state(args, with_llm=False, with_purposes=False)
    if service_state.search_index is None:
        return 2
    hits = service_state.search_index.search(
        question,
        count=args.count,
        legal_acts_filter=_parse_legal_acts(args.legal_act),
        rerank=reranking_enabled(),
    )
    evidence = to_passages(hits)
    if args.json:
        passages = [passage.model_dump() for passage in evidence]
        print(json.dumps(passages, ensure_ascii=False, indent=1, default=str))
        return 0
    print_evidence(args.colors, evidence, show_wording=not args.brief)
    return 0


def command_serve(args: argparse.Namespace) -> int:
    from compliance_helper.service.app import run_server

    colors = args.colors
    print(colors.bold(t("cli.serve_starting", name=t("app.name"))))
    address = colors.blue(f"http://{args.address}:{args.port:d}/")
    print(_wrap(t("cli.serve_address", address=address), indent=""))
    print(_wrap(colors.dim(t("cli.serve_stop")), indent=""))
    print()
    run_server(address=args.address, port=args.port, reload=args.reload)
    return 0


def _status_as_json(service_state: ServiceState, corpus: Path) -> str:
    from compliance_helper.classification.assessor import rule_set

    rules = rule_set()
    as_of = corpus_as_of(service_state.units)
    return json.dumps(
        {
            "language": current_language().value,
            "data_directory": str(paths.data_dir()),
            "corpus": str(corpus),
            "corpus_exists": corpus.exists(),
            "units": len(service_state.units),
            "corpus_as_of": as_of.isoformat() if as_of else "",
            "index_from_file": service_state.index_from_file,
            "embedding_model": service_state.embedding_model,
            "llm": service_state.llm_name,
            "rules_as_of": rules.as_of.isoformat() if rules.as_of else "",
            "obligations": len(rules.obligations),
            "warnings": service_state.warnings,
        },
        ensure_ascii=False,
        indent=1,
    )


def _print_corpus_status(colors: Colors, service_state: ServiceState, corpus: Path) -> None:
    as_of = corpus_as_of(service_state.units)
    _print_heading(colors, t("cli.heading_corpus"))
    print(_wrap(t("cli.file", path=corpus)))
    state = (
        colors.green(t("cli.corpus_present"))
        if corpus.exists()
        else colors.red(t("cli.corpus_missing"))
    )
    summary = t(
        "cli.corpus_summary",
        state=state,
        count=len(service_state.units),
        as_of=_date(as_of) if as_of else t("cli.unknown"),
    )
    print(_wrap(summary))
    units_per_act: dict[str, int] = {}
    for unit in service_state.units:
        units_per_act[unit.legal_act.value] = units_per_act.get(unit.legal_act.value, 0) + 1
    for act_name, unit_count in sorted(units_per_act.items()):
        print(_wrap("%-12s %5d" % (act_name, unit_count), indent="    "))


def _print_index_status(colors: Colors, service_state: ServiceState) -> None:
    from compliance_helper.search.store import METADATA_SUFFIX, VECTORS_SUFFIX, index_path

    search_index_path = index_path(current_language())
    _print_heading(colors, t("cli.heading_search_index"))
    files = t(
        "cli.index_files",
        vectors=search_index_path.name + VECTORS_SUFFIX,
        meta=search_index_path.name + METADATA_SUFFIX,
    )
    print(_wrap(files))
    print(_wrap(t("cli.directory", path=search_index_path.parent)))
    source = (
        colors.green(t("cli.index_from_file"))
        if service_state.index_from_file
        else colors.orange(t("cli.index_in_memory"))
    )
    print(_wrap(t("cli.index_summary", source=source, model=service_state.embedding_model)))


def _print_rule_set_status(colors: Colors) -> None:
    from compliance_helper.classification.assessor import rule_set

    rules = rule_set()
    _print_heading(colors, t("cli.heading_rule_set"))
    print(_wrap(t("cli.directory", path=paths.rules_dir())))
    summary = t(
        "cli.rule_set_summary",
        as_of=_date(rules.as_of) if rules.as_of else t("cli.unknown"),
        obligations=len(rules.obligations),
        sections=len(rules.data_protection),
    )
    print(_wrap(summary))


def command_status(args: argparse.Namespace) -> int:
    """Report corpus, search index, rule set and LLM availability, plus any warnings."""
    from compliance_helper.corpus.build import corpus_file
    from compliance_helper.service.app import load_service_state

    language = current_language()
    corpus = corpus_file(language)
    service_state = load_service_state(languages=(language,))
    if args.json:
        print(_status_as_json(service_state, corpus))
        return 0

    colors = args.colors
    _print_corpus_status(colors, service_state, corpus)
    _print_index_status(colors, service_state)
    _print_rule_set_status(colors)
    _print_heading(colors, t("cli.heading_llm"))
    print(_wrap(service_state.llm_name))
    if service_state.warnings:
        _print_heading(colors, t("cli.heading_warnings"))
        for warning in service_state.warnings:
            print(_wrap(colors.orange("! ") + warning))
    else:
        print()
        print(_wrap(colors.green(t("cli.all_present")), indent=""))
    return 0


def command_build_corpus(args: argparse.Namespace) -> int:
    """Build the corpus of ``--language`` from the raw sources; refuse when they are missing."""
    from compliance_helper.corpus import build

    language = Language(args.language)
    units, report = build.collect(language)
    for warning in report["warnings"]:
        logging.getLogger(build.__name__).warning("%s", warning)
    if not build.has_official_text(units):
        raise DataMissingError(
            t(
                "cli.corpus_without_sources",
                path=build.raw_dir(language),
                command=build.fetch_command(language),
            )
        )
    if report["warnings"]:
        _print_notices(args.colors, [t("cli.corpus_warnings", count=len(report["warnings"]))])
    if args.check:
        print(t("cli.corpus_checked", language_name=_language_name(language), count=len(units)))
        return 0
    corpus, corpus_report = build.corpus_file(language), build.report_file(language)
    if args.output_dir:
        corpus, corpus_report = args.output_dir / corpus.name, args.output_dir / corpus_report.name
    build.write(units, report, corpus, corpus_report)
    print(
        t(
            "cli.corpus_written",
            language_name=_language_name(language),
            count=len(units),
            path=corpus,
        )
    )
    return 0


def command_build_index(args: argparse.Namespace) -> int:
    """Embed the corpus of ``--language`` and store the search index next to it."""
    from compliance_helper.corpus import index_build

    language = Language(args.language)
    handler = index_build.attach_log_file(language)
    try:
        result = index_build.build_index(
            language, model=args.model, fallback=args.fallback, from_scratch=args.from_scratch
        )
    except index_build.ModelMissingError as error:
        raise DataMissingError(t("cli.index_model_missing", model=str(error))) from error
    finally:
        logging.getLogger("compliance_helper").removeHandler(handler)
        handler.close()
    print(
        t(
            "cli.index_written",
            language_name=_language_name(language),
            count=result.units,
            model=result.model,
            seconds=round(result.seconds),
            path=result.index_path.parent,
        )
    )
    print(t("cli.build_log", path=index_build.log_file(language)))
    return 0


def _add_common_options(target: argparse.ArgumentParser) -> None:
    """Register the options every command accepts, before or after the command name."""
    target.add_argument("-h", "--help", action="help", help=t("cli.help_help"))
    target.add_argument("--no-color", action="store_true", help=t("cli.help_no_color"))
    target.add_argument("--json", action="store_true", help=t("cli.help_json"))
    target.add_argument("--verbose", action="store_true", help=t("cli.help_verbose"))
    target.add_argument(
        "--lang", choices=[language.value for language in Language], help=t("cli.help_lang")
    )


def _add_search_options(target: argparse.ArgumentParser, maximum_count: int) -> None:
    target.add_argument(
        "--count",
        type=bounded_count(maximum_count),
        default=8,
        metavar="N",
        help=t("cli.help_count", maximum=maximum_count),
    )
    target.add_argument("--legal-act", action="append", metavar="ACT", help=t("cli.help_legal_act"))


def _add_build_language(target: argparse.ArgumentParser) -> None:
    target.add_argument(
        "--language",
        choices=[language.value for language in Language],
        default=Language.DE.value,
        help=t("cli.help_build_language"),
    )


def _add_query_commands(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
    common: list[argparse.ArgumentParser],
) -> None:
    classify = commands.add_parser("classify", help=t("cli.help_classify"), **_sub(common))
    classify.add_argument("description", help=t("cli.help_system_description"))
    classify.add_argument("--role", action="append", metavar="ROLE", help=t("cli.help_role"))
    classify.set_defaults(run=command_classify)

    ask = commands.add_parser("ask", help=t("cli.help_ask"), **_sub(common))
    ask.add_argument("question", help=t("cli.help_question"))
    ask.add_argument("--description", default="", help=t("cli.help_system_description"))
    ask.add_argument("--role", action="append", metavar="ROLE", help=t("cli.help_role"))
    ask.add_argument("--model", choices=MODEL_CHOICES, default=None, help=t("cli.help_model"))
    _add_search_options(ask, MAX_ASK_COUNT)
    ask.add_argument("--show-wording", action="store_true", help=t("cli.help_show_wording"))
    ask.set_defaults(run=command_ask)

    search = commands.add_parser("search", help=t("cli.help_search"), **_sub(common))
    search.add_argument("query", help=t("cli.help_query"))
    _add_search_options(search, MAX_SEARCH_COUNT)
    search.add_argument("--brief", action="store_true", help=t("cli.help_brief"))
    search.set_defaults(run=command_search)


def _add_operation_commands(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
    common: list[argparse.ArgumentParser],
) -> None:
    serve = commands.add_parser("serve", help=t("cli.help_serve"), **_sub(common))
    serve.add_argument(
        "--address",
        default=os.environ.get("COMPLIANCE_HELPER_HOST", "127.0.0.1"),
        help=t("cli.help_address"),
    )
    serve.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("COMPLIANCE_HELPER_PORT", "8000")),
        help=t("cli.help_port"),
    )
    serve.add_argument("--reload", action="store_true", help=t("cli.help_reload"))
    serve.set_defaults(run=command_serve)

    status = commands.add_parser("status", help=t("cli.help_status"), **_sub(common))
    status.set_defaults(run=command_status)

    corpus = commands.add_parser("build-corpus", help=t("cli.help_build_corpus"), **_sub(common))
    _add_build_language(corpus)
    corpus.add_argument("--check", action="store_true", help=t("cli.help_check"))
    corpus.add_argument("--output-dir", type=Path, help=t("cli.help_output_dir"))
    corpus.set_defaults(run=command_build_corpus)

    index = commands.add_parser("build-index", help=t("cli.help_build_index"), **_sub(common))
    _add_build_language(index)
    index.add_argument("--model", default=None, help=t("cli.help_index_model"))
    index.add_argument("--fallback", action="store_true", help=t("cli.help_fallback"))
    index.add_argument("--from-scratch", action="store_true", help=t("cli.help_from_scratch"))
    index.set_defaults(run=command_build_index)


def _sub(common: list[argparse.ArgumentParser]) -> dict[str, Any]:
    """Keyword arguments shared by every subcommand parser."""
    return {"parents": common, "add_help": False, "allow_abbrev": False}


def build_parser() -> argparse.ArgumentParser:
    """Build the parser with help texts in the active language; commands stay English."""
    parser = argparse.ArgumentParser(
        prog="compliance-helper",
        description=t("cli.description"),
        epilog=t("cli.epilog"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        allow_abbrev=False,
    )
    # Registered on the main parser and on every subcommand, because argparse rejects an
    # option placed after the subcommand otherwise.
    _add_common_options(parser)
    common = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    _add_common_options(common)
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    _add_query_commands(commands, [common])
    _add_operation_commands(commands, [common])
    return parser


def require_data(command: str) -> None:
    """Refuse a command that needs the data directory when it is not there.

    Raises:
        DataMissingError: Naming the directory searched and how to point the tool elsewhere.
    """
    if command in COMMANDS_WITHOUT_DATA or paths.rules_dir().is_dir():
        return
    raise DataMissingError(t("cli.data_missing", path=paths.data_dir(), variable=ROOT_VARIABLE))


def _rule_file_error() -> type[Exception]:
    """The assessor's error for unusable rule files, imported only when an error propagates."""
    from compliance_helper.classification.assessor import RuleFileError

    return RuleFileError


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    with use_language(requested_language(arguments)):
        try:
            return _run(arguments)
        except BrokenPipeError:
            # The reader (e.g. "| head") is gone; drop the rest of the output silently.
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            return 0
        finally:
            logging.captureWarnings(False)


def _run(arguments: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    if not getattr(args, "run", None):
        parser.print_help()
        return 1

    # The subcommand's default overrides the main parser's value, so "--json status"
    # would lose --json; re-read the raw arguments.
    for flag in ("json", "no_color", "verbose"):
        if f"--{flag.replace('_', '-')}" in arguments:
            setattr(args, flag, True)
    args.colors = choose_colors(args.no_color)
    configure_logging(args.verbose, args.command)
    try:
        require_data(args.command)
        return int(args.run(args))
    except InputError as error:
        print(args.colors.red(t("cli.error_input")) + str(error), file=sys.stderr)
        return 2
    except DataMissingError as error:
        print(args.colors.red(t("cli.error_data_missing")) + str(error), file=sys.stderr)
        return 3
    except FileNotFoundError as error:
        print(args.colors.red(t("cli.error_missing_file")) + str(error), file=sys.stderr)
        return 3
    except BrokenPipeError:
        raise
    except OSError as error:
        logging.getLogger(__name__).error("%s", error)
        message = t("cli.file_access", path=error.filename or paths.data_dir())
        print(args.colors.red(t("cli.error_data_missing")) + message, file=sys.stderr)
        return 3
    except _rule_file_error() as error:
        logging.getLogger(__name__).error("%s", error)
        message = t("cli.rules_unusable", path=paths.rules_dir())
        print(args.colors.red(t("cli.error_data_missing")) + message, file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print()
        print(t("cli.cancelled"), file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
