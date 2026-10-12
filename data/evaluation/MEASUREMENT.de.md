# Was nachgemessen ist

[English](MEASUREMENT.md) | **Deutsch**

**Kontext:** wie die veröffentlichten Zahlen zur Einstufung entstanden sind und was sie wert sind | **Eingabe:** die 217 amtlichen Beispiele in `official_examples.json`, der Durchlauf, die Messprotokolle `answers-*.json` und `remeasurement.json` | **Ergebnis:** die Trefferquote, das Verfahren, jede Abweichung mit Ursache und was nicht nachgemessen ist

Stand: 4. Oktober 2026. Die Zahlen stehen in `figures.json`; `tests/test_measurement.py` zählt
sie bei jedem Prüflauf aus den Messprotokollen nach.

## Die Zahl

**Kontext:** das Hauptergebnis | **Eingabe:** alle 217 Beispiele, jedes einmal beantwortet | **Ergebnis:** Trefferquote und durchschnittliche Länge eines Durchlaufs

**207 von 217 amtlichen Beispielen** der Europäischen Kommission werden richtig eingestuft, im
Schnitt in **5,3 Schritten** je Fall.

So wurde gemessen:

1. Die 217 Beispiele stammen aus dem Entwurf der Leitlinien der Kommission vom 19. Mai 2026 zur
   Einstufung von Systemen der künstlichen Intelligenz (KI) mit hohem Risiko. Jedes beschreibt ein
   KI-System und nennt die Wertung der Kommission.
2. Ein Leser, der nur die Beschreibung kennt — nicht die Wertung —, beantwortet damit die Fragen
   des Durchlaufs. `scripts/answer_questions.py` gibt die nächsten offenen Fragen aus und mit
   `--result` den Befund.
3. Verglichen wird, ob der Befund mit der Wertung der Kommission übereinstimmt.

## Was die Zahl wert ist

**Kontext:** warum die Zahl etwas bedeutet und in welche Richtung sie abweicht | **Eingabe:** Herkunft der Soll-Wertungen und Länge der Beispiele | **Ergebnis:** zwei Grenzen der Messung

Die Soll-Wertungen stammen von der Kommission, nicht vom Verfasser der Regeln. Das ist der
Unterschied zur vorigen Fassung, in der dieselbe Person Regeln und Prüffälle geschrieben hatte;
dort hieß eine hohe Trefferquote nur, dass der Helfer mit dieser einen Lesart übereinstimmt.

Die Beschreibungen der Beispiele sind kurz. Wer sein eigenes System einstuft, weiß mehr darüber,
als in zwei Sätzen steht. In diese Richtung ist die gemessene Zahl eher zu niedrig als zu hoch.

## Die zehn Abweichungen

**Kontext:** jedes Beispiel, das der Durchlauf anders einstuft als die Kommission | **Eingabe:** die Messprotokolle, wobei die Nachmessung den ersten Lauf ersetzt | **Ergebnis:** die Ursache jeder Abweichung

Sieben davon messen nicht den Durchlauf. Die Beispiele 2, 6, 13, 47, 48, 72 und 114 stammen aus
dem Abschnitt der Leitlinien zur Ausnahme nach Artikel 6 Absatz 3 der KI-Verordnung (Verordnung
(EU) 2024/1689). Ihre
Beschreibungen begründen keinen Bereich des Anhangs III. Der Durchlauf fragt die Ausnahme erst,
wenn ein Bereich trägt — so verlangt es das Gesetz, denn Artikel 6 Absatz 3 nimmt nur aus, was
zuvor unter Anhang III fällt. Ohne Bereich kommt die Frage nie an die Reihe. Für den Nutzer ist
die Folge dieselbe: keine Hochrisiko-Pflichten.

Rechnet man diese sieben heraus, sind es **207 von 210**.

Die übrigen drei:

| Beispiel | Ursache |
|---|---|
| 108 | Die Beschreibung nennt nicht, dass eine Strafverfolgungsbehörde das System einsetzt. |
| 141 | Die Beschreibung nennt keinen Bereich; das Beispiel ist ein Gegenbeispiel zur Ausnahme. |
| 187 | Die Beschreibung nennt für ein Übersetzungswerkzeug im Straßenverkehr keine Schutzaufgabe. |

Alle drei liegen daran, dass der Beispieltext das entscheidende Merkmal nicht nennt — die
einsetzende Behörde, den Bereich, die Schutzaufgabe. Wer sein eigenes System einstuft, kennt es.

Eine vierte Abweichung, Beispiel 92, ist am 4. Oktober 2026 geschlossen worden. Der Vorfrage nach
der Bewertung von Menschen fehlte ein Satz aus Absatz (73) der Leitlinien: ein Betrieb bleibt ein
Betrieb, auch wenn er einem einzelnen Menschen gehört und keine Rechtsperson ist. Wer allein
Bilanzen, Umsätze und Zahlungsverhalten des Betriebs auswertet, bewertet damit keinen Menschen.
Der Satz steht jetzt in der Frage; vorher stand er nur in der Begründung, wo ihn der Nutzer nicht
beantworten konnte.

## Was sonst nachgemessen ist

**Kontext:** Prüfungen, die neben der Trefferquote laufen | **Eingabe:** die in der Tabelle genannten Befehle und Prüfungen | **Ergebnis:** je Prüfung ein Ergebnis

| Was | Ergebnis | Wo |
|---|---|---|
| Webseite und Python-Programm kommen zum selben Befund | 400 von 400 Läufen | `scripts/check_parity.py --runs 400` |
| Jede Rechtsgrundlage des Regelwerks zeigt auf echten amtlichen Text | 302 von 302 | `tests/test_classification.py` |
| Rechtsbestand ohne Verlust zerlegt | 2811 Einheiten je Sprache, keine Warnung | `data/processed/corpus_report.json`, `corpus_report.en.json` |
| Einstufung freier Beschreibungen an 100 Unternehmensfragen | mindestens 95 von 100, deutsch und englisch | `tests/test_purposes.py`, `tests/test_accuracy_en.py` (langsame Prüfungen, brauchen die lokalen Modelle) |
| Das gebaute Paket startet und liefert die Fragefolge aus | bei jedem Paketbau | `packaging/launch_check.py` |

## Was nicht nachgemessen ist

**Kontext:** die offenen Lücken | **Eingabe:** die Teile der Auskunft ohne fremde Sollvorgabe | **Ergebnis:** zwei Feststellungen, was niemand geprüft hat

Die abgeleiteten Pflichten. Sie stammen aus `data/rules/ai_act_obligations.yaml` und sind gegen
den Verordnungstext geprüft, aber nicht gegen eine fremde Sollvorgabe gemessen — es gibt dafür
keine amtliche Beispielsammlung.

Kein Jurist hat den Durchlauf gegengelesen.
