"""Fetch the AI Act article by article from artificialintelligenceact.eu as a fallback source.

Context: the Official Journal text fetched through Cellar (fetch_official_journal.py) is the first
choice; the corpus build falls back to this site, one page per article, annex and recital, only
when that text is missing. | Input: the German pages of
artificialintelligenceact.eu | Output: data/raw/ai_act/{article,annex,recital}/*.json, log in
data/raw/ai_act/_fetch.log.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "data" / "raw" / "ai_act"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIActComplianceHelper/2.0)"}
PAUSE = 0.4

ARTICLE_COUNT = 113
RECITAL_COUNT = 180
ANNEXES = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]

#: Page chrome lines (German site UI) that are never part of the legal text.
BOILERPLATE = re.compile(
    r"^(BETA|Zum neuen AI Act Explorer|← ?Zurück zum Index|Inhaltsübersicht|"
    r"🔔 ?Neu:|Lesen Sie den offiziellen Text|Vergleichen Sie die Sprachversionen|"
    r"Ein individueller KI-Chatbot|Suche|Menü|Teilen|Drucken|Feedback|"
    r"Kapitel [IVXLC]+:|Abschnitt \d|Anhang [IVXLC]+:|Erwägungsgrund \d+$|"
    r"Artikel \d+:.*$)",
    re.IGNORECASE,
)

log_lines: list[str] = []


def _require_https(address: str) -> str:
    """Return the address unchanged if it is https, else raise ValueError.

    ``urlopen`` also accepts ``file://`` and ``ftp://``; the check stays correct even if the
    addresses ever come from a file instead of the source code.
    """
    if not address.startswith("https://"):
        raise ValueError(f"Only https is allowed, got: {address!r}")
    return address


def say(text: str) -> None:
    log_lines.append(text)
    (TARGET / "_fetch.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(text, flush=True)


def fetch(address: str, attempts: int = 3) -> str | None:
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(_require_https(address), headers=HEADERS)
            with urllib.request.urlopen(
                req,  # nosec B310
                timeout=45,
            ) as response:
                return response.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def extract_content(html: str, _heading_pattern: str = "") -> tuple[str, str]:
    """Return (title, text) of the unit, cut at the page structure.

    ``_heading_pattern`` is unused and kept only for the existing callers: cutting at a heading
    pattern turned 113 articles into 132, because a cross-reference ("Artikel 99") in running
    text looked like the start of an article.
    """
    soup = BeautifulSoup(html, "lxml")
    for element in soup(
        ["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "iframe"]
    ):
        element.decompose()

    title = ""
    header = soup.find("h1")
    if header:
        title = re.sub(r"\s*\|.*$", "", header.get_text(" ", strip=True)).strip()

    candidates: list[str] = []
    area = soup.find("article") or soup.find("main") or soup
    for node in area.find_all(["p", "li", "h2", "h3", "h4", "td"]):
        text = node.get_text(" ", strip=True)
        text = re.sub(r"[ \t ]+", " ", text).strip()
        if not text or len(text) < 3:
            continue
        if BOILERPLATE.match(text):
            continue
        if text.startswith("Artikel ") and len(text) < 90 and ":" in text:
            continue
        candidates.append(text)

    # The table of contents often repeats body lines; keep each once.
    seen: set[str] = set()
    lines: list[str] = []
    for row in candidates:
        dedup_key = row[:120]
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        lines.append(row)

    text = "\n\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text


def write(directory: str, name: str, record: dict) -> None:
    target = TARGET / directory / (f"{name}.json")
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    for directory in ("article", "annex", "recital"):
        (TARGET / directory).mkdir(parents=True, exist_ok=True)
    started = time.time()
    say("FETCHING AI ACT - {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    missing: list[str] = []

    for number in range(1, ARTICLE_COUNT + 1):
        if (TARGET / "article" / ("art-%03d.json" % number)).exists():
            continue
        html = fetch(f"https://artificialintelligenceact.eu/de/article/{number:d}/")
        if not html:
            missing.append(f"article {number:d}")
            continue
        title, text = extract_content(html, rf"Artikel {number:d}")
        write(
            "article",
            "art-%03d" % number,
            {
                "legal_act": "AI-Act",
                "legal_act_full_name": "Verordnung (EU) 2024/1689 über künstliche Intelligenz",
                "unit": "article",
                "number": str(number),
                "title": title,
                "text": text,
                "source": f"https://artificialintelligenceact.eu/de/article/{number:d}/",
            },
        )
        if number % 15 == 0:
            say(f"  article {number:d}/{ARTICLE_COUNT:d}")
        time.sleep(PAUSE)

    for annex_number in ANNEXES:
        if (TARGET / "annex" / (f"annex-{annex_number}.json")).exists():
            continue
        roman = {
            "I": 1,
            "II": 2,
            "III": 3,
            "IV": 4,
            "V": 5,
            "VI": 6,
            "VII": 7,
            "VIII": 8,
            "IX": 9,
            "X": 10,
            "XI": 11,
            "XII": 12,
            "XIII": 13,
        }[annex_number]
        html = fetch(f"https://artificialintelligenceact.eu/de/annex/{roman:d}/")
        if not html:
            missing.append(f"annex {annex_number}")
            continue
        title, text = extract_content(html, rf"Anhang {annex_number}")
        write(
            "annex",
            f"annex-{annex_number}",
            {
                "legal_act": "AI-Act",
                "legal_act_full_name": "Verordnung (EU) 2024/1689 über künstliche Intelligenz",
                "unit": "annex",
                "number": annex_number,
                "title": title,
                "text": text,
                "source": f"https://artificialintelligenceact.eu/de/annex/{roman:d}/",
            },
        )
        time.sleep(PAUSE)
    say("  annexes fetched")

    for number in range(1, RECITAL_COUNT + 1):
        if (TARGET / "recital" / ("recital-%03d.json" % number)).exists():
            continue
        html = fetch(f"https://artificialintelligenceact.eu/de/recital/{number:d}/")
        if not html:
            missing.append(f"recital {number:d}")
            continue
        title, text = extract_content(html, rf"Erwägungsgrund {number:d}")
        write(
            "recital",
            "recital-%03d" % number,
            {
                "legal_act": "AI-Act",
                "legal_act_full_name": "Verordnung (EU) 2024/1689 über künstliche Intelligenz",
                "unit": "recital",
                "number": str(number),
                "title": f"Erwägungsgrund {number:d}",
                "text": text,
                "source": f"https://artificialintelligenceact.eu/de/recital/{number:d}/",
            },
        )
        if number % 30 == 0:
            say(f"  recital {number:d}/{RECITAL_COUNT:d}")
        time.sleep(PAUSE)

    say("")
    for directory, expected in (
        ("article", ARTICLE_COUNT),
        ("annex", len(ANNEXES)),
        ("recital", RECITAL_COUNT),
    ):
        say("%s: %d of %d" % (directory, len(list((TARGET / directory).glob("*.json"))), expected))
    if missing:
        say("MISSING: {}".format(", ".join(missing[:40])))
    say("Duration: %.0f s" % (time.time() - started))
    say("DONE")


if __name__ == "__main__":
    main()
