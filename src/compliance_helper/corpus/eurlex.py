"""Parse an official EUR-Lex full text into citable units.

Context: answers must cite article, paragraph, letter and annex point, so parsing follows the
document's id anchors instead of text patterns and checks the expected unit counts; every language
version carries the same anchors, so German and English yield the same ids | Input: EUR-Lex XHTML
of the AI Act or the GDPR in German or English | Output: a ParsedDocument with units, counts and
issues.
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import date
from itertools import pairwise
from pathlib import Path

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

from compliance_helper.domain import LegalAct, Unit, UnitKind
from compliance_helper.i18n import Language

# EUR-Lex XHTML carries an XML declaration, but lxml's HTML parser reads it reliably.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

EXPECTED_COUNTS: dict[LegalAct, dict[str, int]] = {
    LegalAct.AI_ACT: {"article": 113, "annex": 13, "recital": 180},
    LegalAct.GDPR: {"article": 99, "annex": 0, "recital": 173},
}

#: Paragraph container ids look like "006.003" (article 6, paragraph 3).
_PARAGRAPH_ID_PATTERN = re.compile(r"^(\d{3})\.(\d{3})$")
_LEADING_NUMBERING = re.compile(r"^\(?(\d{1,2})\)?\.?\s+")
_LETTER_PATTERN = re.compile(r"^\(?([a-z])\)\s+")


@dataclass
class ParsedDocument:
    """Parsed units with per-kind counts and parser issues."""

    units: list[Unit] = field(default_factory=list)
    report: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Selection:
    """Decide which candidate passages become units.

    German defines the unit set by minimum text lengths. A translation is shorter or longer
    by a few words, which would add or drop short items such as "(b) the free movement;",
    so it keeps exactly the ids of the German corpus instead.
    """

    reference_ids: frozenset[str] | None = None

    def keeps(self, unit_id: str, text: str, longer_than: int) -> bool:
        if self.reference_ids is None:
            return len(text) > longer_than
        return unit_id in self.reference_ids


_BY_LENGTH = Selection()


#: Annex group headings restart the numbering below them, so the group becomes part of
#: the id: AI-Act/annex-VIII/pt-A-1 instead of three times AI-Act/annex-VIII/pt-1.
_ANNEX_GROUP_HEADING = re.compile(
    r"^(?:(?:Abschnitt|Section)\s+([A-Z]|\d{1,2})\b|(\d{1,2})\.\s+\S)"
)

#: Labels the parser writes into unit fields; the structured ``paragraph`` values stay neutral.
_RECITAL_TITLE = {Language.DE: "Erwägungsgrund {}", Language.EN: "Recital {}"}
_CHAPTER_FALLBACK = {Language.DE: "Kapitel ", Language.EN: "Chapter "}


def _element_id(node: Tag | None) -> str:
    """Return a node's id as a string, joining list values.

    BeautifulSoup may return attribute values as lists; an unhandled list id
    would silently skip the whole article.
    """
    if node is None:
        return ""
    value = node.get("id")
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return " ".join(str(part) for part in value)


def _clean(text: str) -> str:
    """Normalise EUR-Lex whitespace and hyphens into plain running text.

    Non-breaking spaces between "Artikel" and its number would otherwise break
    keyword search for "Artikel 6".
    """
    text = text.replace(" ", " ").replace("‑", "-").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _text_of(node: Tag) -> str:
    return _clean(node.get_text(" ", strip=True))


def _numbering(text: str) -> str:
    """Return the bare marker of a list numbering: German "1." and "a)", English "(1)" and "(a)"."""
    return _clean(text).lstrip("(").rstrip(".)")


def _without_numbering(text: str, numbering: str) -> str:
    return re.sub(rf"^\(?{re.escape(numbering)}[.)]\s*", "", text).strip()


def _chapter_and_section(node: Tag, language: Language) -> tuple[str, str]:
    """Chapter and section heading enclosing a node, resolved via ancestor anchors."""
    chapter = section_title = ""
    ancestor = node.parent
    while ancestor is not None and getattr(ancestor, "name", None):
        key = _element_id(ancestor)
        if re.match(r"^cpt_[IVXLC]+$", key) and not chapter:
            title = ancestor.find(class_=["oj-ti-section-1", "oj-ti-section-2"])
            chapter = _text_of(title) if title else key.replace("cpt_", _CHAPTER_FALLBACK[language])
        elif re.match(r"^cpt_[IVXLC]+\.sct_\d+$", key) and not section_title:
            title = ancestor.find(class_="oj-ti-grseq-1")
            section_title = _text_of(title) if title else key.split(".")[-1]
        ancestor = ancestor.parent
    return chapter, section_title


def _article_paragraphs(div: Tag, number: str = "") -> list[tuple[str, str, Tag | None]]:
    """Return an article's paragraphs as (paragraph number, text, container).

    Without paragraph containers the whole article becomes paragraph "1"; its
    container is kept only if it holds a letter list (e.g. Article 16).

    Args:
        div: The ``div#art_N`` element.
        number: Article number; containers of other articles are skipped, because
            Articles 107 and 108 quote foreign acts with those acts' paragraph ids.

    Returns:
        One tuple per paragraph; the container is ``None`` if it has no letters.
    """
    found: list[tuple[str, str, Tag | None]] = []
    for child in div.find_all("div", recursive=False):
        match = _PARAGRAPH_ID_PATTERN.match(_element_id(child))
        if not match:
            continue
        if number and str(int(match.group(1))) != str(number):
            continue
        text = _text_of(child)
        paragraph_number = str(int(match.group(2)))
        numbering = _LEADING_NUMBERING.match(text)
        if numbering and numbering.group(1) == paragraph_number:
            text = text[numbering.end() :].strip()
        if text:
            found.append((paragraph_number, text, child))
    if found:
        return found

    parts = []
    for paragraph in div.find_all("p", class_="oj-normal"):
        text = _text_of(paragraph)
        if text:
            parts.append(text)
    if not parts:
        return []
    has_letters = any(
        re.fullmatch(r"[a-z]", _numbering_and_cell(table)[0])
        for table in div.find_all("table", recursive=False)
        if table.find_all("tr") and table.find_all("tr")[0].find_all(["td", "th"])
    )
    return [("1", "\n\n".join(parts), div if has_letters else None)]


def _definitions(div: Tag, prefix: str, selection: Selection) -> list[tuple[str, str]]:
    """Return the numbered terms of a definitions article as (point, text).

    Article 3 AI Act (68 terms) and Article 4 GDPR (26 terms) have no
    paragraphs; each term is a table with its number in the first cell.
    """
    chunks: list[tuple[str, str]] = []
    for table in div.find_all("table", recursive=False):
        lines = table.find_all("tr")
        if not lines:
            continue
        cells = lines[0].find_all(["td", "th"])
        if len(cells) < 2:
            continue
        numbering = _numbering(cells[0].get_text(" ", strip=True))
        if not re.fullmatch(r"\d{1,3}", numbering):
            continue
        content = _without_numbering(_clean(table.get_text(" ", strip=True)), numbering)
        if selection.keeps(f"{prefix}{numbering}", content, 30):
            chunks.append((numbering, content))
    return chunks


def _numbering_and_cell(table: Tag) -> tuple[str, Tag | None]:
    """Return a list item's numbering and the text cell that follows it.

    Leading empty cells carry indentation and are skipped; Annex I has its
    numbering in the second cell and would otherwise be lost entirely.
    """
    lines = table.find_all("tr")
    if not lines:
        return "", None
    cells = lines[0].find_all(["td", "th"])
    for cell, following_cell in pairwise(cells):
        numbering = _numbering(cell.get_text(" ", strip=True))
        if numbering:
            return numbering, following_cell
    return "", None


def _letters(div: Tag, prefix: str, selection: Selection) -> list[tuple[str, str, str]]:
    """Return a paragraph's letter items as (id marker, position, text) from the table structure.

    Parsing running text confused nested "i)" lists with letter i (Article 5(1)(c))
    and merged lists across paragraphs (Article 43). A restarted numbering within
    one paragraph marks a second subparagraph: id marker ``sub2-a``, position ``ua2-a``.
    """
    chunks: list[tuple[str, str, str]] = []
    subparagraph = 1
    for table in div.find_all("table", recursive=False):
        numbering, _cell = _numbering_and_cell(table)
        if not re.fullmatch(r"[a-z]", numbering):
            continue
        content = _without_numbering(_clean(table.get_text(" ", strip=True)), numbering)
        restarted = any(marker == numbering for marker, _, _ in chunks)
        candidate = subparagraph + 1 if restarted else subparagraph
        marker, position = numbering, numbering
        if candidate > 1:
            marker, position = f"sub{candidate:d}-{numbering}", f"ua{candidate:d}-{numbering}"
        if not selection.keeps(f"{prefix}{marker}", content, 40):
            continue
        subparagraph = candidate
        chunks.append((marker, position, content))
    return chunks


def _annex_subpoints(
    cell: Tag, marker: str, prefix: str, selection: Selection
) -> list[tuple[str, str]]:
    """Recursively return the letter and roman sub-points nested in an annex point's text cell.

    Classification hinges on these sub-points, e.g. Annex III point 4(a) versus 4(b).
    """
    chunks: list[tuple[str, str]] = []
    for table in cell.find_all("table", recursive=False):
        numbering, text_cell = _numbering_and_cell(table)
        if text_cell is None or not re.fullmatch(r"[a-z]|[ivxlc]+", numbering):
            continue
        content = _without_numbering(_clean(table.get_text(" ", strip=True)), numbering)
        if not selection.keeps(f"{prefix}{marker}-{numbering}", content, 40):
            continue
        chunks.append((f"{marker}-{numbering}", content))
        chunks.extend(_annex_subpoints(text_cell, f"{marker}-{numbering}", prefix, selection))
    return chunks


def _annex_points(div: Tag, prefix: str, selection: Selection) -> list[tuple[str, str]]:
    """Return an annex's numbered points as (marker, text), including nested sub-points.

    Paragraphs and tables are walked in document order so that section headings
    prefix the markers: Annexes VIII and X restart numbering per section and
    would otherwise lose two thirds of their points on deduplication. Without
    tables, the running text is split by its numbering.
    """
    chunks: list[tuple[str, str]] = []
    section_title = ""
    for child in div.find_all(["p", "table"], recursive=False):
        if child.name == "p":
            css_classes: list[str] = list(child.get("class") or [])
            if any(str(css_class).startswith("oj-ti-grseq") for css_class in css_classes):
                header = _clean(child.get_text(" ", strip=True))
                match = _ANNEX_GROUP_HEADING.match(header)
                # Subheadings must not reset the section: Annex XI has one below "Abschnitt 1".
                if match:
                    section_title = match.group(1) or match.group(2)
            continue

        table = child
        numbering, text_cell = _numbering_and_cell(table)
        if text_cell is None or not re.fullmatch(r"\d{1,2}|[a-z]|[ivxlc]+|[A-Z]", numbering):
            continue
        content = _without_numbering(_clean(table.get_text(" ", strip=True)), numbering)
        marker = f"{section_title}-{numbering}" if section_title else numbering
        if selection.keeps(f"{prefix}{marker}", content, 60):
            chunks.append((marker, content))
        chunks.extend(_annex_subpoints(text_cell, marker, prefix, selection))

    if chunks:
        return chunks

    text = _text_of(div)
    parts = re.split(r"(?m)^\s*(\d{1,2})\.\s+", text)
    for position in range(1, len(parts) - 1, 2):
        number, content = parts[position], _clean(parts[position + 1])
        if selection.keeps(f"{prefix}{number}", content, 60):
            chunks.append((number, content))
    return chunks


def parse(
    html: str,
    legal_act: LegalAct,
    source: str = "",
    as_of: date | None = None,
    language: Language = Language.DE,
    reference_ids: Collection[str] | None = None,
) -> ParsedDocument:
    """Parse a EUR-Lex full text into article, paragraph, letter, annex and recital units.

    Args:
        html: The EUR-Lex XHTML document.
        legal_act: Legal act the document belongs to.
        source: Citation of the source, stored on every unit.
        as_of: Version date stored on every unit.
        language: Language of the document, for the recital and chapter labels.
        reference_ids: Ids of the German corpus that a translation must reproduce; without
            them, minimum text lengths decide (see ``Selection``).

    Returns:
        Deduplicated units, counts per kind, and issues for duplicates and
        deviations from ``EXPECTED_COUNTS``.
    """
    result = ParsedDocument()
    selection = Selection(frozenset(reference_ids)) if reference_ids is not None else _BY_LENGTH
    soup = BeautifulSoup(html, "lxml")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    for div in soup.find_all("div", id=re.compile(r"^art_\d+$")):
        number = _element_id(div).removeprefix("art_")
        title_node = div.find(class_="eli-title") or div.find(class_="oj-sti-art")
        title = _text_of(title_node) if title_node else ""
        chapter, section_title = _chapter_and_section(div, language)
        definitions = _definitions(div, f"{legal_act.value}/art-{number}/pt-", selection)
        if definitions:
            result.units.append(
                Unit(
                    id=f"{legal_act.value}/art-{number}",
                    legal_act=legal_act,
                    kind=UnitKind.ARTICLE,
                    number=number,
                    paragraph=None,
                    title=title,
                    chapter=chapter,
                    section_title=section_title,
                    text=_text_of(div),
                    source=source,
                    as_of=as_of,
                )
            )
            for count_value, content in definitions:
                result.units.append(
                    Unit(
                        id=f"{legal_act.value}/art-{number}/pt-{count_value}",
                        legal_act=legal_act,
                        kind=UnitKind.ARTICLE,
                        number=number,
                        paragraph=f"Nummer {count_value}",
                        title=title,
                        chapter=chapter,
                        section_title=section_title,
                        text=content,
                        source=source,
                        as_of=as_of,
                    )
                )
            result.report["definitions"] = result.report.get("definitions", 0) + len(definitions)
            continue

        paragraphs = _article_paragraphs(div, number)
        if not paragraphs:
            continue

        full_text = "\n\n".join(f"({key}) {text}" for key, text, _ in paragraphs)
        result.units.append(
            Unit(
                id=f"{legal_act.value}/art-{number}",
                legal_act=legal_act,
                kind=UnitKind.ARTICLE,
                number=number,
                paragraph=None,
                title=title,
                chapter=chapter,
                section_title=section_title,
                text=full_text,
                source=source,
                as_of=as_of,
            )
        )

        for key, text, container in paragraphs:
            if not selection.keeps(f"{legal_act.value}/art-{number}/para-{key}", text, 24):
                continue
            result.units.append(
                Unit(
                    id=f"{legal_act.value}/art-{number}/para-{key}",
                    legal_act=legal_act,
                    kind=UnitKind.ARTICLE,
                    number=number,
                    paragraph=key,
                    title=title,
                    chapter=chapter,
                    section_title=section_title,
                    text=text,
                    source=source,
                    as_of=as_of,
                )
            )
            letters = (
                _letters(container, f"{legal_act.value}/art-{number}/para-{key}-", selection)
                if container
                else []
            )
            for marker, position, content in letters:
                result.units.append(
                    Unit(
                        id=f"{legal_act.value}/art-{number}/para-{key}-{marker}",
                        legal_act=legal_act,
                        kind=UnitKind.ARTICLE,
                        number=number,
                        paragraph=f"{key} Buchstabe {position}",
                        title=title,
                        chapter=chapter,
                        section_title=section_title,
                        text=content,
                        source=source,
                        as_of=as_of,
                    )
                )

    for div in soup.find_all("div", id=re.compile(r"^anx_[IVXLC]+$")):
        number = _element_id(div).removeprefix("anx_")
        title_lines = div.find_all(class_="oj-doc-ti", limit=2)
        title = _text_of(title_lines[1]) if len(title_lines) > 1 else ""
        text = _text_of(div)
        if not selection.keeps(f"{legal_act.value}/annex-{number}", text, 59):
            continue
        result.units.append(
            Unit(
                id=f"{legal_act.value}/annex-{number}",
                legal_act=legal_act,
                kind=UnitKind.ANNEX,
                number=number,
                paragraph=None,
                title=title,
                text=text,
                source=source,
                as_of=as_of,
            )
        )
        for point, content in _annex_points(
            div, f"{legal_act.value}/annex-{number}/pt-", selection
        ):
            result.units.append(
                Unit(
                    id=f"{legal_act.value}/annex-{number}/pt-{point}",
                    legal_act=legal_act,
                    kind=UnitKind.ANNEX,
                    number=number,
                    paragraph=point,
                    title=title,
                    text=content,
                    source=source,
                    as_of=as_of,
                )
            )

    for node in soup.find_all(id=re.compile(r"^rct_\d+$")):
        number = _element_id(node).removeprefix("rct_")
        text = _text_of(node)
        numbering = re.match(rf"^\({re.escape(number)}\)\s*", text)
        if numbering:
            text = text[numbering.end() :].strip()
        if not selection.keeps(f"{legal_act.value}/recital-{number}", text, 39):
            continue
        result.units.append(
            Unit(
                id=f"{legal_act.value}/recital-{number}",
                legal_act=legal_act,
                kind=UnitKind.RECITAL,
                number=number,
                paragraph=None,
                title=_RECITAL_TITLE[language].format(number),
                text=text,
                source=source,
                as_of=as_of,
            )
        )

    # Duplicates are reported separately by whether their text differs: only identical
    # duplicates are harmless to drop.
    seen: dict[str, str] = {}
    deduplicated: list[Unit] = []
    identical: list[str] = []
    conflicting: list[str] = []
    for unit in result.units:
        before = seen.get(unit.id)
        if before is not None:
            (identical if before == unit.text else conflicting).append(unit.id)
            continue
        seen[unit.id] = unit.text
        deduplicated.append(unit)
    result.units = deduplicated
    if identical:
        result.issues.append(
            "%d identical duplicates skipped: %s"
            % (len(identical), ", ".join(sorted(set(identical))[:6]))
        )
    if conflicting:
        result.issues.append(
            "ATTENTION: %d duplicate ids WITH DIFFERING TEXT — content is lost "
            "here: %s" % (len(conflicting), ", ".join(sorted(set(conflicting))[:10]))
        )

    result.report = {
        "units": len(result.units),
        "article": sum(
            1 for unit in result.units if unit.kind is UnitKind.ARTICLE and unit.paragraph is None
        ),
        "paragraphs": sum(
            1
            for unit in result.units
            if unit.kind is UnitKind.ARTICLE and unit.paragraph is not None
        ),
        "annex": sum(
            1 for unit in result.units if unit.kind is UnitKind.ANNEX and unit.paragraph is None
        ),
        "annex_points": sum(
            1 for unit in result.units if unit.kind is UnitKind.ANNEX and unit.paragraph is not None
        ),
        "recital": sum(1 for unit in result.units if unit.kind is UnitKind.RECITAL),
    }
    for kind, expected in EXPECTED_COUNTS.get(legal_act, {}).items():
        actual = result.report.get(kind, 0)
        if expected and actual != expected:
            result.issues.append(f"{kind}: {actual:d} found, {expected:d} expected")
    return result


def from_file(
    path: Path,
    legal_act: LegalAct,
    source: str = "",
    language: Language = Language.DE,
    reference_ids: Collection[str] | None = None,
) -> ParsedDocument:
    """Parse a saved EUR-Lex file, dated by its modification time."""
    html = path.read_text(encoding="utf-8", errors="ignore")
    as_of = date.fromtimestamp(path.stat().st_mtime)
    return parse(
        html, legal_act, source=source, as_of=as_of, language=language, reference_ids=reference_ids
    )
