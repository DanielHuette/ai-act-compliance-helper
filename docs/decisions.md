# Architecture decisions

**English** | [Deutsch](decisions.de.md)

**Context:** the decisions that shape the project, with what they cost | **Input:** measurements on the official examples, the company questions and the build logs | **Output:** one entry per decision: context, decision, consequences

The project classifies artificial intelligence (AI) systems under Regulation (EU) 2024/1689 of
the European Union (EU) laying down harmonised rules on artificial intelligence (AI Act), and covers
the General Data Protection Regulation (GDPR) and the German Federal Data Protection Act
(Bundesdatenschutzgesetz, BDSG).

Entries are ordered by weight, not by date. An entry that no longer holds is not deleted but marked
as superseded and linked to the entry that replaces it. Entry numbers match the German version
(D1 here is E1 there).

## D1 — Ask instead of guessing

**Context:** a risk class can be guessed from a description or asked for | **Input:** keyword and similarity measurements of earlier versions, 217 official examples | **Output:** the question flow decides; the free-text route stays as a second way in

**Context.** The task is to determine the risk class and the obligations of an AI system. The
obvious way is to let the user describe the project and infer the rest. The project was built that
way, in two stages. Keyword lists classified all 44 of the project's own use cases correctly, but
only 14 of 20 descriptions as companies actually write them: a list only hits what someone wrote
down beforehand. Comparison by meaning (purpose sentences, an embedding model and a cross-encoder)
later reached 98 of 100 company questions.

**Decision.** The classification on the start page comes from a question flow: the user answers
questions about the system, and the finding follows. Measured: 5.3 steps per case on average. The
free-text route (`classification/assessor.py`) remains for the command line, the JavaScript Object Notation (JSON) interface
and the search page, where a description is all there is; it marks every result with a confidence
and lists what it could not tell.

98 of 100 sounds good and is the wrong yardstick. A lawyer asks five to eight things and is then
certain, not 98 percent sure. Accurate guessing is worse than asking, and what was being guessed
were answers to questions that can simply be asked: what is the system intended for, who uses it,
does it decide about people? The user knows that, and nobody else does. Three more things the
guessing route could not deliver:

* **Traceability.** Guessing ended with a class and a similarity score. Now the finding names the
  answer that carried the provision and the guideline paragraph that says so. The user sees what it
  depends on and can change the answer.
* **Provenance.** The purpose sentences of the catalog were written by the author; every gap in
  them was a gap nobody could see. The questions come line by line from the Commission's draft
  guidelines of 19 May 2026 and each carries a paragraph number.
* **An outside yardstick.** Before, the author wrote both the rules and the test cases, so a high
  hit rate only meant agreement with the author's reading. The 217 examples of the guidelines carry
  the Commission's verdict. **207** of them are classified correctly.

**Consequences.**
* Good: the result is not probable but correct, as far as the user's answers are correct. No model
  can change it.
* Good: the question flow needs no language model, no embedding model, no network and no key. It
  runs in the browser.
* Bad: the user has to answer. Whoever does not know what the system is intended for must find out
  first; the tool cannot do that for them.
* Bad: maintenance gets harder. If the guidelines change a paragraph, a question changes, and it
  must be checked in two places (see
  [D3](#d3--the-flow-logic-exists-twice-and-is-measured-against-itself)).
* There are two ways to a classification, and they can disagree. The question flow is the measured
  reference; the free-text route is labelled with its confidence.

## D2 — The questions live in text files, with a paragraph number on every line

**Context:** 379 questions, 214 exclusions and 187 examples rest on a draft that will change | **Input:** the draft guidelines (167 pages), the public consultation until 23 June 2026 | **Output:** `data/rules/question_flow/*.yaml` and `question_flow_layout.yaml`, no question in the code

**Context.** The questions on 31 provisions rest on a 167-page document that is not binding and
will still change: the public consultation on the draft ran until 23 June 2026.

**Decision.** All of it lives in `data/rules/question_flow/*.yaml`, the order separately in
`data/rules/question_flow_layout.yaml`. Every question, exclusion and example carries the guideline
paragraph number in the field `source_ref`. The code contains no question and no article reference
of its own.

Whoever changes a question should change a line of text, not code. That is feasible for someone who
knows the law but does not program, which is exactly the person who notices a change in the
guidelines first. A text file is also readable in version control: a changed question shows up as a
difference and can be reviewed. The paragraph number is not decoration; it answers "how do you know
that?". Without it every question would be an assertion. Hence: **no paragraph, no question.**

Order is kept apart from content because they have different origins: the question comes from the
official text, the order from experience with how people answer. The eight area questions show it:
they carry no paragraph number because they only sort.

**Consequences.**
* Good: a change in the guidelines changes files, not code.
* Good: the same files feed the program and the web page, so both classify alike.
* Good: every text is a bilingual value (`{de, en}`) in the same file, so a question cannot exist
  in one language only.
* Bad: the files have no schema check. A typo in a field name does not stop the build; it produces
  a question without that field. A schema check would be the next sensible step.
* The link between question and legal text is a string: a provision names
  `AI-Act/annex-III/pt-4-a` as its citation. If that id were missing from the corpus, the finding
  would lack the official text to read. `tests/test_question_flow.py` checks that every provision
  points to a corpus unit.

## D3 — The flow logic exists twice and is measured against itself

**Context:** the classification must run in the browser without installation, and in the installed program alike | **Input:** a drift that cost 30 of 217 official examples | **Output:** `question_flow.py` and `walkthrough.js`, checked by `scripts/check_parity.py`

**Context.** The data is the same on both sides, but the flow logic has to exist in two programming
languages: Python for the program, JavaScript for the web page. The alternative would be a web page
that asks a server.

**Decision.** Two copies, `src/compliance_helper/classification/question_flow.py` and
`web/walkthrough.js`, and a check that drives them against each other. `scripts/check_parity.py`
draws answer patterns from a fixed seed and compares step by step: the same question in the same
order, the same group on the same page, the same finding. The packaging workflow builds nothing
until 400 of 400 runs agree.

A web page that asks a server transmits the user's answers. A description of an AI project reveals
business internals, and a page without a server has no operator one has to trust. So the browser
computes. The price is the doubled logic, the most dangerous spot of the project. **Two copies of
the same logic drift apart**: while this walkthrough was built, question order and evaluation did
exactly that and **cost 30 of 217 official examples**. Such a drift is invisible; both sides answer,
just differently. That is why the check is part of the package build, not optional.

**Consequences.**
* Good: the classification runs without server, login or transmission.
* Good: the web page is a handful of static files and can go on any web server.
* Bad: every change to one copy is a change to two. Whoever touches only one breaks parity; the
  check notices, but the work is done twice.
* The 400 runs are a set number, not a measured one: no series shows from which number on a drift
  reliably shows up.

## D4 — Three answers, not two

**Context:** yes/no looks like the simplest flow, and every guideline question seems answerable that way | **Input:** a measured CV-screening case, ten examples on Annex III point 2 | **Output:** the answer "Don't know" and the finding `high_risk_conditional`

**Context.** A flow with yes and no is the simplest form, and every question of the guidelines is
phrased as if it could be answered with yes or no.

**Decision.** Every question has three answers: Yes, No and **Don't know**. The third leaves the
question standing without deciding it; an exclusion only fires on an explicit answer.

Measured on one case: Annex III point 4(a) comes with the question whether a job advertisement
actively shows a specific vacancy. A tool that screens curricula vitae (CVs) places no advertisements; there is
neither a yes nor a no. The forced "no" threw out a case the official text clearly covers. A lawyer
would not press the point.

A second case required its own finding. Annex III point 2 requires, per paragraph (190) of the
guidelines, that the deployer is formally designated as a critical entity, and paragraph (191)
states in the same breath that this designation need not be disclosed to the provider. A software
company selling grid control systems cannot answer the question. Measured, **ten official examples**
fell to "not high risk" that the Commission lists as high-risk. If that question stays open and the
rest applies, the finding is `high_risk_conditional`, with the sentence that says what it depends
on.

**Consequences.**
* Good: questions that do not fit the user's system do not throw it out of the classification.
* Good: the finding can say "everything applies except one thing, and that you cannot know", which
  matches the situation.
* Bad: three answers are more to handle than two, in the interface and in both copies of the logic.
* Bad: whoever picks "Don't know" out of convenience gets an undecided finding instead of a
  classification. The tool cannot tell whether the question really does not fit.

## D5 — Annex III and Annex I are checked differently

**Context:** two routes to high risk with different structures | **Input:** Article 6(1) and 6(2), Annex III point 2, measured losses | **Output:** three check forms in `question_flow_layout.yaml`

**Context.** Article 6(2) with Annex III applies when **one** of eight areas fits. Article 6(1) with
Annex I requires **three** things together. And within Annex III, point 2 is built differently from
the other seven areas: there, too, three things must come together.

**Decision.** Three check forms, kept apart in `question_flow_layout.yaml`:

* **Enumeration**: the points of an area apply individually. The normal case.
* **Condition groups** (`annex_i`): one product category out of 15, the role as safety component
  or as the product itself, a third-party conformity assessment. Within a group one answer is
  enough; across groups all must hold.
* **Compound** (`compounds`): for point 2, supply sector, designated critical entity and own
  protective task, all three together.

Annex I is checked before Annex III because Article 6(1) comes before paragraph 2. The wrong mapping
is measurably expensive. Read as an enumeration, point 2 could produce **no match at all**, because
none of its questions leads to a match on its own: ten official examples. And for Annex I the
walkthrough first required both "is a safety component" and "is itself the product", failing every
system that is itself a regulated product. Article 6(1)(a) requires one **or** the other; if the
system is the product, the safety-component question is moot (`waived_when`).

**Consequences.**
* Good: each route is checked the way the official text builds it.
* Good: the Article 6(3) exemption is only asked under Annex III; it concerns only that route, and
  under Annex I the finding says so.
* Bad: three check forms are three places where something can go wrong, and they are measured only
  on the official examples, not exhaustively.
* Five guideline questions on Annex I are not asked (`skipped_questions`): they only summarise what
  the walkthrough counts itself, or refer to the legal text instead of asking about the system.

## D6 — Obligations and the data protection path stay in the rule set

**Context:** a class and a citation are not yet a list of duties | **Input:** 57 AI Act obligations, 26 sections of the data protection review path | **Output:** selection by class and role from `data/rules/`

**Context.** What follows from a class is a second question: 57 obligations of the AI Act and 26
sections of the review path for data protection law.

**Decision.** Both stay where they were: in `data/rules/ai_act_obligations.yaml` and
`data/rules/gdpr_review_path.yaml`, selected by class and role. Each entry names its legal bases as
unit ids that must exist in the corpus.

The obligations depend on the text of the regulation, not on the guidelines; they change for other
reasons than the questions and are maintained separately. That 14 of the 26 data protection
sections always apply and 12 depend on a condition is also a decision against completeness: without
it everyone would get all 26 sections, a reference collection rather than an answer.

**Consequences.**
* Good: a change in the law changes a line of text.
* Good: every legal basis named exists in the corpus (`tests/test_classification.py`), and the
  English corpus has the same ids as the German one (`tests/test_corpus_en.py`).
* Bad: the obligation list filters by class and role, not by traits. A deployer under Annex III gets
  all deployer obligations of that class. Measured on 9 October 2026: a company pre-sorting job
  applications with bought software received 14 obligations, among them the fundamental rights
  impact assessment of Article 27, which binds only bodies governed by public law, private bodies
  providing public services and deployers under Annex III points 5(b) and (c). The list is longer
  rather than shorter.
* Bad: the derived obligations are checked against the regulation text but not against an outside
  yardstick; no official collection of examples exists for them.

## D7 — Four search routes instead of one

**Context:** legal questions are asked by meaning and by wording | **Input:** hit lists of the four routes, reranking times | **Output:** fusion by rank, citation route weighted three times, reranking off by default

**Context.** Full-text search is an aid for follow-up questions, not for the classification.
"May we pre-sort job applications?" asks for meaning; the law says "recruitment or selection of
natural persons", and no word matches. "What does Article 6(3) say?" asks for wording, precisely.

**Decision.** Four routes at once: vector search for meaning, keyword search with BM25 ("Best
Matching 25") for wording, the sparse weights of the embedding model for what lies between, and a
citation route that resolves a named provision directly. They are merged by rank (*Reciprocal Rank
Fusion*): each hit receives `1 / (60 + rank)` per route that found it. Adding scores would be wrong,
because a BM25 value and a cosine similarity are on different scales, like adding metres and
kilograms. The citation route weighs three times because it is not an estimate but a fact. A
cross-encoder can rescore the best 30.

Vector search alone loses precise questions: numbers look almost alike to it, "Article 6" and
"Article 9" lie close together. Keyword search alone loses questions in other words than the
regulation's. The citation route is the most important and the cheapest: whoever names a provision
should get it, not something similar.

**Consequences.**
* Good: both kinds of question work; a hit only one route knows stays in; if one route fails, the
  others carry on.
* Bad: four routes are four places where something can go wrong, and the weight 3 for the citation
  route is set, not measured.
* The numbers 50 hits per route, 30 for reranking and 60 in the fusion are also set, not measured
  on this index.
* The cross-encoder took a measured 100 seconds per search without a graphics card. Reranking is
  therefore off by default (`COMPLIANCE_HELPER_RERANK=1` switches it on); without it the fusion
  order stands and search gets less precise, not unavailable.
* Use cases are capped at a third of the returned passages: measured, they are 1.6 percent of the
  index but supplied 38 percent of the passages, because they share the everyday language of the
  questions.

## D8 — The embedding model runs on the user's machine

**Context:** vector search needs an embedding model, which hosted services also offer | **Input:** privacy of project descriptions, usability of the shipped index, build times | **Output:** `BAAI/bge-m3` locally; only the worded answer may use a hosted model

**Context.** Hosted interfaces offer embeddings as a service: possibly better hits, no model on the
machine, billing per request.

**Decision.** The embedding model runs locally: `BAAI/bge-m3`, multilingual, 1,024 numbers per
passage, about 2.3 gigabytes. Only the worded answer may be handed to a model through an interface,
and that is optional.

Two reasons, both weighty. First, whoever describes an AI project reveals business internals; a
hosted embedding sends every question to the vendor, even if no language model words the answer.
Second, the shipped index must work for everyone who downloads the project. An index whose vectors
come from a service cannot be queried without a key for that service: the question cannot be brought
into the same vector space, and the index would be worthless. The model is also multilingual, which
made the English index possible without a second model.

**Consequences.**
* Good: runs without key, network or cost per request; the question does not leave the machine.
* Bad: 2.3 gigabytes of model and a long first build before search works: measured, the English
  index took 4,725 seconds for 2,811 units on two processor cores without a graphics card. That is a
  hurdle, and the reason the classification must work without any model.
* Bad: the hit quality of large hosted services is not reached, and this is not measured; no series
  compares the routes.
* Search has a fallback based on word hashes so the mechanics can be tried without a model.
  `compliance-helper build-index` stops, however, when the requested model is missing instead of
  writing an index of substitute quality: such an index looks intact and silently returns wrong
  hits.

## D9 — The corpus is a JSONL file in the repository

**Context:** 2,811 legal units per language need a home | **Input:** database, one file per article, one single file | **Output:** `data/processed/corpus.jsonl` and `corpus.en.jsonl`

**Context.** The legal units could live in a database, in one file per article or in one single file.

**Decision.** One file per language in the JSON Lines format (JSONL), `data/processed/corpus.jsonl`
(German) and `data/processed/corpus.en.jsonl` (English), with one JSON line per unit. Both are in version control.

The form is deliberately simple. One line per unit is readable in version control: whoever changes a
legal text sees exactly one changed line. The file can be checked line by line, also with command
line tools, and read without special tools.

**Consequences.**
* Good: traceable changes, simple checks, no database needed.
* Good: whoever downloads the project has the legal text at once, without a fetch run that can fail
  at EUR-Lex.
* Good: the stored search index carries the ids of the corpus it was built from and is rejected on
  loading if they no longer match. The count alone was not enough: an index from another corpus can
  have the same number of units, and then every vector points to the wrong passage while the answer
  looks as usual.
* Bad: the files are about 3 megabytes each and grow in version control with every change in the
  law. That is acceptable.

## D10 — Fetching is separate from processing

**Context:** the raw sources come from the network, which is unreliable | **Input:** EUR-Lex, the EU's legal database, answering with Hypertext Transfer Protocol (HTTP) status 202 with an empty body and then a firewall captcha | **Output:** fetch scripts write only to `data/raw`; the build never goes online

**Context.** The EUR-Lex website answers requests without a full browser header with HTTP 202 and
an empty body, followed by a captcha from its firewall.

**Decision.** Fetching lives in its own scripts under `scripts/` and writes only to `data/raw`
(English to `data/raw/en`). The corpus build reads from there and never goes online itself. Files
already present and above a minimum size are not fetched again.

A network problem must not damage the corpus. Whoever builds should know that the input lies there
unchanged. And whoever wants to check the sources has them as files, not as a passing response.

**Consequences.**
* Good: the build is repeatable and runs offline; the raw files can be checked.
* Good: if EUR-Lex slows down, only fetching fails, and it says so in the log instead of leaving
  half a corpus.
* Good: both regulations come from the Official Journal through Cellar, the document repository of
  the Publications Office, in German and English. The fallback source steps in only if the official
  text of a legal act is missing **entirely**; mixed in, it had put its own ids (`art-4/para-14`)
  next to the official ones (`art-4/pt-14`). A comparison against the Official Journal had found 51
  percent of the units differing; Article 13 of the General Data Protection Regulation had 909
  instead of 3,374 characters. See [data-sources.md](data-sources.md).
* The minimum size is a crude test: a file large enough but faulty in content is not fetched again.

## D11 — German in code, data and interface (superseded by D12)

**Context:** the first versions were written for staff in German companies | **Input:** German legal terms, an English draft of the guidelines | **Output:** superseded on 9 October 2026 by [D12](#d12--english-code-german-and-english-for-users)

**Context.** The tool addresses staff in German companies. The legal text is German, and the
regulation fixes its terms in German. The Commission's guidelines exist in this draft in English.

**Decision (until version 1.2.4).** German throughout: identifiers in the code, field names in the
data, questions, interface, documentation. The questions were carried over from the English draft
into plain German and carry the paragraph number of the original. Translating terms such as
"Betreiber" back and forth was seen as a risk to legal precision.

**Consequences.**
* The terms in the code matched the regulation; there was no translation layer.
* International contributors faced a hurdle, and English-speaking users had no way in. The
  multilingual embedding model would have allowed more, but it was not built. This is what D12
  changed.

## D12 — English code, German and English for users

**Context:** the German-only code shut out contributors and users without German | **Input:** the binding term list of the rename, the official English version of the regulation | **Output:** version 2.0.0 with English identifiers and message catalogs per language

**Context.** D11 kept the code readable only for German speakers and the tool usable only in
German. The worry behind it, losing legal precision in translation, does not hold for EU law in the
same way: the AI Act and the GDPR have an official English version with equally fixed terms
(deployer for Betreiber, provider for Anbieter).

**Decision.** Identifiers, data keys, enum values, file names and code comments are English, after
one binding term list (risk class `high_risk_annex_iii`, role `deployer`, file
`classification/question_flow.py`). Everything a user reads comes from message catalogs per language
(`src/compliance_helper/locales/<language>/*.json`, `web/locales/<language>.json`). The language is
chosen per request (`?lang=`, cookie, `Accept-Language`) or per call (`--lang`,
`COMPLIANCE_HELPER_LANG`); German stays the default.

**Consequences.**
* Good: the code reads like ordinary English code; the legal terms follow the official English
  version, not a word-by-word translation.
* Good: the German output did not change with the rename.
* Bad: version 2.0.0 breaks compatibility: package `compliance_helper`, command
  `compliance-helper`, English subcommands and options; `--legal-act` accepts only `AI-Act`, `GDPR`,
  `BDSG` and `Guidelines`.
* Bad: every new sentence needs two catalog entries. `tests/test_i18n.py` and
  `scripts/check_web_locales.py` fail on a missing key or a mismatched placeholder, so a gap cannot
  ship unnoticed.

## D13 — Bilingual values in the data, German as the authoritative side

**Context:** questions, rules, cases and evaluation texts must exist in both languages | **Input:** the data files, measurements on the English company questions | **Output:** `{de, en}` values, `pick()` with German fallback, vocabularies matched only in the description's language

**Context.** The data files carry most of the text a user reads. Separate English copies of each
file would double every id and every condition, and the two copies would drift like the two copies
of the flow logic in D3.

**Decision.** Every prose value is a bilingual value `{"de": "…", "en": "…"}` in the same file, next
to the language-neutral fields. `pick()` returns the active side and falls back to German, the
authoritative text. Matching vocabularies are lists per language, and a description is matched only
with the vocabulary and purpose sentences of its own language, decided by function words
(`description_languages()`); short or mixed text keeps both.

Matching across languages produced false hits, because stems cross languages by accident (German
"note" inside English "notes", English "migration" in a data migration). Measured on the English
company questions: own language only 97 of 100, both languages 95 of 100 in twice the time.

**Consequences.**
* Good: one file, one set of ids and conditions; a question cannot change its logic in one language
  only.
* Good: German results did not change; the English cases are classified like the German ones (44 of
  44), and the slow tests hold both languages to the same gate of 95 of 100 company questions.
* Bad: the English texts are a translation of the German ones, reviewed by no lawyer; the paragraph
  number at every line is the cross-check.
* Bad: some markers in the layout file compare against German question text
  (`main_question_contains`); they must stay German.

## D14 — An English corpus with the same unit ids

**Context:** English answers need English legal text to quote | **Input:** the English Official Journal, the official English translation of the BDSG, the German corpus as id reference | **Output:** `data/processed/corpus.en.jsonl` with the same 2,811 ids as the German corpus

**Context.** An English answer that quotes German legal text, or a translation of it made by the
tool, would be of little use and could mislead.

**Decision.** The English corpus is built from the English Official Journal, fetched through Cellar
with the same id anchors and read by the same parser as the German one; the BDSG comes from its
official English translation on gesetze-im-internet.de, the use cases from the English side of
`data/cases`. Short items are kept by the German ids instead of by minimum lengths, so both corpora
contain exactly the same ids; the build reports every id that is missing or extra, and
`tests/test_corpus_en.py` compares ids, counts and positions with the German corpus.

All language versions of an EU regulation are equally authentic, so the English AI Act and GDPR are
law, not a translation. Shared ids keep rules, question flow and tests language-neutral: a rule that
cites `AI-Act/art-26/para-5` finds its text in both corpora.

**Consequences.**
* Good: English answers quote the official English text.
* Good: one rule set, one question flow and one set of tests serve both languages.
* Bad: the English build depends on the German corpus as reference and refuses to run without it.
* Bad: the English BDSG is a translation by the Language Service of the Federal Ministry of the
  Interior; only the German text is legally binding.

## D15 — One search index per language, rebuilt incrementally

**Context:** an English question needs English passages and English keyword search | **Input:** build times, memory per index | **Output:** `search_index.*` and `search_index.en.*`, reuse of unchanged vectors, checkpoints

**Context.** One shared index would let the multilingual vectors find provisions across languages,
but it would show German passages in an English answer and lose the keyword route, which depends on
the language's words and stopwords. Each full build takes more than an hour on a processor without
a graphics card.

**Decision.** Each language has its own index, built from its own corpus, with index text,
stopwords and reranker citation in that language; the metadata records the language, and loading
checks it. The service loads both indexes and shares one embedding model; the command line loads
only its own. A rebuild reuses the vectors and sparse weights of every unit whose id and text
fingerprint are unchanged, and a build writes a checkpoint every two batches.

**Consequences.**
* Good: changing the use cases re-embedded 44 units in 123 seconds instead of 2,811 units; the
  change of the German citation format re-embedded 120 units in 116 seconds. The first English build
  took 4,725 seconds.
* Good: a checkpoint is named after its texts, so a run with other texts never picks up a foreign
  checkpoint.
* Bad: two indexes in memory, about 65 megabytes each, and two sets of files of about 14 megabytes
  each in the repository.
* Bad: the fingerprint covers the citation header, so any change to how citations read re-embeds the
  units it touches.

## D16 — Citations are stored as ids and rendered when shown

**Context:** rules, findings and passages must cite the same provision in two languages | **Input:** the unit ids, the counting words of each legal act | **Output:** `citation_from_id()` in `domain.py`, `readableCitation()` in `web/page.js`

**Context.** Citations written out as text in the data would have to be written twice and kept
consistent by hand. The internal ids, shown directly, are unreadable ("Buchstabe ua2-a").

**Decision.** Data refers to provisions only by unit id. The readable citation is rendered from the
id when it is shown, in the active language and with the counting word the legal act uses: "Artikel
43 Absatz 1 Unterabsatz 2 Buchstabe a KI-VO" in German, "Article 43(1), subparagraph 2, point (a) AI
Act" in English, "Anhang III Nummer 4 Buchstabe a" and "Annex III point 4(a)".

**Consequences.**
* Good: one id, two correct citations; ids stay language-neutral.
* Good: `tests/test_corpus.py` renders the citation of every unit in both corpora from its id and
  compares it with the unit's own citation.
* Bad: a change in how a citation reads touches the indexed text and therefore requires an
  incremental rebuild of the affected units (see D15).
