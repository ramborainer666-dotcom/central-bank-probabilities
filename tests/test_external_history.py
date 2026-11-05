"""Regression tests for source-specific historical snapshots."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from models import boc_prediction_markets as boc
from models import rba_open_model as rba

class HistoryTests(unittest.TestCase):
    def test_boc_snapshot_dedup_and_changes(self):
        with TemporaryDirectory() as folder:
            latest=Path(folder)/"boc-latest.json"
            hist=Path(folder)/"boc-history.json"
            row={
                "bank":"BOC","meeting_date":"2026-12-09","source_type":"prediction_market",
                "source_url":"https://example.org/","probabilities_pct":{"hike":37,"hold":63,"cut":0},
                "raw_sum_pct":100
            }
            doc={"retrieved_at":"2026-11-05T12:00:00+00:00","records":[row],"errors":{}}
            with patch.object(boc,"OUTPUT",latest),patch.object(boc,"HISTORY",hist):
                boc.save(doc)
                self.assertEqual(len(json.loads(hist.read_text())),1)
                boc.save({**doc,"retrieved_at":"2026-11-05T14:00:00+00:00"})
                self.assertEqual(len(json.loads(hist.read_text())),1)
                changed={**row,"probabilities_pct":{"hike":38,"hold":62,"cut":0}}
                boc.save({**doc,"retrieved_at":"2026-11-05T16:00:00+00:00","records":[changed]})
                self.assertEqual(len(json.loads(hist.read_text())),2)
                self.assertEqual(json.loads(hist.read_text())[-1]["probabilities_pct"]["hike"],38)

    def test_rba_history_uses_publisher_timestamp(self):
        with TemporaryDirectory() as folder:
            latest=Path(folder)/"rba-latest.json"
            hist=Path(folder)/"rba-history.json"
            row={"bank":"RBA","meeting_date":"2026-12-08","probabilities_pct":{"hike":13.39,"hold":77.53,"cut":9.08},"implied_rate_pct":4.8616,"expected_move_bps":1.2}
            doc={"retrieved_at":"2026-11-05T08:00:00+00:00","source_asof_utc":"2026-11-05T03:30:00+00:00","records":[row]}
            self.assertEqual(rba.persist(doc,latest,hist),1)
            self.assertEqual(rba.persist({**doc,"retrieved_at":"2026-11-05T13:00:00+00:00"},latest,hist),0)
            self.assertEqual(len(json.loads(hist.read_text())),1)
            newer={**row,"probabilities_pct":{"hike":14,"hold":77,"cut":9}}
            newdoc={**doc,"source_asof_utc":"2026-11-06T03:30:00+00:00","records":[newer]}
            self.assertEqual(rba.persist(newdoc,latest,hist),1)
            rows=json.loads(hist.read_text())
            self.assertEqual(rows[-1]["source_asof_utc"],"2026-11-06T03:30:00+00:00")
            self.assertEqual(len(rows),2)
if __name__=="__main__":
    unittest.main()
