"""Request and response schemas of the web service.

Context: Browsers send loose data (empty fields, strings for booleans); this layer validates it
before it reaches the strict domain model, and responses carry plain-language explanations next
to every technical term. | Input: JSON request bodies | Output: Pydantic models for FastAPI and
the questionnaire in the active language.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from compliance_helper.domain import (
    Answer,
    Classification,
    LegalAct,
    Passage,
    RiskClass,
    Role,
)
from compliance_helper.i18n import t
from compliance_helper.security import MAX_DESCRIPTION_LENGTH, MAX_QUESTION_LENGTH

MAX_TRAITS = 64
MAX_TRAIT_NAME_LENGTH = 64
MAX_TRAIT_TEXT_LENGTH = 500

TraitName = Annotated[str, StringConstraints(max_length=MAX_TRAIT_NAME_LENGTH)]
TraitValue = (
    bool | int | float | Annotated[str, StringConstraints(max_length=MAX_TRAIT_TEXT_LENGTH)]
)

ModelChoice = Literal["auto", "anthropic", "openai", "none"]


class SystemFacts(BaseModel):
    """Roles and questionnaire answers; classify and ask take the same ones, so both agree.

    ``traits`` is an open name-to-value mapping so the questionnaire can grow without schema
    changes; unknown names are reported back rather than silently dropped.
    """

    model_config = ConfigDict(extra="forbid")

    roles: tuple[Role, ...] = Field(default=(), max_length=len(Role))
    traits: dict[TraitName, TraitValue | None] = Field(default_factory=dict, max_length=MAX_TRAITS)


class QuestionRequest(SystemFacts):
    """Full answer request: question, optional description and facts, optional model choice."""

    question: str = Field(
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
        description="The legal question in the user's own words",
    )
    description: str = Field(
        default="",
        max_length=MAX_DESCRIPTION_LENGTH,
        description="The AI system in the user's own words",
    )
    model: ModelChoice | None = Field(
        default=None,
        description="Which LLM words the answer: 'auto' (the operator's model), 'anthropic' or "
        "'openai' (only if it is the operator's model), or 'none' for an answer built from the "
        "rule set only",
    )
    legal_acts_filter: tuple[LegalAct, ...] | None = Field(
        default=None, description="Restrict the search to these legal acts"
    )
    citation_count: int = Field(
        default=8, ge=1, le=20, description="Number of passages cited in the answer"
    )


class ClassificationRequest(SystemFacts):
    """Classification only: no LLM, so fast and reproducible."""

    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)


class SearchRequest(BaseModel):
    """Search only, for users who want to read the sources themselves."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    count: int = Field(default=8, ge=1, le=30)
    legal_acts_filter: tuple[LegalAct, ...] | None = None


class TermExplanation(BaseModel):
    """A technical term with its plain-language explanation, so the UI translates nothing."""

    model_config = ConfigDict(frozen=True)

    id: str
    explanation: str


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: Classification
    most_severe_class: RiskClass
    most_severe_explanation: str
    risk_class_explanations: tuple[TermExplanation, ...]
    role_explanations: tuple[TermExplanation, ...]
    unrecognized_traits: tuple[str, ...] = ()
    rules_as_of: date | None = None
    deadline_caveat: str = ""
    duration_ms: int = 0


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    evidence: tuple[Passage, ...]
    embedding_model: str
    duration_ms: int = 0
    warnings: tuple[str, ...] = ()


class QuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: Answer
    most_severe_class: RiskClass | None = None
    most_severe_explanation: str = ""
    risk_class_explanations: tuple[TermExplanation, ...] = ()
    role_explanations: tuple[TermExplanation, ...] = ()
    rules_as_of: date | None = None
    corpus_as_of: date | None = None
    deadline_caveat: str = ""
    duration_ms: int = 0


class Health(BaseModel):
    """Service health as queried by monitors."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "degraded", "not_ready"]
    corpus_loaded: bool
    index_loaded: bool
    units: int
    embedding_model: str
    llm: str
    corpus_as_of: date | None = None
    rules_as_of: date | None = None
    index_from_file: bool = False
    reranking: bool = Field(
        default=False,
        description="Whether the cross-encoder reranks passages: more accurate, "
        "but very slow without a GPU",
    )
    startup_ms: int = 0
    uptime_seconds: int = 0
    warnings: tuple[str, ...] = ()


class ErrorResponse(BaseModel):
    """Client-safe error: a plain sentence, no internals."""

    model_config = ConfigDict(extra="forbid")

    error: str
    hint: str = ""


QuestionKind = Literal["yes_no", "text", "number", "choice"]


class QuestionnaireItem(BaseModel):
    """One assessor question, prepared for a UI."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Name of the SystemDescription field this question fills")
    question: str = Field(description="The question in plain language")
    kind: QuestionKind
    help_text: str = Field(default="", description="Why the question is asked")
    relevant_for: str = Field(default="", description="Which check depends on the answer")
    options: tuple[TermExplanation, ...] = ()


class Questionnaire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[QuestionnaireItem, ...]
    hint: str


class DeadlineStage(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_value: date
    event: str
    already_in_force: bool


class Deadlines(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation: str
    legal_basis: tuple[str, ...]
    stages: tuple[DeadlineStage, ...]
    caveat: str
    rules_as_of: date | None = None
    version_note: str = ""


# Ordered as the AI Act checks; every id must be a SystemDescription field, which
# check_questionnaire() verifies at startup.
QUESTIONNAIRE_LAYOUT: tuple[tuple[str, QuestionKind], ...] = (
    ("roles", "choice"),
    ("purpose", "text"),
    ("field_of_use", "text"),
    ("affected_group", "text"),
    ("makes_decisions_about_people", "yes_no"),
    ("human_oversight", "yes_no"),
    ("processes_personal_data", "yes_no"),
    ("special_categories_of_data", "yes_no"),
    ("employee_data", "yes_no"),
    ("biometrics", "yes_no"),
    ("emotion_recognition", "yes_no"),
    ("generates_content", "yes_no"),
    ("interacts_with_people", "yes_no"),
    ("embedded_in_product", "yes_no"),
    ("is_gpai_model", "yes_no"),
    ("training_compute_flop", "number"),
    ("public_body", "yes_no"),
    ("third_country_transfer", "yes_no"),
    ("employee_count", "number"),
    ("market", "text"),
)

SELECTABLE_ROLES: tuple[Role, ...] = (
    Role.PROVIDER,
    Role.DEPLOYER,
    Role.IMPORTER,
    Role.DISTRIBUTOR,
    Role.PRODUCT_MANUFACTURER,
    Role.AUTHORISED_REPRESENTATIVE,
)


def role_options() -> tuple[TermExplanation, ...]:
    return tuple(TermExplanation(id=r.value, explanation=r.definition) for r in SELECTABLE_ROLES)


def questionnaire_items() -> tuple[QuestionnaireItem, ...]:
    """Return the questionnaire in the active language; built per call, never cached."""
    return tuple(
        QuestionnaireItem(
            id=item_id,
            kind=kind,
            question=t(f"service.questionnaire.{item_id}.question"),
            help_text=t(f"service.questionnaire.{item_id}.help"),
            relevant_for=t(f"service.questionnaire.{item_id}.relevant_for"),
            options=role_options() if kind == "choice" else (),
        )
        for item_id, kind in QUESTIONNAIRE_LAYOUT
    )


def questionnaire_hint() -> str:
    return t("service.questionnaire.hint")


def check_questionnaire() -> list[str]:
    """Return questionnaire ids that are not ``SystemDescription`` fields.

    Run at startup: a mistyped id would otherwise silently drop the user's answer and skew
    the classification.
    """
    from compliance_helper.domain import SystemDescription

    fields = set(SystemDescription.model_fields)
    return [item_id for item_id, _ in QUESTIONNAIRE_LAYOUT if item_id not in fields]
