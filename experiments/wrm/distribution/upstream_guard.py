"""Source-bound reenactment only: PowerShell issue #19621 / merged PR #19622."""
import re

ISSUE = 'https://github.com/PowerShell/PowerShell/issues/19621'
FIX = 'https://github.com/PowerShell/PowerShell/pull/19622'
BEFORE = 'if (response.StatusCode is HttpStatusCode.Conflict && response.Headers.TryGetValues(HttpKnownHeaderNames.RetryAfter, out IEnumerable<string> retryAfter))'
AFTER = BEFORE.replace('HttpStatusCode.Conflict', 'HttpStatusCode.TooManyRequests')
STATUS = {'Conflict': 409, 'TooManyRequests': 429}


def guarded_status(line):
    if not isinstance(line, str):
        raise ValueError('source must be text')
    matches = re.findall(r'response\.StatusCode\s+is\s+HttpStatusCode\.(\w+)', line)
    if len(matches) != 1 or matches[0] not in STATUS or 'Headers.TryGetValues(HttpKnownHeaderNames.RetryAfter' not in line:
        raise ValueError('ambiguous or incomplete upstream snippet')
    return STATUS[matches[0]]


def response_wait(line, status, retry_after, fallback):
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError('bad status')
    if any(type(x) is not int or x < 0 for x in (retry_after, fallback)):
        raise ValueError('bad interval')
    return retry_after if status == guarded_status(line) else fallback


def memo():
    prior = response_wait(BEFORE, 429, 2, 5)
    fixed = response_wait(AFTER, 429, 2, 5)
    assert (prior, fixed) == (5, 2), 'upstream golden mismatch'
    return {'case': ISSUE, 'reference_fix': FIX,
            'cause': '409 Conflict comparison gates a 429 Retry-After header',
            'before_seconds': prior, 'after_seconds': fixed,
            'source_bound_only': True, 'powershell_runtime_executed': False,
            'commercial_differentiation': 'KILL_ALREADY_FIXED_UPSTREAM',
            'buyer_validated': False, 'revenue_usd': 0}
