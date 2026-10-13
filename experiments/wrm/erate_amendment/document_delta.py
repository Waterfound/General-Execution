"""Fail-closed, offline document-byte RFP/addendum evidence probe.

This is a CANDIDATE. It does not authenticate procurement provider identity,
legal consequences, competitor superiority, customer demand, or deadlines.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

MAX_PDF_BYTES = 16_000_000
MAX_PAGES = 40
MIN_PAGE_CHARS = 25

class EvidenceError(ValueError):
    pass

@dataclass(frozen=True)
class Page:
    number: int
    text: str
    digest: str

@dataclass(frozen=True)
class Document:
    sha256: str
    size: int
    pages: tuple[Page, ...]
    source_url: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean(text: str) -> str:
    return ' '.join(text.split())


def _url(url: str) -> str:
    if not isinstance(url, str):
        raise EvidenceError('expected original HTTPS URL')
    p = urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.fragment:
        raise EvidenceError('expected original HTTPS URL')
    return url


def load_pdf_bytes(path: str | Path, *, source_url: str, expected_sha256: str | None = None) -> Document:
    """Load actual bytes locally; no automatic downloads, no OCR or page guessing."""
    _url(source_url)
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        raise EvidenceError('no regular input file')
    raw = p.read_bytes()
    if len(raw) < 90 or len(raw) > MAX_PDF_BYTES or not raw.startswith(b'%PDF-'):
        raise EvidenceError('input missing, oversized or not a PDF')
    digest = _sha(raw)
    if expected_sha256 is not None and (not re.fullmatch(r'[a-f0-9]{64}', expected_sha256) or digest != expected_sha256):
        raise EvidenceError('frozen exact PDF hash mismatch')
    try:
        import fitz
    except ImportError as exc:
        raise EvidenceError('PyMuPDF free dependency not installed') from exc
    try:
        pdf = fitz.open(stream=raw, filetype='pdf')
        with pdf:
            if pdf.needs_pass or not 0 < len(pdf) <= MAX_PAGES:
                raise EvidenceError('encrypted, empty or over-limit PDF')
            pages = []
            for n, page in enumerate(pdf, 1):
                text = _clean(page.get_text('text', sort=True))
                if len(text) < MIN_PAGE_CHARS:
                    raise EvidenceError('missing/unreadable page; OCR/manual review required')
                pages.append(Page(n, text, _sha(text.encode('utf-8'))))
    except EvidenceError:
        raise
    except Exception as exc:
        raise EvidenceError('invalid/corrupt PDF content') from exc
    return Document(digest, len(raw), tuple(pages), source_url)


def _date(text: str) -> date | None:
    mt = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(20\d{2})\b', text, re.I)
    if not mt: return None
    month = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'].index(mt.group(1).lower()) + 1
    try: return date(int(mt.group(3)), month, int(mt.group(2)))
    except ValueError: return None


def _deadline(doc: Document, *, kind: str) -> dict:
    """Only dates adjacent to a source deadline label; never infer times."""
    pat = r'\b(?:proposal is due by|RFP Responses Due|Response Due Date|BID DUE DATE)\b'
    matches = []
    for page in doc.pages:
        for match in re.finditer(pat, page.text, re.I):
            # Extract from same sentence / row within a bounded proximity.
            segment = page.text[match.end():match.end()+115]
            parsed = _date(segment)
            if parsed:
                matches.append({'date':parsed.isoformat(), 'page': page.number,
                                'matched_label':match.group(0), 'page_text_sha256':page.digest})
    values={x['date'] for x in matches}
    return {'state':'UNAVAILABLE_OR_AMBIGUOUS' if len(values)!=1 else 'DATE_OBSERVED_TIME_UNVERIFIED',
            'date':next(iter(values)) if len(values)==1 else None,
            'matches':matches}


def _evidence(page: Page, match: re.Match, *, key: str) -> dict:
    # Only page id + hashed compact source hit, not entire copyrighted content.
    fragment=page.text[max(0, match.start()-25):min(len(page.text),match.end()+65)]
    return {'category':key,'page':page.number,'page_text_sha256':page.digest,
            'source_text_span':[match.start(),match.end()],
            'matched_fragment_sha256':_sha(fragment.encode('utf-8')),
            'match_phrase_sha256':_sha(match.group(0).encode('utf-8'))}


def analyze(original: Document, addendum: Document, *, rfp_id: str, observed_on: str, original_binding: str = 'MANUAL_SOURCE_ASSOCIATION') -> dict:
    if original.sha256 == addendum.sha256:
        raise EvidenceError('original equals addendum: no independent pair')
    if not re.fullmatch(r'\d{4,12}', rfp_id):
        raise EvidenceError('invalid RFP id')
    if original_binding not in {'MANUAL_SOURCE_ASSOCIATION','PROVIDER_AUTHENTICATED'}:
        raise EvidenceError('unknown source binding')
    if original_binding == 'PROVIDER_AUTHENTICATED':
        raise EvidenceError('provider source authentication cannot be self-asserted')
    try: observed=date.fromisoformat(observed_on)
    except (ValueError,TypeError) as exc: raise EvidenceError('bad ISO observation date') from exc
    if not any(re.search(r'\bRFP\s*#?\s*'+re.escape(rfp_id)+r'\b',p.text,re.I) for p in addendum.pages):
        raise EvidenceError('addendum does not contain matching RFP identifier')
    all_original=' '.join(p.text for p in original.pages)
    all_addendum=' '.join(p.text for p in addendum.pages)
    ack_pattern=r'\b(?:each\s+)?(?:proposer|bidder|responder)?\s*shall\s+acknowledge\s+receipt\s+of\s+the\s+Addendum\b'
    ack_before=bool(re.search(ack_pattern,all_original,re.I))
    ack_after=[]; rejection=[]; precedence=[]
    for p in addendum.pages:
        for m in re.finditer(ack_pattern,p.text,re.I):ack_after.append(_evidence(p,m,key='ACKNOWLEDGEMENT'))
        for m in re.finditer(r'\bFailing\s+to\s+acknowledge\s+(?:this\s+)?Addendum\b.{0,125}?\bmay\s+cause\s+the\s+response\s+to\s+be\s+rejected\b',p.text,re.I):
            rejection.append(_evidence(p,m,key='CONDITIONAL_REJECTION'))
        for m in re.finditer(r'\bfinal\s+and\s+official\s+timeline\b',p.text,re.I):
            precedence.append(_evidence(p,m,key='TIMELINE_PRIORITY'))
    old_due=_deadline(original,kind='original')
    new_due=_deadline(addendum,kind='addendum')
    if old_due['date'] and new_due['date']:
        due_status='DATE_UNCHANGED_TIME_UNVERIFIED' if old_due['date']==new_due['date'] else 'DATE_CHANGED_VERIFY_ACTUAL_DEADLINE'
    else:
        due_status='INSUFFICIENT_BID_DEADLINE_EVIDENCE'
    date_current=(new_due['date'] or old_due['date'])
    historical = (date.fromisoformat(date_current)<observed) if date_current else None
    ack_status=('ADDED_IN_ADDENDUM' if ack_after and not ack_before else
                'REITERATED_OR_PREEXISTING' if ack_after else 'NOT_OBSERVED')
    return {
        'schema':'cr001.verified-pdf-byte-contract.v1', 'rfp_id':rfp_id,
        'documents':{
            'original':{'sha256':original.sha256,'pages':len(original.pages),'size':original.size,'source_url':original.source_url},
            'addendum':{'sha256':addendum.sha256,'pages':len(addendum.pages),'size':addendum.size,'source_url':addendum.source_url}},
        'source_binding':{'level':original_binding,'provider_authenticated':False},
        'acknowledgement':{'status':ack_status,'conditional_rejection_language_observed':bool(rejection),
                           'evidence':ack_after,'rejection_evidence':rejection},
        'official_timeline_precedence':{'observed':bool(precedence),'evidence':precedence},
        'deadline':{'original':old_due,'addendum':new_due,'comparison':due_status,
                    'time_comparison':'NOT_VERIFIED',
                    'historical':historical,
                    'active_bid_proven':False},
        'removals_proven':False,'price_or_quantity_changes_proven':False,
        'content_extracted_from_original_pdf_bytes':True,
        'content_extracted_from_addendum_pdf_bytes':True,
        'human_review_required':True,
        'commercial_differentiation_verified':False,
        'note':'Candidate reads actual local PDF bytes; no authentic provider retrieval, deadline validation, legal determination, installed competitor parity or buyer payment.',
    }


def main() -> None:
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument('original');a.add_argument('addendum')
    a.add_argument('--original-url',required=True);a.add_argument('--addendum-url',required=True)
    a.add_argument('--original-sha256');a.add_argument('--addendum-sha256')
    a.add_argument('--rfp-id',required=True);a.add_argument('--observed-on',required=True)
    v=a.parse_args()
    x=load_pdf_bytes(v.original,source_url=v.original_url,expected_sha256=v.original_sha256)
    y=load_pdf_bytes(v.addendum,source_url=v.addendum_url,expected_sha256=v.addendum_sha256)
    print(json.dumps(analyze(x,y,rfp_id=v.rfp_id,observed_on=v.observed_on),indent=2,sort_keys=True))

if __name__=='__main__':main()
