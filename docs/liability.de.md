# Haftung: was dieses Werkzeug nicht ist

[English](liability.md) | **Deutsch**

**Kontext:** die Grenzen dessen, wofür sich die Ausgabe des Werkzeugs verwenden lässt | **Eingabe:** die Lizenz, die Messungen und die bekannten Grenzen des heutigen Stands | **Ergebnis:** was das Werkzeug nicht ist, was falsch sein kann und was es kann

Dieses Blatt steht ohne Ausreden da. Wer es gelesen hat, weiß, was er in der Hand hält. Es betrifft
die Einstufung von Systemen der künstlichen Intelligenz (KI-Systemen) nach der Verordnung (EU)
2024/1689 zur Festlegung harmonisierter Vorschriften für künstliche Intelligenz (KI-Verordnung) und
die Auskünfte zur Datenschutz-Grundverordnung und zum Bundesdatenschutzgesetz.

## Keine Rechtsberatung

**Kontext:** die rechtliche Einordnung der Ausgabe | **Eingabe:** das Rechtsdienstleistungsgesetz | **Ergebnis:** eine klare Grenze

Dieses Werkzeug leistet **keine Rechtsberatung** im Sinne des Rechtsdienstleistungsgesetzes. Es
prüft keinen konkreten Einzelfall in fremder Angelegenheit, sondern ordnet die eingegebenen
Antworten oder die eingegebene Beschreibung anhand eines Regelwerks ein und nennt die Stellen im
Gesetz dazu.

Eine Rechtsberatung gibt es von Menschen mit Berufszulassung: Rechtsanwältin, Rechtsanwalt, bei
bestimmten Fragen die zuständige Aufsichtsbehörde. Wer eine Entscheidung mit Geld- oder
Rechtsfolgen trifft — ein Produkt umbauen oder nicht umbauen, ein System in Betrieb nehmen oder
nicht, eine Meldung abgeben oder nicht —, holt sich diese Beratung.

## Kein Ersatz für die Prüfung im Einzelfall

**Kontext:** was das Werkzeug nicht wissen kann | **Eingabe:** die beiden Wege zu einer Einstufung | **Ergebnis:** eine Liste blinder Flecken

Die Einstufung entsteht entweder aus den Antworten des Nutzers auf eine Fragefolge oder aus einer
Beschreibung in eigenen Worten, abgeglichen mit einem Regelwerk aus Wortlisten und Bedingungen.
Keines von beiden kann leisten, was eine Prüfung im Einzelfall leistet:

* Es kennt den Vertrag mit dem Anbieter nicht.
* Es kennt die Betriebsanleitung des Systems nicht.
* Es kennt die tatsächlichen Datenflüsse im Unternehmen nicht.
* Es kennt die Absprachen mit dem Betriebsrat nicht.
* Es kennt die Praxis der zuständigen Aufsichtsbehörde nicht.
* Es kennt die Rechtsprechung nicht — keine einzige Entscheidung ist erfasst.

Genau an diesen Punkten entscheidet sich aber, ob eine Pflicht greift und wie sie zu erfüllen ist.

## Keine Gewährleistung

**Kontext:** was die Lizenz sagt | **Eingabe:** Apache License 2.0, Abschnitte 7 und 8 | **Ergebnis:** keine Gewährleistung, keine Haftung

Das Werkzeug steht unter der Apache License 2.0. Deren Abschnitte 7 und 8 gelten ohne
Einschränkung: die Software wird „wie besehen" bereitgestellt, ohne Gewährleistung jeder Art, und
es wird für Schäden nicht gehaftet. Das ist keine Formel am Rand, sondern die Lage.

Insbesondere wird nicht gewährleistet:

* dass die Einstufung richtig ist,
* dass die Pflichtenliste vollständig ist,
* dass die Pflichtenliste keine Pflichten enthält, die nicht gelten,
* dass die Artikelverweise stimmen,
* dass die Fristen aktuell sind,
* dass der mitgelieferte Gesetzestext mit der amtlichen Fassung übereinstimmt,
* dass die englischen Texte genau dasselbe sagen wie die deutschen.

## Was konkret falsch sein kann

**Kontext:** die bekannten Schwächen, gemessen, wo es geht | **Eingabe:** [architecture.de.md](architecture.de.md), Abschnitt „Grenzen des Systems", und der heutige Datenstand | **Ergebnis:** was Sie selbst nachprüfen müssen

Das ist nicht abstrakt. Es ist nachgemessen und im Einzelnen aufgeführt in
[architecture.de.md](architecture.de.md), Abschnitt „Grenzen des Systems". Das Wichtigste hier:

**Die Pflichtenliste ist eher zu lang als zu kurz.** Sie enthält alle Pflichten der erkannten
Risikoklasse und Rolle — auch solche, die auf das einzelne Vorhaben nicht passen. Nachgemessen am
9. Oktober 2026: ein Unternehmen, das mit gekaufter Software Bewerbungen vorsortiert, erhielt 14
Pflichten, darunter die Grundrechte-Folgenabschätzung nach Artikel 27, die nur Einrichtungen des
öffentlichen Rechts, private Einrichtungen mit öffentlichen Dienstleistungen und Betreiber nach
Anhang III Nummer 5 Buchstaben b und c bindet. Jeder Punkt der Liste ist selbst zu prüfen.

**Die Einstufung kann zu niedrig ausfallen.** In der Fragefolge hängt sie an den Antworten: eine
falsche Antwort ergibt einen falschen Befund, und das Werkzeug kann es nicht merken. Auf dem
Freitextweg (Kommandozeile, Suchseite, Schnittstelle im Format JavaScript Object
Notation, JSON) werden Merkmale an Wortlisten erkannt
und, wenn die Modelle installiert sind, am Vergleich mit Zwecksätzen. Wer sein Vorhaben mit anderen
Worten beschreibt, als diese vorsehen, wird möglicherweise nicht erkannt. Eine Beschreibung, die in
keine Regel fällt, landet bei „keine besonderen Pflichten außer KI-Kompetenz nach Artikel 4" — und
diese Einstufung trägt die Sicherheit „wahrscheinlich", nicht „sicher". Lesen Sie die Sicherheiten
und die offenen Fragen.

**10 der 217 amtlichen Beispiele werden anders eingestuft als von der Kommission.** Jede Abweichung
ist in [../data/evaluation/MEASUREMENT.de.md](../data/evaluation/MEASUREMENT.de.md) erklärt.

**Die Leitlinien sind ein Entwurf.** Die Fragen beruhen auf dem Entwurf der Leitlinien der
Europäischen Kommission vom 19. Mai 2026 zur Einstufung von Hochrisiko-KI-Systemen. Die Anhörung
lief bis zum 23. Juni 2026; die endgültige Fassung kann abweichen. Gerichte binden Leitlinien
ohnehin nicht.

**Der mitgelieferte Gesetzestext ist nicht die verbindliche Veröffentlichung.** KI-Verordnung und
Datenschutz-Grundverordnung stammen aus dem Amtsblatt der Europäischen Union, auf Deutsch und
Englisch, das Bundesdatenschutzgesetz (BDSG) von gesetze-im-internet.de. Das Werkzeug zerlegt
diese Texte mit eigenen Zerlegern in Einheiten, und ein Zerleger kann Text falsch zuordnen oder
verlieren. Das englische BDSG ist eine Übersetzung des Sprachendienstes des
Bundesinnenministeriums; rechtlich verbindlich ist nur der deutsche Text. Einzelheiten:
[data-sources.de.md](data-sources.de.md).

**Die englischen Fragen und Erläuterungen sind Übersetzungen.** Fragen, Regeln, Anwendungsfälle und
Erläuterungen wurden auf Deutsch geschrieben und ins Englische übersetzt; kein Jurist hat eine der
beiden Sprachen gegengelesen. Fehlt eine Übersetzung, wird der deutsche Text gezeigt. Die
Absatznummer an jeder Frage ist die Gegenprobe zu den Leitlinien.

**Die Fristen können sich geändert haben.** Der Vorbehalt steht im Regelwerk und in jeder Auskunft:
die Fristen stehen so im Amtsblatt vom 12. Juli 2024; zum Datenstand des Regelsatzes wurden
Änderungen einzelner Fristen politisch erörtert.

**Die Anwendungsfälle sind nicht geprüft.** Die 44 Fallbeispiele sind vom Verfasser geschrieben und
von keiner Behörde und keiner Kanzlei geprüft. Sie sind Anschauung, keine Rechtsquelle, und das
Werkzeug führt sie ausdrücklich unter „Leitlinie", nicht als Gesetz.

**Erwägungsgründe sind keine Pflichten.** Ein Erwägungsgrund begründet eine Verordnung, er regelt
nicht. Er kann als Belegstelle erscheinen. Wer ihn als Pflicht liest, liest falsch.

**Eine formulierte Antwort kann einen Artikel sinnverkehrt wiedergeben.** Die Nachprüfung erkennt
eine erfundene Nummer, aber keine falsche inhaltliche Zusammenfassung einer vorhandenen Vorschrift.
Wer sich auf eine Pflicht verlässt, liest die Belegstelle im Wortlaut nach — sie steht dabei.

**Der Datenstand hat ein Datum.** Pflichten, Risikoklassen und Prüfpfad Datenschutz tragen den Stand
31.05.2026, die Fragefolge den Stand 04.10.2026; die Gesetzestexte wurden am 03.10.2026 (Deutsch)
und am 09.10.2026 (Englisch) geholt. Rechtsprechung, Leitlinien, Angemessenheitsbeschlüsse und
delegierte Rechtsakte nach diesen Daten sind nicht berücksichtigt. Je weiter diese Daten
zurückliegen, desto weniger belastbar ist die Auskunft.

## Was das Werkzeug kann

**Kontext:** damit das Bild nicht schief wird | **Eingabe:** der Leistungsumfang der heutigen Fassung | **Ergebnis:** wofür es taugt

Es kann:

* einen ersten Überblick geben, in welche Richtung ein Vorhaben läuft,
* die Stellen im Gesetz nennen, an denen man selbst weiterliest, mit dem genauen Buchstaben, nicht
  nur dem Anhang,
* die Fragen benennen, die vor einem Gespräch mit einer Kanzlei zu klären sind,
* Anbieter- und Betreibersicht auseinanderhalten,
* zeigen, dass KI-Verordnung und Datenschutzrecht nebeneinander gelten und nicht eines statt des
  anderen,
* das alles auf Deutsch oder Englisch, und auf der Seite mit der Fragefolge ohne Konto, ohne Netz
  und ohne dass die Antworten das Gerät verlassen.

Als Vorarbeit ist es brauchbar. Als Entscheidungsgrundlage nicht.

## Wenn Sie einen Fehler finden

**Kontext:** wie Fehler das Projekt erreichen | **Eingabe:** Ihre Beobachtung | **Ergebnis:** eine Meldung über den eigenen Weg

Melden Sie ihn. Ein falscher Artikelverweis trifft jeden, der das Werkzeug benutzt. Dafür gibt es
einen eigenen Weg mit eigener Vorlage; die Einzelheiten stehen in
[CONTRIBUTING.md](../CONTRIBUTING.md) unter „Rechtsfehler".
