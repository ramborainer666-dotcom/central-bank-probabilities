"""Öffentliche Meeting-Zusammenfassungen auslesen; nie fehlende Daten erfinden."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BANKS = {
    "FED": "federal-reserve", "ECB": "european-central-bank",
    "BOE": "bank-of-england", "BOC": "bank-of-canada",
    "RBA": "reserve-bank-of-australia", "RBNZ": "reserve-bank-of-new-zealand",
    "BOJ": "bank-of-japan", "SNB": "swiss-national-bank",
}
MONTHS = ("January|February|March|April|May|June|July|August|"
          "September|October|November|December")
ENTRY = re.compile(
    rf"(?P<date>(?:{MONTHS})\s+\d{{1,2}},\s+20\d{{2}})\s+"
    r"(?P<move>\d{1,3}(?:\.\d+)?)\s*%\s*"
    r"(?P<bps>[+-]\d+(?:\.\d+)?)\s*bp\s*"
    r"(?P<rate>\d+(?:\.\d+)?)\s*%\s*"
    r"higher\s*(?P<higher>\d+(?:\.\d+)?)\s*%\s*"
    r"same\s*(?P<same>\d+(?:\.\d+)?)\s*%\s*"
    r"lower\s*(?P<lower>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

def parse_bank(html: str, bank: str, retrieved_at: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer"]):
        element.decompose()
    text = re.sub(r"\s+", " ", " ".join(soup.stripped_strings))
    begin = text.find("Move at this meeting")
    if begin == -1:
        raise ValueError("Meeting-Übersicht nicht gefunden")
    end = text.find("Where the market thinks", begin)
    text = text[begin:end if end > begin else begin + 9000]
    today = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00")).date()
    result = []
    seen = set()
    for match in ENTRY.finditer(text):
        meeting = datetime.strptime(match["date"], "%B %d, %Y").date()
        if meeting < today or meeting in seen:
            continue
        cumulative = {key: float(match[key]) for key in ("higher", "same", "lower")}
        move = float(match["move"])
        bp = float(match["bps"])
        rate = float(match["rate"])
        if not (99.3 <= sum(cumulative.values()) <= 100.7 and 0 <= move <= 100 and 0 <= rate <= 30 and abs(bp) <= 200):
            continue
        seen.add(meeting)
        result.append({
            "bank": bank, "meeting_date": meeting.isoformat(),
            "source": "centralbank.watch",
            "source_url": f"https://centralbank.watch/{BANKS[bank]}/",
            "retrieved_at": retrieved_at,
            "move_probability_pct": move,
            "move_direction": "hike" if bp > 0 else "cut" if bp < 0 else "flat",
            "incremental_expected_bps": bp,
            "implied_rate_pct": rate,
            "cumulative": cumulative,
            "incremental_three_way": None,
            "method_note": "Move probability ist keine isolierte Hike/Hold/Cut-Verteilung."
        })
    return result[:9]

def signature(rows: list[dict]) -> str:
    """Zeitstempel nicht in den Inhaltsvergleich einbeziehen."""
    content = [{k: v for k, v in row.items() if k != "retrieved_at"} for row in rows]
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

def main() -> int:
    DATA.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    session = requests.Session()
    session.headers.update({"User-Agent": "CentralBankMonitor/0.2 (research prototype)"})
    latest_path = DATA / "latest.json"
    history_path = DATA / "history.json"
    previous = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else {"records": []}
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    updates = {}
    errors = {}
    for bank, slug in BANKS.items():
        try:
            response = session.get(f"https://centralbank.watch/{slug}/", timeout=25)
            response.raise_for_status()
            rows = parse_bank(response.text, bank, timestamp)
            if len(rows) < 2:
                raise ValueError(f"Nur {len(rows)} gültige Meetings gefunden")
            updates[bank] = rows
        except Exception as exc:
            errors[bank] = str(exc)[:250]
    if not updates:
        print("Abbruch: keine Bank mit mindestens zwei validierten Meetings.", errors, file=sys.stderr)
        return 2
    old_by_bank = {bank: [r for r in previous.get("records", []) if r["bank"] == bank] for bank in BANKS}
    merged = []
    changes = 0
    for bank in BANKS:
        new_rows = updates.get(bank)
        if new_rows is None:
            merged.extend(old_by_bank[bank])
            continue
        merged.extend(new_rows)
        if signature(new_rows) != signature(old_by_bank[bank]):
            history.extend(new_rows)
            changes += 1
    latest = {
        "retrieved_at": timestamp, "records": sorted(merged, key=lambda x: (x["bank"], x["meeting_date"])),
        "errors": errors, "status": "partial" if errors else "ok",
        "timestamp_note": "retrieved_at ist nur der Abrufzeitpunkt, nicht der nachgewiesene Marktdatenzeitpunkt."
    }
    latest_path.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if changes:
        history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Banken mit Daten: {len(updates)}; inhaltlich veränderte Banken: {changes}; Fehler: {errors}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
