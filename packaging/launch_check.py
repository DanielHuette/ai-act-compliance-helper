"""Smoke-test the built package: start it and check that the question flow is served.

Context: a package that builds need not start; the first build lacked its data directories and
only failed at runtime ("rule file missing"). | Input: the PyInstaller output under dist/ |
Output: exit code 0 if /classification/ and question_flow.json (>= 100,000 bytes) answer on
one of the ports 8713-8724; messages in the language of COMPLIANCE_HELPER_LANG, else German.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compliance_helper.i18n import Language, t, use_language  # noqa: E402

FLOW_PAGE_MARKERS = (b"Einstufung", b"Classification")


def find_executable() -> Path:
    candidates = [
        ROOT / "dist" / "ComplianceHelper" / "ComplianceHelper",
        ROOT / "dist" / "ComplianceHelper" / "ComplianceHelper.exe",
        ROOT / "dist" / "ComplianceHelper.app" / "Contents" / "MacOS" / "ComplianceHelper",
    ]
    for k in candidates:
        if k.exists():
            return k
    raise SystemExit(
        t("cli.check_no_executable", candidates="\n  ".join(str(k) for k in candidates))
    )


def fetch(address: str, attempts: int = 90) -> tuple[int, bytes]:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(address, timeout=2) as response:  # nosec B310
                return response.status, response.read()
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)
    return 0, b""


def main() -> int:
    with use_language(Language.parse(os.environ.get("COMPLIANCE_HELPER_LANG"))):
        return check_package()


def check_package() -> int:
    executable = find_executable()
    print(t("cli.check_starting", executable=executable))
    # A file, not a pipe: nobody reads while polling, and a full pipe would block the app.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as output:
        process = subprocess.Popen(  # nosec B603
            [str(executable)],
            cwd=str(executable.parent),
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            return probe_ports(output)
        finally:
            stop(process)


def stop(process: subprocess.Popen[str]) -> None:
    """End the app, forcibly if it does not stop within ten seconds."""
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def output_tail(output: IO[str], characters: int = 2000) -> str:
    output.flush()
    output.seek(0)
    return output.read()[-characters:]


def probe_ports(output: IO[str]) -> int:
    """Find the app on one of the ports 8713-8724 and check that it serves the question flow."""
    for port_number in range(8713, 8725):
        status, content = fetch(f"http://127.0.0.1:{port_number}/classification/", attempts=12)
        if status != 200:
            continue
        if not any(marker in content for marker in FLOW_PAGE_MARKERS):
            print(t("cli.check_page_without_flow"))
            return 1
        status, payload = fetch(
            f"http://127.0.0.1:{port_number}/classification/question_flow.json", 8
        )
        if status != 200 or len(payload) < 100_000:
            print(t("cli.check_flow_data_missing", status=status, size=len(payload)))
            return 1
        print(t("cli.check_passed", port=port_number, kilobytes=len(payload) // 1024))
        return 0
    print(t("cli.check_no_answer"))
    print(output_tail(output))
    return 1


if __name__ == "__main__":
    sys.exit(main())
