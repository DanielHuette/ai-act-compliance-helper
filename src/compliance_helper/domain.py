"""Typed domain model shared by corpus, classification, search and answering.

Context: models are strict (frozen, extra="forbid") because a wrong statement about obligations is
costly; failing on load beats inventing an obligation. | Input: legal text units, system
descriptions, rule data | Output: validated Pydantic models and enums.
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from compliance_helper.i18n import t


class LegalAct(StrEnum):
    """Legal acts the corpus covers."""

    AI_ACT = "AI-Act"
    GDPR = "GDPR"
    BDSG = "BDSG"
    GUIDELINES = "Guidelines"

    @property
    def label(self) -> str:
        return t(f"domain.legal_act_label_{self.name.lower()}")

    @property
    def full_name(self) -> str:
        return t(f"domain.legal_act_name_{self.name.lower()}")

    @property
    def binding(self) -> bool:
        """Guidelines do not bind courts; answers must say so."""
        return self is not LegalAct.GUIDELINES


class UnitKind(StrEnum):
    ARTICLE = "article"
    SECTION = "section"
    ANNEX = "annex"
    RECITAL = "recital"
    GUIDELINES = "guidelines"
    EXAMPLE = "example"


class Unit(BaseModel):
    """Smallest citable piece of law: a paragraph, an annex point, a recital or a case.

    `id` is the key used across the whole system, e.g. ``AI-Act/art-6/para-2``,
    ``GDPR/art-35/para-1``, ``AI-Act/annex-III/pt-5-a``, ``BDSG/sec-26``,
    ``case/application-screening-llm``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=3, max_length=120)
    legal_act: LegalAct
    kind: UnitKind
    number: str = Field(description="Article, section or annex number as text")
    paragraph: str | None = Field(default=None, description="Paragraph, letter or point")
    title: str = ""
    chapter: str = ""
    section_title: str = ""
    text: str = Field(min_length=1)
    applies_from: date | None = Field(default=None, description="Date from which this unit applies")
    source: str = Field(default="", description="URL the text was fetched from")
    as_of: date | None = Field(default=None, description="Date the text was fetched")
    references: tuple[str, ...] = Field(default=(), description="Ids of related units")

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if " " in value:
            raise ValueError(f"Unit id must not contain spaces: {value!r}")
        if value.count("/") < 1:
            raise ValueError(f"Unit id must have the form legal_act/unit: {value!r}")
        return value

    @property
    def citation(self) -> str:
        """Citation in the active language as shown in answers.

        Annexes are numbered by points ("Anhang III Nummer 4", "Annex III point 4"), not
        paragraphs. Examples are not statutory citations and are cited by title, never by id.
        """
        if self.kind is UnitKind.EXAMPLE:
            return t("domain.citation_example", title=self.title or self.number)
        if self.kind is UnitKind.GUIDELINES:
            return self.title or self.number
        return t(
            f"domain.citation_{self.kind.value}",
            number=self.number,
            position=_position(self.paragraph, self.kind) if self.paragraph else "",
            act=self.legal_act.label,
        )


#: Paragraph values of articles and sections: "1", "2 Buchstabe a", "1 Buchstabe ua2-a" (letter a
#: of the second subparagraph) and "Nummer 39" (definition articles are numbered by points).
_ARTICLE_POSITION = re.compile(
    r"^(?:Nummer (?P<point>\S+)|(?P<paragraph>\d+\w*)"
    r"(?: Buchstabe (?:ua(?P<subparagraph>\d+)-)?(?P<letter>[a-z]+))?)$"
)

#: Annex point values: "1", "1-a", "b", "A-1" (section A, point 1), "1-1-a".
_ANNEX_POSITION = re.compile(
    r"^(?:(?:(?P<section>[A-Z0-9]+)-)?(?P<point>[A-Z0-9]+))?(?:-?(?P<letter>[a-z]+))?$"
)


def _position(paragraph: str, kind: UnitKind) -> str:
    """Render the paragraph, letter or point part of a citation in the active language."""
    annex = kind is UnitKind.ANNEX
    match = (_ANNEX_POSITION if annex else _ARTICLE_POSITION).match(paragraph)
    parts: dict[str, Any] = (
        {name: value for name, value in match.groupdict().items() if value} if match else {}
    )
    if not parts:
        if annex:
            return t("domain.position_annex_point", point=paragraph)
        return t("domain.position_paragraph", paragraph=paragraph)
    prefix = "domain.position_annex_" if annex else "domain.position_"
    return t(prefix + "_".join(parts), **parts)


_CITATION_ID = re.compile(
    r"^(?P<act>[^/]+)/(?P<kind>art|sec|annex|recital)-(?P<number>[^/]+)(?:/(?P<rest>.+))?$"
)
_ID_KINDS = {
    "art": UnitKind.ARTICLE,
    "sec": UnitKind.SECTION,
    "annex": UnitKind.ANNEX,
    "recital": UnitKind.RECITAL,
}
_ID_PARAGRAPH = re.compile(
    r"^para-(?P<paragraph>\d+\w*)(?:-(?:sub(?P<sub>\d+)-)?(?P<letter>[a-z]+))?$"
)


def _paragraph_from_id(rest: str, kind: UnitKind) -> str | None:
    """Translate the id tail ("para-1-a", "pt-39", "pt-4-a") into the ``Unit.paragraph`` form."""
    if kind is UnitKind.ANNEX:
        return rest.removeprefix("pt-") if rest.startswith("pt-") else None
    if rest.startswith("pt-"):
        return f"Nummer {rest.removeprefix('pt-')}"
    match = _ID_PARAGRAPH.match(rest)
    if not match:
        return None
    paragraph, sub, letter = match.group("paragraph", "sub", "letter")
    if not letter:
        return paragraph
    return f"{paragraph} Buchstabe {f'ua{sub}-' if sub else ''}{letter}"


def citation_from_id(unit_id: str) -> str:
    """Render a unit id such as ``AI-Act/art-6/para-1-a`` as a citation in the active language.

    Ids that are not statutory citations (cases, guideline examples) are returned unchanged.
    """
    match = _CITATION_ID.match(unit_id)
    if not match or match.group("act") not in LegalAct._value2member_map_:
        return unit_id
    kind = _ID_KINDS[match.group("kind")]
    rest = match.group("rest")
    paragraph = _paragraph_from_id(rest, kind) if rest else None
    if rest and paragraph is None:
        return unit_id
    return t(
        f"domain.citation_{kind.value}",
        number=match.group("number"),
        position=_position(paragraph, kind) if paragraph else "",
        act=LegalAct(match.group("act")).label,
    )


class Role(StrEnum):
    """Actor role under the AI Act; determines which obligations apply."""

    PROVIDER = "provider"
    DEPLOYER = "deployer"
    IMPORTER = "importer"
    DISTRIBUTOR = "distributor"
    PRODUCT_MANUFACTURER = "product_manufacturer"
    AUTHORISED_REPRESENTATIVE = "authorised_representative"
    DATA_SUBJECT = "data_subject"

    @property
    def label(self) -> str:
        return t(f"domain.role_label_{self.value}")

    @property
    def definition(self) -> str:
        return t(f"domain.role_{self.value}")


class RiskClass(StrEnum):
    """AI Act risk classes, most severe first."""

    PROHIBITED = "prohibited"
    HIGH_RISK_ANNEX_I = "high_risk_annex_i"
    HIGH_RISK_ANNEX_III = "high_risk_annex_iii"
    HIGH_RISK_EXEMPTION = "high_risk_exemption"
    TRANSPARENCY = "transparency"
    GPAI_SYSTEMIC_RISK = "gpai_systemic_risk"
    GPAI = "gpai"
    MINIMAL = "minimal"
    UNCLEAR = "unclear"

    @property
    def label(self) -> str:
        return t(f"domain.risk_class_label_{self.value}")

    @property
    def explanation(self) -> str:
        return t(f"domain.risk_class_{self.value}")

    @property
    def rank(self) -> int:
        """Severity order (0 = most severe), used when several classes apply."""
        return {
            "prohibited": 0,
            "high_risk_annex_i": 1,
            "high_risk_annex_iii": 2,
            "high_risk_exemption": 3,
            "gpai_systemic_risk": 4,
            "gpai": 5,
            "transparency": 6,
            "minimal": 7,
            "unclear": 8,
        }[self.value]


class Severity(StrEnum):
    OBLIGATION = "obligation"
    RECOMMENDATION = "recommendation"
    NOTE = "note"

    @property
    def label(self) -> str:
        return t(f"domain.severity_{self.value}")


class Obligation(BaseModel):
    """A single obligation with legal basis, deadline and required action."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    action_required: str = Field(description="Plain-language instruction")
    legal_basis: tuple[str, ...] = Field(min_length=1, description="Unit ids")
    also_cited: tuple[str, ...] = Field(
        default=(),
        description="Provisions referenced by the action text without founding the "
        "obligation (e.g. Art. 72 AI Act, referenced by Art. 26(5)); cited as "
        "evidence so that no citation in an answer lacks a passage.",
    )
    citation_text: str = Field(description="Citation as displayed, e.g. 'Artikel 9 KI-VO'")
    roles: tuple[Role, ...] = Field(min_length=1)
    risk_classes: tuple[RiskClass, ...] = Field(min_length=1)
    severity: Severity = Severity.OBLIGATION
    applies_from: date | None = None
    evidence_of_compliance: str = Field(default="", description="How compliance is evidenced")
    on_infringement: str = Field(default="", description="Consequence of an infringement")
    caveat: str = Field(
        default="",
        description="Set when the obligation depends on a trait the description does "
        "not mention; the obligation is then listed with this caveat instead "
        "of being silently dropped.",
    )


class RiskIndicator(BaseModel):
    """Reason why a risk class was assigned."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    risk_class: RiskClass
    rule: str = Field(description="Id of the rule that fired")
    rationale: str
    legal_basis: tuple[str, ...]
    confidence: Literal["certain", "likely", "needs_review"] = "likely"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def citations(self) -> tuple[str, ...]:
        """The legal basis as citations in the active language."""
        return tuple(citation_from_id(unit_id) for unit_id in self.legal_basis)

    @property
    def confidence_label(self) -> str:
        return t(f"domain.confidence_{self.confidence}")


class SystemDescription(BaseModel):
    """User-supplied facts about an AI system.

    All fields are optional so that a sparse description still yields a useful
    answer plus follow-up questions instead of nothing.
    """

    model_config = ConfigDict(extra="forbid")

    free_text: str = Field(default="", max_length=20_000, description="Free-text description")
    roles: tuple[Role, ...] = ()
    purpose: str = ""
    field_of_use: str = ""
    affected_group: str = ""
    processes_personal_data: bool | None = None
    special_categories_of_data: bool | None = None
    makes_decisions_about_people: bool | None = None
    human_oversight: bool | None = None
    biometrics: bool | None = None
    emotion_recognition: bool | None = None
    generates_content: bool | None = None
    interacts_with_people: bool | None = None
    embedded_in_product: bool | None = None
    is_gpai_model: bool | None = None
    training_compute_flop: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description="Training compute in FLOP, for Article 51",
    )
    public_body: bool | None = None
    third_country_transfer: bool | None = None
    employee_data: bool | None = None
    employee_count: int | None = Field(default=None, ge=0)
    market: str = Field(default="EU", description="Where the system is offered or used")

    def filled_count(self) -> int:
        """Number of filled fields; decides whether a classification is reliable."""
        values = self.model_dump(exclude={"free_text", "market"})
        return sum(1 for w in values.values() if w not in (None, "", ()))


class Passage(BaseModel):
    """Corpus hit shown as evidence in an answer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    citation: str
    legal_act: LegalAct
    title: str
    excerpt: str
    score: float
    routes: tuple[str, ...] = Field(default=(), description="Retrieval routes that found this hit")


class Classification(BaseModel):
    """Assessment result: risk classes, roles, obligations and open questions."""

    model_config = ConfigDict(extra="forbid")

    risk_classes: tuple[RiskClass, ...]
    indicators: tuple[RiskIndicator, ...]
    roles: tuple[Role, ...]
    obligations: tuple[Obligation, ...]
    open_questions: tuple[str, ...] = Field(
        default=(), description="Missing facts needed for a reliable classification"
    )
    data_protection: tuple[Obligation, ...] = ()
    as_of: date | None = None

    @property
    def most_severe(self) -> RiskClass:
        return (
            min(self.risk_classes, key=lambda k: k.rank) if self.risk_classes else RiskClass.UNCLEAR
        )


class Answer(BaseModel):
    """Final answer returned to the user."""

    model_config = ConfigDict(extra="forbid")

    question: str
    text: str
    evidence: tuple[Passage, ...]
    classification: Classification | None = None
    learning_note: str = Field(default="", description="Short educational note")
    example_cases: tuple[str, ...] = ()
    model: str = Field(default="", description="Model that composed the text")
    without_model: bool = Field(
        default=False, description="True if built from rules and hits only, without an LLM"
    )
    warnings: tuple[str, ...] = ()
    duration_ms: int = 0
