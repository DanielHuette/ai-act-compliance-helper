"""Parse the BDSG and the article-by-article regulation fallback files into units.

Context: the BDSG and its official English translation come from gesetze-im-internet.de and are
parsed via their HTML structure; article-wise JSON files substitute for a missing official full
text after stripping page boilerplate | Input: bdsg.html (German or English) and per-article JSON
files | Output: corpus units.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from compliance_helper.corpus.eurlex import Selection
from compliance_helper.domain import LegalAct, Unit, UnitKind

BDSG_SOURCE_URL = "https://www.gesetze-im-internet.de/bdsg_2018/BJNR209710017.html"
BDSG_TRANSLATION_URL = "https://www.gesetze-im-internet.de/englisch_bdsg/englisch_bdsg.html"
BDSG_TRANSLATOR = "translation by the Language Service of the Federal Ministry of the Interior"

_TRANSLATION_VERSION = re.compile(r"Version information:\s*The English translation (.+?\))\.")
_TRANSLATION_SECTION = re.compile(r"^Section (\d+[a-z]?)$")

#: Everything from the first of these markers on is page boilerplate, not legal text.
_BOILERPLATE_MARKERS = (
    "Passende Erwägungsgründe",
    "Passende Paragraphen des BDSG",
    "Passende Paragrafen des BDSG",
    "Erwägungsgründe zu Art",
    "Fehler melden",
    "Inhaltsverzeichnis",
    "Diese Website verwendet",
    "Wir verwenden Cookies",
)

#: Trailing navigation lines such as "← Art. 21 DSGVO".
_NAVIGATION_LINE = re.compile(
    r"(?m)^\s*(?:←|→|«|»)?\s*Art\.?\s*\d{1,3}\s*(?:DSGVO|GDPR)?\s*(?:←|→|«|»)?\s*$"
)

_PARAGRAPH_PATTERN = re.compile(r"(?m)^\s*\((\d{1,2})\)\s+")


def _clean(text: str) -> str:
    text = text.replace(" ", " ").replace("‑", "-").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def strip_boilerplate(text: str) -> str:
    """Remove page boilerplate and navigation lines that follow the legal text."""
    cut_at = len(text)
    for marker in _BOILERPLATE_MARKERS:
        position = text.find(marker)
        if 0 <= position < cut_at:
            cut_at = position
    text = text[:cut_at]
    text = _NAVIGATION_LINE.sub("", text)
    # Lone bracketed numbers are reference numbers from the source site's recital list.
    text = re.sub(r"(?m)^\s*\(\s*\d{1,3}\s*\)\s*$", "", text)
    text = re.sub(r"(?m)^\s*(?:DSGVO|BDSG|GDPR)\s*$", "", text)
    return _clean(text)


def _paragraphs_from_text(text: str, longer_than: int = 25) -> list[tuple[str, str]]:
    """Split legal text into paragraphs at the "(1)" numbering."""
    matches = list(_PARAGRAPH_PATTERN.finditer(text))
    if not matches:
        return []
    chunks: list[tuple[str, str]] = []
    for number, start in enumerate(matches):
        end = matches[number + 1].start() if number + 1 < len(matches) else len(text)
        content = _clean(text[start.end() : end])
        if len(content) > longer_than:
            chunks.append((start.group(1), content))
    return chunks


def parse_bdsg(path: Path) -> list[Unit]:
    """Parse the BDSG page into section and paragraph units; missing file yields none."""
    if not path.exists():
        return []
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    as_of = date.fromtimestamp(path.stat().st_mtime)

    units: list[Unit] = []
    part = ""
    chapter = ""
    for div in soup.select("div.jnnorm"):
        designation = div.select_one(".jnenbez")
        title_node = div.select_one(".jnentitel")
        content: Tag | None = div.select_one(".jnhtml")

        # Structural headings ("Teil 2", "Kapitel 1") carry no legal text, only context.
        raw_designation = _clean(designation.get_text(" ", strip=True)) if designation else ""
        raw_title = _clean(title_node.get_text(" ", strip=True)) if title_node else ""
        if raw_designation.startswith("Teil"):
            part = (f"{raw_designation} {raw_title}").strip()
            continue
        if raw_designation.startswith(("Kapitel", "Abschnitt", "Unterabschnitt")):
            chapter = (f"{raw_designation} {raw_title}").strip()
            continue

        number_match = re.match(r"^§\s*(\d+[a-z]?)$", raw_designation)
        if not number_match or content is None:
            continue
        number = number_match.group(1)

        paragraph_nodes = content.select("div.jurAbsatz")
        if paragraph_nodes:
            raw = "\n\n".join(_clean(node.get_text(" ", strip=True)) for node in paragraph_nodes)
        else:
            raw = _clean(content.get_text("\n"))
        raw = _clean(raw)
        if len(raw) < 40:
            continue

        units.append(
            Unit(
                id=f"BDSG/sec-{number}",
                legal_act=LegalAct.BDSG,
                kind=UnitKind.SECTION,
                number=number,
                paragraph=None,
                title=raw_title,
                chapter=part,
                section_title=chapter,
                text=raw,
                source=BDSG_SOURCE_URL,
                as_of=as_of,
            )
        )

        for paragraph_id, text in _paragraphs_from_text(raw):
            units.append(
                Unit(
                    id=f"BDSG/sec-{number}/para-{paragraph_id}",
                    legal_act=LegalAct.BDSG,
                    kind=UnitKind.SECTION,
                    number=number,
                    paragraph=paragraph_id,
                    title=raw_title,
                    chapter=part,
                    section_title=chapter,
                    text=text,
                    source=BDSG_SOURCE_URL,
                    as_of=as_of,
                )
            )
    return units


def _is_translation_heading(paragraph: Tag) -> bool:
    style = str(paragraph.get("style", ""))
    return "text-align: center" in style and "font-weight: bold" in style


def _translation_sections(soup: BeautifulSoup) -> list[tuple[str, str, str]]:
    """Return (number, title, text) per section of the English BDSG page.

    The page is flat: a centred bold heading "Section 26<br/>Title" is followed by one ``<p>`` per
    paragraph, list item and continuation line. Lines without a "(n)" number continue the current
    paragraph, so a section reads like its German counterpart: one paragraph per "(n)".
    """
    sections: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    for paragraph in soup.find_all("p"):
        if _is_translation_heading(paragraph):
            lines = [_clean(line) for line in paragraph.stripped_strings]
            match = _TRANSLATION_SECTION.match(lines[0]) if lines else None
            current = (match.group(1), " ".join(lines[1:]), []) if match else None
            if current is not None:
                sections.append(current)
            continue
        text = _clean(paragraph.get_text(" ", strip=True))
        if current is None or not text or text == "table of contents":
            continue
        lines_so_far = current[2]
        if lines_so_far and not _PARAGRAPH_PATTERN.match(text):
            lines_so_far[-1] = f"{lines_so_far[-1]} {text}"
        else:
            lines_so_far.append(text)
    return [(number, title, _clean("\n\n".join(lines))) for number, title, lines in sections]


def parse_bdsg_translation(path: Path, reference_ids: frozenset[str] | None = None) -> list[Unit]:
    """Parse the official English BDSG translation into section and paragraph units.

    Args:
        path: The saved page ``englisch_bdsg.html``; a missing file yields no units.
        reference_ids: Ids of the German corpus to reproduce; without them, minimum text
            lengths decide as for the German page.

    Returns:
        Units with the ids of the German BDSG units, each naming the translation as its source.
    """
    if not path.exists():
        return []
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    version = _TRANSLATION_VERSION.search(_clean(soup.get_text(" ")))
    source = f"{BDSG_TRANSLATION_URL} ({BDSG_TRANSLATOR}"
    source += f"; {version.group(1)})" if version else ")"
    selection = Selection(reference_ids)
    as_of = date.fromtimestamp(path.stat().st_mtime)

    units: list[Unit] = []
    for number, title, text in _translation_sections(soup):
        section_id = f"BDSG/sec-{number}"
        if not selection.keeps(section_id, text, 39):
            continue
        units.append(
            Unit(
                id=section_id,
                legal_act=LegalAct.BDSG,
                kind=UnitKind.SECTION,
                number=number,
                paragraph=None,
                title=title,
                text=text,
                source=source,
                as_of=as_of,
            )
        )
        for paragraph_id, paragraph_text in _paragraphs_from_text(text, longer_than=0):
            unit_id = f"{section_id}/para-{paragraph_id}"
            if not selection.keeps(unit_id, paragraph_text, 25):
                continue
            units.append(
                Unit(
                    id=unit_id,
                    legal_act=LegalAct.BDSG,
                    kind=UnitKind.SECTION,
                    number=number,
                    paragraph=paragraph_id,
                    title=title,
                    text=paragraph_text,
                    source=source,
                    as_of=as_of,
                )
            )
    return units


def article_files(directory: Path, legal_act: LegalAct) -> list[Unit]:
    """Read article-by-article JSON files into cleaned article, paragraph and letter units."""
    units: list[Unit] = []
    if not directory.exists():
        return units

    for file in sorted(directory.rglob("*.json")):
        if file.name.startswith("_") or file.name == "table_of_contents.json":
            continue
        try:
            record = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        text = strip_boilerplate(record.get("text", ""))
        if len(text) < 40:
            continue

        unit_kind = record.get("unit", "article")
        kind = {
            "article": UnitKind.ARTICLE,
            "annex": UnitKind.ANNEX,
            "recital": UnitKind.RECITAL,
        }.get(unit_kind, UnitKind.ARTICLE)
        stem = {"article": "art", "annex": "annex", "recital": "recital"}[unit_kind]
        number = str(record["number"])
        as_of = date.fromtimestamp(file.stat().st_mtime)
        title = _clean(record.get("title", ""))

        units.append(
            Unit(
                id=f"{legal_act.value}/{stem}-{number}",
                legal_act=legal_act,
                kind=kind,
                number=number,
                paragraph=None,
                title=title,
                chapter=_clean(record.get("chapter", "")),
                section_title=_clean(record.get("section_title", "")),
                text=text,
                source=record.get("source", ""),
                as_of=as_of,
            )
        )

        if kind is not UnitKind.ARTICLE:
            continue

        structured = record.get("paragraphs") or []
        if structured:
            for paragraph in structured:
                paragraph_id = str(paragraph.get("number", "")).strip()
                paragraph_text = _clean(paragraph.get("text", ""))
                if not paragraph_id or len(paragraph_text) < 25:
                    continue
                units.append(
                    Unit(
                        id=f"{legal_act.value}/art-{number}/para-{paragraph_id}",
                        legal_act=legal_act,
                        kind=UnitKind.ARTICLE,
                        number=number,
                        paragraph=paragraph_id,
                        title=title,
                        chapter=_clean(record.get("chapter", "")),
                        section_title=_clean(record.get("section_title", "")),
                        text=paragraph_text,
                        source=record.get("source", ""),
                        as_of=as_of,
                    )
                )
                for letter_entry in paragraph.get("letters", []):
                    letter = str(letter_entry.get("letter", "")).strip()
                    content = _clean(letter_entry.get("text", ""))
                    if not letter or len(content) < 25:
                        continue
                    units.append(
                        Unit(
                            id=f"{legal_act.value}/art-{number}/para-{paragraph_id}-{letter}",
                            legal_act=legal_act,
                            kind=UnitKind.ARTICLE,
                            number=number,
                            paragraph=f"{paragraph_id} Buchstabe {letter}",
                            title=title,
                            text=content,
                            source=record.get("source", ""),
                            as_of=as_of,
                        )
                    )
            continue

        for paragraph_id, paragraph_text in _paragraphs_from_text(text):
            units.append(
                Unit(
                    id=f"{legal_act.value}/art-{number}/para-{paragraph_id}",
                    legal_act=legal_act,
                    kind=UnitKind.ARTICLE,
                    number=number,
                    paragraph=paragraph_id,
                    title=title,
                    text=paragraph_text,
                    source=record.get("source", ""),
                    as_of=as_of,
                )
            )
    return units
