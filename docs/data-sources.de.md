# Datenquellen und Datenstand

[English](data-sources.md) | **Deutsch**

**Kontext:** eine Rechtsauskunft ohne Datum ist wertlos, darum wird jedes Stück Text zu seiner Herkunft zurückverfolgt | **Eingabe:** die Dateien unter `data/rules`, `data/evaluation`, `data/processed`, `data/cases` und die Abrufskripte | **Ergebnis:** Herkunft, Datum, Umfang und Lizenzlage jeder Quelle und was nicht enthalten ist

Begriffe in diesem Blatt: die **Fragefolge** ist die Reihe von Fragen, aus der die Einstufung
entsteht; der **Rechtsbestand** (im Programm: Korpus) enthält den Gesetzestext, zerlegt in
**Rechtseinheiten** (ein Absatz eines Artikels, eine Nummer eines Anhangs, ein Erwägungsgrund, ein
Paragraf); das **Regelwerk** leitet aus einer Risikoklasse die Pflichten ab.

## Der Stand in drei Daten

**Kontext:** drei verschiedene Dinge, drei verschiedene Daten | **Eingabe:** die Felder `as_of` der Regeldateien und der Baubericht des Rechtsbestands | **Ergebnis:** das Datum, auf dem jeder Teil steht

| Teil | Datum | Woher das Datum kommt |
|---|---|---|
| **Fragefolge** (woraus die Einstufung entsteht) | **19.05.2026** | Entwurf der Leitlinien der Kommission; Feld `as_of` in `data/rules/question_flow_layout.yaml`: 2026-10-04 |
| **Regelwerk** (Pflichten, Datenschutzpfad) | **31.05.2026** | Feld `as_of` in `ai_act_obligations.yaml`, `ai_act_risk_classes.yaml` und `gdpr_review_path.yaml` unter `data/rules` |
| **Rechtstext** (Wortlaut im Bestand) | **09.10.2026** | Feld `built_on` in `data/processed/corpus_report.json` und `corpus_report.en.json` |

Der Rechtstext wurde zuletzt am 09.10.2026 aus den unten genannten Fassungen des Amtsblatts gebaut.
Die Fragen stammen aus dem Entwurf der Leitlinien vom 19. Mai 2026. Welche Pflicht aus welcher
Klasse folgt, ist von Hand geschrieben und steht auf dem 31.05.2026. **Inhaltlich steht die
Auskunft also auf Mai 2026.** Rechtsprechung, Leitlinien des Europäischen Datenschutzausschusses,
Angemessenheitsbeschlüsse der Kommission und delegierte Rechtsakte nach diesem Datum sind nicht
berücksichtigt.

Der Vorbehalt steht im Regelwerk selbst und wird in jeder Auskunft mitgegeben:

> Die Fristen stehen so im Amtsblatt vom 12. Juli 2024. Zum Datenstand dieses Regelsatzes wurden
> Änderungen einzelner Fristen politisch erörtert. Vor einer Entscheidung mit Geld- oder
> Rechtsfolgen ist der geltende Stand bei der zuständigen Behörde zu prüfen.

## 1. Die Leitlinien der Kommission — Grundlage der Einstufung

**Kontext:** die Quelle jeder Frage, jedes Ausschlusses und jedes Beispiels | **Eingabe:** der Entwurf der Leitlinien und die Dateien in `data/rules/question_flow/` | **Ergebnis:** das Dokument, seine Verbindlichkeit und was daraus übernommen ist

* **Dokument:** Entwurf der Leitlinien der Europäischen Kommission zur Einstufung von Systemen der
  künstlichen Intelligenz (KI) mit hohem Risiko nach Artikel 6 der Verordnung (EU) 2024/1689 über
  künstliche Intelligenz (KI-Verordnung), zur Anhörung der Beteiligten
* **Fassung:** 19. Mai 2026, englisch
* **Umfang:** 167 Seiten in drei Teilen — 148 Seiten zu Anhang III, 13 Seiten zu Anhang I,
  6 Seiten allgemeine Grundsätze
* **Bindungswirkung:** **keine.** Es ist ein Entwurf. Die öffentliche Anhörung lief bis zum
  23. Juni 2026; eine endgültige Fassung lag bei Abschluss dieser Arbeit nicht vor. Leitlinien der
  Kommission binden Gerichte ohnehin nicht. Der Helfer sagt diesen Vorbehalt in jeder Auskunft mit,
  die sich darauf stützt.

Aus diesem Dokument stammt die Fragefolge. Jede Frage, jeder Ausschluss und jedes Beispiel trägt im
Feld `source_ref` die Absatznummer der Stelle, auf der es beruht — etwa `"(254)"`. Aus den Dateien
gezählt; `scripts/export_question_flow.py` meldet dieselben 31 Stellen und 187 Beispiele:

| Datei | Bereich des Anhangs III | Stellen | Ausschlüsse | Beispiele |
|---|---|---|---|---|
| `pt-1-biometrics.yaml` | Nummer 1, Abschnitt 3.1 | 3 | 25 | 21 |
| `pt-2-critical-infrastructure.yaml` | Nummer 2, Abschnitt 3.2 | 4 | 22 | 26 |
| `pt-3-education.yaml` | Nummer 3, Abschnitt 3.3 | 4 | 24 | 31 |
| `pt-4-employment.yaml` | Nummer 4, Abschnitt 3.4 | 3 | 18 | 34 |
| `pt-5-essential-services.yaml` | Nummer 5, Abschnitt 3.5 | 4 | 35 | 45 |
| `pt-6-7-8-public-authorities.yaml` | Nummern 6 bis 8, Abschnitte 3.6 bis 3.8 | 13 | 90 | 30 |
| **zusammen** | | **31** | **214** | **187** |

Dazu `annex-i-products.yaml` mit den 15 Produktgattungen und den Bedingungen des Artikels 6
Absatz 1, und `preliminaries-and-filter.yaml` mit den 3 Vorfragen, 4 Hinweisen und der Ausnahme
des Artikels 6 Absatz 3. Über alles gezählt: **379 Fragen.**

Ein Ausschluss ist ein Satz des amtlichen Textes, der sagt, was **nicht** erfasst ist. Ein Beispiel
ist ein Fall, den die Kommission selbst nennt. Beides steht im Befund neben der Einstufung — ohne
diese Sätze wäre der Befund eine Behauptung.

### Die Prüffälle

**Kontext:** der Maßstab für die Einstufung | **Eingabe:** `data/evaluation/official_examples.json` | **Ergebnis:** 217 Beispiele mit der Wertung der Kommission

`data/evaluation/official_examples.json` enthält **217 Beispiele** aus demselben Dokument, jedes
mit Lage, Soll-Wertung, Stelle, Absatznummer und der Begründung der Kommission, auf Deutsch und
Englisch:

```json
{"scenario": {"de": "Ein System erkennt ausschließlich nicht inklusive oder diskriminierende Formulierungen in Anzeigentexten; …",
              "en": "A system exclusively detects non-inclusive or discriminatory wording …"},
 "expected": "not_high_risk",
 "provision": "AI-Act/annex-III/pt-4-a",
 "source_ref": "(254)",
 "official_rationale": {"de": "Es ist nicht dazu bestimmt, Menschen zu gewinnen oder auszuwählen, auch wenn es im weiten Beschäftigungsbereich arbeitet.",
                        "en": "It is not intended for recruiting or selecting people, …"}}
```

Das ist der Maßstab: die Soll-Wertungen stammen von der Kommission. **207 von 217 werden richtig
eingestuft.** Das Messverfahren und jede einzelne Abweichung stehen in
[../data/evaluation/MEASUREMENT.de.md](../data/evaluation/MEASUREMENT.de.md).

## 2. Der Rechtstext — woher der Wortlaut kommt

**Kontext:** der Text, den die Auskünfte zitieren | **Eingabe:** `data/processed/corpus.jsonl`, `corpus.en.jsonl` und ihre Bauberichte | **Ergebnis:** Einheiten je Rechtsakt, Herkunft und Lizenzlage jeder Quelle

Nachgemessen an `data/processed/corpus.jsonl`: 2811 Rechtseinheiten, 2 089 820 Zeichen. Der
englische Bestand `corpus.en.jsonl` enthält dieselben 2811 Einheiten mit 1 877 159 Zeichen. Beide
Bauläufe liefen **ohne Warnung**.

| Rechtsakt | Art der Einheit | Stück |
|---|---|---|
| KI-Verordnung | Artikel, Absätze und Nummern | 1042 |
| KI-Verordnung | Anhänge, Nummern und Buchstaben | 164 |
| KI-Verordnung | Erwägungsgründe | 180 |
| Datenschutz-Grundverordnung (DSGVO) | Artikel, Absätze und Nummern | 851 |
| Datenschutz-Grundverordnung (DSGVO) | Erwägungsgründe | 173 |
| Bundesdatenschutzgesetz (BDSG) | Paragrafen und Absätze | 357 |
| Anwendungsfälle (keine Rechtsquelle) | Fallbeispiele | 44 |

Eine Rechtseinheit ist das kleinste Stück, auf das sich zeigen lässt: ein Absatz eines Artikels,
eine Nummer oder ein Buchstabe eines Anhangs, eine Begriffsbestimmung, ein Erwägungsgrund, ein
Paragraf. Die Fragefolge zeigt mit ihrem Feld `citation` auf genau diese Kennungen — darum steht im
Befund der amtliche Text und nicht nur eine Nummer.

Darin enthalten und für die Einstufung entscheidend:

* die **24 Buchstabenpunkte des Anhangs III** unter den acht Bereichen. Nummer 4 Buchstabe a
  trifft die Einstellung, Buchstabe b die Arbeitsbedingungen — zwei verschiedene Sachverhalte unter
  einer Überschrift.
* die **20 Rechtsakte des Anhangs I**, auf die Artikel 6 Absatz 1 für das hohe Risiko über das
  Produktsicherheitsrecht verweist.
* die **68 Begriffsbestimmungen des Artikels 3 KI-Verordnung** und die **26 des Artikels 4
  DSGVO**, jede als eigene Einheit.

### Der Weg über Cellar

**Kontext:** wie der amtliche Text geholt wird | **Eingabe:** die Cellar-Kennung jeder Verordnung | **Ergebnis:** der Text des Amtsblatts als XHTML-Datei (das Seitenformat, in dem das Amtsblatt erscheint)

Beide Verordnungen kommen aus dem amtlichen Volltext des Amtsblatts. Geholt werden sie nicht über
die Webseite von EUR-Lex, sondern über deren Dokumentenablage **Cellar**, die das Amt für
Veröffentlichungen der Europäischen Union betreibt:

```
http://publications.europa.eu/resource/cellar/<Kennung>
Accept: application/xhtml+xml
Accept-Language: deu      (Englisch: eng)
```

**Warum nicht über die Webseite:** `eur-lex.europa.eu` antwortet ohne vollständigen Browser-Kopf
mit dem Statuscode 202 des Hypertext Transfer Protocol (HTTP) und null Byte und schickt danach ein Captcha seiner Firewall. Vor Cellar
steht diese Firewall nicht. `scripts/fetch_official_journal.py` holt beide Verordnungen so und
verwirft jede Antwort unter der Mindestgröße (1 200 000 Byte für die KI-Verordnung, 800 000 für
die DSGVO) — eine halbe Datei wäre schlimmer als keine.

### KI-Verordnung, amtlicher Volltext — 1386 Einheiten

**Kontext:** der zentrale Rechtsakt | **Eingabe:** `data/raw/ai_act_official_journal_de.xhtml` | **Ergebnis:** Artikel, Anhänge und Erwägungsgründe als Einheiten

* **Rechtsakt:** Verordnung (EU) 2024/1689 zur Festlegung harmonisierter Vorschriften für
  künstliche Intelligenz
* **Kennungen:** CELEX-Nummer 32024R1689 (die Dokumentnummer in EUR-Lex), Cellar
  `dc8116a1-3fe6-11ef-865a-01aa75ed71a1`
* **Fassung:** Amtsblatt der Europäischen Union vom 12. Juli 2024
* **Datei:** `data/raw/ai_act_official_journal_de.xhtml`, 1 338 179 Byte
* **Geliefert:** 1386 Einheiten — 113 Artikel mit 929 Absätzen und Nummern, 13 Anhänge mit 151
  Nummern und Buchstaben, 180 Erwägungsgründe
* **Warnungen:** keine
* **Lizenzlage:** amtlicher Text der Europäischen Union. Für die Weiterverwendung von
  Kommissionsdokumenten gilt der Beschluss 2011/833/EU. Verbindlich ist allein die
  Veröffentlichung im Amtsblatt; die hier mitgelieferte Fassung ist eine maschinell zerlegte Kopie.

### Datenschutz-Grundverordnung, amtlicher Volltext — 1024 Einheiten

**Kontext:** das Datenschutzrecht neben der KI-Verordnung | **Eingabe:** `data/raw/gdpr_official_journal_de.xhtml` | **Ergebnis:** Artikel und Erwägungsgründe als Einheiten

* **Rechtsakt:** Verordnung (EU) 2016/679 (Datenschutz-Grundverordnung)
* **Kennungen:** CELEX-Nummer 32016R0679, Cellar `3e485e15-11bd-11e6-ba9a-01aa75ed71a1`
* **Fassung:** Amtsblatt L 119 vom 4. Mai 2016, Seite 1
* **Datei:** `data/raw/gdpr_official_journal_de.xhtml`, 862 613 Byte
* **Geliefert:** 1024 Einheiten — 99 Artikel mit 752 Absätzen und Nummern, 173 Erwägungsgründe
* **Warnungen:** keine
* **Lizenzlage:** wie bei der KI-Verordnung.

Die Fundstellen zur DSGVO sind damit **absatzgenau**. Ein artikelweiser Text aus einer
Zweitquelle springt nur ein, wenn der amtliche Text eines Rechtsakts **ganz** fehlt; der Bau warnt
dann, dass ein Vergleich am 04.10.2026 bei 51 Prozent der Einheiten Abweichungen fand und
Artikel 13 DSGVO dort 909 statt 3374 Zeichen hatte. Mit dem amtlichen Text gemischt wird er nie,
weil er Begriffsbestimmungen anders zählt (`para-14` statt `pt-14`) und denselben Inhalt doppelt in
den Bestand brächte.

### Der Zerleger

**Kontext:** wie aus dem Text des Amtsblatts Einheiten werden | **Eingabe:** die XHTML-Datei mit ihren Ankern | **Ergebnis:** je Absatz, Nummer, Buchstabe und Erwägungsgrund eine Einheit

`src/compliance_helper/corpus/eurlex.py` arbeitet über die Anker des Dokuments (`div#art_6`,
`div#006.003`, `div#anx_III`, `*#rct_60`), nie über Textmuster. Ein Textmuster hielte jede
Erwähnung von „Artikel 99" im Fließtext für einen Artikelanfang.

Vier Eigenheiten des Amtsblatts, an denen ein einfacher Zerleger scheitert:

* **Die Zählung steht nicht immer in der ersten Tabellenzelle.** Eingerückte Aufzählungen haben
  davor eine leere Zelle, die die Einrückung trägt. Anhang I ist so gebaut und ging vollständig
  verloren, bis leere Zellen am Anfang übersprungen wurden.
* **Abschnittsköpfe setzen die Zählung zurück.** Anhang VIII hat drei Abschnitte, jeder zählt
  wieder ab 1. Der Abschnitt gehört in die Kennung, sonst tragen drei Nummern denselben Namen.
* **Verschachtelte Aufzählungen.** Artikel 5 Absatz 1 Buchstabe c enthält „i)" und „ii)"; im
  Fließtext sieht „i)" wie der Buchstabe i aus, den es dort auch gibt.
* **Fremde Anker.** Artikel 107 und 108 zitieren fremde Rechtsakte mit deren Ankern (`005.004`
  steht in `art_107`). Die Absatznummer wird darum gegen die Artikelnummer geprüft.

Der Baubericht nennt jede Kennung, die zweimal **mit verschiedenem Text** vorkommt, als Warnung,
denn dann geht Rechtstext verloren; gleiche Doppel werden verworfen und gezählt.

### Bundesdatenschutzgesetz — 357 Einheiten

**Kontext:** das deutsche Gesetz zur Durchführung der DSGVO | **Eingabe:** `data/raw/bdsg.html` | **Ergebnis:** Paragrafen und Absätze als Einheiten

* **Adresse:** `https://www.gesetze-im-internet.de/bdsg_2018/BJNR209710017.html`
* **Geholt:** 03.10.2026 mit `scripts/fetch_bdsg.py`, Datei `data/raw/bdsg.html`, 271 137 Byte
* **Umfang:** 357 Einheiten, §§ 1 bis 86
* **Vom Regelwerk zitiert:** nur Paragrafen aus Teil 1 und 2, also die Durchführungsbestimmungen
  zur DSGVO. Teil 3 (§§ 45 bis 84) gilt nach § 45 nur für Verarbeitungen durch Behörden zur
  Verhütung, Ermittlung, Aufdeckung, Verfolgung oder Ahndung von Straftaten und
  Ordnungswidrigkeiten und wird nicht herangezogen, auch wo er gleichlaufende Vorschriften enthält.
* **Lizenzlage:** Gesetze sind nach § 5 Absatz 1 des Urheberrechtsgesetzes amtliche Werke ohne
  Urheberrechtsschutz. Die Darstellung auf gesetze-im-internet.de stammt vom Bundesministerium der
  Justiz und von der juris GmbH.

Der Zerleger `src/compliance_helper/corpus/german_sources.py` arbeitet über die Gliederung der
Seite (`div.jnnorm`, `.jnenbez`, `.jnentitel`, `div.jurAbsatz`), nicht über Textmuster; ein
Textmuster trennte sonst mitten im Satz, wenn ein Querverweis wie „§ 63 Nummer 3 der
Verwaltungsgerichtsordnung" auftritt.

### Anwendungsfälle — 44 Einheiten, keine Rechtsquelle

**Kontext:** ausgearbeitete Beispiele, die Suche und Auskunft stützen | **Eingabe:** `data/cases/*.yaml` | **Ergebnis:** 44 Einheiten eigener Art

* **Woher:** `data/cases/*.yaml`, neun Dateien, für dieses Werkzeug geschrieben
* **Verteilung:** Beschäftigung 7, Kredit und Versicherung 5, Bildung 4, Kundenkontakt und Inhalte
  5, Medizin und Produkte 4, eigene Modelle 4, kein hohes Risiko 6, verbotene Praktiken 5,
  Datenschutz-Mischfälle 4
* **Felder je Fall:** Titel, Lage, Rollen, Einstufung, Begründung, Rechtsgrundlagen, Pflichten,
  Lernhinweis, Stolperstein, verwandte Fälle
* **Im Bestand geführt als:** Rechtsakt `Guidelines`, Art `example`, Kennung `case/<Kurzname>`.
  Das Datenmodell behandelt `Guidelines` ausdrücklich als nicht verbindlich.
* **Geprüft:** von keiner Behörde und von keiner Kanzlei. Sie dienen der Anschauung.

Sie gehen als Belegstellen in die Suche ein, weil ein ausgearbeitetes Beispiel oft schneller trägt
als der Verordnungstext. In der Auskunft erscheinen sie als „Anwendungsfall: <Titel>", nicht als
Artikelzitat.

### Englischer Rechtstext — dieselben 2811 Kennungen

**Kontext:** was die englische Oberfläche zitiert | **Eingabe:** `data/raw/en/` und der deutsche Rechtsbestand | **Ergebnis:** `data/processed/corpus.en.jsonl` mit den Kennungen des deutschen Bestands

Die englische Oberfläche zitiert dieselben Einheiten wie die deutsche, nur im englischen Wortlaut:
`data/processed/corpus.en.jsonl`, Baubericht `corpus_report.en.json`, Rohdateien unter
`data/raw/en/`.

* **KI-Verordnung und DSGVO:** die englische Fassung des Amtsblatts, über Cellar mit
  `Accept-Language: eng` geholt (`scripts/fetch_official_journal.py --language en`). Sie trägt
  dieselben Anker wie die deutsche, der Zerleger ist derselbe.
* **Bundesdatenschutzgesetz:** die Übersetzung des Sprachendienstes des Bundesministeriums des
  Innern, `https://www.gesetze-im-internet.de/englisch_bdsg/englisch_bdsg.html`
  (`scripts/fetch_bdsg.py --language en`). Sie berücksichtigt die Änderungen durch das Gesetz vom
  23. Juni 2021; jede Einheit nennt Übersetzer und Stand in ihrem Feld `source`. Verbindlich ist
  allein der deutsche Text.
* **Anwendungsfälle:** die englische Seite der Felder in `data/cases`.
* **Gleiche Kennungen:** Der deutsche Bau entscheidet über Mindestlängen, ob ein kurzer Buchstabe
  eine eigene Einheit wird. Eine Übersetzung ist ein paar Wörter länger oder kürzer und fiele an
  dieser Grenze anders aus; der englische Bau übernimmt deshalb die Kennungen aus `corpus.jsonl`.
  Er setzt den deutschen Bestand voraus und meldet jede abweichende Kennung als Warnung.

## 3. Das Regelwerk — was aus einer Klasse folgt

**Kontext:** die von Hand geschriebenen Regeln hinter Pflichten und Datenschutz | **Eingabe:** die Regeldateien im Textformat YAML unter `data/rules` | **Ergebnis:** was jede Datei enthält und wie viel

Von Hand geschrieben, Stand 31.05.2026:

| Datei | Inhalt | Anzahl |
|---|---|---|
| `data/rules/ai_act_obligations.yaml` | die Pflichten mit Klasse, Rolle, Fundstelle, Frist, Nachweis und Folge bei Verstoß | 57 Pflichten |
| `data/rules/gdpr_review_path.yaml` | der Prüfpfad des Datenschutzrechts in der Reihenfolge, in der er abzuarbeiten ist | 26 Abschnitte |
| `data/rules/ai_act_risk_classes.yaml` | Verbote nach Artikel 5, Transparenz nach Artikel 50, Modelle mit allgemeinem Verwendungszweck, Rollenwechsel, Fristen, Sanktionen | 8 Verbotstatbestände, 5 Fristenstufen, 3 Sanktionsstufen |
| `data/rules/ai_act_purpose_catalog.yaml` | zu jeder Fundstelle derselbe Zweck in Unternehmenssprache; trägt die Suche im Verordnungstext und die ausformulierte Auskunft | 108 Zwecksätze und 21 Gegenzwecke zu 55 Fundstellen |

Jede Pflicht und jeder Abschnitt nennt seine Rechtsgrundlagen als Kennungen. Alle 302
verschiedenen Rechtsgrundlagen stehen im Bestand; `tests/test_classification.py` prüft das bei
jedem Prüflauf, und [operations-guide.de.md](operations-guide.de.md#das-regelwerk-ändern) zeigt
den Befehl, um es von Hand nachzusehen.

## Was nicht enthalten ist

**Kontext:** wonach hier niemand suchen muss | **Eingabe:** der Umfang der Quellen oben | **Ergebnis:** die Liste der Lücken

* **Rechtsprechung.** Keine Entscheidung eines Gerichts, auch nicht des Gerichtshofs der
  Europäischen Union.
* **Weitere Leitlinien und Stellungnahmen.** Keine Leitlinie des Europäischen
  Datenschutzausschusses, des Büros für Künstliche Intelligenz oder einer deutschen
  Aufsichtsbehörde. Von den Dokumenten der Kommission ist nur der Entwurf zur Einstufung von
  KI-Systemen mit hohem Risiko erfasst.
* **Harmonisierte Normen.** Die technischen Normen, über die sich die Vermutung der Konformität
  nach Artikel 40 herstellen lässt, sind nicht erfasst.
* **Delegierte Rechtsakte und Durchführungsrechtsakte** nach dem 31.05.2026.
* **Landesdatenschutzgesetze** und bereichsspezifische Vorschriften (Sozialgesetzbuch,
  Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz und weitere).
* **Andere Sprachen als Deutsch und Englisch.**
