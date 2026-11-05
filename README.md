# Central Bank Probability Monitor

Browser-Dashboard für FED, ECB, BOE, BOC, RBA, RBNZ, BOJ und SNB.

## Stand

Prototyp: GitHub Actions testet zunächst **nur manuell**. Ein regelmäßiger Abruf wird erst nach erfolgreicher Live-Verifikation der Datenquelle und Prüfung der Nutzungsbedingungen aktiviert. Die öffentlich sichtbaren Tabellen von centralbank.watch sind keine dokumentierte API.

Das Dashboard trennt:
- kumulierte Wahrscheinlichkeit `higher/same/lower` gegenüber dem aktuellen Zinssatz;
- Wahrscheinlichkeit einer frischen Bewegung beim betreffenden Meeting (nicht vollständige Hike/Hold/Cut-Verteilung);
- erwartete Zinsänderung in Basispunkten;
- Veränderung zwischen historischen Snapshots.

Fehlende Werte werden nicht erfunden. Es wird nie eine vermeintliche isolierte Drei-Wege-Verteilung aus einer kumulierten Verteilung konstruiert.

## Lokal auf Windows

```powershell
git clone https://github.com/ramborainer666-dotcom/central-bank-probabilities.git
cd central-bank-probabilities
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m http.server 8766
```

Dann http://localhost:8766/dashboard/ öffnen. Um lokal Daten abzurufen: `.\.venv\Scripts\python.exe -m collectors.collect`. Für GitHub-Snapshots später `git pull` ausführen.

## Status der automatischen Abfrage

Workflow `.github/workflows/collect.yml`: Nur `workflow_dispatch`. Keine automatische Ausführung, bis der echte Abruf belastbar nachgewiesen ist. Das Projekt nutzt keine kostenpflichtigen Datenquellen.

## Datenqualität

Pro Bank werden bis zu 9 zukünftige Meetings gesammelt, um neben dem Zweimeeting-Vergleich auch den längerfristigen relativen Zinspfad zu zeichnen. In `history.json` erscheinen Änderungen nur bei verändertem inhaltlichen Snapshot; `retrieved_at` ist ausdrücklich der Abrufzeitpunkt und **kein** nachgewiesener Markt-Datenzeitpunkt. Quellseite und Fehler bleiben nachvollziehbar.

## Datenqualitaet und bekannte Luecken (03.11.2026)

- Live-Abfrage erfolgreich fuer FED, ECB, BOE, BOJ und SNB; RBNZ kann seit dem Parser-Update auch eine einzelne valide Sitzung speichern.
- BoC: Die oeffentliche centralbank.watch-Seite hat aktuell keine vertrauenswuerdige Meeting-Preistabelle. Keine geschatzten Daten.
- RBA: Die RBA hat am 03.11.2026 den offiziellen Cash-Rate-Target auf 4,85 % erhoeht (https://www.rba.gov.au/news/). Die centralbank.watch-Seite zeigt teilweise noch 4,60 % bzw. widerspruechliche Sitzungstermine. Daher vergleicht der Collector RBA-Daten mit dem offiziellen aktuellen Satz und haelt abweichende Daten zurueck. Keine manuelle Umdeutung veralteter Wahrscheinlichkeiten.
- RateProbability ist **kein automatischer Fallback**: Die Nutzungsbedingungen (https://rateprobability.com/terms) untersagen automatisiertes Scraping ohne schriftliche Erlaubnis.
- Alte Snapshots werden bei Ausfall einer Quelle nicht als neue Beobachtungen historisiert. `stale_banks` kennzeichnet voruebergehend weiter angezeigte Altwerte.
- GitHub Actions: drei Abrufversuche an Werktagen um 06:17, 12:17 und 19:17 UTC. Der Workflow garantiert nicht, dass drei verschiedene Marktaktualisierungen bereitstehen.
- Die Website zeigt kumulierte Hike/Hold/Cut-Verteilung. Die isolierte Bewegung ist keine vollstaendige Drei-Wege-Verteilung; dies ist im Dashboard ausdruecklich gekennzeichnet.

## Eigene Futures-Berechnung (separater Datenkanal)

Die Engine `models/futures.py` berechnet aus dem Preis eines tagesdurchschnittsbasierten 100-minus-Zins-Kontrakts den erwarteten Zinssatz nach einer Sitzung. Bei CORRA COA benutzt sie eine explizit approximierte Zwei-Block-Tagesaufzinsung; die korrekte Settlement-Berechnung benötigt den echten Fixing-Kalender samt Feiertagen und Overnight-Rates.

**Keine Live-Kurse werden ohne Genehmigung beschafft.** Die Quellenmethodik ist in den Börsendokumentationen belegt:
- CME: https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html
- ASX: https://www.asx.com.au/markets/trade-our-derivatives-market/futures-market/rba-rate-tracker
- TMX CORRA COA: https://www.m-x.ca/en/markets/interest-rate-derivatives/coa

Ablauf:
1. `data/futures_quotes.template.json` als `data/futures_quotes.json` kopieren. Nur überprüfte Werte einer für diesen Zweck freigegebenen Kursquelle verwenden. `meeting_effective` bezeichnet den Kalendertag, ab dem der neue Overnight-Referenzzins im Kontrakt gilt; nicht blind den Sitzungstag einsetzen.
2. `python -m models.calculate --input data/futures_quotes.json`
3. `data/model_latest.json` separat im Dashboard ansehen. Die bestehende `data/latest.json` wird **nicht** überschrieben.

Derzeit enthält `model_latest.json` bewusst keine Futures-Beobachtungen. Bei einem erwarteten Schritt über 25 bp liefert das einfache binäre Modell `null` für Hike/Hold/Cut, statt scheinbar exakte Prozentwerte zu behaupten. Für mehrere Meetings braucht es für jedes Meeting passende Futures, einen konsistenten Ausgangssatz, ein Termin-/Fixing-Modell und eine vollständige Wahrscheinlichkeitsverteilung; die Ein-Meeting-Engine ist dafür noch **kein Ersatz**.

Tests: `python -m unittest discover -s tests -v`. Der separate CI-Workflow `model-tests.yml` startet bei Codeänderungen.

## Offizielle Referenzzinssätze – neu (v0.4)

Zusätzlicher und technisch unabhängiger Datenabruf über `models/official_reference.py`:
- **BoC:** CORRA-Fixing über die ausdrücklich dokumentierte Bank-of-Canada-Valet-API: https://www.bankofcanada.ca/valet/docs/ und https://www.bankofcanada.ca/rates/interest-rates/corra/ .
- **RBA:** Aktueller Cash-Rate-Target samt Wirksamkeitsdatum: https://www.rba.gov.au/cash-rate-target-overview.html . Rechte: https://www.rba.gov.au/copyright/ . Quelle: Reserve Bank of Australia 2026. Kein RBA-Endorsement impliziert.
- Output: `data/official_reference_latest.json` mit `rate_type`, `as_of_date` und `retrieved_at`. Fehlgeschlagene Quellen werden als `stale_banks` gemeldet; ältere Daten bleiben bei Teilausfall sichtbar.
- Workflow `.github/workflows/official-references.yml`: werktags 12:43 UTC; auch manuell startbar. Keine Futureskurse werden abgerufen.
- Tests: `python -m unittest discover -s tests -v`.

**Wichtig:** Die Montréal-Exchange-COA-Preise und ASX-IB-Futures-Preise werden **noch nicht automatisiert**. Eine Website mit Kursen ist keine Zusage zur Nutzung als automatisierter Zeitreihen-Feed. Auf Nachfrage Freigabe oder offiziellen lizenzierten Marktdatenfeed einrichten. Quellgebundene Futuresdaten nicht mit staatlichen offiziellen Referenzzinssätzen verwechseln.

## Automatische Alternativdaten (v0.5)

**RBA:** RBA Rate Watch stellt eigene modellierte Wahrscheinlichkeiten als JSON unter CC BY 4.0 zur Verfügung, mit Quellenangabe: https://rbaratewatch.com/methodology/ . Der neue Collector `models/rba_open_model.py` nutzt **ausschließlich die veröffentlichten Modell-Ergebnisse**, nicht den ASX-Futures-Feed im Hintergrund. Er prüft den Herausgeber-Zeitstempel (<72 h), das Datum des nächsten Meetings, die Summe der fünf Wahrscheinlichkeiten und den aktuellen offiziellen RBA-Zins. Bei fehlenden oder veralteten Daten schreibt er nichts Neues. Workflow: `.github/workflows/rba-ccby.yml` (werktäglich 06:45 UTC). Kein Hinweis auf einen verifizierten Live-Lauf bis zum GitHub-Test.

**BoC:** Der öffentliche, dokumentierte Polymarket-Gamma-API-Endpunkt https://docs.polymarket.com/api-reference/events/get-event-by-slug liefert die verschiedenen handelsbasierten Meeting-Ausgänge. Der Collector `models/boc_prediction_markets.py` ruft registrierte BoC-Events ab, kontrolliert Meeting-Datum, Marktöffnung, Mindestvolumen, Vollständigkeit der Kategorien und die Summe der Preise. Niedrige Liquidität oder widersprüchliche Preise -> kein Snapshot. Workflow `.github/workflows/boc-prediction-market.yml` (werktags 06:27/12:27/19:27 UTC). Auch hier ist der erste echte Lauf noch zu bestätigen.

**Unterschied:** Polymarket-Preise sind *Prognosemarktpreise*, keine Futures- oder OIS-Raten; RBA Rate Watch veröffentlicht *Modellwahrscheinlichkeiten aus Futures*, aber nicht die originären Preisfeeds. Die beiden Kategorien werden getrennt im Browser-Dashboard und in separaten JSON-Dateien geführt. Der vorhandene Central-Bank-Watch-Collector bleibt unverändert. Keine manuellen Dateneingaben erforderlich. Bis zum Live-Test keine Garantie, dass die externen Quellen aktuelle und vollständige Wahrscheinlichkeiten liefern.

## Gemeinsame Hauptansicht und echte historische Snapshots (v0.6)

- BOC-Kacheln verwenden ausschließlich aktuelle (<48h) BoC-Prognosemarkt-Preise aus `boc_prediction_market_latest.json`. Die Preise werden **nicht** auf 100 % normiert. Dieser Datenkanal liefert **keinen implizierten Zinssatz** und wird deshalb aus dem Zinspfad-Vergleich ausgeschlossen.
- RBA-Kacheln verwenden ausschließlich aktuelle (<72h seit Herausgeber-Zeitstempel) modellierte Futures-Wahrscheinlichkeiten aus `rba_external_model_latest.json`; der modellierte Zinspfad wird im Diagramm als separates RBA-Modell markiert.
- Alle anderen Banken verwenden den bisherigen Central Bank Watch-Datenkanal (kumulierte statt isolierte Wahrscheinlichkeiten); die Hauptansicht unterscheidet die Quellen und sagt klar, welche Art von Wahrscheinlichkeit angezeigt wird.
- Historische Daten für BOC und RBA liegen unter `data/boc_prediction_market_history.json` und `data/rba_external_model_history.json`. Der Snapshot-Verlauf ist immer nach **Bank, Quelle und identischem Meeting-Datum** getrennt. Die GitHub-Workflows committen Daten und Historie zusammen.
- Nur tatsächlich geänderte Wahrscheinlichkeiten gelangen in die Historie. Eine neue erfolgreiche BoC-Abfrage aktualisiert trotzdem den Abrufzeitstempel in der Latest-Datei, damit unveränderte Quoten nicht fälschlich veraltet erscheinen.
- Die BoC-Historie wurde zusätzlich mit vier **tatsächlich bereits vorhandenen GitHub-Commits** vom 04./05.11.2026 befüllt; keine simulierten Werte. Die RBA-Historie beginnt mit dem ersten gespeicherten Herausgeber-Datensatz am 05.11.2026.
- Bei fehlendem oder veraltetem externem Feed werden BOC/RBA-Kacheln **nicht** durch ungleichartige Central Bank Watch-Zahlen ersetzt; die Kachel meldet fehlende aktuelle Daten.
