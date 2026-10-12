# AI Act Compliance Helper

**English** | [Deutsch](README.de.md)

**Context:** what the tool does and where to start | **Input:** a description of your AI system, given as answers to questions | **Output:** its risk class under the AI Act, with the exact legal provision behind it

About six questions, and you know which risk class your artificial intelligence (AI) system
falls into under Regulation (EU) 2024/1689 laying down harmonised rules on artificial
intelligence (Artificial Intelligence Act, AI Act), together with the exact provision the
classification rests on. Not "Annex III", but "Annex III point 4(a)". The tool works in German
and English.

![License](https://img.shields.io/badge/License-Apache--2.0-blue)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue)
[![Checks](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/checks.yml/badge.svg)](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/checks.yml)
[![Build packages](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/packages.yml/badge.svg)](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/packages.yml)

**Project page:** <https://konformitaetshelfer.speedofthespirit.dev/>, no sign-up, no
installation, works on a phone.
**On your own computer:** [ready-made packages for Windows, macOS and
Linux](https://github.com/DanielHuette/ai-act-compliance-helper/releases).

## This is not legal advice

**Context:** limits of the tool | **Input:** none | **Output:** what you may and may not rely on

The tool classifies an AI system on the basis of the text of the regulation and names the
provisions it relies on. It is **not legal advice**, **no substitute for a case-by-case
review**, and **no guarantee of correctness** is given. Before any decision with financial or
legal consequences, have the current legal position checked by a lawyer or the competent
supervisory authority. Details: [docs/liability.md](docs/liability.md).

## How accurate is it?

**Context:** measured accuracy against an outside standard | **Input:** the official examples of the European Commission | **Output:** how many examples the tool classifies as the Commission does

**207 of 217 official examples** of the European Commission are classified correctly, in
**5.3 steps** per case on average.

The examples come from the draft Commission guidelines of 19 May 2026 on the classification of
high-risk AI systems. Each one describes a system and states the Commission's verdict. The test
was whether the tool reaches the same verdict when someone knows only the description. The run
used the German question wording; the English questions have the same ids and the same logic.

Seven of the ten deviations do not measure the tool: their descriptions name no area of use at
all, and the exemption in Article 6(3) rightly never comes up without one. Leaving them out
gives **207 of 210**. The method and every single deviation are in
[data/evaluation/MEASUREMENT.md](data/evaluation/MEASUREMENT.md).

What this figure does not show: no lawyer has reviewed the run.

## Why questions instead of guessing

**Context:** the central design decision | **Input:** experience from the first versions | **Output:** why the classification comes from answers

The first version let users describe their system and guessed the classification from the
text, first with keyword lists, then by comparing meaning. On twenty descriptions written the
way companies really submit them, it got 11 of 20 right; after a night of work, 20 of 20.

The approach was still wrong. A lawyer asks five to eight things and is then certain, not
98 percent sure. Accurate guessing is worse than asking, and the tool was guessing answers to
questions it could simply have asked.

Today the question flow decides. Because the answers come from the user, the result is not
probable but correct, as far as the answers are. And the user sees what it depends on.

## What is inside

**Context:** scope of data and checks | **Input:** the repository as of version 2.0.0 | **Output:** measured counts

| | |
|---|---|
| Legal corpus | 2811 individually citable text units per language: 1386 from the AI Act, 1024 from Regulation (EU) 2016/679 (General Data Protection Regulation, GDPR), 357 from the German Federal Data Protection Act (Bundesdatenschutzgesetz, BDSG), 44 worked use cases |
| Question flow | 379 questions on 31 provisions of the law, 214 explicit exclusions, 187 official examples |
| Sourced | Every question, exclusion and example carries the paragraph number of the official interpretation |
| Two languages | German and English for the web page, the command-line interface (CLI), the web service, the legal corpus and the search index; both corpora use the same unit ids |
| Two code paths, one result | Web page and program provably compute the same: 400 of 400 test runs |
| Tests | 641 tests, of which 610 run on every push without models or network |

The questions are taken line by line from the draft guidelines of the European Commission of
19 May 2026. None of them is invented.

## What a walkthrough looks like

**Context:** the order of the questions | **Input:** your answers | **Output:** a finding with class, provision and comparable official examples

1. **Three preliminary questions.** Is it an AI system under Article 3(1) at all? Does it
   assess people or only companies? Do you act on behalf of a public authority?
2. **Annex I.** Is your system part of a regulated product (machine, toy, lift, medical
   device, vehicle), or is it such a product itself? 15 product categories.
3. **Eight area questions.** What does your system deal with? Employment, money and essential
   services, physical traits, education, supply networks, courts and elections, police,
   borders. These eight only sort.
4. **The legal questions of the chosen area.** This is where the decision is made.
5. **The exemption under Article 6(3)**, only if a provision applies beforehand. Four
   conditions and the counter-exception for profiling.
6. **The finding.** Class, provision, and the official examples to compare with.

Every question has three answers: Yes, No and **I don't know**. The third is not a
convenience. A tool that screens job applications does not post job adverts; asked whether an advert
announces a specific vacancy, there is neither yes nor no. A forced No measurably dropped
exactly such cases from the classification.

## Getting started

**Context:** three ways to use the tool | **Input:** a browser, a package or the source code | **Output:** a running classification in German or English

### In the browser

<https://konformitaetshelfer.speedofthespirit.dev/>: nothing to install. The page in `web/`
consists of one HyperText Markup Language (HTML) file, two JavaScript files, the question data
and one text catalogue per language. No sign-up, no server, your answers are not transmitted.
The switch **DE | EN** in the top right corner changes the language; `?lang=en` in the address
opens the page in English directly.

### As a program

Download the package for your system from the
[releases page](https://github.com/DanielHuette/ai-act-compliance-helper/releases), install,
start. The interface opens in the browser, in the language of the operating system. No Python,
no Conda, no setup.

The program adds a **full-text search in the legal text**: a question in your own words, and
the tool shows the provisions that answer it. Best results need the search model bge-m3 of
about 2.3 gigabytes (GB), which the package does not contain; the package searches with a
simpler fallback. The classification needs no model.

### From source

```bash
git clone https://github.com/DanielHuette/ai-act-compliance-helper
cd ai-act-compliance-helper
pip install -e .                 # add ".[search]" for the bge-m3 search model
compliance-helper --lang en classify "We pre-sort job applications with purchased software" --role deployer
compliance-helper --lang en serve   # web service on http://127.0.0.1:8000/
```

`python packaging/launch_app.py` starts the service like the package does, on a free port
between 8713 and 8799, and opens the browser.

A built wheel (`pip install ai-act-compliance-helper-2.0.0-py3-none-any.whl`) brings the rules,
the question flow, the use cases and both corpora along; only the search indexes stay out, so
search runs on the fallback until `compliance-helper build-index --language de` (and
`--language en`) has built them. `--verbose` shows the developer log of any command.

## Choosing the language

**Context:** German and English throughout | **Input:** a language choice per page, command or request | **Output:** texts, citations and search results in that language

| Where | How | Default |
|---|---|---|
| Web page (`web/`) | Switch **DE \| EN**, or `?lang=de` / `?lang=en` in the address | Choice stored in the browser, then the browser language, then German |
| Web service | `?lang=en` on any page or Application Programming Interface (API) route, or the cookie `lang` | `Accept-Language` header of the browser (highest weight first), then `COMPLIANCE_HELPER_LANG`, then German |
| Command line | `--lang de` or `--lang en` | Environment variable `COMPLIANCE_HELPER_LANG`, then German |
| Package | Environment variable `COMPLIANCE_HELPER_LANG` | Language of the operating system |

The search uses the index of the active language: `data/processed/search_index.*` for German,
`data/processed/search_index.en.*` for English. Both indexes ship with the repository.

## How the classification is made

**Context:** where the result comes from | **Input:** the rule files | **Output:** a deterministic classification that no language model can change

From the rule set, not from a language model. Three text files carry it, written in YAML (a
plain-text data format), with every text in German and English:

- `data/rules/question_flow/*.yaml`: the questions, exclusions and official examples, each with
  the paragraph number of the guidelines
- `data/rules/question_flow_layout.yaml`: the order, meaning which question comes when, which one
  decides and which one only informs
- `data/rules/ai_act_obligations.yaml`: which obligations follow from a class and a role

A large language model (LLM) phrases the answer at most. It cannot change the result. The
reason: an invented classification costs money and trust.

### Both code paths compute the same, and this is measured

The classification runs in two places: in `src/compliance_helper/classification/question_flow.py`
for the program and in `web/walkthrough.js` for the web page. Two versions of the same logic
drift apart; while this walkthrough was built, question flow and evaluation did exactly that and
cost 30 of 217 examples.

`scripts/check_parity.py` draws random answer patterns and runs both versions with them: the
same question in the same order, the same finding. The check run builds no package until 400 of
400 runs agree.

## Data status and sources

**Context:** where the legal text comes from | **Input:** official publications | **Output:** the dated corpus in both languages

| Source | Status | Size per language |
|---|---|---|
| Regulation (EU) 2024/1689 (AI Act) | Official Journal of 12 July 2024 | 1386 units |
| Regulation (EU) 2016/679 (GDPR) | Official Journal of 4 May 2016 | 1024 units |
| Federal Data Protection Act (BDSG) | Current version on gesetze-im-internet.de; English: the translation by the Language Service of the Federal Ministry of the Interior | 357 units |
| Draft Commission guidelines on the classification of high-risk AI systems | 19 May 2026 | Source of the question flow |

The official wording of both regulations is fetched in German and English through Cellar, the
data service of the Publications Office of the European Union, not from the EUR-Lex website,
which blocks automated access: `scripts/fetch_official_journal.py --language de|en`. The BDSG
comes from `scripts/fetch_bdsg.py --language de|en`. Only the German BDSG is legally binding;
the English translation is for information. `compliance-helper build-corpus --language de|en`
builds the corpus from these files, `compliance-helper build-index --language de|en` its search
index.

The draft guidelines are **not binding**. The tool states this caveat in every answer.

## Contributing

**Context:** how to propose a change | **Input:** a fix, a rule change or a report | **Output:** a change that passes the same checks as the continuous integration

Before every proposal:

```bash
scripts/check_all.sh         # what the GitHub checks run
scripts/check_all.sh --all   # plus container and presentation
```

The script runs the same commands as the checks on GitHub, in the same order; the container
test, which GitHub runs on Python 3.13, runs here with `--all`. Whoever checks only part of it
notices an error only there.

Errors and requests go to the issue tracker. There are three templates, and the choice matters:

* **Bug report**: something crashes or does not do what it says.
* **Feature request**: something is missing.
* **Legal error**: an article reference, a deadline, a classification or an obligation text is
  wrong. This is the most important route: a wrong reference affects everyone who uses the
  tool. These reports are handled before all others.

How a change to the rule set is reviewed, and what a legal error report must include, is in
[CONTRIBUTING.md](CONTRIBUTING.md). Do not report security vulnerabilities publicly; follow
[SECURITY.md](SECURITY.md).

## Further reading

**Context:** the detailed documentation | **Input:** none | **Output:** where to find what

| File | Content |
|---|---|
| [docs/architecture.md](docs/architecture.md) | The path of a question, component by component, with the limits of the system |
| [docs/operations-guide.md](docs/operations-guide.md) | Using, deploying and updating the legal data, and what to do when something fails |
| [docs/data-sources.md](docs/data-sources.md) | Every source with date, size and licence situation |
| [docs/security.md](docs/security.md) | Where data is stored, what leaves the device, protection against injected instructions |
| [docs/decisions.md](docs/decisions.md) | The architecture decisions with reasons and consequences |
| [docs/liability.md](docs/liability.md) | What the tool is not |
| [docs/presentation.en.html](docs/presentation.en.html) | The project as a slide deck (open in a browser) |
| [CHANGELOG.md](CHANGELOG.md) | Changes per version |

## License

**Context:** terms of use | **Input:** none | **Output:** licence of the code and of the bundled legal texts

Apache License 2.0, see [LICENSE](LICENSE). Copyright 2026 Daniel Hütte.

The licence of this work does not cover the bundled legal texts; for them, the legal position
of each source applies, see [NOTICE](NOTICE).
