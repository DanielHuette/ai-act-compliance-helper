"""Language switching and catalog completeness.

Context: Every user-facing text exists in German and English with the same placeholders. |
Input: the message catalogs. | Output: pass/fail per key and language.
"""

from __future__ import annotations

import pytest

from compliance_helper.i18n import (
    DEFAULT_LANGUAGE,
    Language,
    MissingTranslationError,
    catalog,
    current_language,
    pick,
    placeholders,
    t,
    use_language,
)


def test_both_catalogs_have_the_same_keys():
    assert set(catalog(Language.DE)) == set(catalog(Language.EN))


@pytest.mark.parametrize("language", list(Language))
def test_no_catalog_text_is_empty(language):
    empty = [key for key, text in catalog(language).items() if not text.strip()]
    assert not empty


def test_placeholders_match_between_languages():
    german, english = catalog(Language.DE), catalog(Language.EN)
    mismatched = [key for key in german if placeholders(german[key]) != placeholders(english[key])]
    assert not mismatched


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("en", Language.EN),
        ("EN-gb", Language.EN),
        ("de-AT", Language.DE),
        ("fr", Language.DE),
        (None, Language.DE),
        ("", Language.DE),
    ],
)
def test_language_codes_are_parsed_leniently(raw, expected):
    assert Language.parse(raw) is expected


def test_accept_language_takes_the_first_supported_entry():
    assert Language.from_accept_language("fr-FR, en;q=0.8, de;q=0.5") is Language.EN
    assert Language.from_accept_language("fr, es") is DEFAULT_LANGUAGE


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("de;q=0.1, en;q=0.9", Language.EN),
        ("en;q=0.4, de-AT;q=0.6", Language.DE),
        ("de;q=0, en;q=0.2", Language.EN),
        ("de;q=0.5, en;q=0.5", Language.DE),
        ("en;q=abc, de;q=0.3", Language.DE),
    ],
)
def test_accept_language_respects_quality_values(header, expected):
    assert Language.from_accept_language(header) is expected


def test_accept_language_falls_back_to_the_given_default():
    assert Language.from_accept_language("fr, es", default=Language.EN) is Language.EN
    assert Language.from_accept_language(None, default=Language.EN) is Language.EN
    assert Language.from_accept_language("de", default=Language.EN) is Language.DE


def test_active_language_is_scoped_to_the_block():
    assert current_language() is DEFAULT_LANGUAGE
    with use_language(Language.EN):
        assert t("app.name") == "AI Act Compliance Helper"
    assert t("app.name") == "Konformitätshelfer"


def test_unknown_key_fails_loudly():
    with pytest.raises(MissingTranslationError):
        t("app.does_not_exist")


def test_pick_chooses_the_active_side_and_falls_back_to_german():
    bilingual = {"de": "Frage", "en": "Question"}
    assert pick(bilingual) == "Frage"
    assert pick(bilingual, Language.EN) == "Question"
    assert pick({"de": "Nur deutsch", "en": ""}, Language.EN) == "Nur deutsch"
    assert pick("plain") == "plain"


def test_vocabulary_merges_both_languages_without_duplicates():
    from compliance_helper.i18n import all_languages

    assert all_languages({"de": ["Bewerbung", "CV"], "en": ["application", "CV"]}) == [
        "Bewerbung",
        "CV",
        "application",
    ]
    assert all_languages(["Bewerbung"]) == ["Bewerbung"]
    assert all_languages(None) == []


def test_vocabulary_returns_only_the_requested_languages():
    from compliance_helper.i18n import vocabulary

    words = {"de": ["Bewerbung", "CV"], "en": ["application", "CV"]}
    assert vocabulary(words, {Language.EN}) == ["application", "CV"]
    assert vocabulary(words, {Language.DE}) == ["Bewerbung", "CV"]
    assert vocabulary(words, {Language.EN, Language.DE}) == ["Bewerbung", "CV", "application"]
    assert vocabulary(["Bewerbung"], {Language.EN}) == ["Bewerbung"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Wir sortieren Bewerbungen mit einem Sprachmodell vor.", {Language.DE}),
        ("We pre-sort job applications with a language model.", {Language.EN}),
        ("Recruiting-Tool", set(Language)),
        ("", set(Language)),
    ],
)
def test_description_languages_needs_a_clear_majority(text, expected):
    from compliance_helper.i18n import description_languages

    assert description_languages(text) == expected


def _unused_key_finder(root):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "find_unused_catalog_keys", root / "scripts" / "find_unused_catalog_keys.py"
    )
    assert spec is not None and spec.loader is not None
    finder = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = finder
    spec.loader.exec_module(finder)
    return finder


def test_every_catalog_key_is_read_somewhere(root):
    assert _unused_key_finder(root).unused_keys(root) == []


def test_unused_key_finder_recognises_keys_built_at_run_time(root, tmp_path):
    """Keys built with f-strings, template literals and prefixes count as used; others do not."""
    import json

    package = tmp_path / "src" / "compliance_helper"
    (package / "locales" / "de").mkdir(parents=True)
    (package / "locales" / "de" / "demo.json").write_text(
        json.dumps(dict.fromkeys(("label_high", "plain", "js.badge_a", "js.say", "unused"), "x")),
        encoding="utf-8",
    )
    (package / "module.py").write_text(
        'TEXT = t(f"demo.label_{level}") + t("demo.plain")\n', encoding="utf-8"
    )
    (package / "app.js").write_text('say("say"); UI.text["badge_" + id];\n', encoding="utf-8")
    (tmp_path / "web" / "locales").mkdir(parents=True)
    (tmp_path / "web" / "locales" / "de.json").write_text(
        json.dumps({"faq.1.question": "x", "ld.feature.1": "x", "gone": "x"}), encoding="utf-8"
    )
    (tmp_path / "web" / "page.js").write_text(
        't(`faq.${n}.question`); keys.filter((k) => k.startsWith("ld.feature."));\n',
        encoding="utf-8",
    )
    finder = _unused_key_finder(root)
    finder.SCRIPT_TEXTS_PREFIX = "demo.js."
    assert finder.unused_keys(tmp_path) == [
        "src/compliance_helper/locales: demo.unused",
        "web/locales: gone",
    ]
