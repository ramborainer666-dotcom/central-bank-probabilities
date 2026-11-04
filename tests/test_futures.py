import unittest
from datetime import date
from models.futures import (
    rate_from_futures_price, arithmetic_after_rate, compounded_after_rate,
    daily_compounded_annualized_rate, binary_outcomes, infer_meeting, InferenceError
)

class FuturesTests(unittest.TestCase):
    def test_quote_convention(self):
        self.assertAlmostEqual(rate_from_futures_price(95.15), 4.85)
    def test_arithmetic_weighting(self):
        # 10 days before at 4%, 20 days after at 4.25%; 30 days total
        result=arithmetic_after_rate(100-(4*10+4.25*20)/30,
                 date(2026,4,1),date(2026,5,1),date(2026,4,11),4.0)
        self.assertAlmostEqual(result,4.25)
    def test_corra_two_period_reconstruction(self):
        before,after=9,22
        expected=daily_compounded_annualized_rate([2.5,2.75],[before,after])
        result=compounded_after_rate(100-expected,date(2026,12,1),
                 date(2027,1,1),date(2026,12,10),2.5)
        self.assertAlmostEqual(result,2.75,places=7)
    def test_binary_hike(self):
        self.assertEqual(binary_outcomes(10),(40.0,60.0,0.0))
    def test_binary_cut(self):
        self.assertEqual(binary_outcomes(-15),(0.0,40.0,60.0))
    def test_not_identifiable_when_exceeds_one_step(self):
        self.assertIsNone(binary_outcomes(32))
    def test_spread_adjustment(self):
        # Policy 4.85%, overnight benchmark 4.81%; post policy 5.10%, ref 5.06%
        price=100-(4.81*10+5.06*20)/30
        result=infer_meeting(future_price=price,year=2026,month=4,
             meeting_effective=date(2026,4,11),current_policy_rate_pct=4.85,
             current_reference_rate_pct=4.81,contract="arithmetic")
        self.assertAlmostEqual(result.implied_post_rate_pct,5.10,places=6)
        self.assertAlmostEqual(result.hike_pct,100.0,places=5)
    def test_reject_month_without_meeting(self):
        with self.assertRaises(InferenceError):
            infer_meeting(future_price=95,year=2026,month=4,
                meeting_effective=date(2026,5,1),current_policy_rate_pct=4.85,
                current_reference_rate_pct=4.85,contract="arithmetic")
if __name__=="__main__":
    unittest.main()
