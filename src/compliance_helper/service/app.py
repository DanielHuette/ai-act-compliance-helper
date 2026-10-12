"""FastAPI web service: question-flow UI, search page and JSON API.

Context: Loads corpus, search index and rule set once at startup and serves deterministic
classification plus optionally LLM-worded answers, returning plain-sentence errors only, in the
language each request asks for; slow work runs in the threadpool, never on the event loop. |
Input: HTTP requests (language from ``?lang=``, the ``lang`` cookie, ``Accept-Language`` or
``COMPLIANCE_HELPER_LANG``) and ``COMPLIANCE_HELPER_*`` environment variables (see
``.env.example``) | Output: HTML pages, JSON responses and the ``app`` object for uvicorn.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from compliance_helper import paths
from compliance_helper.answer.compose import LanguageModel, choose_model, compose, model_vendor
from compliance_helper.classification.assessor import (
    Assessor,
    RuleSet,
    description_from_text,
    rule_set,
)
from compliance_helper.corpus.build import CASE_LABELS, corpus_file, load
from compliance_helper.corpus.build import build_command as corpus_build_command
from compliance_helper.domain import (
    Classification,
    RiskClass,
    Role,
    SystemDescription,
    Unit,
    UnitKind,
)
from compliance_helper.i18n import (
    DEFAULT_LANGUAGE,
    Language,
    catalog,
    current_language,
    pick,
    t,
    use_language,
)
from compliance_helper.search.embedding import Embedder, HashingEmbedder, choose_embedder
from compliance_helper.search.index import SearchIndex, to_passages
from compliance_helper.search.store import (
    METADATA_SUFFIX,
    VECTORS_SUFFIX,
    build_command,
    index_path,
    sibling,
)
from compliance_helper.security import (
    InputError,
    ServiceNotReadyError,
    check_environment,
    install_log_redaction,
    rate_limiter_from_env,
    sanitize_for_log,
    validate_description,
    validate_question,
)
from compliance_helper.service.schemas import (
    MAX_TRAIT_TEXT_LENGTH,
    SELECTABLE_ROLES,
    ClassificationRequest,
    ClassificationResponse,
    Deadlines,
    DeadlineStage,
    ErrorResponse,
    Health,
    ModelChoice,
    Questionnaire,
    QuestionRequest,
    QuestionResponse,
    SearchRequest,
    SearchResponse,
    SystemFacts,
    TermExplanation,
    check_questionnaire,
    questionnaire_hint,
    questionnaire_items,
)

logger = logging.getLogger("compliance_helper.service")


WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"


def reranking_enabled() -> bool:
    """Whether ``COMPLIANCE_HELPER_RERANK`` enables cross-encoder reranking.

    Off by default: bge-reranker-v2-m3 took a measured 100 s per search without a GPU.
    """
    value = os.environ.get("COMPLIANCE_HELPER_RERANK", "0").strip().lower()
    return value in _ENABLED_WORDS


_ENABLED_WORDS = frozenset(("1", "ja", "true", "an", "ein", "yes", "on"))

# Localhost only; network deployments must set COMPLIANCE_HELPER_CORS_ORIGINS explicitly.
DEFAULT_CORS_ORIGINS = ("http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173")

LANGUAGE_PARAMETER = "lang"
LANGUAGE_COOKIE = "lang"
LANGUAGE_COOKIE_MAX_AGE = 365 * 24 * 60 * 60

# Mounted static files carry their own language; a Content-Language header would mislabel them.
UNLOCALIZED_PATH_PREFIXES = ("/static/", "/classification", "/docs", "/redoc", "/openapi.json")

#: A 20,000-character description in four-byte UTF-8 plus question and questionnaire fits.
DEFAULT_MAX_BODY_BYTES = 128 * 1024
_METHODS_WITH_BODY = frozenset(("POST", "PUT", "PATCH"))

NOT_READY_RETRY_AFTER_SECONDS = 30

_CSP_BASE = (
    "default-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
CONTENT_SECURITY_POLICY = f"{_CSP_BASE}; script-src 'self'; style-src 'self'"
#: web/index.html keeps its styles inline so the page renders without a second request.
QUESTION_FLOW_CONTENT_SECURITY_POLICY = (
    f"{_CSP_BASE}; script-src 'self'; style-src 'self' 'unsafe-inline'"
)
#: FastAPI's API documentation loads Swagger UI and ReDoc from their CDN.
API_DOCS_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; worker-src 'self' blob:; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly"
)
SECURITY_HEADERS: Mapping[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


@dataclass(frozen=True)
class Notice:
    """A service warning kept as message key and values, translated each time it is shown."""

    key: str
    values: Mapping[str, Any] = field(default_factory=dict)

    def text(self) -> str:
        """The notice in the active language; a ``Language`` value is shown by its name."""
        values: dict[str, Any] = {
            name: t(f"search.language_{value.value}") if isinstance(value, Language) else value
            for name, value in self.values.items()
        }
        return t(self.key, **values)


@dataclass
class ServiceState:
    """Everything loaded at startup and shared across requests, with corpus and index per language.

    ``units``, ``search_index``, ``index_from_file`` and ``corpus_as_of`` answer for the language
    of the current request; all indexes share one embedding model.
    """

    units_by_language: dict[Language, list[Unit]] = field(default_factory=dict)
    indexes: dict[Language, SearchIndex] = field(default_factory=dict)
    indexes_from_file: set[Language] = field(default_factory=set)
    corpus_as_of_by_language: dict[Language, date] = field(default_factory=dict)
    assessor: Assessor | None = None
    rules: RuleSet | None = None
    llm: LanguageModel | None = None
    startup_ms: int = 0
    started_at: float = 0.0
    notices: list[Notice] = field(default_factory=list)

    @property
    def units(self) -> list[Unit]:
        return self.units_by_language.get(current_language(), [])

    @property
    def search_index(self) -> SearchIndex | None:
        return self.indexes.get(current_language())

    @property
    def index_from_file(self) -> bool:
        return current_language() in self.indexes_from_file

    @property
    def corpus_as_of(self) -> date | None:
        return self.corpus_as_of_by_language.get(current_language())

    @property
    def rules_as_of(self) -> date | None:
        return self.rules.as_of if self.rules else None

    def require_search_index(self) -> SearchIndex:
        """Return the index of the request language, or explain which index is missing.

        Raises:
            ServiceNotReadyError: If the index of the request language is not loaded.
        """
        if self.search_index is not None:
            return self.search_index
        language = current_language()
        if language is DEFAULT_LANGUAGE:
            raise ServiceNotReadyError(t("service.search_index_not_loaded"))
        raise ServiceNotReadyError(
            t(
                "service.search_index_missing_language",
                language_name=t(f"search.language_{language.value}"),
                command=build_command(language),
            )
        )

    def require_assessor(self) -> tuple[Assessor, RuleSet]:
        """Return assessor and rule set, which classification needs and nothing else.

        Raises:
            ServiceNotReadyError: If the rule set could not be loaded at startup.
        """
        if self.assessor is None or self.rules is None:
            raise ServiceNotReadyError(t("service.assessor_not_loaded"))
        return self.assessor, self.rules

    @property
    def llm_name(self) -> str:
        return str(self.llm.name) if self.llm is not None else t("service.llm_none")

    @property
    def warnings(self) -> list[str]:
        """Warnings in the active language; environment checks are re-run because they are cheap."""
        return [*check_environment(), *(notice.text() for notice in self.notices)]

    @property
    def embedding_model(self) -> str:
        return self.search_index.embedder.name if self.search_index else "none"

    @property
    def readiness(self) -> str:
        if self.assessor is None or not self.units or self.search_index is None:
            return "not_ready"
        if self.warnings:
            return "degraded"
        return "ready"


def _build_commands(languages: Sequence[Language]) -> str:
    return " · ".join(build_command(language) for language in languages)


def _in_memory_embedder(
    missing: list[Language], loaded: Embedder | None
) -> tuple[Embedder, Notice | None]:
    """Choose the embedder for indexes built in memory because no stored one could be used.

    Defaults to the hashing fallback even if a real model is requested: bge-m3 needs about
    2 s per passage on CPU, i.e. more than an hour per language. ``COMPLIANCE_HELPER_BUILD_INDEX=1``
    opts into the slow build, reusing the model a stored index already loaded.

    Returns:
        ``(embedder, notice)``; ``notice`` explains a requested model that was replaced.
    """
    requested = os.environ.get("COMPLIANCE_HELPER_EMBEDDING", "").strip()
    if _fallback_requested() or not requested or requested == HashingEmbedder.name:
        return HashingEmbedder(), None
    permission = os.environ.get("COMPLIANCE_HELPER_BUILD_INDEX", "0").strip().lower()
    if permission not in _ENABLED_WORDS:
        return HashingEmbedder(), Notice(
            "service.warning_index_build_slow",
            {
                "model": requested,
                "files": ", ".join(
                    sibling(index_path(language), suffix).name
                    for language in missing
                    for suffix in (VECTORS_SUFFIX, METADATA_SUFFIX)
                ),
                "command": _build_commands(missing),
            },
        )
    if loaded is not None and loaded.name == requested:
        return loaded, None
    return choose_embedder(requested), None


def _fallback_requested() -> bool:
    """An explicit fallback request wins over stored indexes, so fast test runs load no model."""
    requested = os.environ.get("COMPLIANCE_HELPER_EMBEDDING", "").strip().lower()
    return requested in {"fallback", "hashing", HashingEmbedder.name}


def _load_corpora(service_state: ServiceState, languages: tuple[Language, ...]) -> None:
    for language in languages:
        try:
            units = load(language)
        except FileNotFoundError as error:
            service_state.notices.append(
                Notice(
                    "service.warning_corpus_missing",
                    {
                        "corpus": str(corpus_file(language)),
                        "command": corpus_build_command(language),
                    },
                )
            )
            logger.error("Corpus (%s) not loaded: %s", language.value, sanitize_for_log(error))
            continue
        service_state.units_by_language[language] = units
        as_of = max((unit.as_of for unit in units if unit.as_of), default=None)
        if as_of is not None:
            service_state.corpus_as_of_by_language[language] = as_of


def _stored_index(
    service_state: ServiceState, language: Language, units: list[Unit], embedder: Embedder | None
) -> SearchIndex | None:
    """Load the stored index of ``language``; a problem becomes a notice naming the language."""
    try:
        index = SearchIndex.load(language, units, embedder)
    except Exception as error:
        service_state.notices.append(
            Notice(
                "service.warning_index_unavailable",
                {"language_name": language, "command": build_command(language)},
            )
        )
        logger.warning("Search index (%s) not loaded: %s", language.value, sanitize_for_log(error))
        return None
    service_state.indexes_from_file.add(language)
    return index


def _load_indexes(service_state: ServiceState) -> None:
    """Load the index of every loaded corpus, sharing one embedding model between them.

    A language without a usable stored index gets one built in memory, with a notice naming the
    build command: the packaged app ships no index, and a missing one must not disable search.
    """
    shared: Embedder | None = None
    if not _fallback_requested():
        for language, units in service_state.units_by_language.items():
            index = _stored_index(service_state, language, units, shared)
            if index is not None:
                service_state.indexes[language] = index
                shared = shared or index.embedder
    missing = [
        language
        for language in service_state.units_by_language
        if language not in service_state.indexes
    ]
    if not missing:
        return
    embedder, notice = _in_memory_embedder(missing, shared)
    for language in missing:
        index = SearchIndex(service_state.units_by_language[language], embedder, language)
        index.build()
        service_state.indexes[language] = index
    if notice is not None:
        service_state.notices.append(notice)
    elif embedder.name == HashingEmbedder.name:
        service_state.notices.append(
            Notice("service.warning_hashing_fallback", {"command": _build_commands(missing)})
        )


def _load_rules(service_state: ServiceState) -> None:
    """Load assessor and rule set; they need only the rule files, not corpus or index."""
    try:
        service_state.rules = rule_set()
        service_state.assessor = Assessor()
    except Exception as error:
        service_state.assessor, service_state.rules = None, None
        service_state.notices.append(Notice("service.warning_rules_missing"))
        logger.error("Rule set not loaded: %s", sanitize_for_log(error))


def _load_purpose_matching(service_state: ServiceState) -> None:
    """Load purpose matching now, reusing the search index's embedding model.

    Loading it here keeps the minutes the cross-encoder needs out of the first classification;
    if it stays off, a notice names the reason, because classification then relies on the rule
    keywords alone.
    """
    if service_state.assessor is None:
        return
    matcher = service_state.assessor.purpose_matcher()
    if matcher is None:
        service_state.notices.append(Notice("service.warning_purpose_matching_no_model"))
        return
    index_embedder = next(
        (
            index.embedder
            for index in service_state.indexes.values()
            if index.embedder.name != HashingEmbedder.name
        ),
        None,
    )
    if index_embedder is not None:
        matcher.share_embedder(index_embedder)
    if matcher.load():
        return
    if matcher.unavailable_reason.startswith("COMPLIANCE_HELPER_"):
        service_state.notices.append(
            Notice(
                "service.warning_purpose_matching_switched_off",
                {"setting": matcher.unavailable_reason},
            )
        )
    else:
        service_state.notices.append(Notice("service.warning_purpose_matching_no_model"))


def _load_llm(service_state: ServiceState, with_llm: bool) -> None:
    requested_model = os.environ.get("COMPLIANCE_HELPER_MODEL", "auto").strip().lower()
    if not with_llm or requested_model in ("none", "rules"):
        logger.info("LLM disabled, answers come from the rule set")
        return
    # Chosen once, not per request: the reachability check costs up to 3 s.
    service_state.llm = choose_model(requested_model)
    if service_state.llm is None:
        service_state.notices.append(Notice("service.warning_no_llm"))


def _startup_summary(service_state: ServiceState) -> str:
    parts = []
    for language, units in service_state.units_by_language.items():
        index = service_state.indexes.get(language)
        model = index.embedder.name if index else "no"
        parts.append(f"{language.value}: {len(units)} units, {model} index")
    return "; ".join(parts) or "no corpus"


def load_service_state(
    with_llm: bool = True,
    languages: tuple[Language, ...] = tuple(Language),
    with_purposes: bool = True,
) -> ServiceState:
    """Load corpora, search indexes, rule set, purpose matching and LLM once at startup.

    Args:
        with_llm: ``False`` skips LLM discovery (up to 3 s and an irrelevant warning), e.g. for
            the CLI ``search`` command.
        languages: Languages whose corpus and index are loaded; the CLI loads only its own,
            because each index holds about 65 MB.
        with_purposes: ``False`` skips loading purpose matching, e.g. for the CLI ``search``
            command, which classifies nothing.
    """
    install_log_redaction()
    started = time.perf_counter()
    service_state = ServiceState(started_at=time.time())

    missing_fields = check_questionnaire()
    if missing_fields:
        service_state.notices.append(
            Notice("service.warning_questionnaire_fields", {"fields": ", ".join(missing_fields)})
        )

    _load_corpora(service_state, languages)
    _load_indexes(service_state)
    _load_rules(service_state)
    if with_purposes:
        _load_purpose_matching(service_state)
    _load_llm(service_state, with_llm)

    service_state.startup_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Started in %d ms (%s), wording with %s",
        service_state.startup_ms,
        _startup_summary(service_state),
        service_state.llm_name,
    )
    for warning in service_state.warnings:
        logger.warning("%s", sanitize_for_log(warning))
    return service_state


def _explain_risk_classes(risk_classes: tuple[RiskClass, ...]) -> tuple[TermExplanation, ...]:
    return tuple(
        TermExplanation(id=risk_class.value, explanation=risk_class.explanation)
        for risk_class in risk_classes
    )


def _explain_roles(roles: tuple[Role, ...]) -> tuple[TermExplanation, ...]:
    return tuple(TermExplanation(id=role.value, explanation=role.definition) for role in roles)


def _learning_note_and_cases(units: list[Unit]) -> tuple[str, tuple[str, ...]]:
    """Extract the learning note of the best-matching case example and up to five case titles.

    Case examples are ordinary corpus units whose text contains a "Worauf es ankommt:" ("What
    matters:") section in the language of the corpus; that sentence is surfaced separately
    instead of staying buried in the passage.
    """
    label = CASE_LABELS[current_language()]["learning_note"] + ":"
    note = ""
    titles: list[str] = []
    for unit in units:
        if unit.kind is not UnitKind.EXAMPLE:
            continue
        titles.append(unit.title or unit.number)
        if note:
            continue
        for paragraph in unit.text.split("\n\n"):
            if paragraph.startswith(label):
                note = paragraph.split(":", 1)[1].strip()
                break
    return note, tuple(titles[:5])


# Browsers send "ja", "true" and "1" for the same answer; none of them is a bool.
_TRUTHY = frozenset(("true", "ja", "1", "yes", "wahr", "on"))
_FALSY = frozenset(("false", "nein", "0", "no", "falsch", "off"))


def _parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _TRUTHY:
        return True
    if text in _FALSY:
        return False
    return None


def _non_negative_number(value: object) -> float:
    """Parse a count or an amount of compute.

    Raises:
        ValueError: For text that is no number, a negative number, infinity or NaN.
    """
    if isinstance(value, bool):
        raise ValueError(value)
    try:
        number = float(str(value).strip())
    except OverflowError as error:
        raise ValueError(value) from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(value)
    return number


def _trait_value(field_type: str, raw: object) -> object:
    """Convert a questionnaire answer to the type of its ``SystemDescription`` field.

    Returns:
        The converted value, or ``None`` for "don't know".

    Raises:
        ValueError: For a value the field cannot take.
    """
    if "bool" in field_type:
        return _parse_bool(raw)
    if "float" in field_type:
        return _non_negative_number(raw)
    if "int" in field_type:
        return int(_non_negative_number(raw))
    return str(raw)[:MAX_TRAIT_TEXT_LENGTH] if raw not in (None, "") else None


def build_description(text: str, facts: SystemFacts) -> tuple[SystemDescription, tuple[str, ...]]:
    """Build the ``SystemDescription`` from sanitised free text, roles and questionnaire traits.

    Explicit traits override what the free text suggests: a ticked answer outweighs a keyword
    hint.

    Returns:
        The description and the sorted names of traits that were unknown or unparseable.
    """
    values: dict[str, Any] = description_from_text(text).model_dump()
    if facts.roles:
        values["roles"] = tuple(facts.roles)

    fields = SystemDescription.model_fields
    unrecognized: set[str] = set()
    for name, raw in facts.traits.items():
        if name == "roles":
            continue
        if name not in fields or name == "free_text":
            unrecognized.add(name)
            continue
        try:
            value = _trait_value(str(fields[name].annotation), raw)
        except ValueError:
            unrecognized.add(name)
            continue
        if value is not None:
            values[name] = value

    return SystemDescription(**values), tuple(sorted(unrecognized))


def _has_facts(facts: SystemFacts) -> bool:
    return bool(facts.roles) or any(value not in (None, "") for value in facts.traits.values())


def classify(
    assessor: Assessor, text: str, facts: SystemFacts
) -> tuple[Classification, tuple[str, ...]]:
    """Classify sanitised ``text`` with roles and traits; one path for classify and ask alike.

    Returns:
        The classification and the names of traits that were not taken into account.
    """
    description, unrecognized = build_description(text, facts)
    return assessor.check(description), unrecognized


def answer_model(
    configured: LanguageModel | None, requested: ModelChoice | None
) -> tuple[LanguageModel | None, str]:
    """Pick the model that words an answer; a client can never enable one the operator did not.

    Returns:
        ``(model, warning)``: the operator's model or ``None``, and a sentence for the user when
        the request named a vendor that is not the operator's model.
    """
    if requested == "none":
        return None, ""
    if requested in (None, "auto"):
        return configured, ""
    if configured is not None and model_vendor(configured) == requested:
        return configured, ""
    return None, t("service.model_not_enabled", model=requested)


def _error_response(status_code: int, message: str, hint: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content=ErrorResponse(error=message, hint=hint).model_dump()
    )


def _package_version() -> str:
    """Read the version from package metadata so it cannot drift from pyproject.toml."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("ai-act-compliance-helper")
    except PackageNotFoundError:
        return "unknown"


def _supported_language(code: str | None) -> Language | None:
    value = (code or "").strip().lower()
    return next((language for language in Language if language.value == value), None)


def requested_language(connection: HTTPConnection) -> Language | None:
    """Return the language named by ``?lang=``, or ``None`` if absent or unsupported."""
    return _supported_language(connection.query_params.get(LANGUAGE_PARAMETER))


def chosen_language(connection: HTTPConnection) -> Language | None:
    """Return the language the visitor picked explicitly, by ``?lang=`` or the ``lang`` cookie."""
    return requested_language(connection) or _supported_language(
        connection.cookies.get(LANGUAGE_COOKIE)
    )


def service_default_language() -> Language:
    """The operator's default from ``COMPLIANCE_HELPER_LANG``, else German."""
    return _supported_language(os.environ.get("COMPLIANCE_HELPER_LANG")) or DEFAULT_LANGUAGE


def request_language(connection: HTTPConnection) -> Language:
    """Resolve the language: ``?lang=``, the cookie, the browser, then the operator's default."""
    return chosen_language(connection) or Language.from_accept_language(
        connection.headers.get("accept-language"), default=service_default_language()
    )


def question_flow_address(connection: HTTPConnection) -> str:
    """``/classification/`` with the query of ``connection`` and any explicit language choice.

    The static question flow cannot read the ``lang`` cookie, so a choice made by cookie travels
    as ``?lang=`` and the page opens in the language the visitor asked for.
    """
    query = connection.url.query
    cookie_language = _supported_language(connection.cookies.get(LANGUAGE_COOKIE))
    if requested_language(connection) is None and cookie_language is not None:
        language_query = f"{LANGUAGE_PARAMETER}={cookie_language.value}"
        query = f"{query}&{language_query}" if query else language_query
    return f"/classification/?{query}" if query else "/classification/"


def _language_cookie(language: Language) -> str:
    return (
        f"{LANGUAGE_COOKIE}={language.value}; Max-Age={LANGUAGE_COOKIE_MAX_AGE}; "
        "Path=/; SameSite=Lax"
    )


class LanguageMiddleware:
    """Run each HTTP request inside ``use_language`` and label the response accordingly.

    Pure ASGI rather than ``BaseHTTPMiddleware``: the request runs in this task, so the
    language reaches every inner middleware, exception handler and threadpool call.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        language = request_language(connection)
        chosen = requested_language(connection)
        localized = not str(scope["path"]).startswith(UNLOCALIZED_PATH_PREFIXES)

        async def send_with_language(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if localized:
                    headers["Content-Language"] = language.value
                    headers.add_vary_header("Accept-Language")
                    headers.add_vary_header("Cookie")
                if chosen is not None:
                    headers.append("Set-Cookie", _language_cookie(chosen))
            await send(message)

        with use_language(language):
            await self.app(scope, receive, send_with_language)


def content_security_policy(path: str) -> str:
    """The policy for ``path``: strict everywhere except the pages that need more."""
    if path.startswith(("/docs", "/redoc")):
        return API_DOCS_CONTENT_SECURITY_POLICY
    if path.startswith("/classification"):
        return QUESTION_FLOW_CONTENT_SECURITY_POLICY
    return CONTENT_SECURITY_POLICY


class SecurityHeadersMiddleware:
    """Add CSP, framing, sniffing, referrer and permissions headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        policy = content_security_policy(str(scope["path"]))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                headers.setdefault("Content-Security-Policy", policy)
            await send(message)

        await self.app(scope, receive, send_with_headers)


def max_body_bytes() -> int:
    """Request-body limit from ``COMPLIANCE_HELPER_MAX_BODY_BYTES`` (default 128 KiB)."""
    try:
        limit = int(os.environ.get("COMPLIANCE_HELPER_MAX_BODY_BYTES", ""))
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES
    return limit if limit > 0 else DEFAULT_MAX_BODY_BYTES


async def _bounded_body(scope: Scope, receive: Receive, limit: int) -> bytes | None:
    """Read the whole request body, or return ``None`` as soon as it exceeds ``limit`` bytes."""
    declared = Headers(scope=scope).get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return None
    chunks: list[bytes] = []
    size = 0
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunk = message.get("body", b"")
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay(body: bytes, receive: Receive) -> Receive:
    """A ``receive`` that hands out the already-read ``body`` once, then defers to the server."""
    delivered = False

    async def replay() -> Message:
        nonlocal delivered
        if delivered:
            return await receive()
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay


class BodySizeLimitMiddleware:
    """Reject request bodies above ``limit`` bytes with 413 before any parsing happens."""

    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _METHODS_WITH_BODY:
            await self.app(scope, receive, send)
            return
        body = await _bounded_body(scope, receive, self.limit)
        if body is None:
            response = _error_response(
                413,
                t("service.http_413"),
                t("service.http_413_hint", kilobytes=self.limit // 1024),
            )
            await response(scope, receive, send)
            return
        await self.app(scope, _replay(body, receive), send)


def format_date(value: date | None) -> str:
    """Format a data-version date the way readers of the active language expect."""
    if value is None:
        return t("webui.unknown")
    if current_language() is Language.DE:
        return value.strftime("%d.%m.%Y")
    return value.isoformat()


def format_count(value: int) -> str:
    """Group thousands by hand; setting the process locale would affect every request."""
    grouped = f"{value:,}"
    return grouped.replace(",", ".") if current_language() is Language.DE else grouped


def browser_texts() -> dict[str, Any]:
    """UI strings for app.js, embedded in the page as a JSON data block."""
    prefix = "webui.js."
    texts = catalog(current_language())
    return {
        "lang": current_language().value,
        "text": {
            key.removeprefix(prefix): text for key, text in texts.items() if key.startswith(prefix)
        },
        "roles": {role.value: t(f"webui.role.{role.value}") for role in SELECTABLE_ROLES},
    }


_HTTP_ERROR_KEYS: dict[int, tuple[str, str]] = {
    404: ("service.http_404", "service.http_404_hint"),
    405: ("service.http_405", "service.http_405_hint"),
    413: ("service.http_413", ""),
    429: ("service.http_429", ""),
}

#: Location parts pydantic appends for the member of a union or a dict key; not field names.
_LOCATION_TAGS = frozenset(("bool", "int", "float", "str", "constrained-str", "[key]"))


def _field_message(error_type: str, field_path: str) -> str:
    if error_type == "missing":
        return t("service.validation_missing", field=field_path)
    if "too_long" in error_type or "max_length" in error_type:
        return t("service.validation_too_long", field=field_path)
    if "too_short" in error_type or "min_length" in error_type:
        return t("service.validation_too_short", field=field_path)
    if error_type == "extra_forbidden":
        return t("service.validation_extra_forbidden", field=field_path)
    if "enum" in error_type or error_type == "literal_error":
        return t("service.validation_enum", field=field_path)
    return t("service.validation_invalid", field=field_path)


def validation_failure(errors: Sequence[Any]) -> tuple[int, str]:
    """Turn Pydantic validation errors into a status and short user-facing sentences.

    A body that is no JSON object is the client's syntax error (400); a JSON object with wrong
    fields is unprocessable content (422). Union members and dict keys are reported once, under
    the field the user knows, with "too long" winning over "invalid".
    """
    status = 422
    by_field: dict[str, str] = {}
    for entry in errors:
        location = [part for part in entry.get("loc", ()) if part != "body"]
        error_type = str(entry.get("type", ""))
        if error_type == "json_invalid":
            status = 400
            by_field.setdefault("", t("service.validation_json_invalid"))
            continue
        while location and location[-1] in _LOCATION_TAGS:
            location.pop()
        if not location:
            status = 400
            by_field.setdefault("", t("service.validation_body_shape"))
            continue
        field_path = ".".join(str(part) for part in location)
        if field_path not in by_field or "too_long" in error_type:
            by_field[field_path] = _field_message(error_type, field_path)
    messages = list(by_field.values())[:6]
    return status, " ".join(messages) or t("service.validation_shape")


def proxy_settings() -> dict[str, Any]:
    """uvicorn settings that trust ``X-Forwarded-For`` only from configured proxies.

    uvicorn trusts the header from 127.0.0.1 by default, so any local process could choose the
    address the rate limit counts. ``COMPLIANCE_HELPER_TRUSTED_PROXIES`` (comma-separated
    addresses or networks) names the reverse proxies whose header is believed; without it the
    header is ignored.
    """
    trusted = [
        address.strip()
        for address in os.environ.get("COMPLIANCE_HELPER_TRUSTED_PROXIES", "").split(",")
        if address.strip()
    ]
    if not trusted:
        return {"proxy_headers": False}
    return {"proxy_headers": True, "forwarded_allow_ips": trusted}


def build_app() -> FastAPI:
    """Create the FastAPI app; a factory so tests can build isolated instances."""

    install_log_redaction()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.service_state = await asyncio.to_thread(load_service_state)
        app.state.rate_limiter = rate_limiter_from_env()
        yield

    app = FastAPI(
        title="AI Act Compliance Helper",
        description="Cited information on the EU AI Act and data protection law. Not legal advice.",
        version=_package_version(),
        lifespan=lifespan,
        debug=False,
    )

    def service_state() -> ServiceState:
        loaded: ServiceState = app.state.service_state
        return loaded

    origins = [
        origin.strip()
        for origin in os.environ.get(
            "COMPLIANCE_HELPER_CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(BodySizeLimitMiddleware, limit=max_body_bytes())

    @app.middleware("http")
    async def rate_limit_and_timing(request: Request, call_next: Callable) -> Response:
        """Apply the per-address rate limit to ``/api/`` and add ``X-Duration-ms``."""
        address = request.client.host if request.client else "unknown"
        # UI and /health stay unlimited so a monitor polling every minute cannot lock itself out.
        if request.url.path.startswith("/api/"):
            rate_limiter = getattr(app.state, "rate_limiter", None)
            if rate_limiter is not None:
                allowed, retry_after = rate_limiter.check(address)
                if not allowed:
                    response = _error_response(
                        429, rate_limiter.message(retry_after), t("service.rate_limit_hint")
                    )
                    response.headers["Retry-After"] = str(retry_after)
                    return response

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as error:
            # Last line of defence: never leak a stack trace to the client.
            logger.exception(
                "Unhandled error on %s: %s",
                sanitize_for_log(request.url.path),
                sanitize_for_log(error),
            )
            return _error_response(
                500, t("service.error_unexpected"), t("service.error_unexpected_hint_retry")
            )
        duration = int((time.perf_counter() - started) * 1000)
        response.headers["X-Duration-ms"] = str(duration)
        completed: Response = response
        return completed

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LanguageMiddleware)

    @app.exception_handler(InputError)
    async def handle_input_error(_request: Request, error: InputError) -> JSONResponse:
        return _error_response(400, str(error))

    @app.exception_handler(ServiceNotReadyError)
    async def handle_not_ready(_request: Request, error: ServiceNotReadyError) -> JSONResponse:
        response = _error_response(503, str(error))
        response.headers["Retry-After"] = str(NOT_READY_RETRY_AFTER_SECONDS)
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        status, message = validation_failure(error.errors())
        return _error_response(status, message, t("service.validation_hint"))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        """Return Starlette HTTP errors in the same ``ErrorResponse`` shape as all other errors."""
        if error.status_code in _HTTP_ERROR_KEYS:
            message_key, hint_key = _HTTP_ERROR_KEYS[error.status_code]
            message, hint = t(message_key), t(hint_key) if hint_key else ""
        else:
            message, hint = t("service.http_other", code=error.status_code), ""
        return _error_response(error.status_code, message, hint)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, error: Exception) -> JSONResponse:
        """Runs in Starlette's outermost layer, outside ``LanguageMiddleware``."""
        logger.exception(
            "Error on %s: %s", sanitize_for_log(request.url.path), sanitize_for_log(error)
        )
        with use_language(request_language(request)):
            return _error_response(
                500, t("service.error_unexpected"), t("service.error_unexpected_hint")
            )

    templates = Jinja2Templates(directory=str(WEBUI_DIR / "templates"))
    templates.env.globals["t"] = t
    app.mount("/static", StaticFiles(directory=str(WEBUI_DIR / "static")), name="static")

    # The question flow is the same static site as the public web version
    # (parity checked by scripts/check_parity.py).
    question_flow_dir = paths.root() / "web"
    if question_flow_dir.is_dir():
        app.mount(
            "/classification",
            StaticFiles(directory=str(question_flow_dir), html=True),
            name="classification",
        )

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def index_redirect(request: Request) -> Response:
            return RedirectResponse(question_flow_address(request), status_code=307)

        favicon = question_flow_dir / "favicon.svg"

        @app.get("/favicon.svg", include_in_schema=False)
        async def favicon_file() -> Response:
            if not favicon.is_file():
                raise StarletteHTTPException(status_code=404)
            return FileResponse(favicon, media_type="image/svg+xml")

    @app.get("/search", response_class=HTMLResponse, include_in_schema=False)
    def search_page(request: Request) -> Response:
        loaded = service_state()
        rules = loaded.rules
        return templates.TemplateResponse(
            request,
            "page.html",
            {
                "lang": current_language().value,
                "languages": [
                    (language.value, t("webui.language_name", language)) for language in Language
                ],
                "corpus_as_of": format_date(loaded.corpus_as_of),
                "rules_as_of": format_date(loaded.rules_as_of),
                "units_text": format_count(len(loaded.units)),
                "embedding_model": loaded.embedding_model,
                "llm": loaded.llm_name,
                "deadline_caveat": rules.deadline_caveat if rules else "",
                "version_note_text": rules.version_note_text if rules else "",
                "restricted": bool(loaded.notices),
                "questionnaire": questionnaire_items(),
                "questionnaire_hint": questionnaire_hint(),
                "browser_texts": browser_texts(),
            },
        )

    @app.get("/health", response_model=Health, summary="Service health")
    async def health() -> Health:
        loaded = service_state()
        return Health(
            status=loaded.readiness,  # type: ignore[arg-type]
            corpus_loaded=bool(loaded.units),
            index_loaded=loaded.search_index is not None,
            units=len(loaded.units),
            embedding_model=loaded.embedding_model,
            llm=loaded.llm_name,
            corpus_as_of=loaded.corpus_as_of,
            rules_as_of=loaded.rules_as_of,
            index_from_file=loaded.index_from_file,
            reranking=reranking_enabled(),
            startup_ms=loaded.startup_ms,
            uptime_seconds=int(time.time() - loaded.started_at),
            warnings=tuple(loaded.warnings),
        )

    @app.post(
        "/api/classify",
        response_model=ClassificationResponse,
        summary="Classification only, without an LLM",
    )
    def classification(request: ClassificationRequest) -> ClassificationResponse:
        assessor, rules = service_state().require_assessor()
        started = time.perf_counter()
        text = validate_description(request.description)
        if not text and not _has_facts(request):
            raise InputError(t("security.description_empty"))
        result, unrecognized = classify(assessor, text, request)
        return ClassificationResponse(
            classification=result,
            most_severe_class=result.most_severe,
            most_severe_explanation=result.most_severe.explanation,
            risk_class_explanations=_explain_risk_classes(result.risk_classes),
            role_explanations=_explain_roles(result.roles),
            unrecognized_traits=unrecognized,
            rules_as_of=rules.as_of,
            deadline_caveat=rules.deadline_caveat,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    @app.post("/api/search", response_model=SearchResponse, summary="Search the legal corpus only")
    def search(request: SearchRequest) -> SearchResponse:
        search_index = service_state().require_search_index()
        started = time.perf_counter()
        question = validate_question(request.question)
        hits = search_index.search(
            question,
            count=request.count,
            legal_acts_filter=request.legal_acts_filter,
            rerank=reranking_enabled(),
        )
        warnings: list[str] = []
        if search_index.embedder.name == HashingEmbedder.name:
            warnings.append(t("service.warning_search_fallback"))
        return SearchResponse(
            question=question,
            evidence=to_passages(hits),
            embedding_model=search_index.embedder.name,
            duration_ms=int((time.perf_counter() - started) * 1000),
            warnings=tuple(warnings),
        )

    @app.post(
        "/api/ask",
        response_model=QuestionResponse,
        summary="Full answer: classification, obligations, passages",
    )
    def ask_question(request: QuestionRequest) -> QuestionResponse:
        loaded = service_state()
        assessor, rules = loaded.require_assessor()
        search_index = loaded.require_search_index()
        started = time.perf_counter()
        question = validate_question(request.question)
        description_text = validate_description(request.description)

        # Without a description the question itself describes the system, as on /api/classify.
        result, _unrecognized = classify(assessor, description_text or question, request)

        search_text = f"{question}\n{description_text}" if description_text else question
        hits = search_index.search(
            search_text[:4000],
            count=request.citation_count,
            legal_acts_filter=request.legal_acts_filter,
            rerank=reranking_enabled(),
        )
        evidence = to_passages(hits)
        learning_note, cases = _learning_note_and_cases([hit.unit for hit in hits])

        model, model_warning = answer_model(loaded.llm, request.model)
        answer = compose(
            question,
            description_text,
            result,
            evidence,
            model=model,
            learning_note=learning_note,
            example_cases=cases,
        )
        duration = int((time.perf_counter() - started) * 1000)
        warnings = (*answer.warnings, model_warning) if model_warning else answer.warnings
        answer = answer.model_copy(update={"duration_ms": duration, "warnings": warnings})

        return QuestionResponse(
            answer=answer,
            most_severe_class=result.most_severe,
            most_severe_explanation=result.most_severe.explanation,
            risk_class_explanations=_explain_risk_classes(result.risk_classes),
            role_explanations=_explain_roles(result.roles),
            rules_as_of=rules.as_of,
            corpus_as_of=loaded.corpus_as_of,
            deadline_caveat=rules.deadline_caveat,
            duration_ms=duration,
        )

    @app.get(
        "/api/questionnaire",
        response_model=Questionnaire,
        summary="Questionnaire used by the assessor",
    )
    async def questionnaire() -> Questionnaire:
        return Questionnaire(items=questionnaire_items(), hint=questionnaire_hint())

    @app.get(
        "/api/deadlines",
        response_model=Deadlines,
        summary="Application dates under Article 113 with caveat",
    )
    async def deadlines() -> Deadlines:
        _assessor, rules = service_state().require_assessor()
        raw = rules.risk_classes_rules.get("deadlines") or {}
        today = date.today()
        stages: list[DeadlineStage] = []
        for stage in rules.deadlines:
            date_value = stage.get("date")
            if not isinstance(date_value, date):
                try:
                    date_value = date.fromisoformat(str(date_value))
                except ValueError:
                    continue
            stages.append(
                DeadlineStage(
                    date_value=date_value,
                    event=" ".join(str(pick(stage.get("event", ""))).split()),
                    already_in_force=date_value <= today,
                )
            )
        return Deadlines(
            citation=str(pick(raw.get("citation")) or t("service.deadlines_citation")),
            legal_basis=tuple(raw.get("legal_basis", ["AI-Act/art-113"])),
            stages=tuple(sorted(stages, key=lambda stage: stage.date_value)),
            caveat=" ".join(rules.deadline_caveat.split()),
            rules_as_of=rules.as_of,
            version_note=" ".join(rules.version_note_text.split()),
        )

    return app


# Cheap at import time: data is loaded in the lifespan handler, not here.
app = build_app()


def run_server(address: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run the service with uvicorn, bound to localhost unless ``address`` says otherwise.

    Exposure to the network must be an explicit choice; the container passes 0.0.0.0 itself.
    """
    import uvicorn

    uvicorn.run(
        "compliance_helper.service.app:app" if reload else app,
        host=address,
        port=port,
        reload=reload,
        log_level="info",
        **proxy_settings(),
    )
