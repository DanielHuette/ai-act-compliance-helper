"""LLM wording layer that may phrase, but never change, the rule-based classification.

Context: The assessor decides what applies; an optional LLM only words the answer within a
time limit, every user input fenced by per-request markers against prompt injection, and the
reply checked afterwards for invented citations. | Input: question, user description,
classification, evidence passages, optional LLM, ``COMPLIANCE_HELPER_LLM_TIMEOUT`` |
Output: an ``Answer`` with text, evidence and warnings.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Protocol

from compliance_helper.domain import Answer, Classification, Passage
from compliance_helper.i18n import t
from compliance_helper.security import sanitize_for_log

logger = logging.getLogger(__name__)

# Caps cost and stops attempts to push the system prompt out of the context window.
MAX_PROMPT_QUESTION_CHARS = 1_000
MAX_PROMPT_DESCRIPTION_CHARS = 6_000
MAX_PASSAGE_CHARS = 1_400
MAX_PASSAGES = 10

#: The SDKs default to 600 s and two retries; a hanging provider would block a worker that long.
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0
LLM_MAX_RETRIES = 1


def llm_timeout_seconds() -> float:
    """Seconds an LLM call may take, from ``COMPLIANCE_HELPER_LLM_TIMEOUT`` (default 30)."""
    try:
        seconds = float(os.environ.get("COMPLIANCE_HELPER_LLM_TIMEOUT", ""))
    except ValueError:
        return DEFAULT_LLM_TIMEOUT_SECONDS
    return seconds if 0 < seconds < float("inf") else DEFAULT_LLM_TIMEOUT_SECONDS


class ModelTimeoutError(TimeoutError):
    """The LLM did not answer within ``seconds``."""

    def __init__(self, seconds: float) -> None:
        super().__init__(f"no answer within {seconds:g} s")
        self.seconds = seconds


def system_prompt() -> str:
    """Return the system prompt in the active language; English answers quote sources as given."""
    return t("answer.system_prompt")


class LanguageModel(Protocol):
    """Interface every LLM provider adapter implements."""

    name: str

    def answers(self, system_prompt: str, prompt: str) -> str: ...


@dataclass
class Anthropic:
    """Claude via the Anthropic API."""

    model: str = "claude-sonnet-4-5"
    api_key: str | None = None
    name: str = ""
    timeout_seconds: float = field(default_factory=llm_timeout_seconds)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.name = f"anthropic/{self.model}"

    def answers(self, system_prompt: str, prompt: str) -> str:
        import anthropic

        api_client = anthropic.Anthropic(
            api_key=self.api_key, timeout=self.timeout_seconds, max_retries=LLM_MAX_RETRIES
        )
        try:
            answer = api_client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APITimeoutError as error:
            raise ModelTimeoutError(self.timeout_seconds) from error
        return "".join(part.text for part in answer.content if getattr(part, "type", "") == "text")


@dataclass
class OpenAI:
    """GPT via the OpenAI API."""

    model: str = "gpt-4.1"
    api_key: str | None = None
    name: str = ""
    timeout_seconds: float = field(default_factory=llm_timeout_seconds)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.name = f"openai/{self.model}"

    def answers(self, system_prompt: str, prompt: str) -> str:
        import openai

        api_client = openai.OpenAI(
            api_key=self.api_key, timeout=self.timeout_seconds, max_retries=LLM_MAX_RETRIES
        )
        try:
            answer = api_client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
        except openai.APITimeoutError as error:
            raise ModelTimeoutError(self.timeout_seconds) from error
        return answer.choices[0].message.content or ""


_ADAPTERS: dict[str, type[Anthropic] | type[OpenAI]] = {
    "anthropic": Anthropic,
    "openai": OpenAI,
}


def model_vendor(model: LanguageModel) -> str:
    """The vendor part of a model name such as ``anthropic/claude-sonnet-4-5``."""
    return model.name.split("/", 1)[0]


def choose_model(requested_model: str | None = None) -> LanguageModel | None:
    """Return the requested LLM, or for ``auto`` the first available one (Claude, then GPT).

    Returns:
        The model adapter, or ``None`` when it is not configured or the request names no known
        vendor; callers then answer from the rule set, which carries the same classification
        and obligations.
    """
    if not requested_model or requested_model == "auto":
        candidates = list(_ADAPTERS.values())
    elif requested_model in _ADAPTERS:
        candidates = [_ADAPTERS[requested_model]]
    else:
        logger.warning("Unknown model request %r, answering from the rule set", requested_model)
        return None

    for model_class in candidates:
        try:
            return model_class()
        except Exception as error:
            logger.info("%s not available: %s", model_class.__name__, sanitize_for_log(error))
    return None


def _truncate(text: str, cap: int) -> str:
    text = text.strip()
    if len(text) <= cap:
        return text
    return text[:cap] + "\n" + t("answer.truncated")


def _fenced(section_key: str, marker: str, body: str) -> str:
    """Wrap ``body`` in begin and end lines that carry the per-request ``marker``."""
    section = t(section_key)
    begin = t("answer.fence_begin", section=section, marker=marker)
    end = t("answer.fence_end", section=section, marker=marker)
    return f"{begin}\n{body}\n{end}"


def build_prompt(
    question: str,
    description: str,
    classification: Classification | None,
    evidence: tuple[Passage, ...],
) -> str:
    """Build the user prompt with section markers the user cannot forge.

    Question, description and evidence each sit between begin and end lines carrying a marker
    that is random per request, so faking a section boundary would require guessing it. The
    classification comes last so the model reads the fact after any injection attempt.
    """
    marker = secrets.token_hex(6)
    parts: list[str] = []

    question_body = (
        f"{t('answer.question_preamble')}\n{_truncate(question, MAX_PROMPT_QUESTION_CHARS)}"
    )
    parts.append(_fenced("answer.section_question", marker, question_body))

    if description.strip():
        body = (
            f"{t('answer.description_preamble')}\n"
            f"{_truncate(description, MAX_PROMPT_DESCRIPTION_CHARS)}"
        )
        parts.append(_fenced("answer.section_description", marker, body))

    if evidence:
        lines = []
        for passage in evidence[:MAX_PASSAGES]:
            excerpt = _truncate(passage.excerpt, MAX_PASSAGE_CHARS)
            lines.append(f"[{passage.citation}] {passage.title}\n{excerpt}")
        body = "{}\n\n{}".format(t("answer.evidence_preamble"), "\n\n".join(lines))
        parts.append(_fenced("answer.section_evidence", marker, body))

    if classification:
        parts.append(
            f"{t('answer.section_classification')}\n{classification_as_text(classification)}"
        )

    parts.append(f"{t('answer.section_task')}\n{t('answer.task')}")
    return "\n\n".join(parts)


def classification_as_text(classification: Classification) -> str:
    """Render the classification as the fixed-fact block of the prompt."""
    lines: list[str] = []
    most_severe = classification.most_severe
    lines.append(
        t(
            "answer.fact_risk_class",
            risk_class=most_severe.label,
            explanation=most_severe.explanation,
        )
    )
    further_classes = [
        risk_class for risk_class in classification.risk_classes if risk_class is not most_severe
    ]
    if further_classes:
        lines.append(
            t(
                "answer.fact_more_classes",
                risk_classes=", ".join(risk_class.label for risk_class in further_classes),
            )
        )
    if classification.roles:
        lines.append(
            t(
                "answer.role_line",
                roles=", ".join(
                    f"{role.label} ({role.definition})" for role in classification.roles
                ),
            )
        )
    else:
        lines.append(t("answer.fact_no_role"))

    for indicator in classification.indicators:
        lines.append(
            t(
                "answer.fact_indicator",
                confidence=indicator.confidence_label,
                rationale=indicator.rationale,
                citations=", ".join(indicator.citations) or t("answer.fact_no_citations"),
            )
        )

    if classification.obligations:
        lines.append(t("answer.fact_ai_act_obligations"))
        for obligation in classification.obligations:
            deadline = (
                t("answer.fact_applies_from", date=obligation.applies_from.isoformat())
                if obligation.applies_from
                else ""
            )
            lines.append(
                f"  - {obligation.title} ({obligation.citation_text}){deadline}: "
                f"{obligation.action_required}"
            )
    if classification.data_protection:
        lines.append(t("answer.fact_data_protection_obligations"))
        for obligation in classification.data_protection:
            lines.append(
                f"  - {obligation.title} ({obligation.citation_text}): {obligation.action_required}"
            )
    if classification.open_questions:
        lines.append(t("answer.fact_open_questions"))
        lines.extend(f"  - {question}" for question in classification.open_questions)
    return "\n".join(lines)


#: German and English citation forms: "Artikel 6" / "Art. 6" / "Article 6(1)(a)", "§ 26" /
#: "Section 26 BDSG", "Anhang III" / "Annex III point 4(a)", "Erwägungsgrund 53" / "recital 53".
_CITATION_IN_TEXT = re.compile(
    r"\b(?:Artikel|Art\.|[Aa]rticles?)\s*(?P<art>\d{1,3})"
    r"|§\s*(?P<sec>\d{1,3}[a-z]?)"
    r"|\bSections?\s+(?P<section>\d{1,3}[a-z]?)"
    r"(?=(?:\(\w{1,3}\))*\s+(?:of\s+the\s+)?(?:BDSG|Federal\s+Data\s+Protection\s+Act))"
    r"|\b(?:Anhang|Annex)\s+(?P<annex>[IVXLC]+)\b"
    r"|\b(?:Erwägungsgr(?:und|ünde)|ErwG\.?|[Rr]ecitals?)\s*(?P<recital>\d{1,3})"
)

_CITATION_IN_ID = re.compile(r"(?<=/)(?:(?:art|sec|recital)-\d{1,3}[a-z]?|annex-[IVXLC]+)(?=/|$)")

_CITATION_DISPLAY = {
    "art": "answer.citation_article",
    "sec": "answer.citation_section",
    "annex": "answer.citation_annex",
    "recital": "answer.citation_recital",
}


def _cited(text: str) -> list[tuple[str, str]]:
    """Return ``(kind, number)`` for every citation in ``text``, in order of appearance."""
    found: list[tuple[str, str]] = []
    for match in _CITATION_IN_TEXT.finditer(text):
        groups = match.groupdict()
        if groups["art"]:
            found.append(("art", groups["art"]))
        elif groups["sec"] or groups["section"]:
            found.append(("sec", groups["sec"] or groups["section"]))
        elif groups["annex"]:
            found.append(("annex", groups["annex"].upper()))
        elif groups["recital"]:
            found.append(("recital", groups["recital"]))
    return found


def unsupported_citations(text: str, evidence: tuple[Passage, ...]) -> list[str]:
    """Return citations in ``text`` that do not occur in the evidence.

    Last safeguard against an invented obligation: not exhaustive, but an answer citing
    Article 77 when no passage contained it is caught, in German or English citation form.
    Tokens are compared exactly, so Article 6 in the evidence does not cover Article 60.
    """
    allowed: set[str] = set()
    for passage in evidence:
        allowed.update(_CITATION_IN_ID.findall(passage.id))
        allowed.update(
            f"{kind}-{number}" for kind, number in _cited(f"{passage.excerpt} {passage.citation}")
        )

    suspicious: list[str] = []
    for kind, number in _cited(text):
        if f"{kind}-{number}" in allowed:
            continue
        display = t(_CITATION_DISPLAY[kind], number=number)
        if display not in suspicious:
            suspicious.append(display)
    return suspicious


def from_rules(
    question: str,
    classification: Classification | None,
    evidence: tuple[Passage, ...],
    learning_note: str = "",
    example_cases: tuple[str, ...] = (),
) -> Answer:
    """Build a plain but complete answer directly from classification and evidence."""
    lines: list[str] = []
    if classification:
        lines.append(
            t("answer.rules_classification", explanation=classification.most_severe.explanation)
        )
        if classification.roles:
            lines.append(
                t("answer.role_line", roles=", ".join(role.label for role in classification.roles))
            )
        lines.append("")
        lines.append(t("answer.rules_why"))
        for indicator in classification.indicators:
            lines.append(f"- {indicator.rationale} [{indicator.confidence_label}]")
        if classification.obligations:
            lines.append("")
            lines.append(t("answer.rules_ai_act_todo"))
            for obligation in classification.obligations:
                deadline = (
                    t("answer.rules_applies_from", date=obligation.applies_from.isoformat())
                    if obligation.applies_from
                    else ""
                )
                lines.append(
                    f"- {obligation.title} ({obligation.citation_text}){deadline}\n"
                    f"  {obligation.action_required}"
                )
        if classification.data_protection:
            lines.append("")
            lines.append(t("answer.rules_data_protection_todo"))
            for obligation in classification.data_protection:
                lines.append(
                    f"- {obligation.title} ({obligation.citation_text})\n"
                    f"  {obligation.action_required}"
                )
        if classification.open_questions:
            lines.append("")
            lines.append(t("answer.rules_more_detail"))
            lines.extend(f"- {question}" for question in classification.open_questions)
    elif evidence:
        lines.append(t("answer.rules_search_found"))
        for passage in evidence[:5]:
            lines.append("")
            lines.append(f"{passage.citation} — {passage.title}")
            lines.append(passage.excerpt[:600])
    else:
        lines.append(t("answer.rules_nothing_found"))

    return Answer(
        question=question,
        text="\n".join(lines),
        evidence=evidence,
        classification=classification,
        learning_note=learning_note,
        example_cases=example_cases,
        model="",
        without_model=True,
        warnings=(t("answer.warning_without_model"),),
    )


def compose(
    question: str,
    description: str,
    classification: Classification | None,
    evidence: tuple[Passage, ...],
    model: LanguageModel | None = None,
    learning_note: str = "",
    example_cases: tuple[str, ...] = (),
) -> Answer:
    """Compose the answer with ``model``, falling back to ``from_rules`` on absence or failure."""
    if model is None:
        return from_rules(question, classification, evidence, learning_note, example_cases)

    started = time.perf_counter()
    prompt = build_prompt(question, description, classification, evidence)
    try:
        text = model.answers(system_prompt(), prompt)
    except Exception as error:
        logger.warning("Model %s did not respond: %s", model.name, sanitize_for_log(error))
        fallback = from_rules(question, classification, evidence, learning_note, example_cases)
        return fallback.model_copy(
            update={"warnings": (*fallback.warnings, _model_failure_warning(error))}
        )

    warnings: list[str] = []
    suspicious = unsupported_citations(text, evidence)
    if suspicious:
        warnings.append(t("answer.warning_unsupported_citations", citations=", ".join(suspicious)))
    if not text.strip():
        return from_rules(question, classification, evidence, learning_note, example_cases)

    return Answer(
        question=question,
        text=text.strip(),
        evidence=evidence,
        classification=classification,
        learning_note=learning_note,
        example_cases=example_cases,
        model=model.name,
        without_model=False,
        warnings=tuple(warnings),
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def _model_failure_warning(error: Exception) -> str:
    """The user-facing note on a failed LLM call; the error itself goes to the log only."""
    if isinstance(error, TimeoutError):
        seconds = getattr(error, "seconds", None) or llm_timeout_seconds()
        return t("answer.warning_model_timeout", seconds=f"{seconds:g}")
    return t("answer.warning_model_unreachable")
