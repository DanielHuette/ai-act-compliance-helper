"""Language selection and English output of the HTTP service and web UI.

Context: every request picks its language from ``?lang=``, the ``lang`` cookie or
``Accept-Language`` and must answer entirely in it, including code run in the threadpool. |
Input: FastAPI app with the fallback embedder, called in-process by TestClient | Output: pass
when language resolution, response headers and all service and UI texts are correct in English.
"""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

import pytest

from compliance_helper.i18n import Language, catalog, current_language

fastapi_testclient = pytest.importorskip("fastapi.testclient")

APP_JS = (
    Path(__file__).resolve().parent.parent / "src/compliance_helper/webui/static/app.js"
).read_text(encoding="utf-8")


def _german_only_texts(*areas: str, min_length: int = 15) -> list[str]:
    """German catalog texts of ``areas`` that differ in English and are long enough to be unique.

    Texts with placeholders are skipped; short words such as "Ja" would match inside other text.
    """
    german, english = catalog(Language.DE), catalog(Language.EN)
    return [
        text
        for key, text in german.items()
        if key.split(".", 1)[0] in areas
        and text != english[key]
        and "{" not in text
        and len(text) >= min_length
    ]


@pytest.fixture(scope="module")
def app():
    os.environ["COMPLIANCE_HELPER_EMBEDDING"] = "fallback"
    os.environ["COMPLIANCE_HELPER_REQUESTS_PER_MINUTE"] = "1000"
    from compliance_helper.service.app import build_app

    return build_app()


@pytest.fixture(scope="module")
def client(app):
    with fastapi_testclient.TestClient(app) as client:
        yield client


@pytest.fixture()
def fresh(client):
    """The shared client without the language cookie an earlier test may have left behind."""
    client.cookies.clear()
    yield client
    client.cookies.clear()


def test_query_parameter_selects_english_and_sets_cookie(fresh):
    answer = fresh.get("/api/questionnaire", params={"lang": "en"})
    assert answer.headers["content-language"] == "en"
    vary = {part.strip().lower() for part in answer.headers["vary"].split(",")}
    assert {"accept-language", "cookie"} <= vary
    cookie = answer.headers["set-cookie"]
    assert cookie.startswith("lang=en;")
    assert "Max-Age=31536000" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/" in cookie


def test_cookie_selects_the_language_without_query(fresh):
    fresh.cookies.set("lang", "en")
    answer = fresh.get("/api/questionnaire")
    assert answer.headers["content-language"] == "en"
    assert "set-cookie" not in answer.headers


def test_accept_language_selects_the_language_without_cookie(fresh):
    answer = fresh.get("/api/questionnaire", headers={"Accept-Language": "fr-FR, en;q=0.8"})
    assert answer.headers["content-language"] == "en"


def test_query_wins_over_cookie_and_browser(fresh):
    fresh.cookies.set("lang", "en")
    answer = fresh.get(
        "/api/questionnaire", params={"lang": "de"}, headers={"Accept-Language": "en"}
    )
    assert answer.headers["content-language"] == "de"
    assert answer.headers["set-cookie"].startswith("lang=de;")


def test_unsupported_query_value_is_ignored(fresh):
    answer = fresh.get(
        "/api/questionnaire", params={"lang": "fr"}, headers={"Accept-Language": "en"}
    )
    assert answer.headers["content-language"] == "en"
    assert "set-cookie" not in answer.headers


def test_german_is_the_default(fresh):
    answer = fresh.get("/api/questionnaire", headers={"Accept-Language": "fr, es"})
    assert answer.headers["content-language"] == "de"
    assert answer.json()["items"][0]["question"] == "Welche Rolle haben Sie bei diesem System?"


def test_vary_keeps_the_cors_origin(fresh):
    answer = fresh.get(
        "/api/questionnaire", params={"lang": "en"}, headers={"Origin": "http://localhost:8000"}
    )
    vary = {part.strip().lower() for part in answer.headers["vary"].split(",")}
    assert {"origin", "accept-language", "cookie"} <= vary


def test_static_files_get_no_content_language(fresh):
    answer = fresh.get("/static/app.js", params={"lang": "en"})
    assert answer.status_code == 200
    assert "content-language" not in answer.headers


def test_language_reaches_threadpool_code():
    """Sync endpoints and run_in_threadpool run in worker threads; the language must follow."""
    from starlette.concurrency import run_in_threadpool

    from compliance_helper.service.app import build_app

    app = build_app()

    @app.get("/test-language/sync")
    def language_in_sync_endpoint() -> dict[str, str]:
        return {"language": current_language().value}

    @app.get("/test-language/threadpool")
    async def language_in_threadpool() -> dict[str, str]:
        language = await run_in_threadpool(current_language)
        return {"language": language.value}

    isolated = fastapi_testclient.TestClient(app)
    for path in ("/test-language/sync", "/test-language/threadpool"):
        assert isolated.get(path, params={"lang": "en"}).json() == {"language": "en"}
        assert isolated.get(path, params={"lang": "de"}).json() == {"language": "de"}


def test_errors_are_english(fresh):
    not_found = fresh.get("/does-not-exist", params={"lang": "en"}).json()
    assert not_found == {
        "error": "This path does not exist.",
        "hint": "The available paths are listed at /openapi.json.",
    }
    wrong_method = fresh.get("/api/classify", params={"lang": "en"}).json()
    assert wrong_method["error"] == "This path does not accept this method."
    invalid = fresh.post("/api/classify", params={"lang": "en"}, json={"unknown_field": 1}).json()
    assert invalid["error"] == "The service does not know the field 'unknown_field'."
    assert invalid["hint"] == "The expected form is described at /openapi.json."


def test_rate_limit_hint_is_english():
    from compliance_helper.security import rate_limiter_from_env
    from compliance_helper.service.app import build_app

    app = build_app()
    os.environ["COMPLIANCE_HELPER_REQUESTS_PER_MINUTE"] = "1"
    try:
        app.state.rate_limiter = rate_limiter_from_env()
    finally:
        os.environ["COMPLIANCE_HELPER_REQUESTS_PER_MINUTE"] = "1000"
    limited = fastapi_testclient.TestClient(app)
    answers = [limited.get("/api/questionnaire", params={"lang": "en"}) for _ in range(3)]
    rejected = next(answer for answer in answers if answer.status_code == 429)
    assert rejected.headers["content-language"] == "en"
    assert rejected.json()["hint"].startswith("The limit protects the service from overload.")


def test_questionnaire_is_english_and_matches_german_ids(fresh):
    english = fresh.get("/api/questionnaire", params={"lang": "en"}).json()
    german = fresh.get("/api/questionnaire", params={"lang": "de"}).json()
    assert [item["id"] for item in english["items"]] == [item["id"] for item in german["items"]]
    assert english["items"][0]["question"] == "What is your role regarding this system?"
    assert english["hint"].startswith("No question has to be answered.")
    body = json.dumps(english, ensure_ascii=False)
    for text in _german_only_texts("service"):
        assert text not in body


def test_health_warnings_are_english(fresh):
    warnings = fresh.get("/health", params={"lang": "en"}).json()["warnings"]
    joined = " ".join(warnings)
    assert "Ersatzmodell" not in joined
    assert not re.search(r"[äöüß]", joined)


def test_classification_explanations_are_english(fresh):
    body = fresh.post(
        "/api/classify",
        params={"lang": "en"},
        json={
            "description": "Wir sortieren Bewerbungen mit einem Sprachmodell vor "
            "und erstellen eine Rangfolge der Kandidaten.",
            "roles": ["deployer"],
        },
    ).json()
    assert body["most_severe_class"] == "high_risk_annex_iii"
    explanations = [body["most_severe_explanation"]]
    explanations += [entry["explanation"] for entry in body["risk_class_explanations"]]
    explanations += [entry["explanation"] for entry in body["role_explanations"]]
    for explanation in explanations:
        assert explanation.strip()
        assert not re.search(r"[äöüß]|\b(der|die|das|und|nicht)\b", explanation)


def test_search_page_is_english(fresh):
    page = fresh.get("/search", params={"lang": "en"}).text
    assert '<html lang="en">' in page
    assert 'href="?lang=de"' in page
    assert 'href="?lang=en"' in page
    assert 'aria-current="true">EN</a>' in page
    assert "Describe your AI system" in page
    assert "What is your role regarding this system?" in page
    visible = html.unescape(page)
    for text in _german_only_texts("webui", "service"):
        assert text not in visible, text


def test_search_page_embeds_english_browser_texts(fresh):
    page = fresh.get("/search", params={"lang": "en"}).text
    block = re.search(r'<script type="application/json" id="ui-text">(.*?)</script>', page, re.S)
    assert block
    data = json.loads(block.group(1))
    assert data["lang"] == "en"
    assert data["roles"]["deployer"] == "Deployer"
    assert data["text"]["checking"] == "Checking …"
    for text in data["text"].values():
        assert not re.search(r"[äöüß]", text)


def test_german_page_keeps_german_text(fresh):
    page = fresh.get("/search", params={"lang": "de"}).text
    assert '<html lang="de">' in page
    assert "Beschreiben Sie Ihr KI-System" in page
    assert "<strong>keine Rechtsberatung</strong>, ersetzt keine anwaltliche Prüfung" in page


def test_app_js_has_no_german_literals():
    literals = set(re.findall(r'"([^"\\]*)"', APP_JS))
    assert not [literal for literal in literals if re.search(r"[äöüÄÖÜß]", literal)]
    assert not literals & set(_german_only_texts("webui", min_length=1))
    for text in _german_only_texts("webui"):
        assert text not in APP_JS


def test_app_js_keys_exist_in_both_catalogs():
    keys = set(re.findall(r'say\("(\w+)"', APP_JS))
    keys |= {"deadline_in_force", "deadline_upcoming", "applies_from", "applies_since"}
    keys |= {
        f"{prefix}_{risk_class}"
        for prefix in ("badge", "title")
        for risk_class in (
            "prohibited",
            "high_risk_annex_i",
            "high_risk_annex_iii",
            "high_risk_exemption",
            "gpai_systemic_risk",
            "gpai",
            "transparency",
            "minimal",
            "unclear",
        )
    }
    keys |= {f"confidence_{level}" for level in ("certain", "likely", "needs_review")}
    for language in Language:
        missing = {key for key in keys if f"webui.js.{key}" not in catalog(language)}
        assert not missing, (language, missing)


def test_api_calls_forward_the_language():
    assert "withLanguage(url)" in APP_JS
    assert 'withLanguage("/api/deadlines")' in APP_JS


def test_english_search_uses_the_english_index(fresh):
    answer = fresh.post(
        "/api/search", params={"lang": "en"}, json={"question": "Article 6(3) AI Act", "count": 4}
    )
    assert answer.status_code == 200, answer.text
    evidence = answer.json()["evidence"]
    assert evidence[0]["id"] == "AI-Act/art-6/para-3"
    assert evidence[0]["citation"] == "Article 6(3) AI Act"
    assert "high-risk" in evidence[0]["excerpt"]
    assert len(evidence) <= 4


def test_german_and_english_search_cite_the_same_unit(fresh):
    questions = {"de": "Artikel 6 Absatz 3 KI-VO", "en": "Article 6(3) AI Act"}
    top_ids = {
        language: fresh.post(
            "/api/search", params={"lang": language}, json={"question": question, "count": 3}
        ).json()["evidence"][0]["id"]
        for language, question in questions.items()
    }
    assert top_ids["de"] == top_ids["en"] == "AI-Act/art-6/para-3"


def test_english_answer_surfaces_the_english_learning_note(fresh):
    answer = fresh.post(
        "/api/ask",
        params={"lang": "en"},
        json={
            "question": "May we pre-sort job applications with a language model?",
            "model": "none",
        },
    )
    assert answer.status_code == 200, answer.text
    learning_note = answer.json()["answer"]["learning_note"]
    assert learning_note
    assert not re.search(r"[äöüß]|\b(der|die|das|und|nicht)\b", learning_note)
