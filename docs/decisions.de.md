# Architekturentscheidungen

[English](decisions.md) | **Deutsch**

**Kontext:** die Entscheidungen, die das Projekt prägen, mit ihrem Preis | **Eingabe:** Messungen an den amtlichen Beispielen, den Unternehmensfragen und den Bauprotokollen | **Ergebnis:** je Entscheidung ein Eintrag: Lage, Entscheidung, Folgen

Das Projekt stuft Systeme der künstlichen Intelligenz (KI-Systeme) nach der Verordnung (EU)
2024/1689 der Europäischen Union (EU) zur Festlegung harmonisierter Vorschriften für künstliche
Intelligenz (KI-Verordnung, in Zitaten KI-VO) ein und deckt die Datenschutz-Grundverordnung (DSGVO)
und das Bundesdatenschutzgesetz (BDSG) ab.

Die Einträge stehen nach Gewicht, nicht nach Datum. Ein Eintrag, der nicht mehr gilt, wird nicht
gelöscht, sondern als überholt gekennzeichnet und mit dem Eintrag verknüpft, der ihn ersetzt. Die
Nummern stimmen mit der englischen Fassung überein (E1 hier ist D1 dort).

## E1 — Fragen statt Raten

**Kontext:** eine Risikoklasse lässt sich aus einer Beschreibung erraten oder erfragen | **Eingabe:** Stichwort- und Ähnlichkeitsmessungen früherer Fassungen, 217 amtliche Beispiele | **Ergebnis:** die Fragefolge entscheidet; der Freitextweg bleibt als zweiter Zugang

**Lage.** Die Aufgabe ist, zu einem KI-System die Risikoklasse und die Pflichten zu bestimmen. Der
naheliegende Weg ist, den Nutzer sein Vorhaben beschreiben zu lassen und daraus zu schließen. Genau
so war das Projekt gebaut, in zwei Stufen. Stichwortlisten stuften alle 44 eigenen Anwendungsfälle
richtig ein, aber nur 14 von 20 Beschreibungen, wie Unternehmen sie wirklich schreiben: eine Liste
trifft nur, was vorher jemand aufgeschrieben hat. Der Bedeutungsvergleich (Zwecksätze, ein
Einbettungsmodell und ein Kreuzbewerter) erreichte später 98 von 100 Unternehmensfragen.

**Entscheidung.** Die Einstufung auf der Startseite entsteht aus einer Fragefolge: der Nutzer
beantwortet Fragen über sein System, und daraus folgt der Befund. Gemessen 5,3 Schritte je Fall im
Schnitt. Der Freitextweg (`classification/assessor.py`) bleibt für Kommandozeile,
Schnittstelle im Format JavaScript Object Notation (JSON) und Suchseite, wo nur eine Beschreibung vorliegt; er versieht jedes Ergebnis mit
einer Sicherheit und nennt, was er nicht erkennen konnte.

98 von 100 klingt gut und ist der falsche Maßstab. Ein Jurist fragt fünf bis acht Dinge ab und hat
danach Gewissheit, nicht 98 Prozent. Genaues Raten ist schlechter als Fragen — und geraten wurden
Antworten auf Fragen, die sich einfach stellen lassen: Wofür ist das System bestimmt? Wer setzt es
ein? Entscheidet es über Menschen? Das weiß der Nutzer, und niemand sonst. Dazu drei Dinge, die der
Ratenweg nicht leisten konnte:

* **Nachvollziehbarkeit.** Beim Raten stand am Ende eine Klasse und eine Ähnlichkeitszahl. Jetzt
  nennt der Befund die Antwort, die den Punkt getragen hat, und den Absatz der Leitlinien, der das
  sagt. Der Nutzer sieht, woran es hängt, und kann die Antwort ändern.
* **Herkunft.** Die Zwecksätze des Katalogs waren vom Verfasser formuliert; jede Lücke darin war
  eine Lücke, die niemand sehen konnte. Die Fragen stammen Zeile für Zeile aus dem Entwurf der
  Leitlinien der Kommission vom 19. Mai 2026 und tragen jede eine Absatznummer.
* **Ein fremder Maßstab.** Vorher schrieb der Verfasser sowohl die Regeln als auch die Prüffälle;
  eine hohe Trefferquote hieß nur, dass das Werkzeug mit seiner Lesart übereinstimmt. Die 217
  Beispiele der Leitlinien nennen die Wertung der Kommission. Davon werden **207** richtig
  eingestuft.

**Folgen.**
* Gut: das Ergebnis ist nicht wahrscheinlich, sondern richtig, soweit die Antworten des Nutzers
  stimmen. Kein Modell kann es verändern.
* Gut: die Fragefolge braucht kein Sprachmodell, kein Einbettungsmodell, kein Netz und keinen
  Schlüssel. Sie läuft im Browser.
* Schlecht: der Nutzer muss antworten. Wer nicht weiß, wofür sein System bestimmt ist, muss das
  erst klären — das Werkzeug kann es ihm nicht abnehmen.
* Schlecht: die Pflege wird aufwendiger. Ändern die Leitlinien einen Absatz, ändert sich eine
  Frage, und sie ist an zwei Stellen nachzumessen (siehe
  [E3](#e3--die-ablauflogik-steht-zweimal-da-und-wird-gegeneinander-gemessen)).
* Es gibt zwei Wege zu einer Einstufung, und sie können voneinander abweichen. Die Fragefolge ist
  der gemessene Maßstab; der Freitextweg trägt seine Sicherheit sichtbar mit.

## E2 — Die Fragen stehen in Textdateien, mit Absatznummer an jeder Zeile

**Kontext:** 379 Fragen, 214 Ausschlüsse und 187 Beispiele beruhen auf einem Entwurf, der sich ändern wird | **Eingabe:** der Entwurf der Leitlinien (167 Seiten), die öffentliche Anhörung bis zum 23. Juni 2026 | **Ergebnis:** `data/rules/question_flow/*.yaml` und `question_flow_layout.yaml`, keine Frage im Programmtext

**Lage.** Die Fragen zu 31 Stellen beruhen auf einem Dokument von 167 Seiten, das nicht bindend ist
und sich noch ändern wird: die öffentliche Anhörung zum Entwurf lief bis zum 23. Juni 2026.

**Entscheidung.** Alles davon liegt in `data/rules/question_flow/*.yaml`, die Reihenfolge getrennt
in `data/rules/question_flow_layout.yaml`. Jede Frage, jeder Ausschluss und jedes Beispiel trägt im
Feld `source_ref` die Absatznummer der Leitlinien. Der Programmtext enthält selbst keine Frage und
keinen Artikelverweis.

Wer eine Frage ändert, soll eine Textzeile ändern und nicht Programmtext. Das ist für jemanden
machbar, der die Rechtslage kennt, aber nicht programmiert — und das ist genau die Person, die eine
Änderung der Leitlinien zuerst bemerkt. Eine Textdatei ist außerdem in der Versionsverwaltung
lesbar: eine geänderte Frage ist als Unterschied sichtbar und damit prüfbar. Die Absatznummer ist
kein Schmuck; sie beantwortet die Frage „woher wissen Sie das?". Ohne sie wäre jede Frage eine
Behauptung. Darum gilt: **ohne Absatz keine Frage.**

Reihenfolge getrennt von Inhalt, weil beides verschiedenen Ursprungs ist: die Frage stammt aus dem
amtlichen Text, die Reihenfolge aus der Erfahrung, wie Leute antworten. Die acht Bereichsfragen
zeigen es: sie tragen keine Absatznummer, weil sie nur sortieren.

**Folgen.**
* Gut: eine Änderung der Leitlinien ändert Dateien, nicht Programmtext.
* Gut: dieselben Dateien versorgen Programm und Webseite, sodass beide gleich einstufen.
* Gut: jeder Text ist ein zweisprachiger Wert (`{de, en}`) in derselben Datei; eine Frage kann
  nicht nur in einer Sprache vorhanden sein.
* Schlecht: die Dateien sind nicht schemageprüft. Ein Tippfehler in einem Feldnamen führt nicht zum
  Abbruch, sondern zu einer Frage ohne diese Angabe. Eine Schemaprüfung wäre der nächste sinnvolle
  Schritt.
* Die Verknüpfung zwischen Frage und Rechtstext ist eine Zeichenfolge: ein Punkt nennt
  `AI-Act/annex-III/pt-4-a` als Fundstelle. Fehlte diese Kennung im Korpus, fehlte im Befund der
  amtliche Text zum Nachlesen. `tests/test_question_flow.py` prüft, dass jeder Punkt auf eine
  Einheit des Korpus zeigt.

## E3 — Die Ablauflogik steht zweimal da und wird gegeneinander gemessen

**Kontext:** die Einstufung soll ohne Installation im Browser laufen und im installierten Programm genauso | **Eingabe:** ein Auseinanderlaufen, das 30 von 217 amtlichen Beispielen kostete | **Ergebnis:** `question_flow.py` und `walkthrough.js`, geprüft von `scripts/check_parity.py`

**Lage.** Die Daten sind auf beiden Seiten dieselben, aber die Ablauflogik muss in zwei
Programmiersprachen vorliegen: Python für das Programm, JavaScript für die Webseite. Die Alternative
wäre eine Webseite, die einen Server fragt.

**Entscheidung.** Zwei Fassungen, `src/compliance_helper/classification/question_flow.py` und
`web/walkthrough.js`, und eine Prüfung, die sie gegeneinander fährt. `scripts/check_parity.py`
würfelt Antwortmuster mit festem Startwert und vergleicht Schritt für Schritt: dieselbe Frage in
derselben Reihenfolge, dieselbe Gruppe auf demselben Blatt, derselbe Befund. Der Ablauf, der die
Pakete baut, baut keines, bevor 400 von 400 Läufen gleich sind.

Eine Webseite, die einen Server fragt, überträgt die Angaben des Nutzers. Die Beschreibung eines
KI-Vorhabens verrät Geschäftsinterna, und eine Seite ohne Server hat keinen Betreiber, dem man
vertrauen müsste. Darum rechnet der Browser selbst. Der Preis ist die doppelte Logik, die
gefährlichste Stelle des Projekts. **Zwei Fassungen derselben Logik laufen auseinander** — beim Bau
dieses Durchlaufs haben Fragefolge und Auswertung genau das getan und **30 von 217 amtlichen
Beispielen gekostet**. Eine solche Abweichung sieht man nicht: beide Seiten antworten, nur
verschieden. Darum ist die Prüfung nicht freiwillig, sondern Teil des Paketbaus.

**Folgen.**
* Gut: die Einstufung läuft ohne Server, ohne Anmeldung und ohne Übertragung.
* Gut: die Webseite besteht aus wenigen festen Dateien und lässt sich auf jeden Webserver legen.
* Schlecht: jede Änderung an einer Fassung ist eine Änderung an zwei Fassungen. Wer nur eine
  anfasst, bricht die Gleichheit — die Prüfung merkt es, aber die Arbeit fällt zweimal an.
* Die 400 Läufe sind gesetzt, nicht gemessen: es gibt keine Messreihe, die sagt, ab welcher Zahl
  ein Auseinanderlaufen zuverlässig auffällt.

## E4 — Drei Antworten, nicht zwei

**Kontext:** Ja/Nein wirkt wie die einfachste Fragefolge, und jede Frage der Leitlinien scheint so beantwortbar | **Eingabe:** ein gemessener Fall zur Lebenslaufsichtung, zehn Beispiele zu Anhang III Nummer 2 | **Ergebnis:** die Antwort „Weiß ich nicht" und der Befund `high_risk_conditional`

**Lage.** Eine Fragefolge mit Ja und Nein ist die einfachste Form, und jede Frage der Leitlinien
ist so gestellt, als ließe sie sich mit Ja oder Nein beantworten.

**Entscheidung.** Jede Frage hat drei Antworten: Ja, Nein und **Weiß ich nicht**. Die dritte lässt
die Frage stehen, ohne zu entscheiden; ein Ausschluss greift nur auf eine ausdrückliche Antwort.

Gemessen an einem Fall: Zu Anhang III Nummer 4 Buchstabe a gehört die Frage, ob eine Stellenanzeige
aktiv eine konkrete offene Stelle anzeigt. Ein Werkzeug, das Lebensläufe sichtet, schaltet keine
Anzeigen — darauf gibt es weder Ja noch Nein. Das erzwungene Nein warf einen Fall aus der
Einstufung, der nach dem amtlichen Text klar erfasst ist. Ein Jurist fragt an dieser Stelle nicht
weiter.

Ein zweiter Fall machte eine eigene Befundklasse nötig. Anhang III Nummer 2 verlangt nach Absatz
(190) der Leitlinien, dass der Betreiber förmlich als kritische Einrichtung benannt ist — und Absatz
(191) stellt im selben Atemzug fest, dass diese Benennung dem Anbieter nicht offengelegt werden
muss. Ein Softwarehaus, das Netzleitsysteme verkauft, kann die Frage nicht beantworten. Gemessen
fielen so **zehn amtliche Beispiele** auf „kein hohes Risiko", die die Kommission als hochriskant
führt. Bleibt die Frage offen und trägt der Rest, lautet der Befund `high_risk_conditional` mit dem
Satz, der sagt, woran es hängt.

**Folgen.**
* Gut: Fragen, die auf das eigene System nicht passen, werfen es nicht aus der Einstufung.
* Gut: der Befund kann sagen „alles trifft zu bis auf eines, und das können Sie nicht wissen" —
  eine Auskunft, die der Lage entspricht.
* Schlecht: drei Antworten sind mehr zu bedenken als zwei, in der Oberfläche und in beiden
  Fassungen der Ablauflogik.
* Schlecht: wer „Weiß ich nicht" aus Bequemlichkeit wählt, bekommt einen unentschiedenen Befund
  statt einer Einstufung. Das Werkzeug kann nicht unterscheiden, ob die Frage wirklich nicht passt.

## E5 — Anhang III und Anhang I werden verschieden geprüft

**Kontext:** zwei Wege zum hohen Risiko mit verschiedenem Aufbau | **Eingabe:** Artikel 6 Absätze 1 und 2, Anhang III Nummer 2, gemessene Verluste | **Ergebnis:** drei Prüfformen in `question_flow_layout.yaml`

**Lage.** Artikel 6 Absatz 2 mit Anhang III trifft zu, wenn **einer** von acht Bereichen passt.
Artikel 6 Absatz 1 mit Anhang I verlangt, dass **drei** Dinge zusammenkommen. Und innerhalb des
Anhangs III ist Nummer 2 anders gebaut als die übrigen sieben Bereiche: dort müssen ebenfalls drei
Dinge zusammentreffen.

**Entscheidung.** Drei Prüfformen, in `question_flow_layout.yaml` auseinandergehalten:

* **Aufzählung** — die Punkte eines Bereichs tragen einzeln. Der Regelfall.
* **Bedingungsgruppen** (`annex_i`) — eine Produktgattung aus 15, die Rolle als Sicherheitsbauteil
  oder als Produkt selbst, eine Konformitätsbewertung durch eine dritte Stelle. Innerhalb einer
  Gruppe genügt eine Antwort, über die Gruppen hinweg müssen alle tragen.
* **Verbund** (`compounds`) — für Nummer 2: Versorgungsbereich, benannte kritische Einrichtung und
  eigene Schutzaufgabe, alle drei zusammen.

Anhang I wird vor Anhang III geprüft, weil Artikel 6 Absatz 1 vor Absatz 2 steht. Die falsche
Abbildung ist gemessen teuer. Als Aufzählung gelesen konnte Nummer 2 **überhaupt keinen** Treffer
ergeben, weil keine ihrer Fragen allein zum Treffer führt — zehn amtliche Beispiele. Und bei Anhang
I verlangte der Durchlauf zunächst sowohl „ist Sicherheitsbauteil" als auch „ist selbst das
Produkt" und ließ damit jedes System durchfallen, das selbst ein geregeltes Produkt ist. Artikel 6
Absatz 1 Buchstabe a verlangt das eine **oder** das andere; ist das System selbst das Produkt, ist
die Frage nach dem Sicherheitsbauteil gegenstandslos (`waived_when`).

**Folgen.**
* Gut: jeder Weg wird so geprüft, wie der amtliche Text ihn baut.
* Gut: die Ausnahme nach Artikel 6 Absatz 3 wird nur bei Anhang III gefragt — sie betrifft nur
  diesen Weg, und bei Anhang I sagt der Befund das ausdrücklich.
* Schlecht: drei Prüfformen sind drei Stellen, an denen etwas schieflaufen kann, und sie sind nur
  an den amtlichen Beispielen gemessen, nicht erschöpfend.
* Fünf Fragen der Leitlinien zu Anhang I werden nicht gestellt (`skipped_questions`): sie fassen nur
  zusammen, was der Durchlauf selbst mitzählt, oder verweisen in den Gesetzestext, statt nach dem
  eigenen System zu fragen.

## E6 — Die Pflichten und der Datenschutzpfad bleiben im Regelwerk

**Kontext:** eine Klasse und eine Fundstelle sind noch keine Pflichtenliste | **Eingabe:** 57 Pflichten der KI-Verordnung, 26 Abschnitte des Prüfpfads Datenschutz | **Ergebnis:** Auswahl nach Klasse und Rolle aus `data/rules/`

**Lage.** Was aus einer Klasse an Pflichten folgt, ist eine zweite Frage: 57 Pflichten der
KI-Verordnung und 26 Abschnitte des Prüfpfads zum Datenschutzrecht.

**Entscheidung.** Beides bleibt, wo es war: in `data/rules/ai_act_obligations.yaml` und
`data/rules/gdpr_review_path.yaml`, ausgewählt nach Klasse und Rolle. Jeder Eintrag nennt seine
Rechtsgrundlagen als Kennungen, die im Korpus vorhanden sein müssen.

Die Pflichten hängen am Verordnungstext, nicht an den Leitlinien — sie ändern sich durch andere
Ereignisse als die Fragen und werden darum getrennt gepflegt. Dass 14 der 26
Datenschutzabschnitte immer gelten und 12 an einer Bedingung hängen, ist ebenfalls eine
Entscheidung gegen Vollständigkeit: ohne diese Zuordnung bekäme jeder alle 26 Abschnitte, und das
wäre keine Auskunft mehr, sondern eine Materialsammlung.

**Folgen.**
* Gut: eine Rechtsänderung bei den Pflichten ändert eine Textzeile.
* Gut: jede genannte Rechtsgrundlage ist im Korpus vorhanden (`tests/test_classification.py`), und
  der englische Korpus hat dieselben Kennungen wie der deutsche (`tests/test_corpus_en.py`).
* Schlecht: die Pflichtenliste filtert nach Klasse und Rolle, nicht nach Merkmalen. Wer als
  Betreiber unter Anhang III fällt, bekommt alle Betreiberpflichten dieser Klasse. Nachgemessen am
  9. Oktober 2026: ein Unternehmen, das mit gekaufter Software Bewerbungen vorsortiert, erhielt 14
  Pflichten, darunter die Grundrechte-Folgenabschätzung nach Artikel 27, die nur Einrichtungen des
  öffentlichen Rechts, private Einrichtungen mit öffentlichen Dienstleistungen und Betreiber nach
  Anhang III Nummer 5 Buchstaben b und c bindet. Die Liste ist eher zu lang als zu kurz.
* Schlecht: die abgeleiteten Pflichten sind gegen den Verordnungstext geprüft, aber gegen keine
  fremde Sollvorgabe gemessen — eine amtliche Beispielsammlung dafür gibt es nicht.

## E7 — Vier Suchwege statt einem

**Kontext:** Rechtsfragen werden nach Sinn und nach Wortlaut gestellt | **Eingabe:** Trefferlisten der vier Wege, Rechenzeiten der Neubewertung | **Ergebnis:** Zusammenführung über Rangplätze, Fundstellenweg dreifach gewichtet, Neubewertung von Haus aus aus

**Lage.** Die Volltextsuche ist Beiwerk für Rückfragen, nicht für die Einstufung. „Dürfen wir
Bewerbungen vorsortieren?" fragt nach Sinn — das Gesetz sagt „Einstellung oder Auswahl natürlicher
Personen", kein Wort stimmt überein. „Was steht in Artikel 6 Absatz 3?" fragt nach Wortlaut, und
zwar genau.

**Entscheidung.** Vier Wege gleichzeitig: Vektorsuche für die Bedeutung, Stichwortsuche nach BM25
(„Best Matching 25") für den Wortlaut, die Wortgewichte des Einbettungsmodells für das Dazwischen,
und ein Fundstellenweg, der eine genannte Stelle unmittelbar auflöst. Zusammengeführt wird über die
Rangplätze (*Reciprocal Rank Fusion*): für jeden Treffer wird `1 / (60 + Rangplatz)` je Weg addiert,
der ihn gefunden hat. Punktzahlen zu addieren wäre falsch, weil ein BM25-Wert und ein Kosinusmaß
verschiedene Maßstäbe haben — das Addieren von Metern und Kilogramm. Der Fundstellenweg wiegt
dreifach, weil er kein Schätzwert ist, sondern eine Tatsache. Ein Kreuzbewerter kann die besten 30
neu bewerten.

Eine Vektorsuche allein verliert genaue Fragen: Zahlen sehen für sie fast gleich aus, „Artikel 6"
und „Artikel 9" liegen dicht beieinander. Eine Stichwortsuche allein verliert Fragen in anderen
Worten als denen der Verordnung. Der Fundstellenweg ist der wichtigste und der billigste: wer eine
Stelle nennt, soll sie bekommen und nicht etwas Ähnliches.

**Folgen.**
* Gut: beide Frageformen funktionieren; ein Treffer, den nur ein Weg kennt, fällt nicht heraus;
  fällt ein Weg aus, tragen die anderen weiter.
* Schlecht: vier Wege sind vier Stellen, an denen etwas schieflaufen kann, und das Gewicht 3 des
  Fundstellenwegs ist gesetzt, nicht gemessen.
* Die Zahlen 50 Treffer je Weg, 30 zur Neubewertung und 60 in der Rangfusion sind ebenfalls
  gesetzt und nicht an diesem Bestand gemessen.
* Der Kreuzbewerter brauchte ohne Grafikkarte gemessen 100 Sekunden je Suche. Die Neubewertung ist
  darum von Haus aus aus (`COMPLIANCE_HELPER_RERANK=1` schaltet sie ein); ohne sie bleibt die
  Reihenfolge der Rangfusion, die Suche wird ungenauer, fällt aber nicht aus.
* Anwendungsfälle sind auf ein Drittel der gelieferten Stellen gedeckelt: gemessen machen sie 1,6
  Prozent des Bestands aus, lieferten aber 38 Prozent der Stellen, weil sie die Alltagssprache der
  Fragen teilen.

## E8 — Das Einbettungsmodell läuft auf dem eigenen Rechner

**Kontext:** die Vektorsuche braucht ein Einbettungsmodell, das auch Dienste im Netz anbieten | **Eingabe:** Vertraulichkeit der Beschreibungen, Brauchbarkeit des mitgelieferten Bestands, Bauzeiten | **Ergebnis:** `BAAI/bge-m3` örtlich; nur die ausformulierte Antwort darf ein Modell im Netz nutzen

**Lage.** Schnittstellen im Netz bieten Einbettungen als Dienst an: möglicherweise bessere Treffer,
kein Modell auf dem Rechner, Abrechnung je Anfrage.

**Entscheidung.** Das Einbettungsmodell läuft örtlich: `BAAI/bge-m3`, mehrsprachig, 1024 Zahlen je
Textstück, rund 2,3 Gigabyte. Nur die ausformulierte Antwort kann ein Modell über eine Schnittstelle
übernehmen, und das ist freiwillig.

Zwei Gründe, und beide wiegen schwer. Erstens: wer sein KI-Vorhaben beschreibt, verrät
Geschäftsinterna; eine Einbettung über eine Schnittstelle schickt jede Frage zum Anbieter — auch
dann, wenn am Ende kein Sprachmodell formuliert. Zweitens: der mitgelieferte Bestand muss bei jedem
funktionieren, der das Projekt herunterlädt. Ein Bestand, dessen Vektoren von einem Dienst stammen,
ist ohne Schlüssel bei diesem Dienst nicht abfragbar — die Frage lässt sich nicht in denselben
Zahlenraum bringen, und der Bestand wäre wertlos. Das Modell ist zudem mehrsprachig; der englische
Bestand kam darum ohne zweites Modell aus.

**Folgen.**
* Gut: läuft ohne Schlüssel, ohne Netz, ohne Kosten je Anfrage; die Frage verlässt den Rechner
  nicht.
* Schlecht: 2,3 Gigabyte Modell und ein langer erster Bau, bevor die Suche läuft: gemessen brauchte
  der englische Bestand 4725 Sekunden für 2811 Einheiten auf zwei Prozessorkernen ohne Grafikkarte.
  Das ist eine Hürde — und der Grund, warum die Einstufung ohne Modell auskommen muss.
* Schlecht: die Trefferqualität der großen Dienste ist nicht erreicht, und das ist hier nicht
  gemessen — es gibt keine Messreihe, die die Wege vergleicht.
* Die Suche hat einen Rückfall über Wort-Streuwerte, damit sich die Mechanik ohne Modell
  ausprobieren lässt. `compliance-helper build-index` bricht aber ab, wenn das gewünschte Modell
  fehlt, statt einen Bestand in Ersatzqualität zu schreiben: ein solcher Bestand sieht heil aus und
  liefert still falsche Treffer.

## E9 — Der Rechtsbestand liegt als JSONL im Verzeichnis

**Kontext:** 2811 Rechtseinheiten je Sprache brauchen einen Ort | **Eingabe:** Datenbank, eine Datei je Artikel, eine einzige Datei | **Ergebnis:** `data/processed/corpus.jsonl` und `corpus.en.jsonl`

**Lage.** Die Rechtseinheiten könnten in einer Datenbank liegen, in einer Datei je Artikel oder in
einer einzigen Datei.

**Entscheidung.** Eine Datei je Sprache im Format JSON Lines (JSONL), `data/processed/corpus.jsonl`
(Deutsch) und `data/processed/corpus.en.jsonl` (Englisch), mit einer JSON-Zeile je Einheit. Beide wandern mit in
die Versionsverwaltung.

Die Form ist absichtlich einfach. Eine Zeile je Einheit ist in der Versionsverwaltung lesbar: wer
einen Rechtstext ändert, sieht genau eine geänderte Zeile. Sie lässt sich zeilenweise prüfen, auch
mit Kommandozeilenwerkzeugen, und ohne Hilfsmittel einlesen.

**Folgen.**
* Gut: nachvollziehbare Änderungen, einfache Prüfung, keine Datenbank nötig.
* Gut: wer das Projekt herunterlädt, hat den Rechtstext sofort — ohne Beschaffungslauf, der an
  EUR-Lex scheitern kann.
* Gut: der abgelegte Suchbestand trägt die Kennungen des Korpus, aus dem er gebaut wurde, und wird
  beim Laden abgewiesen, wenn sie nicht mehr passen. Die Anzahl allein genügte nicht: ein Bestand
  aus einem anderen Korpus kann gleich viele Einheiten haben, und dann zeigt jeder Vektor auf die
  falsche Fundstelle, während die Antwort aussieht wie immer.
* Schlecht: die Dateien sind je rund 3 Megabyte groß und wachsen mit jeder Rechtsänderung in der
  Versionsverwaltung mit. Das ist tragbar.

## E10 — Beschaffung getrennt von Verarbeitung

**Kontext:** die Rohquellen kommen aus dem Netz, und das Netz ist unzuverlässig | **Eingabe:** EUR-Lex, die Rechtsdatenbank der EU, antwortet mit dem Status 202 des Hypertext Transfer Protocol (HTTP), leerem Körper und danach einem Captcha | **Ergebnis:** Beschaffungsskripte schreiben nur nach `data/raw`; der Bau geht nie ins Netz

**Lage.** Die Webseite von EUR-Lex antwortet auf Anfragen ohne vollständigen Browser-Kopf mit HTTP
202 und leerem Körper und schickt danach ein Captcha ihrer Firewall.

**Entscheidung.** Die Beschaffung liegt in eigenen Skripten unter `scripts/` und schreibt nur nach
`data/raw` (Englisch nach `data/raw/en`). Der Bau des Korpus liest von dort und geht nie selbst ins
Netz. Geholte Dateien werden nicht erneut geholt, wenn sie vorliegen und eine Mindestgröße
erreichen.

Ein Netzproblem darf den Bestand nicht beschädigen. Wer baut, soll wissen, dass die Eingangsdaten
unverändert daliegen. Und wer die Quellen prüfen will, hat sie als Datei vor sich, nicht als
flüchtige Antwort.

**Folgen.**
* Gut: der Bau ist wiederholbar und läuft ohne Netz; die Rohdateien sind prüfbar.
* Gut: wenn EUR-Lex bremst, scheitert nur die Beschaffung, und das steht im Protokoll statt in
  einem halben Korpus.
* Gut: beide Verordnungen kommen über Cellar, die Dokumentenablage des Amts für Veröffentlichungen,
  aus dem Amtsblatt, auf Deutsch und Englisch. Die Rückfallquelle greift nur ein, wenn der amtliche
  Text für einen Rechtsakt **ganz** fehlt — beigemischt hatte sie ihre Kennungen (`art-4/para-14`)
  neben die amtlichen (`art-4/pt-14`) gestellt. Der Abgleich gegen das Amtsblatt hatte 51 Prozent
  abweichende Einheiten ergeben; Artikel 13 der Datenschutz-Grundverordnung hatte 909 statt 3374
  Zeichen. Siehe [data-sources.de.md](data-sources.de.md).
* Die Mindestgröße als Erkennungsmerkmal ist grob: eine Datei, die groß genug ist, aber inhaltlich
  fehlerhaft, wird nicht erneut geholt.

## E11 — Deutsch im Quelltext, in den Daten und in der Oberfläche (überholt durch E12)

**Kontext:** die ersten Fassungen waren für Mitarbeiter in deutschen Unternehmen geschrieben | **Eingabe:** deutsche Rechtsbegriffe, ein englischer Entwurf der Leitlinien | **Ergebnis:** am 9. Oktober 2026 überholt durch [E12](#e12--englischer-programmtext-deutsch-und-englisch-für-nutzer)

**Lage.** Das Werkzeug richtet sich an Mitarbeiter in deutschen Unternehmen. Der Rechtstext ist
deutsch, die Verordnung legt ihre Begriffe auf Deutsch fest. Die Leitlinien der Kommission liegen
in diesem Entwurf auf Englisch vor.

**Entscheidung (bis Fassung 1.2.4).** Deutsch durchgehend: Bezeichner im Programmtext, Feldnamen
in den Daten, Fragen, Oberfläche, Dokumentation. Die Fragen wurden aus dem englischen Entwurf in
deutsche Alltagssprache übertragen und tragen die Absatznummer des Originals. Begriffe wie
„Betreiber" hin und her zu übersetzen, galt als Gefahr für die rechtliche Schärfe.

**Folgen.**
* Die Begriffe im Programmtext entsprachen der Verordnung; es gab keine Übersetzungsschicht.
* Wer international mitarbeiten wollte, stieß auf eine Hürde, und englischsprachige Nutzer hatten
  keinen Zugang. Das mehrsprachige Einbettungsmodell hätte mehr erlaubt, gebaut war es nicht. Das
  hat E12 geändert.

## E12 — Englischer Programmtext, Deutsch und Englisch für Nutzer

**Kontext:** der rein deutsche Programmtext schloss Mitarbeiter und Nutzer ohne Deutsch aus | **Eingabe:** die verbindliche Begriffsliste der Umbenennung, die amtliche englische Fassung der Verordnung | **Ergebnis:** Fassung 2.0.0 mit englischen Bezeichnern und Textkatalogen je Sprache

**Lage.** E11 hielt den Programmtext nur für Deutschsprachige lesbar und das Werkzeug nur auf
Deutsch nutzbar. Die Sorge dahinter, beim Übersetzen rechtliche Schärfe zu verlieren, trifft für
EU-Recht so nicht zu: KI-Verordnung und Datenschutz-Grundverordnung haben eine amtliche englische
Fassung mit ebenso festgelegten Begriffen (deployer für Betreiber, provider für Anbieter).

**Entscheidung.** Bezeichner, Datenschlüssel, Aufzählungswerte, Dateinamen und Kommentare im
Programmtext sind englisch, nach einer verbindlichen Begriffsliste (Risikoklasse
`high_risk_annex_iii`, Rolle `deployer`, Datei `classification/question_flow.py`). Alles, was ein
Nutzer liest, kommt aus Textkatalogen je Sprache
(`src/compliance_helper/locales/<Sprache>/*.json`, `web/locales/<Sprache>.json`). Die Sprache wird
je Anfrage gewählt (`?lang=`, Cookie, `Accept-Language`) oder je Aufruf (`--lang`,
`COMPLIANCE_HELPER_LANG`); Deutsch bleibt die Vorgabe.

**Folgen.**
* Gut: der Programmtext liest sich wie gewöhnlicher englischer Programmtext; die Rechtsbegriffe
  folgen der amtlichen englischen Fassung, nicht einer Wort-für-Wort-Übersetzung.
* Gut: die deutsche Ausgabe hat sich durch die Umbenennung nicht geändert.
* Schlecht: Fassung 2.0.0 bricht die Verträglichkeit: Paket `compliance_helper`, Befehl
  `compliance-helper`, englische Unterbefehle und Optionen; `--legal-act` nimmt nur `AI-Act`,
  `GDPR`, `BDSG` und `Guidelines`.
* Schlecht: jeder neue Satz braucht zwei Katalogeinträge. `tests/test_i18n.py` und
  `scripts/check_web_locales.py` schlagen bei einem fehlenden Schlüssel oder einem abweichenden
  Platzhalter an, sodass eine Lücke nicht unbemerkt ausgeliefert wird.

## E13 — Zweisprachige Werte in den Daten, Deutsch als maßgebliche Seite

**Kontext:** Fragen, Regeln, Fälle und Messtexte müssen in beiden Sprachen vorliegen | **Eingabe:** die Datendateien, Messungen an den englischen Unternehmensfragen | **Ergebnis:** `{de, en}`-Werte, `pick()` mit Rückfall auf Deutsch, Wortlisten nur in der Sprache der Beschreibung

**Lage.** Die Datendateien tragen den größten Teil des Textes, den ein Nutzer liest. Getrennte
englische Kopien jeder Datei verdoppelten jede Kennung und jede Bedingung, und die beiden Kopien
liefen auseinander wie die beiden Fassungen der Ablauflogik in E3.

**Entscheidung.** Jeder Fließtext ist ein zweisprachiger Wert `{"de": "…", "en": "…"}` in derselben
Datei, neben den sprachneutralen Feldern. `pick()` liefert die eingestellte Seite und fällt auf
Deutsch zurück, den maßgeblichen Text. Wortlisten zum Erkennen sind Listen je Sprache, und eine
Beschreibung wird nur mit den Wortlisten und Zwecksätzen ihrer eigenen Sprache verglichen,
entschieden über Funktionswörter (`description_languages()`); kurzer oder gemischter Text behält
beide.

Der Vergleich über Sprachgrenzen hinweg erzeugte Fehltreffer, weil Wortstämme zufällig in der
anderen Sprache vorkommen (deutsch „note" in englisch „notes", englisch „migration" in einer
Datenmigration). Gemessen an den englischen Unternehmensfragen: nur die eigene Sprache 97 von 100,
beide Sprachen 95 von 100 bei doppelter Rechenzeit.

**Folgen.**
* Gut: eine Datei, ein Satz Kennungen und Bedingungen; eine Frage kann ihre Logik nicht nur in
  einer Sprache ändern.
* Gut: die deutschen Ergebnisse haben sich nicht geändert; die englischen Fälle werden wie die
  deutschen eingestuft (44 von 44), und die langsamen Prüfungen halten beide Sprachen an dieselbe
  Schwelle von 95 von 100 Unternehmensfragen.
* Schlecht: die englischen Texte sind eine Übersetzung der deutschen, von keinem Juristen
  gegengelesen; die Absatznummer an jeder Zeile ist die Gegenprobe.
* Schlecht: einige Marken in der Ablaufdatei vergleichen mit deutschem Fragetext
  (`main_question_contains`); sie müssen deutsch bleiben.

## E14 — Ein englischer Korpus mit denselben Kennungen

**Kontext:** englische Antworten brauchen englischen Rechtstext zum Zitieren | **Eingabe:** das englische Amtsblatt, die amtliche englische Übersetzung des BDSG, der deutsche Korpus als Vorgabe der Kennungen | **Ergebnis:** `data/processed/corpus.en.jsonl` mit denselben 2811 Kennungen wie der deutsche Korpus

**Lage.** Eine englische Antwort, die deutschen Rechtstext zitiert oder eine vom Werkzeug selbst
angefertigte Übersetzung davon, wäre wenig nütze und könnte in die Irre führen.

**Entscheidung.** Der englische Korpus entsteht aus dem englischen Amtsblatt, über Cellar geholt,
mit denselben Ankern und vom selben Zerleger gelesen wie der deutsche; das BDSG kommt aus seiner
amtlichen englischen Übersetzung auf gesetze-im-internet.de, die Anwendungsfälle aus der englischen
Seite von `data/cases`. Kurze Einträge werden über die deutschen Kennungen gehalten statt über
Mindestlängen, sodass beide Korpora genau dieselben Kennungen enthalten; der Bau meldet jede
Kennung, die fehlt oder zu viel ist, und `tests/test_corpus_en.py` vergleicht Kennungen,
Stückzahlen und Stellen mit dem deutschen Korpus.

Alle Sprachfassungen einer EU-Verordnung sind gleichermaßen verbindlich; die englische
KI-Verordnung und die englische Datenschutz-Grundverordnung sind also Recht, keine Übersetzung.
Geteilte Kennungen halten Regeln, Fragefolge und Prüfungen sprachneutral: eine Regel, die
`AI-Act/art-26/para-5` nennt, findet ihren Text in beiden Korpora.

**Folgen.**
* Gut: englische Antworten zitieren den amtlichen englischen Text.
* Gut: ein Regelwerk, eine Fragefolge und eine Prüfreihe dienen beiden Sprachen.
* Schlecht: der englische Bau hängt am deutschen Korpus als Vorgabe und verweigert sich ohne ihn.
* Schlecht: das englische BDSG ist eine Übersetzung des Sprachendienstes des
  Bundesinnenministeriums; rechtlich verbindlich ist nur der deutsche Text.

## E15 — Ein Suchbestand je Sprache, schrittweise neu gebaut

**Kontext:** eine englische Frage braucht englische Stellen und eine englische Stichwortsuche | **Eingabe:** Bauzeiten, Arbeitsspeicher je Bestand | **Ergebnis:** `search_index.*` und `search_index.en.*`, Übernahme unveränderter Vektoren, Zwischenstände

**Lage.** Ein gemeinsamer Bestand ließe die mehrsprachigen Vektoren Vorschriften über
Sprachgrenzen hinweg finden, zeigte aber deutsche Stellen in einer englischen Antwort und verlöre
die Stichwortsuche, die an den Wörtern und Füllwörtern der Sprache hängt. Jeder vollständige Bau
dauert auf einem Prozessor ohne Grafikkarte mehr als eine Stunde.

**Entscheidung.** Jede Sprache hat ihren eigenen Bestand, gebaut aus ihrem eigenen Korpus, mit
eingebettetem Text, Füllwörtern und Zitat für den Kreuzbewerter in dieser Sprache; die Kopfdaten
nennen die Sprache, und das Laden prüft sie. Der Dienst lädt beide Bestände und teilt sich ein
Einbettungsmodell; die Kommandozeile lädt nur ihren eigenen. Ein Neubau übernimmt Vektoren und
Wortgewichte jeder Einheit, deren Kennung und Text-Fingerabdruck gleich geblieben sind, und ein Bau
schreibt alle zwei Stapel einen Zwischenstand.

**Folgen.**
* Gut: die Änderung der Anwendungsfälle bettete 44 Einheiten in 123 Sekunden neu ein statt 2811;
  die Änderung der deutschen Zitierweise 120 Einheiten in 116 Sekunden. Der erste englische Bau
  brauchte 4725 Sekunden.
* Gut: ein Zwischenstand ist nach seinen Texten benannt, sodass ein Lauf mit anderen Texten nie
  einen fremden Zwischenstand übernimmt.
* Schlecht: zwei Bestände im Arbeitsspeicher, je rund 65 Megabyte, und zwei Dateisätze von je rund
  14 Megabyte im Verzeichnis.
* Schlecht: der Fingerabdruck umfasst den Zitatkopf; jede Änderung daran, wie Zitate lauten, bettet
  die betroffenen Einheiten neu ein.

## E16 — Fundstellen werden als Kennung gespeichert und beim Anzeigen ausgeschrieben

**Kontext:** Regeln, Befunde und Belegstellen müssen dieselbe Vorschrift in zwei Sprachen zitieren | **Eingabe:** die Kennungen, die Zählwörter jedes Rechtsakts | **Ergebnis:** `citation_from_id()` in `domain.py`, `readableCitation()` in `web/page.js`

**Lage.** Ausgeschriebene Zitate in den Daten müssten zweimal geschrieben und von Hand gleich
gehalten werden. Die internen Kennungen, unmittelbar gezeigt, sind unlesbar („Buchstabe ua2-a").

**Entscheidung.** Die Daten verweisen auf Vorschriften nur über die Kennung. Das lesbare Zitat
entsteht erst beim Anzeigen, in der eingestellten Sprache und mit dem Zählwort, das der Rechtsakt
verwendet: „Artikel 43 Absatz 1 Unterabsatz 2 Buchstabe a KI-VO" auf Deutsch, „Article 43(1),
subparagraph 2, point (a) AI Act" auf Englisch, „Anhang III Nummer 4 Buchstabe a" und „Annex III
point 4(a)".

**Folgen.**
* Gut: eine Kennung, zwei richtige Zitate; Kennungen bleiben sprachneutral.
* Gut: `tests/test_corpus.py` bildet das Zitat jeder Einheit beider Korpora aus ihrer Kennung und
  vergleicht es mit dem eigenen Zitat der Einheit.
* Schlecht: eine Änderung daran, wie ein Zitat lautet, berührt den eingebetteten Text und verlangt
  darum einen schrittweisen Neubau der betroffenen Einheiten (siehe E15).
