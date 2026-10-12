# AI Act Compliance Helper – Konformitätshelfer zur KI-Verordnung

[English](README.md) | **Deutsch**

**Kontext:** was das Werkzeug tut und wo man anfängt | **Eingabe:** eine Beschreibung Ihres KI-Systems, gegeben als Antworten auf Fragen | **Ergebnis:** seine Risikoklasse nach der KI-Verordnung, mit der genauen Stelle im Gesetz

Rund sechs Fragen, und Sie wissen, in welche Risikoklasse Ihr System der künstlichen
Intelligenz (KI) nach der Verordnung (EU) 2024/1689 zur Festlegung harmonisierter Vorschriften
für künstliche Intelligenz (KI-Verordnung) fällt, mit der genauen Stelle im Gesetz, auf der die
Einstufung beruht. Nicht „Anhang III", sondern „Anhang III Nummer 4 Buchstabe a". Das Werkzeug
arbeitet auf Deutsch und auf Englisch.

![Lizenz](https://img.shields.io/badge/Lizenz-Apache--2.0-blue)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue)
[![Prüfung](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/checks.yml/badge.svg)](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/checks.yml)
[![Pakete](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/packages.yml/badge.svg)](https://github.com/DanielHuette/ai-act-compliance-helper/actions/workflows/packages.yml)

**Projektseite:** <https://konformitaetshelfer.speedofthespirit.dev/>, ohne Anmeldung, ohne
Installation, auch auf dem Handy.
**Für den eigenen Rechner:** [fertige Pakete für Windows, macOS und
Linux](https://github.com/DanielHuette/ai-act-compliance-helper/releases).

## Das ist keine Rechtsberatung

**Kontext:** Grenzen des Werkzeugs | **Eingabe:** keine | **Ergebnis:** worauf Sie sich verlassen dürfen und worauf nicht

Dieses Werkzeug ordnet ein KI-System anhand des Verordnungstextes ein und nennt die
Fundstellen dazu. Es ist **keine Rechtsberatung**, **kein Ersatz für eine Prüfung im
Einzelfall**, und es wird **keine Richtigkeit gewährleistet**. Vor einer Entscheidung mit Geld-
oder Rechtsfolgen ist der geltende Stand bei einer Rechtsanwältin, einem Rechtsanwalt oder der
zuständigen Aufsichtsbehörde zu prüfen. Ausführlich: [docs/liability.de.md](docs/liability.de.md).

## Wie genau ist es?

**Kontext:** gemessene Genauigkeit an einem fremden Maßstab | **Eingabe:** die amtlichen Beispiele der Europäischen Kommission | **Ergebnis:** wie viele Beispiele das Werkzeug so einstuft wie die Kommission

**207 von 217 amtlichen Beispielen** der Europäischen Kommission werden richtig eingestuft,
im Schnitt in **5,3 Schritten** je Fall.

Die Beispiele stammen aus dem Entwurf der Leitlinien der Kommission vom 19. Mai 2026 zur
Einstufung von Hochrisiko-KI-Systemen. Jedes beschreibt ein System und nennt die Wertung der
Kommission. Gemessen wurde, ob der Helfer zur selben Wertung kommt, wenn jemand nur die
Beschreibung kennt. Der Durchlauf lief mit den deutschen Fragen; die englischen Fragen haben
dieselben Kennungen und dieselbe Logik.

Sieben der zehn Abweichungen messen den Helfer nicht: ihre Beschreibungen nennen gar keinen
Anwendungsbereich, und die Ausnahme des Artikels 6 Absatz 3 kommt ohne Bereich zu Recht nie an
die Reihe. Rechnet man sie heraus, sind es **207 von 210**. Das Verfahren und jede einzelne
Abweichung stehen in [data/evaluation/MEASUREMENT.de.md](data/evaluation/MEASUREMENT.de.md).

Was diese Zahl nicht hergibt: kein Jurist hat den Durchlauf gegengelesen.

## Warum Fragen statt Raten

**Kontext:** die Grundentscheidung | **Eingabe:** die Erfahrung aus den ersten Fassungen | **Ergebnis:** warum die Einstufung aus Antworten entsteht

Die erste Fassung ließ den Nutzer sein System beschreiben und erriet daraus die Einstufung,
erst über Stichwortlisten, dann über Bedeutungsvergleich. Auf zwanzig Beschreibungen, wie
Unternehmen sie wirklich einreichen, traf das 11 von 20; nach einer Nacht Arbeit 20 von 20.

Trotzdem war der Ansatz falsch. Ein Jurist fragt fünf bis acht Dinge ab und hat danach
Gewissheit, nicht 98 Prozent. Genaues Raten ist schlechter als Fragen, und der Helfer riet die
Antworten auf Fragen, die er einfach stellen konnte.

Heute entscheidet die Fragefolge. Weil die Antworten vom Nutzer kommen, ist das Ergebnis nicht
wahrscheinlich, sondern richtig, soweit seine Angaben stimmen. Und er sieht, woran es hängt.

## Was drinsteckt

**Kontext:** Umfang der Daten und Prüfungen | **Eingabe:** das Verzeichnis in Fassung 2.0.0 | **Ergebnis:** nachgezählte Mengen

| | |
|---|---|
| Rechtsbestand | 2811 einzeln ansprechbare Textstellen je Sprache: 1386 aus der KI-Verordnung, 1024 aus der Verordnung (EU) 2016/679 (Datenschutz-Grundverordnung, DSGVO), 357 aus dem Bundesdatenschutzgesetz (BDSG), 44 ausgearbeitete Anwendungsfälle |
| Fragefolge | 379 Fragen zu 31 Stellen des Gesetzes, 214 ausdrückliche Ausschlüsse, 187 amtliche Beispiele |
| Belegt | Jede Frage, jeder Ausschluss, jedes Beispiel trägt die Absatznummer der amtlichen Auslegung |
| Zwei Sprachen | Deutsch und Englisch für Webseite, Kommandozeile, Webdienst, Rechtsbestand und Suchbestand; beide Rechtsbestände nutzen dieselben Kennungen |
| Zwei Wege, ein Ergebnis | Webseite und Programm rechnen nachweislich gleich: 400 von 400 Prüfläufen |
| Prüfungen | 641 Prüfungen, davon laufen 610 bei jedem Hochladen ohne Modelle und ohne Netz |

Die Fragen stammen Zeile für Zeile aus dem Entwurf der Leitlinien der Europäischen Kommission
vom 19. Mai 2026. Nichts darin ist ausgedacht.

## Wie ein Durchlauf aussieht

**Kontext:** die Reihenfolge der Fragen | **Eingabe:** Ihre Antworten | **Ergebnis:** ein Befund mit Klasse, Fundstelle und amtlichen Beispielen zum Vergleich

1. **Drei Vorfragen.** Ist es überhaupt ein KI-System nach Artikel 3 Nummer 1? Bewertet es
   Menschen oder nur Firmen? Handeln Sie im Auftrag einer Behörde?
2. **Anhang I.** Steckt Ihr System in einem geregelten Produkt (Maschine, Spielzeug, Aufzug,
   Medizinprodukt, Fahrzeug), oder ist es selbst eines? 15 Produktgattungen.
3. **Acht Bereichsfragen.** Womit hat Ihr System zu tun? Beschäftigung, Geld und
   Daseinsvorsorge, Körpermerkmale, Bildung, Versorgungsnetze, Gerichte und Wahlen, Polizei,
   Grenze. Diese acht Sätze sortieren nur.
4. **Die Rechtsfragen des gewählten Bereichs.** Erst hier wird entschieden.
5. **Die Ausnahme nach Artikel 6 Absatz 3**, nur wenn vorher eine Stelle trägt. Vier
   Bedingungen und die Gegenausnahme Profiling.
6. **Der Befund.** Klasse, Fundstelle, die amtlichen Beispiele zum Vergleichen.

Jede Frage hat drei Antworten: Ja, Nein und **Weiß ich nicht**. Die dritte ist keine
Bequemlichkeit. Ein Werkzeug, das Lebensläufe sichtet, schaltet keine Stellenanzeigen; auf die
Frage, ob eine Anzeige eine konkrete offene Stelle anzeigt, gibt es dort weder Ja noch Nein. Ein
erzwungenes Nein warf nachweislich genau solche Fälle aus der Einstufung.

## Loslegen

**Kontext:** drei Wege zum Werkzeug | **Eingabe:** ein Browser, ein Paket oder der Quelltext | **Ergebnis:** eine laufende Einstufung auf Deutsch oder Englisch

### Im Browser

<https://konformitaetshelfer.speedofthespirit.dev/>: nichts zu installieren. Die Seite in
`web/` besteht aus einer HTML-Datei (Hypertext Markup Language, die Auszeichnungssprache von
Webseiten), zwei JavaScript-Dateien, den Fragedaten und einem Textkatalog je Sprache. Keine
Anmeldung, kein Server, keine Übertragung Ihrer Angaben. Der Schalter **DE | EN** oben rechts
wechselt die Sprache; `?lang=en` in der Adresse öffnet die Seite gleich auf Englisch.

### Als Programm

Paket für Ihr System von der
[Veröffentlichungsseite](https://github.com/DanielHuette/ai-act-compliance-helper/releases)
holen, installieren, starten. Die Bedienoberfläche öffnet sich im Browser, in der Sprache des
Betriebssystems. Kein Python, kein Conda, keine Einrichtung.

Dazu kommt dort die **Volltextsuche im Verordnungstext**: eine Frage in eigenen Worten, und der
Helfer zeigt die Stellen, die sie beantworten. Am besten sucht sie mit dem Suchmodell bge-m3 von
rund 2,3 Gigabyte, das nicht im Paket liegt; das Paket sucht mit einem einfacheren Ersatz. Die
Einstufung braucht kein Modell.

### Aus dem Quelltext

```bash
git clone https://github.com/DanielHuette/ai-act-compliance-helper
cd ai-act-compliance-helper
pip install -e .                 # mit ".[search]" kommt das Suchmodell bge-m3 dazu
compliance-helper --lang de classify "Wir sortieren Bewerbungen mit zugekaufter Software vor" --role deployer
compliance-helper --lang de serve   # Webdienst unter http://127.0.0.1:8000/
```

`python packaging/launch_app.py` startet den Dienst so wie das Paket, auf einem freien
Netzwerkanschluss zwischen 8713 und 8799, und öffnet den Browser.

Ein gebautes Rad (`pip install ai-act-compliance-helper-2.0.0-py3-none-any.whl`) bringt Regeln,
Fragefolge, Anwendungsfälle und beide Korpora mit; nur die Suchbestände bleiben draußen, die Suche
läuft also mit dem Ersatzmodell, bis `compliance-helper build-index --language de` (und
`--language en`) sie gebaut hat. `--verbose` zeigt bei jedem Befehl das Entwicklerprotokoll.

## Die Sprache wählen

**Kontext:** Deutsch und Englisch durchgehend | **Eingabe:** eine Sprachwahl je Seite, Befehl oder Anfrage | **Ergebnis:** Texte, Fundstellen und Suchtreffer in dieser Sprache

| Wo | Wie | Ohne Wahl |
|---|---|---|
| Webseite (`web/`) | Schalter **DE \| EN**, oder `?lang=de` / `?lang=en` in der Adresse | die im Browser gemerkte Wahl, dann die Browsersprache, dann Deutsch |
| Webdienst | `?lang=en` an jeder Seite und jeder Programmierschnittstelle (API, Application Programming Interface), oder das Cookie `lang` | die Sprachangabe des Browsers (`Accept-Language`, höchste Gewichtung zuerst), dann `COMPLIANCE_HELPER_LANG`, dann Deutsch |
| Kommandozeile | `--lang de` oder `--lang en` | Umgebungsvariable `COMPLIANCE_HELPER_LANG`, dann Deutsch |
| Paket | Umgebungsvariable `COMPLIANCE_HELPER_LANG` | Sprache des Betriebssystems |

Die Suche nutzt den Suchbestand der gewählten Sprache: `data/processed/search_index.*` für
Deutsch, `data/processed/search_index.en.*` für Englisch. Beide liegen im Verzeichnis bei.

## Wie die Einstufung zustande kommt

**Kontext:** woher das Ergebnis kommt | **Eingabe:** die Regeldateien | **Ergebnis:** eine feststehende Einstufung, die kein Sprachmodell ändern kann

Aus dem Regelwerk, nicht aus einem Sprachmodell. Drei Textdateien im YAML-Format (YAML Ain't
Markup Language, ein einfaches Textformat für Daten) tragen sie, jeder Text darin auf Deutsch
und Englisch:

- `data/rules/question_flow/*.yaml`: die Fragen, Ausschlüsse und amtlichen Beispiele, je mit
  Absatznummer der Leitlinien
- `data/rules/question_flow_layout.yaml`: die Reihenfolge, also welche Frage wann kommt, welche
  entscheidet und welche nur unterrichtet
- `data/rules/ai_act_obligations.yaml`: welche Pflichten aus einer Klasse und einer Rolle folgen

Ein Sprachmodell formuliert höchstens die Auskunft aus. Es kann das Ergebnis nicht verändern.
Grund: eine erfundene Einstufung kostet Geld und Vertrauen.

### Dass beide Wege gleich rechnen, ist nachgemessen

Die Einstufung läuft an zwei Orten: in `src/compliance_helper/classification/question_flow.py`
für das Programm und in `web/walkthrough.js` für die Webseite. Zwei Fassungen derselben Logik
laufen auseinander; beim Bau dieses Durchlaufs haben Fragefolge und Auswertung genau das getan
und 30 von 217 Beispielen gekostet.

`scripts/check_parity.py` würfelt Antwortmuster und fährt beide Fassungen damit: dieselbe Frage
in derselben Reihenfolge, derselbe Befund. Der Prüflauf baut kein Paket, bevor 400 von 400
Läufen gleich sind.

## Datenstand und Quellen

**Kontext:** woher der Rechtstext kommt | **Eingabe:** amtliche Veröffentlichungen | **Ergebnis:** der datierte Rechtsbestand in beiden Sprachen

| Quelle | Stand | Umfang je Sprache |
|---|---|---|
| Verordnung (EU) 2024/1689 (KI-Verordnung) | Amtsblatt vom 12.07.2024 | 1386 Textstellen |
| Verordnung (EU) 2016/679 (DSGVO) | Amtsblatt vom 04.05.2016 | 1024 Textstellen |
| Bundesdatenschutzgesetz (BDSG) | geltende Fassung auf gesetze-im-internet.de; Englisch: die Übersetzung des Sprachendienstes des Bundesministeriums des Innern | 357 Textstellen |
| Entwurf der Leitlinien der Kommission zur Einstufung von Hochrisiko-KI-Systemen | 19.05.2026 | Grundlage der Fragefolge |

Der amtliche Wortlaut beider Verordnungen wird auf Deutsch und Englisch über Cellar geholt, den
Datendienst des Amts für Veröffentlichungen der Europäischen Union, nicht von der
EUR-Lex-Webseite, die maschinellen Abruf sperrt: `scripts/fetch_official_journal.py --language de|en`.
Das BDSG holt `scripts/fetch_bdsg.py --language de|en`. Verbindlich ist nur das deutsche BDSG;
die englische Übersetzung dient der Information. `compliance-helper build-corpus --language de|en`
baut daraus den Korpus, `compliance-helper build-index --language de|en` seinen Suchbestand.

Der Entwurf der Leitlinien ist **nicht bindend**. Der Helfer sagt diesen Vorbehalt in jeder
Auskunft mit.

## Mitarbeit

**Kontext:** wie man eine Änderung vorschlägt | **Eingabe:** eine Berichtigung, eine Regeländerung oder eine Meldung | **Ergebnis:** eine Änderung, die dieselben Prüfungen besteht wie der Prüfstand auf GitHub

Vor jedem Vorschlag:

```bash
scripts/check_all.sh         # was der Prüfstand prüft
scripts/check_all.sh --all   # zusätzlich Container und Präsentation
```

Das Skript führt dieselben Befehle aus wie der Prüfstand auf GitHub, in derselben Reihenfolge;
die Containerprüfung, die GitHub auf Python 3.13 laufen lässt, läuft hier mit `--all`. Wer nur
einen Teil prüft, merkt einen Fehler erst dort.

Fehler und Wünsche gehören in die Fehlerverwaltung. Es gibt drei Vorlagen, und die Wahl ist
wichtig:

* **Fehler im Programm**: etwas stürzt ab oder tut nicht, was dasteht.
* **Wunsch**: etwas fehlt.
* **Rechtsfehler**: ein Artikelverweis, eine Frist, eine Einstufung oder ein Pflichttext ist
  falsch. Das ist der wichtigste Weg: ein falscher Verweis trifft jeden, der das Werkzeug
  benutzt. Diese Meldungen werden vor allen anderen bearbeitet.

Wie eine Änderung am Regelwerk geprüft wird und was einer Meldung über einen Rechtsfehler
beiliegen muss, steht in [CONTRIBUTING.de.md](CONTRIBUTING.de.md). Sicherheitslücken nicht
öffentlich melden, sondern nach [SECURITY.de.md](SECURITY.de.md).

## Weiterlesen

**Kontext:** die ausführliche Dokumentation | **Eingabe:** keine | **Ergebnis:** wo was steht

| Datei | Inhalt |
|---|---|
| [docs/architecture.de.md](docs/architecture.de.md) | Der Weg einer Frage, Baustein für Baustein, mit den Grenzen des Systems |
| [docs/operations-guide.de.md](docs/operations-guide.de.md) | Benutzen, aufstellen, Rechtsdaten aktualisieren, und was tun, wenn etwas nicht geht |
| [docs/data-sources.de.md](docs/data-sources.de.md) | Jede Quelle mit Datum, Umfang und Lizenzlage |
| [docs/security.de.md](docs/security.de.md) | Wo Daten liegen, was das Gerät verlässt, Schutz gegen untergeschobene Anweisungen |
| [docs/decisions.de.md](docs/decisions.de.md) | Die Architekturentscheidungen mit Begründung und Folgen |
| [docs/liability.de.md](docs/liability.de.md) | Was das Werkzeug nicht ist |
| [docs/presentation.html](docs/presentation.html) | Das Projekt als Foliensatz (im Browser öffnen) |
| [CHANGELOG.md](CHANGELOG.md) | Änderungen je Fassung (auf Englisch) |

## Lizenz

**Kontext:** Nutzungsbedingungen | **Eingabe:** keine | **Ergebnis:** Lizenz des Programms und der mitgelieferten Rechtstexte

Apache License 2.0, siehe [LICENSE](LICENSE). Copyright 2026 Daniel Hütte.

Für die mitgelieferten Rechtstexte gilt die Lizenz dieses Werks nicht; dafür gilt die
Rechtslage der jeweiligen Quelle, siehe [NOTICE](NOTICE).
