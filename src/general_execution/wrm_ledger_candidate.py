"""Fail-closed, read-only PR evidence status candidate."""
import hashlib
import json

def summarize(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('checks'), list):
        raise ValueError('missing check receipts')
    checks = snapshot['checks']
    names = [x.get('name') for x in checks]
    if any(not x for x in names) or len(set(names)) != len(names):
        raise ValueError('duplicate or unnamed checks')
    failures = sorted(x['name'] for x in checks if x.get('conclusion') not in ('success', None))
    pending = sorted(x['name'] for x in checks if x.get('status') != 'completed')
    return {'evidence_level':'SUPPLIED_SNAPSHOT', 'failed_checks':failures,
            'pending_checks':pending, 'customer_roi':None, 'first_revenue':None,
            'snapshot_sha256':hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()}
