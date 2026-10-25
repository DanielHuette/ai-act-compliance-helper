# Refactoring report

[Deutsche Fassung](REFACTORING_REPORT.de.md)

## Scope

**Context:** Rework of the German-only Konformitätshelfer 1.2.4 into the bilingual AI Act Compliance Helper 2.0.0 | **Input:** German code, data, corpus, search index and documentation | **Output:** English code, a German/English switch in every interface, bilingual content, one corpus and one search index per language

| Item | Before (1.2.4) | After (2.0.0) |
|---|---|---|
| Language of code, ids, data keys | German | English |
| User interface | German | German and English, switchable: web page, search page, command line (`--lang`), service (`?lang=`, cookie, Accept-Language), start scripts, Windows installer |
| Questions, obligations, cases, evaluation data | German | bilingual `{de, en}` values (379 questions, 57 obligations, 44 cases, 217 official examples) |
| Legal corpus | German, 2,811 units | German and English, 2,811 units each with identical ids; English from the Official Journal and the official BDSG translation |
| Search index | German, full rebuild about one hour | one per language, incremental rebuild of changed units only |
| Package / command | `helfer` / `konformitaetshelfer` | `compliance_helper` / `compliance-helper` |
| Tests | 218 | 670 (639 without models, network or Docker) |
| Comment lines in code | 9.6 % | below 5 % per file |

## Measured results

**Context:** Classification quality must not drop through the rework | **Input:** official Commission examples, stored cases, company questions | **Output:** figures per language

| Measurement | German | English |
|---|---|---|
| Official examples of the Commission draft guidelines | 207 of 217 | same walkthrough, language-independent |
| Stored cases | 44 of 44 | 44 of 44 |
| Company questions (free text, real models) | 100 of 100 | 100 of 100 |
| Python and browser walkthrough identical | 200 of 200 random runs | 200 of 200 |

## Defects fixed

**Context:** Findings of an independent review and a clean-install run | **Input:** version 1.2.4 and the intermediate state | **Output:** fixes, each with a regression test

| Finding | Change |
|---|---|
| "Don't know" counted as "yes" for Annex I products and exclusions | only "yes" affirms; open answers give "conditionally high risk" or an open result |
| A pure CV-ranking tool came out as "not high risk" in the web walkthrough (also Annex III 4(b), 5(b), 5(c), 8(a)) | questions are grouped by legal alternative; a "no" on one alternative no longer excludes another |
| Negations were ignored ("we do not use emotion recognition") | negated keywords no longer count |
| A visitor could switch the language model back on against the operator's setting | the service only uses the operator's configured model |
| The search page could show two different classifications | answer and classification use the same facts |
| Slow requests blocked the whole service; model calls had no timeout | work runs in a thread pool; configurable timeout |
| Secrets were not redacted in most log lines | redaction applies to every log record |
| No body size limit, no security headers | 413 above 128 KiB; Content Security Policy and related headers |
| Missing rule files silently gave "minimal risk" | loading fails with a clear message; the package ships its data |
| Raw ids in output ("needs_review", "KI-VO/anh-III/nr-4") | readable labels and citations in the chosen language |
| Two published figures were wrong (11 deviations, 303 legal bases) | corrected to 10 and 302 |

## Worked examples

**Context:** The accuracy figure was only stated, not visible on the page | **Input:** 20 of the 217 official examples, chosen to cover every verdict and nine areas | **Output:** a replayable showcase on the start page, guarded by tests and the parity check

| Finding | Change | Evidence |
|---|---|---|
| Visitors could not check "207 of 217" themselves | start page section with 20 worked examples; each replays the walkthrough and ends with the helper's finding next to the Commission's verdict and paragraph | `tests/test_showcase.py`: 20 of 20 agree; browser run of all 20, German and English |
| Curated answers could silently drift from the question flow | the replay rejects answers to questions the flow never asks; the export refuses a case that misses the verdict | `test_replay_rejects_answers_the_flow_never_asks`, `test_export_rejects_a_replay_that_misses_the_verdict` |
| The browser copy could fall behind the curated answers | `scripts/export_showcase.py` writes `web/showcase.json`; a test compares a fresh export with the committed file | `test_export_writes_the_web_copy_by_default_and_it_is_current` |
| Python and browser walkthrough were only compared on random answers | `scripts/check_parity.py` also replays the 20 worked examples in both | 400 of 400 random runs and 20 of 20 worked examples identical |
| YAML 1.1 reads the key `yes` as the boolean true, which emptied the answers | keys are `yes_answers` and `unknown_answers`; a case answered both yes and "don't know" is rejected | `test_load_cases_rejects_contradicting_answers` |

## Final check

**Context:** Acceptance before publication | **Input:** fresh clone, fresh environment | **Output:** all checks passed

| Check | Result |
|---|---|
| `ruff check`, `ruff format --check`, `mypy` | clean |
| `pytest` without models | 639 passed |
| Slow search and accuracy tests with models, both languages | passed |
| Container build and container tests | 13 passed |
| Wheel built and installed in a clean environment, `classify` run | works |
| Browser run of web page and search page, German and English, 390 px width | no console errors, no CSP violations, no language mix |
