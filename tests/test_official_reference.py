import unittest
from unittest.mock import Mock
from pathlib import Path
from tempfile import TemporaryDirectory
from models.official_reference import parse_corra,parse_rba,collect,persist

class OfficialSourcesTests(unittest.TestCase):
    def test_valet_corra(self):
        d={"observations":[{"d":"2026-11-02","AVG.INTWO":{"v":"2.54"}},{"d":"2026-10-30","AVG.INTWO":{"v":"2.55"}}]}
        x=parse_corra(d)
        self.assertEqual(x["rate_pct"],2.54)
        self.assertEqual(x["as_of_date"],"2026-11-02")
        self.assertEqual(x["rate_type"],"overnight_benchmark")
    def test_rba(self):
        html="<html><h2>Cash rate target</h2>4.85 % <p>Effective date 4 November 2026</p><div>2 to 3% inflation</div></html>"
        x=parse_rba(html)
        self.assertEqual(x["rate_pct"],4.85)
        self.assertEqual(x["as_of_date"],"2026-11-04")
    def test_wrong_rba_layout(self):
        with self.assertRaises(ValueError):
            parse_rba("<html>Cash rate target coming soon; inflation 2-3%</html>")
    def test_partial_source_failure(self):
        sess=Mock()
        good=Mock();good.json.return_value={"observations":[{"d":"2026-11-02","AVG.INTWO":{"v":"2.54"}}]}
        bad=Mock();bad.raise_for_status.side_effect=ValueError("Source failed")
        sess.get.side_effect=[good,bad]
        x=collect(sess)
        self.assertEqual(x["status"],"partial")
        self.assertEqual(len(x["records"]),1)
        self.assertIn("RBA",x["errors"])
    def test_deduplicate_unchanged_reference_data(self):
        with TemporaryDirectory() as td:
            path=Path(td)/"a.json"
            doc={"retrieved_at":"A","records":[{"bank":"RBA","as_of_date":"2026-11-04","rate_pct":4.85}],"errors":{}}
            self.assertTrue(persist(doc,path))
            self.assertFalse(persist({**doc,"retrieved_at":"B"},path))
if __name__=="__main__":
    unittest.main()
