import unittest
from datetime import datetime,timezone
from models.boc_prediction_markets import parse_event

class BoCPredictionTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,4,15,0,tzinfo=timezone.utc)
        self.slug="bank-of-canada-decision-in-december-20260908230600011"
        questions=[("increase by 25 bps","0.40"),("make no change","0.58"),
                   ("decrease by 25 bps","0.01"),("increase by 50+ bps","0.005"),
                   ("decrease by 50+ bps","0.005")]
        self.doc={"slug":self.slug,"active":True,"closed":False,"volume":"10000",
                  "markets":[{"id":str(i),"active":True,"question":"Will the BoC "+q+"?",
                  "outcomes":"[\"Yes\",\"No\"]",
                  "outcomePrices":'["'+price+'","0.5"]'} for i,(q,price) in enumerate(questions)]}
    def test_valid_market(self):
        row=parse_event(self.doc,self.slug,"2026-12-09",self.now)
        self.assertAlmostEqual(row["probabilities_pct"]["hike"],40.5)
        self.assertAlmostEqual(row["probabilities_pct"]["hold"],58)
        self.assertEqual(row["source_type"],"prediction_market")
    def test_illiquid_market(self):
        self.doc["volume"]="0"
        with self.assertRaisesRegex(ValueError,"Low event volume"):
            parse_event(self.doc,self.slug,"2026-12-09",self.now)
    def test_malformed_sum(self):
        self.doc["markets"][0]["outcomePrices"]='["0.8","0.2"]'
        with self.assertRaisesRegex(ValueError,"coherent"):
            parse_event(self.doc,self.slug,"2026-12-09",self.now)
    def test_no_stale_meetings(self):
        with self.assertRaisesRegex(ValueError,"already passed"):
            parse_event(self.doc,self.slug,"2026-11-03",self.now)
if __name__=="__main__":
    unittest.main()
