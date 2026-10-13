import unittest
from benchmark_substitutes import fixture, candidate_pairs, shapely_baseline, execute

class SyntheticSameInputBaselineTests(unittest.TestCase):
    def test_separately_generated_ground_truth(self):
        self.assertEqual(candidate_pairs(fixture(20)), [('g0000','g0019'),('g0001','g0018')])
    def test_free_native_parity(self):
        self.assertEqual(candidate_pairs(fixture(60)),shapely_baseline(fixture(60)))
    def test_input_not_mutated(self):
        d=fixture(20);before=[x['geometry'].wkb_hex for x in d]; candidate_pairs(d)
        self.assertEqual(before,[x['geometry'].wkb_hex for x in d])
    def test_adversarial_small_input(self):
        with self.assertRaises(ValueError):fixture(5)
    def test_metadata_truthfulness(self):
        r=execute()
        for key in ('buyer_data','external_acceptance','qgis_executed','competitive_advantage','5m_30min_benchmark'):
            self.assertFalse(r[key]);
        self.assertTrue(all(x['equal_pair_sets'] for x in r['benchmark_cases']))

if __name__=='__main__':unittest.main()
