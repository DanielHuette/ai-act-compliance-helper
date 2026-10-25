"""Citation route of the search: provisions a question names, as corpus unit ids.

Context: a question naming "Art. 9 Abs. 2" or "Article 6(3)" must get exactly that provision, not
the most similar text; unit ids are language-neutral, so German and English citation forms map to
the same ids | Input: a question in German or English | Output: candidate unit ids, most specific
first per citation.
"""

from __future__ import annotations

import re

from compliance_helper.domain import LegalAct

_ARTICLE = r"Art(?:ikel|icle)?\.?"
_LETTER_WORD = r"(?:Buchst(?:abe)?\.?|lit\.?|point|letter)"

#: Matches "Art. 6 Abs. 3", "Art. 5 Abs. 1 lit. f", "Artikel 9", "§ 26 BDSG", "Anhang III Nr. 4",
#: "Erwägungsgrund 60" and the English forms "Article 6(3)(a)", "Article 5(1), point (f)",
#: "point (f) of Article 5(1)", "Section 26 BDSG", "Annex III point 4(a)" and "recital 60".
_CITATION_PATTERN = re.compile(
    r"(?:\bpoint\s*\((?P<lead_letter>[a-z])\)\s*of\s+" + _ARTICLE + r"\s*"
    r"(?P<lead_article_no>\d{1,3})\s*\((?P<lead_paragraph>\d{1,2})\)"
    r"|\b" + _ARTICLE + r"\s*(?P<article_no>\d{1,3})"
    r"(?:\s*(?:Abs(?:atz)?\.?|para(?:graph)?\.?)\s*(?P<paragraph_no>\d{1,2})"
    r"|\s*\((?P<paragraph_paren>\d{1,2})\))?"
    r"(?:,?\s*" + _LETTER_WORD + r"\s*\(?(?P<letter>[a-z])\b\)?"
    r"|\s*\((?P<letter_paren>[a-z])\))?"
    r"|(?P<section_sign>§)\s*(?P<section_no>\d{1,3}[a-z]?)"
    r"|\b(?P<section_word>Section)\s+(?P<section_word_no>\d{1,3}[a-z]?)"
    r"|\b(?P<annex>Anhang|Annex)\s*(?P<annex_no>[IVXLC]+)\b"
    r"(?:\s*(?:Nr\.?|Nummer|point)\s*(?P<annex_point>\d{1,2})"
    r"(?:\s*\((?P<annex_letter>[a-z])\))?)?"
    r"|\b(?P<recital>Erw(?:ägungsgrund|aegungsgrund|G)?\.?|Recital)\s*(?P<recital_no>\d{1,3}))",
    re.IGNORECASE,
)

_ACT_HINTS = (
    (LegalAct.BDSG, ("bdsg", "bundesdatenschutz", "federal data protection")),
    (LegalAct.GDPR, ("dsgvo", "datenschutz-grundverordnung", "gdpr", "general data protection")),
    (
        LegalAct.AI_ACT,
        (
            "ki-vo",
            "ki-verordnung",
            "ai act",
            "ai-act",
            "kuenstliche intelligenz",
            "künstliche intelligenz",
            "artificial intelligence act",
        ),
    ),
)


def _named_acts(question: str) -> list[LegalAct]:
    """The legal act the question names; without a hint the AI Act and the GDPR both qualify."""
    folded = question.lower()
    for act, hints in _ACT_HINTS:
        if any(hint in folded for hint in hints):
            return [act]
    return [LegalAct.AI_ACT, LegalAct.GDPR]


def _first_named_act(text: str) -> LegalAct | None:
    """The legal act named first in ``text``, or None if it names none."""
    folded = text.lower()
    found = [
        (position, act)
        for act, hints in _ACT_HINTS
        for hint in hints
        if (position := folded.find(hint)) >= 0
    ]
    return min(found, key=lambda pair: pair[0])[1] if found else None


def _acts_per_citation(question: str, matches: list[re.Match[str]]) -> list[list[LegalAct]]:
    """The act of each citation: the first one named before the next citation, else the question's.

    "Article 6 AI Act and Article 35 GDPR" cites two acts; one guess for the whole question would
    look for Article 6 in the GDPR.
    """
    question_acts = _named_acts(question)
    ends = [match.start() for match in matches[1:]] + [len(question)]
    acts: list[list[LegalAct]] = []
    for match, end in zip(matches, ends, strict=False):
        following = _first_named_act(question[match.end() : end])
        acts.append([following] if following else question_acts)
    return acts


def _article_ids(
    article: str, paragraph: str | None, letter: str | None, acts: list[LegalAct]
) -> list[str]:
    position = ""
    if paragraph:
        position = f"/para-{paragraph}" + (f"-{letter.lower()}" if letter else "")
    return [f"{act.value}/art-{article}{position}" for act in acts]


def _annex_id(number: str, point: str | None, letter: str | None) -> str:
    unit_id = f"{LegalAct.AI_ACT.value}/annex-{number.upper()}"
    if point:
        unit_id += f"/pt-{point}" + (f"-{letter.lower()}" if letter else "")
    return unit_id


def _ids_for_match(parts: dict[str, str | None], acts: list[LegalAct]) -> list[str]:
    if parts["lead_article_no"]:
        return _article_ids(
            parts["lead_article_no"], parts["lead_paragraph"], parts["lead_letter"], acts
        )
    if parts["article_no"]:
        paragraph = parts["paragraph_no"] or parts["paragraph_paren"]
        letter = parts["letter"] or parts["letter_paren"]
        return _article_ids(parts["article_no"], paragraph, letter, acts)
    if parts["section_no"]:
        return [f"{LegalAct.BDSG.value}/sec-{parts['section_no']}"]
    if parts["section_word_no"] and acts == [LegalAct.BDSG]:
        return [f"{LegalAct.BDSG.value}/sec-{parts['section_word_no'].lower()}"]
    if parts["annex_no"]:
        return [_annex_id(parts["annex_no"], parts["annex_point"], parts["annex_letter"])]
    if parts["recital_no"]:
        return [f"{act.value}/recital-{parts['recital_no']}" for act in acts]
    return []


def citations_from_question(question: str) -> list[str]:
    """Translate citations named in a question into corpus unit ids.

    The legal act of each citation is the one named right after it, else the one the question
    names; without any hint, ids for both the AI Act and the GDPR are returned and the search
    keeps those that exist.
    """
    matches = list(_CITATION_PATTERN.finditer(question))
    ids: list[str] = []
    for match, acts in zip(matches, _acts_per_citation(question, matches), strict=True):
        ids.extend(_ids_for_match(match.groupdict(), acts))
    return ids
