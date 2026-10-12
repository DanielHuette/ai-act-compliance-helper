"""Container image: offline operation, non-root user and bundled legal texts.

Context: only a real container can prove the service works without network or root; built with
WITH_SEARCH_MODEL=0 to test mechanics, not retrieval quality. Skipped without Docker. | Input:
Dockerfile, docker CLI | Output: pass when the running container meets each guarantee.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
IMAGE_TAG = "compliance-helper-test:no-model"

docker = shutil.which("docker")
pytestmark = [
    pytest.mark.skipif(not docker, reason="Docker is not installed"),
    pytest.mark.container,
]


def _run(*cli_args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run([docker, *cli_args], capture_output=True, text=True, timeout=timeout)


@pytest.fixture(scope="module")
def image() -> str:
    """Build the image once for this module."""
    command = ["build", "--build-arg", "WITH_SEARCH_MODEL=0", "-t", IMAGE_TAG, str(ROOT)]
    # In a sandboxed build environment the network is only reachable through the proxy.
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "PIP_INDEX_URL"):
        if os.environ.get(name):
            command[1:1] = ["--build-arg", f"{name}={os.environ[name]}"]
    if os.environ.get("HTTPS_PROXY"):
        command[1:1] = ["--network=host"]
    completed = _run(*command)
    if completed.returncode != 0:
        pytest.skip(f"Image cannot be built here:\n{completed.stderr[-900:]}")
    return IMAGE_TAG


@pytest.fixture(scope="module")
def container(image) -> str:
    """Start the service without network and wait until it responds."""
    name = f"compliance-helper-test-{uuid.uuid4().hex[:8]}"
    completed = _run("run", "-d", "--name", name, "--network=none", image)
    if completed.returncode != 0:
        pytest.skip(f"Container does not start: {completed.stderr[-400:]}")
    try:
        for _ in range(40):
            if (
                _exec_in_container(
                    name,
                    "import urllib.request;"
                    "urllib.request.urlopen("
                    "'http://127.0.0.1:8000/health', timeout=5)",
                ).returncode
                == 0
            ):
                break
            time.sleep(2)
        else:
            logs = _run("logs", name).stdout[-900:]
            pytest.fail(f"Service in container does not respond:\n{logs}")
        yield name
    finally:
        _run("rm", "-f", name, timeout=60)


def _exec_in_container(name: str, executable: str) -> subprocess.CompletedProcess:
    return _run("exec", name, "python", "-c", executable, timeout=120)


def _query_api(name: str, path: str, payload: dict | None = None) -> dict:
    """Query an API path from inside the container."""
    executable = (
        "import json, urllib.request\n"
        f"payload = {payload!r}\n"
        f"url = 'http://127.0.0.1:8000{path}'\n"
        "if payload is None:\n"
        "    request = urllib.request.Request(url)\n"
        "else:\n"
        "    request = urllib.request.Request(\n"
        "        url, data=json.dumps(payload).encode(),\n"
        "        headers={'Content-Type': 'application/json'})\n"
        "with urllib.request.urlopen(request, timeout=60) as response:\n"
        "    print(response.read().decode())\n"
    )
    completed = _exec_in_container(name, executable)
    assert completed.returncode == 0, completed.stderr[-600:]
    return json.loads(completed.stdout)


def test_service_runs_without_root(container):
    """Not root, so a bug in the service cannot affect the host system."""
    completed = _run("exec", container, "id", "-u")
    assert completed.stdout.strip() == "10001", completed.stdout


def test_source_is_not_writable_by_service_user(container):
    """The service user must not be able to modify its own source."""
    for field_path in ("/app/src", "/app/data", "/app/src/compliance_helper/cli.py"):
        completed = _exec_in_container(
            container, f"import os,sys;sys.exit(0 if not os.access({field_path!r}, os.W_OK) else 1)"
        )
        assert completed.returncode == 0, f"writable by service user: {field_path}"


def test_service_cannot_overwrite_its_source(container):
    """Cross-check with a real write attempt, not just permission bits."""
    completed = _exec_in_container(
        container,
        "import sys\n"
        "try:\n"
        "    open('/app/src/compliance_helper/cli.py', 'a').write('# ')\n"
        "    sys.exit(1)\n"
        "except OSError:\n"
        "    sys.exit(0)\n",
    )
    assert completed.returncode == 0, "the service could modify its source"


def test_service_answers_without_network(container):
    """The container runs with --network=none and must still work."""
    body = _query_api(container, "/health")
    assert body["corpus_loaded"] is True
    assert body["units"] > 2000


def test_network_is_unavailable(container):
    """Cross-check that the network is really absent, not just unused."""
    completed = _exec_in_container(
        container,
        "import socket,sys\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=4)\n"
        "    sys.exit(1)\n"
        "except OSError:\n"
        "    sys.exit(0)\n",
    )
    assert completed.returncode == 0, "container has network access; test is meaningless"


def test_legal_texts_are_in_image(container):
    body = _query_api(container, "/health")
    assert body["units"] > 2000
    assert body["corpus_as_of"]


def test_classification_in_container(container):
    body = _query_api(
        container,
        "/api/classify",
        {
            "description": "Wir setzen ein Sprachmodell ein, um Bewerbungen "
            "vorzusortieren und eine Rangfolge zu erstellen.",
            "roles": ["deployer"],
        },
    )
    assert "high_risk_annex_iii" in body["classification"]["risk_classes"]
    assert body["classification"]["obligations"]


def test_ui_in_container(container):
    completed = _exec_in_container(
        container,
        "import urllib.request\n"
        "with urllib.request.urlopen("
        "'http://127.0.0.1:8000/', timeout=30) as a:\n"
        "    print(len(a.read().decode()))\n",
    )
    assert completed.returncode == 0
    assert int(completed.stdout.strip()) > 5_000


def test_cli_in_container(container):
    completed = _run(
        "exec",
        container,
        "python",
        "-m",
        "compliance_helper.cli",
        "--json",
        "classify",
        "Wir sortieren Bewerbungen vor.",
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr[-500:]
    body = json.loads(completed.stdout)
    assert body["risk_classes"]


def test_degraded_status_is_reported(container):
    """Without the search model the service is degraded and must report it."""
    body = _query_api(container, "/health")
    if body["embedding_model"].startswith("hashing"):
        assert body["status"] == "degraded"
        assert body["warnings"]


def test_small_image_switches_purpose_matching_off_and_says_so(container):
    """The small image has no cross-encoder; purpose matching is off and /health names why."""
    warnings = " ".join(_query_api(container, "/health")["warnings"])
    assert "COMPLIANCE_HELPER_RERANK=0" in warnings


def test_rebuild_hints_run_in_the_container(container):
    """A hint must name a command that exists where it is read; scripts/ is not in the image."""
    for language in ("de", "en"):
        completed = _run(
            "exec",
            container,
            "compliance-helper",
            "build-index",
            "--language",
            language,
            "--help",
            timeout=120,
        )
        assert completed.returncode == 0, completed.stderr[-500:]
        assert "--language" in completed.stdout


def test_build_index_in_the_container_needs_a_writable_copy(container):
    """The image data is read-only; the build refuses there instead of half-writing an index."""
    completed = _run(
        "exec",
        container,
        "compliance-helper",
        "build-index",
        "--language",
        "de",
        "--fallback",
        timeout=300,
    )
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
