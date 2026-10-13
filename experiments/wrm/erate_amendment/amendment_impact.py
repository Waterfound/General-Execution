"""Bounded read-only E-Rate bid amendment impact triage.

Consumes a MANUALLY TRANSCRIBED official procurement-page event fixture.
This is NOT an authenticated site adapter or a contractual determination.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse


class EvidenceError(ValueError):
    pass


def _time(raw: str) -> datetime:
    if not isinstance(raw, str) or not raw.endswith(('Z', '+00:00')):
        raise EvidenceError('time must be UTC RFC3339')
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as error:
        raise EvidenceError('invalid time') from error
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise EvidenceError('time must be UTC')
    return parsed


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise EvidenceError(f'{field} must be nonempty bounded string')
    return value.strip()


def classify_attachment(name: str) -> str:
    s = name.casefold()
    if 'notice of intent to award' in s or 'award notice' in s:
        return 'AWARD_NOTICE'
    if 'revised' in s and ('price schedule' in s or 'pricing schedule' in s):
        return 'REVISED_PRICE_SCHEDULE'
    if 'addendum' in s:
        return 'ADDENDUM_DOCUMENT'
    return 'UNKNOWN_REQUIRES_REVIEW'


def evaluate(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict) or snapshot.get('schema') != 'cr001.official-amendment-transcription.v1':
        raise EvidenceError('unsupported snapshot schema')
    if snapshot.get('evidence_class') != 'MANUALLY_TRANSCRIBED_PUBLIC_WEB_PAGE':
        raise EvidenceError('provenance class missing or overstated')
    u = urlparse(_string(snapshot.get('source_url'), 'source_url'))
    if u.scheme != 'https' or u.hostname != 'oregonbuys.gov' or not u.path.startswith('/bso/external/bidDetail.sda'):
        raise EvidenceError('source url is not an expected official procurement page')
    ident = _string(snapshot.get('solicitation_id'), 'solicitation_id')
    form = _string(snapshot.get('fcc_form_470'), 'fcc_form_470')
    bid = _time(snapshot.get('bid_opening_utc'))
    observed = _time(snapshot.get('observed_as_of_utc'))
    events = snapshot.get('events')
    if not isinstance(events, list) or not events or len(events) > 64:
        raise EvidenceError('events missing or over limit')
    all_names: set[str] = set()
    reports = []
    last_time = None
    for number, event in enumerate(events, start=1):
        if not isinstance(event, dict) or type(event.get('sequence')) is not int or event['sequence'] != number:
            raise EvidenceError('event sequence missing, duplicated or noncontiguous')
        occurred = _time(event.get('occurred_at_utc'))
        if occurred > observed or (last_time is not None and occurred <= last_time):
            raise EvidenceError('event occurred after observation or out of chronological order')
        last_time = occurred
        attachments = event.get('added_attachments')
        if not isinstance(attachments, list) or not attachments or len(attachments) > 32:
            raise EvidenceError('no complete added_attachments evidence')
        if event.get('note_relation') != 'ADDED_ATTACHMENT_ENTRIES_TRANSCRIBED_FROM_OFFICIAL_AMENDMENT_NOTE':
            raise EvidenceError('attachment set not bound to official note')
        analyzed = []
        for item in attachments:
            name = _string(item, 'attachment')
            key = name.casefold()
            if key in all_names:
                raise EvidenceError('duplicate document key across event log')
            all_names.add(key)
            analyzed.append({'filename': name, 'category': classify_attachment(name), 'document_contents_verified': False})
        prebid = occurred <= bid
        has_price = any(x['category'] == 'REVISED_PRICE_SCHEDULE' for x in analyzed)
        has_unknown = any(x['category'] == 'UNKNOWN_REQUIRES_REVIEW' for x in analyzed)
        has_bid_doc = any(x['category'] in {'REVISED_PRICE_SCHEDULE', 'ADDENDUM_DOCUMENT'} for x in analyzed)
        if not prebid:
            disposition = 'AFTER_BID_OPENING_HISTORICAL_ONLY'
        elif has_unknown:
            disposition = 'EVIDENCE_REVIEW_REQUIRED'
        elif has_price:
            disposition = 'POTENTIAL_PRICE_SCHEDULE_IMPACT_VERIFY_CONTENTS'
        elif has_bid_doc:
            disposition = 'POTENTIAL_ADDENDUM_IMPACT_VERIFY_CONTENTS'
        else:
            disposition = 'NON_BID_DOCUMENT'
        reports.append({
            'sequence': number, 'occurred_at_utc': occurred.isoformat().replace('+00:00','Z'),
            'relative_to_bid_opening': 'PRE_BID' if prebid else 'POST_BID',
            'disposition': disposition,
            'attachments': analyzed,
            'buyer_action': 'REVIEW_SOURCE_AND_VERIFY_CURRENT_DEADLINE' if prebid and has_bid_doc and not has_unknown and observed < bid else 'NO_CURRENT_BID_ACTION_INFERRED',
        })
    return {
        'schema': 'cr001.amendment-impact-report.v1', 'solicitation_id': ident, 'fcc_form_470': form,
        'source_url': snapshot['source_url'], 'evidence_class': snapshot['evidence_class'],
        'authenticated_source_bytes': False, 'document_bytes_inspected': False,
        'accepted_payment_or_bid_submission': False,
        'events': reports,
        'pre_bid_impact_events': sum(r['relative_to_bid_opening'] == 'PRE_BID' and r['disposition'].startswith('POTENTIAL') for r in reports),
        'current_bid_action_events': sum(r['buyer_action'].startswith('REVIEW_SOURCE') for r in reports),
        'historical_snapshot': observed >= bid,
        'caveat': 'Names and official amendment notes only. Bid opening date is not verified submission deadline. No prices, quantities, compliance or legal effect verified. Revalidate directly against official procurement source.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Offline read-only procurement amendment triage from manually transcribed events')
    parser.add_argument('fixture', type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.fixture.read_text(encoding='utf-8'))), indent=2))


if __name__ == '__main__':
    main()
