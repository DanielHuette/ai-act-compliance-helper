"""Safeguards for the web service and the CLI.

Context: The tool accepts free text from outside, so input size, hidden characters, request
floods and secrets in logs each need a dependency-free countermeasure. | Input: raw user text,
log records, the process environment | Output: sanitised text, rate-limit decisions, redacted
log lines and startup warnings.
"""

from __future__ import annotations

import logging
import os
import re
import time
import traceback
import unicodedata
from collections import OrderedDict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from compliance_helper.i18n import t

MAX_QUESTION_LENGTH = 2_000

# Must equal the ``max_length`` in the request schemas, or the schema rejects what this
# check let through.
MAX_DESCRIPTION_LENGTH = 20_000


class InputError(ValueError):
    """Rejected input whose message is safe to show to the user, unlike a programming error."""


class ServiceNotReadyError(RuntimeError):
    """A part the request needs is not loaded; the message is safe to show to the user."""


# Bidi overrides let a line render harmlessly in the browser while the log or LLM sees
# something else.
_BIDI_CONTROL_CHARS = frozenset(
    [chr(z) for z in range(0x202A, 0x202F)] + [chr(z) for z in range(0x2066, 0x206A)]
)

_ALLOWED_CONTROL_CHARS = frozenset("\n\t")


def sanitize_text(text: str) -> str:
    """Remove control, format and bidi characters and normalise to NFC.

    NFC matters for search: without it the same word exists in two code-point sequences
    depending on the keyboard, and keyword search matches only one of them.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    kept: list[str] = []
    for character in text:
        if character in _BIDI_CONTROL_CHARS:
            continue
        group = unicodedata.category(character)
        if group == "Cc" and character not in _ALLOWED_CONTROL_CHARS:
            continue
        if group == "Cf":
            continue
        kept.append(character)
    cleaned = "".join(kept)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def validate_question(question: str) -> str:
    """Sanitise a question and enforce its length limit.

    Raises:
        InputError: If the question is empty or too long.
    """
    cleaned = sanitize_text(question or "")
    if not cleaned:
        raise InputError(t("security.question_empty"))
    if len(cleaned) > MAX_QUESTION_LENGTH:
        raise InputError(
            t("security.question_too_long", length=len(cleaned), limit=MAX_QUESTION_LENGTH)
        )
    return cleaned


def require_description(description: str | None) -> str:
    """Sanitise a system description that must not be empty.

    Raises:
        InputError: If the description is empty or too long.
    """
    cleaned = validate_description(description)
    if not cleaned:
        raise InputError(t("security.description_empty"))
    return cleaned


def validate_description(description: str | None) -> str:
    """Sanitise a system description and enforce its length limit; empty is allowed.

    Raises:
        InputError: If the description is too long.
    """
    cleaned = sanitize_text(description or "")
    if len(cleaned) > MAX_DESCRIPTION_LENGTH:
        raise InputError(
            t("security.description_too_long", length=len(cleaned), limit=MAX_DESCRIPTION_LENGTH)
        )
    return cleaned


@dataclass
class RateLimiter:
    """In-memory sliding-window rate limiter keyed by client address.

    A sliding window avoids the double burst a per-minute counter allows at the minute
    boundary. Behind a load balancer each worker counts separately; limit there instead.
    ``max_addresses`` is a hard cap: beyond it the least recently seen address is dropped, so
    rotating addresses cannot grow memory or the time spent under the lock.
    """

    limit: int = 30
    window_seconds: float = 60.0
    max_addresses: int = 10_000
    _buckets: OrderedDict[str, deque[float]] = field(default_factory=OrderedDict)
    _lock: Lock = field(default_factory=Lock)

    def check(self, address: str) -> tuple[bool, int]:
        """Record a request from ``address``.

        Returns:
            ``(allowed, retry_after_seconds)``; ``retry_after_seconds`` is 0 when allowed.
        """
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(address, deque())
            self._buckets.move_to_end(address)
            while len(self._buckets) > max(1, self.max_addresses):
                self._buckets.popitem(last=False)
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = self.window_seconds - (now - bucket[0])
                return False, max(1, int(retry_after) + 1)
            bucket.append(now)
            return True, 0

    def message(self, retry_after: int) -> str:
        """User-facing rejection message."""
        return t("security.rate_limited", limit=self.limit, seconds=retry_after)

    def reset(self) -> None:
        """Clear all buckets (for tests)."""
        with self._lock:
            self._buckets.clear()


def rate_limiter_from_env() -> RateLimiter:
    """Build the limiter from ``COMPLIANCE_HELPER_REQUESTS_PER_MINUTE`` (default 30)."""
    try:
        limit = int(os.environ.get("COMPLIANCE_HELPER_REQUESTS_PER_MINUTE", "30"))
    except ValueError:
        limit = 30
    return RateLimiter(limit=max(1, limit))


# Named fields come first so the field name survives; the free-standing patterns would
# otherwise hit an already-redacted value and process the line twice.
_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(api[-_ ]?key|key|token|secret|geheimnis|passwor[dt]|"
        r"schl(?:ü|ue)ssel|credential|authorization)\b"
        r"\s*[:=]\s*[\"']?[^\s\"',;)⟨⟩]{6,}"
    ),
    re.compile(
        r"\b(?:sk|pk|rk|ghp|gho|ghs|ghu|github_pat|xoxb|xoxp|AIza)"
        r"[-_A-Za-z0-9]{10,}",
        re.IGNORECASE,
    ),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s/@]+:[^\s/@]+@", re.IGNORECASE),
)

_LONG_TOKEN = re.compile(r"[A-Za-z0-9+/=_\-]{48,}")

MAX_LOG_LINE_LENGTH = 2_000


def sanitize_for_log(text: object) -> str:
    """Make a value safe for a log line: redact secrets, strip control characters, cap length.

    Applied to every logged value, including third-party error messages, which often echo
    the whole request with its headers.
    """
    raw = text if isinstance(text, str) else str(text)
    raw = raw.replace("\r", " ").replace("\n", " ⏎ ")
    raw = redact_secrets(raw)
    raw = "".join(
        character
        for character in raw
        if unicodedata.category(character) not in ("Cc", "Cf") or character == " "
    )
    if len(raw) > MAX_LOG_LINE_LENGTH:
        raw = raw[:MAX_LOG_LINE_LENGTH] + " …⟨truncated⟩"
    return raw


def _redact_match(match: str) -> str:
    """Keep the field name, drop the value, so the line stays readable."""
    for separator in ("=", ":"):
        if separator in match:
            name, _, _value = match.partition(separator)
            if len(name) < 40:
                return f"{name}{separator} ⟨secret removed⟩"
    return "⟨secret removed⟩"


def redact_secrets(text: str) -> str:
    """Replace secrets in text such as a traceback, keeping its line breaks for readability."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda found: _redact_match(found.group(0)), text)
    return _LONG_TOKEN.sub(
        lambda found: f"⟨long token, {len(found.group(0)):d} chars, removed⟩", text
    )


#: Loggers whose formatter unpacks ``record.args`` by position, so the arguments must keep shape.
_STRUCTURED_ARGUMENT_LOGGERS = frozenset({"uvicorn.access"})


def _safe_log_argument(value: object) -> object:
    if value is None or isinstance(value, bool | int | float):
        return value
    return sanitize_for_log(value)


def redact_log_record(record: logging.LogRecord) -> None:
    """Redact message, arguments and exception text of ``record`` in place."""
    if record.msg is not None:
        record.msg = sanitize_for_log(record.msg)
    if isinstance(record.args, tuple):
        record.args = tuple(_safe_log_argument(value) for value in record.args)
    elif isinstance(record.args, Mapping):
        record.args = {name: _safe_log_argument(value) for name, value in record.args.items()}
    if record.args and record.name not in _STRUCTURED_ARGUMENT_LOGGERS:
        _redact_assembled_message(record)
    if record.exc_info and record.exc_info[0] is not None and not record.exc_text:
        record.exc_text = redact_secrets("".join(traceback.format_exception(*record.exc_info)))
        record.exc_text = record.exc_text.rstrip("\n")


def _redact_assembled_message(record: logging.LogRecord) -> None:
    """Catch a secret split between message and argument, such as ``"token=%s"`` and its value."""
    try:
        assembled = record.getMessage()
    except (TypeError, ValueError):
        return
    if redact_secrets(assembled) != assembled:
        record.msg, record.args = sanitize_for_log(assembled), ()


class _RedactingRecordFactory:
    """Log-record factory that redacts every record right after the wrapped factory builds it."""

    def __init__(self, wrapped: Any) -> None:
        self.wrapped = wrapped

    def __call__(self, *args: Any, **kwargs: Any) -> logging.LogRecord:
        record: logging.LogRecord = self.wrapped(*args, **kwargs)
        redact_log_record(record)
        return record


def install_log_redaction() -> None:
    """Redact secrets in every log record of the process, whichever logger or handler emits it.

    A record factory rather than a filter: a filter on the root logger skips records that
    propagate from child loggers (``compliance_helper.*``, ``uvicorn.error``), and filters on
    handlers miss handlers configured later, as uvicorn does at start. Calling it again is a no-op.
    """
    current = logging.getLogRecordFactory()
    if not isinstance(current, _RedactingRecordFactory):
        logging.setLogRecordFactory(_RedactingRecordFactory(current))


def check_environment() -> list[str]:
    """Return warnings in the active language about risky runtime conditions instead of aborting.

    Running as root or in debug mode stays possible on purpose, but must not go unnoticed.
    """
    warnings: list[str] = []

    geteuid = getattr(os, "geteuid", None)
    if geteuid is not None and geteuid() == 0:
        warnings.append(t("security.running_as_root"))

    for name in ("DEBUG", "COMPLIANCE_HELPER_DEBUG", "FASTAPI_DEBUG"):
        value = os.environ.get(name, "")
        if value and value.lower() not in ("0", "false", "no", "nein", "off", ""):
            warnings.append(t("security.debug_enabled", name=name, value=repr(value)))

    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("OPENAI_API_KEY"):
        warnings.append(t("security.two_llm_keys"))

    return warnings
