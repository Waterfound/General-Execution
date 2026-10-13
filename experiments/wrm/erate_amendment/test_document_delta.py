from __future__ import annotations
import hashlib
import io
import pathlib
import sys
import tempfile
import textwrap
import unittest
from contextlib import contextmanager

from reportlab.pdfgen.canvas import Canvas
from document_delta import load_pdf_bytes, analyze, EvidenceError

U1='https://example.org/rfp-original.pdf'
U2='https://example.org/rfp-addendum-1.pdf'
ORIG=[
 'INTERNET SERVICE REQUEST. Required throughput 20 to 100 GBPS. Proposal is due by 1:00 pm local time on February 20th, 2023. All questions must be received on February 3, 2023.',
 'Acceptable Contract Form. The District accepts a representative contract. Submitted bids must include a detailed implementation plan.'
]
AMEND=[
 'Addendum #1 for RFP 21372 Internet Services. Each proposer shall acknowledge receipt of the Addendum in your proposal response. Failing to acknowledge this Addendum on the form may cause the response to be rejected.',
 'Clarification of Timeline: Below is the final and official timeline for this RFP. RFP Responses Due February 20, 2023. Pre-proposal meeting information updated.'
]

def pdf_bytes(pages):
    b=io.BytesIO();c=Canvas(b,pagesize=(612,792),pageCompression=0)
    for pg in pages:
        t=c.beginText(40,725)
        for line in textwrap.wrap(pg, width=84, break_long_words=False):t.textLine(line)
        c.drawText(t);c.showPage()
    c.save();return b.getvalue()

@contextmanager
def pair(original=None,addendum=None):
    with tempfile.TemporaryDirectory() as temp:
        a=pathlib.Path(temp)/'original.pdf';b=pathlib.Path(temp)/'addendum.pdf'
        a.write_bytes(pdf_bytes(ORIG if original is None else original))
        b.write_bytes(pdf_bytes(AMEND if addendum is None else addendum))
        yield a,b

def load(a,b):
    return load_pdf_bytes(a,source_url=U1),load_pdf_bytes(b,source_url=U2)

class ByteExtractionAndFailureTests(unittest.TestCase):
    def test_real_pdf_byte_extraction(self):
        with pair() as (a,b):
            x,y=load(a,b);self.assertEqual((len(x.pages),len(y.pages)),(2,2));self.assertEqual(x.sha256,hashlib.sha256(a.read_bytes()).hexdigest())
    def test_expected_digest_bound(self):
        with pair() as (a,b):
            x=load_pdf_bytes(a,source_url=U1,expected_sha256=hashlib.sha256(a.read_bytes()).hexdigest());self.assertEqual(len(x.pages),2)
    def test_wrong_digest_rejected(self):
        with pair() as (a,b):
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url=U1,expected_sha256='0'*64)
    def test_bad_digest_format(self):
        with pair() as (a,b):
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url=U1,expected_sha256='INVALID')
    def test_no_file(self):
        with self.assertRaises(EvidenceError):load_pdf_bytes('/path/that/does/not/exist',source_url=U1)
    def test_non_pdf(self):
        with tempfile.TemporaryDirectory() as temp:
            p=pathlib.Path(temp)/'x.pdf';p.write_bytes(b'Not a PDF'*20)
            with self.assertRaises(EvidenceError):load_pdf_bytes(p,source_url=U1)
    def test_truncated_pdf(self):
        with pair() as (a,b):
            a.write_bytes(a.read_bytes()[:140])
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url=U1)
    def test_page_without_extractable_text(self):
        with pair(original=['A page with enough chars and other explanatory details.','']) as (a,b):
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url=U1)
    def test_reject_http_source(self):
        with pair() as (a,b):
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url='http://example.org/orig')
    def test_reject_hostname_suffix_trap(self):
        with pair() as (a,b):
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url='https://user:pass@example.org/doc')
    def test_corrupted_raw_overlimit(self):
        with pair() as (a,b):
            a.write_bytes(b'%PDF-'+b'A'*16000000)
            with self.assertRaises(EvidenceError):load_pdf_bytes(a,source_url=U1)

class ObligationDiffTests(unittest.TestCase):
    def result(self,original=None,addendum=None,now='2026-10-12'):
        with pair(original,addendum) as (a,b):
            x,y=load(a,b)
            return analyze(x,y,rfp_id='21372',observed_on=now)
    def test_ack_added(self):
        v=self.result()
        self.assertEqual(v['acknowledgement']['status'],'ADDED_IN_ADDENDUM')
        self.assertTrue(v['acknowledgement']['conditional_rejection_language_observed'])
        self.assertEqual(v['acknowledgement']['evidence'][0]['page'],1)
    def test_original_preexisting_ack(self):
        old=ORIG.copy();old[1]+=' Each proposer shall acknowledge receipt of the Addendum in your proposal response.'
        self.assertEqual(self.result(original=old)['acknowledgement']['status'],'REITERATED_OR_PREEXISTING')
    def test_no_fabricated_rejection(self):
        add=[AMEND[0].replace('may cause the response to be rejected','the response will be reviewed manually'),AMEND[1]]
        self.assertFalse(self.result(addendum=add)['acknowledgement']['conditional_rejection_language_observed'])
    def test_timeline_priority(self):self.assertTrue(self.result()['official_timeline_precedence']['observed'])
    def test_no_timeline_priority(self):
        add=[AMEND[0], AMEND[1].replace('the final and official timeline','the chronology of this meeting')]
        self.assertFalse(self.result(addendum=add)['official_timeline_precedence']['observed'])
    def test_original_and_addendum_deadline(self):
        v=self.result();self.assertEqual(v['deadline']['original']['date'],'2023-02-20');self.assertEqual(v['deadline']['addendum']['date'],'2023-02-20')
        self.assertEqual(v['deadline']['comparison'],'DATE_UNCHANGED_TIME_UNVERIFIED')
        self.assertEqual(v['deadline']['time_comparison'],'NOT_VERIFIED')
    def test_changed_deadline(self):
        add=[AMEND[0],AMEND[1].replace('February 20, 2023','February 24, 2023')]
        self.assertEqual(self.result(addendum=add)['deadline']['comparison'],'DATE_CHANGED_VERIFY_ACTUAL_DEADLINE')
    def test_missing_deadline(self):
        add=[AMEND[0],AMEND[1].replace('RFP Responses Due February 20, 2023','No deadline evidence here at all')]
        self.assertEqual(self.result(addendum=add)['deadline']['comparison'],'INSUFFICIENT_BID_DEADLINE_EVIDENCE')
    def test_historical_not_actionable(self):
        x=self.result()
        self.assertTrue(x['deadline']['historical']);self.assertFalse(x['deadline']['active_bid_proven'])
    def test_not_yet_expired_is_not_proof_current_bid(self):
        x=self.result(now='2023-02-01');self.assertFalse(x['deadline']['historical']);self.assertFalse(x['deadline']['active_bid_proven'])
    def test_wrong_addendum_id(self):
        with pair(addendum=[AMEND[0].replace('21372','21373'),AMEND[1]]) as (a,b):
            with self.assertRaises(EvidenceError):analyze(*load(a,b),rfp_id='21372',observed_on='2026-10-12')
    def test_identical_document_pair_rejected(self):
        with pair() as (a,b):
            x=load_pdf_bytes(a,source_url=U1)
            with self.assertRaises(EvidenceError):analyze(x,x,rfp_id='21372',observed_on='2026-10-12')
    def test_cannot_self_assert_provider_provenance(self):
        with pair() as (a,b):
            with self.assertRaises(EvidenceError):analyze(*load(a,b),rfp_id='21372',observed_on='2026-10-12',original_binding='PROVIDER_AUTHENTICATED')
    def test_unsupported_id_and_observation(self):
        with pair() as (a,b):
            x,y=load(a,b)
            for kwargs in ({'rfp_id':'21372bad','observed_on':'2026-10-12'},{'rfp_id':'21372','observed_on':'12 Oct 2026'}):
                with self.assertRaises(EvidenceError):analyze(x,y,**kwargs)
    def test_removals_not_inferred(self):
        v=self.result();self.assertFalse(v['removals_proven']);self.assertFalse(v['price_or_quantity_changes_proven'])
    def test_provenance_hashes_per_page(self):
        v=self.result();z=v['acknowledgement']['evidence'][0]
        self.assertRegex(z['page_text_sha256'],r'^[a-f0-9]{64}$');self.assertRegex(z['match_phrase_sha256'],r'^[a-f0-9]{64}$')
    def test_no_commercial_claims(self):
        v=self.result();self.assertTrue(v['human_review_required']);self.assertFalse(v['commercial_differentiation_verified']);self.assertFalse(v['source_binding']['provider_authenticated'])

if __name__=='__main__':unittest.main(verbosity=2)
