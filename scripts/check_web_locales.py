"""Check the German and English catalogs of the static web page.

Context: web/index.html keeps German as the no-JavaScript fallback and page.js swaps every
marked text for the catalog entry of the chosen language, so catalogs, markup and script must
name the same keys. | Input: web/locales/de.json, web/locales/en.json, web/index.html,
web/page.js (folder set by --web) | Output: one line per problem; exit code 1 if any.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("de", "en")
SOURCE_LANGUAGE = "de"
VOID_ELEMENTS = frozenset({"meta", "link", "img", "br", "hr", "input", "source", "wbr"})
STRUCTURED_DATA_TEXT_FIELDS = frozenset({"name", "text", "description"})
PLACEHOLDER = re.compile(r"\{(\w+)\}")
QUOTED_KEY = re.compile(r'"([a-zA-Z]+(?:\.\w+)+)"')
TEMPLATE_KEY = re.compile(r"`([a-zA-Z]\w*\.(?:\w|\.|\$\{\w+\})+)`")
TEMPLATE_FIELD = re.compile(r"(\$\{\w+\})")


@dataclass
class MarkedText:
    key: str
    tag: str
    text: list[str] = field(default_factory=list)
    has_child_element: bool = False


@dataclass
class MarkedAttribute:
    key: str
    attribute: str
    value: str | None


@dataclass
class PageMarkup:
    texts: list[MarkedText] = field(default_factory=list)
    attributes: list[MarkedAttribute] = field(default_factory=list)
    structured_data: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


class MarkupScanner(HTMLParser):
    """Collect data-i18n texts, data-i18n-attr values and the JSON-LD block of a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = PageMarkup()
        self._stack: list[MarkedText | None] = []
        self._in_structured_data = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for entry in self._stack:
            if entry is not None:
                entry.has_child_element = True
        for pair in (values.get("data-i18n-attr") or "").split(";"):
            attribute, _, attribute_key = (part.strip() for part in pair.partition(":"))
            if attribute and attribute_key:
                self.page.attributes.append(
                    MarkedAttribute(attribute_key, attribute, values.get(attribute))
                )
        key = values.get("data-i18n")
        if tag in VOID_ELEMENTS:
            if key:
                self.page.problems.append(f"<{tag} data-i18n={key!r}> cannot hold text")
            return
        entry = MarkedText(key, tag) if key else None
        if entry is not None:
            self.page.texts.append(entry)
        self._stack.append(entry)
        self._in_structured_data = tag == "script" and values.get("type") == "application/ld+json"

    def handle_endtag(self, tag: str) -> None:
        if tag not in VOID_ELEMENTS and self._stack:
            self._stack.pop()
        self._in_structured_data = False

    def handle_data(self, data: str) -> None:
        if self._in_structured_data:
            self.page.structured_data.append(data)
        for entry in self._stack:
            if entry is not None:
                entry.text.append(data)


def normalized(text: str) -> str:
    return " ".join(text.split())


def load_catalog(path: Path) -> dict[str, str]:
    catalog: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return catalog


def scan_markup(path: Path) -> PageMarkup:
    scanner = MarkupScanner()
    scanner.feed(path.read_text(encoding="utf-8"))
    scanner.close()
    return scanner.page


def catalog_problems(catalogs: dict[str, dict[str, str]]) -> list[str]:
    """Same keys in every language, no empty texts, the same {placeholders} per key."""
    problems: list[str] = []
    source = catalogs[SOURCE_LANGUAGE]
    for language, catalog in catalogs.items():
        problems += [
            f"{language}: {key!r} has no text" for key, text in catalog.items() if not text
        ]
        if language == SOURCE_LANGUAGE:
            continue
        problems += [
            f"{language}: {key!r} missing" for key in sorted(source.keys() - catalog.keys())
        ]
        problems += [
            f"{language}: {key!r} not in {SOURCE_LANGUAGE}"
            for key in sorted(catalog.keys() - source.keys())
        ]
        for key in sorted(source.keys() & catalog.keys()):
            expected = set(PLACEHOLDER.findall(source[key]))
            found = set(PLACEHOLDER.findall(catalog[key]))
            if expected != found:
                problems.append(
                    f"{language}: {key!r} has {sorted(found)}, expected {sorted(expected)}"
                )
    return problems


def markup_problems(page: PageMarkup, source: dict[str, str]) -> list[str]:
    """Every marked key exists, and the German fallback in the HTML matches the catalog."""
    problems = list(page.problems)
    for entry in page.texts:
        if entry.key not in source:
            problems.append(f"index.html: data-i18n {entry.key!r} not in the catalog")
        elif entry.has_child_element:
            problems.append(f"index.html: data-i18n {entry.key!r} wraps markup; mark the text only")
        elif normalized("".join(entry.text)) != normalized(source[entry.key]):
            problems.append(f"index.html: fallback text of {entry.key!r} differs from de.json")
    for marked in page.attributes:
        if marked.key not in source:
            problems.append(f"index.html: data-i18n-attr {marked.key!r} not in the catalog")
        elif normalized(marked.value or "") != normalized(source[marked.key]):
            problems.append(
                f"index.html: {marked.attribute} of {marked.key!r} differs from de.json"
            )
    return problems


def structured_data_texts(node: object, parent_type: str = "") -> list[str]:
    if isinstance(node, list):
        return [text for item in node for text in structured_data_texts(item, parent_type)]
    if not isinstance(node, dict):
        return []
    node_type = str(node.get("@type", parent_type))
    texts: list[str] = []
    for key, value in node.items():
        if key == "featureList":
            texts += [str(item) for item in value]
        elif key in STRUCTURED_DATA_TEXT_FIELDS and isinstance(value, str):
            if node_type != "Person":
                texts.append(value)
        else:
            texts += structured_data_texts(value, node_type)
    return texts


def structured_data_problems(page: PageMarkup, source: dict[str, str]) -> list[str]:
    """The static German JSON-LD must say what page.js rebuilds from the catalog."""
    if not page.structured_data:
        return []
    known = {normalized(text) for text in source.values()}
    data = json.loads("".join(page.structured_data))
    return [
        f"index.html: JSON-LD text not in de.json: {text[:60]!r}"
        for text in structured_data_texts(data)
        if normalized(text) not in known
    ]


def script_problems(script: Path, source: dict[str, str]) -> list[str]:
    """Every key literal in page.js exists; every template key matches at least one key."""
    code = script.read_text(encoding="utf-8")
    prefixes = {key.split(".")[0] for key in source}
    problems = [
        f"{script.name}: key {key!r} not in the catalog"
        for key in sorted(set(QUOTED_KEY.findall(code)))
        if key.split(".")[0] in prefixes and key not in source
    ]
    for template in sorted(set(TEMPLATE_KEY.findall(code))):
        pattern = re.compile(
            "".join(
                r"\w+" if part.startswith("${") else re.escape(part)
                for part in TEMPLATE_FIELD.split(template)
            )
        )
        if not any(pattern.fullmatch(key) for key in source):
            problems.append(f"{script.name}: template key {template!r} matches no catalog key")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", type=Path, default=ROOT / "web")
    args = parser.parse_args(argv)

    catalogs = {
        language: load_catalog(args.web / "locales" / f"{language}.json") for language in LANGUAGES
    }
    source = catalogs[SOURCE_LANGUAGE]
    page = scan_markup(args.web / "index.html")
    problems = (
        catalog_problems(catalogs)
        + markup_problems(page, source)
        + structured_data_problems(page, source)
        + script_problems(args.web / "page.js", source)
    )
    for problem in problems:
        print(problem)
    print(
        f"{len(source)} keys, {len(page.texts)} texts and {len(page.attributes)} attributes "
        f"marked, {len(problems)} problems."
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
