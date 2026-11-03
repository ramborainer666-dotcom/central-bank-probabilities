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
