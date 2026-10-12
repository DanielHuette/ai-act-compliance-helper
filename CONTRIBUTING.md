# Contributing

**English** | [Deutsch](CONTRIBUTING.de.md)

**Context:** how to report problems and propose changes | **Input:** a bug, a wrong legal statement, a request or a code change | **Output:** the right route and the conditions a change must meet

Thank you for taking the time. This guide says where each kind of report goes and what a change
must meet to be accepted.

One rule first: **legal errors are treated differently from program errors.** A program error
annoys whoever runs into it. A wrong article reference goes into an answer on which someone
bases a decision. It therefore has its own route, its own template and priority over everything
else. See [Legal errors](#legal-errors).

## Which route do I take?

**Context:** choosing the template | **Input:** your situation | **Output:** the matching route

| Your situation | Route |
|---|---|
| An article reference, a deadline, a classification or an obligation text is wrong | Template **Legal error** (`legal_error.yml`) |
| Something crashes or does not do what it says | Template **Bug report** (`bug_report.yml`) |
| Something is missing | Template **Feature request** (`feature_request.yml`) |
| A security vulnerability | **Not in public.** Follow [SECURITY.md](SECURITY.md) |
| A question about how something works | Discussions, or a bug report if the documentation should have answered it |

## Legal errors

**Context:** reports about wrong legal content | **Input:** what the tool says, what is right, and the provision behind it | **Output:** a correction, a warning or a documented open question

### Why a separate route

The tool classifies projects using artificial intelligence (AI) under the law. If a reference is wrong, the answer is wrong,
for everyone who uses the tool, not only for the person who noticed. Therefore:

* Legal errors are handled **before** all other reports.
* A report is not closed because it is old.
* If the error cannot be fixed at once, a warning goes into the affected record first, then the
  correction.

### What the report must contain

The template asks for it; here is the reason for each item:

1. **What the tool says.** The answers or description that led to the result, and the output,
   preferably as text. Without the input the error cannot be reproduced, because the
   classification depends on it.
2. **What would be right.** Not only "this is wrong", but the correct statement.
3. **The provision you rely on.** Article, paragraph, point, letter. For Regulation (EU)
   2024/1689 (Artificial Intelligence Act, AI Act), please use the Official Journal of 12 July
   2024 or a later corrected version, and say which one. For national law, the section and the
   act.
4. **Where your provision comes from.** Official Journal, Federal Law Gazette, a court decision
   with case number, a guideline with date. A blog post is not enough, because no correction can
   be based on it.
5. **Which file is affected**, if you know: `ai_act_obligations.yaml`, `ai_act_risk_classes.yaml`,
   `gdpr_review_path.yaml`, a question flow file under `data/rules/question_flow/`, a case file
   under `data/cases/`, or the legal corpus itself.

### Four kinds of legal errors and what happens to them

* **Wrong reference** (the obligation is in Article 27, not 26). Corrected as soon as the
  provision is confirmed. This is the simplest case.
* **Wrong deadline.** Corrected. The `as_of` date in the file is updated and the caveat checked.
* **Wrong obligation content** (the obligation requires something else). Needs the provision's
  wording, because the text in `action_required` is a summary and is measured against it.
* **Wrong classification** (the system does not fall under Annex III, or it does). The hardest
  case, because it contains a legal assessment. If the legal position is disputed, the
  classification is not simply reversed. The affected rule gets a note on the dispute and a
  lower confidence (`needs_review` instead of `likely`), and the open question is added.
  Presenting a disputed question as settled would be the bigger error.

### What does not count as a legal error

* **"The list is too long."** This is known and described: obligations are selected by class
  and role, not by the traits of the project. See [docs/architecture.md](docs/architecture.md),
  section on the limits of the system. A request for a finer selection is welcome, as a feature
  request.
* **"This is not legal advice."** Correct, and it says so. See
  [docs/liability.md](docs/liability.md).
* **A different view without a provision.** Legal views differ; the rule set follows the wording
  and says where it is uncertain. Without a provision nothing can be changed.

## Changes to the rule set

**Context:** editing the files under `data/rules/` | **Input:** a confirmed legal change or correction | **Output:** a consistent rule set in both languages, re-exported and re-measured

The rule set lives in `data/rules/*.yaml` and `data/rules/question_flow/*.yaml`. Whoever changes
it:

1. **Updates the date.** Each rule file has an `as_of` field in its header, most also a
   `version_note`. The date appears in every answer; a wrong date is worse than an old one.
2. **Keeps ids stable.** The `id` of an obligation, section or question is referenced from cases,
   evaluation data and the web page. An obligation whose content becomes something else gets a
   new id.
3. **Gives legal bases as citation ids**, such as `AI-Act/art-26/para-1`, `GDPR/art-35` or
   `BDSG/sec-26`. They must exist in the corpus, otherwise the obligation appears without its
   wording. `scripts/check_rule_set.py`, a step of `.github/workflows/checks.yml`, checks
   this.
4. **Writes both languages.** Every user-facing text is a pair `{de: ..., en: ...}`. Both sides
   say the same thing.
5. **Writes in plain language.** A `title` is a sentence, not a quotation of the law.
   `action_required` says what to do, not what the law says. Explain every technical term on
   first use and write out every abbreviation.
6. **Measures the figures, does not remember them:**

```bash
PYTHONPATH=src python -c "
from compliance_helper.classification.assessor import rule_set
rules = rule_set()
print('as of:', rules.as_of, '| obligations:', len(rules.obligations),
      '| data protection sections:', len(rules.data_protection))
"
```

7. **Re-exports the question flow** after a change under `data/rules/question_flow/` or to
   `question_flow_layout.yaml`, so that web page and program read the same data, and checks
   that both still agree:

```bash
python scripts/export_question_flow.py --output web/question_flow.json
python scripts/check_parity.py --runs 400
```

8. **Adds an entry to [CHANGELOG.md](CHANGELOG.md)** under "Unreleased". A change to the rule set
   matters more to users than any program change.

## Changes to the program

**Context:** code, tests and the web page | **Input:** a fix or a feature | **Output:** a change that passes every check of the continuous integration

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --constraint constraints.txt -e ".[dev]"
```

### What must pass

The same as `.github/workflows/checks.yml`, or in one go `scripts/check_all.sh`:

```bash
ruff check .
ruff format --check .
mypy src
bandit -c pyproject.toml -r src scripts packaging
pip-audit --disable-pip --no-deps --requirement constraints.txt
pytest -m "not slow and not network and not container"
python scripts/check_parity.py --runs 400
python scripts/check_rule_set.py
```

Every one of these steps fails the run, and none reports anything today. Bring in no new
finding. `bandit` runs without global exceptions; the few `# nosec` markers each name their rule
at the call site.

Three test markers are defined: `slow` for tests that need the local models, `network` for tests
that need network access, and `container` for tests that build a Docker image. `slow` and
`network` never run in the checks, which download no model. Whoever writes a test that needs a
model marks it with `@pytest.mark.slow`.

After a change to `web/index.html`, `web/page.js` or `web/locales/*.json`, run
`python scripts/check_web_locales.py`.

### What a change must meet

* **English in code, both languages for users.** Identifiers, comments and developer messages
  are English. Every text a user reads exists in German and English, in
  `src/compliance_helper/locales/` and `web/locales/` or as a `{de, en}` pair in the data.
* **The module docstring states context, input and output.** Whoever creates a file writes it;
  whoever changes a decision updates it.
* **Explain technical terms.** On first use, in plain language, every abbreviation written out.
  This applies to code and documentation alike.
* **No invented figure.** Every count in documentation or comments is measured: count the lines,
  open the file, do not estimate, do not remember.
* **What is not checked is marked as not checked.** An assumption is written as an assumption.
* **Classification and phrasing stay separate.** A change after which a language model decides
  the risk class or an obligation is not accepted, not as a fallback, not behind a switch. This
  is the founding decision of the project, see [docs/architecture.md](docs/architecture.md),
  section "Wording by a language model, and its limits".
* **No diagnostic displays in the finished tool.** What the tool can do must be visible from
  the result. Operational messages belong in the log, not in the answer.

## Submitting a pull request

**Context:** the proposal itself | **Input:** your branch | **Output:** a reviewable pull request

* One proposal, one topic. A proposal that changes the rule set **and** restructures code cannot
  be reviewed.
* The description says which issue it resolves and how to verify it.
* Renaming, reordering, reformatting and tidying without effect are not accepted. Whoever
  improves something improves the substance.
* By submitting, you license your contribution under the Apache License 2.0 (section 5 of the
  licence text). No additional agreement is needed.
* Whoever contributes more than a small fix may add themselves to [AUTHORS.md](AUTHORS.md).

## Tone

**Context:** how we work together | **Input:** none | **Output:** the applicable rules

The [Code of Conduct](CODE_OF_CONDUCT.md) applies. In short: stay factual, even when someone
says something wrong, especially on legal questions, where views differ and that is not the
person's fault.
