# Betriebsanleitung

[English](operations-guide.md) | **Deutsch**

**Kontext:** drei Leserkreise, drei Teile — lesen Sie den, der auf Sie passt | **Eingabe:** dieses Verzeichnis, ein Browser und für die Teile b und c Python 3.11 oder neuer | **Ergebnis:** ein laufender Helfer in der Sprache Ihrer Wahl und die Befehle, mit denen sein Datenstand aktuell bleibt

* [a) Ich will es nur benutzen](#a-ich-will-es-nur-benutzen)
* [b) Ich stelle es im Unternehmen auf](#b-ich-stelle-es-im-unternehmen-auf)
* [c) Ich pflege die Rechtsdaten und die Fragen](#c-ich-pflege-die-rechtsdaten-und-die-fragen)
* [Wenn etwas nicht geht](#wenn-etwas-nicht-geht)

Die Rechtsakte: die Verordnung (EU) 2024/1689 über künstliche Intelligenz (KI), kurz
**KI-Verordnung**, die **Datenschutz-Grundverordnung** (DSGVO, Verordnung (EU) 2016/679) und das
**Bundesdatenschutzgesetz** (BDSG). Begriffe in dieser Anleitung: die **Fragefolge** ist die Reihe von Fragen, aus der die Einstufung
entsteht; der **Korpus** ist der Rechtstext, zerlegt in Einheiten (ein Absatz eines Artikels, eine
Nummer eines Anhangs, ein Erwägungsgrund); der **Suchbestand** enthält die Zahlenreihen, mit denen
sich der Korpus nach Bedeutung durchsuchen lässt; das **Regelwerk** leitet aus einer Risikoklasse
die Pflichten ab.

---

## a) Ich will es nur benutzen

**Kontext:** den Helfer nutzen, ohne etwas einzurichten | **Eingabe:** ein Browser oder ein heruntergeladenes Paket | **Ergebnis:** eine Einstufung mit der genauen Stelle im Gesetz

### Im Browser — nichts zu installieren

**Kontext:** der schnellste Weg | **Eingabe:** die öffentliche Internetseite | **Ergebnis:** der Durchlauf auf Deutsch oder Englisch

<https://konformitaetshelfer.speedofthespirit.dev/>

Sie beantworten Fragen über Ihr System und bekommen die Einstufung mit der genauen Stelle im
Gesetz. Keine Anmeldung, kein Konto, kein Server: die Seite besteht aus `index.html`, ihren
JavaScript-Modulen, den Fragedaten und je Sprache einer Textdatei. Ihre Angaben werden im Browser
verrechnet und nicht übertragen.

Ein Durchlauf dauert im Schnitt 5,3 Schritte. Jede Frage hat drei Antworten: **Ja**, **Nein** und
**Weiß ich nicht**. Die dritte ist keine Bequemlichkeit — nehmen Sie sie, wenn eine Frage auf Ihr
System nicht passt. Beispiel: Ein Werkzeug, das Lebensläufe sichtet, schaltet keine
Stellenanzeigen; auf die Frage, ob eine Anzeige eine konkrete offene Stelle zeigt, gibt es dort
weder Ja noch Nein. Ein erzwungenes Nein warf gemessen genau solche Fälle aus der Einstufung.

Zu jedem Befund stehen die amtlichen Beispiele der Kommission zur selben Stelle dabei. Lesen Sie
sie: wenn Ihr Fall einem davon gleicht, ist die Einstufung belegt; wenn nicht, sehen Sie, woran es
hängt.

### Die Sprache umschalten

**Kontext:** alle Wege, Deutsch oder Englisch zu wählen | **Eingabe:** ein Klick, eine Angabe auf der Kommandozeile, eine Umgebungsvariable oder ein Anfrageparameter | **Ergebnis:** Texte, Fragen und Fundstellen in der gewählten Sprache

Vorgabe ist überall Deutsch. Die Fundstellen folgen der Sprache: die englische Oberfläche zitiert
den englischen Amtsblatttext derselben Einheit.

| Wo | So wird umgeschaltet | Was gilt, wenn nichts gesetzt ist |
|---|---|---|
| Internetseite (auch unter `/classification/` des Dienstes) | **DE / EN** oben rechts, oder `?lang=en` in der Adresse | die in diesem Browser gespeicherte Wahl, dann die Browsersprache |
| Kommandozeile | `--lang en` oder `--lang de` bei jedem Befehl | die Umgebungsvariable `COMPLIANCE_HELPER_LANG`, dann Deutsch |
| Dienst (`/search` und jeder Pfad unter `/api/`) | `?lang=en` an einer beliebigen Anfrage; das setzt das Cookie `lang` für ein Jahr | das Cookie `lang`, dann die Kopfzeile `Accept-Language` des Browsers (höchstes `q` zuerst), dann `COMPLIANCE_HELPER_LANG`, dann Deutsch |
| Startskripte und das Paket (Konsolenmeldungen und die Seite, die es öffnet) | `COMPLIANCE_HELPER_LANG=en` | die Sprache des Betriebssystems |

`COMPLIANCE_HELPER_LANG` nimmt Kürzel wie `en`, `en-GB` oder `EN`; alles, was weder Englisch noch
Deutsch ist, gilt als Deutsch. Jede Antwort des Dienstes trägt die Kopfzeile `Content-Language` mit
der Sprache, in der sie beantwortet wurde.

### Als Programm auf dem eigenen Rechner

**Kontext:** das fertige Paket, ohne Python | **Eingabe:** das Paket für Ihr Betriebssystem | **Ergebnis:** die Bedienoberfläche im Browser, ohne Netz lauffähig

Von der
[Veröffentlichungsseite](https://github.com/DanielHuette/ai-act-compliance-helper/releases) das
Paket für Ihr System holen:

| System | Datei |
|---|---|
| Windows | Installationsprogramm `.exe` oder das Archiv `.zip` |
| Mac | Abbild `ComplianceHelper-Mac.dmg` — das Programm nach „Programme" ziehen |
| Linux | Archiv `ComplianceHelper-Linux.tar.gz` — entpacken, `ComplianceHelper` starten |

Starten, fertig. Die Bedienoberfläche öffnet sich im Browser unter einer Adresse zwischen
`http://127.0.0.1:8713` und `:8799` — das Programm sucht einen freien Anschluss, damit es nicht an
einer belegten Nummer scheitert. Kein Python, keine Umgebung, kein Nachladen.

Im Paket liegen der Korpus in beiden Sprachen, das Regelwerk, die Fragefolge und die
Anwendungsfälle. Damit läuft die Einstufung sofort und ohne Netz.

Dazu kommt die **Volltextsuche im Verordnungstext** unter `/search`: eine Frage in eigenen Worten,
und das Werkzeug zeigt die Stellen, die sie beantworten. Im Paket vergleicht diese Suche nur
Wörter, weil das Einbettungsmodell (rund 2,3 Gigabyte) und seine Bibliotheken nicht darin liegen.
Die Suche nach Bedeutung braucht den Container oder eine Installation aus dem Quellcode mit Suche
(Teil b).

### Aus dem Quellcode

**Kontext:** den Programmtext unmittelbar laufen lassen | **Eingabe:** Python 3.11 oder neuer und dieses Verzeichnis | **Ergebnis:** der Dienst auf dem eigenen Rechner

```bash
git clone https://github.com/DanielHuette/ai-act-compliance-helper
cd ai-act-compliance-helper
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e .
python packaging/launch_app.py
```

Nur den Dienst, ohne dass sich ein Browser öffnet:

```bash
compliance-helper serve --port 8000
```

Dann liegt die Fragefolge unter `http://127.0.0.1:8000/classification/` und die Volltextsuche unter
`http://127.0.0.1:8000/search`.

Womit das Werkzeug gerade arbeitet und was fehlt:

```bash
compliance-helper status              # Deutsch
compliance-helper status --lang en    # Englisch
```

Keine Farbe in der Ausgabe: `--no-color`, oder `NO_COLOR` setzen. Geht die Ausgabe in eine Datei
statt an ein Fenster, schaltet sich die Farbe von selbst ab. Hinweise für den Nutzer erscheinen in
der gewählten Sprache; das Entwicklerprotokoll der Module (Englisch) nur mit `--verbose`.

Als Paket installiert (`pip install ai-act-compliance-helper-2.0.0-py3-none-any.whl`) bringt das
Werkzeug Regeln, Fragefolge, Anwendungsfälle und beide Korpora mit und findet sie unter
`<Umgebung>/share/ai-act-compliance-helper/`; `compliance-helper classify` geht sofort. Die
Suchbestände gehören nicht zum Paket (28 Megabyte, ohne das 2,3 Gigabyte große Modell wertlos), die
Suche läuft also mit dem Ersatzmodell, bis `compliance-helper build-index` sie gebaut hat. Wer mit
eigenen Daten arbeitet, setzt `COMPLIANCE_HELPER_ROOT` auf den Ordner, der `data/` enthält. Fehlen
die Regeldateien, verweigert das Werkzeug mit einer Meldung, statt alles als minimales Risiko
einzustufen.

---

## b) Ich stelle es im Unternehmen auf

**Kontext:** den Helfer für andere betreiben | **Eingabe:** ein Server oder Container-Rechner, auf Wunsch ein Einbettungsmodell und Schlüssel für ein Sprachmodell | **Ergebnis:** die Internetseite oder der volle Dienst, sicher betrieben

### Was Sie entscheiden müssen, bevor Sie anfangen

**Kontext:** vier Fragen, die den Aufbau bestimmen | **Eingabe:** Ihre Anforderungen | **Ergebnis:** der Aufbau, den Sie brauchen

1. **Reicht die Internetseite?** Für die Einstufung braucht niemand eine Installation. Wer sie im
   Haus anbieten will, legt die Dateien aus `web/` auf einen beliebigen Webserver — mehr ist es
   nicht.
2. **Soll im Verordnungstext gesucht werden?** Dann brauchen Sie das Einbettungsmodell (rund
   2,3 Gigabyte) und je Sprache einen Suchbestand.
3. **Soll ein Sprachmodell die Auskunft ausformulieren?** Ohne läuft alles, nur nüchterner. Mit
   Sprachmodell geht die Frage des Nutzers an den Anbieter dieses Modells — bei einem Vorhaben mit
   Geschäftsinterna ist das eine Entscheidung mit Folgen.
4. **Wer pflegt den Datenstand?** Die Rechtslage ändert sich. Ohne Zuständigkeit veraltet das
   Werkzeug, ohne dass es jemand merkt.

### Die Internetseite im Haus aufstellen

**Kontext:** nur die Einstufung, als feste Dateien | **Eingabe:** der Ordner `web/` | **Ergebnis:** eine Seite, die jeder Webserver ausliefern kann

```bash
python scripts/export_question_flow.py --output web/question_flow.json
```

Danach enthält `web/` alles: `index.html`, `page.js`, `walkthrough.js`, `question_flow.json`,
`locales/de.json`, `locales/en.json` und die Bilder. Diese Dateien brauchen keinen
Anwendungsserver und keine Datenbank. `web/_headers` enthält die Kopfzeilen, mit denen die Seite
ausgeliefert werden soll — Cloudflare Pages liest die Datei von allein, jeder andere Webserver
braucht dieselben Angaben in seiner eigenen Form.

### Als Container — der kürzeste Weg zum vollen Umfang

**Kontext:** Dienst, Suche und Fragefolge in einem Abbild | **Eingabe:** Docker mit Compose | **Ergebnis:** der Dienst unter `http://127.0.0.1:8000/`

```bash
git clone https://github.com/DanielHuette/ai-act-compliance-helper.git
cd ai-act-compliance-helper
cp .env.example .env          # und ausfüllen, soweit nötig
./scripts/start.sh            # Windows: scripts\start.ps1
```

Das Skript prüft die Voraussetzungen und sagt bei jedem Mangel, was zu tun ist, statt eine Meldung
von Docker durchzulassen. Es spricht Englisch, wenn `COMPLIANCE_HELPER_LANG` oder die
Systemsprache Englisch ist, sonst Deutsch. Beide Schreibweisen jedes Schalters gehen:

| Zweck | `start.sh` englisch | `start.sh` deutsch | `start.ps1` | Zweitname in `start.ps1` |
|---|---|---|---|---|
| ohne das große Suchmodell bauen (schnell, die Suche vergleicht dann nur Wörter) | `--small` | `--klein` | `-Small` | `-Klein` |
| ohne Zwischenspeicher neu bauen | `--refresh` | `--refresh` | `-Refresh` | `-Neu` |
| den Dienst anhalten | `--stop` | `--stopp` | `-Stop` | `-Stopp` |
| die Hilfe zeigen | `--help` | `--help` | `Get-Help .\scripts\start.ps1` | |

Von Hand: `docker compose up --build`. Es gibt zwei Abbilder:

* **Volles Abbild** (Vorgabe, `WITH_SEARCH_MODEL=1`): es enthält das Einbettungsmodell
  `BAAI/bge-m3`, damit die mitgelieferten Suchbestände auch ohne Netz taugen, und den
  Kreuzbewerter `BAAI/bge-reranker-v2-m3`, den der Zweckabgleich braucht. Der Zweckabgleich ist an,
  das langsame Umordnen der Suchtreffer bleibt aus (`COMPLIANCE_HELPER_RERANK` leer). Der Bau
  braucht rund 12 Gigabyte freien Plattenplatz, der laufende Dienst rund 5 Gigabyte Arbeitsspeicher
  (`COMPLIANCE_HELPER_MEMORY`, Vorgabe `6g`).
* **Kleines Abbild** (`--klein`, `WITH_SEARCH_MODEL=0`): ohne Modelle. Die Suche vergleicht nur
  Wörter, und der Zweckabgleich ist aus (`COMPLIANCE_HELPER_RERANK=0`), sodass sich die Einstufung
  nur auf die Stichwörter des Regelwerks stützt; `/health` meldet beides als Warnung und den Zustand
  `degraded`. Gut zum Ausprobieren und für die Containerprüfungen, nicht für den Betrieb.

**Daten für den Container neu bauen.** Das Abbild hält Korpus und Suchbestände nur lesbar unter
`/app/data`; neu gebaut wird deshalb außerhalb des laufenden Containers, danach das Abbild. Die
Befehle sind dieselben wie auf dem eigenen Rechner (`compliance-helper build-corpus --language
de|en`, `compliance-helper build-index --language de|en`); sie laufen im Quellordner, danach
`docker compose up --build`. Im Container selbst gehen sie nur auf einer beschreibbaren Kopie:
`COMPLIANCE_HELPER_ROOT` zeigt auf einen Ordner, der `data/` enthält.

Was `docker-compose.yml` und `Dockerfile` festlegen: der Dienst läuft unter dem Nutzer `app`
(Kennung 10001) ohne Verwalterrechte, mit nur lesendem Dateisystem, ohne alle Sonderrechte, ohne
Rechteausweitung und nach außen nur an `127.0.0.1` gebunden. Die Zustandsprüfung fragt `/health`
und wertet `not_ready` als krank — ein Dienst, dessen Korpus fehlt, antwortet zwar, ist aber nicht
betriebsbereit.

### Ohne Container, mit Suche

**Kontext:** der volle Dienst auf einem Arbeitsplatzrechner oder Server | **Eingabe:** Python 3.11 oder neuer, rund 2,3 Gigabyte für das Modell | **Ergebnis:** beide Suchbestände, fertig zum Laden

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[search]"                          # mit Suche
# pip install -e ".[search,llm]"                    # zusätzlich Claude oder GPT
compliance-helper build-index --language de  # deutscher Suchbestand
compliance-helper build-index --language en  # englischer Suchbestand
```

Jede Sprache hat ihren eigenen Suchbestand, gebaut aus ihrem eigenen Korpus; die Oberfläche fragt
den Bestand der eingestellten Sprache. Den deutschen zuerst bauen — der englische Korpus übernimmt
die deutschen Kennungen. Ein Lauf lädt das Modell und rechnet jede Einheit einmal. Von Grund auf
dauert das auf einem Hauptprozessor ohne Grafikkarte mehr als eine Stunde je Sprache (gemessen am
09.10.2026: 4725 Sekunden für die 2811 englischen Einheiten). Der Lauf schreibt sein Protokoll nach
`data/processed/_index_build.log` (englisch: `_index_build.en.log`), legt alle 64 Einheiten einen
Zwischenstand ab und protokolliert am Ende die drei besten Treffer einer Probefrage, damit ein
kaputter Bestand sofort auffällt. Danach liegen in `data/processed/` die Dateien
`search_index.vectors.npy`, `search_index.meta.json.gz` und `search_index.meta.json`, für Englisch
dieselben drei als `search_index.en.*`.

**Der Bau rechnet nur das Nötige.** Ein erneuter Lauf rechnet nur die Einheiten neu, deren Kennung
oder Text sich geändert hat; alle anderen übernimmt er aus dem abgelegten Bestand derselben Sprache
und desselben Modells. Nach einer Änderung an den Anwendungsfällen dauert er deshalb Minuten statt
einer Stunde (gemessen am 09.10.2026: 44 geänderte Einheiten, 123 Sekunden). Alles neu rechnen:

```bash
compliance-helper build-index --language de --from-scratch
compliance-helper build-index --language en --from-scratch
```

Ein kleines Modell zum Ausprobieren, falls 2,3 Gigabyte zu viel sind:

```bash
compliance-helper build-index --language de --model intfloat/multilingual-e5-small
```

Dann muss aber auch die Suche mit diesem Modell laufen — ein Bestand lässt sich nur mit dem Modell
abfragen, mit dem er gebaut wurde. Das wird beim Laden geprüft.

### Den Webdienst betreiben

**Kontext:** Einstellungen des Dienstes | **Eingabe:** Angaben auf der Kommandozeile oder Umgebungsvariablen | **Ergebnis:** ein Dienst, der dort lauscht, wo Sie es wollen

```bash
compliance-helper serve --address 127.0.0.1 --port 8000
```

Dieselben Werte und weitere kommen aus Umgebungsvariablen (Vorlage: `.env.example`):

| Variable | Wirkung |
|---|---|
| `COMPLIANCE_HELPER_HOST`, `COMPLIANCE_HELPER_PORT` | wo der Dienst lauscht (Vorgabe `127.0.0.1`, `8000`) |
| `COMPLIANCE_HELPER_MODEL` | welches Sprachmodell die Auskunft formuliert: `auto`, `anthropic`, `openai` oder `none` |
| `COMPLIANCE_HELPER_EMBEDDING` | welches Einbettungsmodell die Suche nimmt, falls ein Bestand im Speicher gebaut werden muss |
| `COMPLIANCE_HELPER_BUILD_INDEX` | `1` lässt den Dienst einen fehlenden Bestand beim Start mit diesem Modell bauen (dauert ohne Grafikkarte Stunden) |
| `COMPLIANCE_HELPER_RERANK` | `1` lässt den Kreuzbewerter die besten 30 Treffer einer Suche neu ordnen (ohne Grafikkarte rund 100 Sekunden je Suche); `0` schaltet zusätzlich den Zweckabgleich ab, was `/health` als Hinweis meldet; leer (die Vorgabe) lässt die Reihenfolge der Suche, wie sie ist, und den Zweckabgleich an |
| `COMPLIANCE_HELPER_LLM_TIMEOUT` | Sekunden, die ein Sprachmodell für eine Auskunft brauchen darf (Vorgabe 30, ein zweiter Versuch); danach kommt die Auskunft mit einem Hinweis aus dem Regelwerk |
| `COMPLIANCE_HELPER_REQUESTS_PER_MINUTE` | Obergrenze je Adresse für Pfade unter `/api/` (Vorgabe 30) |
| `COMPLIANCE_HELPER_CORS_ORIGINS` | kommagetrennte Herkunftsadressen, die die Schnittstelle aufrufen dürfen |
| `COMPLIANCE_HELPER_LANG` | Sprache der Kommandozeile, der Startskripte und des Pakets; Vorgabe des Dienstes, wenn ein Browser weder Deutsch noch Englisch nennt |
| `COMPLIANCE_HELPER_MAX_BODY_BYTES` | größter Anfragekörper, den der Dienst liest (Vorgabe 131072, also 128 Kibibyte); größere bekommen 413 |
| `COMPLIANCE_HELPER_TRUSTED_PROXIES` | kommagetrennte Adressen vorgeschalteter Vermittler, deren Kopfzeile `X-Forwarded-For` die Anfragegrenze glaubt; ohne Angabe wird sie übergangen |
| `COMPLIANCE_HELPER_ROOT` | Ordner, der `data/` (und `web/`) enthält, für ein eigenes Regelwerk oder eine beschreibbare Kopie für die Datenbauten |
| `HF_HOME`, `HF_HUB_OFFLINE` | Ablage der Modelle; `1` verbietet das Herunterladen von Modellen |

**Standardmäßig lauscht der Dienst nur auf `127.0.0.1`**, also nur auf dem eigenen Rechner. Wer
ihn im Haus anbietet, beachtet:

* Der Dienst hat **keine Anmeldung**. Wer ihn erreicht, kann ihn benutzen. Eine Zugangssperre
  gehört davor — ein vorgeschalteter Server oder das Netz selbst.
* Es gibt eine Obergrenze je Adresse gegen Überlast, aber keine Benutzerverwaltung und keine
  Abrechnung.
* Der Dienst soll **nicht als Verwalter** laufen. `compliance-helper status` weist darauf hin,
  wenn er das tut.
* `GET /health` eignet sich als Prüfpunkt für eine Überwachung und zählt nicht zur Obergrenze.
* Was die Schnittstellen annehmen und zurückgeben, beschreibt der Dienst selbst unter
  `/openapi.json`: `/api/classify`, `/api/search`, `/api/ask`, `/api/questionnaire`,
  `/api/deadlines`.

Der Dienst lädt Korpus, Suchbestand und Regelwerk beider Sprachen beim Start in den Speicher. Der
erste Start dauert deshalb länger als die erste Antwort danach.

### Schlüssel setzen, wenn ein Sprachmodell formulieren soll

**Kontext:** auf Wunsch formuliert Claude oder GPT | **Eingabe:** ein Zugangsschlüssel des Anbieters | **Ergebnis:** vom Modell formulierte Auskünfte; die Einstufung bleibt unverändert

```bash
export ANTHROPIC_API_KEY="…"     # für Claude
export OPENAI_API_KEY="…"        # für GPT
```

Mit `COMPLIANCE_HELPER_MODEL=auto` versucht der Dienst erst Claude, dann GPT. Ist keins
erreichbar, entsteht die Auskunft aus dem Regelwerk und sagt das in einem Hinweis dazu. Die
Einstufung selbst kommt in jedem Fall aus der Fragefolge; ein Sprachmodell kann sie nicht ändern.

Legen Sie Schlüssel nicht in eine Datei im Verzeichnis. `.gitignore` hält `.env` zwar heraus, aber
ein Schlüssel in einer Datei ist ein Schlüssel, der einmal versehentlich mitwandert.

### Die Pakete selbst bauen

**Kontext:** die installierbaren Pakete für Windows, Mac und Linux | **Eingabe:** eine Marke oder ein Lauf von Hand auf GitHub | **Ergebnis:** Pakete an der Veröffentlichung

Der Ablauf `.github/workflows/packages.yml` („Build packages") baut auf drei Maschinen — Windows,
Mac und Linux. Ein Paket enthält die Laufzeitumgebung des Systems, auf dem es gebaut wurde; ein auf
Linux gebautes Windows-Programm gibt es nicht.

* Eine Marke mit `v` davor schieben (etwa `v2.0.0`), dann baut der Ablauf und hängt die Pakete an
  die Veröffentlichung.
* Oder den Ablauf von Hand starten; dann liegen die Pakete als Ergebnis beim Lauf.

Der Ablauf erzeugt zuerst die Fragefolge neu, vergleicht dann die Browser- und die
Python-Umsetzung mit 400 Antwortmustern und baut erst danach. Grund: laufen Programm und
Internetseite auseinander, bekommt derselbe Fall zwei Antworten. Nach dem Bau startet
`packaging/launch_check.py` das Paket und sieht nach, ob es antwortet und die Fragefolge ausliefert
— sonst merkt es erst der erste Nutzer.

Auf dem eigenen Rechner:

```bash
pip install pyinstaller
python scripts/export_question_flow.py --output web/question_flow.json
python scripts/check_parity.py --runs 400
python -m PyInstaller packaging/compliance_helper.spec --noconfirm
python packaging/launch_check.py
```

`scripts/check_parity.py` braucht Node.js, weil es die Browser-Umsetzung ausführt.

### Was Sie den Nutzern sagen müssen

**Kontext:** die Grenzen, die Nutzer kennen müssen | **Eingabe:** der Umfang des Werkzeugs | **Ergebnis:** drei Aussagen zum Weitergeben

Dass es keine Rechtsberatung ist. Dass die Einstufung so gut ist wie die Antworten — wer nicht
weiß, wofür sein System bestimmt ist, muss das erst klären. Und dass die Pflichtenliste eher zu
lang als zu kurz ist: sie enthält alle Pflichten der erkannten Klasse und Rolle, auch solche, die
auf das einzelne Vorhaben nicht passen. Siehe
[architecture.de.md, „Grenzen des Systems"](architecture.de.md#grenzen-des-systems) und
[liability.de.md](liability.de.md).

---

## c) Ich pflege die Rechtsdaten und die Fragen

**Kontext:** die drei Datenbestände aktuell halten | **Eingabe:** neue Leitlinien, ein neuer Rechtstext oder neue Regeln | **Ergebnis:** aktualisierte Dateien, die jede Prüfung bestehen

Drei Dinge veralten, und sie werden getrennt gepflegt:

1. **Die Fragefolge** — die Fragen, Ausschlüsse und Beispiele aus den Leitlinien der Kommission, in
   `data/rules/question_flow/` samt `data/rules/question_flow_layout.yaml`. Sie veraltet, wenn die
   Kommission ihre Leitlinien ändert — und der Entwurf vom 19.05.2026 bekommt noch eine endgültige
   Fassung.
2. **Der Rechtstext** — der Wortlaut der Verordnungen und des Gesetzes. Er wird nach `data/raw`
   (englisch: `data/raw/en`) geholt und zu `data/processed/corpus.jsonl` und `corpus.en.jsonl`
   gebaut.
3. **Das Regelwerk** — die 57 Pflichten und die 26 Abschnitte des Datenschutzpfads in
   `data/rules`. Es veraltet nicht durch einen neuen Textstand, sondern durch neue Rechtsakte und
   Rechtsprechung.

### Eine Frage ändern oder hinzufügen

**Kontext:** die Fragefolge bearbeiten | **Eingabe:** eine Fragedatei in `data/rules/question_flow/` | **Ergebnis:** eine Fragefolge, die Browser und Python gleich verrechnen

Eine Frage gehört in die Datei ihres Bereichs. Pflicht ist:

* `question` — mit `de` und `en`: ein Satz, den jemand über sein eigenes Unternehmen beantworten
  kann. Kein Gesetzeszitat.
* `on_yes` und `on_no` — `covered`, `not_covered` oder `continue`.
* `source_ref` — die Absatznummer der Leitlinien, etwa `"(254)"`. **Ohne Absatz keine Frage.** Eine
  Frage ohne Fundstelle ist eine ausgedachte Frage, und genau das soll es hier nicht geben.

Reihenfolge und Tore stehen getrennt in `data/rules/question_flow_layout.yaml`. Dort wird auch
festgelegt, welche Frage nur unterrichtet (`kind: note`) und welche den Weg lenkt (`kind: gate`).

Nach jeder Änderung — in dieser Reihenfolge:

```bash
python -c "
from compliance_helper.classification.question_flow import Walkthrough
print(Walkthrough.load().figures())
"
python scripts/export_question_flow.py --output web/question_flow.json
python scripts/check_parity.py --runs 400
```

Erwartet, nachgemessen am 09.10.2026: 3 Vorfragen, 4 Hinweise, 31 Stellen, 379 Fragen,
214 Ausschlüsse, 187 Beispiele. Und `400 of 400 runs identical.`

**Der letzte Befehl ist der wichtigste.** Die Ablauflogik steht zweimal da — in
`src/compliance_helper/classification/question_flow.py` und in `web/walkthrough.js`. Beim Bau
dieses Durchlaufs sind die beiden auseinandergelaufen und haben richtige Einstufungen amtlicher
Beispiele gekostet. Wer die eine Fassung anfasst, fasst die andere mit an und misst nach.

Danach gegen die amtlichen Beispiele messen, wie es in
[../data/evaluation/MEASUREMENT.de.md](../data/evaluation/MEASUREMENT.de.md) beschrieben ist.
`scripts/answer_questions.py --answers <Datei>` gibt die nächsten offenen Fragen aus, mit
`--result` den Befund.

### Beide Korpora holen und bauen

**Kontext:** den Rechtstext auf Deutsch und Englisch erneuern | **Eingabe:** Netzzugang zu Cellar und gesetze-im-internet.de | **Ergebnis:** `corpus.jsonl` und `corpus.en.jsonl` mit denselben Kennungen

**Erst Deutsch.** Der englische Korpus übernimmt die Kennungen des deutschen und lässt sich deshalb
erst danach bauen.

```bash
python scripts/fetch_official_journal.py      # KI-Verordnung und DSGVO, deutscher Amtsblatttext
python scripts/fetch_bdsg.py                  # Bundesdatenschutzgesetz
compliance-helper build-corpus --language de --check
compliance-helper build-corpus --language de
```

```bash
python scripts/fetch_official_journal.py --language en
python scripts/fetch_bdsg.py --language en    # amtliche englische Übersetzung
compliance-helper build-corpus --language en --check
compliance-helper build-corpus --language en
```

Die Abrufskripte überspringen Dateien, die schon vorliegen; `--refresh` holt sie neu. `--check`
baut und berichtet, ohne etwas zu schreiben.

Danach `data/processed/corpus_report.json` lesen (englisch: `corpus_report.en.json`). Dort stehen
die Stückzahlen je Quelle und die Warnungen des Laufs. **Die Läufe vom 09.10.2026 haben keine
Warnung.** Steht eine da, ist sie zu lesen und nicht zu übergehen:

| Warnung | Bedeutung |
|---|---|
| `ATTENTION: n duplicate ids WITH DIFFERING TEXT — content is lost here: …` | der Zerleger fand dieselbe Kennung zweimal mit verschiedenem Text; Rechtstext verschwindet |
| `OFFICIAL FULL TEXT MISSING: …` | die Amtsblattdatei fehlt oder ist zu klein; der Bau griff auf eine unvollständige Zweitquelle zurück |
| `IDS DIFFER FROM THE GERMAN CORPUS: …` | der englische Bau passt nicht zu den deutschen Kennungen; Fundstellen zeigten auf andere Einheiten |
| `BDSG MISSING: …` | die Datei des Bundesdatenschutzgesetzes fehlt |

Prüfen Sie, dass die Stückzahlen zu den Erwartungen passen: die KI-Verordnung hat 113 Artikel,
13 Anhänge und 180 Erwägungsgründe, die Datenschutz-Grundverordnung 99 Artikel und
173 Erwägungsgründe; zusammen 2811 Einheiten je Sprache. Diese Zahlen stehen als Erwartung in
`src/compliance_helper/corpus/eurlex.py` und in `tests/test_corpus.py`; weicht ein Lauf ab, steht
das als Warnung im Bericht, und die Prüfungen schlagen fehl.

**Nach jedem Korpusbau die Suchbestände neu bauen,** sonst passen die Zahlenreihen nicht mehr zum
Text. Erst Deutsch, dann Englisch; gerechnet werden nur geänderte Einheiten:

```bash
compliance-helper build-index --language de
compliance-helper build-index --language en
```

### Das Regelwerk ändern

**Kontext:** Pflichten und Datenschutzpfad bearbeiten | **Eingabe:** `data/rules/ai_act_obligations.yaml`, `gdpr_review_path.yaml`, `ai_act_risk_classes.yaml` | **Ergebnis:** Regeln, deren jede Rechtsgrundlage im Korpus steht

Jede Datei trägt im Kopf ein Feld `as_of`, die Pflichten- und die Datenschutzdatei zusätzlich eine
`version_note`. **Beides mit ändern** — der Stand erscheint in jeder Auskunft, und ein falsches
Datum ist schlimmer als ein altes.

Eine Pflicht in `data/rules/ai_act_obligations.yaml` hat diese Felder:

* `id` — eindeutig, wird nicht mehr geändert, weil andere Daten darauf verweisen
* `title` — ein Satz in Alltagssprache (`de` und `en`), kein Gesetzeszitat
* `risk_classes` und `roles` — wer sie wann erfüllen muss
* `legal_basis` — Kennungen wie `AI-Act/art-26/para-1`, **die im Korpus vorhanden sein müssen**
* `citation_text` — das Zitat, wie es in der Auskunft steht
* `applies_from` — der Geltungsbeginn nach Artikel 113
* `action_required`, `evidence_of_compliance`, `on_infringement`, `severity`

Nach einer Änderung prüfen, dass die Dateien lesbar sind und die Zahlen stimmen:

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

Erwartet, nachgemessen am 09.10.2026: Stand 2026-05-31, 57 Pflichten, 26 Abschnitte,
5 Fristenstufen.

Und prüfen, dass jede genannte Rechtsgrundlage im Korpus steht:

```bash
python -m pytest tests/test_classification.py -q -k "rule_citation_exists_in_corpus or every_obligation_cites"
```

Eine Pflicht, deren Rechtsgrundlage im Korpus fehlt, erscheint in der Auskunft ohne den Wortlaut
ihrer Quelle. Das ist kein Absturz, aber ein Mangel. Dasselbe gilt für das Feld `citation` einer
Frage: zeigt es auf nichts, fehlt im Befund der amtliche Text zum Nachlesen.

Jede Änderung gehört in [CHANGELOG.md](../CHANGELOG.md).

### Was sich erfahrungsgemäß ändert

**Kontext:** wo mit Änderungen zu rechnen ist | **Eingabe:** die Entwicklung des Rechts | **Ergebnis:** die Dateien, die dann neu anzusehen sind

* **Die Leitlinien.** Der Entwurf vom 19.05.2026 ist nicht bindend, und die Anhörung lief bis zum
  23. Juni 2026. Kommt die endgültige Fassung, sind die Absatznummern neu zu prüfen — jede Frage
  trägt eine.
* **Fristen.** Artikel 113 nennt die Geltungstermine. Der Vorbehalt dazu steht im Regelwerk, weil
  einzelne Termine zum Datenstand politisch erörtert wurden.
* **Anhang III.** Die Kommission kann die Liste der Hochrisikobereiche durch delegierte Rechtsakte
  ändern. Dann ändern sich die Fragedateien **und** `data/rules/ai_act_risk_classes.yaml`.
* **Bundesdatenschutzgesetz.** Das Regelwerk zitiert nur Teile 1 und 2, also die
  Durchführungsbestimmungen zur Datenschutz-Grundverordnung. Teil 3 gilt nach § 45 nur für
  Behörden im Bereich der Strafverfolgung und ist absichtlich nicht herangezogen.

---

## Wenn etwas nicht geht

**Kontext:** Anzeichen und ihre Abhilfe, mit den Meldungen so, wie das Programm sie ausgibt | **Eingabe:** eine Fehlermeldung oder ein falsches Verhalten | **Ergebnis:** die Ursache und der Befehl, der sie behebt

Meldungen aus den Sprachdateien erscheinen in der eingestellten Sprache; Meldungen für Entwickler
— etwa aus dem Suchbestand und den Bauskripten — gibt das Programm immer auf Englisch aus. Sie
stehen hier im Wortlaut, damit Sie sie wiedererkennen.

### Die Internetseite zeigt „Die Fragen lassen sich nicht laden"

**Kontext:** die Fragedaten fehlen neben der Seite | **Eingabe:** `web/question_flow.json` | **Ergebnis:** eine Seite, die ihre Fragen lädt

Dann fehlt `question_flow.json` neben `index.html`, oder die Datei ist unvollständig. Neu
erzeugen:

```bash
python scripts/export_question_flow.py --output web/question_flow.json
```

Die Seite lädt die Datei mit `fetch("./question_flow.json")`, also aus demselben Ordner. Wird
`index.html` als Datei vom Dateisystem geöffnet statt über einen Webserver ausgeliefert,
verweigern manche Browser diesen Abruf. Dann ein beliebiger kleiner Webserver im Ordner `web/`:

```bash
python -m http.server 8080 --directory web
```

### Die Oberfläche zeigt die falsche Sprache

**Kontext:** eine Sprachwahl, die hängen bleibt | **Eingabe:** die Adresse, das Cookie oder die Browsereinstellung | **Ergebnis:** die gewünschte Sprache

Die Internetseite merkt sich die letzte Wahl im Browser, der Dienst im Cookie `lang`. Einmal
`?lang=de` oder `?lang=en` an die Adresse hängen; beide merken sich dann die neue Wahl. Auf der
Kommandozeile geht `--lang` vor `COMPLIANCE_HELPER_LANG`.

### Internetseite und Programm stufen denselben Fall verschieden ein

**Kontext:** die beiden Umsetzungen des Durchlaufs sind sich uneins | **Eingabe:** die Antworten, die zu beiden Ergebnissen geführt haben | **Ergebnis:** der erste Schritt, an dem sie auseinandergehen

Das ist ein Fehler und gehört gemeldet — mit den Antworten, die zu beiden Ergebnissen geführt
haben. Nachmessen:

```bash
python scripts/check_parity.py --runs 400
```

Für jeden abweichenden Lauf gibt das Skript `--- Run n: Python and browser differ ---` aus und den
ersten Schritt, an dem die beiden auseinandergehen. Häufigste Ursache: `web/question_flow.json` ist
älter als die Fragedateien in `data/rules/`. Erst neu erzeugen, dann vergleichen.

### Der Befund lautet „Bedingt hohes Risiko"

**Kontext:** ein Befund, der kein Fehler ist | **Eingabe:** ein System unter Anhang III Nummer 2 | **Ergebnis:** der Grund für den bedingten Befund

Kein Fehler. Es heißt: alles trifft zu bis auf eine Bedingung, die Sie nicht wissen können. Bei
Anhang III Nummer 2 verlangt Absatz (190) der Leitlinien, dass ein Mitgliedstaat den Betreiber
förmlich als kritische Einrichtung benannt hat — und Absatz (191) stellt fest, dass diese Benennung
dem Anbieter nicht offengelegt werden muss. Rechnen Sie damit, dass ein solcher Betreiber zu Ihren
Kunden gehört, so gelten die Pflichten für Hochrisiko-KI-Systeme.

### Der Dienst startet nicht: „address already in use"

**Kontext:** der Anschluss ist belegt | **Eingabe:** die Anschlussnummer | **Ergebnis:** ein freier Anschluss

Ein anderes Programm lauscht dort. Einen anderen Anschluss nehmen (`--port 8001`) oder nachsehen,
was dort lauscht:

```bash
ss -tlnp | grep 8000
```

Das gepackte Programm sucht sich selbst einen freien Anschluss zwischen 8713 und 8799.

### „bge-m3 requires the FlagEmbedding package"

**Kontext:** das Einbettungsmodell ist nicht installiert | **Eingabe:** die Python-Umgebung | **Ergebnis:** ein lauffähiges Suchmodell oder der bewusste Verzicht darauf

Die Meldung endet mit `Install it with: pip install 'ai-act-compliance-helper[search]'`. Entweder
nachinstallieren:

```bash
pip install -e ".[search]"
```

oder mit dem kleinen Modell arbeiten (`--model intfloat/multilingual-e5-small`), oder ohne Suche
auskommen — die Einstufung braucht kein Modell.

`compliance-helper build-index` bricht dann mit „Das Einbettungsmodell BAAI/bge-m3 ist nicht
verfügbar. Ein Suchbestand in Ersatzqualität wird nicht geschrieben." ab und schreibt nichts. Das ist gewollt: ein Bestand in
Ersatzqualität sieht heil aus und liefert still falsche Treffer. Wer ohne Modell die Mechanik
ausprobieren will, nimmt `--fallback`; der Bestand taugt dann nicht für den Betrieb.

### „The search index was built with X, but Y is loaded"

**Kontext:** Bestand und Modell gehören nicht zusammen | **Eingabe:** der im Bestand vermerkte Modellname | **Ergebnis:** ein passendes Modell oder ein neu gebauter Bestand

Einbettungen verschiedener Modelle sind nicht vergleichbar — jedes Modell rechnet seine eigenen
Zahlenreihen. Entweder dasselbe Modell laden oder den Bestand neu bauen:

```bash
compliance-helper build-index --language de --model <das Modell des Bestands>
```

### „Search index and corpus do not match" oder „The stored search index belongs to a different corpus"

**Kontext:** der Korpus wurde nach dem Suchbestand neu gebaut | **Eingabe:** die Sprache, die die Meldung nennt | **Ergebnis:** ein Bestand, der wieder zu seinem Korpus passt

Das ist die Prüfung, die stillen Schaden verhindert: ohne sie zeigte jede Zahlenreihe auf die
falsche Fundstelle, und die Auskunft sähe aus wie immer. Der Dienst meldet es als „Der abgelegte
Suchbestand (Englisch) fehlt oder passt nicht zum Korpus und wurde nicht genommen (…). Neu bauen: …"
und nennt den Befehl für diese Sprache:

```bash
compliance-helper build-index --language de  # Deutsch
compliance-helper build-index --language en  # Englisch
```

Der Lauf rechnet nur geänderte Einheiten neu und legt alle 64 Einheiten einen Zwischenstand ab.
Bricht er ab — unter 8 Gigabyte Arbeitsspeicher kommt das vor —, einfach erneut starten: er
überspringt, was schon gerechnet ist, und protokolliert, wie viele Einheiten er übernommen hat.

### „Der Suchbestand für Englisch fehlt" oder „The search index was built for language de, but en was requested"

**Kontext:** der Bestand der verlangten Sprache fehlt oder ist vertauscht | **Eingabe:** die Sprache der Anfrage | **Ergebnis:** ein Bestand für diese Sprache

Jede Sprache braucht ihre eigenen Bestandsdateien: `search_index.*` für Deutsch,
`search_index.en.*` für Englisch. Den fehlenden mit dem Befehl bauen, den die Meldung nennt, für
Englisch:

```bash
compliance-helper build-index --language en
```

### „Kein Sprachmodell erreichbar" oder „ANTHROPIC_API_KEY is not set"

**Kontext:** kein Sprachmodell steht bereit | **Eingabe:** die Schlüssel in der Umgebung | **Ergebnis:** Auskünfte aus dem Regelwerk oder ein Schlüssel für ein Modell

Kein Fehler, sondern eine Feststellung. Ohne Schlüssel läuft alles weiter; die Auskunft kommt dann
unmittelbar aus dem Regelwerk und trägt den Hinweis „Diese Auskunft ist ohne Sprachmodell
entstanden und deshalb knapper formuliert." Wer einen Schlüssel setzen will, siehe Teil b. Wer den
Hinweis abstellen will, setzt `COMPLIANCE_HELPER_MODEL=none`.

### „Zu viele Anfragen von dieser Adresse"

**Kontext:** die Obergrenze greift | **Eingabe:** die Zahl der Anfragen je Minute | **Ergebnis:** eine Antwort nach der Wartezeit oder eine höhere Grenze

Der Dienst erlaubt unter `/api/` standardmäßig 30 Anfragen je Minute und Adresse und antwortet
darüber mit dem Statuscode 429 des Hypertext Transfer Protocol (HTTP) und der Kopfzeile `Retry-After`. Die Grenze lässt sich mit
`COMPLIANCE_HELPER_REQUESTS_PER_MINUTE` anheben.

### „Korpus fehlt. Erst bauen"

**Kontext:** der Rechtstext ist nicht gebaut | **Eingabe:** `data/processed/` | **Ergebnis:** ein ladbarer Korpus

Bauen wie in Teil c beschrieben, Deutsch zuerst. Auf der Kommandozeile lautet die Meldung „Es fehlt
eine Datei: Korpus fehlt (Deutsch): <Pfad>. Erst bauen: compliance-helper build-corpus --language
de"; für Englisch nennt sie `--language en`.

### EUR-Lex liefert nur ein paar Kilobyte

**Kontext:** die falsche Adresse wurde abgefragt | **Eingabe:** das Abrufskript | **Ergebnis:** der vollständige Amtsblatttext

Die **Webseite** von EUR-Lex antwortet ohne vollständigen Browser-Kopf mit dem HTTP-Status 202 und
null Byte und schickt danach ein Captcha ihrer Firewall. Davor hilft keine Wartezeit und keine
Kopfzeile.

Der amtliche Text kommt darum nicht von der Webseite, sondern aus der Ablage **Cellar**, vor der
diese Firewall nicht steht:

```bash
python scripts/fetch_official_journal.py
```

Das Skript holt beide Verordnungen über `http://publications.europa.eu/resource/cellar/<Kennung>`
mit `Accept: application/xhtml+xml` und `Accept-Language: deu` (`eng` mit `--language en`) und
verwirft jede Antwort unter der Mindestgröße mit `attempt n: only … bytes, expected at least … —
discarded`. Die Kennungen stehen in [data-sources.de.md](data-sources.de.md).

### Die Prüfreihe wird mitten im Lauf abgebrochen („Killed")

**Kontext:** zu wenig Arbeitsspeicher | **Eingabe:** die Prüfreihe | **Ergebnis:** ein vollständiger Prüflauf

Mehrere Prüfungen laden beide Korpora und bauen Suchbestände im Speicher; unter 8 Gigabyte geht
die ganze Reihe womöglich nicht in einem Lauf durch. Dann dateiweise prüfen:

```bash
for f in tests/test_*.py; do python3 -m pytest "$f" -q; done
```

### ruff oder mypy melden etwas

**Kontext:** die statischen Prüfungen schlagen an | **Eingabe:** der Programmtext | **Ergebnis:** ein sauberer Lauf

Dann ist etwas zu beheben. `ruff check .`, `ruff format --check .` und `mypy src` sollen ohne
Beanstandung durchlaufen, und die Prüfungen auf GitHub brechen bei jedem Befund ab. Ein Lauf, der
dauerhaft rot ist, wird nicht mehr gelesen — dann fällt auch der erste echte Fehler nicht auf. Jede
Ausnahme wird in `pyproject.toml` begründet.

Alles auf einmal, mit denselben Befehlen und in derselben Reihenfolge wie die Prüfungen auf GitHub
(die Containerprüfung nur mit `--all`):

```bash
scripts/check_all.sh
scripts/check_all.sh --all   # zusätzlich Container und Präsentation
```

### Der Dienst antwortet, aber die Suche findet nichts Brauchbares

**Kontext:** die Suche läuft ohne echtes Modell | **Eingabe:** `compliance-helper status` | **Ergebnis:** wieder eine Suche nach Bedeutung

`compliance-helper status` ansehen. Nennt der Abschnitt zum Suchbestand das Einbettungsmodell
`hashing-fallback`, wurde kein abgelegter Bestand geladen; die Warnung lautet „Die Suche läuft mit
dem Ersatzmodell 'hashing-fallback'. Es vergleicht nur Wörter, nicht Bedeutung — die Fundstellen
sind deutlich schlechter." Abhilfe:

```bash
pip install -e ".[search]"
compliance-helper build-index --language de
compliance-helper build-index --language en
```

Die Einstufung ist davon nicht betroffen — sie braucht keinen Suchbestand.
