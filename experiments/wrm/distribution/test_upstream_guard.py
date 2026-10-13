import unittest
from upstream_guard import BEFORE, AFTER, guarded_status, response_wait, memo

class PublicIssueProof(unittest.TestCase):
    def test_source_gates(self):
        self.assertEqual(guarded_status(BEFORE), 409)
        self.assertEqual(guarded_status(AFTER), 429)
    def test_upstream_golden(self):
        self.assertEqual(response_wait(BEFORE, 429, 2, 5), 5)
        self.assertEqual(response_wait(AFTER, 429, 2, 5), 2)
    def test_negative_controls(self):
        self.assertEqual(response_wait(AFTER, 409, 2, 5), 5)
        self.assertEqual(response_wait(AFTER, 500, 2, 5), 5)
    def test_fails_closed(self):
        for item in (BEFORE + AFTER, 'if (response.StatusCode is HttpStatusCode.TooManyRequests)'):
            with self.assertRaises(ValueError): guarded_status(item)
    def test_no_commercial_justification(self):
        m = memo()
        self.assertFalse(m['buyer_validated'])
        self.assertEqual(m['revenue_usd'], 0)
        self.assertFalse(m['powershell_runtime_executed'])
        self.assertEqual(m['commercial_differentiation'], 'KILL_ALREADY_FIXED_UPSTREAM')

if __name__ == '__main__': unittest.main()
