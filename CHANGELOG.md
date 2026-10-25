# Changelog

All notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): major for incompatible changes,
minor for new features, patch for fixes.

**Context:** what changed in each version | **Input:** the commit history | **Output:** one entry per version, rule set and legal data first

Changes to the rule set and the legal corpus come before program changes within each entry.
For someone who receives an answer, a changed article reference matters more than any program
change. Every entry on the data status names the date the rule set stands on afterwards.

## [Unreleased]

**Context:** visitors can check the measured accuracy themselves | **Input:** 20 official Commission examples with curated answers | **Output:** worked examples on the start page, a replay check and a parity check for them

The rule set still stands on **31 May 2026**; no question, rule or legal text changed.

### Added

- Start page section with 20 worked examples from the Commission draft guidelines of 19 May
  2026: 13 high risk, 6 not high risk, 1 exemption under Article 6(3), across nine areas. A card
  replays the walkthrough with the answers prefilled and ends with the helper's finding next to
  the Commission's verdict and paragraph, in German and English.
- `data/evaluation/showcase.yaml` (the answers), `compliance_helper.classification.showcase`
  (replay and agreement check) and `scripts/export_showcase.py`, which writes
  `web/showcase.json` and refuses to write a case that misses the Commission's verdict.
- `scripts/check_parity.py` also replays the 20 worked examples in Python and in the browser
  code and requires identical results.
- Web page: a tab bar at the bottom with four deep-linkable views, `#projekt` (the walkthrough),
  `#organigramm` (the stations from legal text to finding, with the skills applied at each),
  `#benchmarks` (the measurement as charts) and `#praesentation` (eight self-playing scenes).
  Browser back and forward move between tabs; reduced motion stops autoplay and moving signals.
- `scripts/export_benchmarks.py` writes `web/benchmarks.json` from the run logs, figures and
  corpus report; `tests/test_benchmarks.py` keeps it current and checks that every chart adds up.
- The masthead names the measured figure, 207 of 217 official examples.

### Changed

- Web page in the RepoCity design: night blue, solid gold for everything chosen, self-hosted
  Archivo, Source Serif 4 and Syncopate (`web/fonts/`, licences in `web/fonts/LICENSE`).
- `scripts/check_web_locales.py` checks the catalog keys of every script in `web/`, not only
  `page.js`.

### Fixed

- Web page on phones: the step rail no longer runs off the right edge, the heading no longer
  touches the GitHub and language buttons, the text over the flag photo has a darker veil, and
  the 20 worked examples scroll sideways instead of filling four screen heights.
- Web page: the 187 examples shown beside a finding and the 217 examples of the measurement are
  told apart; "six questions" now reads "about six steps", as measured (5.3 on average).
- Web page: the footer stands at the end of the page instead of between the examples and the
  frequently asked questions; questions, Annex III areas and sources are laid out in columns.

## [2.0.0] - 2026-10-09

**Context:** the project speaks English as well as German | **Input:** all commits after 1.2.4 | **Output:** English code and data names, a German/English switch everywhere, an English corpus and search index

Version 2.0.0 renames the whole project from German to English identifiers and adds English as
a second language for every user-facing text, the legal corpus and the search. The corpus covers
Regulation (EU) 2024/1689 (Artificial Intelligence Act, AI Act), Regulation (EU) 2016/679
(General Data Protection Regulation, GDPR) and the German Federal Data Protection Act
(Bundesdatenschutzgesetz, BDSG). German output is unchanged in substance, except where the
final review found it wrong (see Fixed). The rule set still stands on **31 May 2026**; the measured figures are
unchanged: **207 of 217** official examples, **5.3** steps on average, **400 of 400** parity
runs.

### Breaking

- The distribution is now `ai-act-compliance-helper` (was `konformitaetshelfer`), the Python
  package `compliance_helper` (was `helfer`), the command `compliance-helper`
  (was `konformitaetshelfer`).
- Subcommands are `classify`, `ask`, `search`, `serve` and `status` (were `pruefen`, `fragen`,
  `suchen`, `dienst`, `stand`); all options are English, for example `--legal-act`,
  `--show-wording`, `--no-color`. `--legal-act` accepts only `AI-Act`, `GDPR`, `BDSG` and
  `Guidelines`.
- Web service routes are English: `/api/classify`, `/api/search`, `/api/ask`,
  `/api/questionnaire`, `/api/deadlines`, `/health`, `/search` and `/classification/`.
- Environment variables use the prefix `COMPLIANCE_HELPER_` (were `HELFER_`), for example
  `COMPLIANCE_HELPER_PORT` and `COMPLIANCE_HELPER_MODEL`. The container build arguments are
  `WITH_SEARCH_MODEL` and the container user is `app`.
- Directories and files are English: `daten` became `data` (`rules`, `processed`, `cases`,
  `evaluation`), `skripte` became `scripts`, `verpacken` became `packaging`, `praesentation`
  became `presentation`; the search index files are `search_index.*`.
- Data keys and values in the rule, case and evaluation files are English (`id`, `as_of`,
  `title`, `action_required`, `legal_basis`, `confidence: certain | likely | needs_review`).
- Citation ids follow a new scheme, for example `AI-Act/art-6/para-1-a`,
  `AI-Act/annex-III/pt-4-a`, `AI-Act/recital-5`, `GDPR/art-35`, `BDSG/sec-26/para-1`. Question
  ids start with `main:`, `follow-up:`, `annex-i:` or `area:`.
- Test markers are `slow` and `network` (were `langsam` and `netz`).
- Workflows are `.github/workflows/checks.yml` and `.github/workflows/packages.yml`.

### Added

- **English throughout.** Every user-facing text in the rule set, question flow, cases and
  evaluation data is a German/English pair. Message catalogues per area live in
  `src/compliance_helper/locales/de` and `src/compliance_helper/locales/en`, those of the static
  page in `web/locales`.
- **Language switch.** A switch **DE | EN** on the static page (`web/`) and on the search page of
  the service; `?lang=` in the address; a `lang` cookie and the browser's `Accept-Language`
  header for the service; `--lang de|en` and `COMPLIANCE_HELPER_LANG` for the command line and
  the packages. Installers and start scripts speak both languages.
- **English corpus** `data/processed/corpus.en.jsonl` with the same 2811 unit ids as the German
  one: the AI Act and the GDPR from the English Official Journal via Cellar, the BDSG from the
  official translation on gesetze-im-internet.de, the cases from the English side of
  `data/cases`. `scripts/fetch_official_journal.py` and the new `scripts/fetch_bdsg.py` take
  `--language`; the corpus build takes `--language` and `--output-dir`.
- **English search index** `data/processed/search_index.en.*`, built with bge-m3. The service
  loads both indexes at start with one shared embedding model and answers each request from the
  index of its language; the command line loads only the index of its language. A missing index
  is named together with its build command.
- **Incremental index build.** `compliance-helper build-index --language de|en` reuses vectors
  and sparse weights of units whose id and text are unchanged, resumes from checkpoints after an
  abort and rebuilds everything with `--from-scratch`.
- English free text reaches the same rule set through English purpose sentences and
  vocabularies (`src/compliance_helper/classification/vocabulary.py`). Each description is
  matched only with the vocabulary of its own language. English reaches the same expected
  classification as German on every stored case.
- The citation route of the search also reads English forms such as "point (f) of
  Article 5(1)", "Article 5(1), point (f)" and "lit. f".
- `scripts/check_web_locales.py` checks that the catalogues, markup and script of the static
  page name the same keys.
- English and German documentation: every guide exists as `X.md` (English) and `X.de.md`
  (German), from `README.md` to the files in `docs/`. Issue and pull request templates are
  bilingual; the issue templates are now `bug_report.yml`, `legal_error.yml` and
  `feature_request.yml`.
- `compliance-helper build-corpus --language de|en` and `compliance-helper build-index
  --language de|en` build the corpus and the search index of one language. Every rebuild hint
  names these commands, which work in the source folder, in an installed package and in the
  container; `scripts/build_search_index.py` is gone.
- The wheel and the source archive ship the rules, the question flow, the use cases, both corpora
  and the web pages, installed under `<environment>/share/ai-act-compliance-helper/`; an installed
  `compliance-helper classify` works without a source folder. Without rule files the command line
  refuses with a message instead of answering "minimal risk".
- `--verbose` on every command shows the developer log; without it the command line shows only
  notices from the message catalogs, in the chosen language.
- `constraints.txt` pins every dependency; the image, the checks and the desktop packages install
  with it, and `pip-audit` audits it.
- `scripts/check_rule_set.py` holds the rule-set smoke test and the legal-basis check that the
  workflow ran inline; `scripts/check_all.sh` now runs exactly the commands of the checks.

### Changed

- Risk classes, roles, confidence and severity are shown with readable labels; rule citations
  are rendered from their ids in the active language. German reads "Unterabsatz 2 Buchstabe a"
  instead of "Buchstabe ua2-a", and lettered annex points read "Anhang III Nummer 4
  Buchstabe a".
- Docstrings, comments and developer messages are English; module docstrings state context,
  input and output.
- The search code is split into the modules `citations`, `keywords`, `store` and `index`.
- The German corpus was rebuilt with the current use cases and its index updated
  incrementally.
- `ask` without a language model prints the classification once, with labels instead of ids such
  as `deployer` or `[needs_review]`.
- `status` shows the date of the corpus of the active language; the English corpus showed
  "as of unknown".
- `--count` accepts 1 to 20 for `ask` and 1 to 30 for `search`, like the web service; `--model`
  accepts `auto`, `anthropic`, `openai` and `none`; abbreviated options such as `--lan` are
  refused; `ask --help` documents `--role`.
- The public page and `llms.txt` give the passage counts measured from the corpus (1,386 for the
  AI Act, 1,024 for the GDPR, in German and English) and 379 questions; `llms.txt` is in English
  and German.
- The release workflow grants write access only to the job that attaches the packages and pins
  the release action by commit.

### Removed

- `BAUPLAN.md` is no longer part of the repository.
- The superseded measurement runs `messung-*`, `messung2-*` and `_nachzumessen.json`; the valid
  run is `data/evaluation/answers-*.json`.
- `scripts/fetch_eurlex.py`: the Official Journal text comes through Cellar
  (`scripts/fetch_official_journal.py`), and nothing read the files it wrote.
- The unused dependencies `slowapi`, `python-multipart`, `onnxruntime`, `pytest-asyncio` and
  `types-requests`; `httpx` moved to the `dev` extra.

### Fixed

- Five places in the obligation texts and the preliminary questions had a wrongly replaced
  umlaut ("sexuellen", "kontextuellen", "virtuelle") that reached the output.
- The web page named 378 questions; the measured count is 379.
- `--help` works next to `-h`; it used to abort with an error.
- Piping the output into a program that stops reading (`| head`) no longer ends in a traceback.
- `.dockerignore` excludes caches and build metadata at every depth, not only at the top.
- **Question flow.** "I don't know" no longer counts as yes for an Annex I category or condition,
  nor as an affirmed exclusion. On a page that asks all questions of a provision at once, a "no"
  to a question of one alternative (job advertisements, tenders) no longer excludes Annex III
  point 4(a) when another alternative (screening or evaluating applicants) is met; a pure
  CV-ranking tool is high risk on the web page as in the command line and the service. The
  parity check also compares evidence, open provisions and the closing text.
- **Fail closed.** Missing or broken rule files stop the command line with a localized message
  and make the service answer classification with 503 and `/health` with `not_ready`; nothing is
  classified as minimal risk for lack of rules. Classification works without corpus or search
  index; "not ready" is 503, not 400.
- **Service safeguards.** Request bodies over `COMPLIANCE_HELPER_MAX_BODY_BYTES` (128 KiB) get
  413, invalid JSON gets 400, an empty description gets the same localized refusal as on the
  command line, and number traits that are negative, infinite or not a number are refused
  instead of ending in 500. Every response carries a Content Security Policy and the other
  security headers; `X-Forwarded-For` counts only from `COMPLIANCE_HELPER_TRUSTED_PROXIES`; the
  rate limiter's address cap is a hard cap. Slow work runs off the event loop, and language
  model calls end after `COMPLIANCE_HELPER_LLM_TIMEOUT` seconds (default 30).
- **Language model.** A client can no longer switch on a model or a vendor the operator did not
  set up, and the user's question goes to the model inside its own fenced section, like the
  description and the evidence.
- **Secrets in logs.** Every log record of every logger is redacted when it is created, through
  a log record factory; before, almost no log line passed the filter.
- **Purpose matching.** It shares the embedding model and the cross-encoder of the search instead
  of loading a second copy, loads at service start off the event loop, honours
  `COMPLIANCE_HELPER_RERANK=0`, and `/health` names the reason when it is off. The full container
  image ships the cross-encoder and has purpose matching on; the small image keeps it off and says
  so.
- **Readable output.** The search page shows one classification, not two; answers, cases and
  warnings show labels instead of ids such as `high_risk_annex_iii`, `deployer`,
  `[needs_review]` or exception class names; visitors of the search page get one plain sentence
  when something is missing, the details go to the log and `/health`; switching DE | EN keeps
  the entered description and result.
- **German and English alike.** Annex III keywords honour negation in both languages; English
  free text reaches the cases its German equivalent reaches and reads the role alike; matched
  keywords are shown as written in the description; the command line in German prints German
  notices; `Accept-Language` quality values are honoured; an explicit language choice survives
  `/`, and the packaged app follows the system language.
- **Search.** Each cited article gets the legal act named right after it: "Article 6 AI Act and
  Article 35 GDPR" now finds Article 6 of the AI Act. Every build hint names
  `compliance-helper build-corpus|build-index --language de|en`.
- **Tidying.** Unused catalog keys are removed and `scripts/find_unused_catalog_keys.py` keeps it
  that way; `scripts/export_question_flow.py` writes `web/question_flow.json` by default and the
  unread copy in `data/processed/` is gone; `scripts/check_parity.py` stops a hanging Node.js
  run after five minutes; the question-flow page links its favicon relative to itself; comments
  and identifiers left in German in configuration and the web page are English.

## [1.2.4] - 2026-10-04

**Context:** packaging | **Input:** the new web interface | **Output:** packages with the same interface as the web page

The packages carry the same interface as the web page: the questionnaire with picture, the
three answers including "I don't know". Version 1.2.3 had been built before these changes were
finished.

## 1.2.3 - 2026-10-04

**Context:** one deviation fewer | **Input:** official example 92 | **Output:** 207 of 217 instead of 206

- Example 92, the creditworthiness of the owner of a small business that is not a legal person,
  was classified as high-risk against the Commission's verdict. The preliminary question on
  assessing people now says that analysing only the business's accounts, turnover and payment
  behaviour assesses no person (paragraph 73 of the guidelines).
- The web interface was rebuilt as a questionnaire with the course of the review at the side and
  the citation in the margin of each question.

## 1.2.2 - 2026-10-04

**Context:** Windows package | **Input:** a failed build | **Output:** a Windows package in every case

- Inno Setup is no longer preinstalled on GitHub runners; the step reported success without
  building. It is now installed, the step fails without it, and a zip archive is always built.

## 1.2.1 - 2026-10-04

**Context:** two errors seen only on other machines | **Input:** the first package builds | **Output:** working Windows parity check and container start page

- The parity driver pasted the question flow path raw into JavaScript; Windows backslashes
  broke it. The path is now passed as a JSON (JavaScript Object Notation) string.
- The container lacked the `web` folder, so `/` answered 404.

## 1.2.0 - 2026-10-04

**Context:** asking instead of guessing | **Input:** the draft Commission guidelines of 19 May 2026 | **Output:** a question flow measured against 217 official examples

- The classification comes from a question flow the user answers, no longer from guessing
  from a description. Measured: 206 of 217 official examples, 5.3 steps on average, 400 of 400
  parity runs between web page and program.
- New source: the draft Commission guidelines of 19 May 2026 on classifying high-risk AI
  systems. Every question, exclusion and example carries its paragraph number: 379 questions on
  31 provisions, 214 exclusions, 187 examples, plus 3 preliminary questions, 4 notes, 8 area
  questions and 15 Annex I product categories.
- Three answers per question: yes, no and "not applicable"; an exclusion applies only on an
  explicit answer.
- New finding "conditionally high-risk" for Annex III point 2, which requires the deployer to be
  designated as a critical entity.
- Annex III point 2 requires all conditions together; Annex I asks for safety component **or**
  regulated product, no longer both.
- Static web page running the classification in the browser without server or model; one export
  of the question flow read by both web page and program; a parity check of both.
- Packages for Windows, macOS and Linux built on three runners, with a start script that picks a
  free port between 8713 and 8799 and a check that the built package starts.

## 1.1.0 - 2026-10-04

**Context:** accuracy on outside questions | **Input:** 100 descriptions as companies submit them | **Output:** 100 of 100 instead of 55

- Corpus rebuilt on 4 October 2026: 2811 units, no warning. AI Act (1386) and GDPR (1024) both
  from the Official Journal; Annex III split down to the letter; Annex I recovered; Annex XI no
  longer truncated; the definitions in Article 3 AI Act and Article 4 GDPR added.
- New purpose catalogue as a second route into the same rule set, and 100 company questions with
  the citation behind each expected result.
- Article 50 now respects the role; prohibitions need stronger evidence than other classes;
  Article 5(1)(d) requires its exact wording; the exception in Article 3(63) for models not
  placed on the market is honoured.
- The stored search index is checked against the corpus ids, not only their count.
- Fixed an endless recursion in the corpus parser and wrong letter points from nested lists.

## 1.0.0 - 2026-10-03

**Context:** first version | **Input:** AI Act, GDPR, BDSG | **Output:** a rule-based classification with citations

- Rule set as of 31 May 2026: 28 classification rules, 57 obligations, 26 sections of the data
  protection review path, 5 deadline stages under Article 113, 3 penalty tiers under Article 99.
- Corpus of 2721 units from the Official Journal, artificialintelligenceact.eu,
  dsgvo-gesetz.de and gesetze-im-internet.de, plus 44 use cases.
- Classification from a decision tree in YAML (YAML Ain't Markup Language) files; obligations
  per provider and deployer; open questions instead of guesses.
- Search over four routes merged by reciprocal rank fusion, reranked by a cross-encoder; local
  embedding model bge-m3; answers optionally phrased by a large language model (LLM), otherwise
  built from the rule set.
- Command line, web service with five Application Programming Interface (API) routes,
  container, input limits and protection against injected instructions.

[2.0.0]: https://github.com/DanielHuette/ai-act-compliance-helper/compare/v1.2.4...v2.0.0
[1.2.4]: https://github.com/DanielHuette/ai-act-compliance-helper/releases/tag/v1.2.4
