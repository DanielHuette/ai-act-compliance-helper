# Bauplan: der Konformitätshelfer in einem Durchgang

Dieses Dokument ist ein Auftrag an einen Programmierassistenten. Wer es ihm
vorlegt, bekommt den **EU AI Act und DSGVO Konformitätshelfer** gebaut — den
Rechtsbestand, die Fragefolge, die Einstufung, die Suche, die Oberflächen, die
Pakete, die Messung und die Prüfungen — ohne eine einzige Rückfrage.

Es ist zugleich die Beschreibung dessen, was hier steht: jede Zahl darin ist an
diesem Projekt nachgemessen, und jede Regel ist aus einem Fehler entstanden,
der wirklich gemacht wurde.

| | |
|---|---|
| **Ergebnis** | 2.811 Rechtsstellen · 379 Fragen zu 31 Stellen des Gesetzes · 57 Pflichten · 44 Anwendungsfälle · 207 von 217 amtlichen Beispielen richtig eingestuft · Webseite, Programm für Windows, Mac und Linux, Container, Präsentation |
| **Voraussetzung** | Python 3.11 oder neuer, Node (für den Abgleich der beiden Rechenwege), Netzzugang zu EUR-Lex und Hugging Face, Docker, rund 20 Gigabyte Platte |
| **Nicht vorausgesetzt** | Rechtskenntnis des Assistenten — die Rechtsfragen stehen unten als Prüfkriterien |

---

## Wie dieser Bauplan zu benutzen ist

Kopieren Sie den Abschnitt **„Der Auftrag"** vollständig in Ihren Assistenten.
Alles darüber und darunter ist Erläuterung für Sie, nicht für ihn.

Der Auftrag ist so geschrieben, dass keine Frage offenbleibt: Jede Entscheidung,
die sonst eine Rückfrage auslösen würde, ist vorweg getroffen und begründet. Die
Begründungen stehen dabei, weil ein Assistent eine Regel ohne Grund an der
erstbesten Gelegenheit aufgibt.

---

## Der Auftrag

> Baue ein Werkzeug, das Unternehmen sagt, in welche Risikoklasse der
> KI-Verordnung (EU) 2024/1689 ihr KI-System fällt — und auf welcher Stelle im
> Gesetz die Antwort beruht. Es heißt **EU AI Act und DSGVO
> Konformitätshelfer**. Arbeite die Stufen unten der Reihe nach ab. Frage
> nichts — jede Entscheidung ist hier getroffen. Halte dich an die elf
> Grundsätze; sie stehen über jeder Einzelanweisung.

### Die elf Grundsätze

**1. Gefragt, nicht geraten.** Die Einstufung entsteht aus Fragen, die der
Nutzer beantwortet, und aus Regeln in Textdateien — nie aus einem Sprachmodell.
Ein Sprachmodell formuliert höchstens die Auskunft aus; es kann das Ergebnis
nicht verändern.

Diese Reihenfolge ist das Ergebnis einer Messung. Die erste Fassung ließ den
Nutzer sein System beschreiben und erriet die Einstufung daraus — zuerst über
Wortlisten, dann über Bedeutungsvergleich. Auf hundert Beschreibungen, wie
Unternehmen sie wirklich einreichen, kam sie damit auf 98. Trotzdem war der
Ansatz falsch: ein Jurist fragt fünf bis acht Dinge ab und hat danach
Gewissheit, nicht 98 Prozent. Genaues Raten ist schlechter als Fragen — und
geraten wurden Antworten auf Fragen, die man stellen kann. Weil die Antworten
vom Nutzer kommen, ist das Ergebnis nicht wahrscheinlich, sondern richtig,
soweit seine Angaben stimmen. Und er sieht, woran es hängt.

**2. Jede Frage trägt ihre Fundstelle.** Keine Frage, kein Ausschluss, kein
Beispiel ohne die Absatznummer der amtlichen Auslegung, aus der sie stammt. Eine
Frage ohne Fundstelle ist eine Behauptung über das Gesetz.

**3. Nie schätzen, immer messen.** Keine Zahl in Programmtext, Dokumentation
oder Präsentation, die nicht gemessen wurde. „Rund 2.700 Einheiten" ist keine
Angabe, sondern ein Versäumnis.

**4. Jeder eigene Fehler wird zur Prüfung.** Wer einen Fehler behebt, schreibt
eine Prüfung mit dem Fehler im Namen und der Ursache im Beschreibungstext.
Beispiel: `test_trifft_nicht_zu_wirft_den_fall_nicht_aus_der_einstufung` — ein
erzwungenes Nein hatte erfasste Fälle aus der Einstufung geworfen.

**5. Rechtsfragen gehören in Daten, nicht in Programmtext.** Welche Frage
welchen Buchstaben des Anhangs III trägt, ist eine Rechtsfrage. Sie steht in
einer YAML-Datei, die ein Jurist ohne Programmierkenntnis ändern kann.

**6. Was offen ist, wird genannt — nicht weggelassen.** Kann der Nutzer eine
Bedingung nicht wissen, lautet der Befund „bedingt" und sagt, wovon es abhängt.
Ein Nein wäre dort eine falsche Auskunft, ein Ja eine erfundene.

**7. Nichts verlässt das Gerät, außer der Nutzer will es.** Rechtsbestand,
Regelwerk, Fragefolge und Suche liegen lokal. Die Webseite rechnet im Browser;
die Angaben des Nutzers gehen nirgendwohin. Ein Sprachmodell wird nur
angesprochen, wenn ein Schlüssel hinterlegt ist, und das steht in der
Oberfläche.

**8. Keine Datei, die beim Laden Code ausführen kann.** Kein `pickle`, kein
`allow_pickle`, keine `eval`. Was mit dem Repository ausgeliefert wird, kommt
beim Nutzer über Kopien und Spiegel an — eine veränderte Kopie darf falsche
Treffer verursachen, aber keinen fremden Code starten.

**9. Deutsch, durchgehend.** Modulnamen, Feldnamen, Kommentare,
Fehlermeldungen, Oberfläche. Das Werkzeug erklärt deutsches und europäisches
Recht auf Deutsch; ein Mischwort wie `EingabeError` bricht die Benennung des
ganzen Projekts.

**10. Keine Rechtsberatung, und das wird gesagt.** Jede Auskunft nennt den
Datenstand, den Vorbehalt, dass die Leitlinien ein Entwurf sind, und den Satz,
dass über den Einzelfall ein Mensch mit Zulassung entscheidet.

**11. Nichts halb.** Bricht die Arbeit ab, bleibt sie offen, nicht halb fertig.
Ein Lauf, der eine Stunde rechnet, legt Zwischenstände ab.

### Stufe 1 — Rechtstexte und Leitlinien beschaffen

Hole den amtlichen deutschen Volltext aus EUR-Lex:

- KI-Verordnung: CELEX `32024R1689`
- Datenschutz-Grundverordnung: CELEX `32016R0679`

**Fallstrick, der Stunden kostet:** EUR-Lex antwortet auf einen Aufruf ohne
vollständigen Browser-Kopf mit HTTP 202 und null Bytes — kein Fehler, nur
nichts. Setze `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`,
`Sec-Fetch-User`, `Upgrade-Insecure-Requests` und `Accept-Encoding: identity`.
Kommt trotzdem eine Seite von rund 2 Kilobyte zurück, ist es ein Captcha der
Firewall: nimm dann `dsgvo-gesetz.de` artikelweise als zweite Quelle und
**schreibe in `docs/datenquellen.md`, welcher Text woher stammt.** Den amtlichen
Wortlaut holst du am besten über Cellar, den Datendienst des Amts für
Veröffentlichungen — nicht über die EUR-Lex-Webseite.

Hole außerdem das Bundesdatenschutzgesetz von `gesetze-im-internet.de`.

**Und hole den Entwurf der Leitlinien der Europäischen Kommission vom
19. Mai 2026 zur Einstufung von Hochrisiko-KI-Systemen.** 167 Seiten: 148 zu
Anhang III, 13 zu Anhang I, 6 zu den allgemeinen Grundsätzen. Aus diesem
Dokument entsteht in Stufe 3 die Fragefolge, und ohne es gibt es nichts zu
bauen. Es ist durchgehend in Absätze mit Nummern gegliedert — diese Nummern sind
später die Fundstelle jeder einzelnen Frage.

Jedes Beschaffungsskript lässt nur `https` durch (eine eigene kleine Prüfung
vor dem Aufruf) und legt die Rohdateien unverändert ab.

### Stufe 2 — Zerlegen

Zerlege **ausschließlich an der Gliederung des Dokuments**, nie an Textmustern.

**Der Fehler, den jeder einmal macht:** Ein Zerleger, der nach „Artikel" sucht,
findet 132 statt 113 Artikel — ein Querverweis im Fließtext („… nach Artikel
99 …") sieht aus wie ein Artikelanfang, und Artikel 5 wird 31.828 Zeichen lang.
EUR-Lex trägt `div#art_6`, `div#006.003` (Artikel 6 Absatz 3), `div#anx_III`,
`#rct_71`. Daran wird getrennt. Das Bundesdatenschutzgesetz trägt
`div.jnnorm` mit `.jnenbez`, `.jnentitel`, `.jnhtml`.

Jede Einheit bekommt eine Kennung in genau dieser Form:

```
KI-VO/art-6            DSGVO/art-13/abs-1-a       BDSG/par-26/abs-1
KI-VO/art-6/abs-3      KI-VO/anh-III/nr-4-a       KI-VO/art-3/nr-39
KI-VO/erw-71           KI-VO/anh-I/nr-A-11        KI-VO/anh-VIII/nr-A-1
```

**Zerlege die Anhänge bis zum Buchstaben, nicht bis zur Nummer.** Anhang III
nennt acht Bereiche, aber die Einstufung hängt nicht am Bereich, sondern am
Buchstaben darunter: Nummer 4 Buchstabe a trifft die Einstellung, Buchstabe b
die Arbeitsbedingungen — zwei verschiedene Sachverhalte unter einer
Überschrift. Wer nur die Nummer erfasst, kann einen Fall nicht auf die Stelle
zurückführen, die ihn trägt, und hat für die Einstufung acht sehr ähnlich
formulierte Texte statt vierundzwanzig unterscheidbarer. Die Fragefolge in
Stufe 3 ist nach diesen Buchstaben aufgebaut; ohne sie lässt sie sich nicht
verankern.

**Die Begriffsbestimmungen gehören einzeln erfasst.** Artikel 3 hat 68 Nummern,
Artikel 4 der Datenschutz-Grundverordnung 26. `KI-VO/art-3/nr-39` ist die
Begriffsbestimmung der Emotionserkennung, und auf genau diese Nummer stützt sich
die Unterscheidung, ob eine Stimmungsauswertung verboten ist oder nicht. Auf
einen ganzen Artikel 3 zu verweisen hieße, den Nutzer 68 Nummern durchlesen zu
lassen.

**Drei Fallen in den Aufzählungstabellen von EUR-Lex:**

* *Die Zählung steht nicht immer in der ersten Zelle.* Eingerückte
  Aufzählungen haben davor eine leere Zelle, die die Einrückung trägt. Anhang I
  ist so gebaut. Wer blind `zellen[0]` liest, findet nichts und verliert den
  ganzen Anhang — die 20 Rechtsakte, auf die Artikel 6 Absatz 1 verweist.
  Überspringe führende leere Zellen.
* *Abschnittsköpfe setzen die Zählung zurück.* Anhang I hat zwei Abschnitte
  (A mit den Nummern 1 bis 12, B mit 13 bis 20), Anhang VIII drei, und jeder
  zählt wieder ab 1. Ohne den Abschnitt in der Kennung trägt eine Nummer
  mehrfach denselben Namen, und der Rest geht beim Entdoppeln verloren. Ein
  Abschnittskopf heißt „Abschnitt A — …", „Abschnitt 1" oder „1. Schengener
  Informationssystem". Eine **zweite** Überschrift unter dem Abschnittskopf darf
  den Abschnitt nicht löschen — Anhang XI hat das.
* *Verschachtelte Aufzählungen.* Artikel 5 Absatz 1 Buchstabe c enthält „i)",
  „ii)" — im Fließtext sieht „i)" wie der Buchstabe i aus, und denselben
  Buchstaben gibt es dort auch echt. Darum über die Tabellenstruktur gehen,
  nie über den Fließtext.

**Baue die Entdopplung so, dass sie den Verlust nennt.** Zwei Einheiten mit
derselben Kennung und *verschiedenem* Text bedeuten, dass Inhalt verschwindet.
Die Warnung muss die betroffenen Kennungen aufzählen — eine Zahl allein sagt
nicht, wo zu suchen ist. Der Lauf muss am Ende **ohne Warnung** durchgehen.

**Zielzahlen — sie sind Prüfkriterien, nicht Angaben:**

| Rechtsakt | Artikel | Anhangseinheiten | Erwägungsgründe | Einheiten |
|---|---:|---:|---:|---:|
| KI-Verordnung | 113 | 164 | 180 | 1.386 |
| Datenschutz-Grundverordnung | 99 | — | 173 | 1.024 |
| Bundesdatenschutzgesetz | — | — | — | 357 |
| Anwendungsfälle | — | — | — | 44 |
| **Zusammen** | | | | **2.811** |

Darin enthalten: die 8 Nummern und 24 Buchstabenpunkte des Anhangs III, die
20 Rechtsakte des Anhangs I in zwei Abschnitten, die 13 Anhänge der
KI-Verordnung als Stammeinheiten, 68 Begriffsbestimmungen des Artikels 3 und
26 des Artikels 4 der Datenschutz-Grundverordnung.

Stimmt eine Zahl nicht, ist der Zerleger falsch — nicht die Zahl.

Baue daraus `data/processed/corpus.jsonl`, eine Zeile je Einheit, und einen
Befund mit den gezählten Beständen.

### Stufe 3 — Die Fragefolge

Das ist das Herz. Lies den Entwurf der Leitlinien Absatz für Absatz und
übersetze ihn in Fragen, die ein Mitarbeiter über sein eigenes System
beantworten kann. Nichts darin wird ausgedacht: jede Zeile hat einen Absatz als
Fundstelle.

Die Daten liegen in `data/rules/question_flow/*.yaml` — eine Datei je Bereich des
Anhangs III, eine für Anhang I, eine für die Vorfragen und den Filter — und in
`data/rules/question_flow_layout.yaml`, die die Reihenfolge bestimmt.

**Der Aufbau einer Stelle.** Jede Stelle des Gesetzes („Punkt") trägt:

* `fundstelle` — die Kennung aus Stufe 2, etwa `KI-VO/anh-III/nr-4-a`
* `hauptfrage` — ein Satz, der entscheidet, ob diese Stelle überhaupt in Frage
  kommt
* `folgefragen` — die Rechtsfragen darunter, jede mit `bei_ja` und `bei_nein`
  (`erfasst`, `nicht_erfasst` oder `weiter`) und mit `beleg`
* `erfasst` und `nicht_erfasst` — was die Leitlinien ausdrücklich einbeziehen
  und ausnehmen, als Text mit Beleg; das ist, was der Nutzer am Ende liest
* `beispiele` — die amtlichen Beispiele zu dieser Stelle, zum Vergleichen

**Drei Antworten, nicht zwei: Ja, Nein und „Weiß ich nicht".** Die dritte ist
keine Bequemlichkeit, sie ist gemessen. Zu Anhang III Nummer 4 Buchstabe a
gehört nach Absatz (251) die Frage, ob eine Stellenanzeige aktiv eine konkrete
offene Stelle anzeigt; ein Nein darauf schließt aus. Für ein Werkzeug, das
Lebensläufe sichtet, gibt es darauf weder Ja noch Nein — es schaltet keine
Anzeigen. Das erzwungene Nein warf genau solche Fälle aus der Einstufung, obwohl
sie nach dem amtlichen Text klar erfasst sind. Ein Jurist fragt an dieser Stelle
nicht weiter. **Ein Ausschluss greift nur auf eine ausdrückliche Antwort, nie
auf ein Offenlassen.**

**Stelle keine Frage, deren Antwort das Programm selbst kennt.** Die Leitlinien
fragen an mehreren Stellen „Haben Sie alle sechs vorstehenden Fragen mit Nein
beantwortet?". Das mitzuzählen ist Arbeit des Rechners, nicht des Nutzers, und
eine Fehlerquelle, die der Rechner nicht hat. Wirf solche Fragen beim Einlesen
heraus.

**Acht Sätze, die nur sortieren.** Vor den Rechtsfragen steht eine Frage je
Bereich des Anhangs III: Beschäftigung, Geld und Daseinsvorsorge,
Körpermerkmale, Bildung, Versorgungsnetze, Gerichte und Wahlen, Polizei, Grenze.
Sie entscheiden nichts. Ohne sie stünden 31 Rechtsfragen auf einem Blatt.

**Drei Vorfragen.** Ist es überhaupt ein KI-System nach Artikel 3 Nummer 1?
Bewertet es Menschen oder nur Firmen? Handeln Sie im Auftrag einer Behörde? Die
erste beendet den Durchlauf, wenn sie verneint wird; die zweite und dritte
sperren einzelne Stellen, auf die sie wirken (`wirkt_auf`).

**Anhang I bekommt einen eigenen Weg.** Artikel 6 Absatz 1 verlangt drei Dinge
zusammen: ein geregeltes Produkt aus einer der 15 Produktgattungen (Maschine,
Spielzeug, Aufzug, Medizinprodukt, Fahrzeug und so fort), die Rolle im Produkt
(das KI-System *ist* das Produkt oder ist Sicherheitsbauteil darin) und eine
Konformitätsbewertung durch eine dritte Stelle vor dem Verkauf. Baue das als
Gruppen: eine Gruppe gilt als erfüllt, wenn eine ihrer Fragen bejaht ist; ein
Ausschluss in der Gruppe hebt sie wieder auf; ist eine Gruppe verneint, ist der
Weg zu Ende. Eine Gruppe kann gegenstandslos werden — wer das Produkt selbst
liefert, muss nicht auch noch Sicherheitsbauteil sein (`entfaellt_wenn`).

**Der Filter des Artikels 6 Absatz 3** kommt zum Schluss und nur dann, wenn eine
Stelle trägt: vier Bedingungen (enge Verfahrensaufgabe, Verbesserung
menschlicher Tätigkeit, Erkennung von Entscheidungsmustern, vorbereitende
Aufgabe) und die Gegenausnahme Profiling.

**Zielzahlen:**

| | |
|---|---:|
| Fragen insgesamt | 379 |
| Stellen des Gesetzes mit eigener Fragefolge | 31 |
| ausdrückliche Ausschlüsse | 214 |
| amtliche Beispiele in den Fragedateien | 187 |
| Vorfragen | 3 |
| Bereichsfragen | 8 |
| Produktgattungen des Anhangs I | 15 |

### Stufe 4 — Der Durchlauf

`src/compliance_helper/classification/question_flow.py`. Zwei Aufgaben: die nächste Frage stellen
und am Ende den Schluss ziehen. **Beide müssen dieselbe Logik benutzen.** Das
ist der teuerste Fehler dieses Projekts, und er ist zweimal in zwei Gestalten
aufgetreten:

**Der Weg darf nicht bei der ersten entscheidenden Antwort abbrechen.** Wer
„Geht es um Kredite?" mit Ja beantwortete, war erfasst, bevor „Betrifft es nur
Wertpapierkredite?" ihn herausnehmen konnte. Erst der Tatbestand, dann die
Ausnahme — und die Ausnahme immer ganz. Sortiere die Folgefragen entsprechend:
eine Frage, deren Ja oder Nein `nicht_erfasst` auslöst, kommt nach den anderen.

**Und die Wertung darf nicht auf Antworten warten, die der Weg nie holt.** Hörte
der Weg nach dem ersten Ja auf zu fragen, blieb der Punkt für die Wertung für
immer offen. Ein Punkt, der nie schließt, ist für den Nutzer dasselbe wie ein
Punkt, der nicht trifft — nur dass er es nicht erfährt. Darum: alle Folgefragen
eines geöffneten Punkts, keine ausgelassen, und dieselben Sperren im Weg wie in
der Wertung.

**Ein Treffer kann am Nein hängen.** Anhang III Nummer 1 Buchstabe a trägt über
das Nein zu „Bleibt das Material aus der Tatortarbeit in sich geschlossen?". Wer
nur die Ja-Seite liest, kann diesen Punkt überhaupt nicht treffen — gemessen
fielen so beide amtlichen Gesichtserkennungsbeispiele durch.

**Ein Bereichstor öffnet seinen Bereich, es trägt den Fall nicht selbst.** Die
Tore der Nummern 6 und 7 fragen breit nach dem Gebiet („Verarbeitet Ihr System
Gesicht, Fingerabdruck oder Gangbild?") und kennen die Ausnahmen der Buchstaben
darunter nicht. Gemessen stufte das eine Grenzkamera, die nur Alter und
Geschlecht ableitet, als hochriskant ein, obwohl Nummer 1 Buchstabe b genau das
ausnimmt.

**Ein Bereich kann als Ganzes entscheiden.** Anhang III Nummer 2 verlangt
mehreres zusammen: kritische Infrastruktur, eine Schutzaufgabe und einen
Betreiber, den sein Mitgliedstaat förmlich als kritische Einrichtung benannt
hat. Baue das als Verbund, in dem alle Punkte tragen müssen.

**Der Befund „bedingt".** Nach Absatz (190) der Leitlinien muss der Betreiber
förmlich benannt sein, und Absatz (191) stellt fest, dass der Anbieter das nicht
erfahren muss. Ein Nein wäre dort eine falsche Auskunft, ein Ja eine erfundene.
Darum gibt es einen dritten Befund: alle übrigen Voraussetzungen sind erfüllt,
und der Nutzer bekommt den Satz dazu, was das für ihn heißt.

**Bündle die Fragen auf Blätter.** Ein Jurist fragt in fünf bis acht Schritten,
nicht in vierzig. Er bündelt aber, was zusammengehört: „In welchem Bereich
arbeiten Sie?" ist eine Frage mit acht Kästchen, nicht acht Fragen; und wenn er
den Bereich kennt, legt er alle Fragen dazu auf einmal vor. Ein Blatt ist
jeweils: die Vorfragen, die Bereichsauswahl, die Produktgattungen des Anhangs I,
die Fragen eines Punktes, der Filter. Gemessen sinkt die Lebenslauf-Sichtung
damit von 37 Schritten auf acht, ohne dass eine Frage wegfällt.

**Die Klassen, die herauskommen können:** `kein_ki_system`,
`kein_hohes_risiko`, `hochrisiko_anhang_i`, `hochrisiko_anhang_iii`,
`hochrisiko_ausnahme`, `hochrisiko_bedingt`. Mehr nicht — eine unbekannte Klasse
ist in der Oberfläche ein leeres Ergebnis.

**Anhang I steht vor Anhang III**, so wie Artikel 6 Absatz 1 vor Absatz 2 steht,
und der Filter des Artikels 6 Absatz 3 gilt dort nicht. Das muss im Ergebnistext
stehen, sonst sucht der Nutzer eine Ausnahme, die es für ihn nicht gibt.

**Greift der Filter, ersetzt er die Einordnung in Anhang III** — beide Klassen
zugleich wären ein Widerspruch in der Auskunft. Nimmt das System Profiling vor,
bleibt es hochriskant, gleich wie gründlich ein Mensch nachprüft.

**Rechtliche Feinheiten, die ohne Hinweis falsch werden:**

| Fall | Richtig | Grundlage |
|---|---|---|
| Stimmung in Kundenfreitexten | **nicht** verboten | Artikel 3 Nummer 39 setzt biometrische Daten voraus; Text ist keine |
| Emotionen aus Mimik im Bewerbungsgespräch | verboten | Artikel 5 Absatz 1 Buchstabe f; das Bewerbungsverfahren gehört zum Arbeitsplatz |
| Müdigkeitserkennung bei Fahrern | **nicht** verboten | Ausnahme aus Sicherheitsgründen, Artikel 5 Absatz 1 Buchstabe f |
| Biometrie am Werkstor | Hochrisiko, **nicht** Artikel 26 Absatz 10 | der verlangt zusätzlich Strafverfolgung |
| Lernplattform für Beschäftigte, unverbindlich | kein hohes Risiko | kein Einsatz *für* Entscheidungen über Beschäftigte |
| Rückfallprognose für die Polizei | Hochrisiko, **nicht** verboten | Artikel 5 Absatz 1 Buchstabe d verlangt „ausschließlich auf der Grundlage des Profiling"; sonst Anhang III Nummer 6 Buchstabe d |
| Betreiber, der mit ChatGPT Texte erzeugt | **keine** Kennzeichnungspflicht nach Absatz 2 | Artikel 50 Absatz 2 bindet den Anbieter; den Betreiber treffen Absatz 3 und 4 |
| Schweißnahtprüfung per Kamera an der Maschine | kein hohes Risiko | Qualitätsprüfung ist kein Sicherheitsbauteil nach Anhang I |
| Schichtplan, der Nachtschichten nach Krankheitstagen verteilt | Hochrisiko | Anhang III Nummer 4 Buchstabe b: Aufgabenzuweisung nach persönlichen Merkmalen |
| Modell nur für die eigene Forschung, nicht in Verkehr | kein hohes Risiko | Ausnahme in Artikel 3 Nummer 63 |

### Stufe 5 — Dieselbe Rechnung im Browser

Die Einstufung soll ohne Installation laufen und im installierten Programm
genauso. Dafür steht die Ablauflogik zweimal da: in `question_flow.py` und in
`web/walkthrough.js`.

**Das ist die gefährlichste Stelle des ganzen Projekts.** Zwei Fassungen
derselben Logik laufen auseinander, und beim Bau dieses Durchlaufs haben sie
genau das getan: 30 von 217 amtlichen Beispielen gingen darauf zurück, dass
Fragefolge und Auswertung nicht deckungsgleich waren.

Drei Dinge halten sie zusammen:

1. **Eine Datenquelle.** `scripts/export_question_flow.py` schreibt die
   YAML-Dateien in eine einzige JSON-Datei, die der Browser lädt. Die Fragen
   werden nie zweimal gepflegt.
2. **`scripts/check_parity.py`** würfelt Antwortmuster mit festem Startwert
   und fährt beide Fassungen damit: dieselbe Frage in derselben Reihenfolge,
   dieselbe Gruppe auf demselben Blatt, derselbe Befund am Ende. Weicht etwas
   ab, nennt es die erste Stelle. **400 von 400 Läufen müssen gleich sein.**
3. **Dieser Abgleich steht im Prüfstand und vor jedem Paketbau.** Er prüft
   nebenher etwas, das sonst niemand prüft: dass die JSON-Datei für den Browser
   zum Regelwerk passt. Wer eine Regel ändert und die Datei nicht neu erzeugt,
   bekommt hier zwei verschiedene Ergebnisse — und nicht erst dann, wenn ein
   Nutzer im Netz eine veraltete Auskunft bekommt.

Die Webseite ist eine HTML-Datei, eine JavaScript-Datei und die Fragedaten.
Keine Anmeldung, kein Server, keine Übertragung der Angaben.

### Stufe 6 — Pflichten, Fristen und Datenschutz

Was aus einer Klasse und einer Rolle folgt, steht in YAML-Dateien unter
`data/rules/`:

**`ai_act_obligations.yaml`** — 57 Pflichten. Jede trägt: `kennung`, `titel`,
`was_zu_tun_ist` (Alltagssprache, als Handlungsanweisung), `rechtsgrundlage`
(Kennungen aus dem Korpus), `auch_genannt` (Normen, auf die der Handlungstext
verweist, ohne die Pflicht zu begründen), `fundstellen_text`, `rollen`,
`klassen`, `schwere`, `gilt_ab`, `nachweis`, `bei_verstoss`, und wo nötig
`nur_wenn` / `nur_wenn_alle` / `bei_unbekannt` / `vorbehalt`.

**Die Pflichtenliste wird dreifach gefiltert: nach Klasse, nach Rolle und nach
Merkmalen.** Ohne den dritten Filter bekommt ein Bewerbungsfilter Artikel 26
Absatz 10 zur biometrischen Fernidentifizierung mitgeliefert, und der Nutzer
muss selbst aussortieren — genau die Arbeit, die ihm abgenommen werden soll.

**`gdpr_review_path.yaml`** — 26 Prüfabschnitte, davon 14, die immer gelten, und
12 mit Bedingung.

**`ai_act_risk_classes.yaml`** — die Stellen, auf die sich die Pflichten
beziehen: 8 Verbote nach Artikel 5 mit ihren Ausnahmen, Anhang I, die 8 Bereiche
des Anhangs III, die Ausnahme nach Artikel 6 Absatz 3 mit der Gegenausnahme
Profiling, 4 Transparenzfälle nach Artikel 50, KI-Modelle mit allgemeinem
Verwendungszweck samt der Schwelle von 10²⁵ Rechenoperationen, der Rollenwechsel
nach Artikel 25, die 5 Fristenstufen nach Artikel 113, die Sanktionen nach
Artikel 99.

### Stufe 7 — Der Freitext als Vorschlag

Der Nutzer darf sein System in eigenen Worten beschreiben. Daraus werden die
Antworten **vorbelegt** und als Vorschlag angezeigt, den er bestätigt oder
berichtigt. Entscheiden tut der Freitext nichts — Grundsatz 1.

Zwei Wege führen dahin, und beide greifen auf dieselben Regeln zu:

**Wortlisten.** Je Bereich drei Listen: `starke_woerter` (kennzeichnen den
Bereich allein), `stichworte` (Wortgruppen, bei denen alle Wörter vorkommen
müssen), `kombination: {traeger, handlung}`. Dazu einmal für alle Bereiche
`entlastung`: Wendungen, mit denen eine Beschreibung ausdrücklich sagt, dass
niemand betroffen ist.

**Fallstrick: Wortstämme treffen zu viel.** „gericht" trifft „gerichtet" — und
macht eine Kamera, die auf ein Förderband gerichtet ist, zur Rechtspflege.
„assistent" macht einen Notbremsassistenten zum Gesprächssystem. „Maschine"
macht einen Maschinenbauer, der Handbücher übersetzt, zum Hochrisikoanbieter.
Prüfe jedes Einzelwort gegen einen Gegenfall, bevor du es in `starke_woerter`
schreibst. Und umgekehrt: „bewerbung filtern" trifft „Bewerbungen vorsortieren"
nicht — verlange bei Wortgruppen alle Wörter als Wortstamm.

**Zweckkatalog.** `data/rules/ai_act_purpose_catalog.yaml`: 55 Einträge, 21
Gegenzwecke. Zu jeder Fundstelle derselbe Zweck in der Sprache, in der ein
Unternehmen ihn beschreibt. Das Feld `regel` zeigt auf eine **bestehende**
Kennung in `ai_act_risk_classes.yaml` — ein zweiter Eingang in dieselbe Regel,
kein zweites Regelwerk.

Vier Dinge daran sind gemessen und nicht verhandelbar:

**a) Vergleiche Zweck mit Zweck, nicht mit dem Gesetzestext.** Anhang III
formuliert fast alle seine Punkte mit derselben Formel („KI-Systeme, die
bestimmungsgemäß … verwendet werden sollen"). Wer die Beschreibung gegen den
Gesetzestext stellt, misst überwiegend diese gemeinsame Formel. Gemessen: ein
richtiger Treffer lag bei 0,0017, ein falscher bei 0,1009 — die Reihenfolge
stimmte, die Höhe nicht, und eine Schwelle ist darauf nicht zu setzen.

**b) Schreibe jeden Zwecksatz als Aussagesatz in der ersten Person Plural.**
Drei Formen, je gegen dieselben drei Beschreibungen gemessen:

| Form des Zwecksatzes | richtige Treffer | falsche |
|---|---|---|
| „Bilder oder Fotos erzeugen" | 0,036–0,447 | bis 0,141 |
| „Das System erzeugt Bilder." | 0,037–0,546 | bis 0,159 |
| **„Wir erzeugen mit KI Bilder."** | **0,986–0,989** | **bis 0,073** |

Nur die dritte Form trennt. Eine Beschreibung ist ein Aussagesatz in der ersten
Person, und der Kreuzbewerter vergleicht Satz mit Satz.

**c) Vergleiche satzweise und leite die Satzform an.** „Wir sind ein Softwarehaus
und verkaufen eine Recruiting-Software. Die KI liest Lebensläufe und schlägt
dem Personaler die drei besten Kandidaten vor. Was müssen wir beachten?" — zwei
von drei Sätzen sagen über den Zweck nichts, und die Rückfrage am Ende zieht
den Wert herunter. Zerlege in Sätze, wirf reine Rückfragen weg, und leite zu
jedem Satz mit Verkäufervorspann („Wir verkaufen eine Software, die X") oder
mit dem System als Subjekt („Die KI liest X") **zusätzlich** den Satz „Wir X"
ab. Gemessen: 0,35 mit Vorspann, 0,75 ohne ihn, bei einer Schwelle von 0,50.
Nimm aber nur Subjekte, die das System bezeichnen: „Eine Kollegin liest alles
gegen" darf nicht zu „Wir lesen alles gegen" werden, denn dort handelt ein
Mensch, und genau das entlastet nach Artikel 6 Absatz 3.

**d) Drei Dinge halten die Fehltreffer draußen.**

* *Gegenzwecke.* Zu jeder Stelle gehören Zwecke, die ihr ähnlich sehen und
  nicht erfasst sind: die Sichtprüfung in der Fertigung neben dem
  Sicherheitsbauteil, die Suche nach Vertragsfristen neben der Kündigung, das
  Besprechungsprotokoll neben der Stimmauswertung. Ein Gegenzweck wirkt auf die
  **ganze Regel**, nicht nur auf die Fundstelle, bei der er steht. Trifft er
  deutlich (ab 0,90) und besser als der Zweck einer Stelle, schlägt er **jede**
  Regel: er beschreibt einen Zweck, den die Verordnung nicht erfasst.
* *Eine eigene, höhere Schwelle für Verbote.* Gemessen traf eine Lernplattform,
  die Aufsätze benotet, den Satz „Wir erkennen die Gefühle von Schülern" mit
  0,6297; die App, die die Stimmung von Mitarbeitern misst, traf ihren Satz mit
  0,9974. 0,85 für Verbote, 0,50 für alles andere.
* *Verlangter Wortlaut.* Artikel 5 Absatz 1 Buchstabe d verbietet die Vorhersage
  von Straftaten nur, wenn sie **ausschließlich** auf Profiling beruht. Fehlt das
  Wort, greift Anhang III Nummer 6 Buchstabe d — Pflichten statt Verbot. Für den
  Nutzer ist das der Unterschied zwischen weitermachen mit Auflagen und
  einstellen. Setze das auf **beiden** Wegen durch, im Katalog als `verlangt`
  und im Regelwerk als `verlangt_wortlaut`.

**Zwei Stufen, damit es nichts kostet.** Der Kreuzbewerter rechnet je Paar.
Erst wählt die Sinn-Nähe des Einbetters je Satz höchstens fünf Fundstellen aus,
davon höchstens zwei je Regel; nur diese Paare bewertet der Kreuzbewerter. Die
Grenze je Regel ist nötig: Anhang I nennt 20 Produktgattungen mit gleich
gebauten Sätzen, deren gemeinsames Satzgerüst sonst die ganze Vorauswahl
belegt — derselbe Fehler wie in a), nur eine Stufe früher.

**Fehlt eines der Modelle, liefert der Zweckweg eine leere Liste** und die
Wortlisten bleiben allein zuständig, mit einer Meldung im Protokoll. Der
Container ohne Netz und das Paket ohne Suchmodell müssen weiter einstufen
können — die Fragefolge braucht kein Modell.

**Messe die Vorbelegung an Fragen, die nicht aus der eigenen Sammlung kommen.**
Schreibe mindestens 100 Beschreibungen, wie Unternehmen sie wirklich einreichen:
knapp, in eigener Sprache, oft als Frage, mit Produktnamen und ohne
Rechtsbegriffe, aus Sicht des Softwarehauses, das ein KI-Produkt verkauft,
**und** aus Sicht des Anwenders. Bestimme die Soll-Einstufung aus dem
Verordnungstext, nicht aus dem, was der Prüfer gerade liefert. Mindestens ein
Viertel davon muss harmlos sein — eine Vorbelegung, die alles für Hochrisiko
erklärt, ist genauso wertlos wie eine, die nichts erkennt.

Hier stand die Quote auf diesen Fragen bei 55 Prozent, als nur die Wortlisten
liefen, bei 86 mit dem Zweckkatalog in erster Fassung, bei 98 nach dem
Abarbeiten der vierzehn Fehlschläge und bei 100, nachdem Artikel 50 nach Rollen
getrennt war. Jeder Fehlschlag hatte eine benennbare Ursache — fehlender
Zwecksatz, fehlender Gegenzweck, falsche Schwelle, fehlende Rollenprüfung,
fehlender verlangter Wortlaut. Keiner war „das Modell ist eben ungenau".

Setze die Grenze in der Prüfung aber **nicht** auf 100. Eine Grenze, die beim
ersten neuen Zwecksatz bricht, wird hochgesetzt statt behoben; 95 lässt Luft und
fängt einen echten Rückfall.

### Stufe 8 — Die Suche im Verordnungstext

Vier Wege, weil Rechtsfragen auf zwei Arten gestellt werden:

1. **Vektorsuche** (Bedeutung) — bge-m3 auf dem Rechner, 1024 Dimensionen
2. **BM25-Stichwortsuche** (Wortlaut) — eigene Fassung, k1 = 1,5, b = 0,75
3. **Wortgewichte des Modells** — nur bge-m3
4. **Fundstellenweg** — „Art. 6 Abs. 3" wird per regulärem Ausdruck zu
   `KI-VO/art-6/abs-3` aufgelöst und direkt geholt

Es gibt bewusst nur ein Modell. Ein kleineres zweites für schwächere Geräte
hieße: dieselbe Auskunft, zwei Genauigkeiten, ein Name. Wer sich auf eine
Rechtsauskunft verlässt, darf nicht raten müssen, welche der beiden er bekommt.

Zusammengeführt wird über **Reciprocal Rank Fusion** (`gewicht / (60 + rang)`),
nicht über die Punktzahlen: die sind zwischen den Wegen nicht vergleichbar. Der
Fundstellenweg bekommt Gewicht 3,0. Danach bewertet ein Kreuzbewerter
(bge-reranker-v2-m3) die besten 30 neu.

Der Bestand wird einmal gerechnet und abgelegt — **als gepacktes JSON, nie als
pickle** (Grundsatz 8). Beim Laden wird der Modellname verglichen: Einbettungen
verschiedener Modelle liegen in verschiedenen Räumen, und die Treffer wären
stiller Unsinn.

**Der Lauf dauert rund eine Stunde. Lege alle 64 Einheiten ein Teilstück ab**,
sonst kostet jeder Abbruch die ganze Rechenzeit. (Dieser Fehler wurde hier
zweimal gemacht, bevor die Zwischenstände eingebaut wurden.)

### Stufe 9 — Die Antwort

Die Einstufung wird dem Modell als feststehende Tatsache vorgelegt, und zwar
**nach** den Angaben des Nutzers: das Letzte, was es liest, ist das Regelwerk.

Gegen untergeschobene Anweisungen: eine je Anfrage gewürfelte Abschnittsmarke
(`secrets.token_hex(6)`). Wer eine Abschnittsgrenze nachbauen will, müsste sie
erraten. Die Systemanweisung erklärt Beschreibung und Belege ausdrücklich zu
Daten.

Nach dem Formulieren wird nachgesehen, ob die Antwort Fundstellen nennt, die in
keinem Beleg stehen. Ohne Schlüssel entsteht die Auskunft allein aus dem
Regelwerk — knapper formuliert, inhaltlich dieselbe.

### Stufe 10 — Die Oberflächen

- **Die Fragefolge ist die Startseite.** Im Browser unter `web/`, im Programm
  dieselben Dateien unter `/classification`. Die Volltextsuche liegt daneben unter
  `/search`; sie braucht das große Sprachmodell, die Einstufung nicht.
- **Schnittstelle** (FastAPI): `/health`, `/api/classify`, `/api/search`,
  `/api/ask`, `/api/questionnaire`, `/api/deadlines`. `/health` nennt den wahren
  Zustand samt Warnungen — läuft die Suche mit dem Ersatzverfahren, muss das
  dort stehen.
- **Kommandozeile**: `pruefen`, `fragen`, `suchen`, `dienst`, `stand`, jeweils
  mit `--json`. **Fallstrick:** stehen die allgemeinen Schalter am Haupt- und am
  Unterbefehl, überschreibt argparse den Wert des Hauptbefehls mit der Vorgabe
  des Unterbefehls — `helfer --json stand` verliert dann sein `--json`. Sieh in
  `sys.argv` nach, was wirklich auf der Zeile stand.
- **Container**: Nutzer ohne Verwalterrechte (feste Kennung 10001), Quelltext
  und Daten gehören root und sind nur lesbar. Ratenbegrenzung 30 Anfragen je
  Minute auf `/api/`, nicht auf `/health` — ein Prüfprogramm soll sich nicht
  selbst aussperren.

### Stufe 11 — Wo die Daten liegen, und die Pakete

**Eine Stelle beantwortet die Frage, wo die Daten liegen: `src/compliance_helper/paths.py`.**
Alle anderen fragen dort. Die Reihenfolge der Suche: `COMPLIANCE_HELPER_ROOT` aus der
Umgebung, falls ein Betreiber das Regelwerk selbst pflegt; dann der Ordner, in
den der Packer die Daten geschrieben hat (`sys._MEIPASS`); dann die
Projektwurzel.

**Der Grund steht im ersten Paketbau.** Dort legt der Packer die Datenordner
woanders ab als im Quellbaum, und ein Pfad, der von der Lage der Programmdatei
ausgeht, zeigt dann ins Leere. Gemessen hieß das: das Programm startete, meldete
„Regeldatei fehlt" und war nutzlos — die Dateien waren da, nur an einer anderen
Stelle.

**Pakete für Windows, Mac und Linux**, gebaut mit PyInstaller aus
`packaging/compliance_helper.spec`, Startpunkt `packaging/launch_app.py`. Was der Nutzer
bekommt: eine Datei zum Ausführen, die beim Start die Bedienoberfläche im
Browser öffnet. Kein Python, keine Umgebung, kein Nachladen.

Drei Dinge dazu:

* **Auf drei Maschinen bauen, nicht auf einer.** Ein Paket enthält die
  Laufzeitumgebung des Systems, auf dem es gebaut wurde; ein auf Linux gebautes
  Windows-Programm gibt es nicht. `.github/workflows/packages.yml` baut auf
  `windows-latest`, `macos-latest` und `ubuntu-latest`.
* **Was mit ins Paket kommt:** Rechtsbestand, Regelwerk samt Fragefolge,
  Anwendungsfälle, Bedienoberfläche, die Webseite. Was draußen bleibt: das
  Suchmodell von rund 2,3 Gigabyte — es würde das Paket vervierzigfachen, und
  die Einstufung braucht es nicht. Der Helfer holt es auf Wunsch nach, an der
  Stelle, wo es gebraucht wird. Ebenso bleiben die Rohdateien draußen.
* **`packaging/launch_check.py` startet das fertige Paket und sieht nach, ob
  die Oberfläche antwortet.** Ein Paket, das sich bauen lässt, muss sich noch
  lange nicht starten lassen; den Fehler oben fand niemand beim Bauen, nur beim
  Starten.

### Stufe 12 — Die Anwendungsfälle und die Messung

**44 Anwendungsfälle** in 9 Gebieten, jeder mit `lage` (Alltagssprache, kein
Fachjargon), `rolle`, `einstufung`, `begruendung` und `rechtsgrundlagen`. Sie
sind der Maßstab für die Pflichten: eine Prüfung schickt jeden Fall durch und
vergleicht mit der hinterlegten Einstufung.

**Aber sie messen die Genauigkeit nicht.** Es sind dieselben Fälle, an denen die
Regeln entwickelt wurden; 44 von 44 heißt dort nur, dass nichts zurückgefallen
ist. Eine Trefferquote auf eigenen Prüffällen sagt aus, dass das Werkzeug mit
der eigenen Lesart übereinstimmt.

**Darum wird an den amtlichen Beispielen gemessen.** Der Entwurf der Leitlinien
enthält 217 Beispiele; jedes beschreibt ein System und nennt die Wertung der
Kommission. Gemessen wird so: ein Leser, der nur die Beschreibung kennt — nicht
die Wertung —, beantwortet damit die Fragen des Durchlaufs. Verglichen wird, ob
der Durchlauf zur selben Wertung kommt wie die Kommission.
`scripts/answer_questions.py` gibt dafür die nächsten offenen Fragen heraus
und nimmt die Antworten entgegen.

**Die Zielzahlen der Messung:**

| Was | Ergebnis |
|---|---|
| amtliche Beispiele richtig eingestuft | **207 von 217** |
| Schritte je Fall im Schnitt | **5,3** |
| Webseite und Programm rechnen gleich | **400 von 400** |
| Belegstellen, die auf echten amtlichen Text zeigen | 303 von 303 |
| Rechtsbestand ohne Verlust zerlegt | 2.811 Einheiten, keine Warnung |

Elf Abweichungen bleiben, und sieben davon messen den Durchlauf nicht: ihre
Beschreibungen nennen gar keinen Bereich des Anhangs III, und der Filter des
Artikels 6 Absatz 3 kommt ohne Bereich zu Recht nie an die Reihe. Rechnet man
sie heraus, sind es 207 von 210. Alle drei übrigen liegen daran, dass der
Beispieltext das entscheidende Merkmal nicht nennt — wer sein eigenes System
einstuft, kennt es.

**Lege die Zahlen in eine Datei** (`data/evaluation/figures.json`) und lass
README, Oberfläche und Präsentation daraus schöpfen. **Schreibe jede Abweichung
mit ihrer Ursache auf** (`data/evaluation/MEASUREMENT.md`) — eine Trefferquote ohne
die Liste der Fehlschläge ist eine Behauptung.

Und schreibe dazu, was die Zahl **nicht** hergibt: kein Jurist hat den Durchlauf
gegengelesen, und die abgeleiteten Pflichten sind gegen den Verordnungstext
geprüft, aber gegen keine fremde Sollvorgabe gemessen — es gibt dafür keine
amtliche Beispielsammlung.

### Stufe 13 — Die Prüfungen

Mindestens so viel wie hier, aufgeteilt nach Gegenstand:

| Datei | Gegenstand | Hier |
|---|---|---:|
| `test_answer.py` | Angriffsreihe, erfundene Fundstellen, Auskunft ohne Modell | 36 |
| `test_classification.py` | alle 44 Anwendungsfälle, Merkmalsfilter, Rückfallprüfungen | 33 |
| `test_search.py` | vier Wege, Ablegen und Laden, kein pickle | 26 |
| `test_question_flow.py` | Belege, gezählte Zahlen, vollständige Wege durch die Folge | 23 |
| `test_service.py` | die Pfade der Schnittstelle, Ratenbegrenzung, Fehlerantworten | 23 |
| `test_purposes.py` | Katalogform, Fundstellen im Korpus, Satzform, Schwellen | 19 |
| `test_corpus.py` | Zielzahlen, Kennungsform, keine Doppelten, kein Beiwerk | 18 |
| `test_cli.py` | fünf Befehle, `--json`, Schutzwall | 16 |
| `test_container.py` | ohne Netz, ohne Verwalterrechte, Schreibschutz | 10 |
| `test_measurement.py` | die veröffentlichten Zahlen gegen die Messprotokolle | 8 |
| `test_paths.py` | Quellbaum, Paket, eigener Ordner über die Umgebung | 5 |
| `test_parity.py` | 400 Läufe Webseite gegen Programm | 1 |

**Was jede dieser Dateien trägt, und warum sie nicht zusammengelegt werden
dürfen:**

* **Die Fragefolge wird an ihren Belegen geprüft, nicht nur am Ergebnis.** Jede
  Rechtsfrage trägt ihre Absatznummer, jeder Punkt zeigt auf eine Stelle, die im
  Rechtsbestand wirklich steht. Eine Frage, die auf nichts zeigt, fällt sonst
  nie auf — sie funktioniert, sie ist nur unbelegt.
* **Die Wege werden vollständig gefahren**, von der ersten Vorfrage bis zum
  Befund, mit den Antworten, die ein Mitarbeiter über sein eigenes System gäbe.
  Eine Prüfung, die nur die Wertung aufruft, prüft die Hälfte: dass der Weg die
  nötigen Fragen überhaupt stellt, ist die andere.
* **„Weiß ich nicht" braucht die Gegenprobe.** Eine Prüfung, die zeigt, dass
  der Fall mit der offenen Antwort erfasst bleibt, ist nur halb etwas wert. Die
  andere Hälfte: mit einem erzwungenen Nein fällt er heraus. Ohne diese
  Gegenprobe prüft die erste Hälfte nichts.
* **Die veröffentlichten Zahlen werden nachgezählt.** 207 von 217 wird aus den
  Messprotokollen gerechnet, der Rechtsbestand aus dem Korpus, und das README
  wird dagegen gelesen. Eine Zahl, die einmal gestimmt hat, stimmt nach der
  nächsten Änderung nicht mehr — und niemand sieht es ihr an.
* **Der Container-Test prüft beides:** dass der Dienst ohne Netz antwortet, und
  dass das Netz wirklich fehlt. Ohne die Gegenprobe ist die erste Prüfung
  wertlos.
* **Die Angriffsreihe** gehört dazu: mindestens zehn Versuche, über die
  Beschreibung Anweisungen unterzuschieben, jeder zweifach geprüft — die
  Abschnittsmarke bleibt eindeutig, und die Einstufung bleibt dieselbe.

**Prüfungen, die ein Modell brauchen, tragen die Marke `langsam`** und laufen
nicht in der schnellen Runde. Und sie prüfen vorher, ob das Modell schon auf der
Platte liegt, statt es anzufordern: wer es anfordert, löst einen Download von
rund zwei Gigabyte aus, und ein Prüflauf, der scheinbar steht, wird abgebrochen
und danach nicht mehr gestartet. Dasselbe gilt für Marken `netz` und
`container`.

**ruff, ruff format, mypy, bandit und pip-audit müssen ohne Beanstandung
durchlaufen, und der Prüfstand muss bei einem Befund abbrechen.** Ein Lauf, der
dauerhaft rot ist, wird nicht gelesen — dann fällt auch der erste echte Fehler
nicht auf. Jede Ausnahme wird begründet: die Regeln in `pyproject.toml`, die
einzelnen Stellen mit `# nosec` samt Nummer.

**Lege ein Skript an, das genau dasselbe prüft wie der Prüfstand**, in derselben
Reihenfolge und mit denselben Befehlen (`scripts/check_all.sh`). Wer nur
einen Teil prüft, schiebt einen Fehler in den Prüfstand und merkt es erst dort —
hier war es einmal die Formatierung eines Ordners, der beim Aufruf nicht
dabeistand, einmal fehlende Typangaben fremder Pakete, die auf dem
Entwicklungsrechner zufällig schon lagen, und einmal ein Ordner im Aufruf von
bandit, den es gar nicht mehr gab. Der zweite Fall ist der unangenehmste: der
Prüfstand meldet etwas, das lokal niemand nachvollziehen kann.

Darum gehören **alle** Prüfwerkzeuge samt Typangaben in die
Entwicklungsabhängigkeiten, nicht nur die, die gerade fehlen.

### Stufe 14 — Die Präsentation

16 Folien im Format 16:9, für Fachkundige **und** Fachfremde: Lage, warum
gefragt und nicht geraten wird, der Durchlauf, ein Beispiel, die Herkunft der
Fragen, der Grundsatz, Rechtsbestand, Einstufung, Pflichten, Suche, Sicherheit,
Orte, Betriebsanleitung, was nachgemessen ist, Grenzen.

Baue sie als einzelne Folien-Dateien plus ein Skript, das daraus eine
eigenständige HTML-Seite setzt — sie läuft ohne Netz, blättert mit den
Pfeiltasten und druckt eine Folie je Seite.

**Zwei Fallstricke, die beide erst beim Messen auffallen:**

1. `transform: scale(calc(100cqw / 1920))` wirkt nicht — `scale()` braucht eine
   blanke Zahl, und eine Breite geteilt durch eine Zahl ist in CSS eine Länge.
   Setze den Maßstab per Skript.
2. Ein Browser setzt von sich aus Ränder auf Überschriften, Absätze und Listen.
   Über eine Folie summieren sie sich auf mehrere hundert Punkte, und der Inhalt
   läuft unten heraus, **ohne dass man es dem Text ansieht**. Räume sie ab.

**Miss jede Folie nach**, statt die Höhe zu schätzen: Fläche 1920 × 1080, innen
1664 × 824, keine Schrift unter 24 Pixel. In diesem Projekt liefen beim ersten
Bau 14 von 14 Folien über, die schlimmste um das Doppelte.

### Stufe 15 — Veröffentlichen

README, LICENSE (Apache-2.0), NOTICE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
CHANGELOG, AUTHORS, CITATION.cff, `.gitignore`, `.gitattributes`,
`.editorconfig`, Prüfstand, Paketbau, Dependabot, Vorlagen für Meldungen und
Vorschläge.

Eine Vorlage verdient besondere Aufmerksamkeit: **`rechtsfehler.yml`** — eine
falsch eingeordnete Lage ist der schwerste Fehler, den dieses Werkzeug machen
kann, und die Meldung dazu braucht Fundstelle, erwartete und erhaltene
Einstufung.

Dokumentation unter `docs/`: Architektur, Betriebsanleitung, Datenquellen,
Entscheidungen, Haftung, Sicherheit.

**Der Entwurf der Leitlinien ist nicht bindend.** Die öffentliche Anhörung lief
bis zum 23. Juni 2026; eine endgültige Fassung lag bei Abschluss dieser Arbeit
nicht vor. Der Helfer sagt diesen Vorbehalt in jeder Auskunft mit, die sich
darauf stützt.

### Zum Schluss: nachmessen, nicht behaupten

Zähle jede Zahl, die in README, Dokumentation und Präsentation steht, am
fertigen Stand nach. Was nicht stimmt, wird berichtigt — nicht gerundet.

Und lies die Dokumentation noch einmal gegen den fertigen Stand. Sätze, die beim
Schreiben richtig waren, sind es nach der nächsten Stufe nicht mehr. Erledigtes
wird gelöscht, nicht durchgestrichen. Eine Dokumentation, die einen behobenen
Mangel noch nennt, ist schlimmer als keine: der Leser sucht nach einem Fehler,
der nicht mehr da ist.

---

## Was dieser Bauplan absichtlich offenlässt

- **Der Wortlaut der Fragen.** Wie ein Absatz der Leitlinien in einen Satz
  übersetzt wird, den ein Laie beantworten kann, ist Handarbeit am Einzelfall.
  Der Bauplan gibt die Form vor, die Pflicht zum Beleg und die Fälle, an denen
  sich die Fragen bewähren müssen.
- **Die Wortlisten für den Freitext.** Welches Wort einen Bereich kennzeichnet,
  ist eine Rechtsfrage. Vorgegeben sind die Form und die Gegenfälle.
- **Die Gestaltung der Präsentation.** Vorgegeben sind Fläche, Mindestgröße der
  Schrift und die Pflicht zum Nachmessen.
- **Das Sprachmodell zum Formulieren.** Austauschbar; die Einstufung hängt nicht
  daran (Grundsatz 1).

## Was er nicht leistet

Er ersetzt keine juristische Prüfung der Regeldateien. Die Fragen stammen aus
dem Entwurf der Leitlinien und tragen ihre Absatznummer — aber wer das Werkzeug
im Unternehmen einsetzt, lässt Fragefolge und Regelwerk von einem Menschen mit
Zulassung durchsehen.

---

<sub>Dieser Bauplan beschreibt das Repository, in dem er liegt. Alle Zahlen sind
am Stand vom 04.10.2026 nachgemessen. Apache-2.0 — nachbauen, ändern und
weitergeben ausdrücklich erwünscht.</sub>
