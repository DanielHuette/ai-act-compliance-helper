"""Safeguards of the HTTP service: limits, headers, model choice, readiness and consistent results.

Context: the service is reachable by anyone on its network, so oversized or malformed bodies,
forged proxy headers, client model choices and missing data must each end in a clear, localized
answer, slow work must not stall other requests, and the search page must show one
classification only. | Input: FastAPI app with the fallback embedder, called in-process by
TestClient | Output: pass when every safeguard holds.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import logging
import re
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from compliance_helper.classification.assessor import RuleFileError
from compliance_helper.corpus.build import build_command as corpus_build_command
from compliance_helper.i18n import Language, t, use_language
from compliance_helper.search.store import build_command as index_build_command
from compliance_helper.security import RateLimiter, install_log_redaction

app_module = importlib.import_module("compliance_helper.service.app")

fastapi_testclient = pytest.importorskip("fastapi.testclient")

ROOT = Path(__file__).resolve().parent.parent
SECRET = "sk-ant-REALSECRET1234567890abcdef"
RAW_IDS = re.compile(
    r"\[(certain|likely|needs_review)\]|\b(high_risk_annex_iii|gpai_systemic_risk)\b"
    r"|\b(Rolle|Role): (deployer|provider)\b|\((RuntimeError|TimeoutError)\)"
)

GPAI_REQUEST = {
    "description": "Wir bieten anderen Unternehmen ein allgemeines KI-Modell an.",
    "roles": ["provider"],
    "traits": {"is_gpai_model": "true", "training_compute_flop": "3e25"},
}


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as environment:
        environment.setenv("COMPLIANCE_HELPER_EMBEDDING", "fallback")
        environment.setenv("COMPLIANCE_HELPER_REQUESTS_PER_MINUTE", "1000")
        environment.setenv("COMPLIANCE_HELPER_MODEL", "none")
        with fastapi_testclient.TestClient(app_module.build_app()) as client:
            yield client


@pytest.fixture()
def fresh(client):
    client.cookies.clear()
    yield client
    client.cookies.clear()


def _app_without_corpus(monkeypatch, rules_fail: bool = False):
    def missing_corpus(language: Language) -> list:
        raise FileNotFoundError(f"no corpus for {language.value}")

    def broken_rules() -> None:
        raise RuleFileError("Rule file missing: ai_act_risk_classes.yaml")

    monkeypatch.setattr(app_module, "load", missing_corpus)
    if rules_fail:
        monkeypatch.setattr(app_module, "rule_set", broken_rules)
    return fastapi_testclient.TestClient(app_module.build_app())


def test_answer_uses_the_classification_of_the_card(fresh):
    card = fresh.post("/api/classify", json=GPAI_REQUEST).json()
    asked = fresh.post(
        "/api/ask",
        json={"question": "Welche Pflichten haben wir?", "model": "none", **GPAI_REQUEST},
    )
    assert asked.status_code == 200, asked.text
    answer = asked.json()
    assert card["most_severe_class"] == "gpai_systemic_risk"
    assert answer["most_severe_class"] == card["most_severe_class"]
    answered = answer["answer"]["classification"]
    assert answered["risk_classes"] == card["classification"]["risk_classes"]
    assert answered["roles"] == card["classification"]["roles"]
    assert [o["id"] for o in answered["obligations"]] == [
        o["id"] for o in card["classification"]["obligations"]
    ]


def test_search_page_sends_the_same_facts_to_both_endpoints():
    script = (ROOT / "src/compliance_helper/webui/static/app.js").read_text(encoding="utf-8")
    classify_call = (
        'post("/api/classify",\n      Object.assign({ description: description || question }'
    )
    assert f"{classify_call}, facts))" in script
    assert re.search(r'post\("/api/ask",\s+Object\.assign\(\{[^}]*\},\s+facts\)\)', script)


def test_client_cannot_enable_a_disabled_model(fresh, monkeypatch):
    calls: list[str] = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(
        "compliance_helper.answer.compose.Anthropic.answers",
        lambda self, system, prompt: calls.append(prompt) or "reply",
    )
    for choice in ("anthropic", "auto"):
        body = fresh.post(
            "/api/ask",
            json={"question": "Was gilt?", "description": "Ein Chatbot.", "model": choice},
        ).json()
        assert body["answer"]["without_model"] is True
    assert calls == []
    rejected = fresh.post("/api/ask", json={"question": "Was gilt?", "model": "x"})
    assert rejected.status_code == 422
    assert rejected.json()["error"] == t("service.validation_enum", field="model")


def test_client_cannot_switch_to_another_vendor(fresh, monkeypatch):
    class OperatorModel:
        name = "anthropic/claude-test"

        def __init__(self) -> None:
            self.prompts: list[str] = []

        def answers(self, system_prompt: str, prompt: str) -> str:
            self.prompts.append(prompt)
            return "Formulierte Antwort."

    operator = OperatorModel()
    monkeypatch.setattr(fresh.app.state.service_state, "llm", operator)
    asked = {"question": "Was gilt?", "description": "Ein Chatbot."}
    chosen = fresh.post("/api/ask", json={**asked, "model": "openai"}).json()["answer"]
    assert chosen["without_model"] is True
    assert chosen["warnings"][-1] == t("service.model_not_enabled", model="openai")
    assert operator.prompts == []
    same = fresh.post("/api/ask", json={**asked, "model": "anthropic"}).json()["answer"]
    assert same["model"] == "anthropic/claude-test"
    assert len(operator.prompts) == 1


def test_slow_classification_does_not_block_other_requests(fresh, monkeypatch):
    assessor = fresh.app.state.service_state.assessor
    original = assessor.check

    def slow_check(description):
        time.sleep(1.5)
        return original(description)

    monkeypatch.setattr(assessor, "check", slow_check)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            fresh.post, "/api/classify", json={"description": "Wir ranken Bewerber."}
        )
        time.sleep(0.3)
        started = time.perf_counter()
        assert fresh.get("/health").status_code == 200
        waited = time.perf_counter() - started
        assert pending.result().status_code == 200
    assert waited < 1.0, f"/health waited {waited:.2f} s behind a classification"


def test_secrets_are_redacted_in_every_logger(caplog):
    install_log_redaction()
    factory = logging.getLogRecordFactory()
    install_log_redaction()
    assert logging.getLogRecordFactory() is factory
    with caplog.at_level(logging.INFO):
        logging.getLogger("compliance_helper.answer.compose").warning(
            "Model did not respond: %s", f"api_key={SECRET}"
        )
        logging.getLogger("uvicorn.error").error("token=%s", "abcdefghijklmn")
        logging.getLogger("compliance_helper.service").warning(
            "%s", RuntimeError(f"Bearer {SECRET}")
        )
        try:
            raise RuntimeError(f"Authorization: Bearer {SECRET}")
        except RuntimeError:
            logging.getLogger("compliance_helper.search.index").exception("failed")
    assert "REALSECRET" not in caplog.text
    assert "abcdefghijklmn" not in caplog.text
    assert caplog.text.count("⟨secret removed⟩") >= 4


def test_access_log_keeps_its_shape_while_redacted():
    from uvicorn.logging import AccessFormatter

    install_log_redaction()
    record = logging.getLogger("uvicorn.access").makeRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", f"/api/deadlines?api_key={SECRET}", "1.1", 200),
        None,
    )
    line = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s').format(record)
    assert "REALSECRET" not in line
    assert line.endswith("200 OK")


@pytest.mark.parametrize(
    ("traits", "rejected"),
    [
        ({"employee_count": "1e999"}, "employee_count"),
        ({"employee_count": "-5"}, "employee_count"),
        ({"employee_count": "nan"}, "employee_count"),
        ({"training_compute_flop": "inf", "is_gpai_model": "true"}, "training_compute_flop"),
        ({"training_compute_flop": "-1e26", "is_gpai_model": "true"}, "training_compute_flop"),
    ],
)
def test_impossible_numbers_are_reported_not_used(fresh, traits, rejected):
    answer = fresh.post(
        "/api/classify",
        json={"description": "Wir bieten ein allgemeines KI-Modell an.", "traits": traits},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert rejected in body["unrecognized_traits"]
    assert body["most_severe_class"] != "gpai_systemic_risk"


def test_overflowing_json_number_is_reported(fresh):
    answer = fresh.post(
        "/api/classify",
        content=b'{"description": "Ein Chatbot.", "traits": {"employee_count": 1e999}}',
        headers={"Content-Type": "application/json"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["unrecognized_traits"] == ["employee_count"]


def test_oversized_body_is_refused_with_413(fresh):
    body = b'{"description": "' + b"A" * 200_000 + b'"}'
    for content in (body, iter([body[:100_000], body[100_000:]])):
        answer = fresh.post(
            "/api/classify", content=content, headers={"Content-Type": "application/json"}
        )
        assert answer.status_code == 413
        assert answer.json() == {
            "error": "Die Anfrage ist zu groß.",
            "hint": "Pro Anfrage werden höchstens 128 KB angenommen.",
        }


def test_too_many_or_too_long_traits_are_refused(fresh):
    many = fresh.post(
        "/api/classify",
        params={"lang": "en"},
        json={"description": "A chatbot.", "traits": {f"trait_{n}": True for n in range(65)}},
    )
    assert many.status_code == 422
    assert many.json()["error"] == "The field 'traits' is too long."
    long_value = fresh.post(
        "/api/classify",
        params={"lang": "en"},
        json={"description": "A chatbot.", "traits": {"purpose": "x" * 501}},
    )
    assert long_value.status_code == 422
    assert long_value.json()["error"] == "The field 'traits.purpose' is too long."


def test_malformed_bodies_get_400_with_a_clear_sentence(fresh):
    invalid = fresh.post(
        "/api/classify",
        params={"lang": "en"},
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"] == "The request body is not valid JSON."
    for content, content_type in (
        (b"We rank applicants.", "text/plain"),
        (b"[1, 2]", "application/json"),
    ):
        shaped = fresh.post(
            "/api/classify",
            params={"lang": "en"},
            content=content,
            headers={"Content-Type": content_type},
        )
        assert shaped.status_code == 400
        assert shaped.json()["error"] == (
            "The request body must be a JSON object, sent with the header "
            "Content-Type: application/json."
        )


def test_empty_description_is_refused_like_in_the_cli(fresh):
    for description in ("", "   ​ "):
        answer = fresh.post(
            "/api/classify", params={"lang": "en"}, json={"description": description}
        )
        assert answer.status_code == 400
        assert answer.json()["error"] == (
            "Please describe the AI system: what it does, who uses it and who is affected by "
            "its results."
        )
    with_facts = fresh.post("/api/classify", json={"description": "", "roles": ["deployer"]})
    assert with_facts.status_code == 200


@pytest.mark.parametrize(
    "path", ["/search", "/classification/", "/static/app.js", "/api/deadlines", "/missing"]
)
def test_every_response_carries_security_headers(fresh, path):
    headers = fresh.get(path).headers
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    policy = headers["content-security-policy"]
    assert "frame-ancestors 'none'" in policy
    assert "script-src 'self';" in policy
    if path == "/classification/":
        assert "style-src 'self' 'unsafe-inline'" in policy
    else:
        assert "unsafe-inline" not in policy


def test_root_keeps_the_language_choice(fresh):
    assert fresh.get("/", follow_redirects=False).headers["location"] == "/classification/"
    chosen = fresh.get("/", params={"lang": "en"}, follow_redirects=False)
    assert chosen.status_code == 307
    assert chosen.headers["location"] == "/classification/?lang=en"
    fresh.cookies.set("lang", "en")
    assert fresh.get("/", follow_redirects=False).headers["location"] == "/classification/?lang=en"


def test_operator_language_is_the_default_after_the_browser(fresh, monkeypatch):
    monkeypatch.setenv("COMPLIANCE_HELPER_LANG", "en")
    unsupported = fresh.get("/api/questionnaire", headers={"Accept-Language": "fr"})
    assert unsupported.headers["content-language"] == "en"
    german = fresh.get("/api/questionnaire", headers={"Accept-Language": "de"})
    assert german.headers["content-language"] == "de"


def test_packaged_app_opens_the_question_flow_in_the_system_language():
    spec = importlib.util.spec_from_file_location("launch_app", ROOT / "packaging/launch_app.py")
    assert spec and spec.loader
    launch_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch_app)
    assert (
        launch_app.start_page("http://127.0.0.1:8713/", "en")
        == "http://127.0.0.1:8713/classification/?lang=en"
    )


def test_favicon_is_served_at_the_root(fresh):
    answer = fresh.get("/favicon.svg")
    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("image/svg+xml")


def test_question_flow_page_links_its_favicon_relative_to_itself(fresh):
    """The page lives under /classification/ and in any folder of a static host."""
    page = fresh.get("/classification/").text
    assert '<link rel="icon" href="./favicon.svg"' in page
    assert fresh.get("/classification/favicon.svg").status_code == 200


def test_classification_works_without_corpus_and_search_reports_503(monkeypatch):
    with _app_without_corpus(monkeypatch) as without_corpus:
        classified = without_corpus.post(
            "/api/classify", json={"description": "Wir ranken Bewerber für offene Stellen."}
        )
        assert classified.status_code == 200, classified.text
        for path, body in (
            ("/api/search", {"question": "Artikel 6"}),
            ("/api/ask", {"question": "Was gilt?", "model": "none"}),
        ):
            refused = without_corpus.post(path, json=body)
            assert refused.status_code == 503
            assert refused.headers["retry-after"] == "30"
            assert refused.json()["error"] == t("service.search_index_not_loaded")
        health = without_corpus.get("/health", params={"lang": "en"}).json()
        assert health["status"] == "not_ready"
        assert any(corpus_build_command(Language.EN) in warning for warning in health["warnings"])


def test_missing_rules_make_classification_503(monkeypatch):
    with _app_without_corpus(monkeypatch, rules_fail=True) as without_rules:
        refused = without_rules.post("/api/classify", json={"description": "Ein Chatbot."})
        assert refused.status_code == 503
        assert refused.json()["error"] == t("service.assessor_not_loaded")
        assert without_rules.get("/api/deadlines").status_code == 503
        for language in Language:
            health = without_rules.get("/health", params={"lang": language.value}).json()
            assert health["status"] == "not_ready"
            assert t("service.warning_rules_missing", language) in health["warnings"]
            assert "RuleFileError" not in " ".join(health["warnings"])


class _RecordingMatcher:
    def __init__(self, available: bool, reason: str = "") -> None:
        self.available, self.unavailable_reason = available, reason
        self.shared: object = None

    def share_embedder(self, embedder: object) -> None:
        self.shared = embedder

    def load(self) -> bool:
        return self.available


def _state_with(matcher: _RecordingMatcher, embedder_name: str) -> object:
    state = app_module.ServiceState(started_at=time.time())
    state.assessor = types.SimpleNamespace(purpose_matcher=lambda: matcher)
    embedder = types.SimpleNamespace(name=embedder_name)
    state.indexes = {Language.DE: types.SimpleNamespace(embedder=embedder)}
    app_module._load_purpose_matching(state)
    return state


def test_purpose_matching_reuses_the_index_embedding_model():
    matcher = _RecordingMatcher(available=True)
    state = _state_with(matcher, "BAAI/bge-m3")
    assert getattr(matcher.shared, "name", None) == "BAAI/bge-m3"
    assert not state.notices


def test_purpose_matching_does_not_reuse_the_hashing_fallback():
    matcher = _RecordingMatcher(available=True)
    _state_with(matcher, "hashing-fallback")
    assert matcher.shared is None


@pytest.mark.parametrize("language", list(Language))
def test_switched_off_purpose_matching_is_reported_with_its_setting(language):
    matcher = _RecordingMatcher(available=False, reason="COMPLIANCE_HELPER_RERANK=0")
    state = _state_with(matcher, "BAAI/bge-m3")
    with use_language(language):
        assert state.warnings[-1] == t(
            "service.warning_purpose_matching_switched_off", setting="COMPLIANCE_HELPER_RERANK=0"
        )


def test_missing_cross_encoder_is_reported_in_plain_words():
    state = _state_with(_RecordingMatcher(available=False, reason="no cross-encoder"), "x")
    assert state.notices[-1].key == "service.warning_purpose_matching_no_model"
    assert "no cross-encoder" not in state.warnings[-1]


def test_service_state_is_loaded_off_the_event_loop(monkeypatch):
    loaded_on_loop: list[bool] = []

    def load_service_state() -> object:
        try:
            asyncio.get_running_loop()
            loaded_on_loop.append(True)
        except RuntimeError:
            loaded_on_loop.append(False)
        return app_module.ServiceState(started_at=time.time())

    monkeypatch.setattr(app_module, "load_service_state", load_service_state)
    with fastapi_testclient.TestClient(app_module.build_app()) as client:
        assert client.get("/health").status_code == 200
    assert loaded_on_loop == [False]


def test_corpus_date_follows_the_request_language(fresh):
    state = fresh.app.state.service_state
    for language in Language:
        expected = max(unit.as_of for unit in state.units_by_language[language] if unit.as_of)
        health = fresh.get("/health", params={"lang": language.value}).json()
        assert health["corpus_as_of"] == expected.isoformat()


def test_build_hints_name_the_language(fresh):
    warnings = " ".join(fresh.get("/health", params={"lang": "en"}).json()["warnings"])
    for language in Language:
        assert index_build_command(language) in warnings
    assert "python -m scripts.build_search_index" not in warnings


@pytest.mark.parametrize("language", ["de", "en"])
def test_answers_show_labels_not_internal_ids(fresh, language):
    body = fresh.post(
        "/api/ask",
        params={"lang": language},
        json={
            "question": "Welche Pflichten gelten?",
            "description": "Wir setzen als Betreiber ein KI-System ein, das Bewerbungen bewertet.",
            "roles": ["deployer"],
            "model": "none",
        },
    ).json()
    answer = body["answer"]
    assert not RAW_IDS.search(answer["text"]), answer["text"]
    assert not any("Error" in warning for warning in answer["warnings"])


def test_search_page_shows_visitors_one_plain_sentence(fresh):
    page = fresh.get("/search", params={"lang": "en"}).text
    box = re.search(r'<section class="notice warning"[^>]*>(.*?)</section>', page, re.S)
    assert box, "the fallback search must be announced"
    text = " ".join(re.sub(r"<[^>]+>", " ", box.group(1)).split())
    assert (
        text
        == f"{t('webui.degraded_title', Language.EN)} {t('webui.degraded_notice', Language.EN)}"
    )
    for internal in ("python", "hashing", "root", "Error", "COMPLIANCE_HELPER"):
        assert internal not in text


def test_search_page_keeps_input_across_a_language_switch():
    script = (ROOT / "src/compliance_helper/webui/static/app.js").read_text(encoding="utf-8")
    assert "sessionStorage.setItem(STATE_KEY" in script
    assert 'document.querySelectorAll(".language-switch a")' in script
    assert "if (storedState.ran) { runCheck(); }" in script


def test_forwarded_header_is_trusted_only_from_configured_proxies(monkeypatch):
    import uvicorn
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    monkeypatch.delenv("COMPLIANCE_HELPER_TRUSTED_PROXIES", raising=False)
    plain = uvicorn.Config(app_module.app, **app_module.proxy_settings())
    plain.load()
    assert not isinstance(plain.loaded_app, ProxyHeadersMiddleware)

    monkeypatch.setenv("COMPLIANCE_HELPER_TRUSTED_PROXIES", "10.0.0.5, 10.1.0.0/16")
    behind_proxy = uvicorn.Config(app_module.app, **app_module.proxy_settings())
    behind_proxy.load()
    assert isinstance(behind_proxy.loaded_app, ProxyHeadersMiddleware)
    assert app_module.proxy_settings()["forwarded_allow_ips"] == ["10.0.0.5", "10.1.0.0/16"]


def test_rate_limiter_never_tracks_more_addresses_than_its_cap():
    limiter = RateLimiter(limit=5, max_addresses=100)
    for number in range(1_000):
        assert limiter.check(f"2001:db8::{number:x}") == (True, 0)
    assert len(limiter._buckets) == 100
    for _ in range(5):
        limiter.check("2001:db8::3e7")
    assert limiter.check("2001:db8::3e7")[0] is False
