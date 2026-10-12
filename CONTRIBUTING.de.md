# Mitarbeit

[English](CONTRIBUTING.md) | **Deutsch**

**Kontext:** wie man Fehler meldet und Änderungen vorschlägt | **Eingabe:** ein Programmfehler, eine falsche Rechtsangabe, ein Wunsch oder eine Programmänderung | **Ergebnis:** der richtige Weg und die Bedingungen, die eine Änderung erfüllen muss

Danke, dass Sie sich die Mühe machen. Dieses Blatt sagt, wohin was gehört und was eine Änderung
erfüllen muss, um übernommen zu werden.

Eine Besonderheit vorweg: **Rechtsfehler werden anders behandelt als Programmfehler.** Ein
Programmfehler ärgert den, der ihn trifft. Ein falscher Artikelverweis geht in eine Auskunft
ein, nach der jemand eine Entscheidung trifft. Deshalb hat er einen eigenen Weg, eine eigene
Vorlage und Vorrang vor allem anderen. Siehe [Rechtsfehler](#rechtsfehler).

## Welchen Weg nehme ich?

**Kontext:** die Wahl der Vorlage | **Eingabe:** Ihre Lage | **Ergebnis:** der passende Weg

| Ihre Lage | Weg |
|---|---|
| Ein Artikelverweis, eine Frist, eine Einstufung oder ein Pflichttext ist falsch | Vorlage **Rechtsfehler** (`legal_error.yml`) |
| Etwas stürzt ab oder tut nicht, was dasteht | Vorlage **Fehler im Programm** (`bug_report.yml`) |
| Etwas fehlt | Vorlage **Wunsch** (`feature_request.yml`) |
| Eine Sicherheitslücke | **Nicht öffentlich.** Nach [SECURITY.de.md](SECURITY.de.md) |
| Eine Verständnisfrage | Diskussionen, oder ein Fehlerbericht, wenn die Dokumentation die Antwort hätte geben müssen |

## Rechtsfehler

**Kontext:** Meldungen über falschen Rechtsinhalt | **Eingabe:** was das Werkzeug sagt, was richtig wäre, und die Fundstelle dazu | **Ergebnis:** eine Berichtigung, eine Warnung oder eine festgehaltene offene Frage

### Warum ein eigener Weg

Das Werkzeug ordnet Vorhaben mit künstlicher Intelligenz (KI) rechtlich ein. Ist ein Verweis falsch, ist die Auskunft falsch,
und zwar für jeden, der das Werkzeug benutzt, nicht nur für den, der den Fehler bemerkt hat.
Deshalb:

* Rechtsfehler werden **vor** allen anderen Meldungen bearbeitet.
* Eine Meldung wird nicht geschlossen, weil sie alt ist.
* Lässt sich der Fehler nicht gleich beheben, kommt zuerst eine Warnung in den betroffenen
  Datensatz, dann die Berichtigung.

### Was in die Meldung gehört

Die Vorlage fragt es ab; hier die Begründung dazu:

1. **Was das Werkzeug sagt.** Die Antworten oder die Beschreibung, die zu der Auskunft geführt
   haben, und die Ausgabe, am besten als Text zum Mitlesen. Ohne die Eingabe ist der Fehler
   nicht nachzustellen, weil die Einstufung davon abhängt.
2. **Was richtig wäre.** Nicht nur „das stimmt nicht", sondern die richtige Angabe.
3. **Die Fundstelle, auf die Sie sich stützen.** Artikel, Absatz, Nummer, Buchstabe. Bei der
   Verordnung (EU) 2024/1689 (KI-Verordnung) bitte am Amtsblatt vom 12. Juli 2024 oder an einer
   späteren berichtigten Fassung, und sagen Sie, welche Sie benutzt haben. Bei nationalem Recht
   der Paragraf samt Gesetz.
4. **Woher Ihre Fundstelle kommt.** Amtsblatt, Bundesgesetzblatt, Entscheidung eines Gerichts
   mit Aktenzeichen, Leitlinie mit Datum. Ein Verweis auf einen Blogbeitrag genügt nicht, weil
   daraus keine Berichtigung werden kann.
5. **Welche Datei betroffen ist**, wenn Sie es wissen: `ai_act_obligations.yaml`,
   `ai_act_risk_classes.yaml`, `gdpr_review_path.yaml`, eine Datei der Fragefolge unter
   `data/rules/question_flow/`, eine Falldatei unter `data/cases/` oder der Rechtsbestand selbst.

### Vier Arten von Rechtsfehlern und was mit ihnen geschieht

* **Falscher Verweis** (die Pflicht steht in Artikel 27, nicht 26). Wird berichtigt, sobald die
  Fundstelle belegt ist. Das ist der einfachste Fall.
* **Falsche Frist.** Wird berichtigt. Dabei wird das Datum `as_of` in der Datei mitgeführt und
  der Vorbehalt geprüft.
* **Falscher Pflichtinhalt** (die Pflicht verlangt etwas anderes). Braucht die Fundstelle im
  Wortlaut, weil der Text in `action_required` eine Zusammenfassung ist und daran gemessen wird.
* **Falsche Einstufung** (das System fällt nicht unter Anhang III, oder doch). Der schwierigste
  Fall, weil hier eine Wertung steckt. Ist die Rechtslage umstritten, wird die Einstufung nicht
  einfach umgedreht. Dann bekommt die betroffene Regel einen Hinweis auf den Streitstand und
  eine niedrigere Sicherheit (`needs_review` statt `likely`), und die offene Frage kommt dazu.
  Eine strittige Frage als entschieden darzustellen wäre der größere Fehler.

### Was nicht als Rechtsfehler gilt

* **„Die Liste ist zu lang."** Das ist bekannt und beschrieben: die Pflichten werden nach Klasse
  und Rolle ausgewählt, nicht nach den Merkmalen des Vorhabens. Siehe
  [docs/architecture.de.md](docs/architecture.de.md), Abschnitt über die Grenzen des Systems.
  Ein Wunsch nach einer genaueren Auswahl ist willkommen, als Wunsch.
* **„Das ist keine Rechtsberatung."** Richtig, das steht so da. Siehe
  [docs/liability.de.md](docs/liability.de.md).
* **Eine andere Auffassung ohne Fundstelle.** Rechtsauffassungen können auseinandergehen; das
  Regelwerk folgt dem Wortlaut und sagt, wo es unsicher ist. Ohne Fundstelle lässt sich daran
  nichts ändern.

## Änderungen am Regelwerk

**Kontext:** Arbeit an den Dateien unter `data/rules/` | **Eingabe:** eine belegte Rechtsänderung oder Berichtigung | **Ergebnis:** ein stimmiges Regelwerk in beiden Sprachen, neu ausgegeben und nachgemessen

Das Regelwerk liegt in `data/rules/*.yaml` und `data/rules/question_flow/*.yaml`. Wer dort etwas
ändert:

1. **Ändert das Datum mit.** Jede Regeldatei hat im Kopf ein Feld `as_of`, die meisten auch eine
   `version_note`. Das Datum erscheint in jeder Auskunft; ein falsches Datum ist schlimmer als
   ein altes.
2. **Lässt Kennungen stehen.** Das Feld `id` einer Pflicht, eines Abschnitts oder einer Frage
   wird verwiesen, aus den Fallbeispielen, den Messdaten und der Webseite. Eine Pflicht, die
   inhaltlich etwas anderes wird, bekommt eine neue Kennung.
3. **Gibt Rechtsgrundlagen als Kennungen an**, in der Form `AI-Act/art-26/para-1`,
   `GDPR/art-35` oder `BDSG/sec-26`. Sie müssen im Rechtsbestand vorhanden sein, sonst erscheint
   die Pflicht ohne Wortlaut. Das prüft `scripts/check_rule_set.py`, ein Schritt in
   `.github/workflows/checks.yml`.
4. **Schreibt beide Sprachen.** Jeder Text, den ein Nutzer liest, ist ein Paar
   `{de: ..., en: ...}`. Beide Seiten sagen dasselbe.
5. **Schreibt in Alltagssprache.** Der `title` ist ein Satz, kein Gesetzeszitat.
   `action_required` sagt, was zu tun ist, nicht was das Gesetz sagt. Jeden Fachbegriff beim
   ersten Vorkommen erklären, jede Abkürzung ausschreiben.
6. **Misst die Zahlen nach**, statt sie zu erinnern:

```bash
PYTHONPATH=src python -c "
from compliance_helper.classification.assessor import rule_set
rules = rule_set()
print('as of:', rules.as_of, '| obligations:', len(rules.obligations),
      '| data protection sections:', len(rules.data_protection))
"
```

7. **Gibt die Fragefolge neu aus**, nach einer Änderung unter `data/rules/question_flow/` oder an
   `question_flow_layout.yaml`, damit Webseite und Programm dieselben Daten lesen, und prüft,
   dass beide weiter gleich rechnen:

```bash
python scripts/export_question_flow.py --output web/question_flow.json
python scripts/check_parity.py --runs 400
```

8. **Trägt die Änderung in [CHANGELOG.md](CHANGELOG.md) ein**, unter „Unreleased". Die
   Änderungsliste wird auf Englisch geführt. Eine Änderung am Regelwerk ist für die Nutzer
   wichtiger als jede Programmänderung.

## Änderungen am Programm

**Kontext:** Programmtext, Prüfungen und Webseite | **Eingabe:** eine Berichtigung oder eine neue Fähigkeit | **Ergebnis:** eine Änderung, die jede Prüfung des Prüfstands besteht

### Voraussetzungen

```bash
python -m venv .venv
source .venv/bin/activate
pip install --constraint constraints.txt -e ".[dev]"
```

### Was laufen muss

Das Gleiche, was in `.github/workflows/checks.yml` läuft, oder auf einmal `scripts/check_all.sh`:

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

Jeder dieser Schritte bricht den Lauf ab, und keiner meldet heute etwas. Bringen Sie keinen neuen
Befund hinzu. `bandit` läuft ohne allgemeine Ausnahmen; die wenigen Vermerke `# nosec` nennen
ihre Regel jeweils an der Stelle selbst.

Drei Marken für Prüfungen sind festgelegt: `slow` für Prüfungen, die die lokalen Modelle
brauchen, `network` für solche, die Netzzugang brauchen, und `container` für solche, die ein
Docker-Abbild bauen. `slow` und `network` laufen im Prüfstand **nicht** mit; er lädt keine
Modelle herunter. Wer eine Prüfung schreibt, die ein Modell braucht, markiert sie mit
`@pytest.mark.slow`.

Nach einer Änderung an `web/index.html`, `web/page.js` oder `web/locales/*.json`:
`python scripts/check_web_locales.py`.

### Was eine Änderung erfüllen muss

* **Englisch im Programmtext, beide Sprachen für die Nutzer.** Bezeichner, Kommentare und
  Meldungen für Entwickler sind englisch. Jeder Text, den ein Nutzer liest, steht auf Deutsch
  und Englisch, in `src/compliance_helper/locales/` und `web/locales/` oder als Paar
  `{de, en}` in den Daten.
* **Der Dateikopf nennt Kontext, Eingabe und Ergebnis.** Wer eine Datei anlegt, schreibt ihn
  mit. Wer eine Entscheidung ändert, ändert ihn mit.
* **Fachbegriffe erklären.** Beim ersten Vorkommen in Alltagssprache, jede Abkürzung
  ausgeschrieben. Das gilt im Programmtext wie in der Dokumentation.
* **Keine erfundene Zahl.** Jede Mengenangabe in Dokumentation oder Kommentar wird nachgemessen:
  Zeilen zählen, die Datei öffnen, nicht schätzen, nicht erinnern.
* **Was nicht geprüft ist, steht als nicht geprüft da.** Eine Vermutung wird als Vermutung
  geschrieben.
* **Die Trennung von Einstufung und Formulierung bleibt.** Eine Änderung, nach der ein
  Sprachmodell die Risikoklasse oder eine Pflicht bestimmt, wird nicht übernommen, auch nicht als
  Rückfall, auch nicht hinter einem Schalter. Das ist die Grundentscheidung des Projekts, siehe
  [docs/architecture.de.md](docs/architecture.de.md), Abschnitt über die Formulierung durch ein
  Sprachmodell.
* **Keine Diagnoseanzeigen im fertigen Werkzeug.** Was das Werkzeug kann, muss am Ergebnis
  ablesbar sein. Betriebsmeldungen gehören ins Protokoll, nicht in die Auskunft.

## Änderungsvorschläge einreichen

**Kontext:** der Vorschlag selbst | **Eingabe:** Ihr Zweig | **Ergebnis:** ein prüfbarer Änderungsvorschlag

* Ein Vorschlag, eine Sache. Ein Vorschlag, der das Regelwerk ändert **und** etwas umbaut, lässt
  sich nicht prüfen.
* In der Beschreibung steht, welchen Fehlerbericht er erledigt und wie man es nachprüft.
* Umbenennen, Umsortieren, Formatieren und Aufräumen ohne Wirkung werden nicht übernommen. Wer
  eine Sache verbessert, verbessert die Sache.
* Mit dem Einreichen stellen Sie Ihren Beitrag unter die Apache License 2.0 (Abschnitt 5 des
  Lizenztexts). Ein Zusatzvertrag ist nicht zu unterschreiben.
* Wer mehr als eine Kleinigkeit beiträgt, darf sich in [AUTHORS.md](AUTHORS.md) eintragen.

## Umgangston

**Kontext:** wie wir zusammenarbeiten | **Eingabe:** keine | **Ergebnis:** die geltenden Regeln

Es gilt der [Verhaltenskodex](CODE_OF_CONDUCT.de.md). Kurz: sachlich bleiben, auch wenn jemand
etwas Falsches sagt, besonders bei Rechtsfragen, wo Auffassungen auseinandergehen und das nicht
an der Person liegt.
