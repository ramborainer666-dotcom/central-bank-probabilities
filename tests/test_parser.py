import unittest
from collectors.collect import parse_bank, signature

EXAMPLE = """<html><body>
<h2>Move at this meeting The fresh move priced for this date alone</h2>
<p>Rate level by this date Cumulative</p>
<p>December 17, 2026</p><p>56.6%+14.2 bp</p>
<p>1.39%higher 56.6%same 43.4%lower 0.0%</p>
<p>January 19, 2027</p><p>53.7%+13.4 bp</p>
<p>1.53%higher 79.9%same 20.1%lower 0.0%</p>
<h3>Where the market thinks the rate will be</h3></body></html>"""

class ParseTests(unittest.TestCase):
    def test_two_rows(self):
        rows = parse_bank(EXAMPLE, "BOJ", "2026-11-03T17:00:00Z")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["incremental_expected_bps"], 14.2)
        self.assertEqual(rows[1]["cumulative"]["higher"], 79.9)
        self.assertIsNone(rows[0]["incremental_three_way"])
    def test_signature_ignores_retrieval_timestamp(self):
        a = parse_bank(EXAMPLE, "BOJ", "2026-11-03T17:00:00Z")
        b = parse_bank(EXAMPLE, "BOJ", "2026-11-03T19:00:00Z")
        self.assertEqual(signature(a), signature(b))
    def test_reject_bad_total(self):
        bad = EXAMPLE.replace("43.4%", "63.4%")
        rows = parse_bank(bad, "BOJ", "2026-11-03T17:00:00Z")
        self.assertEqual(len(rows), 1)

if __name__ == "__main__":
    unittest.main()
