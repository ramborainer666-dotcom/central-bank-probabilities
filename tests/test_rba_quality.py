import unittest
from unittest.mock import Mock
from collectors.collect import parse_bank, validate_rba_rows

RBA_HTML = """<html><body>
<h2>Move at this meeting</h2><div>Rate level by this date</div>
<table><tr><th>Meeting</th><th>Move</th><th>Implied</th><th>Higher</th><th>Same</th><th>Lower</th></tr>
<tr><td>December 8, 2026</td><td>22.9%+5.7 bp</td><td>4.85%</td><td>100.0%</td><td>0.0%</td><td>0.0%</td></tr>
<tr><td>November 2, 2027</td><td>13.1%-3.3 bp</td><td>4.82%</td><td>86.9%</td><td>13.1%</td><td>0.0%</td></tr></table>
<h2>Where the market thinks the rate will be</h2></body></html>"""

class RBAQualityTests(unittest.TestCase):
    def test_table_fallback(self):
        rows=parse_bank(RBA_HTML, "RBA", "2026-11-03T17:30:00Z")
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["meeting_date"],"2026-12-08")
        self.assertEqual(rows[0]["cumulative"]["higher"],100.0)
    def test_rba_rejects_stale_rate(self):
        fake=Mock()
        fake.get.return_value.text="<html><body>Cash rate target 4.85 %</body></html>"
        rows=parse_bank(RBA_HTML,"RBA","2026-11-03T17:30:00Z")
        with self.assertRaisesRegex(ValueError,"weicht"):
            validate_rba_rows(rows,fake)
    def test_rba_accepts_current_rate(self):
        fake=Mock()
        fake.get.return_value.text="<html><body>Cash rate target 4.79 %</body></html>"
        rows=parse_bank(RBA_HTML,"RBA","2026-11-03T17:30:00Z")
        validate_rba_rows(rows,fake)

if __name__ == "__main__":
    unittest.main()
