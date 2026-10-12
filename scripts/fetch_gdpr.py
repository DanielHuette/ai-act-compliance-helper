"""Fetch the GDPR from dsgvo-gesetz.de with its paragraph and letter structure.

Context: fallback for the Official Journal text fetched through Cellar (fetch_official_journal.py),
used by the corpus build only when that text is missing; this source lists each paragraph of an
article as a list item, so answers can cite "Art. 35(3)(a)" instead of "somewhere in Art. 35". |
Input: the German pages of dsgvo-gesetz.de (--refresh re-fetches everything) | Output:
data/raw/gdpr/{article,recital}/*.json with a "paragraphs" field, log in data/raw/gdpr/_fetch.log.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "data" / "raw" / "gdpr"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIActComplianceHelper/2.0)"}
PAUSE = 0.35
ARTICLE_COUNT = 99
RECITAL_COUNT = 173

#: CSS classes of page chrome; removed by class, not by text pattern.
BOILERPLATE = (
    "empfehlung-erwaegungsgruende",
    "empfehlung-bdsg-paragraphen",
    "empfehlung-dsgvo-artikel",
    "page-navigation",
    "link-to-overview",
    "feedback",
    "hidden-print",
    "widget",
    "widget-area",
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
                timeout=40,
            ) as response:
                return response.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def _clean(text: str) -> str:
    text = text.replace(" ", " ").replace("‑", "-")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _content_area(html: str) -> Tag | None:
    soup = BeautifulSoup(html, "lxml")
    for element in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        element.decompose()
    area = soup.select_one("div.entry-content") or soup.find("article")
    if area is None:
        return None
    for css_class in BOILERPLATE:
        for element in area.select(f"[class*={css_class}]"):
            element.decompose()
    return area


def read_paragraphs(html: str) -> tuple[list[dict], str]:
    """Return (paragraphs, full text); each top-level list item is one paragraph."""
    area = _content_area(html)
    if area is None:
        return [], ""

    paragraphs: list[dict] = []
    ordered_list = area.find("ol", recursive=False) or area.find("ol")
    if ordered_list is not None:
        for number, list_item in enumerate(ordered_list.find_all("li", recursive=False), 1):
            subpoints = []
            for nested_list in list_item.find_all(["ol", "ul"], recursive=False):
                for position, row in enumerate(nested_list.find_all("li", recursive=False)):
                    letter = chr(ord("a") + position)
                    content = _clean(row.get_text(" ", strip=True))
                    if len(content) > 20:
                        subpoints.append({"letter": letter, "text": content})
                nested_list.decompose()
            text = _clean(list_item.get_text(" ", strip=True))
            if len(text) < 15 and not subpoints:
                continue
            paragraphs.append({"number": str(number), "text": text, "letters": subpoints})
    full_text = _clean(area.get_text("\n"))
    return paragraphs, full_text


def table_of_contents() -> dict[str, dict]:
    """Map article number to title, chapter and section heading from the start page."""
    html = fetch("https://dsgvo-gesetz.de/")
    if not html:
        return {}
    soup = BeautifulSoup(html, "lxml")
    toc_by_article: dict[str, dict] = {}
    chapter = section_title = ""
    for node in soup.find_all(["h2", "h3", "h4", "a"]):
        text = _clean(node.get_text(" ", strip=True))
        if not text:
            continue
        if re.match(r"^Kapitel\s+\d+", text):
            chapter, section_title = text, ""
            continue
        if re.match(r"^Abschnitt\s+\d+", text):
            section_title = text
            continue
        match = re.match(r"^Artikel\s+(\d{1,3})\s*[:\-–]?\s*(.*)$", text)
        if match:
            number, title = match.group(1), match.group(2).strip()
            if number not in toc_by_article or (title and not toc_by_article[number]["title"]):
                toc_by_article[number] = {
                    "title": title,
                    "chapter": chapter,
                    "section_title": section_title,
                }
    return toc_by_article


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="fetch everything again")
    args = parser.parse_args(argv)

    (TARGET / "article").mkdir(parents=True, exist_ok=True)
    (TARGET / "recital").mkdir(parents=True, exist_ok=True)
    started = time.time()
    say("FETCHING GDPR - {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))

    toc_by_article = table_of_contents()
    say(f"Table of contents: {len(toc_by_article):d} article titles")
    (TARGET / "table_of_contents.json").write_text(
        json.dumps(toc_by_article, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    missing: list[str] = []
    without_paragraphs: list[str] = []

    for number in range(1, ARTICLE_COUNT + 1):
        target = TARGET / "article" / ("art-%02d.json" % number)
        if target.exists() and not args.refresh:
            try:
                if json.loads(target.read_text(encoding="utf-8")).get("paragraphs"):
                    continue
            except (OSError, json.JSONDecodeError):
                pass
        address = f"https://dsgvo-gesetz.de/art-{number:d}-dsgvo/"
        html = fetch(address)
        if not html:
            missing.append(f"article {number:d}")
            continue
        paragraphs, full_text = read_paragraphs(html)
        if not paragraphs:
            without_paragraphs.append(str(number))
        header = toc_by_article.get(str(number), {})
        target.write_text(
            json.dumps(
                {
                    "legal_act": "GDPR",
                    "legal_act_full_name": "Verordnung (EU) 2016/679 (Datenschutz-Grundverordnung)",
                    "unit": "article",
                    "number": number,
                    "title": header.get("title", ""),
                    "chapter": header.get("chapter", ""),
                    "section_title": header.get("section_title", ""),
                    "source": address,
                    "text": full_text,
                    "paragraphs": paragraphs,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        if number % 15 == 0:
            say(f"  article {number:d}/{ARTICLE_COUNT:d}")
        time.sleep(PAUSE)

    for number in range(1, RECITAL_COUNT + 1):
        target = TARGET / "recital" / ("recital-%03d.json" % number)
        if target.exists() and not args.refresh:
            continue
        address = f"https://dsgvo-gesetz.de/erwaegungsgruende/nr-{number:d}/"
        html = fetch(address)
        if not html:
            missing.append(f"recital {number:d}")
            continue
        _, full_text = read_paragraphs(html)
        target.write_text(
            json.dumps(
                {
                    "legal_act": "GDPR",
                    "legal_act_full_name": "Verordnung (EU) 2016/679 (Datenschutz-Grundverordnung)",
                    "unit": "recital",
                    "number": number,
                    "title": f"Erwägungsgrund {number:d}",
                    "source": address,
                    "text": full_text,
                    "paragraphs": [],
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        if number % 40 == 0:
            say(f"  recital {number:d}/{RECITAL_COUNT:d}")
        time.sleep(PAUSE)

    say("")
    say("Articles: %d of %d" % (len(list((TARGET / "article").glob("*.json"))), ARTICLE_COUNT))
    say("Recitals: %d of %d" % (len(list((TARGET / "recital").glob("*.json"))), RECITAL_COUNT))
    if without_paragraphs:
        say(
            "without recognised paragraphs (single-paragraph articles): {}".format(
                ", ".join(without_paragraphs)
            )
        )
    if missing:
        say("MISSING: {}".format(", ".join(missing[:40])))
    say("Duration: %.0f s" % (time.time() - started))
    say("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
