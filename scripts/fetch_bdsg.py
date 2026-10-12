"""Fetch the BDSG in German or in its official English translation from gesetze-im-internet.de.

Context: the corpus builder parses the saved page offline; the English text is the translation by
the Language Service of the Federal Ministry of the Interior, published next to the German law. |
Input: --language de|en (--refresh re-fetches an existing file) | Output: data/raw/bdsg.html or
data/raw/en/bdsg.html, stored as served.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIActComplianceHelper/2.0)"}

SOURCES = {
    "de": ("https://www.gesetze-im-internet.de/bdsg_2018/BJNR209710017.html", TARGET),
    "en": ("https://www.gesetze-im-internet.de/englisch_bdsg/englisch_bdsg.html", TARGET / "en"),
}
#: Both pages hold the whole act; anything smaller is an error page.
MIN_SIZE = 150_000


def fetch(address: str, attempts: int = 3) -> bytes | None:
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(address, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310
                payload: bytes = response.read()
        except (urllib.error.URLError, OSError) as error:
            print(f"    attempt {attempt:d} failed: {error}")
            time.sleep(2 * attempt)
            continue
        if len(payload) >= MIN_SIZE:
            return payload
        print(f"    attempt {attempt:d}: only {len(payload):d} bytes — discarded")
        time.sleep(2 * attempt)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=sorted(SOURCES), default="de")
    parser.add_argument("--refresh", action="store_true", help="fetch even if already present")
    args = parser.parse_args(argv)

    address, directory = SOURCES[args.language]
    target = directory / "bdsg.html"
    if target.exists() and not args.refresh:
        print(f"already present: {target} ({target.stat().st_size / 1024:.0f} KB)")
        return 0
    print(f"BDSG ({args.language}): {address}")
    payload = fetch(address)
    if payload is None:
        print("    NOT FETCHED")
        return 1
    directory.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    print(f"    {len(payload) / 1024:.0f} KB stored in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
