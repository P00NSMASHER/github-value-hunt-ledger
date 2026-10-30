"""Read-only synthetic recovery-evidence triage, NOT proof of a real restore.

All inputs are untrusted assertions. Even 'complete' means internally coherent
synthetic fields, NOT authenticated documents, independent execution, or SLA.
"""
from collections import Counter
from datetime import datetime

COMPLETE = 'SYNTHETICALLY_CONSISTENT_UNAUTHENTICATED'
REVIEW = 'REVIEW_MISSING_OR_UNTRUSTED_EVIDENCE'
PROBLEM = 'EXPLICIT_FIXTURE_PROBLEM'

REQUIRED = frozenset({
    'id', 'scenario', 'backup_status', 'restore_status', 'app_data_validation',
    'validation_depth', 'keys_available', 'dependencies_recovered',
    'recovery_minutes', 'rto_minutes', 'recovery_point_age_minutes',
    'rpo_minutes', 'observer_evidence', 'attestation_integrity',
    'evidence_reference', 'started_at', 'completed_at', 'expected_class'
})


def _time(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _minutes(value, *, threshold=False):
    return type(value) is int and 0 <= value <= 525600 and (not threshold or value > 0)


def classify(case):
    if not isinstance(case, dict) or set(case) != REQUIRED:
        return REVIEW
    # Explicit failures take precedence over incomplete claims; every other
    # unrecognized value is reviewed and NEVER coerced to success.
    if (case['backup_status'] == 'FAILED' or case['restore_status'] == 'FAILED'
        or case['app_data_validation'] == 'FAIL'
        or case['keys_available'] is False
        or case['dependencies_recovered'] is False
        or case['attestation_integrity'] == 'BAD'):
        return PROBLEM

    start, end = _time(case['started_at']), _time(case['completed_at'])
    if start is not None and end is not None and end < start:
        return PROBLEM

    timings = ('recovery_minutes', 'rto_minutes', 'recovery_point_age_minutes', 'rpo_minutes')
    if all(_minutes(case[field], threshold=field in ('rto_minutes','rpo_minutes')) for field in timings):
        if (case['recovery_minutes'] > case['rto_minutes']
            or case['recovery_point_age_minutes'] > case['rpo_minutes']):
            return PROBLEM

    if (case['backup_status'] != 'SUCCESS'
        or case['restore_status'] != 'COMPLETED'
        or case['app_data_validation'] != 'PASS'
        or case['validation_depth'] != 'APP_AND_DATA'
        or case['keys_available'] is not True
        or case['dependencies_recovered'] is not True
        or case['observer_evidence'] != 'THIRD_PARTY_ASSERTED'
        or case['attestation_integrity'] != 'PRESENT_ASSERTED'
        or not isinstance(case['evidence_reference'], str)
        or not case['evidence_reference'].startswith('SYN-EVID-')
        or start is None or end is None or end <= start
        or not all(_minutes(case[field], threshold=field in ('rto_minutes','rpo_minutes')) for field in timings)):
        return REVIEW
    return COMPLETE


def evaluate(data):
    if (not isinstance(data, dict)
        or data.get('dataset_id') != 'golden-goose-029-synthetic-restore-evidence'
        or data.get('verified_owner_revenue_usd') != '0.00'
        or data.get('verified_collectible_usd') != '0.00'
        or data.get('real_customer_restore_tests') != 0):
        raise ValueError('Non-frozen synthetic study or unverified real-world claims')
    cases = data.get('cases')
    if not isinstance(cases, list) or len(cases) != 20:
        raise ValueError('Frozen case count must be exactly 20')
    ids = [case.get('id') if isinstance(case, dict) else None for case in cases]
    if len(set(ids)) != 20 or not all(isinstance(i,str) and i.startswith('SYN-RP-') for i in ids):
        raise ValueError('Fixture identities must be unique and synthetic')
    result = Counter(classify(case) for case in cases)
    mismatches = [(case['id'], classify(case), case['expected_class']) for case in cases
                  if classify(case) != case['expected_class']]
    if mismatches:
        raise ValueError(f'Frozen oracle mismatch: {mismatches}')
    naive_green = [c for c in cases if c['backup_status'] == 'SUCCESS']
    return {
        'synthetic_cases':len(cases),
        'consistent_unauthed':result[COMPLETE],
        'needs_review':result[REVIEW],
        'explicit_problems':result[PROBLEM],
        'naive_backup_success_count':len(naive_green),
        'naive_backup_success_not_evidence_complete':sum(classify(c)!=COMPLETE for c in naive_green),
        'verified_restores':0,
        'verified_collectible_usd':'0.00',
        'verified_owner_revenue_usd':'0.00',
        'independent_incumbent_head_to_head':'NOT_RUN',
        'customer_demand':'NOT_TESTED'
    }
