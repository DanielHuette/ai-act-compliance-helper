# Operations guide

**English** | [Deutsch](operations-guide.de.md)

**Context:** three groups of readers, three parts — read the one that fits you | **Input:** this repository, a browser, and for parts b and c Python 3.11 or newer | **Output:** a running helper in the language you choose, and the commands to keep its data current

* [a) I only want to use it](#a-i-only-want-to-use-it)
* [b) I set it up in my organisation](#b-i-set-it-up-in-my-organisation)
* [c) I maintain the legal data and the questions](#c-i-maintain-the-legal-data-and-the-questions)
* [When something does not work](#when-something-does-not-work)

The legal acts: the **AI Act** (Regulation (EU) 2024/1689 on artificial intelligence (AI)), the
**General Data Protection Regulation** (GDPR, Regulation (EU) 2016/679) and the German **Federal
Data Protection Act** (Bundesdatenschutzgesetz, BDSG). Terms used below: the **question flow** is
the series of questions that decides the classification; the **corpus** is the legal text split into units (a paragraph of an article, a
point of an annex, a recital); the **search index** holds the vectors that make the corpus
searchable by meaning; the **rule set** derives obligations from a risk class.

---

## a) I only want to use it

**Context:** using the helper without setting anything up | **Input:** a browser or a downloaded package | **Output:** a classification with the exact place in the law

### In the browser — nothing to install

**Context:** the quickest way | **Input:** the public web page | **Output:** the walkthrough in German or English

<https://konformitaetshelfer.speedofthespirit.dev/>

You answer questions about your system and get the classification with the exact place in the law.
No sign-in, no account, no server: the page consists of `index.html`, two JavaScript files, the
question data and one text file per language. Your answers are computed in the browser and not
transmitted.

A walkthrough takes 5.3 steps on average. Every question has three answers: **Yes**, **No** and
**Don't know**. The third is not a convenience — choose it when a question does not fit your
system. Example: a tool that screens CVs does not publish job ads; to the question whether an ad
shows a specific vacancy there is neither a yes nor a no. In the measurement, a forced no knocked
exactly such cases out of the classification.

Each finding comes with the Commission's official examples for the same provision. Read them: if
your case resembles one of them, the classification is backed; if not, you see what it depends on.

### Switch the language

**Context:** every way to choose German or English | **Input:** a click, a command-line option, an environment variable or a request parameter | **Output:** text, questions and legal citations in the chosen language

German is the default everywhere. Legal citations follow the language: the English interface
quotes the English Official Journal text of the same unit.

| Where | How to switch | What decides when nothing is set |
|---|---|---|
| Web page (also under `/classification/` of the service) | **DE / EN** at the top right, or `?lang=en` in the address | the choice saved in this browser, then the browser language |
| Command line | `--lang en` or `--lang de` on any command | the environment variable `COMPLIANCE_HELPER_LANG`, then German |
| Service (`/search` and every `/api/` path) | `?lang=en` on any request; it sets the cookie `lang` for one year | the cookie `lang`, then the `Accept-Language` header of the browser (highest `q` first), then `COMPLIANCE_HELPER_LANG`, then German |
| Start scripts and the packaged app (console messages and the page it opens) | `COMPLIANCE_HELPER_LANG=en` | the language of the operating system |

`COMPLIANCE_HELPER_LANG` accepts codes such as `en`, `en-GB` or `EN`; any value that is not
English or German counts as German. Every service response carries a `Content-Language` header
with the language it was answered in.

### As a program on your own computer

**Context:** the packaged app, no Python needed | **Input:** the package for your operating system | **Output:** the interface in your browser, working offline

Download the package for your system from the
[releases page](https://github.com/DanielHuette/ai-act-compliance-helper/releases):

| System | File |
|---|---|
| Windows | installer `.exe`, or the `.zip` archive |
| Mac | disk image `ComplianceHelper-Mac.dmg` — drag the app into "Programme" (Applications) |
| Linux | archive `ComplianceHelper-Linux.tar.gz` — unpack, start `ComplianceHelper` |

Start it, done. The interface opens in the browser at an address between `http://127.0.0.1:8713`
and `:8799` — the program looks for a free port so it does not fail on one that is taken. No
Python, no environment, nothing downloaded later.

The package contains the legal corpus in both languages, the rule set, the question flow and the
use cases, so the classification runs at once and offline.

It also offers **full-text search in the legal text** at `/search`: a question in your own words,
and the tool shows the passages that answer it. In the package this search compares words only,
because the embedding model (about 2.3 gigabytes) and its libraries are left out. Search by
meaning needs the container or an installation from source with search (part b).

### From source

**Context:** running the code directly | **Input:** Python 3.11 or newer and this repository | **Output:** the service on your machine

```bash
git clone https://github.com/DanielHuette/ai-act-compliance-helper
cd ai-act-compliance-helper
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e .
python packaging/launch_app.py
```

Only the service, without a browser window opening:

```bash
compliance-helper serve --port 8000
```

The question flow is then at `http://127.0.0.1:8000/classification/` and the full-text search at
`http://127.0.0.1:8000/search`.

What the tool is working with and what is missing:

```bash
compliance-helper status              # German
compliance-helper status --lang en    # English
```

No colour in the output: `--no-color`, or set `NO_COLOR`. When the output goes to a file instead of
a terminal, colour switches off by itself. Notices for the user appear in the chosen language; the
developer log of the modules (English) only with `--verbose`.

Installed as a package instead (`pip install ai-act-compliance-helper-2.0.0-py3-none-any.whl`), the
tool brings the rules, the question flow, the use cases and both corpora along and finds them under
`<environment>/share/ai-act-compliance-helper/`; `compliance-helper classify` works at once. The
search indexes are not part of the package (28 megabytes, useless without the 2.3-gigabyte model),
so search runs on the fallback until `compliance-helper build-index` has built them. To work with
your own data, set `COMPLIANCE_HELPER_ROOT` to the folder that contains `data/`. Without rule files
the tool refuses with a message instead of classifying everything as minimal risk.

---

## b) I set it up in my organisation

**Context:** running the helper for others | **Input:** a server or container host, optionally an embedding model and keys for a language model | **Output:** the web page or the full service, operated safely

### Decide before you start

**Context:** four questions that shape the setup | **Input:** your requirements | **Output:** the setup you need

1. **Is the web page enough?** Nobody needs an installation for the classification. To offer it
   in-house, put the files from `web/` on any web server — that is all.
2. **Should users search the legal text?** Then you need the embedding model (about 2.3 gigabytes)
   and one search index per language.
3. **Should a language model word the answer?** Everything works without one, just more tersely.
   With one, the user's question goes to that model's provider — for a project involving business
   internals, that decision has consequences.
4. **Who keeps the data current?** The law changes. Without someone responsible, the tool goes
   stale without anyone noticing.

### Host the web page in-house

**Context:** the classification only, as static files | **Input:** the folder `web/` | **Output:** a page any web server can deliver

```bash
python scripts/export_question_flow.py --output web/question_flow.json
```

Afterwards `web/` holds everything: `index.html`, `page.js`, `walkthrough.js`,
`question_flow.json`, `locales/de.json`, `locales/en.json` and the images. These files need no
application server and no database. `web/_headers` holds the response headers the page should be
served with — Cloudflare Pages reads that file on its own, any other web server needs the same
settings in its own format.

### As a container — the shortest way to the full scope

**Context:** service, search and question flow in one image | **Input:** Docker with Compose | **Output:** the service at `http://127.0.0.1:8000/`

```bash
git clone https://github.com/DanielHuette/ai-act-compliance-helper.git
cd ai-act-compliance-helper
cp .env.example .env          # and fill in what you need
./scripts/start.sh            # Windows: scripts\start.ps1
```

The script checks the prerequisites and says what to do about each gap instead of passing on a
Docker error. It talks in English when `COMPLIANCE_HELPER_LANG` or the system language is English,
otherwise in German. Both spellings of each option work:

| Purpose | `start.sh` English | `start.sh` German | `start.ps1` | Alias in `start.ps1` |
|---|---|---|---|---|
| build without the large search model (fast, search compares words only) | `--small` | `--klein` | `-Small` | `-Klein` |
| rebuild without the build cache | `--refresh` | `--refresh` | `-Refresh` | `-Neu` |
| stop the service | `--stop` | `--stopp` | `-Stop` | `-Stopp` |
| show the help | `--help` | `--help` | `Get-Help .\scripts\start.ps1` | |

By hand: `docker compose up --build`. There are two images:

* **Full image** (default, `WITH_SEARCH_MODEL=1`): it includes the embedding model `BAAI/bge-m3`,
  so that the shipped search indexes also work offline, and the cross-encoder
  `BAAI/bge-reranker-v2-m3`, which purpose matching needs. Purpose matching is on, the slow
  reranking of search hits stays off (`COMPLIANCE_HELPER_RERANK` empty). The build needs about
  12 gigabytes of free disk space, the running service about 5 gigabytes of memory
  (`COMPLIANCE_HELPER_MEMORY`, default `6g`).
* **Small image** (`--small`, `WITH_SEARCH_MODEL=0`): no models. Search compares words only, and
  purpose matching is off (`COMPLIANCE_HELPER_RERANK=0`), so classification relies on the rule
  keywords alone; `/health` reports both as warnings and the status `degraded`. Good for trying
  things out and for the container tests, not for production.

**Rebuilding data for the container.** The image holds corpus and search indexes read-only under
`/app/data`, so rebuild them outside the running container and then the image. The commands are the
same as on a workstation (`compliance-helper build-corpus --language de|en`,
`compliance-helper build-index --language de|en`); run them in the source folder and then
`docker compose up --build`. Inside a container they only work on a writable copy:
`COMPLIANCE_HELPER_ROOT` points them to a folder that contains `data/`.

How the container is configured in `docker-compose.yml` and `Dockerfile`: the service runs as user
`app` (id 10001) without administrator rights, with a read-only file system, all capabilities
dropped, no new privileges, and bound to `127.0.0.1` only. The health check asks `/health` and
counts `not_ready` as unhealthy — a service whose corpus is missing still answers but is not fit
for work.

### Without a container, with search

**Context:** the full service on a workstation or server | **Input:** Python 3.11 or newer, about 2.3 gigabytes for the model | **Output:** both search indexes, ready to load

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[search]"                          # with search
# pip install -e ".[search,llm]"                    # plus Claude or GPT
compliance-helper build-index --language de  # German search index
compliance-helper build-index --language en  # English search index
```

Each language has its own search index, built from its own corpus; the interface queries the index
of the active language. Build the German one first — the English corpus takes over the German ids.
A run loads the model and embeds every unit once. A build from scratch takes more than an hour per
language on a processor without a graphics card (measured on 9 October 2026: 4,725 seconds for the
2,811 English units). It writes its log to `data/processed/_index_build.log` (English:
`_index_build.en.log`), saves a checkpoint every 64 units and finally logs the three best hits for a
probe question, so a broken index shows at once. Afterwards `data/processed/` holds
`search_index.vectors.npy`, `search_index.meta.json.gz` and `search_index.meta.json`, and the same
three files as `search_index.en.*` for English.

**The build is incremental.** A new run embeds only the units whose id or text changed; all others
it takes from the stored index of the same language and the same model. After a change to the use
cases it therefore takes minutes instead of an hour (measured on 9 October 2026: 44 changed units,
123 seconds). To embed everything again:

```bash
compliance-helper build-index --language de --from-scratch
compliance-helper build-index --language en --from-scratch
```

A small model for trying things out, if 2.3 gigabytes is too much:

```bash
compliance-helper build-index --language de --model intfloat/multilingual-e5-small
```

The search must then run with the same model — an index can only be queried with the model it was
built with. This is checked on load.

### Run the web service

**Context:** settings of the web service | **Input:** command-line options or environment variables | **Output:** a service listening where you want it

```bash
compliance-helper serve --address 127.0.0.1 --port 8000
```

The same settings, and more, come from environment variables (template: `.env.example`):

| Variable | Effect |
|---|---|
| `COMPLIANCE_HELPER_HOST`, `COMPLIANCE_HELPER_PORT` | where the service listens (default `127.0.0.1`, `8000`) |
| `COMPLIANCE_HELPER_MODEL` | which language model words the answer: `auto`, `anthropic`, `openai` or `none` |
| `COMPLIANCE_HELPER_EMBEDDING` | which embedding model the search uses if an index must be built in memory |
| `COMPLIANCE_HELPER_BUILD_INDEX` | `1` lets the service build a missing index at start with that model (takes hours without a graphics card) |
| `COMPLIANCE_HELPER_RERANK` | `1` lets the cross-encoder reorder the best 30 hits of a search (about 100 seconds per search without a graphics card); `0` also switches purpose matching off, which then shows as a notice in `/health`; empty (the default) leaves the search order as it is and purpose matching on |
| `COMPLIANCE_HELPER_LLM_TIMEOUT` | seconds a language model may take to word an answer (default 30, one retry); after that the answer comes from the rule set with a note |
| `COMPLIANCE_HELPER_REQUESTS_PER_MINUTE` | limit per client address for paths under `/api/` (default 30) |
| `COMPLIANCE_HELPER_CORS_ORIGINS` | comma-separated web origins allowed to call the interface |
| `COMPLIANCE_HELPER_LANG` | language of the command line, the start scripts and the packaged app; the service's default when a browser names neither German nor English |
| `COMPLIANCE_HELPER_MAX_BODY_BYTES` | largest request body the service reads (default 131072, that is 128 kibibytes); larger ones get 413 |
| `COMPLIANCE_HELPER_TRUSTED_PROXIES` | comma-separated addresses of reverse proxies whose `X-Forwarded-For` header the rate limit believes; unset, the header is ignored |
| `COMPLIANCE_HELPER_ROOT` | folder that contains `data/` (and `web/`), for your own rule set or a writable copy for the data builds |
| `HF_HOME`, `HF_HUB_OFFLINE` | model cache directory; `1` forbids model downloads |

**By default the service listens only on `127.0.0.1`**, that is, on the machine itself. If you offer
it in-house:

* The service has **no sign-in**. Whoever reaches it can use it. Access control belongs in front of
  it — a reverse proxy or the network itself.
* There is a limit per address against overload, but no user management and no billing.
* The service should **not run as administrator**. `compliance-helper status` warns if it does.
* `GET /health` serves as a probe for monitoring and is not rate-limited.
* The service describes its interfaces itself at `/openapi.json`: `/api/classify`, `/api/search`,
  `/api/ask`, `/api/questionnaire`, `/api/deadlines`.

The service loads corpus, search index and rule set of both languages into memory at start. The
first start therefore takes longer than the first answer after it.

### Set keys if a language model should word the answer

**Context:** optional wording by Claude or GPT | **Input:** an application programming interface (API) key of the provider | **Output:** answers worded by the model; the classification stays unchanged

```bash
export ANTHROPIC_API_KEY="…"     # for Claude
export OPENAI_API_KEY="…"        # for GPT
```

With `COMPLIANCE_HELPER_MODEL=auto` the service tries Claude, then GPT. If neither is reachable,
the answer is built from the rule set and says so in a note. The classification itself always
comes from the question flow; a language model cannot change it.

Do not put keys into a file inside the repository. `.gitignore` keeps `.env` out, but a key in a
file is a key that one day travels along by mistake.

### Build the packages yourself

**Context:** the installable packages for Windows, Mac and Linux | **Input:** a tag or a manual run on GitHub | **Output:** packages attached to the release

The workflow `.github/workflows/packages.yml` ("Build packages") builds on three machines —
Windows, Mac and Linux. A package contains the runtime of the system it was built on; there is no
Windows program built on Linux.

* Push a tag starting with `v` (for example `v2.0.0`); the workflow builds and attaches the
  packages to the release.
* Or start the workflow by hand; the packages are then stored as artifacts of the run.

The workflow first regenerates the question flow, then compares the browser and the Python
implementation with 400 answer patterns, and only then builds. Reason: if program and web page
drift apart, the same case gets two answers. After the build, `packaging/launch_check.py` starts
the package and checks that it answers and serves the question flow — otherwise the first user
would notice.

Locally:

```bash
pip install pyinstaller
python scripts/export_question_flow.py --output web/question_flow.json
python scripts/check_parity.py --runs 400
python -m PyInstaller packaging/compliance_helper.spec --noconfirm
python packaging/launch_check.py
```

`scripts/check_parity.py` needs Node.js, because it runs the browser implementation.

### What to tell your users

**Context:** the limits users must know | **Input:** the scope of the tool | **Output:** three statements to pass on

That it is not legal advice. That the classification is only as good as the answers — whoever does
not know what their system is intended for has to clarify that first. And that the list of
obligations errs on the long side: it contains every obligation of the class and role found, also
some that may not fit the individual project. See
[architecture.md, "Limits of the system"](architecture.md#limits-of-the-system) and
[liability.md](liability.md).

---

## c) I maintain the legal data and the questions

**Context:** keeping the three data sets current | **Input:** new guidelines, a new legal text or new rules | **Output:** updated files that pass every check

Three things go stale, and they are maintained separately:

1. **The question flow** — the questions, exclusions and examples from the Commission guidelines,
   in `data/rules/question_flow/` together with `data/rules/question_flow_layout.yaml`. It goes
   stale when the Commission changes its guidelines — and the draft of 19 May 2026 will still get a
   final version.
2. **The legal text** — the wording of the regulations and the German act. It is fetched into
   `data/raw` (English: `data/raw/en`) and built into `data/processed/corpus.jsonl` and
   `corpus.en.jsonl`.
3. **The rule set** — the 57 obligations and the 26 sections of the data protection path in
   `data/rules`. It does not go stale with a new text version, but with new legal acts and case
   law.

### Change or add a question

**Context:** editing the question flow | **Input:** a question file in `data/rules/question_flow/` | **Output:** a question flow that the browser and Python compute identically

A question belongs in the file of its area. Required:

* `question` — with `de` and `en`: a sentence someone can answer about their own organisation. No
  quotation from the law.
* `on_yes` and `on_no` — `covered`, `not_covered` or `continue`.
* `source_ref` — the paragraph number of the guidelines, such as `"(254)"`. **No paragraph, no
  question.** A question without a source is an invented question, and that is exactly what must
  not exist here.

Order and gates are set separately in `data/rules/question_flow_layout.yaml`. That file also states
which question only informs (`kind: note`) and which steers the path (`kind: gate`).

After every change — in this order:

```bash
python -c "
from compliance_helper.classification.question_flow import Walkthrough
print(Walkthrough.load().figures())
"
python scripts/export_question_flow.py --output web/question_flow.json
python scripts/check_parity.py --runs 400
```

Expected, measured on 9 October 2026: 3 preliminary questions, 4 notes, 31 provisions,
379 questions, 214 exclusions, 187 examples. And `400 of 400 runs identical.`

**The last command matters most.** The walkthrough logic exists twice — in
`src/compliance_helper/classification/question_flow.py` and in `web/walkthrough.js`. While this
walkthrough was built, the two drifted apart and cost correct classifications of official examples.
Whoever touches one touches the other and measures again.

Then measure against the official examples as described in
[../data/evaluation/MEASUREMENT.md](../data/evaluation/MEASUREMENT.md).
`scripts/answer_questions.py --answers <file>` prints the next open questions, and with `--result`
the finding.

### Fetch and build both corpora

**Context:** renewing the legal text in German and English | **Input:** network access to Cellar and gesetze-im-internet.de | **Output:** `corpus.jsonl` and `corpus.en.jsonl` with the same ids

**German first.** The English corpus takes over the ids of the German one, so it can only be built
after it.

```bash
python scripts/fetch_official_journal.py      # AI Act and GDPR, German Official Journal text
python scripts/fetch_bdsg.py                  # Federal Data Protection Act
compliance-helper build-corpus --language de --check
compliance-helper build-corpus --language de
```

```bash
python scripts/fetch_official_journal.py --language en
python scripts/fetch_bdsg.py --language en    # official English translation
compliance-helper build-corpus --language en --check
compliance-helper build-corpus --language en
```

The fetch scripts skip files that are already there; `--refresh` fetches them again. `--check`
builds and reports without writing anything.

Then read `data/processed/corpus_report.json` (English: `corpus_report.en.json`). It lists the
counts per source and the warnings of the run. **The runs of 9 October 2026 have no warning.** If
one appears, read it rather than skip it:

| Warning | Meaning |
|---|---|
| `ATTENTION: n duplicate ids WITH DIFFERING TEXT — content is lost here: …` | the parser found the same id twice with different text; legal text disappears |
| `OFFICIAL FULL TEXT MISSING: …` | the Official Journal file is missing or too small; the build fell back to an incomplete secondary source |
| `IDS DIFFER FROM THE GERMAN CORPUS: …` | the English build does not match the German ids; citations would point to different units |
| `BDSG MISSING: …` | the Federal Data Protection Act file is missing |

Check that the counts meet the expectations: the AI Act has 113 articles, 13 annexes and 180
recitals, the General Data Protection Regulation 99 articles and 173 recitals; together 2,811 units
per language. These numbers are expectations in `src/compliance_helper/corpus/eurlex.py` and in
`tests/test_corpus.py`; a deviating run shows a warning in the report and fails the tests.

**After every corpus build, rebuild the search indexes**, otherwise the vectors no longer match the
text. German first, then English; only changed units are embedded again:

```bash
compliance-helper build-index --language de
compliance-helper build-index --language en
```

### Change the rule set

**Context:** editing obligations and the data protection path | **Input:** `data/rules/ai_act_obligations.yaml`, `gdpr_review_path.yaml`, `ai_act_risk_classes.yaml` | **Output:** rules whose every legal basis exists in the corpus

Each file carries `as_of` in its header, and the obligations and data protection files also a
`version_note`. **Change both together** — the date appears in every answer, and a wrong date is
worse than an old one.

An obligation in `data/rules/ai_act_obligations.yaml` has these fields:

* `id` — unique, never changed afterwards, because other data refers to it
* `title` — one sentence in plain language (`de` and `en`), not a quotation from the law
* `risk_classes` and `roles` — who must fulfil it when
* `legal_basis` — corpus ids such as `AI-Act/art-26/para-1`, **which must exist in the corpus**
* `citation_text` — the citation as it appears in the answer
* `applies_from` — the date of application under Article 113
* `action_required`, `evidence_of_compliance`, `on_infringement`, `severity`

After a change, check that the files load and the counts are right:

```bash
python -c "
from compliance_helper.classification.assessor import rule_set
rules = rule_set()
print('as of:', rules.as_of)
print('obligations:', len(rules.obligations))
print('data protection sections:', len(rules.data_protection))
print('deadline stages:', len(rules.deadlines))
"
```

Expected, measured on 9 October 2026: as of 2026-05-31, 57 obligations, 26 sections, 5 deadline
stages.

And check that every legal basis exists in the corpus:

```bash
python -m pytest tests/test_classification.py -q -k "rule_citation_exists_in_corpus or every_obligation_cites"
```

An obligation whose legal basis is missing from the corpus appears in the answer without the
wording of its source. That is no crash, but a defect. The same holds for the `citation` of a
question: if it points nowhere, the finding lacks the official text to read.

Every change belongs in [CHANGELOG.md](../CHANGELOG.md).

### What usually changes

**Context:** where updates are to be expected | **Input:** developments in the law | **Output:** the files to revisit

* **The guidelines.** The draft of 19 May 2026 is not binding, and the consultation ran until
  23 June 2026. When the final version arrives, the paragraph numbers must be rechecked — every
  question carries one.
* **Deadlines.** Article 113 sets the dates of application. The caveat about them is in the rule
  set, because individual dates were under political discussion at the time of the data version.
* **Annex III.** The Commission can amend the list of high-risk areas by delegated acts. Then the
  question files **and** `data/rules/ai_act_risk_classes.yaml` change.
* **Federal Data Protection Act.** The rule set cites only Parts 1 and 2, the provisions
  implementing the GDPR. Part 3 applies under section 45 only to authorities in criminal
  prosecution and is deliberately not drawn on.

---

## When something does not work

**Context:** symptoms and their fixes, with the messages as the program prints them | **Input:** an error message or a wrong behaviour | **Output:** the cause and the command that fixes it

### The web page shows "The questions could not be loaded"

**Context:** the question data is missing next to the page | **Input:** `web/question_flow.json` | **Output:** a page that loads its questions

`question_flow.json` is missing next to `index.html` or is incomplete. Regenerate it:

```bash
python scripts/export_question_flow.py --output web/question_flow.json
```

The page loads the file with `fetch("./question_flow.json")`, from the same folder. If
`index.html` is opened as a file from disk instead of through a web server, some browsers refuse
this request. Then use any small web server in the folder `web/`:

```bash
python -m http.server 8080 --directory web
```

### The interface shows the wrong language

**Context:** a language choice that sticks | **Input:** the address, the cookie or the browser setting | **Output:** the language you want

The web page remembers the last choice in the browser, the service in the cookie `lang`. Append
`?lang=en` or `?lang=de` to the address once; both then remember the new choice. On the command
line, `--lang` beats `COMPLIANCE_HELPER_LANG`.

### Web page and program classify the same case differently

**Context:** the two implementations of the walkthrough disagree | **Input:** the answers that led to both results | **Output:** the first step where they part

That is a bug and should be reported — with the answers that led to both results. Measure:

```bash
python scripts/check_parity.py --runs 400
```

For each differing run the script prints `--- Run n: Python and browser differ ---` and the first
step where they part. Most common cause: `web/question_flow.json` is older than the question files in `data/rules/`.
Regenerate it first, then compare.

### The finding says "Conditionally high risk"

**Context:** a finding that is not a bug | **Input:** a system under Annex III point 2 | **Output:** the reason for the conditional finding

Not a bug. It means: everything applies except one condition you cannot know. For Annex III
point 2, paragraph (190) of the guidelines requires that a Member State has formally designated the
deployer as a critical entity — and paragraph (191) states that this designation need not be
disclosed to the provider. If such a deployer may be among your customers, the obligations for
high-risk AI systems apply.

### The service does not start: "address already in use"

**Context:** the port is taken | **Input:** the port number | **Output:** a free port

Another program listens on the port. Choose another one (`--port 8001`) or look at what listens
there:

```bash
ss -tlnp | grep 8000
```

The packaged program finds a free port between 8713 and 8799 by itself.

### "bge-m3 requires the FlagEmbedding package"

**Context:** the embedding model is not installed | **Input:** the Python environment | **Output:** a working search model, or a deliberate choice to do without

The full message ends with `Install it with: pip install 'ai-act-compliance-helper[search]'`.
Either install it:

```bash
pip install -e ".[search]"
```

or work with the small model (`--model intfloat/multilingual-e5-small`), or do without search —
the classification needs no model.

`compliance-helper build-index` stops with `The embedding model BAAI/bge-m3 is not available. A
search index of fallback quality is not written.` and writes nothing. That is deliberate: an index of fallback quality
looks intact and silently returns wrong hits. To try the mechanics without a model, use
`--fallback`; that index is not fit for production.

### "The search index was built with X, but Y is loaded"

**Context:** index and model do not belong together | **Input:** the model name stored in the index | **Output:** a matching model or a rebuilt index

Embeddings of different models are not comparable — each model computes its own vectors. Either
load the same model or rebuild the index:

```bash
compliance-helper build-index --language de --model <the model of the index>
```

### "Search index and corpus do not match" or "The stored search index belongs to a different corpus"

**Context:** the corpus was rebuilt after the index | **Input:** the language the message names | **Output:** an index that matches its corpus again

This is the check that prevents silent damage: without it every vector would point to the wrong
provision, and the answer would look as usual. The service reports it as `The stored search index
(English) is missing or does not match the corpus and was not used (…). Rebuild it: …` and names the
command for that language:

```bash
compliance-helper build-index --language de  # German
compliance-helper build-index --language en  # English
```

The run embeds only changed units and saves a checkpoint every 64 units. If it aborts — below
8 gigabytes of memory that can happen — simply start it again: it skips what is already computed
and logs how many units it reused.

### "The English search index is missing" or "The search index was built for language de, but en was requested"

**Context:** the index of the requested language is absent or swapped | **Input:** the language of the request | **Output:** an index for that language

Each language needs its own index file set: `search_index.*` for German, `search_index.en.*` for
English. Build the missing one with the command the message names, for English:

```bash
compliance-helper build-index --language en
```

### "No LLM is reachable" or "ANTHROPIC_API_KEY is not set"

**Context:** no language model is available | **Input:** the keys in the environment | **Output:** answers from the rule set, or a key for a model

Not a bug, a statement. Without a key everything keeps working; the answer comes straight from the
rule set and carries the note "This answer was produced without a language model and is therefore
worded more briefly." To set a key, see part b. To silence the note, set
`COMPLIANCE_HELPER_MODEL=none`.

### "Too many requests from this address"

**Context:** the rate limit applies | **Input:** the number of requests per minute | **Output:** an answer after the wait, or a higher limit

The service allows 30 requests per minute and address under `/api/` by default and returns Hypertext Transfer Protocol (HTTP)
status 429 with a `Retry-After` header. Raise the limit with
`COMPLIANCE_HELPER_REQUESTS_PER_MINUTE`.

### "The corpus is missing. Build it first"

**Context:** the legal text has not been built | **Input:** `data/processed/` | **Output:** a corpus to load

Build it as described in part c, German first. On the command line the message reads `A file is
missing: The corpus is missing (German): <path>. Build it first: compliance-helper build-corpus
--language de`; for English it names `--language en`.

### EUR-Lex delivers only a few kilobytes

**Context:** the wrong address was queried | **Input:** the fetch script | **Output:** the full Official Journal text

The **website** of EUR-Lex answers without complete browser headers with HTTP status 202 and zero
bytes and then serves a firewall captcha. No waiting and no header helps against that.

The official text therefore comes not from the website but from the repository **Cellar**, which
has no such firewall:

```bash
python scripts/fetch_official_journal.py
```

The script fetches both regulations via
`http://publications.europa.eu/resource/cellar/<id>` with `Accept: application/xhtml+xml` and
`Accept-Language: deu` (`eng` with `--language en`) and discards any response below the minimum
size with `attempt n: only … bytes, expected at least … — discarded`. The ids are listed in
[data-sources.md](data-sources.md).

### The test run is cut off in the middle ("Killed")

**Context:** too little memory | **Input:** the test suite | **Output:** a complete test run

Several tests load both corpora and build search indexes in memory; below 8 gigabytes the whole
suite may not get through in one run. Then test file by file:

```bash
for f in tests/test_*.py; do python3 -m pytest "$f" -q; done
```

### ruff or mypy report something

**Context:** the static checks fail | **Input:** the code | **Output:** a clean run

Then something needs fixing. `ruff check .`, `ruff format --check .` and `mypy src` are meant to pass
without findings, and the GitHub checks fail on any finding. A run that is permanently red is no
longer read — and then the first real bug goes unnoticed too. Every exception is justified in
`pyproject.toml`.

Everything at once, with the same commands and in the same order as the checks on GitHub (the
container test only with `--all`):

```bash
scripts/check_all.sh
scripts/check_all.sh --all   # plus container and presentation
```

### The service answers, but search finds nothing useful

**Context:** search runs without a real model | **Input:** `compliance-helper status` | **Output:** search by meaning again

Look at `compliance-helper status`. If the search index section shows the embedding model
`hashing-fallback`, no stored index was loaded; the warning reads `Search runs on the fallback model
'hashing-fallback'. It compares words only, not meaning — the passages found are noticeably
worse.` Fix:

```bash
pip install -e ".[search]"
compliance-helper build-index --language de
compliance-helper build-index --language en
```

The classification is not affected — it needs no search index.
