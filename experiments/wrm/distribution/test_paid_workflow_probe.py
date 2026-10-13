"""Offline adversarial regression for the source-bound buyer proof."""
import unittest
from paid_workflow_probe import (PublishedBuyerInput, proof, least_peak_possible,
                                 hypothetical_batching, hypothetical_one_job_economics)

class BuyerProofTests(unittest.TestCase):
    def test_buyer_input_lower_bounds(self):
        self.assertEqual(proof()["calls_lower_bounds"], {"total":390000,"reads":347000,"updates":40000})
    def test_does_not_invent_residual_from_lower_bound_counts(self):
        self.assertNotIn("unclassified", proof()["calls_lower_bounds"])
    def test_no_quota_or_root_cause_overclaim(self):
        d=proof()
        self.assertFalse(d["quota_exceeded_verified"])
        self.assertFalse(d["root_cause_verified"])
    def test_opposite_burst_models_same_monthly_totals(self):
        counter=proof()["counterexample"]
        self.assertTrue(counter["evenly_distributed_reads_can_fit_user_quota"])
        self.assertTrue(counter["same_read_count_in_one_minute_exceeds_project_quota"])
    def test_min_peak(self):
        self.assertEqual(least_peak_possible(347000,43200),9)
        self.assertEqual(least_peak_possible(40000,43200),1)
    def test_min_peak_invalid(self):
        for a,b in [(-1,5),(1,0),(True,5),(1,2.5)]:
            with self.subTest(a=a,b=b),self.assertRaises(ValueError):least_peak_possible(a,b)
    def test_hypothetical_batching(self):
        r=hypothetical_batching(347000,50)
        self.assertEqual(r["saved_calls"],173500)
        self.assertFalse(r["observed"])
    def test_batching_bad_rates(self):
        for rate in [-1,101,True,0.5]:
            with self.subTest(rate=rate),self.assertRaises(ValueError):hypothetical_batching(250,rate)
    def test_batching_zero_case(self):
        self.assertEqual(hypothetical_batching(0,100)["remaining_calls"],0)
    def test_economics_zero_fee(self):
        self.assertEqual(hypothetical_one_job_economics(fee_percent="0")["after_modelled_nonlabor_usd"],"458.80")
    def test_economics_ten_fee(self):
        self.assertEqual(hypothetical_one_job_economics(fee_percent="10")["after_modelled_nonlabor_usd"],"408.80")
    def test_economics_fifteen_fee(self):
        d=hypothetical_one_job_economics(fee_percent="15")
        self.assertEqual(d["after_modelled_nonlabor_usd"],"383.80")
        self.assertEqual(d["max_hours_before_modelled_labor_cost"],"25.59")
    def test_economics_invalid_nonfinite_or_negative(self):
        for v in ("NaN","Infinity","-1","0"):
            with self.subTest(v=v),self.assertRaises(ValueError):
                hypothetical_one_job_economics(labor_per_hour=v)
    def test_economics_invalid_assumptions(self):
        for args in ({"connects":True},{"fee_percent":"101"},{"price":"-20"}):
            with self.subTest(args=args),self.assertRaises(ValueError):hypothetical_one_job_economics(**args)
    def test_bad_buyer_metrics(self):
        for args in ({"days":0},{"low_job_preparation_minutes":6,"high_job_preparation_minutes":4},{"offered_fixed_budget_usd":True}):
            with self.subTest(args=args),self.assertRaises(ValueError):PublishedBuyerInput(**args)
    def test_no_real_customer_claim(self):
        d=proof()
        self.assertFalse(d["buyer_wtp_for_waterfound_verified"])
        self.assertEqual(d["actual_revenue_usd"],"0")
        self.assertFalse(d["unattended_runtime_verified"])

if __name__ == "__main__":
    unittest.main()
