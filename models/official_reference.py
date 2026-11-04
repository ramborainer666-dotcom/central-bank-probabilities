"""Official benchmark and policy-rate ingestion. No futures prices or probabilities.

The Canadian overnight repo rate is published by Bank of Canada's documented
Valet API. Australian cash-rate target is published by Reserve Bank of Australia.
Keep data source timestamp and retrieval timestamp separate.
"""
from __future__ import annotations
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BOC_URL = "https://www.bankofcanada.ca/valet/observations/AVG.INTWO/json?recent=10"
RBA_URL = "https://www.rba.gov.au/cash-rate-target-overview.html"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "official_reference_latest.json"

def parse_corra(response: dict) -> dict:
    observations = response.get("observations")
    if not isinstance(observations, list):
        raise ValueError("BoC response has no observations list")
    valid=[]
    for row in observations:
        try:
            d=date.fromisoformat(row["d"])
            value=float(row["AVG.INTWO"]["v"])
            if not -5 <= value <= 30:
                raise ValueError("CORRA outside plausible range")
            valid.append((d,value))
        except (KeyError,ValueError,TypeError):
            continue
    if not valid:
        raise ValueError("BoC response has no valid CORRA observation")
    d,val=max(valid,key=lambda x:x[0])
    if d > datetime.now(timezone.utc).date():
        raise ValueError("Future dated CORRA observation rejected")
    return {"bank":"BOC","rate_type":"overnight_benchmark","rate_name":"CORRA",
            "rate_pct":val,"as_of_date":d.isoformat(),"source":BOC_URL}

def parse_rba(html: str) -> dict:
    soup=BeautifulSoup(html,"html.parser")
    for node in soup(["script","style","nav","footer"]):
        node.decompose()
    body=re.sub(r"\s+"," "," ".join(soup.stripped_strings))
    # Anchor within the Cash rate target section instead of scanning all
    # percentages: inflation target 2-3% is also present on the page.
    match=re.search(
        r"Cash rate target\s+(\d{1,2}(?:\.\d+)?)\s*%\s+Effective date\s+"
        r"(\d{1,2}\s+[A-Za-z]+\s+20\d{2})", body, flags=re.I
    )
    if not match:
        raise ValueError("RBA current target and effective date not found")
    rate=float(match.group(1))
    effective=datetime.strptime(match.group(2),"%d %B %Y").date()
    if not 0 <= rate <= 30 or effective > datetime.now(timezone.utc).date():
        raise ValueError("Invalid RBA cash rate observation")
    return {"bank":"RBA","rate_type":"policy_target","rate_name":"Cash Rate Target",
            "rate_pct":rate,"as_of_date":effective.isoformat(),"source":RBA_URL}

def collect(session=None) -> dict:
    session=session or requests.Session()
    session.headers.update({"User-Agent":"CentralBankProbabilityMonitor/0.4 (personal research; contact via GitHub)"})
    now=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    records=[]
    errors={}
    for bank,url,parser in (
        ("BOC",BOC_URL,lambda r:parse_corra(r.json())),
        ("RBA",RBA_URL,lambda r:parse_rba(r.text)),
    ):
        try:
            response=session.get(url,timeout=25)
            response.raise_for_status()
            records.append(parser(response))
        except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
            errors[bank]=str(exc)[:250]
    return {"retrieved_at":now,"records":records,"errors":errors,
            "status":"ok" if len(records)==2 else "partial" if records else "error",
            "note":"These are official benchmark/target rates, NOT futures-implied rates or meeting probabilities."}

def persist(result: dict, path: Path=OUTPUT) -> bool:
    # Do not overwrite a good snapshot if all official sources fail.
    if not result["records"]:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    previous=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    fresh={r["bank"]:r for r in result["records"]}
    old={r["bank"]:r for r in previous.get("records",[])}
    stale=[bank for bank in result["errors"] if bank in old]
    merged=dict(old)
    merged.update(fresh)
    result={**result,"records":sorted(merged.values(),key=lambda r:r["bank"]),"stale_banks":stale}
    def fingerprint(doc):
        return {(r["bank"],r["as_of_date"],r["rate_pct"]) for r in doc.get("records",[])}
    if (fingerprint(previous)==fingerprint(result) and
        previous.get("errors")==result.get("errors") and
        previous.get("stale_banks",[])==stale):
        return False
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return True

if __name__=="__main__":
    result=collect()
    saved=persist(result)
    print(json.dumps({"status":result["status"],"records":result["records"],"errors":result["errors"],"changed":saved},ensure_ascii=False))
    if not result["records"]:
        raise SystemExit("No official reference observations validated")
