"""German and English text for everything the user reads.

Context: Code never holds user-facing text; it asks this module for a message key or picks
the right side of a bilingual data field, in the language active for the current request; input
text is matched only with the vocabulary of the language it is written in. | Input: message
catalogs in ``locales/<language>/*.json``, bilingual data values ``{"de": ..., "en": ...}`` and
user descriptions | Output: text in the active language, a description's languages and the
vocabulary items of those languages.
"""

from __future__ import annotations

import json
import re
import string
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum
from functools import cache, lru_cache
from importlib import resources
from typing import Any


class Language(StrEnum):
    """Supported languages; German is the default and the language of the legal sources."""

    DE = "de"
    EN = "en"

    @classmethod
    def parse(cls, value: str | None) -> Language:
        """Return the language for a code such as ``en``, ``en-GB`` or ``EN``; default German."""
        code = (value or "").strip().lower()[:2]
        return cls(code) if code in cls._value2member_map_ else DEFAULT_LANGUAGE

    @classmethod
    def from_accept_language(cls, header: str | None, default: Language | None = None) -> Language:
        """Return the supported language an HTTP ``Accept-Language`` header weights highest.

        Entries rank by their ``q`` value (1 when absent), equal weights keep header order and
        ``q=0`` excludes a language. ``default`` (German if omitted) answers when none fits.
        """
        ranked = sorted(_weighted_language_codes(header), key=lambda entry: -entry[1])
        for code, weight in ranked:
            if weight > 0 and code in cls._value2member_map_:
                return cls(code)
        return default or DEFAULT_LANGUAGE


def _weighted_language_codes(header: str | None) -> list[tuple[str, float]]:
    """Split an ``Accept-Language`` header into ``(two-letter code, q)`` pairs in header order."""
    entries: list[tuple[str, float]] = []
    for part in (header or "").split(","):
        code, *parameters = (piece.strip() for piece in part.split(";"))
        weight = 1.0
        for parameter in parameters:
            name, _, value = parameter.partition("=")
            if name.strip().lower() == "q":
                try:
                    weight = float(value)
                except ValueError:
                    weight = 0.0
        if code:
            entries.append((code.lower()[:2], weight))
    return entries


DEFAULT_LANGUAGE = Language.DE

_active: ContextVar[Language] = ContextVar("language", default=DEFAULT_LANGUAGE)


class MissingTranslationError(KeyError):
    """A message key is not in the catalog of the requested language."""


def current_language() -> Language:
    return _active.get()


@contextmanager
def use_language(language: Language) -> Iterator[Language]:
    """Make ``language`` active for the enclosed block (per request, per CLI call)."""
    token = _active.set(language)
    try:
        yield language
    finally:
        _active.reset(token)


@cache
def catalog(language: Language) -> Mapping[str, str]:
    """Merge all catalog files of one language into one flat ``key -> text`` mapping."""
    merged: dict[str, str] = {}
    folder = resources.files("compliance_helper") / "locales" / language.value
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(".json"):
            continue
        area = entry.name.removesuffix(".json")
        for key, text in json.loads(entry.read_text(encoding="utf-8")).items():
            merged[f"{area}.{key}"] = text
    return merged


def t(key: str, /, language: Language | None = None, **values: Any) -> str:
    """Return the message ``key`` in the active language, formatted with ``values``."""
    chosen = language or current_language()
    try:
        template = catalog(chosen)[key]
    except KeyError as error:
        raise MissingTranslationError(f"{key!r} missing for {chosen.value}") from error
    return template.format(**values) if values else template


def pick(value: Any, language: Language | None = None) -> Any:
    """Return the active-language side of a bilingual ``{"de": ..., "en": ...}`` value.

    Plain values pass through unchanged, so callers need not know which fields of a data file
    are bilingual. A missing translation falls back to German, the authoritative text.
    """
    if isinstance(value, Mapping) and DEFAULT_LANGUAGE.value in value:
        chosen = (language or current_language()).value
        return value.get(chosen) or value[DEFAULT_LANGUAGE.value]
    return value


def vocabulary(value: Any, languages: Iterable[Language]) -> list[Any]:
    """Return the items of a ``{"de": [...], "en": [...]}`` vocabulary in ``languages``.

    German items come first, duplicates are dropped; a plain list belongs to no language and is
    returned whole.
    """
    if isinstance(value, Mapping) and DEFAULT_LANGUAGE.value in value:
        wanted = frozenset(languages)
        merged: list[Any] = []
        for language in Language:
            if language in wanted:
                merged.extend(value.get(language.value) or [])
        return list(dict.fromkeys(merged))
    return list(value or [])


def all_languages(value: Any) -> list[Any]:
    """Return the items of a vocabulary in every language, German first."""
    return vocabulary(value, Language)


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


#: Frequent function words per language, none shared between them.
_FUNCTION_WORDS = {
    Language.DE: _words(
        "der die das den dem des und oder nicht wir unser unsere unseren ein eine einen einem "
        "ist sind wird werden mit für fuer von zu auf bei aus nach über ueber dass ob wer was "
        "wie sie es sich auch kein keine im zum zur"
    ),
    Language.EN: _words(
        "the and or not we our ours a is are be will with for of to on at from by that which "
        "who what how it its they their this these into do does can"
    ),
}

#: Share of function words one language needs before the other language is left out; below it
#: the description counts as mixed.
LANGUAGE_DECISION_SHARE = 0.75


@lru_cache(maxsize=64)
def description_languages(description: str) -> frozenset[Language]:
    """Return the languages a description is written in, judged by its function words.

    A clear majority picks one language; short, mixed or unknown text keeps both. A description is
    matched only with the vocabulary and purpose sentences of these languages, because stems
    cross languages by accident (German "note" in "notes", English "migration" in a data
    migration). Measured on the English company questions: own language 97 of 100, both
    languages 95 of 100 in twice the time.
    """
    words = re.findall(r"[a-zäöüß]+", description.lower())
    counts = {
        language: sum(word in function_words for word in words)
        for language, function_words in _FUNCTION_WORDS.items()
    }
    total = sum(counts.values())
    if total:
        for language, count in counts.items():
            if count / total >= LANGUAGE_DECISION_SHARE:
                return frozenset({language})
    return frozenset(Language)


def placeholders(template: str) -> set[str]:
    """Return the ``{name}`` fields of a catalog text; used to check both languages match."""
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}
