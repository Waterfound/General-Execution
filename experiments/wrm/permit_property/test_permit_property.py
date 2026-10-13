from __future__ import annotations
import copy
import json
import pathlib
import unittest
from permit_property import reconcile, EvidenceError, canonical_digest
BASE = json.loads((pathlib.Path(__file__).parent/'observations.json').read_text())

class TestPublicDataJoin(unittest.TestCase):
    def outcome(self, data=None):
        return reconcile(copy.deepcopy(BASE if data is None else data))
    def reject(self, mutator, msg=None):
        data=copy.deepcopy(BASE)
        mutator(data)
        with self.assertRaises(EvidenceError, msg=msg):
            self.outcome(data)
    def test_real_sample_three_matches(self):
        r=self.outcome();self.assertEqual(r['sample_size'],3)
        self.assertEqual(r['geographic_reference_match_count'],3)
        self.assertEqual(r['distinct_geo_ids'],2)
        self.assertEqual(r['outcome_counts'],{'MATCHED_GEOGRAPHIC_REFERENCE':3})
    def test_real_two_permits_same_geographic_id_are_legal(self):
        r=self.outcome()
        self.assertEqual(r['rows'][1]['public_property_reference'],822637)
        self.assertEqual(r['rows'][2]['public_property_reference'],822637)
        self.assertNotEqual(r['rows'][1]['permit_number'],r['rows'][2]['permit_number'])
    def test_leading_zeros_kept(self):
        self.assertEqual(self.outcome()['rows'][0]['geographic_id'],'0239360701')
    def test_no_owner_or_commercial_claims(self):
        for row in self.outcome()['rows']:
            self.assertFalse(row['owner_identity_verified'])
            self.assertFalse(row['property_legal_identity_verified'])
            self.assertFalse(row['commercial_value_verified'])
    def test_provenance_transparency(self):
        self.assertEqual(self.outcome()['provenance_class'],'CONNECTOR_EXTRACTED_PUBLIC_JSON_NOT_RAW_BYTES')
    def test_deterministic_digest(self):
        a=copy.deepcopy(BASE);b=copy.deepcopy(BASE)
        self.assertEqual(canonical_digest(a),canonical_digest(b))
        self.assertEqual(self.outcome(a),self.outcome(b))
    def test_wrong_schema(self):self.reject(lambda d:d.update(schema='x'))
    def test_unknown_provenance(self):self.reject(lambda d:d['provenance'].update(evidence_class='RAW_AUTHENTICATED_BYTES'))
    def test_wrong_dataset(self):self.reject(lambda d:d['provenance'].update(austin_dataset='other'))
    def test_wrong_gis_layer(self):self.reject(lambda d:d['provenance'].update(gis_layer='a'))
    def test_wrong_source_host(self):self.reject(lambda d:d['provenance'].update(austin_url='https://fake.test/'))
    def test_wrong_gis_host(self):self.reject(lambda d:d['provenance'].update(gis_url='https://gis.traviscountytx.gov.attacker.test/'))
    def test_non_https_source(self):self.reject(lambda d:d['provenance'].update(gis_url='http://gis.traviscountytx.gov/test'))
    def test_incomplete_permit_page(self):self.reject(lambda d:d['provenance'].update(complete_sample=False))
    def test_incomplete_gis_page(self):self.reject(lambda d:d['provenance'].update(gis_complete=False))
    def test_empty_permits(self):self.reject(lambda d:d.update(permits=[]))
    def test_empty_parcels(self):self.reject(lambda d:d.update(parcels=[]))
    def test_duplicate_permit(self):self.reject(lambda d:d['permits'].append(copy.deepcopy(d['permits'][0])))
    def test_nonnumeric_geographic_id(self):self.reject(lambda d:d['permits'][0].update(tcad_id='ABC'))
    def test_numeric_type_geographic_id(self):self.reject(lambda d:d['permits'][0].update(tcad_id=239360701))
    def test_missing_geographic_id(self):self.reject(lambda d:d['permits'][0].pop('tcad_id'))
    def test_gis_record_not_in_sample(self):self.reject(lambda d:d['parcels'][0].update(geo_id='9999999999'))
    def test_gis_record_invalid_property_id(self):self.reject(lambda d:d['parcels'][0].update(PROP_ID=0))
    def test_boolean_property_id(self):self.reject(lambda d:d['parcels'][0].update(PROP_ID=True))
    def test_bad_permit_format(self):self.reject(lambda d:d['permits'][0].update(permit_number='bad'))
    def test_invalid_issue_date(self):self.reject(lambda d:d['permits'][0].update(issue_date='2030-99-45T00:00:00.000'))
    def test_wrong_postal_code_format(self):self.reject(lambda d:d['permits'][0].update(original_zip='n/a'))
    def test_missing_city_postal_code_must_review(self):
        d=copy.deepcopy(BASE);d['permits'][0]['original_zip']=None
        r=self.outcome(d);self.assertEqual(r['rows'][0]['outcome'],'ZIP_EVIDENCE_INCOMPLETE_REVIEW')
        self.assertIsNone(r['rows'][0]['public_property_reference'])
    def test_missing_gis_postal_code_must_review(self):
        d=copy.deepcopy(BASE);d['parcels'][0]['situs_zip']=None
        r=self.outcome(d);self.assertEqual(r['rows'][0]['outcome'],'ZIP_EVIDENCE_INCOMPLETE_REVIEW')
    def test_postal_conflict_must_review(self):
        d=copy.deepcopy(BASE);d['permits'][0]['original_zip']='99999'
        r=self.outcome(d);self.assertEqual(r['rows'][0]['outcome'],'POSTAL_CODE_CONFLICT_REVIEW')
        self.assertIsNone(r['rows'][0]['public_property_reference'])
    def test_mismatch_between_count_and_feature_list(self):
        self.reject(lambda d:d['provenance']['gis_counts'].update({'0239360701':2}))
    def test_absent_gis_count_blocked(self):self.reject(lambda d:d['provenance']['gis_counts'].pop('0239360701'))
    def test_unexpected_extra_count_blocked(self):self.reject(lambda d:d['provenance']['gis_counts'].update({'9999999999':1}))
    def test_string_gis_count_blocked(self):self.reject(lambda d:d['provenance']['gis_counts'].update({'0239360701':'1'}))
    def test_boolean_gis_count_blocked(self):self.reject(lambda d:d['provenance']['gis_counts'].update({'0239360701':True}))
    def test_record_not_found_with_count_zero_is_not_identity(self):
        d=copy.deepcopy(BASE);d['parcels']=d['parcels'][1:]
        d['provenance']['gis_counts']['0239360701']=0
        r=self.outcome(d);self.assertEqual(r['rows'][0]['outcome'],'NOT_FOUND_IN_BOUNDED_GIS_QUERY')
    def test_two_gis_candidates_blocked(self):
        d=copy.deepcopy(BASE);p=copy.deepcopy(d['parcels'][0]);p['PROP_ID']=993000
        d['parcels'].append(p);d['provenance']['gis_counts']['0239360701']=2
        r=self.outcome(d);self.assertEqual(r['rows'][0]['outcome'],'AMBIGUOUS_GIS_GEOGRAPHIC_ID')
        self.assertIsNone(r['rows'][0]['public_property_reference'])
    def test_repeated_invalid_nulls(self):self.reject(lambda d:d['permits'][0].update(jurisdiction=None))
    def test_sample_size_limit(self):self.reject(lambda d:d.update(permits=d['permits']*35))

if __name__=='__main__':unittest.main()
