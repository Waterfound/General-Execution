import unittest
from shapely.geometry import Polygon
from gis_probe import buyer_requirements, demo, inspect, digest

P = lambda c: Polygon(c)
CLEAN = P([(0,0),(1,0),(1,1),(0,1)])
OVERLAP = P([(0.5,0.5),(1.5,0.5),(1.5,1.5),(0.5,1.5)])
BOWTIE = P([(3,0),(4,1),(3,1),(4,0)])

class QCProbeTests(unittest.TestCase):
    def test_demo_reference_patterns(self):
        self.assertEqual(demo()['synthetic_issues_observed'], [('INVALID_GEOMETRY','bowtie'),('NULL_OR_EMPTY','missing'),('OVERLAP','clean|overlap')])
    def test_no_silent_repair(self):
        r = inspect([{'id':'x', 'geometry':BOWTIE}])
        self.assertEqual(r['repairs_applied'],0)
        self.assertTrue(r['issues'][0]['change_requires_approval'])
        self.assertEqual(r['issues'][0]['action'],'REVIEW_ONLY')
    def test_original_unchanged(self):
        wkt = BOWTIE.wkt
        inspect([{'id':'x','geometry':BOWTIE}])
        self.assertEqual(BOWTIE.wkt,wkt)
    def test_semantic_overlap_never_fix(self):
        self.assertEqual(inspect([{'id':'a','geometry':CLEAN},{'id':'b','geometry':OVERLAP}])['issues'][0]['action'],'NEVER_FIX')
    def test_nonoverlap(self):
        self.assertFalse(inspect([{'id':'a','geometry':CLEAN}])['issues'])
    def test_null_never_guess(self):
        self.assertEqual(inspect([{'id':'x','geometry':None}])['issues'][0]['action'],'NEVER_FIX')
    def test_empty_polygon(self):
        self.assertEqual(inspect([{'id':'x','geometry':Polygon()}])['issues'][0]['kind'],'NULL_OR_EMPTY')
    def test_invalid_input_type(self):
        for bad in (None,[],{},'x', list(range(1001))):
            with self.subTest(bad=str(type(bad))),self.assertRaises(ValueError): inspect(bad)
    def test_wrong_feature_schema(self):
        for bad in ({}, {'id':'x'}, {'id':'x','geometry':None,'owner':'x'}):
            with self.subTest(bad=bad),self.assertRaises(ValueError): inspect([bad])
    def test_id_type_violations(self):
        for bad in ('',0,None):
            with self.subTest(id=bad),self.assertRaises(ValueError): inspect([{'id':bad,'geometry':CLEAN}])
    def test_duplicate_ids(self):
        with self.assertRaises(ValueError): inspect([{'id':'x','geometry':CLEAN},{'id':'x','geometry':OVERLAP}])
    def test_refuse_unknown_geometry(self):
        with self.assertRaises(ValueError): inspect([{'id':'x','geometry':'POLYGON()'}])
    def test_fixed_budget_not_income(self):
        r=buyer_requirements()
        self.assertEqual(r['budget_usd_posted'],1000)
        self.assertFalse(demo()['buyer_acceptance_proven'])
        self.assertFalse(demo()['competitive_superiority_proven'])
    def test_required_throughput(self):
        self.assertAlmostEqual(buyer_requirements()['throughput_required_features_per_second'], 2777.7777777778)
    def test_recall_threshold_count(self):
        self.assertEqual(buyer_requirements()['min_detected_for_recall_95pct'],1900)
    def test_false_positive_is_rate_not_count(self):
        self.assertEqual(buyer_requirements()['max_clean_control_false_positive_rate'],.02)
    def test_missing_official_acceptance_data(self):
        self.assertFalse(buyer_requirements()['reference_benchmark_available'])
    def test_deterministic_synthetic_receipt(self):
        self.assertEqual(demo()['synthetic_issues_digest'],digest(demo()['synthetic_issues_observed']))
    def test_no_qgis_execution_claim(self):
        self.assertIn('QGIS_NOT_EXECUTED',buyer_requirements()['competition'])

if __name__=='__main__': unittest.main()
