"""Assemble the individual slides into one self-contained HTML presentation per language.

Context: one file per slide keeps each slide editable on its own, with the order defined in one
place; every text on a slide is a ``<de>…</de><en>…</en>`` pair, so both languages share one
layout. | Input: presentation/slides/*.html (1920x1080 sections), presentation/deck.json (order,
title, fonts), --language de|en (default: both), --measure to check the layout in a browser |
Output: docs/presentation.html (German), docs/presentation.en.html (English).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
SLIDES_DIR = ROOT / "presentation" / "slides"
INDEX = ROOT / "presentation" / "deck.json"
LANGUAGES = ("de", "en")
TARGETS = {
    "de": ROOT / "docs" / "presentation.html",
    "en": ROOT / "docs" / "presentation.en.html",
}

#: Design size of a slide; the page scales it down to the window width.
WIDTH, HEIGHT = 1920, 1080

#: Content ending below this line collides with the footer line of a slide.
CONTENT_LIMIT = 952

TEXT_PAIR = re.compile(r"<(de|en)>(.*?)</\1>", re.S)

PAGE_TEXT = {
    "de": {
        "description": "Architektur, Funktionsweise und Betrieb des EU AI Act und DSGVO "
        "Konformitätshelfers.",
        "slides": "Folien",
        "as_of": "Stand des Rechtstextes 31.05.2026",
        "not_advice": "keine Rechtsberatung",
        "hide_notes": "Sprechernotizen ausblenden",
        "show_notes": "Sprechernotizen einblenden",
        "hint": "Blättern mit &larr; und &rarr; &middot; Drucken ergibt eine Folie je Seite",
        "switch_label": "English",
        "switch_language": "en",
    },
    "en": {
        "description": "Architecture, workings and operation of the EU AI Act and GDPR "
        "Compliance Helper.",
        "slides": "slides",
        "as_of": "Legal text as of 31 May 2026",
        "not_advice": "not legal advice",
        "hide_notes": "Hide speaker notes",
        "show_notes": "Show speaker notes",
        "hint": "Page with &larr; and &rarr; &middot; Printing gives one slide per page",
        "switch_label": "Deutsch",
        "switch_language": "de",
    },
}


class Slide(NamedTuple):
    slide_id: str
    html: str
    note: str


def localize(raw: str, language: str, slide_id: str) -> str:
    """Keep the ``language`` side of every text pair and drop the other side.

    Raises:
        SystemExit: If a slide holds a different number of German and English texts, or a pair
            is nested or left open, because one language would then silently lose text.
    """
    counts = Counter(match.group(1) for match in TEXT_PAIR.finditer(raw))
    if counts["de"] != counts["en"]:
        raise SystemExit(
            f"Slide {slide_id}: {counts['de']} German and {counts['en']} English texts"
        )
    localized = TEXT_PAIR.sub(
        lambda match: match.group(2) if match.group(1) == language else "", raw
    )
    if re.search(r"</?(?:de|en)>", localized):
        raise SystemExit(f"Slide {slide_id}: nested or unclosed <de>/<en> text")
    return localized


def read_slides(index: dict, language: str) -> list[Slide]:
    """Read the slides in index order, in one language, with the speaker note split off."""
    slides: list[Slide] = []
    for slide_id in index["order"]:
        file = SLIDES_DIR / f"{slide_id}.html"
        if not file.exists():
            raise SystemExit(f"Slide missing: {file}")
        raw = localize(file.read_text(encoding="utf-8"), language, slide_id)

        note = ""
        match = re.search(r"<aside>(.*?)</aside>", raw, re.S)
        if match:
            note = match.group(1).strip()
            raw = raw[: match.start()] + raw[match.end() :]

        # These data attributes drive transitions in another tool's presenter mode; inert here.
        raw = re.sub(r'\s+data-(?:transition|section|build-in|build-out)="[^"]*"', "", raw)
        slides.append(Slide(slide_id, raw.strip(), note))
    return slides


def build_page(index: dict, slides: list[Slide], language: str) -> str:
    text = PAGE_TEXT[language]
    title = index["title"][language]
    other_page = TARGETS[text["switch_language"]].name
    font_links = "\n".join(
        f'<link rel="stylesheet" href="{face["href"]}">'
        for face in index.get("faces", {}).values()
        if "href" in face
    )

    parts = []
    for number, slide in enumerate(slides, 1):
        counter = f'<p class="counter">{number} / {len(slides)}</p>'
        note_block = f'<div class="note"><p>{slide.note}</p></div>' if slide.note else ""
        parts.append(
            f'<div class="stage" id="slide-{number}">{slide.html}{counter}</div>{note_block}'
        )

    return f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{text["description"]}">
<link rel="alternate" hreflang="{text["switch_language"]}" href="{other_page}">
{font_links}
<style>
  :root {{ --gutter: 24px; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: #11182B; }}
  body {{ font-family: 'IBM Plex Sans', Arial, sans-serif; -webkit-font-smoothing: antialiased; }}

  .header {{
    position: sticky; top: 0; z-index: 10;
    display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
    padding: 14px var(--gutter); background: #0B1220; color: #8FA3BF;
    border-bottom: 1px solid #22314F; font-size: 15px; line-height: 1.4;
  }}
  .header b {{ color: #FAFAF7; font-weight: 600; }}
  .header button, .header .language {{
    font: inherit; color: #BCCBDD; background: #1B2A41; cursor: pointer;
    border: 1px solid #38496B; border-radius: 8px; padding: 6px 14px; text-decoration: none;
  }}
  .header button:hover, .header .language:hover {{ background: #24375A; color: #FAFAF7; }}
  .header .hint {{ margin-left: auto; }}

  .slides {{ display: flex; flex-direction: column; gap: 32px; padding: 32px var(--gutter) 96px; }}

  /* The scale comes from the script below: scale() needs a plain number, and a width divided
     by {WIDTH} is a length in CSS. Without script the slide stays at 1 and the stage scrolls. */
  .stage {{
    position: relative; width: 100%; max-width: {WIDTH}px; margin: 0 auto;
    aspect-ratio: 16 / 9; overflow: hidden;
    border-radius: 14px; box-shadow: 0 18px 50px rgba(0, 0, 0, .45);
  }}
  .stage > section {{
    position: absolute; top: 0; left: 0;
    width: {WIDTH}px; height: {HEIGHT}px;
    transform-origin: top left; transform: scale(var(--scale, 1));
  }}

  /* The slide format spaces blocks only via the parent's gap; default browser margins add up
     to several hundred pixels per slide and push content off the bottom. */
  .stage section :where(h1, h2, h3, h4, p, ul, ol, table, figure, blockquote) {{
    margin: 0;
  }}
  .stage section :where(ul, ol) {{ padding-left: 1.3em; }}
  .stage section table {{ border-collapse: collapse; }}
  .stage section :where(td, th) {{ padding: 0.35em 0.6em; }}
  html:not(.scaled) .stage {{ overflow: auto; }}

  .counter {{
    position: absolute; right: 18px; bottom: 12px; margin: 0;
    font-size: 13px; color: rgba(138, 143, 126, .75);
  }}
  .note {{
    max-width: {WIDTH}px; margin: -12px auto 0; padding: 18px 26px;
    background: #0B1220; border: 1px solid #22314F; border-left: 3px solid #C8742B;
    border-radius: 10px; color: #A9BBD4; font-size: 16px; line-height: 1.6;
  }}
  .note p {{ margin: 0; }}
  body.notes-hidden .note {{ display: none; }}
  body.notes-hidden .slides {{ gap: 28px; }}

  @media print {{
    :root {{ --gutter: 0; }}
    html, body {{ background: #FFFFFF; }}
    .header, .note, .counter {{ display: none !important; }}
    .slides {{ gap: 0; padding: 0; }}
    .stage {{ border-radius: 0; box-shadow: none; break-after: page; }}
    @page {{ size: {WIDTH}px {HEIGHT}px; margin: 0; }}
  }}
</style>
</head>
<body>
<header class="header">
  <b>{title}</b>
  <span>{len(slides)} {text["slides"]} &middot; {text["as_of"]} &middot; {text["not_advice"]}</span>
  <button type="button" id="notes-toggle">{text["hide_notes"]}</button>
  <a class="language" href="{other_page}" hreflang="{text["switch_language"]}"
     lang="{text["switch_language"]}">{text["switch_label"]}</a>
  <span class="hint">{text["hint"]}</span>
</header>
<main class="slides">
{chr(10).join(parts)}
</main>
<script>
  (function () {{
    var stages = Array.prototype.slice.call(document.querySelectorAll('.stage'));
    if (!stages.length) return;

    function applyScale() {{
      var width = stages[0].clientWidth;
      document.documentElement.style.setProperty('--scale', width / {WIDTH});
      document.documentElement.classList.add('scaled');
    }}
    applyScale();
    window.addEventListener('resize', applyScale);
    if ('ResizeObserver' in window) new ResizeObserver(applyScale).observe(stages[0]);

    if (window.matchMedia) {{
      var printQuery = window.matchMedia('print');
      var onPrintChange = function (e) {{
        if (e.matches) document.documentElement.style.setProperty('--scale', 1);
        else applyScale();
      }};
      if (printQuery.addEventListener) printQuery.addEventListener('change', onPrintChange);
    }}

    // Paging scrolls to the next slide instead of keeping a view state, so the page stays
    // fully readable without JavaScript.
    var current = 0;
    function show(n) {{
      current = Math.max(0, Math.min(stages.length - 1, n));
      stages[current].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}
    document.addEventListener('keydown', function (e) {{
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{
        e.preventDefault(); show(current + 1);
      }} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
        e.preventDefault(); show(current - 1);
      }} else if (e.key === 'Home') {{ e.preventDefault(); show(0); }}
      else if (e.key === 'End') {{ e.preventDefault(); show(stages.length - 1); }}
    }});
    if ('IntersectionObserver' in window) {{
      var observer = new IntersectionObserver(function (entries) {{
        entries.forEach(function (e) {{
          if (e.isIntersecting) current = stages.indexOf(e.target);
        }});
      }}, {{ rootMargin: '-45% 0px -45% 0px' }});
      stages.forEach(function (b) {{ observer.observe(b); }});
    }}

    var toggle = document.getElementById('notes-toggle');
    var labels = {json.dumps([text["hide_notes"], text["show_notes"]], ensure_ascii=False)};
    toggle.addEventListener('click', function () {{
      var hidden = document.body.classList.toggle('notes-hidden');
      toggle.textContent = labels[hidden ? 1 : 0];
    }});
  }})();
</script>
</body>
</html>
"""


def build(index: dict, language: str) -> Path:
    """Write the presentation of one language and return its path."""
    slides = read_slides(index, language)
    target = TARGETS[language]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_page(index, slides, language), encoding="utf-8")
    size_kb = target.stat().st_size / 1024
    print(f"{target.relative_to(ROOT)}: {len(slides)} slides, {size_kb:.0f} KB")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language",
        choices=LANGUAGES,
        help="build only this language; without it both are built",
    )
    parser.add_argument(
        "--measure",
        action="store_true",
        help="after building, check in a browser that everything fits on the slide",
    )
    args = parser.parse_args(argv)

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    languages = (args.language,) if args.language else LANGUAGES
    targets = [build(index, language) for language in languages]

    if not args.measure:
        return 0
    return max(measure_layout(target) for target in targets)


def measure_layout(target: Path) -> int:
    """Render one page in Chromium and flag slides that overflow or use text below 24 px.

    Overflow past the slide height is cut off when presenting and is invisible in the source,
    so it is measured instead of estimated. Returns 1 if any slide is flagged.
    """
    try:
        import asyncio

        from playwright.async_api import async_playwright
    except ImportError:
        print("Measuring needs playwright: pip install playwright && playwright install chromium")
        return 0

    async def run() -> int:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": WIDTH, "height": 1200})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(target.as_uri())
            await page.wait_for_timeout(1800)
            measurement = await page.evaluate(
                """() => {
                  const ms = parseFloat(getComputedStyle(document.documentElement)
                             .getPropertyValue('--scale')) || 1;
                  const results = [];
                  document.querySelectorAll('.stage section').forEach((sec, i) => {
                    const sr = sec.getBoundingClientRect();
                    let bottom = 0, small = 0;
                    Array.from(sec.children).forEach(el => {
                      if (el.tagName === 'ASIDE') return;
                      if (getComputedStyle(el).position === 'absolute') return;
                      bottom = Math.max(bottom, (el.getBoundingClientRect().bottom - sr.top) / ms);
                    });
                    sec.querySelectorAll('*').forEach(el => {
                      if (el.children.length || !el.textContent.trim()) return;
                      // Superscripts and subscripts (10^25) are small by design.
                      if (el.tagName === 'SUP' || el.tagName === 'SUB') return;
                      if (parseFloat(getComputedStyle(el).fontSize) / ms < 23.5) small++;
                    });
                    results.push([i + 1, sec.id, Math.round(bottom), small]);
                  });
                  return results;
                }"""
            )
            await browser.close()

        print(f"\n{target.relative_to(ROOT)}")
        flagged = 0
        for number, slide_id, bottom, small in measurement:
            markers = []
            if bottom > CONTENT_LIMIT:
                markers.append("overflows by %d px" % (bottom - CONTENT_LIMIT))
            if small:
                markers.append("%d texts below 24px" % small)
            if markers:
                flagged += 1
            print("%2d %-26s %4d  %s" % (number, slide_id, bottom, "; ".join(markers)))
        if errors:
            print("Errors in the page:", errors)
            flagged += 1
        print("Slides flagged:", flagged, "of", len(measurement))
        return 1 if flagged else 0

    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
