"""CC-BY-4.0 RBA model estimates, via publisher's machine-readable JSON.

NOT raw ASX quotes. Derivative estimates are attributed to RBA Rate Watch.
Fail closed on stale/mismatched observations. Never replace good data with
stale or unverified figures.
"""
from __future__ import annotations
import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests

SOURCE = "https://rbaratewatch.com/data/latest.json"
METHOD = "https://rbaratewatch.com/methodology/"
ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data/official_reference_latest.json"
OUTPUT = ROOT / "data/rba_external_model_latest.json"

def parse_rba_model(doc: dict, official_rate: float, now: datetime | None=None) -> dict:
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    asof=datetime.fromisoformat(str(doc["asof_utc"]).replace("Z","+00:00"))
    if asof.tzinfo is None:
        raise ValueError("source timestamp has no timezone")
    age=(now-asof).total_seconds()
    if age < -300 or age > 72*3600:
        raise ValueError(f"Source snapshot outdated or future-dated: {doc['asof_utc']}")
    source_rate=float(doc["cash_rate"])
    if abs(source_rate-official_rate)>0.025:
        raise ValueError(f"Stale policy rate: source {source_rate:.3f} vs RBA {official_rate:.3f}")
    rows=[]
    for item in doc.get("meetings",[]):
        meeting=date.fromisoformat(item["date"])
        if meeting < now.date():
            continue
        probs=item["probabilities"]
        vals={key:float(probs[key]) for key in ("cut_50","cut_25","hold","hike_25","hike_50")}
        if any(x<0 or x>1 for x in vals.values()) or abs(sum(vals.values())-1)>0.012:
            raise ValueError(f"Invalid probability distribution for {meeting}")
        rate=float(item["expected_rate"])
        if not -5<rate<25:
            raise ValueError("Invalid implied rate")
        rows.append({
            "bank":"RBA","meeting_date":meeting.isoformat(),"implied_rate_pct":rate,
            "expected_move_bps":float(item["implied_move_bps"]),
            "probabilities_pct":{
                "cut":round((vals["cut_25"]+vals["cut_50"])*100,3),
                "hold":round(vals["hold"]*100,3),
                "hike":round((vals["hike_25"]+vals["hike_50"])*100,3)
            },
            "five_outcome_probabilities_pct":{k:round(v*100,3) for k,v in vals.items()},
            "source_asof_utc":asof.isoformat(),"method":"RBA Rate Watch model v1.0"
        })
    if not rows:
        raise ValueError("No future RBA meetings in publisher snapshot")
    rows.sort(key=lambda r:r["meeting_date"])
    return {"retrieved_at":now.isoformat(),"source_asof_utc":asof.isoformat(),
      "source":SOURCE,"attribution":"RBA Rate Watch · CC BY 4.0",
      "license":"https://creativecommons.org/licenses/by/4.0/",
      "methodology":METHOD,
      "status":"ok","records":rows,
      "warning":"Publisher's modeled probabilities; not the raw ASX futures price or a uniquely identified market distribution."}

def load_official(path: Path=OFFICIAL) -> float:
    obj=json.loads(path.read_text(encoding="utf-8"))
    entries=[r for r in obj.get("records",[]) if r.get("bank")=="RBA" and r.get("rate_type")=="policy_target"]
    if not entries or "RBA" in obj.get("stale_banks",[]):
        raise ValueError("Fresh official RBA policy rate unavailable")
    target=max(entries,key=lambda r:r["as_of_date"])
    target_date=date.fromisoformat(target["as_of_date"])
    if (datetime.now(timezone.utc).date()-target_date).days > 100:
        raise ValueError("Official RBA policy target observation is outdated")
    return float(target["rate_pct"])

def run():
    rate=load_official()
    response=requests.get(SOURCE,timeout=20,headers={"User-Agent":"CentralBankProbabilityMonitor/0.5 (CC-BY attribution; public JSON)"})
    response.raise_for_status()
    parsed=parse_rba_model(response.json(),rate)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    old=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    if old.get("source_asof_utc")==parsed["source_asof_utc"]:
        print("RBA source unchanged; no commit")
        return
    OUTPUT.write_text(json.dumps(parsed,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"RBA publisher snapshot: {len(parsed['records'])} meetings, as-of {parsed['source_asof_utc']}")

if __name__=="__main__":
    run()
