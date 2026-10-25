"""Fetch the official full texts in German or English from the Official Journal via Cellar.

Context: eur-lex.europa.eu sits behind a firewall (HTTP 202, captcha) that is not to be bypassed;
Cellar serves the same texts without it, every language version with the same id anchors. | Input:
fixed Cellar work ids in LEGAL_ACTS, --language de|en (--refresh re-fetches existing files) |
Output: data/raw/*_official_journal_de.xhtml or data/raw/en/*_official_journal_en.xhtml.
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

#: Cellar ids of the *work*; Cellar returns the language version named in "Accept-Language".
LEGAL_ACTS = {
    "ai_act_official_journal": (
        "dc8116a1-3fe6-11ef-865a-01aa75ed71a1",
        "Regulation (EU) 2024/1689 — AI Act",
        1_200_000,
    ),
    "gdpr_official_journal": (
        "3e485e15-11bd-11e6-ba9a-01aa75ed71a1",
        "Regulation (EU) 2016/679 — General Data Protection Regulation",
        800_000,
    ),
}

CELLAR_URL = "http://publications.europa.eu/resource/cellar/%s"
CELLAR_LANGUAGES = {"de": "deu", "en": "eng"}
TARGET_DIRS = {"de": TARGET, "en": TARGET / "en"}


def fetch(cellar_id: str, target: Path, min_size: int, language: str, attempts: int = 3) -> bool:
    """Fetch one legal act and store it only if it reaches ``min_size``."""
    headers = {
        # This rendition carries the id anchors at which the parser splits articles and annexes.
        "Accept": "application/xhtml+xml",
        "Accept-Language": CELLAR_LANGUAGES[language],
    }
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(CELLAR_URL % cellar_id, headers=headers)
            with urllib.request.urlopen(  # nosec B310
                request, timeout=180
            ) as response:
                payload = response.read()
        except (urllib.error.URLError, OSError) as error:
            print(f"    attempt {attempt:d} failed: {error}")
            time.sleep(3 * attempt)
            continue

        # A short payload is an error page; storing it would pass it off as legal text later.
        if len(payload) < min_size:
            print(
                f"    attempt {attempt:d}: only {len(payload):d} bytes, expected "
                f"at least {min_size:d} — discarded"
            )
            time.sleep(3 * attempt)
            continue

        target.write_bytes(payload)
        print(f"    {len(payload) / 1024:.0f} KB stored")
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="also fetch what is already present")
    parser.add_argument("--language", choices=sorted(CELLAR_LANGUAGES), default="de")
    args = parser.parse_args(argv)

    target_dir = TARGET_DIRS[args.language]
    target_dir.mkdir(parents=True, exist_ok=True)
    pending = 0
    for stem, (cellar_id, designation, min_size) in LEGAL_ACTS.items():
        path = target_dir / f"{stem}_{args.language}.xhtml"
        print(f"{designation} ({args.language})")
        if path.exists() and not args.refresh:
            print(f"    already present ({path.stat().st_size / 1024:.0f} KB)")
            continue
        if not fetch(cellar_id, path, min_size, args.language):
            print("    NOT FETCHED")
            pending += 1

    if pending:
        print(f"\n{pending:d} legal acts missing. Without them the corpus is incomplete.")
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())
