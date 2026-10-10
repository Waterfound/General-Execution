'use strict';
// Candidate-only pure function. Input: a supplied JSON snapshot; no network or mutations.
function diagnose(s) {
  const missing = [], links = [];
  const result = (status, next) => ({ status, next, links, missing, proof: 'fixture-only; no buyer validation' });
  if (!s || !s.pr || !s.pr.url || !s.pr.head_sha) {
    missing.push('pr identity and head'); return result('UNKNOWN', 'obtain PR facts');
  }
  links.push(s.pr.url);
  if (!Array.isArray(s.required_checks) || !Array.isArray(s.checks)) {
    missing.push('required-check policy and head check runs');
    return result('UNKNOWN', 'obtain current check policy');
  }
  for (const name of s.required_checks) {
    const check = s.checks.find(x => x.name === name && x.head_sha === s.pr.head_sha);
    if (!check || !check.url) {
      missing.push('current-head check: ' + name);
      return result('UNKNOWN', 'obtain missing current-head check');
    }
    links.push(check.url);
    if (check.status !== 'completed') return result('WAIT', 'wait for ' + name);
    if (['failure', 'timed_out', 'cancelled', 'action_required', 'stale'].includes(check.conclusion)) {
      return result('INVESTIGATE', 'inspect failing check ' + name);
    }
    if (!['success', 'neutral', 'skipped'].includes(check.conclusion)) {
      missing.push('check conclusion: ' + name);
      return result('UNKNOWN', 'verify check conclusion');
    }
  }
  const policy = s.approval_policy;
  if (!policy || !policy.url || typeof policy.required !== 'boolean') {
    missing.push('authoritative approval policy');
    return result('UNKNOWN', 'read approval policy');
  }
  links.push(policy.url);
  if (policy.required && policy.satisfied !== true) {
    if (policy.satisfied === false && policy.review_url) {
      links.push(policy.review_url);
      return result('HUMAN_GATE', 'obtain authorized review');
    }
    missing.push('current approval state');
    return result('UNKNOWN', 'verify review state');
  }
  if (s.pr.mergeable !== true) {
    missing.push('mergeability or conflict resolution');
    return result('UNKNOWN', 'verify mergeability');
  }
  return result('REVIEW_CANDIDATE', 'request authorized integration review; never auto-merge');
}
module.exports = { diagnose };
