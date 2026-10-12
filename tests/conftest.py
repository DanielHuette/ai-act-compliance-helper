"""Shared pytest fixtures for the test suite.

Context: loads corpus, assessor and use cases once per session and keeps the slow purpose route
out of the fast run. | Input: processed corpus, data/cases/*.yaml | Output: session fixtures and
an autouse purpose-route stub.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def corpus():
    """Processed corpus, loaded once per session."""
    from compliance_helper.corpus.build import load

    units = load()
    if not units:
        pytest.skip("No processed corpus (run compliance-helper build-corpus --language de)")
    return units


@pytest.fixture(scope="session")
def ids(corpus) -> set[str]:
    return {e.id for e in corpus}


@pytest.fixture(scope="session")
def assessor():
    from compliance_helper.classification.assessor import Assessor

    return Assessor()


@pytest.fixture(scope="session")
def cases() -> list[dict]:
    """All use cases from data/cases, each tagged with its source file."""
    import yaml

    collected: list[dict] = []
    for file in sorted((ROOT / "data" / "cases").glob("*.yaml")):
        document = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        for case in document.get("cases", []):
            case = dict(case)
            case["_file"] = file.name
            collected.append(case)
    if not collected:
        pytest.skip("No use cases found")
    return collected


@pytest.fixture(autouse=True)
def _purpose_route_only_in_slow_run(request):
    """Disable the cross-encoder purpose route unless the test is marked ``slow``.

    The decision-tree tests do not depend on it and it would make the fast run ten
    times slower; its accuracy is measured in ``test_accuracy_on_company_questions``.
    """
    if request.node.get_closest_marker("slow"):
        yield
        return
    from compliance_helper.classification import assessor as assessor_module
    from compliance_helper.classification import purposes

    # Patch the name in the assessor module: it was bound there at import time.
    empty = purposes.PurposeMatcher(lines=[])
    empty._reranker_attempted = True
    original = assessor_module.shared_purpose_matcher
    assessor_module.shared_purpose_matcher = lambda: empty  # type: ignore[assignment]
    # A session-scoped Assessor may already hold a real matcher from an earlier test.
    for fixture_value in (request.node.funcargs or {}).values():
        if isinstance(fixture_value, assessor_module.Assessor):
            fixture_value._purpose_matcher = empty
            fixture_value._purpose_matcher_attempted = True
    try:
        yield
    finally:
        assessor_module.shared_purpose_matcher = original
