"""The CLI in English: ``--lang en`` and ``COMPLIANCE_HELPER_LANG`` switch every text it owns.

Context: commands, options and JSON keys stay identical in both languages; headings, help texts,
errors and the disclaimer follow the chosen language. | Input: CLI arguments with ``--lang`` or
the environment variable, fallback embedder | Output: pass when English output carries no German
text of the CLI catalog.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from compliance_helper.cli import main
from compliance_helper.i18n import Language, catalog

GERMAN_ONLY = {
    key: text
    for key, text in catalog(Language.DE).items()
    if key.startswith("cli.") and text != catalog(Language.EN)[key] and "{" not in text
}
HELP_TEXTS = [
    " ".join(text.split())
    for key, text in GERMAN_ONLY.items()
    if key.startswith("cli.help_") or key in ("cli.description", "cli.epilog")
]


@pytest.fixture(autouse=True)
def fallback_model(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_HELPER_EMBEDDING", "fallback")
    monkeypatch.setenv("COMPLIANCE_HELPER_REQUESTS_PER_MINUTE", "1000")
    monkeypatch.delenv("COMPLIANCE_HELPER_LANG", raising=False)


def _run(*cli_args: str) -> tuple[int, str, str]:
    """Run the CLI in-process and capture stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            exit_code = main(list(cli_args))
        except SystemExit as stop:
            exit_code = int(stop.code or 0)
    return exit_code, out.getvalue(), err.getvalue()


def _lines(output: str) -> set[str]:
    return {line.strip() for line in output.splitlines()}


@pytest.mark.parametrize(
    "command",
    [
        (),
        ("classify",),
        ("ask",),
        ("search",),
        ("serve",),
        ("status",),
        ("build-corpus",),
        ("build-index",),
    ],
)
def test_help_is_english_without_german_help_texts(command):
    exit_code, output, _ = _run("--lang", "en", *command, "--help")
    assert exit_code == 0
    flowing = " ".join(output.split())
    assert "show this help message and exit" in flowing
    leftovers = [text for text in HELP_TEXTS if text in flowing]
    assert not leftovers


def test_command_and_option_names_are_identical_in_both_languages():
    _, german, _ = _run("--help")
    _, english, _ = _run("--lang", "en", "--help")
    for name in (
        "classify",
        "ask",
        "search",
        "serve",
        "status",
        "build-corpus",
        "build-index",
        "--json",
        "--no-color",
        "--verbose",
        "--lang",
    ):
        assert name in german
        assert name in english


def test_classify_in_english_shows_english_frame():
    exit_code, output, _ = _run(
        "--lang", "en", "classify", "Wir sortieren Bewerbungen mit einem Sprachmodell vor."
    )
    assert exit_code == 0
    lines = _lines(output)
    assert {"Classification", "Why"} <= lines
    assert any(line.startswith("To do under the AI Act (") for line in lines)
    assert "Not legal advice." in output
    assert not {GERMAN_ONLY[key] for key in GERMAN_ONLY if key.startswith("cli.heading_")} & lines
    assert "Keine Rechtsberatung." not in output


def test_language_option_after_the_command_is_honoured():
    _, output, _ = _run("classify", "--lang", "en", "Wir sortieren Bewerbungen vor.")
    assert "Classification" in _lines(output)


def test_environment_variable_sets_the_default_and_option_overrides_it(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_HELPER_LANG", "en")
    _, english, _ = _run("classify", "Wir sortieren Bewerbungen vor.")
    _, german, _ = _run("--lang", "de", "classify", "Wir sortieren Bewerbungen vor.")
    assert "Classification" in _lines(english)
    assert "Einstufung" in _lines(german)


def test_status_in_english_has_english_headings():
    exit_code, output, _ = _run("--lang", "en", "status")
    assert exit_code == 0
    lines = _lines(output)
    assert {"Legal texts", "Search index", "Rule set", "Wording"} <= lines
    assert not {"Rechtstexte", "Suchbestand", "Regelsatz", "Formulierung"} & lines


def test_json_keys_do_not_depend_on_the_language():
    _, german, _ = _run("--json", "status")
    _, english, _ = _run("--json", "--lang", "en", "status")
    assert set(json.loads(german)) == set(json.loads(english))


def test_ask_in_english_frames_the_answer_in_english():
    exit_code, output, _ = _run(
        "--lang",
        "en",
        "ask",
        "Was müssen wir beachten?",
        "--description",
        "Wir setzen ein Sprachmodell ein, um Bewerbungen vorzusortieren.",
        "--model",
        "none",
    )
    assert exit_code == 0
    lines = _lines(output)
    assert "Classification" in lines
    assert any(line.startswith("Citations (") for line in lines)
    assert "Compiled from the rule set without a language model." in output
    assert "Einstufung" not in lines


def test_input_errors_are_reported_in_english():
    exit_code, _, error = _run("--lang", "en", "classify", "x", "--role", "owner")
    assert exit_code == 2
    assert "Input not usable: The tool does not know the role 'owner'." in error
    assert "Eingabe nicht brauchbar" not in error


def test_unknown_language_is_rejected():
    exit_code, _, error = _run("--lang", "fr", "status")
    assert exit_code == 2
    assert "invalid choice" in error


def test_status_reports_the_date_of_the_english_corpus():
    """The English corpus has its own date; "as of unknown" hid it."""
    from compliance_helper.corpus.build import load

    expected = max(unit.as_of for unit in load(Language.EN) if unit.as_of)
    _, output, _ = _run("--json", "--lang", "en", "status")
    assert json.loads(output)["corpus_as_of"] == expected.isoformat()
    _, text, _ = _run("--lang", "en", "status")
    assert f"as of {expected.isoformat()}" in text
