"""Read-only RMA-DIST channel-source parity; no network, buyer contact or authority."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Status = Literal['OPEN', 'CLOSED', 'UNKNOWN']

@dataclass(frozen=True)
class SourceCase:
    case_id: str
    source_url: str
    primary_url: str
    discovery_status: Status
    primary_status: Status
    source_checked: str
    budget_usd: str | None = None


CASES = (
    SourceCase('upwork-permit-30',
        'https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/',
        'https://www.upwork.com/freelance-jobs/apply/Python-Developer-for-Permit-Portal-Scrapers_~022090116979619755021/',
        'OPEN', 'CLOSED', '2026-10-12', '30'),
    SourceCase('algora-nuclei-6674',
        'https://algora.io/projectdiscovery/bounties?status=open',
        'https://github.com/projectdiscovery/nuclei/issues/6674',
        'OPEN', 'CLOSED', '2026-10-12', '100'),
    SourceCase('algora-nuclei-6532',
        'https://algora.io/projectdiscovery/bounties?status=open',
        'https://github.com/projectdiscovery/nuclei/issues/6532',
        'OPEN', 'CLOSED', '2026-10-12', '100'),
)


def assess(case: SourceCase) -> dict:
    """Primary-source closure vetoes secondary-marketplace eligibility.

    Sources represent an inspected frozen snapshot, not a live monitor.
    Secondary source status OPEN for Upwork is the historical listing, not
    a claim that Upwork itself currently shows OPEN.
    """
    if type(case) is not SourceCase:
        raise ValueError('SourceCase required')
    if not case.case_id or not case.source_url.startswith('https://') or not case.primary_url.startswith('https://'):
        raise ValueError('case ID and HTTPS source URLs required')
    if case.discovery_status not in ('OPEN', 'CLOSED', 'UNKNOWN') or case.primary_status not in ('OPEN', 'CLOSED', 'UNKNOWN'):
        raise ValueError('invalid source status')
    if case.budget_usd is not None:
        try:
            d = Decimal(case.budget_usd)
        except (TypeError, ValueError, ArithmeticError):
            raise ValueError('invalid posted budget') from None
        if not d.is_finite() or d <= 0:
            raise ValueError('invalid posted budget')
    if case.primary_status == 'CLOSED':
        verdict = 'CLOSED_CURRENT_BUYER_OPPORTUNITY'
    elif case.primary_status == 'UNKNOWN':
        verdict = 'UNVERIFIED_PRIMARY_SOURCE'
    elif case.discovery_status == 'OPEN':
        verdict = 'CONDITIONAL_NEEDS_COMMERCIAL_VALIDATION'
    else:
        verdict = 'INCONSISTENT_OR_CLOSED_DISCOVERY_SOURCE'
    return {
        'case_id': case.case_id,
        'inspection_date': case.source_checked,
        'primary_source': case.primary_url,
        'secondary_source': case.source_url,
        'primary_status': case.primary_status,
        'discovery_status': case.discovery_status,
        'verdict': verdict,
        'currently_accessible': verdict == 'CONDITIONAL_NEEDS_COMMERCIAL_VALIDATION',
        'posted_budget_usd_historical': case.budget_usd,
        'waterfound_buyer_wtp_verified': False,
        'waterfound_revenue_verified': False,
        'buyer_contact_authorized': False,
        'automatic_publication_authorized': False,
        'runtime_monitor_running': False,
    }


def current_screen() -> dict:
    results = [assess(c) for c in CASES]
    return {'schema':'rma.dist.primary_source_parity.v1', 'source_snapshot_date':'2026-10-12',
            'cases':results, 'currently_accessible_candidates':sum(int(x['currently_accessible']) for x in results),
            'disposition':'NO_CURRENTLY_ACCESSIBLE_BUYER_IN_SCREENED_CASES',
            'revenue_usd_observed':'0', 'authority_created':False,
            'next_direct_commercial_predicate':'lawful_open_buyer_job_and_independent_acceptance_proof'}


if __name__ == '__main__':
    import json
    print(json.dumps(current_screen(), sort_keys=True, indent=2))
