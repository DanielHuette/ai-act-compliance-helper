"""Find message catalog keys that no code, template, page or rule file refers to.

Context: a key that nothing reads still has to be translated and reviewed, and it hides which
texts the tool really shows. Keys built at run time count as used: f-strings and template
literals (``f"domain.risk_class_label_{value}"``, ``t(`faq.${n}.question`)``) become patterns,
a quoted prefix that is concatenated (``"badge_" + id``) covers every key it starts, and so does
a quoted namespace prefix (``"ld.feature."``, ``"domain.position_"``). Keys under ``webui.js.``
are read by app.js without that prefix. | Input: the catalogs under
src/compliance_helper/locales and web/locales, the sources that read them | Output: one line per
unused key; exit code 1 if there is any.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_CATALOGS = Path("src/compliance_helper/locales")
WEB_CATALOGS = Path("web/locales")
SCRIPT_TEXTS_PREFIX = "webui.js."

PACKAGE_READERS = (
    "src/compliance_helper/**/*.py",
    "src/compliance_helper/**/*.html",
    "src/compliance_helper/**/*.js",
    "packaging/*.py",
    "scripts/*.py",
    "data/rules/**/*.yaml",
)
WEB_READERS = ("web/*.js", "web/*.html")

PYTHON_FORMATTED = re.compile(r"""\bf(["'])((?:(?!\1).)*\{(?:(?!\1).)*)\1""")
PYTHON_FIELD = re.compile(r"\{[^{}]*\}")
TEMPLATE_LITERAL = re.compile(r"`([^`]*\$\{[^`]*)`")
TEMPLATE_FIELD = re.compile(r"\$\{[^{}]*\}")
CONCATENATED_PREFIX = re.compile(r"""(["'])([A-Za-z][\w.]*[._])\1\s*\+""")
NAMESPACE_PREFIX = re.compile(r"""(["'])([A-Za-z]\w*\.[\w.]*[._])\1""")
KEY_CHARACTERS = r"[\w.-]+"


@dataclass(frozen=True)
class References:
    """What a group of source files says about catalog keys."""

    text: str
    patterns: tuple[re.Pattern[str], ...]
    prefixes: tuple[str, ...]

    def mention(self, key: str) -> bool:
        if re.search(rf"(?<![\w.]){re.escape(key)}(?![\w.])", self.text):
            return True
        if any(key.startswith(prefix) for prefix in self.prefixes):
            return True
        return any(pattern.fullmatch(key) for pattern in self.patterns)


def _pattern(template: str, field: re.Pattern[str]) -> re.Pattern[str] | None:
    """Turn a formatted string into a key pattern; one without a namespace matches nothing."""
    literal_head = field.split(template, maxsplit=1)[0]
    if "." not in literal_head and "_" not in literal_head:
        return None
    parts = field.split(template)
    return re.compile(KEY_CHARACTERS.join(re.escape(part) for part in parts))


def _patterns(text: str) -> tuple[re.Pattern[str], ...]:
    found = [_pattern(match.group(2), PYTHON_FIELD) for match in PYTHON_FORMATTED.finditer(text)]
    found += [_pattern(match.group(1), TEMPLATE_FIELD) for match in TEMPLATE_LITERAL.finditer(text)]
    return tuple(pattern for pattern in found if pattern is not None)


def read_references(root: Path, globs: Iterable[str]) -> References:
    files = sorted({path for pattern in globs for path in root.glob(pattern) if path.is_file()})
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    prefixes = tuple(
        {match.group(2) for match in CONCATENATED_PREFIX.finditer(text)}
        | {match.group(2) for match in NAMESPACE_PREFIX.finditer(text)} - {SCRIPT_TEXTS_PREFIX}
    )
    return References(text=text, patterns=_patterns(text), prefixes=prefixes)


def package_keys(root: Path) -> set[str]:
    """Keys of the package catalogs, prefixed with their file name as ``t()`` expects them."""
    keys: set[str] = set()
    for catalog in (root / PACKAGE_CATALOGS).glob("*/*.json"):
        content = json.loads(catalog.read_text(encoding="utf-8"))
        keys.update(f"{catalog.stem}.{key}" for key in content)
    return keys


def web_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    for catalog in (root / WEB_CATALOGS).glob("*.json"):
        keys.update(json.loads(catalog.read_text(encoding="utf-8")))
    return keys


def _package_key_used(key: str, references: References) -> bool:
    if references.mention(key):
        return True
    return key.startswith(SCRIPT_TEXTS_PREFIX) and references.mention(
        key.removeprefix(SCRIPT_TEXTS_PREFIX)
    )


def unused_keys(root: Path = ROOT) -> list[str]:
    """Return every catalog key nothing refers to, as ``<catalog folder>: <key>``."""
    package_references = read_references(root, PACKAGE_READERS)
    web_references = read_references(root, WEB_READERS)
    unused = [
        f"{PACKAGE_CATALOGS}: {key}"
        for key in sorted(package_keys(root))
        if not _package_key_used(key, package_references)
    ]
    unused += [
        f"{WEB_CATALOGS}: {key}"
        for key in sorted(web_keys(root))
        if not web_references.mention(key)
    ]
    return unused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="source tree to check")
    found = unused_keys(parser.parse_args(argv).root)
    for line in found:
        print(f"unused: {line}")
    print(f"{len(found)} unused catalog keys.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
