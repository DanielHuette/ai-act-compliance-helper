# Bericht über die Überarbeitung

[English version](REFACTORING_REPORT.md)

## Umfang

**Kontext:** Umbau des rein deutschen Konformitätshelfers 1.2.4 zum zweisprachigen AI Act Compliance Helper 2.0.0 | **Eingabe:** deutscher Code, Daten, Rechtsbestand, Suchindex und Doku | **Ergebnis:** englischer Code, Umschalter Deutsch/Englisch in jeder Oberfläche, zweisprachige Inhalte, je ein Rechtsbestand und Suchindex pro Sprache

| Punkt | Vorher (1.2.4) | Nachher (2.0.0) |
|---|---|---|
| Sprache von Code, Kennungen, Datenfeldern | deutsch | englisch |
| Oberfläche | deutsch | deutsch und englisch, umschaltbar: Webseite, Suchseite, Kommandozeile (`--lang`), Dienst (`?lang=`, Cookie, Browsersprache), Startskripte, Windows-Installer |
| Fragen, Pflichten, Fälle, Prüfdaten | deutsch | zweisprachig `{de, en}` (379 Fragen, 57 Pflichten, 44 Fälle, 217 amtliche Beispiele) |
| Rechtsbestand | deutsch, 2.811 Stellen | deutsch und englisch, je 2.811 Stellen mit gleichen Kennungen; Englisch aus dem Amtsblatt und der amtlichen BDSG-Übersetzung |
| Suchindex | deutsch, Neubau rund eine Stunde | je Sprache einer, Neubau nur geänderter Stellen |
| Paket / Befehl | `helfer` / `konformitaetshelfer` | `compliance_helper` / `compliance-helper` |
| Prüfungen | 218 | 641 (610 ohne Modelle, Netz und Docker) |
| Kommentarzeilen im Code | 9,6 % | unter 5 % je Datei |

## Gemessene Ergebnisse

**Kontext:** Die Einstufung darf durch den Umbau nicht schlechter werden | **Eingabe:** amtliche Beispiele der Kommission, gespeicherte Fälle, Unternehmensfragen | **Ergebnis:** Zahlen je Sprache

| Messung | Deutsch | Englisch |
|---|---|---|
| Amtliche Beispiele aus dem Leitlinienentwurf der Kommission | 207 von 217 | gleicher Durchlauf, sprachunabhängig |
| Gespeicherte Fälle | 44 von 44 | 44 von 44 |
| Unternehmensfragen (Freitext, echte Modelle) | 100 von 100 | 100 von 100 |
| Durchlauf in Python und im Browser gleich | 200 von 200 Zufallsläufen | 200 von 200 |

## Behobene Fehler

**Kontext:** Befunde einer unabhängigen Prüfung und einer frischen Installation | **Eingabe:** Version 1.2.4 und der Zwischenstand | **Ergebnis:** Korrekturen, jede mit eigenem Test

| Befund | Änderung |
|---|---|
| „Weiß nicht“ zählte bei Anhang-I-Produkten und Ausschlüssen wie „Ja“ | nur „Ja“ bestätigt; offene Antworten ergeben „bedingt hochriskant“ oder einen offenen Befund |
| Ein reines Lebenslauf-Sortierwerkzeug kam im Webdurchlauf als „kein hohes Risiko“ heraus (ebenso Anhang III 4b, 5b, 5c, 8a) | Fragen sind nach Tatbestandsalternativen gruppiert; ein Nein bei einer Alternative schließt die andere nicht mehr aus |
| Verneinungen wurden übersehen („wir nutzen keine Emotionserkennung“) | verneinte Stichworte zählen nicht mehr |
| Ein Besucher konnte das Sprachmodell gegen die Einstellung des Betreibers einschalten | der Dienst nutzt nur das vom Betreiber eingestellte Modell |
| Die Suchseite konnte zwei verschiedene Einstufungen zeigen | Antwort und Einstufung beruhen auf denselben Angaben |
| Langsame Anfragen blockierten den ganzen Dienst; Modellaufrufe ohne Zeitlimit | Arbeit läuft in einem Thread-Pool; einstellbares Zeitlimit |
| Schlüssel wurden in den meisten Protokollzeilen nicht geschwärzt | Schwärzung gilt für jede Protokollzeile |
| Keine Größenbegrenzung, keine Sicherheitskopfzeilen | 413 über 128 KiB; Content Security Policy und weitere Kopfzeilen |
| Fehlende Regeldateien ergaben still „minimales Risiko“ | Laden bricht mit klarer Meldung ab; das Paket enthält seine Daten |
| Interne Kürzel in der Ausgabe („needs_review“, „KI-VO/anh-III/nr-4“) | lesbare Bezeichnungen und Fundstellen in der gewählten Sprache |
| Zwei veröffentlichte Zahlen waren falsch (11 Abweichungen, 303 Rechtsgrundlagen) | korrigiert auf 10 und 302 |

## Abschlussprüfung

**Kontext:** Abnahme vor der Veröffentlichung | **Eingabe:** frischer Klon, frische Umgebung | **Ergebnis:** alle Prüfungen bestanden

| Prüfung | Ergebnis |
|---|---|
| `ruff check`, `ruff format --check`, `mypy` | fehlerfrei |
| `pytest` ohne Modelle | 610 bestanden |
| Langsame Such- und Genauigkeitsprüfungen mit Modellen, beide Sprachen | bestanden |
| Container bauen und Container-Prüfungen | 13 bestanden |
| Paket gebaut, in frischer Umgebung installiert, `classify` ausgeführt | funktioniert |
| Browserdurchgang Webseite und Suchseite, deutsch und englisch, 390 px Breite | keine Konsolenfehler, keine CSP-Verstöße, keine Sprachmischung |
