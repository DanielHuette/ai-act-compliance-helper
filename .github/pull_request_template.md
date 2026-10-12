## What this change does / Was diese Änderung tut

<!-- One to three sentences: what changes for someone who uses the tool?
     Ein bis drei Sätze: was ändert sich für jemanden, der das Werkzeug benutzt? -->

Resolves / Erledigt #

## Kind of change / Art der Änderung

- [ ] Correction of a legal error (reference, deadline, classification, obligation text) / Berichtigung eines Rechtsfehlers (Verweis, Frist, Einstufung, Pflichttext)
- [ ] Rule set change after a change in the law / Änderung am Regelwerk aus einer Rechtsänderung
- [ ] New legal text status (corpus rebuilt) / Neuer Rechtstextstand (Rechtsbestand neu gebaut)
- [ ] Bug fix / Behebung eines Programmfehlers
- [ ] New feature / Neue Fähigkeit
- [ ] Translation (German or English) / Übersetzung (Deutsch oder Englisch)
- [ ] Documentation / Dokumentation
- [ ] Build or checks / Bauablauf oder Prüfung

## How to verify / Wie man es nachprüft

<!-- The commands or steps that let someone else see the result. For a change to the
     classification: the answers or description that gave a different result before.
     Die Befehle oder Schritte, mit denen jemand anders das Ergebnis sieht. Bei einer Änderung
     an der Einstufung: die Antworten oder die Beschreibung, die vorher ein anderes Ergebnis
     gab. -->

```
```

## For a rule set change / Bei einer Änderung am Regelwerk

- [ ] The field `as_of` in the changed file is updated / Das Feld `as_of` in der geänderten Datei ist mitgeändert
- [ ] Existing ids (`id`) are unchanged; new content has a new id / Vorhandene Kennungen (`id`) sind unverändert; inhaltlich Neues hat eine neue Kennung
- [ ] Every legal basis exists in the corpus (step "Legal bases present in corpus" in `.github/workflows/checks.yml`) / Jede Rechtsgrundlage ist im Rechtsbestand vorhanden (Schritt „Legal bases present in corpus" in `.github/workflows/checks.yml`)
- [ ] Every user-facing text has a German and an English side that say the same / Jeder Text für Nutzer hat eine deutsche und eine englische Seite, die dasselbe sagen
- [ ] The provision was read in the official text, and the source is named in the issue or here / Die Fundstelle ist am amtlichen Text nachgelesen, und die Quelle steht im Fehlerbericht oder hier
- [ ] After a question flow change: `scripts/export_question_flow.py` was run and `scripts/check_parity.py --runs 400` agrees / Nach einer Änderung an der Fragefolge: `scripts/export_question_flow.py` ist gelaufen und `scripts/check_parity.py --runs 400` stimmt überein
- [ ] The figures are measured, not remembered / Die Zahlen sind nachgemessen, nicht erinnert

## For a new legal text status / Bei einem neuen Rechtstextstand

- [ ] `data/processed/corpus_report.json` and `data/processed/corpus_report.en.json` are part of the change, and their warnings are named / `data/processed/corpus_report.json` und `data/processed/corpus_report.en.json` sind Teil der Änderung, und ihre Warnungen sind benannt
- [ ] Both search indexes are rebuilt (`compliance-helper build-index --language de` and `--language en`) / Beide Suchbestände sind neu gebaut (`compliance-helper build-index --language de` und `--language en`)
- [ ] The counts in `data/evaluation/figures.json`, both READMEs and the data sources documentation are updated / Die Stückzahlen in `data/evaluation/figures.json`, beiden READMEs und der Dokumentation der Datenquellen sind angepasst

## Always / Immer

- [ ] `scripts/check_all.sh` passes (ruff, ruff format, mypy, bandit, pip-audit, pytest, parity, rule set) / `scripts/check_all.sh` läuft durch (ruff, ruff format, mypy, bandit, pip-audit, pytest, Gleichlauf, Regelsatz)
- [ ] English identifiers, comments and developer messages; user-facing texts in both languages / Englische Bezeichner, Kommentare und Entwicklermeldungen; Texte für Nutzer in beiden Sprachen
- [ ] Technical terms explained on first use, abbreviations written out / Fachbegriffe beim ersten Vorkommen erklärt, Abkürzungen ausgeschrieben
- [ ] The module docstring of every changed file still states context, input and output / Der Dateikopf jeder geänderten Datei nennt weiter Kontext, Eingabe und Ergebnis
- [ ] The classification is still made without a language model / Die Einstufung entsteht weiterhin ohne Sprachmodell
- [ ] What is not checked is marked as not checked / Was nicht geprüft ist, steht als nicht geprüft da
- [ ] CHANGELOG.md has an entry under "Unreleased" / CHANGELOG.md ist unter „Unreleased" ergänzt

## What I did not check / Was ich nicht geprüft habe

<!-- Here. Better an open point named than completeness claimed.
     Hier hin. Lieber eine offene Stelle benannt als eine behauptete Vollständigkeit. -->
