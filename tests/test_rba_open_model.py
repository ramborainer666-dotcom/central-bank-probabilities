import unittest
from datetime import datetime,timezone
from models.rba_open_model import parse_rba_model

class RbaOpenModelTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,4,15,0,tzinfo=timezone.utc)
        self.doc={
          "asof_utc":"2026-11-04T13:00:00+00:00","cash_rate":4.85,
          "meetings":[{"date":"2026-12-08","expected_rate":4.95,"implied_move_bps":10.0,
          "probabilities":{"cut_50":0.01,"cut_25":0.04,"hold":0.56,
                           "hike_25":0.33,"hike_50":0.06}}]
        }
    def test_valid_model(self):
        out=parse_rba_model(self.doc,4.85,self.now)
        self.assertEqual(len(out["records"]),1)
        self.assertAlmostEqual(out["records"][0]["probabilities_pct"]["hike"],39)
        self.assertEqual(out["attribution"],"RBA Rate Watch · CC BY 4.0")
    def test_policy_rate_mismatch(self):
        with self.assertRaisesRegex(ValueError,"Stale policy"):
            parse_rba_model(self.doc,4.60,self.now)
    def test_old_source_rejected(self):
        self.doc["asof_utc"]="2026-10-28T02:16:18+00:00"
        with self.assertRaisesRegex(ValueError,"outdated"):
            parse_rba_model(self.doc,4.85,self.now)
    def test_no_future_meeting_rejected(self):
        self.doc["meetings"][0]["date"]="2026-11-03"
        with self.assertRaisesRegex(ValueError,"No future"):
            parse_rba_model(self.doc,4.85,self.now)
    def test_malformed_probability_rejected(self):
        self.doc["meetings"][0]["probabilities"]["hold"]=0.9
        with self.assertRaisesRegex(ValueError,"Invalid probability"):
            parse_rba_model(self.doc,4.85,self.now)
if __name__=="__main__":
    unittest.main()
