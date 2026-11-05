"""BoC rate-decision prediction-market odds from Polymarket's public Gamma API.

This is NOT futures/OIS pricing. Do not mix with either source in charts.
Only pre-registered, publicly documented event slugs and meeting dates.
Reject thin or inconsistent markets instead of normalizing illiquid quotes.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, date, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data/boc_prediction_market_latest.json"
HISTORY=ROOT/"data/boc_prediction_market_history.json"
EVENTS=[
 ("bank-of-canada-decision-in-december-20260908230600011","2026-12-09"),
 ("bank-of-canada-decision-in-january-2027","2027-01-27"),
 ("bank-of-canada-decision-in-march-2027","2027-03-03"),
]
BASE="https://gamma-api.polymarket.com/events/slug/"

def unpack(raw):
    if isinstance(raw,str):
        return json.loads(raw)
    return raw

def category(question: str) -> str | None:
    q=question.lower()
    if "no change" in q or "maintain" in q or "unchanged" in q:
        return "hold"
    if any(k in q for k in ("increase","hike","raise")):
        return "hike"
    if any(k in q for k in ("decrease","cut","lower","reduce")):
        return "cut"
    return None

def parse_event(doc: dict, expected_slug: str, meeting: str, now: datetime | None=None) -> dict:
    now=now or datetime.now(timezone.utc)
    if doc.get("slug")!=expected_slug:
        raise ValueError("Event slug mismatch")
    if doc.get("closed") or not doc.get("active"):
        raise ValueError("Market not active")
    meeting_date=date.fromisoformat(meeting)
    if meeting_date < now.date():
        raise ValueError("Meeting already passed")
    event_volume=float(doc.get("volume") or 0)
    if event_volume < 1000:
        raise ValueError("Low event volume; do not report odds")
    cats={"hike":0.0,"hold":0.0,"cut":0.0}
    found=set()
    used=[]
    for m in doc.get("markets",[]):
        if m.get("closed") or not m.get("active",True):
            continue
        typ=category(m.get("question",""))
        if typ is None:
            continue
        outcomes=unpack(m.get("outcomes","[]"))
        prices=unpack(m.get("outcomePrices","[]"))
        if not isinstance(outcomes,list) or not isinstance(prices,list) or len(outcomes)!=len(prices):
            continue
        try:
            yes=next(float(p) for outcome,p in zip(outcomes,prices) if str(outcome).lower()=="yes")
        except (StopIteration, ValueError,TypeError):
            continue
        if not 0<=yes<=1:
            continue
        cats[typ]+=yes
        found.add(typ)
        used.append({"market_id":m.get("id"),"question":m.get("question"),"yes_price":yes})
    if found!={"hike","hold","cut"} or len(used)<4:
        raise ValueError("Incomplete outcome coverage")
    total=sum(cats.values())
    if not 0.92<=total<=1.08:
        raise ValueError(f"Market quotes do not form coherent distribution, sum={total:.3f}")
    # Never silently normalize an inconsistent orderbook/last-price snapshot.
    return {"bank":"BOC","meeting_date":meeting,"source_type":"prediction_market",
      "source":"Polymarket public Gamma API","source_url":f"https://polymarket.com/event/{expected_slug}",
      "event_slug":expected_slug,"event_volume_usd":event_volume,
      "probabilities_pct":{k:round(v*100,3) for k,v in cats.items()},
      "raw_sum_pct":round(total*100,3),"markets":used,
      "method_note":"YES share prices are prediction-market prices, not CORRA/OIS-implied probabilities. May include spreads and illiquidity."}

def fetch():
    now=datetime.now(timezone.utc)
    rows=[]
    errors={}
    for slug,meeting in EVENTS:
        if date.fromisoformat(meeting) < now.date():
            continue
        try:
            response=requests.get(BASE+slug,timeout=20,headers={"User-Agent":"CentralBankProbabilityMonitor/0.5 (read-only public API)"})
            response.raise_for_status()
            rows.append(parse_event(response.json(),slug,meeting,now))
        except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
            errors[meeting]=str(exc)[:200]
    return {"retrieved_at":now.isoformat(),"records":rows,"errors":errors,
            "status":"ok" if rows and not errors else "partial" if rows else "unavailable"}

def save(doc: dict):
    """Store the latest valid observations and an append-only change history.

    Each history row is keyed by source, bank and meeting_date. A repeated
    quote with a new retrieval time does not create a false market change.
    """
    if not doc["records"]:
        print(f"No reliable BoC markets: {doc['errors']}")
        return
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    previous=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    hist=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    if not isinstance(hist,list):
        raise ValueError("BoC history must be a list")
    last={}
    for r in hist:
        if r.get("source_type")=="prediction_market":
            last[r["meeting_date"]]=r
    added=0
    for r in sorted(doc["records"],key=lambda x:x["meeting_date"]):
        key=r["meeting_date"]
        previous_row=last.get(key)
        if previous_row is None:
            previous_row=next((x for x in previous.get("records",[]) if x["meeting_date"]==key),None)
        changed=(previous_row is None or
                 previous_row["probabilities_pct"]!=r["probabilities_pct"] or
                 previous_row.get("raw_sum_pct")!=r["raw_sum_pct"])
        if changed:
            entry={
                "bank":"BOC","meeting_date":key,
                "source_type":"prediction_market","source":"Polymarket public Gamma API",
                "retrieved_at":doc["retrieved_at"],
                "probabilities_pct":r["probabilities_pct"],
                "raw_sum_pct":r["raw_sum_pct"],
                "source_url":r["source_url"]
            }
            hist.append(entry)
            last[key]=entry
            added+=1
    def fingerprint(d):
        return [(r["meeting_date"],r["probabilities_pct"],r["raw_sum_pct"]) for r in d.get("records",[])]
    if added:
        HISTORY.write_text(json.dumps(hist,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    # Publish a fresh retrieval timestamp even when market prices do not move.
    # Otherwise a successful but unchanged feed would appear stale after 48h.
    # This does NOT append a false historical price change.
    OUTPUT.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"BoC: {len(doc['records'])} meeting odds, {added} historical changes")
if __name__=="__main__":
    save(fetch())
