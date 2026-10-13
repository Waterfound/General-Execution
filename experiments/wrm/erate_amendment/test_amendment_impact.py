import copy, json, pathlib, unittest
from amendment_impact import evaluate, EvidenceError, classify_attachment

FX=json.loads((pathlib.Path(__file__).parent/'oregon_2025_grounded.json').read_text())
class TestOfficialGrounded(unittest.TestCase):
    def test_source_case_expected(self):
        out=evaluate(FX)
        self.assertEqual(out['pre_bid_impact_events'],1)
        self.assertEqual(out['events'][0]['disposition'],'POTENTIAL_PRICE_SCHEDULE_IMPACT_VERIFY_CONTENTS')
        self.assertEqual(out['events'][1]['disposition'],'AFTER_BID_OPENING_HISTORICAL_ONLY')
        self.assertEqual(out['events'][1]['buyer_action'],'NO_CURRENT_BID_ACTION_INFERRED')
        self.assertFalse(out['authenticated_source_bytes'])
        self.assertFalse(out['document_bytes_inspected'])
    def test_naive_all_amendments_raises_false_bid_event(self):
        self.assertEqual(len(FX['events']), 2)
        self.assertEqual(evaluate(FX)['pre_bid_impact_events'],1)
    def test_classes(self):
        self.assertEqual(classify_attachment('Notice of Intent to Award: X'),'AWARD_NOTICE')
        self.assertEqual(classify_attachment('REVISED Price Schedule'),'REVISED_PRICE_SCHEDULE')
        self.assertEqual(classify_attachment('other attachment'),'UNKNOWN_REQUIRES_REVIEW')
    def fail(self, fn):
        x=copy.deepcopy(FX);fn(x)
        with self.assertRaises(EvidenceError):evaluate(x)
    def test_wrong_provenance(self):self.fail(lambda x:x.update(evidence_class='RAW_PROVIDER_AUTHENTICATED'))
    def test_wrong_host(self):self.fail(lambda x:x.update(source_url='https://oregonbuys.gov.evil.test/fake'))
    def test_http_host(self):self.fail(lambda x:x.update(source_url='http://oregonbuys.gov/bso/external/bidDetail.sda'))
    def test_duplicate_sequence(self):self.fail(lambda x:x['events'][1].update(sequence=1))
    def test_missing_sequence(self):self.fail(lambda x:x['events'][1].pop('sequence'))
    def test_out_of_order(self):self.fail(lambda x:x['events'][1].update(occurred_at_utc='2024-01-01T00:00:00Z'))
    def test_future_event(self):self.fail(lambda x:x['events'][1].update(occurred_at_utc='2027-01-01T00:00:00Z'))
    def test_duplicate_attachment(self):self.fail(lambda x:x['events'][1].update(added_attachments=x['events'][0]['added_attachments']))
    def test_missing_attachment(self):self.fail(lambda x:x['events'][0].update(added_attachments=[]))
    def test_unbound_attachments(self):self.fail(lambda x:x['events'][0].update(note_relation='NOT_VERIFIED'))
    def test_non_utc(self):self.fail(lambda x:x.update(bid_opening_utc='2025-02-28T14:30:00-08:00'))
    def test_bool_sequence(self):self.fail(lambda x:x['events'][0].update(sequence=True))
    def test_unknown_prebid_requires_review(self):
        x=copy.deepcopy(FX);x['events'][0]['added_attachments']=['unidentified technical document'];z=evaluate(x)
        self.assertEqual(z['events'][0]['disposition'],'EVIDENCE_REVIEW_REQUIRED')
        self.assertEqual(z['events'][0]['buyer_action'],'NO_CURRENT_BID_ACTION_INFERRED')
    def test_post_bid_revised_schedule_no_current_action(self):
        x=copy.deepcopy(FX);x['events'][1]['added_attachments']=['REVISED Attachment C Price Schedule'];z=evaluate(x)
        self.assertEqual(z['events'][1]['disposition'],'AFTER_BID_OPENING_HISTORICAL_ONLY')
        self.assertEqual(z['events'][1]['buyer_action'],'NO_CURRENT_BID_ACTION_INFERRED')

if __name__=='__main__':unittest.main()
