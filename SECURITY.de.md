# Sicherheitslücken melden

[English](SECURITY.md) | **Deutsch**

**Kontext:** wie man eine Sicherheitslücke meldet und was man erwarten kann | **Eingabe:** eine Lücke, die Sie gefunden haben | **Ergebnis:** eine vertrauliche Meldung, eine Bestätigung und, wo möglich, eine Behebung

## Nicht öffentlich melden

**Kontext:** der Meldeweg | **Eingabe:** Ihr Fund | **Ergebnis:** eine vertrauliche Nachricht

Eine Sicherheitslücke gehört **nicht** in einen öffentlichen Fehlerbericht.

Melden Sie sie an **dhuette@gmx.net** mit „Sicherheit" im Betreff. Falls Sie verschlüsseln
wollen, fragen Sie in einer ersten Nachricht ohne Einzelheiten nach einem Schlüssel.

## Was in die Meldung gehört

**Kontext:** der Inhalt einer Meldung | **Eingabe:** Ihr Fund | **Ergebnis:** eine Meldung, die sich nachstellen lässt

* Was die Lücke erlaubt.
* Wie man sie nachstellt, Schritt für Schritt.
* Welche Fassung betroffen ist: Marke oder Commit, und ob es die Webseite, das fertige Paket,
  den Container oder den Quelltext betrifft.
* Ihre Einschätzung, wen es trifft.

## Was Sie erwarten können

**Kontext:** Antwortzeiten eines Ein-Personen-Projekts | **Eingabe:** Ihre Meldung | **Ergebnis:** was versprochen wird und was nicht

Dieses Projekt wird von einer einzelnen Person nebenher betrieben. Daraus folgt, was versprochen
wird und was nicht:

* **Eingangsbestätigung:** innerhalb von 7 Tagen.
* **Erste Einschätzung:** innerhalb von 30 Tagen.
* **Behebung:** kein Termin. Es gibt kein Sicherheitsteam und keine Bereitschaft. Was behoben
  wird, wird in [CHANGELOG.md](CHANGELOG.md) eingetragen.
* **Nennung:** wer es möchte, wird in der Änderungsliste genannt.
* **Kein Geld.** Es gibt kein Belohnungsprogramm.

Antwortet niemand innerhalb von 30 Tagen, dürfen Sie die Lücke veröffentlichen. Eine Lücke, die
unbemerkt bleibt, ist schlimmer als eine veröffentlichte.

## Welche Fassungen betreut werden

**Kontext:** welche Fassungen Behebungen bekommen | **Eingabe:** keine | **Ergebnis:** die betreute Fassung

Nur die jeweils neueste. Es gibt keine Pflege älterer Fassungen.

## Was in diesem Projekt eine Sicherheitslücke ist

**Kontext:** die Grenze zwischen Lücke und gewolltem Verhalten | **Eingabe:** Ihr Fund | **Ergebnis:** ob er hierher gehört oder in einen gewöhnlichen Fehlerbericht

| Ja | Nein |
|---|---|
| Ein Weg, über den die Beschreibung des Nutzers unbemerkt das Gerät verlässt | Die Beschreibung geht an Claude oder GPT, wenn ein Schlüssel für deren Programmierschnittstelle (API, Application Programming Interface) eingetragen ist. Das ist beschrieben und gewollt. |
| Ein Weg, über den ein eingetragener Schlüssel von außen ausgelesen werden kann | Der Schlüssel wird aus der Umgebung oder der Datei `.env` gelesen; diese Datei für sich zu behalten, ist Sache dessen, der den Dienst betreibt |
| Programmausführung über eine untergeschobene Datei oder Eingabe | Der Suchbestand liegt als NumPy-Felder (`.npy`) und gepacktes JSON (JavaScript Object Notation, `.meta.json.gz`); eine veränderte Datei kann falsche Treffer verursachen, aber keinen Code starten. Eine Datei im alten `pickle`-Format wird abgewiesen, nicht gelesen |
| Eine Abhängigkeit, die Berechtigungen oder Telemetrie einschleppt | Eine Abhängigkeit mit bekannter Schwachstelle ohne Weg zum Missbrauch hier: bitte als gewöhnlichen Fehlerbericht |
| Ein Weg, der die feststehende Einstufung durch das Sprachmodell ersetzbar macht | Dass eine formulierte Antwort schlecht formuliert ist |

## Was keine Sicherheitslücke ist, aber genauso wichtig

**Kontext:** falscher Rechtsinhalt | **Eingabe:** ein falscher Verweis | **Ergebnis:** der richtige Weg dafür

**Ein falscher Artikelverweis.** Der geht in eine Auskunft ein, nach der jemand eine
Entscheidung trifft. Er gehört in die Vorlage **Rechtsfehler** und wird vor allen anderen
Meldungen bearbeitet. Siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md).

## Was geprüft ist und was nicht

**Kontext:** wie tief die Sicherheitsprüfung tatsächlich geht | **Eingabe:** das Verzeichnis in seinem jetzigen Stand | **Ergebnis:** was Sie annehmen dürfen und was nicht

Damit niemand mehr annimmt, als geprüft wurde:

* Selbsttätige Prüfungen in `tests/` prüfen unter anderem, dass eine
  untergeschobene Anweisung in ihrem Abschnitt der Anfrage bleibt, die Einstufung nicht ändern
  kann und dass erfundene Fundstellen gemeldet werden. **Kein Angriffsversuch gegen ein echtes
  Sprachmodell** wurde durchgeführt; die Vorkehrungen sind begründet, nicht erprobt.
* `bandit` (Suche nach unsicheren Mustern im Programmtext) und `pip-audit` (bekannte
  Schwachstellen in Abhängigkeiten) laufen in der Prüfung, Dependabot meldet neue Fassungen
  wöchentlich. Das ist Werkzeugprüfung, keine Durchsicht durch Menschen.
* Die **fertigen Pakete sind nicht unterschrieben**. Woher ein Paket stammt, lässt sich nur über
  den öffentlichen Lauf in GitHub Actions nachvollziehen. Eine Unterschrift für Windows und macOS
  setzt ein kostenpflichtiges Zertifikat voraus. Auf dem Mac verlangt das System darum beim
  ersten Start den Weg über das Kontextmenü.

Einzelheiten dazu, wo Daten liegen und was ein Gerät verlässt:
[docs/security.de.md](docs/security.de.md).
