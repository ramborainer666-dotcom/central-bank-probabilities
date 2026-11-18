"""Regressionstest: erfolgreiche Prüfungen aktualisieren den Abrufstatus,
ohne unveränderte Marktwerte erneut in der Historie abzulegen."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from collectors import collect


HTML = """<html><body>
<h2>Move at this meeting The fresh move priced for this date alone</h2>
<div>Rate level by this date Cumulative</div>
<p>December 10, 2026</p>
<p>18.4%+4.6 bp</p>
<p>0.05%higher 18.4%same 81.7%lower 0.0%</p>
<h3>Where the market thinks the rate will be</h3>
</body></html>"""


class FixedClock(datetime):
    value = "2026-11-18T09:00:00Z"

    @classmethod
    def now(cls, tz=None):
        return datetime.fromisoformat(cls.value.replace("Z", "+00:00"))


class CollectorFreshnessTests(unittest.TestCase):
    def test_unchanged_data_refreshes_latest_but_not_history(self):
        session = Mock()
        session.get.return_value.text = HTML
        session.get.return_value.raise_for_status.return_value = None
        banks = {
            "FED": "federal-reserve",
            "ECB": "european-central-bank",
            "BOE": "bank-of-england",
            "SNB": "swiss-national-bank",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(collect, "DATA", Path(tmp)), \
                 patch.object(collect, "BANKS", banks), \
                 patch.object(collect, "datetime", FixedClock), \
                 patch.object(collect.requests, "Session", return_value=session):
                FixedClock.value = "2026-11-18T09:00:00Z"
                self.assertEqual(collect.main(), 0)
                first = json.loads((Path(tmp) / "history.json").read_text(encoding="utf-8"))
                self.assertEqual(len(first), 4)

                FixedClock.value = "2026-11-18T10:00:00Z"
                self.assertEqual(collect.main(), 0)
                latest = json.loads((Path(tmp) / "latest.json").read_text(encoding="utf-8"))
                history = json.loads((Path(tmp) / "history.json").read_text(encoding="utf-8"))

                self.assertEqual(latest["retrieved_at"], "2026-11-18T10:00:00Z")
                self.assertTrue(all(row["retrieved_at"] == "2026-11-18T10:00:00Z"
                                    for row in latest["records"]))
                self.assertEqual(len(history), 4)


if __name__ == "__main__":
    unittest.main()
