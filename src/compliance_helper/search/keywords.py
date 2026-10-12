"""Keyword route of the search: tokenization per language and a BM25 index.

Context: questions that name a term of the law ("CE marking", "Folgenabschätzung") need exact word
matches, which vector search blurs; filler words are removed per language because they occur in
every legal text | Input: index texts and questions, the language of the index | Output: tokens
and BM25-ranked positions of the index texts.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from compliance_helper.i18n import DEFAULT_LANGUAGE, Language

RESULTS_PER_ROUTE = 50

_UMLAUTS = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"))
_WORD_PATTERN = re.compile(r"[a-z0-9]+")
_COMPOUND_PATTERN = re.compile(r"[a-z]+(?:-[a-z]+)+")


def fold_text(text: str) -> str:
    """Lowercase and transliterate umlauts and accents to ASCII for keyword matching."""
    text = text.lower()
    for umlaut, transliteration in _UMLAUTS:
        text = text.replace(umlaut, transliteration)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _folded_words(words: str) -> frozenset[str]:
    return frozenset(fold_text(word) for word in words.split())


STOPWORDS = {
    Language.DE: _folded_words(
        "aber alle allem allen aller alles als also am an ander andere anderem anderen anderer "
        "anderes auch auf aus bei beim bin bis bist da damit dann das dass dein deine dem den der "
        "des deshalb dessen die dies diese diesem diesen dieser dieses doch dort du durch ein eine "
        "einem einen einer eines er es euch euer für gegen gewesen hab habe haben hat hatte hatten "
        "hier hin hinter ich ihr ihre ihrem ihren ihrer ihres im in indem ins ist ja jede jedem "
        "jeden jeder jedes jene jener kann kein keine keinem keinen keiner man mehr mein meine mit "
        "nach nicht nichts noch nun nur ob oder ohne sämtliche sein seine seinem seinen seiner "
        "sich sie sind so solche solchem solchen soll sollen sondern sonst über um und uns unser "
        "unsere unter vom von vor während war waren was weil welche welchem welchen welcher "
        "welches wenn wer werde werden wie wieder will wir wird wirst wo wollen wurde wurden zu "
        "zum zur zwar zwischen"
    ),
    Language.EN: _folded_words(
        "a about above after again against all also am an and any are as at be because been "
        "before being below between both but by can could did do does doing down during each "
        "either few for from further had has have having he her here hers herself him himself his "
        "how i if in into is it its itself just may me might more most must my myself neither no "
        "nor not now of off on once only or other our ours ourselves out over own same shall she "
        "should so some such than that the their theirs them themselves then there these they "
        "this those through to too under until up upon very was we were what when where whether "
        "which while who whom whose why will with within without would you your yours yourself"
    ),
}


def _english_stem(word: str) -> str:
    """Reduce English plurals to the singular, so "employees" matches "employee"."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def _normalize(word: str, language: Language) -> str:
    return _english_stem(word) if language is Language.EN else word


def tokenize(text: str, language: Language = DEFAULT_LANGUAGE) -> list[str]:
    """Split text into keyword tokens of ``language`` without its stopwords.

    Hyphenated compounds ("Hochrisiko-KI-System", "high-risk") are emitted as their parts once
    more, so a query for "Risiko" weighs them like a standalone word.
    """
    folded = fold_text(text)
    stopwords = STOPWORDS[language]
    words = [
        _normalize(token, language)
        for token in _WORD_PATTERN.findall(folded)
        if len(token) >= 2 and token not in stopwords
    ]
    for compound in _COMPOUND_PATTERN.findall(folded):
        words.extend(
            _normalize(part, language)
            for part in compound.split("-")
            if len(part) > 2 and part not in stopwords
        )
    return words


@dataclass
class KeywordIndex:
    """BM25 keyword index without third-party dependencies.

    The length normalisation matters: without it the long articles always win.
    """

    language: Language = DEFAULT_LANGUAGE
    k1: float = 1.5
    b: float = 0.75
    term_freqs: list[dict[str, int]] = field(default_factory=list)
    doc_lengths: list[int] = field(default_factory=list)
    postings: dict[str, list[int]] = field(default_factory=dict)
    avg_doc_length: float = 0.0
    doc_count: int = 0

    def build(self, texts: list[str]) -> None:
        positions: dict[str, list[int]] = defaultdict(list)
        self.term_freqs = []
        self.doc_lengths = []
        for number, text in enumerate(texts):
            words = tokenize(text, self.language)
            counter = dict(Counter(words))
            self.term_freqs.append(counter)
            self.doc_lengths.append(len(words))
            for word in counter:
                positions[word].append(number)
        self.postings = dict(positions)
        self.doc_count = len(texts)
        self.avg_doc_length = sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0

    def search(self, question: str, count: int = RESULTS_PER_ROUTE) -> list[tuple[int, float]]:
        words = set(tokenize(question, self.language))
        if not words or not self.doc_count:
            return []
        scores: dict[int, float] = defaultdict(float)
        for word in words:
            positions = self.postings.get(word)
            if positions:
                self._add_scores(word, positions, scores)
        return sorted(scores.items(), key=lambda item: -item[1])[:count]

    def _add_scores(self, word: str, positions: list[int], scores: dict[int, float]) -> None:
        rarity = math.log(1 + (self.doc_count - len(positions) + 0.5) / (len(positions) + 0.5))
        for number in positions:
            term_freq = self.term_freqs[number][word]
            relative_length = (self.doc_lengths[number] or 1) / self.avg_doc_length
            saturation = term_freq + self.k1 * (1 - self.b + self.b * relative_length)
            scores[number] += rarity * term_freq * (self.k1 + 1) / saturation

    def to_dict(self) -> dict[str, Any]:
        return {
            "term_freqs": self.term_freqs,
            "doc_lengths": self.doc_lengths,
            "postings": self.postings,
            "avg_doc_length": self.avg_doc_length,
            "count": self.doc_count,
        }

    @classmethod
    def from_dict(cls, stored: dict[str, Any], language: Language) -> KeywordIndex:
        return cls(
            language=language,
            term_freqs=stored["term_freqs"],
            doc_lengths=stored["doc_lengths"],
            postings=stored["postings"],
            avg_doc_length=stored["avg_doc_length"],
            doc_count=stored["count"],
        )
