"""Rule-based AI Act classification of a system description.

Context: classification must be reproducible and cite an article at every branch, so it is a
decision tree over ``data/rules`` with no language model involved | Input: a SystemDescription
and the rule files | Output: a Classification with risk classes, indicators, obligations,
data-protection sections and open questions.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

import yaml

from compliance_helper import paths
from compliance_helper.classification.purposes import PurposeMatch, PurposeMatcher
from compliance_helper.classification.purposes import purpose_matcher as shared_purpose_matcher
from compliance_helper.classification.vocabulary import (
    BIOMETRIC_CARRIERS,
    COMPUTE_MENTIONS,
    DEPLOYER_PHRASES,
    EXEMPTION_CASES,
    NO_DECISION_INFLUENCE,
    PROCURED,
    PROVIDER_PHRASES,
    SAFETY_OR_MEDICAL_EXEMPTION,
    TRAINING_ON_OWN_DATA,
    TRAIT_KEYWORDS,
)
from compliance_helper.domain import (
    Classification,
    Obligation,
    RiskClass,
    RiskIndicator,
    Role,
    Severity,
    SystemDescription,
)
from compliance_helper.i18n import Language, description_languages, pick, t, vocabulary

logger = logging.getLogger(__name__)

#: Rule files and the top-level entries each must contain; a missing one fails open to
#: "minimal risk" for every description, so loading stops instead.
RULE_FILES: dict[str, tuple[str, ...]] = {
    "ai_act_risk_classes.yaml": ("prohibitions", "high_risk_annex_iii", "minimal"),
    "ai_act_obligations.yaml": ("obligations",),
    "gdpr_review_path.yaml": ("sections",),
}


class RuleFileError(RuntimeError):
    """A rule file is missing, malformed or incomplete; no classification is possible."""


@dataclass
class RuleSet:
    """Rule files, loaded once."""

    risk_classes_rules: dict[str, Any] = field(default_factory=dict)
    obligations: list[dict[str, Any]] = field(default_factory=list)
    data_protection: list[dict[str, Any]] = field(default_factory=list)
    as_of: date | None = None

    # YAML values are untyped; converting at this boundary makes a wrong field type fail here.

    @property
    def deadlines(self) -> list[dict[str, Any]]:
        stages = (self.risk_classes_rules.get("deadlines") or {}).get("stages", [])
        return list(stages) if isinstance(stages, list) else []

    @property
    def deadline_caveat(self) -> str:
        return str(pick((self.risk_classes_rules.get("deadlines") or {}).get("caveat", "")))

    @property
    def version_note_text(self) -> str:
        return str(pick(self.risk_classes_rules.get("version_note", "")))


def _data_text(value: Any) -> str:
    """Return a rule-file text in the active language with its line breaks folded."""
    return " ".join(str(pick(value) or "").split())


def _read_rule_file(directory: Path, name: str) -> dict[str, Any]:
    """Read one rule file and check that it holds its required entries.

    Raises:
        RuleFileError: the file is missing, malformed or lacks a required entry.
    """
    path = directory / name
    if not path.is_file():
        raise RuleFileError(
            f"Rule file missing: {path}. Set COMPLIANCE_HELPER_ROOT to the folder that contains "
            "data/rules."
        )
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RuleFileError(f"Rule file {path} is malformed: {error}") from error
    missing = [key for key in RULE_FILES[name] if not (content or {}).get(key)]
    if not isinstance(content, dict) or missing:
        raise RuleFileError(f"Rule file {path} lacks: {', '.join(missing) or 'any content'}")
    return content


@lru_cache(maxsize=1)
def rule_set() -> RuleSet:
    """Load the rule files once.

    Raises:
        RuleFileError: a rule file is missing, malformed or incomplete.
    """
    directory = paths.rules_dir()
    risk_rules, obligation_rules, data_protection_rules = (
        _read_rule_file(directory, name) for name in RULE_FILES
    )
    as_of = risk_rules.get("as_of")
    return RuleSet(
        risk_classes_rules=risk_rules,
        obligations=obligation_rules["obligations"],
        data_protection=data_protection_rules["sections"],
        as_of=as_of if isinstance(as_of, date) else None,
    )


def _fold_text(text: str) -> str:
    """Lower-case the text, spell out umlauts and English negations ("doesn't" -> "does not")."""
    text = text.lower().replace("\u2019", "'")
    for old, new in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("n't", " not")):
        text = text.replace(old, new)
    return text


def _languages(description: SystemDescription) -> frozenset[Language]:
    """Return the languages whose vocabulary the description is matched with."""
    return description_languages(
        " ".join(
            (
                description.free_text,
                description.purpose,
                description.field_of_use,
                description.affected_group,
            )
        )
    )


PhraseMatcher = Callable[[str, str], bool]


def _starts_word(word: str, text: str) -> bool:
    """Return True if the word starts a word in the text ("bewerbung" -> "bewerbungen")."""
    word = _fold_text(word)
    return len(word) > 3 and bool(re.search(rf"\b{re.escape(word)}", text))


def _keyword_found(keyword: str, text: str) -> bool:
    """Return True if every word of a keyword phrase longer than three characters starts a word.

    Single area-defining words belong under ``strong_keywords`` in the rule file, since which
    word defines an area is a legal question, not a code question.
    """
    parts = [t for t in _fold_text(keyword).split() if len(t) > 3]
    if not parts:
        return False
    return all(_starts_word(t, text) for t in parts)


def _stem_in_text(stem: str, text: str) -> bool:
    """Return True if the stem starts a word, or occurs inside a German compound.

    Mid-word matches ("modell" in "Sprachmodell") need at least five characters; shorter stems
    occur by accident ("note" in "Notebook", "bild" in "Abbildung").
    """
    if re.search(r"\b%s" % re.escape(stem), text):
        return True
    return len(stem) >= 5 and stem in text


def _german_stems_found(phrase: str, text: str) -> bool:
    """Return True if all words of the phrase longer than three characters occur as stems.

    The words need not be adjacent, since German word order splits verbs ("bieten ... an");
    a phrase of short words only must occur verbatim.
    """
    parts = [t for t in phrase.split() if len(t) > 3]
    if not parts:
        return phrase in text
    return all(_stem_in_text(t, text) for t in parts)


def _substring_found(phrase: str, text: str) -> bool:
    return _fold_text(phrase) in text


#: Negations that may neither precede an English phrase nor stand between its words:
#: "generates content" must not match "does not generate content" or "generates no content".
_NEGATIONS = ("no", "not", "never", "none", "nothing", "nobody", "neither", "nor", "without")

#: Words an English phrase tolerates between its own ("does not itself assess").
MAX_ENGLISH_GAP = 2

#: Words a German role phrase tolerates between its own: separable verbs put the object between
#: verb and particle ("wir setzen in der Personalabteilung ein Werkzeug ein").
MAX_GERMAN_ROLE_GAP = 6


@lru_cache(maxsize=4096)
def _english_pattern(phrase: str, max_gap: int = MAX_ENGLISH_GAP) -> re.Pattern[str]:
    """Compile an English phrase: its words in order within one clause, a few words apart.

    English has fixed word order and few compounds, so word order carries the negation and stems
    only match at word starts ("face" not in "interface"). Words of up to three characters ("no",
    "api", "we") must match whole; longer ones are stems ("assess" -> "assesses").
    """
    negation = rf"(?:{'|'.join(_NEGATIONS)})\b"
    not_negated = "".join(rf"(?<!\b{word} )" for word in _NEGATIONS)
    separator = r"[^\w.,;:!?]+"
    gap = rf"(?:{separator}(?!{negation})[\w']+){{0,{max_gap}}}?{separator}"
    tokens = [
        rf"\b{re.escape(word)}" + (r"\b" if len(word) <= 3 else r"\w*")
        for word in _fold_text(phrase).split()
    ]
    return re.compile(not_negated + gap.join(tokens))


def _english_found(phrase: str, text: str) -> bool:
    return _english_pattern(phrase).search(text) is not None


def _german_role_found(phrase: str, text: str) -> bool:
    """Match a German role phrase in order within one clause, across a separable verb's object."""
    return _english_pattern(phrase, MAX_GERMAN_ROLE_GAP).search(text) is not None


def _phrases(
    words: Any, languages: frozenset[Language], german: PhraseMatcher
) -> Iterator[tuple[str, PhraseMatcher]]:
    """Yield the vocabulary's phrases in the description's languages with their matcher.

    German phrases keep the matcher their list was tuned with; English phrases match as words in
    order (``_english_pattern``).
    """
    matchers: dict[Language, PhraseMatcher] = {Language.DE: german, Language.EN: _english_found}
    for language in Language:
        if language in languages:
            for phrase in vocabulary(words, (language,)):
                yield phrase, matchers[language]


def _mentions(text: str, words: Any, languages: frozenset[Language], german: PhraseMatcher) -> bool:
    """Return True if a phrase in one of the description's languages occurs in the folded text."""
    return any(matches(phrase, text) for phrase, matches in _phrases(words, languages, german))


#: Words that negate a rule keyword standing near them in the same clause.
_RULE_NEGATIONS = frozenset(
    {
        *_NEGATIONS,
        "nicht",
        "kein",
        "keine",
        "keinen",
        "keinem",
        "keiner",
        "keines",
        "keinerlei",
        "ohne",
        "nie",
        "niemals",
        "weder",
    }
)

#: Words after a negation that leave the keyword standing: "not only ..." affirms it, and "plays
#: no role in lending" denies an influence, which the Art. 6(3) check weighs, not the area.
_NEGATION_LIFTERS = frozenset(
    {
        "only",
        "just",
        "merely",
        "nur",
        "bloss",
        "lediglich",
        "role",
        "part",
        "bearing",
        "influence",
        "rolle",
        "einfluss",
    }
)

_CLAUSE_BREAK = re.compile(r"[.,;:!?]|\b(?:but|however|aber|sondern|jedoch)\b")
_WORD = re.compile(r"[\w'-]+")

#: Words before a keyword that a negation may stand in: "we do not use any emotion recognition".
NEGATION_WINDOW = 4

#: Longest clause tail after a keyword whose last two words may negate it: German puts "nicht"
#: at the end ("Emotionserkennung nutzen wir nicht"), English passives too ("are not ranked").
CLAUSE_TAIL_WINDOW = 4


def _negates(words: list[str], index: int) -> bool:
    following = words[index + 1] if index + 1 < len(words) else ""
    return words[index] in _RULE_NEGATIONS and following not in _NEGATION_LIFTERS


def _negated(text: str, start: int, end: int) -> bool:
    """Return True if a negation in the same clause governs ``text[start:end]``."""
    preceding = _WORD.findall(_CLAUSE_BREAK.split(text[:start])[-1])[-NEGATION_WINDOW:]
    tail = _WORD.findall(_CLAUSE_BREAK.split(text[end:])[0])
    words = [*preceding, text[start:end]]
    if any(_negates(words, i) for i in range(len(preceding))):
        return True
    return len(tail) <= CLAUSE_TAIL_WINDOW and any(
        _negates(tail, i) for i in range(max(0, len(tail) - 2), len(tail))
    )


@dataclass(frozen=True)
class FoldedText:
    """A folded description that remembers where each folded character came from.

    Matching runs on the folded text; matches are shown as the user wrote them.
    """

    original: str
    text: str
    origin: tuple[int, ...]

    @classmethod
    def of(cls, original: str) -> FoldedText:
        folded = _fold_text(original)
        if len(folded) == len(original):
            return cls(original, folded, tuple(range(len(original))))
        characters: list[str] = []
        origin: list[int] = []
        for position, character in enumerate(original):
            replaced = _fold_text(character)
            characters.append(replaced)
            origin.extend([position] * len(replaced))
        text = "".join(characters)
        if text != folded:
            # Only "n't" spans characters; it is re-folded as a whole with its positions.
            text, origin = _fold_contractions(text, origin)
        return cls(original, text, tuple(origin))

    def written(self, start: int, end: int) -> str:
        return self.original[self.origin[start] : self.origin[end - 1] + 1]

    def affirmed_spans(self, stem: str) -> Iterator[tuple[int, int]]:
        """Spans of words starting with ``stem`` that no negation in their clause governs."""
        stem = _fold_text(stem)
        if len(stem) <= 3:
            return
        for match in re.finditer(rf"\b{re.escape(stem)}[\w'-]*", self.text):
            if not _negated(self.text, *match.span()):
                yield match.span()


def _fold_contractions(text: str, origin: list[int]) -> tuple[str, list[int]]:
    characters: list[str] = []
    positions: list[int] = []
    index = 0
    while index < len(text):
        if text.startswith("n't", index):
            characters.append(" not")
            positions.extend([origin[index]] * 2 + origin[index + 1 : index + 3])
            index += 3
        else:
            characters.append(text[index])
            positions.append(origin[index])
            index += 1
    return "".join(characters), positions


def _written_word(word: str, text: FoldedText) -> str | None:
    """The affirmed occurrence of a word or adjacent phrase as written, or None."""
    span = next(text.affirmed_spans(word), None)
    return text.written(*span) if span else None


def _written_keyword(keyword: str, text: FoldedText) -> str | None:
    """The affirmed words of a keyword phrase as written, in any order, or None.

    Every word longer than three characters must start an affirmed word of the text.
    """
    parts = [part for part in _fold_text(keyword).split() if len(part) > 3]
    spans = [next(text.affirmed_spans(part), None) for part in parts]
    if not spans or None in spans:
        return None
    return " ".join(dict.fromkeys(text.written(*span) for span in spans if span))


WrittenMatcher = Callable[[str, FoldedText], str | None]


def _written_rule_words(
    text: FoldedText, words: Any, languages: frozenset[Language], find: WrittenMatcher
) -> list[str]:
    """Return the rule-file words found affirmed in the text, as the user wrote them."""
    found = (find(word, text) for word in vocabulary(words, languages))
    return [written for written in found if written]


def _rule_words(
    text: str, words: Any, languages: frozenset[Language], matches: PhraseMatcher
) -> list[str]:
    """Return the rule-file words in the description's languages that occur in the folded text.

    Rule files write both languages as stems for the same matcher, so unlike the code-level
    vocabularies one matcher serves both.
    """
    return [word for word in vocabulary(words, languages) if matches(word, text)]


def traits_from_free_text(description: SystemDescription) -> dict[str, bool]:
    """Infer traits from the free text as hints, not proof.

    Explicitly set fields always win; inferred traits only fill gaps and lower the confidence.
    """
    found: dict[str, bool] = {}
    text = _fold_text(
        description.free_text
        + " "
        + description.purpose
        + " "
        + description.field_of_use
        + " "
        + description.affected_group
    )
    if not text.strip():
        return found
    languages = _languages(description)
    for trait, words in TRAIT_KEYWORDS.items():
        if getattr(description, trait, None) is not None:
            continue
        if _mentions(text, words, languages, _german_stems_found):
            found[trait] = True

    if found.get("emotion_recognition") and not _mentions(
        text, BIOMETRIC_CARRIERS, languages, _german_stems_found
    ):
        found.pop("emotion_recognition")

    if _mentions(text, SAFETY_OR_MEDICAL_EXEMPTION, languages, _german_stems_found):
        found["safety_or_medical_exemption"] = True
    return found


def _trait_value(
    description: SystemDescription, text_traits: dict[str, bool], name: str
) -> bool | None:
    """Return the declared trait value, else the text-inferred one, else None."""
    value = getattr(description, name, None)
    if value is not None:
        return bool(value)
    return text_traits.get(name)


class Assessor:
    """Classifies a system description and derives its obligations."""

    def __init__(
        self, rules: RuleSet | None = None, purpose_matcher: PurposeMatcher | None = None
    ) -> None:
        self.rules = rules or rule_set()
        # Built lazily so runs without models (benchmark, phone, offline) never block on loading.
        self._purpose_matcher = purpose_matcher
        self._purpose_matcher_attempted = purpose_matcher is not None

    def purpose_matcher(self) -> PurposeMatcher | None:
        """Return the purpose matcher, built once; ``None`` if unavailable."""
        if not self._purpose_matcher_attempted:
            self._purpose_matcher_attempted = True
            try:
                self._purpose_matcher = shared_purpose_matcher()
            except Exception as error:
                logger.warning(
                    "Purpose catalog unreadable (%s); classifying with rule keywords only",
                    error,
                )
        return self._purpose_matcher

    def _purposes(self, description: SystemDescription) -> dict[str, PurposeMatch]:
        """Return the best purpose match per triggered rule."""
        matcher = self.purpose_matcher()
        if matcher is None:
            return {}
        text = " ".join(
            t
            for t in (
                description.free_text,
                description.purpose,
                description.field_of_use,
            )
            if t
        )
        found: dict[str, PurposeMatch] = {}
        for match in matcher.find(text):
            existing = found.get(match.rule)
            if existing is None or match.value > existing.value:
                found[match.rule] = match
        return found

    @staticmethod
    def _purpose_rationale(match: PurposeMatch) -> str:
        """Explain a purpose match by citation, matched sentence and similarity."""
        return t(
            "assessor.purpose_rationale",
            citation=match.citation,
            confidence=match.confidence,
            sentence=match.sentence,
            purpose=match.purpose,
            value=match.value,
        )

    def _prohibitions(
        self,
        description: SystemDescription,
        text_traits: dict[str, bool],
        purposes: dict[str, PurposeMatch] | None = None,
    ) -> list[RiskIndicator]:
        purposes = purposes or {}
        indicators: list[RiskIndicator] = []
        for rule in self.rules.risk_classes_rules.get("prohibitions", []):
            conditions = rule.get("when", [])
            values = [_trait_value(description, text_traits, b["trait"]) for b in conditions]
            purpose_match = purposes.get(rule["id"])
            if (not values or any(w is not True for w in values)) and purpose_match is None:
                continue

            # Required wording beats similarity; without it, other routes yield obligations.
            if not self._required_wording_present(rule, description):
                continue

            # A claimed exemption lifts the ban, but the practice stays Annex III point 1 high risk.
            if rule.get("exemption") and text_traits.get("safety_or_medical_exemption"):
                indicators.append(
                    RiskIndicator(
                        risk_class=RiskClass.HIGH_RISK_ANNEX_III,
                        rule="{}-exemption".format(rule["id"]),
                        rationale=t(
                            "assessor.prohibition_lifted_by_exemption",
                            citation=pick(rule.get("citation", "")),
                            wording=_data_text(rule["exemption"]),
                        ),
                        legal_basis=(
                            *tuple(rule.get("legal_basis", [])),
                            "AI-Act/annex-III/pt-1",
                        ),
                        confidence="needs_review",
                    )
                )
                continue
            # A prohibition inferred from free text alone is only a suspicion.
            from_text_only = any(b["trait"] in text_traits for b in conditions)
            rationale = self._rationale_with_exemption(rule)
            basis = tuple(rule.get("legal_basis", []))
            if purpose_match is not None:
                rationale += " " + self._purpose_rationale(purpose_match)
                if purpose_match.citation not in basis:
                    basis = (purpose_match.citation, *basis)
                from_text_only = True
            indicators.append(
                RiskIndicator(
                    risk_class=RiskClass.PROHIBITED,
                    rule=rule["id"],
                    rationale=rationale,
                    legal_basis=basis,
                    confidence="needs_review"
                    if from_text_only
                    else rule.get("confidence", "likely"),
                )
            )
        return indicators

    @staticmethod
    def _required_wording_present(rule: dict[str, Any], description: SystemDescription) -> bool:
        """Return True if the description contains a word the rule explicitly requires."""
        languages = _languages(description)
        if not vocabulary(rule.get("required_wording"), languages):
            return True
        text = _fold_text(" ".join((description.free_text, description.purpose)))
        return bool(_rule_words(text, rule.get("required_wording"), languages, _substring_found))

    @staticmethod
    def _rationale_with_exemption(rule: dict[str, Any]) -> str:
        text = _data_text(rule.get("rationale"))
        if rule.get("exemption"):
            text += " " + t("assessor.exemption", wording=_data_text(rule["exemption"]))
        return text

    def _annex_i(
        self,
        description: SystemDescription,
        text_traits: dict[str, bool],
        purposes: dict[str, PurposeMatch] | None = None,
    ) -> RiskIndicator | None:
        purposes = purposes or {}
        rule = self.rules.risk_classes_rules.get("high_risk_annex_i") or {}
        if not rule:
            return None
        purpose_match = purposes.get(rule["id"])
        values = [_trait_value(description, text_traits, b["trait"]) for b in rule.get("when", [])]
        certain = bool(values) and all(w is True for w in values)

        # Users cannot answer "product under Annex I" without knowing the law, so the product
        # category named in the text is a second route.
        if not certain:
            text = FoldedText.of(
                " ".join((description.free_text, description.purpose, description.field_of_use))
            )
            product_match = bool(
                _written_rule_words(
                    text, rule.get("keywords"), _languages(description), _written_keyword
                )
            )
            carriers = _trait_value(description, text_traits, "embedded_in_product") is True
            # A purpose match names the product category, which already implies embedding.
            if not (product_match and carriers) and purpose_match is None:
                return None

        rationale = _data_text(rule.get("rationale"))
        basis = tuple(rule.get("legal_basis", []))
        if purpose_match is not None:
            rationale += " " + self._purpose_rationale(purpose_match)
            if purpose_match.citation not in basis:
                basis = (purpose_match.citation, *basis)
            rationale += " " + t("assessor.annex_i_third_party_assessment")
        return RiskIndicator(
            risk_class=RiskClass.HIGH_RISK_ANNEX_I,
            rule=rule["id"],
            rationale=rationale,
            legal_basis=basis,
            confidence="likely" if certain else "needs_review",
        )

    def _annex_iii(
        self,
        description: SystemDescription,
        _text_traits: dict[str, bool] | None = None,
        purposes: dict[str, PurposeMatch] | None = None,
    ) -> list[RiskIndicator]:
        """Find Annex III areas via the rule file's keywords.

        ``_text_traits`` is unused because this route matches the free text directly; it keeps the
        signature uniform across all routes.
        """
        purposes = purposes or {}
        section_rules = self.rules.risk_classes_rules.get("high_risk_annex_iii") or {}
        text = FoldedText.of(
            " ".join(
                (
                    description.free_text,
                    description.purpose,
                    description.field_of_use,
                    description.affected_group,
                )
            )
        )
        languages = _languages(description)
        exonerated = bool(
            _rule_words(
                text.text, section_rules.get("exoneration_phrases"), languages, _substring_found
            )
        )

        indicators: list[RiskIndicator] = []
        for area in section_rules.get("areas", []):
            match = _written_rule_words(text, area.get("strong_keywords"), languages, _written_word)
            match += _written_rule_words(text, area.get("keywords"), languages, _written_keyword)

            # Carrier plus action word catches cases like staff KPIs (pt. 4) with no defining word.
            pair = area.get("combination") or {}
            if pair:
                carriers = _written_rule_words(text, pair.get("carriers"), languages, _written_word)
                actions = _written_rule_words(
                    text, pair.get("actions"), languages, _written_keyword
                )
                if carriers and actions:
                    match += [f"{carriers[0]} + {actions[0]}"]

            purpose_match = purposes.get(area["id"])
            # An explicit denial outweighs a purpose-only match: "mails sorted by department" scored
            # 0.75 against "we pre-sort applications" merely because both sort.
            if not match and purpose_match is not None and self._no_decision_influence(description):
                continue
            if (not match and purpose_match is None) or exonerated:
                continue
            covers = [str(pick(entry)) for entry in pick(area.get("covers")) or []]
            title = pick(area.get("title", ""))
            if match:
                rationale = t(
                    "assessor.annex_iii_area_with_keywords",
                    title=title,
                    keywords=", ".join(list(dict.fromkeys(match))[:3]),
                )
            else:
                rationale = t("assessor.annex_iii_area", title=title)
            if covers:
                rationale += " " + t("assessor.annex_iii_area_covers", covers="; ".join(covers))
            if area.get("exemption"):
                rationale += " " + t(
                    "assessor.annex_iii_area_note", note=_data_text(area["exemption"])
                )
            basis = tuple(area.get("legal_basis", []))
            if purpose_match is not None:
                rationale += " " + self._purpose_rationale(purpose_match)
                # The purpose citation (letter) is more specific than the area's (point).
                if purpose_match.citation not in basis:
                    basis = (purpose_match.citation, *basis)
            indicators.append(
                RiskIndicator(
                    risk_class=RiskClass.HIGH_RISK_ANNEX_III,
                    rule=area["id"],
                    rationale=rationale,
                    legal_basis=basis,
                    confidence="needs_review",
                )
            )
        return indicators

    @staticmethod
    def _no_decision_influence(description: SystemDescription) -> bool:
        """Return True if the description explicitly says the system does not decide.

        Matched as a phrase, not a substring, so "bewertet es nicht" equals "bewertet nicht".
        """
        text = _fold_text(" ".join((description.free_text, description.purpose)))
        return _mentions(text, NO_DECISION_INFLUENCE, _languages(description), _keyword_found)

    @staticmethod
    def _detect_exemption_case(description: SystemDescription) -> str | None:
        """Return the matching Art. 6(3) exemption case id, if any."""
        text = _fold_text(
            " ".join((description.free_text, description.purpose, description.field_of_use))
        )
        languages = _languages(description)
        for case_id, markers in EXEMPTION_CASES.items():
            if _mentions(text, markers, languages, _keyword_found):
                return case_id
        return None

    def _check_exemption(
        self, description: SystemDescription, text_traits: dict[str, bool]
    ) -> RiskIndicator | None:
        """Check the Art. 6(3) exemption, including the profiling counter-exemption.

        The exemption is never assumed, because it requires a documented assessment and
        registration; the description must claim it explicitly.
        """
        section_rules = self.rules.risk_classes_rules.get("high_risk_exemption") or {}
        if not section_rules:
            return None
        profiling = _trait_value(description, text_traits, "makes_decisions_about_people")
        counter_scores = section_rules.get("counter_exemption") or {}

        if profiling is True and not self._no_decision_influence(description):
            return RiskIndicator(
                risk_class=RiskClass.HIGH_RISK_ANNEX_III,
                rule=counter_scores.get("id", "art6-3-profiling"),
                rationale=_data_text(counter_scores.get("text")),
                legal_basis=tuple(counter_scores.get("legal_basis", [])),
                confidence="likely",
            )
        case = self._detect_exemption_case(description)
        if not (case and self._no_decision_influence(description)):
            # Wrongly assuming the exemption is the more dangerous error.
            return None
        explanation = next(
            (
                _data_text(f.get("text"))
                for f in section_rules.get("one_of_cases", [])
                if f.get("id") == case
            ),
            "",
        )
        follow_up_obligation = section_rules.get("follow_up_obligation") or {}
        return RiskIndicator(
            risk_class=RiskClass.HIGH_RISK_EXEMPTION,
            rule=section_rules["id"],
            rationale=t(
                "assessor.exemption_case",
                case=explanation,
                precondition=_data_text(section_rules.get("precondition")),
                follow_up_obligation=_data_text(follow_up_obligation.get("text")),
            ),
            legal_basis=tuple(
                section_rules.get("legal_basis", []) + follow_up_obligation.get("legal_basis", [])
            ),
            confidence="needs_review",
        )

    def _transparency(
        self,
        description: SystemDescription,
        text_traits: dict[str, bool],
        purposes: dict[str, PurposeMatch] | None = None,
    ) -> list[RiskIndicator]:
        purposes = purposes or {}
        section_rules = self.rules.risk_classes_rules.get("transparency") or {}
        indicators: list[RiskIndicator] = []
        for case in section_rules.get("cases", []):
            # Art. 50(1)-(2) bind providers, (3)-(4) deployers: a ChatGPT user need not watermark.
            allowed = case.get("roles") or ([case["role"]] if case.get("role") else [])
            if (
                allowed
                and description.roles
                and not any(Role(r) in description.roles for r in allowed)
            ):
                continue
            values = [
                _trait_value(description, text_traits, b["trait"]) for b in case.get("when", [])
            ]
            matched = bool(values) and all(w is True for w in values)
            # Art. 50(4) needs alternatives: deepfakes, or published media that may fake reality.
            for entry in case.get("or_when", []):
                alternative_values = [
                    _trait_value(description, text_traits, b["trait"])
                    for b in entry.get("when", [])
                ]
                if alternative_values and all(w is True for w in alternative_values):
                    matched = True
                    break
            purpose_match = purposes.get(case["id"])
            if not matched and purpose_match is None:
                continue
            from_text_only = any(b["trait"] in text_traits for b in case.get("when", []))
            rationale = "{} ({})".format(
                _data_text(case.get("obligation")), pick(case.get("citation", ""))
            )
            basis = tuple(case.get("legal_basis", []))
            if purpose_match is not None:
                rationale += " " + self._purpose_rationale(purpose_match)
                if purpose_match.citation not in basis:
                    basis = (purpose_match.citation, *basis)
                from_text_only = True
            indicators.append(
                RiskIndicator(
                    risk_class=RiskClass.TRANSPARENCY,
                    rule=case["id"],
                    rationale=rationale,
                    legal_basis=basis,
                    confidence="needs_review" if from_text_only else "likely",
                )
            )
        return indicators

    def _gpai(
        self,
        description: SystemDescription,
        text_traits: dict[str, bool],
        purposes: dict[str, PurposeMatch] | None = None,
    ) -> list[RiskIndicator]:
        purposes = purposes or {}
        section_rules = self.rules.risk_classes_rules.get("gpai") or {}
        if not section_rules:
            return []
        values = [
            _trait_value(description, text_traits, b["trait"])
            for b in section_rules.get("when", [])
        ]
        purpose_match = purposes.get(section_rules["id"])
        if (not values or any(w is not True for w in values)) and purpose_match is None:
            return []

        # Not placed on the market: Art. 3(63) exception.
        free_text = _fold_text(" ".join((description.free_text, description.purpose)))
        if _rule_words(
            free_text,
            section_rules.get("exoneration_phrases"),
            _languages(description),
            _substring_found,
        ):
            return []

        # Art. 51/53 bind providers; a buyer mentioning their "Modellanbieter" is still a deployer.
        if Role.DEPLOYER in description.roles and Role.PROVIDER not in description.roles:
            return []

        rationale = t("assessor.gpai_model_provided")
        basis = tuple(section_rules.get("legal_basis", []))
        if purpose_match is not None:
            rationale += " " + self._purpose_rationale(purpose_match)
            if purpose_match.citation not in basis:
                basis = (purpose_match.citation, *basis)
        indicators = [
            RiskIndicator(
                risk_class=RiskClass.GPAI,
                rule=section_rules["id"],
                rationale=rationale,
                legal_basis=basis,
                confidence="likely",
            )
        ]
        systemic = section_rules.get("systemic_risk") or {}
        threshold = float(systemic.get("threshold_flop", 1e25))
        if description.training_compute_flop and description.training_compute_flop >= threshold:
            indicators.append(
                RiskIndicator(
                    risk_class=RiskClass.GPAI_SYSTEMIC_RISK,
                    rule=systemic.get("id", "art51-systemic-risk"),
                    rationale=t(
                        "assessor.gpai_systemic_risk_threshold",
                        compute=description.training_compute_flop,
                        threshold=threshold,
                        presumption=_data_text(systemic.get("presumption")),
                    ),
                    legal_basis=tuple(systemic.get("legal_basis", [])),
                    confidence="likely",
                )
            )
        return indicators

    @staticmethod
    def _trait_state(
        name: str, description: SystemDescription, text_traits: dict[str, bool]
    ) -> bool | None:
        """Return the declared trait, else the text-inferred one, else None.

        With None, ``on_unknown`` in the rule file decides.
        """
        declared = getattr(description, name, None)
        if isinstance(declared, bool):
            return declared
        if name in text_traits:
            return text_traits[name]
        return None

    def _trait_filter(
        self, entry: dict, description: SystemDescription, text_traits: dict[str, bool]
    ) -> tuple[bool, str]:
        """Decide whether a trait-bound obligation is listed.

        Some obligations depend on a system trait, not the risk class (remote biometric
        identification approval does not concern an application filter). Deliberately cautious:
        only what the description excludes, or what ``on_unknown: omit`` marks as too narrow, is
        dropped; everything else is listed with a caveat for the user to verify.

        Returns:
            ``(include, caveat)``.
        """
        traits = entry.get("only_when") or []
        required_traits = entry.get("only_when_all") or []
        if not traits and not required_traits:
            return True, ""

        # Art. 26(10) needs biometrics and law enforcement, or every gate access control gets it.
        if required_traits:
            strict_states = [
                self._trait_state(m, description, text_traits) for m in required_traits
            ]
            if any(b is not True for b in strict_states):
                if entry.get("on_unknown", "with_caveat") == "omit" or any(
                    b is False for b in strict_states
                ):
                    return False, ""
                return True, _data_text(entry.get("caveat"))
            if not traits:
                return True, ""

        trait_states = [self._trait_state(m, description, text_traits) for m in traits]
        if any(b is True for b in trait_states):
            return True, ""
        if all(b is False for b in trait_states):
            return False, ""
        if entry.get("on_unknown", "with_caveat") == "omit":
            return False, ""
        return True, _data_text(entry.get("caveat")) or t(
            "assessor.trait_caveat",
            traits=t("assessor.trait_separator").join(m.replace("_", " ") for m in traits),
        )

    def _obligations(
        self,
        risk_classes: set[RiskClass],
        roles: set[Role],
        description: SystemDescription | None = None,
        text_traits: dict[str, bool] | None = None,
    ) -> list[Obligation]:
        """Return all obligations matching the risk classes, roles and traits."""
        description = description or SystemDescription()
        text_traits = text_traits or {}
        found: list[tuple[tuple[str, str], Obligation]] = []
        for entry in self.rules.obligations:
            entry_risk_classes = {
                RiskClass(k)
                for k in entry.get("risk_classes", [])
                if k in RiskClass._value2member_map_
            }
            entry_roles = {Role(r) for r in entry.get("roles", []) if r in Role._value2member_map_}
            if entry_risk_classes and not (entry_risk_classes & risk_classes):
                continue
            if entry_roles and roles and not (entry_roles & roles):
                continue
            include, caveat = self._trait_filter(entry, description, text_traits)
            if not include:
                continue
            applies_from = entry.get("applies_from")
            obligation = Obligation(
                id=entry["id"],
                title=pick(entry.get("title", entry["id"])),
                action_required=_data_text(entry.get("action_required")),
                legal_basis=tuple(entry.get("legal_basis", [])) or ("",),
                also_cited=tuple(entry.get("also_cited", [])),
                citation_text=pick(entry.get("citation_text", "")),
                roles=tuple(entry_roles) or tuple(roles) or (Role.PROVIDER,),
                risk_classes=tuple(entry_risk_classes) or tuple(risk_classes),
                severity=Severity(entry.get("severity", "obligation"))
                if entry.get("severity") in Severity._value2member_map_
                else Severity.OBLIGATION,
                applies_from=applies_from if isinstance(applies_from, date) else None,
                evidence_of_compliance=_data_text(entry.get("evidence_of_compliance")),
                on_infringement=_data_text(entry.get("on_infringement")),
                caveat=caveat,
            )
            order = (obligation.severity.value, pick(entry.get("citation_text", ""), Language.DE))
            found.append((order, obligation))
        return [obligation for _, obligation in sorted(found, key=lambda item: item[0])]

    #: GDPR review-path sections that apply to any processing of personal data.
    ALWAYS_DATA_PROTECTION = frozenset(
        {
            "a-personal-data",
            "b-role",
            "c-legal-basis",
            "d1-principle-lawfulness",
            "d2-principle-purpose-limitation",
            "d3-principle-data-minimisation",
            "d5-principle-storage-limitation",
            "d6-principle-integrity-confidentiality",
            "d7-principle-accountability",
            "e-data-subject-information",
            "f-data-subject-rights",
            "i-records-of-processing",
            "k-security-of-processing",
            "o-breach-notification-authority",
        }
    )

    #: Conditional sections; without them every user would get all 26 sections.
    CONDITIONAL_DATA_PROTECTION: ClassVar[dict[str, tuple[str, ...]]] = {
        "g-automated-decision-making": ("makes_decisions_about_people",),
        "h-processor": ("procured",),
        "j-data-protection-by-design": ("in_house_development",),
        "l-data-protection-impact-assessment": ("high_risk",),
        "m-prior-consultation": ("high_risk",),
        "n-data-protection-officer": ("many_employees",),
        "p-breach-communication-data-subjects": ("high_risk",),
        "q-third-country-transfers": ("third_country_transfer",),
        "r-employee-data": ("employee_data",),
        "s-training-on-personal-data": ("trains_on_personal_data",),
        "t-ai-act-interplay": ("always_for_ai",),
        "d4-principle-accuracy": ("makes_decisions_about_people",),
    }

    def _condition_met(
        self,
        name: str,
        description: SystemDescription,
        text_traits: dict[str, bool],
        risk_classes: set[RiskClass],
    ) -> bool:
        """Resolve a condition of the conditional data-protection sections."""
        if name == "always_for_ai":
            return True
        if name == "high_risk":
            return bool(
                risk_classes
                & {
                    RiskClass.HIGH_RISK_ANNEX_I,
                    RiskClass.HIGH_RISK_ANNEX_III,
                    RiskClass.HIGH_RISK_EXEMPTION,
                    RiskClass.PROHIBITED,
                }
            )
        if name == "many_employees":
            count_value = description.employee_count
            return count_value is not None and count_value >= 20
        if name == "third_country_transfer":
            return _trait_value(description, text_traits, "third_country_transfer") is True
        if name == "employee_data":
            return _trait_value(description, text_traits, "employee_data") is True
        if name == "trains_on_personal_data":
            folded = _fold_text(description.free_text + " " + description.purpose)
            return _mentions(
                folded, TRAINING_ON_OWN_DATA, _languages(description), _substring_found
            )
        if name == "procured":
            folded = _fold_text(description.free_text)
            return _mentions(folded, PROCURED, _languages(description), _substring_found)
        if name == "in_house_development":
            return Role.PROVIDER in description.roles
        return _trait_value(description, text_traits, name) is True

    def _data_protection(
        self,
        description: SystemDescription,
        text_traits: dict[str, bool],
        risk_classes: set[RiskClass] | None = None,
    ) -> list[Obligation]:
        """Return the GDPR review-path sections that apply."""
        personal_data = _trait_value(description, text_traits, "processes_personal_data")
        if personal_data is False:
            return []
        risk_classes = risk_classes or set()
        found: list[Obligation] = []
        for section in self.rules.data_protection:
            section_id = section.get("id", "")
            conditions = self.CONDITIONAL_DATA_PROTECTION.get(section_id)
            if conditions is not None:
                if not all(
                    self._condition_met(b, description, text_traits, risk_classes)
                    for b in conditions
                ):
                    continue
            elif section_id not in self.ALWAYS_DATA_PROTECTION:
                logger.debug("Data-protection section without mapping, kept: %s", section_id)
            found.append(
                Obligation(
                    id=section.get("id", "gdpr-unnamed-section"),
                    title=pick(section.get("title", "")),
                    action_required=_data_text(
                        section.get("action_required") or section.get("question")
                    ),
                    legal_basis=tuple(section.get("legal_basis", [])) or ("",),
                    also_cited=tuple(section.get("also_cited", [])),
                    citation_text=pick(section.get("citation_text", "")),
                    roles=(Role.PROVIDER, Role.DEPLOYER),
                    risk_classes=(RiskClass.MINIMAL,),
                    severity=Severity.OBLIGATION,
                    evidence_of_compliance=_data_text(section.get("evidence_of_compliance")),
                    on_infringement=_data_text(section.get("on_infringement")),
                )
            )
        return found

    def _open_questions(
        self,
        description: SystemDescription,
        text_traits: dict[str, bool],
        risk_classes: set[RiskClass],
    ) -> list[str]:
        questions: list[str] = []
        if not description.roles:
            questions.append(t("assessor.open_question_role"))
        if _trait_value(description, text_traits, "processes_personal_data") is None:
            questions.append(t("assessor.open_question_personal_data"))
        if RiskClass.HIGH_RISK_ANNEX_III in risk_classes:
            if _trait_value(description, text_traits, "human_oversight") is None:
                questions.append(t("assessor.open_question_human_oversight"))
            if _trait_value(description, text_traits, "makes_decisions_about_people") is None:
                questions.append(t("assessor.open_question_profiling"))
        if RiskClass.GPAI in risk_classes and description.training_compute_flop is None:
            questions.append(t("assessor.open_question_training_compute"))
        if description.filled_count() < 3:
            questions.append(t("assessor.open_question_thin_description"))
        return questions

    def check(self, description: SystemDescription) -> Classification:
        """Classify a system description."""
        text_traits = traits_from_free_text(description)
        purposes = self._purposes(description)
        indicators: list[RiskIndicator] = []

        prohibitions = self._prohibitions(description, text_traits, purposes)
        indicators.extend(prohibitions)

        if not prohibitions:
            annex_i = self._annex_i(description, text_traits, purposes)
            if annex_i:
                indicators.append(annex_i)
            annex_iii = self._annex_iii(description, text_traits, purposes)
            indicators.extend(annex_iii)
            if annex_iii:
                exemption = self._check_exemption(description, text_traits)
                if exemption is not None:
                    if exemption.risk_class is RiskClass.HIGH_RISK_EXEMPTION:
                        # The exemption replaces Annex III instead of contradicting it.
                        indicators = [
                            h
                            for h in indicators
                            if h.risk_class is not RiskClass.HIGH_RISK_ANNEX_III
                        ]
                    indicators.append(exemption)
            indicators.extend(self._transparency(description, text_traits, purposes))
            indicators.extend(self._gpai(description, text_traits, purposes))

        risk_classes = {h.risk_class for h in indicators}
        if not risk_classes:
            minimal = self.rules.risk_classes_rules.get("minimal") or {}
            indicators.append(
                RiskIndicator(
                    risk_class=RiskClass.MINIMAL,
                    rule=minimal.get("id", "minimal-risk"),
                    rationale=_data_text(minimal.get("rationale")),
                    legal_basis=tuple(minimal.get("legal_basis", [])),
                    confidence="likely",
                )
            )
            risk_classes = {RiskClass.MINIMAL}

        roles = set(description.roles)
        # No declared role: show both views.
        effective_roles = roles or {Role.PROVIDER, Role.DEPLOYER}

        return Classification(
            risk_classes=tuple(sorted(risk_classes, key=lambda k: k.rank)),
            indicators=tuple(indicators),
            roles=tuple(sorted(roles, key=lambda r: r.value)),
            obligations=tuple(
                self._obligations(risk_classes, effective_roles, description, text_traits)
            ),
            data_protection=tuple(self._data_protection(description, text_traits, risk_classes)),
            open_questions=tuple(self._open_questions(description, text_traits, risk_classes)),
            as_of=self.rules.as_of,
        )


def roles_from_text(text: str) -> tuple[Role, ...]:
    """Infer roles from explicit phrases such as "wir entwickeln" or "we purchased".

    Without a matching phrase nothing is claimed and the assessor asks for the role.
    """
    folded = _fold_text(text)
    languages = description_languages(text)
    found: list[Role] = []
    if _mentions(folded, PROVIDER_PHRASES, languages, _german_role_found):
        found.append(Role.PROVIDER)
    if _mentions(folded, DEPLOYER_PHRASES, languages, _german_role_found):
        found.append(Role.DEPLOYER)
    return tuple(found)


#: Art. 51(2) threshold notations: "10^25", "10²⁵", "1e26", "2.5e25", "10 hoch 25",
#: "10 to the power of 25", "2,5 x 10^25", "3 times 10^25".
_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
#: Superscripts span two blocks: ⁰ and ⁴-⁹ at U+2070 ff., but ¹²³ at U+00B9/U+00B2/U+00B3.
_DIGIT_CLASS = "0-9\u2070\u2074-\u2079\u00b9\u00b2\u00b3"
_COMPUTE_PATTERN = re.compile(
    r"(?:(?P<factor>\d+(?:[.,]\d+)?)\s*(?:x|×|\*|·|mal|times)\s*)?"
    r"(?:10\s*(?:\^|\*\*|hoch\s*|to the power of\s*)?|(?P<coefficient>\d+(?:[.,]\d+)?)\s*e\+?)"
    r"\s*(?P<exponent>[" + _DIGIT_CLASS + r"]{1,3})(?=[^0-9]|$)",
    re.IGNORECASE,
)


def _decimal(value: str | None) -> float:
    return float((value or "1").replace(",", "."))


def compute_from_text(text: str) -> float | None:
    """Return the training compute in FLOP stated in the text, or None.

    Parsed only when the text mentions compute, so years or quantities are not misread.
    """
    if not _mentions(
        _fold_text(text), COMPUTE_MENTIONS, description_languages(text), _substring_found
    ):
        return None
    match = _COMPUTE_PATTERN.search(text)
    if not match:
        return None
    mantissa = _decimal(match["factor"]) * _decimal(match["coefficient"])
    exponent = int(match["exponent"].translate(_SUPERSCRIPT_DIGITS))
    if not 10 <= exponent <= 40:
        return None
    return mantissa * (10.0**exponent)


def description_from_text(text: str) -> SystemDescription:
    """Build a SystemDescription from free text."""
    text = re.sub(r"\s+", " ", text).strip()
    return SystemDescription(
        free_text=text[:20_000],
        roles=roles_from_text(text),
        training_compute_flop=compute_from_text(text),
    )
