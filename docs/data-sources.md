# Data sources and data version

**English** | [Deutsch](data-sources.de.md)

**Context:** a legal answer without a date is worthless, so every piece of text is traced to its origin | **Input:** the files under `data/rules`, `data/evaluation`, `data/processed`, `data/cases` and the fetch scripts | **Output:** origin, date, size and licence of each source, and what is not included

Terms used below: the **question flow** is the series of questions that decides the
classification; the **legal corpus** holds the legal text, split into **legal units** (a paragraph
of an article, a point of an annex, a recital, a section of a German act); the **rule set** derives
obligations from a risk class.

## The data version in three dates

**Context:** three different things, three different dates | **Input:** the `as_of` fields of the rule files and the corpus build report | **Output:** the date each part reflects

| Part | Date | Where the date comes from |
|---|---|---|
| **Question flow** (decides the classification) | **19 May 2026** | draft Commission guidelines; field `as_of` in `data/rules/question_flow_layout.yaml`: 2026-10-04 |
| **Rule set** (obligations, data protection path) | **31 May 2026** | field `as_of` in `ai_act_obligations.yaml`, `ai_act_risk_classes.yaml` and `gdpr_review_path.yaml` under `data/rules` |
| **Legal text** (wording in the corpus) | **9 October 2026** | field `built_on` in `data/processed/corpus_report.json` and `corpus_report.en.json` |

The legal text was last built on 9 October 2026 from the Official Journal versions named below.
The questions come from the draft guidelines of 19 May 2026. Which obligation follows from which
class is written by hand and reflects 31 May 2026. **In substance the answers reflect May 2026.**
Case law, guidelines of the European Data Protection Board, Commission adequacy decisions and
delegated acts after that date are not taken into account.

The rule set carries this caveat itself and every answer repeats it:

> The deadlines are as published in the Official Journal of 12 July 2024. As of the data version of
> this rule set, changes to individual deadlines were under political discussion. Before any
> decision with financial or legal consequences, check the current state with the competent
> authority.

## 1. The Commission guidelines — basis of the classification

**Context:** the source of every question, exclusion and example | **Input:** the draft guidelines and the files in `data/rules/question_flow/` | **Output:** the document, its status and what was taken from it

* **Document:** draft guidelines of the European Commission on classifying high-risk artificial
  intelligence (AI) systems under Article 6 of Regulation (EU) 2024/1689 on artificial
  intelligence (AI Act), for stakeholder consultation
* **Version:** 19 May 2026, English
* **Scope:** 167 pages in three parts — 148 pages on Annex III, 13 pages on Annex I, 6 pages of
  general principles
* **Binding effect:** **none.** It is a draft. The public consultation ran until 23 June 2026; no
  final version existed when this work was completed. Commission guidelines do not bind courts in
  any case. The helper states this caveat in every answer that relies on them.

The question flow comes from this document. Every question, exclusion and example carries in the
field `source_ref` the paragraph number it rests on — for example `"(254)"`. Counted from the files;
`scripts/export_question_flow.py` reports the same 31 provisions and 187 examples:

| File | Annex III area | Provisions | Exclusions | Examples |
|---|---|---|---|---|
| `pt-1-biometrics.yaml` | point 1, section 3.1 | 3 | 25 | 21 |
| `pt-2-critical-infrastructure.yaml` | point 2, section 3.2 | 4 | 22 | 26 |
| `pt-3-education.yaml` | point 3, section 3.3 | 4 | 24 | 31 |
| `pt-4-employment.yaml` | point 4, section 3.4 | 3 | 18 | 34 |
| `pt-5-essential-services.yaml` | point 5, section 3.5 | 4 | 35 | 45 |
| `pt-6-7-8-public-authorities.yaml` | points 6 to 8, sections 3.6 to 3.8 | 13 | 90 | 30 |
| **total** | | **31** | **214** | **187** |

In addition, `annex-i-products.yaml` holds the 15 product categories and the conditions of
Article 6(1), and `preliminaries-and-filter.yaml` holds the 3 preliminary questions, 4 notes and
the derogation of Article 6(3). Counted over everything: **379 questions.**

An exclusion is a sentence of the official text that says what is **not** covered. An example is a
case the Commission names itself. Both appear in the finding next to the classification — without
them the finding would be a mere claim.

### The test cases

**Context:** the benchmark for the classification | **Input:** `data/evaluation/official_examples.json` | **Output:** 217 examples with the Commission's verdict

`data/evaluation/official_examples.json` holds **217 examples** from the same document, each with
scenario, expected verdict, provision, paragraph number and the Commission's reasoning, in German
and English:

```json
{"scenario": {"de": "Ein System erkennt ausschließlich nicht inklusive oder diskriminierende …",
              "en": "A system exclusively detects non-inclusive or discriminatory wording in job advertisement texts; …"},
 "expected": "not_high_risk",
 "provision": "AI-Act/annex-III/pt-4-a",
 "source_ref": "(254)",
 "official_rationale": {"de": "Es ist nicht dazu bestimmt, Menschen zu gewinnen oder auszuwählen, …",
                        "en": "It is not intended for recruiting or selecting people, even though it operates in the broad field of employment."}}
```

This is the yardstick: the expected verdicts come from the Commission. **207 of 217 are classified
correctly.** The method and every single mismatch are in
[../data/evaluation/MEASUREMENT.md](../data/evaluation/MEASUREMENT.md).

## 2. The legal text — where the wording comes from

**Context:** the text the answers quote | **Input:** `data/processed/corpus.jsonl`, `corpus.en.jsonl` and their build reports | **Output:** units per legal act, origin and licence of each source

Measured on `data/processed/corpus.jsonl`: 2,811 legal units, 2,089,820 characters. The English
`corpus.en.jsonl` holds the same 2,811 units with 1,877,159 characters. Both builds ran **without a
warning**.

| Legal act | Kind of unit | Count |
|---|---|---|
| AI Act | articles, paragraphs and points | 1,042 |
| AI Act | annexes, points and letters | 164 |
| AI Act | recitals | 180 |
| General Data Protection Regulation (GDPR) | articles, paragraphs and points | 851 |
| General Data Protection Regulation (GDPR) | recitals | 173 |
| Federal Data Protection Act (Bundesdatenschutzgesetz, BDSG) | sections and subsections | 357 |
| Use cases (not a legal source) | worked examples | 44 |

A legal unit is the smallest piece that can be pointed to: a paragraph of an article, a point or
letter of an annex, a definition, a recital, a section. The question flow points to exactly these
ids with its field `citation` — that is why the finding shows the official text and not just a
number.

Included and decisive for the classification:

* the **24 lettered points of Annex III** under the eight areas. Point 4(a) covers recruitment,
  point 4(b) working conditions — two different situations under one heading.
* the **20 legal acts of Annex I**, to which Article 6(1) refers for high risk through product
  safety law.
* the **68 definitions of Article 3 AI Act** and the **26 of Article 4 GDPR**, each a unit of its
  own.

### The route via Cellar

**Context:** how the official text is fetched | **Input:** the Cellar id of each regulation | **Output:** the Official Journal text as XHTML (the web page format in which the Official Journal is published)

Both regulations come from the official full text of the Official Journal. They are fetched not
from the EUR-Lex website but from its document repository **Cellar**, run by the Publications
Office of the European Union:

```
http://publications.europa.eu/resource/cellar/<id>
Accept: application/xhtml+xml
Accept-Language: deu      (English: eng)
```

**Why not the website:** `eur-lex.europa.eu` answers a request without complete browser headers
with Hypertext Transfer Protocol (HTTP) status 202 and zero bytes, and then serves a firewall captcha. Cellar has no such
firewall. `scripts/fetch_official_journal.py` fetches both regulations this way and discards any
response below a minimum size (1,200,000 bytes for the AI Act, 800,000 for the GDPR) — half a file
would be worse than none.

### AI Act, official full text — 1,386 units

**Context:** the central legal act | **Input:** `data/raw/ai_act_official_journal_de.xhtml` | **Output:** articles, annexes and recitals as units

* **Legal act:** Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence
* **Identifiers:** CELEX number 32024R1689 (the document number in EUR-Lex), Cellar
  `dc8116a1-3fe6-11ef-865a-01aa75ed71a1`
* **Version:** Official Journal of the European Union of 12 July 2024
* **File:** `data/raw/ai_act_official_journal_de.xhtml`, 1,338,179 bytes
* **Delivered:** 1,386 units — 113 articles with 929 paragraphs and points, 13 annexes with 151
  points and letters, 180 recitals
* **Warnings:** none
* **Licence:** official text of the European Union. Reuse of Commission documents is governed by
  Decision 2011/833/EU. Only the publication in the Official Journal is authentic; the copy shipped
  here is machine-split.

### General Data Protection Regulation, official full text — 1,024 units

**Context:** the data protection law beside the AI Act | **Input:** `data/raw/gdpr_official_journal_de.xhtml` | **Output:** articles and recitals as units

* **Legal act:** Regulation (EU) 2016/679 (General Data Protection Regulation)
* **Identifiers:** CELEX number 32016R0679, Cellar `3e485e15-11bd-11e6-ba9a-01aa75ed71a1`
* **Version:** Official Journal L 119 of 4 May 2016, page 1
* **File:** `data/raw/gdpr_official_journal_de.xhtml`, 862,613 bytes
* **Delivered:** 1,024 units — 99 articles with 752 paragraphs and points, 173 recitals
* **Warnings:** none
* **Licence:** as for the AI Act.

GDPR citations are therefore **accurate to the paragraph**. An article-by-article text from a
secondary source steps in only if the official text of a legal act is missing **entirely**; the
build then warns that a comparison on 4 October 2026 found 51 percent of its units differing, with
Article 13 GDPR at 909 instead of 3,374 characters. It is never mixed with the official text,
because it numbers definitions differently (`para-14` instead of `pt-14`) and would put the same
content into the corpus twice.

### The parser

**Context:** how the Official Journal text becomes units | **Input:** the XHTML with its anchors | **Output:** one unit per paragraph, point, letter and recital

`src/compliance_helper/corpus/eurlex.py` works through the anchors of the document (`div#art_6`,
`div#006.003`, `div#anx_III`, `*#rct_60`), never through text patterns. A text pattern would take
every mention of "Artikel 99" in running text for the start of an article.

Four peculiarities of the Official Journal on which a naive parser fails:

* **The numbering is not always in the first table cell.** Indented lists have an empty cell
  before it that carries the indentation. Annex I is built that way and was lost entirely until
  leading empty cells were skipped.
* **Section headings reset the numbering.** Annex VIII has three sections, each counting from 1
  again. The section goes into the id, otherwise three points would share one name.
* **Nested lists.** Article 5(1)(c) contains "i)" and "ii)"; in running text "i)" looks like the
  letter i, which also exists there.
* **Foreign anchors.** Articles 107 and 108 quote other legal acts with their anchors (`005.004`
  appears inside `art_107`). The paragraph number is therefore checked against the article number.

The build report names every id that occurs twice **with differing text** as a warning, because
then legal text is lost; identical duplicates are dropped and counted.

### Federal Data Protection Act — 357 units

**Context:** the German law implementing the GDPR | **Input:** `data/raw/bdsg.html` | **Output:** sections and subsections as units

* **Address:** `https://www.gesetze-im-internet.de/bdsg_2018/BJNR209710017.html`
* **Fetched:** 3 October 2026 with `scripts/fetch_bdsg.py`, file `data/raw/bdsg.html`, 271,137
  bytes
* **Scope:** 357 units, sections 1 to 86
* **Cited by the rule set:** only sections of Parts 1 and 2, the provisions implementing the GDPR.
  Part 3 (sections 45 to 84) applies under section 45 only to processing by authorities for the
  prevention, investigation, detection, prosecution or punishment of criminal and administrative
  offences, and is not drawn on, even where it contains parallel provisions.
* **Licence:** under section 5(1) of the German Copyright Act, statutes are official works without
  copyright protection. The presentation on gesetze-im-internet.de comes from the Federal Ministry
  of Justice and juris GmbH.

The parser in `src/compliance_helper/corpus/german_sources.py` works through the structure of the
page (`div.jnnorm`, `.jnenbez`, `.jnentitel`, `div.jurAbsatz`), not through text patterns, which
would split mid-sentence at a cross-reference such as "§ 63 Nummer 3 der
Verwaltungsgerichtsordnung".

### Use cases — 44 units, not a legal source

**Context:** worked examples that support search and answers | **Input:** `data/cases/*.yaml` | **Output:** 44 units of their own kind

* **Origin:** `data/cases/*.yaml`, nine files, written for this project
* **Distribution:** employment 7, credit and insurance 5, education 4, customer contact and content
  5, medical and products 4, own models 4, not high risk 6, prohibited practices 5, mixed data
  protection cases 4
* **Fields per case:** title, scenario, roles, classification, rationale, legal basis,
  obligations, learning note, pitfall, related cases
* **Stored in the corpus as:** legal act `Guidelines`, kind `example`, id `case/<slug>`. The data
  model treats `Guidelines` explicitly as non-binding.
* **Reviewed:** by no authority and no law firm. They are illustrations.

They enter the search as passages because a worked example often helps faster than the legal text.
In an answer they appear as "Use case: <title>", not as an article citation.

### English legal text — the same 2,811 ids

**Context:** what the English interface quotes | **Input:** `data/raw/en/` and the German corpus | **Output:** `data/processed/corpus.en.jsonl` with the ids of the German corpus

The English interface cites the same units as the German one, in the English wording:
`data/processed/corpus.en.jsonl`, build report `corpus_report.en.json`, raw files under
`data/raw/en/`.

* **AI Act and GDPR:** the English version of the Official Journal, fetched from Cellar with
  `Accept-Language: eng` (`scripts/fetch_official_journal.py --language en`). It carries the same
  anchors as the German version, and the parser is the same.
* **Federal Data Protection Act:** the translation by the Language Service of the Federal Ministry
  of the Interior, `https://www.gesetze-im-internet.de/englisch_bdsg/englisch_bdsg.html`
  (`scripts/fetch_bdsg.py --language en`). It includes the amendments by the Act of 23 June 2021;
  every unit names translator and version in its `source` field. Only the German text is
  authentic.
* **Use cases:** the English side of the fields in `data/cases`.
* **Same ids:** the German build decides by minimum lengths whether a short letter becomes a unit
  of its own. A translation is a few words longer or shorter and would fall differently at that
  limit, so the English build takes the ids from `corpus.jsonl`. It requires the German corpus and
  reports every differing id as a warning.

## 3. The rule set — what follows from a class

**Context:** the hand-written rules behind obligations and data protection | **Input:** the plain-text rule files (YAML format) under `data/rules` | **Output:** what each file holds and how much

Written by hand, data version 31 May 2026:

| File | Content | Count |
|---|---|---|
| `data/rules/ai_act_obligations.yaml` | the obligations with class, role, citation, deadline, evidence and consequence of an infringement | 57 obligations |
| `data/rules/gdpr_review_path.yaml` | the data protection review path in the order in which it is worked through | 26 sections |
| `data/rules/ai_act_risk_classes.yaml` | prohibitions under Article 5, transparency under Article 50, general-purpose models, change of role, deadlines, penalties | 8 prohibitions, 5 deadline stages, 3 penalty tiers |
| `data/rules/ai_act_purpose_catalog.yaml` | for each citation the same purpose in business language; supports the search in the legal text and the worded answer | 108 purpose sentences and 21 counter-purposes for 55 citations |

Every obligation and every section names its legal bases as corpus ids. All 302 distinct legal
bases are present in the corpus; `tests/test_classification.py` checks this on every test run, and
[operations-guide.md](operations-guide.md#change-the-rule-set) shows the command to check it by
hand.

## What is not included

**Context:** what nobody should look for here | **Input:** the scope of the sources above | **Output:** the list of gaps

* **Case law.** No court decision, not even of the Court of Justice of the European Union.
* **Further guidelines and opinions.** No guideline of the European Data Protection Board, the AI
  Office or a German supervisory authority. Of the Commission's documents only the draft on
  classifying high-risk AI systems is covered.
* **Harmonised standards.** The technical standards that give a presumption of conformity under
  Article 40 are not covered.
* **Delegated and implementing acts** after 31 May 2026.
* **German state data protection acts** and sector-specific rules (Social Code, Telecommunications
  Digital Services Data Protection Act and others).
* **Languages other than German and English.**
