"""Entry point of the packaged app: start the service on a free port and open the browser.

Context: users should only install and double-click; no command line, environment variables or
API key prompt. | Input: bundled data (PyInstaller _MEIPASS or source tree), optional
COMPLIANCE_HELPER_ROOT and COMPLIANCE_HELPER_LANG (else the system locale) | Output: local web
service on 127.0.0.1:8713-8799 whose pages default to that language, the question flow opened in
the browser in it, and a console message in German or English.
"""

from __future__ import annotations

import locale
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def root() -> Path:
    """Directory holding the shipped data, for both the frozen bundle and the source tree."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    return Path(bundle_dir) if bundle_dir else Path(__file__).resolve().parents[1]


def system_language() -> str:
    """Locale name of the operating system, such as ``de_DE`` or ``English_United States``."""
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(variable):
            return os.environ[variable]
    return locale.getlocale()[0] or ""


def free_port(lower: int = 8713, upper: int = 8799) -> int:
    """Return the first free local port in the range.

    A fixed port fails as soon as another program holds it, and the user would only see a
    browser window that never loads.
    """
    for number in range(lower, upper + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", number))
                return number
            except OSError:
                continue
    raise RuntimeError("No free port between %d and %d." % (lower, upper))


def start_page(address: str, language: str) -> str:
    """The question flow in ``language``; the static page reads ``?lang=``, not the OS setting."""
    return f"{address}classification/?lang={language}"


def open_browser(address: str) -> None:
    """Open the browser once the service responds."""
    import urllib.error
    import urllib.request

    for _ in range(100):
        try:
            with urllib.request.urlopen(address, timeout=1):  # nosec B310
                break
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    webbrowser.open(address)


def main() -> int:
    # paths.root() finds the bundle anyway; being explicit keeps it traceable and relocatable.
    if "COMPLIANCE_HELPER_ROOT" not in os.environ:
        os.environ["COMPLIANCE_HELPER_ROOT"] = str(root())
    # No API key prompt at start: the classification needs no LLM.
    os.environ.setdefault("COMPLIANCE_HELPER_MODEL", "none")

    sys.path.insert(0, str(root() / "src"))
    import uvicorn

    from compliance_helper.i18n import Language, t
    from compliance_helper.service.app import build_app, proxy_settings

    language = Language.parse(os.environ.get("COMPLIANCE_HELPER_LANG") or system_language())
    os.environ["COMPLIANCE_HELPER_LANG"] = language.value

    port_number = free_port()
    address = f"http://127.0.0.1:{port_number}/"
    print(t("cli.app_running", language=language, address=address))
    print(t("cli.app_close", language=language))
    threading.Thread(
        target=open_browser, args=(start_page(address, language.value),), daemon=True
    ).start()
    uvicorn.run(
        build_app(),
        host="127.0.0.1",
        port=port_number,
        log_level="warning",
        **proxy_settings(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
