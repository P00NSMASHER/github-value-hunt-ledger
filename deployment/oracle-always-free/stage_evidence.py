"""Reject skipped/synthetic-only GitHub evidence as proof of live OCI execution."""
from stage_context import (CANARY_PATH, CANARY_WORKFLOW_ID, OWNER_ID,
                           REPO_ID, REQUIRED_CHECKS, REQUIRED_JOBS, require)


def inspect(run, jobs, checks, sha, run_id):
    repo = run.get('repository') or {}
    require(run.get('id') == run_id and run.get('workflow_id') == CANARY_WORKFLOW_ID and
            run.get('path') == CANARY_PATH and run.get('event') == 'workflow_dispatch' and
            run.get('head_branch') == 'main' and run.get('head_sha') == sha and
            run.get('status') == 'completed' and run.get('conclusion') == 'success' and
            type(run.get('run_attempt')) is int and run['run_attempt'] >= 1 and
            repo.get('id') == int(REPO_ID) and
            (repo.get('owner') or {}).get('id') == int(OWNER_ID),
            'EXACT_MANUAL_CANARY_NOT_PROVEN')
    entries = jobs.get('jobs')
    require(isinstance(entries, list) and jobs.get('total_count') == len(entries) and
            len(entries) <= 100, 'INCOMPLETE_CANARY_JOBS')
    for job in REQUIRED_JOBS:
        found = [j for j in entries if j.get('name') == job and
                 j.get('run_id') == run_id and j.get('status') == 'completed' and
                 j.get('conclusion') == 'success']
        require(len(found) == 1, 'REQUIRED_CANARY_JOB_NOT_GREEN')
    entries = checks.get('check_runs')
    require(isinstance(entries, list) and checks.get('total_count') == len(entries) and
            len(entries) <= 100, 'INCOMPLETE_SHA_CHECKS')
    for check in REQUIRED_CHECKS:
        require(any(c.get('name') == check and c.get('head_sha') == sha and
                    (c.get('app') or {}).get('id') == 15368 and
                    c.get('status') == 'completed' and c.get('conclusion') == 'success'
                    for c in entries), 'EXACT_SHA_CI_MISSING')
