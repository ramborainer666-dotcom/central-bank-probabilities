"""Generate independent modeled estimates from explicitly supplied futures prices.

Usage: python -m models.calculate --input data/futures_quotes.json
No network access. No invented or fetched market prices.
"""
import argparse
import json
from datetime import date
from pathlib import Path
from .futures import infer_meeting, InferenceError

def calculate_document(document: dict) -> dict:
    rows=[]
    errors=[]
    for i,q in enumerate(document.get("quotes", [])):
        try:
            for key in ("future_price","current_policy_rate_pct","current_reference_rate_pct",
                        "observed_at_utc","source"):
                if q.get(key) is None or q.get(key)=="":
                    raise InferenceError(f"Missing required field: {key}")
            if q["source"]=="AUTHORIZED_SOURCE_REQUIRED":
                raise InferenceError("Cannot use a placeholder source")
            d=date.fromisoformat(q["meeting_effective"])
            result=infer_meeting(
                future_price=float(q["future_price"]), year=int(q["year"]),
                month=int(q["month"]),meeting_effective=d,
                current_policy_rate_pct=float(q["current_policy_rate_pct"]),
                current_reference_rate_pct=float(q["current_reference_rate_pct"]),
                contract=q["contract"]
            )
            rows.append({
                "bank":q["bank"],
                "meeting_date":d.isoformat(),
                "observed_at_utc":q["observed_at_utc"],
                "source":q["source"],
                "source_type":"licensed_futures_quote",
                "contract":q["contract"],
                "current_policy_rate_pct":result.implied_pre_rate_pct,
                "implied_post_rate_pct":result.implied_post_rate_pct,
                "expected_move_bps":result.expected_move_bps,
                "model":result.model,
                "model_probabilities_pct":{
                    "hike":result.hike_pct,"hold":result.hold_pct,"cut":result.cut_pct
                },
                "notes":result.notes
            })
        except (KeyError,ValueError,TypeError) as exc:
            errors.append({"index":i,"bank":q.get("bank"),"error":str(exc)})
    return {"status":"ok" if rows and not errors else "partial" if rows else "no_valid_quotes",
            "records":rows,"errors":errors,
            "warning":"Model-based scenarios, not directly observable market probabilities."}

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",default="data/model_latest.json")
    args=p.parse_args()
    doc=json.loads(Path(args.input).read_text(encoding="utf-8"))
    out=calculate_document(doc)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Modeled {len(out['records'])} valid quotes; errors: {len(out['errors'])}.")
    if out["errors"]:
        print(json.dumps(out["errors"],ensure_ascii=False))
if __name__=="__main__":
    main()
