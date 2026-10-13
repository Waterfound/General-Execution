"""Zero-I/O adversarial tests of buyer/bounty status parity."""
import unittest
from source_parity import SourceCase, CASES, assess, current_screen

class PrimarySourceParityTests(unittest.TestCase):
    def test_three_historical_offers_are_not_currently_accessible(self):
        data=current_screen()
        self.assertEqual(len(data['cases']),3)
        self.assertEqual(data['currently_accessible_candidates'],0)
        self.assertTrue(all(c['verdict']=='CLOSED_CURRENT_BUYER_OPPORTUNITY' for c in data['cases']))

    def test_closed_primary_source_overrides_open_marketplace(self):
        for case in CASES:
            r=assess(case)
            self.assertEqual(r['primary_status'],'CLOSED')
            self.assertFalse(r['currently_accessible'])

    def test_unknown_primary_never_counted_as_open(self):
        c=SourceCase('unknown','https://example.org/list','https://example.org/issue','OPEN','UNKNOWN','2026-10-12','25')
        self.assertEqual(assess(c)['verdict'],'UNVERIFIED_PRIMARY_SOURCE')
        self.assertFalse(assess(c)['currently_accessible'])

    def test_both_sources_open_is_conditional_not_customer(self):
        c=SourceCase('hypothetical','https://example.org/a','https://example.org/b','OPEN','OPEN','2026-10-12','25')
        result=assess(c)
        self.assertEqual(result['verdict'],'CONDITIONAL_NEEDS_COMMERCIAL_VALIDATION')
        self.assertTrue(result['cross_source_open'])
        self.assertFalse(result['currently_accessible'])
        self.assertFalse(result['waterfound_buyer_wtp_verified'])
        self.assertFalse(result['waterfound_revenue_verified'])
        self.assertFalse(result['automatic_publication_authorized'])

    def test_discovery_closed_primary_open_needs_reconciliation(self):
        c=SourceCase('drift','https://example.org/a','https://example.org/b','CLOSED','OPEN','2026-10-12')
        self.assertEqual(assess(c)['verdict'],'INCONSISTENT_OR_CLOSED_DISCOVERY_SOURCE')

    def test_negative_zero_nonfinite_or_invalid_budget_rejected(self):
        for bad in ('0','-1','Infinity','NaN','hi'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                assess(SourceCase('x','https://example.org/a','https://example.org/b','OPEN','CLOSED','2026-10-12',bad))

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            assess(SourceCase('x','https://example.org/a','https://example.org/b','AVAILABLE','CLOSED','2026-10-12'))

    def test_non_https_source_rejected(self):
        with self.assertRaises(ValueError):
            assess(SourceCase('x','http://example.org/a','https://example.org/b','OPEN','CLOSED','2026-10-12'))

    def test_wrong_case_type_rejected(self):
        with self.assertRaises(ValueError):
            assess({'primary_status':'OPEN'})

    def test_repeatable_snapshot_no_authority_or_payment(self):
        a=current_screen();b=current_screen()
        self.assertEqual(a,b)
        self.assertFalse(a['authority_created'])
        self.assertEqual(a['revenue_usd_observed'],'0')
        self.assertTrue(all(not x['buyer_contact_authorized'] for x in a['cases']))

if __name__ == '__main__': unittest.main()
