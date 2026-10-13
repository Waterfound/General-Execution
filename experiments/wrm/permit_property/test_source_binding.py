import copy
import unittest
from urllib.parse import urlencode
from source_binding import verified_query_urls, SourceBindingError
A = 'https://data.austintexas.gov/resource/3syk-w9eu.json?'
G = 'https://gis.traviscountytx.gov/server1/rest/services/Boundaries_and_Jurisdictions/TCAD_public/MapServer/0/query?'
IDS = ('0239360701', '0339500820')
def feature(g):
    return G + urlencode({'where':f"geo_id='{g}'",'outFields':'geo_id,PROP_ID,situs_address,situs_zip','returnGeometry':'false','f':'json'})
def count(g):
    return G + urlencode({'where':f"geo_id='{g}'",'returnCountOnly':'true','f':'json'})
def snapshot():
    return {'austin_url': A+urlencode({'$select':'permit_number,tcad_id,issue_date,permit_class_mapped,jurisdiction','$where':'tcad_id IS NOT NULL','$limit':'3'}),
        'austin_completeness_contract':'EXPLICIT_LIMIT_3_NOT_EXHAUSTIVE_SOURCE',
        'gis_completeness_contract':'TWO_EXACT_GEO_ID_COUNT_QUERIES_EACH_COUNT_ONE',
        'gis_url':feature(IDS[0]), 'gis_url_second':feature(IDS[1]),
        'gis_counts':{IDS[0]:1,IDS[1]:1},'gis_count_urls':{g:count(g) for g in IDS}}
class SourceBindingTests(unittest.TestCase):
    def test_sample(self):
        x=snapshot(); self.assertEqual(verified_query_urls(x,IDS,3),{g:feature(g) for g in IDS})
    def reject(self, change):
        x=copy.deepcopy(snapshot());change(x)
        with self.assertRaises(SourceBindingError): verified_query_urls(x,IDS,3)
    def test_feature_wrong_id(self): self.reject(lambda x:x.update(gis_url_second=feature(IDS[0])))
    def test_feature_wrong_host(self): self.reject(lambda x:x.update(gis_url_second=x['gis_url_second'].replace('gis.traviscountytx.gov','evil.example')))
    def test_feature_wrong_path(self): self.reject(lambda x:x.update(gis_url=x['gis_url'].replace('MapServer/0','MapServer/9')))
    def test_feature_wrong_field(self): self.reject(lambda x:x.update(gis_url=x['gis_url'].replace('situs_zip','parcel_owner')))
    def test_feature_geometry_only(self): self.reject(lambda x:x.update(gis_url=x['gis_url'].replace('false','true')))
    def test_count_wrong_id(self): self.reject(lambda x:x['gis_count_urls'].update({IDS[1]:count(IDS[0])}))
    def test_count_wrong_count_flag(self): self.reject(lambda x:x['gis_count_urls'].update({IDS[1]:x['gis_count_urls'][IDS[1]].replace('true','false')}))
    def test_count_missing(self): self.reject(lambda x:x['gis_count_urls'].pop(IDS[1]))
    def test_count_extra(self): self.reject(lambda x:x['gis_count_urls'].update({'9999999999':count('9999999999')}))
    def test_unexpected_param(self): self.reject(lambda x:x.update(gis_url=x['gis_url']+'&returnCountOnly=true'))
    def test_duplicate_where(self): self.reject(lambda x:x.update(gis_url=x['gis_url']+'&where=geo_id%3D%27fake%27'))
    def test_wrong_austin_filter(self): self.reject(lambda x:x.update(austin_url=x['austin_url'].replace('NOT+NULL','NULL')))
    def test_wrong_austin_limit(self): self.reject(lambda x:x.update(austin_url=x['austin_url'].replace('limit=3','limit=2')))
    def test_austin_zip_not_selected(self): self.reject(lambda x:x.update(austin_url=x['austin_url'].replace('jurisdiction','original_zip')))
    def test_austin_extra_query(self): self.reject(lambda x:x.update(austin_url=x['austin_url']+'&x=1'))
    def test_austin_wrong_host(self): self.reject(lambda x:x.update(austin_url=x['austin_url'].replace('austintexas.gov','austintexas.gov.evil.test')))
    def test_completeness_overclaim(self): self.reject(lambda x:x.update(austin_completeness_contract='FULL_SOURCE_EXHAUSTIVE'))
    def test_one_geo_without_contract(self):
        with self.assertRaises(SourceBindingError):verified_query_urls(snapshot(),IDS[:1],3)
    def test_four_permits(self):
        with self.assertRaises(SourceBindingError):verified_query_urls(snapshot(),IDS,4)
    def test_unordered_ids(self):
        with self.assertRaises(SourceBindingError):verified_query_urls(snapshot(),IDS[::-1],3)
    def test_gis_count_not_one(self):self.reject(lambda x:x['gis_counts'].update({IDS[0]:2}))
    def test_missing_second_url(self):self.reject(lambda x:x.pop('gis_url_second'))
    def test_https_port(self):self.reject(lambda x:x.update(gis_url=x['gis_url'].replace('.gov/', '.gov:443/')))
    def test_userinfo(self):self.reject(lambda x:x.update(gis_url=x['gis_url'].replace('https://','https://attacker@')))
if __name__ == '__main__':unittest.main()
