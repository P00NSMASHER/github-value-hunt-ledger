#!/usr/bin/env python3
"""Read-only GitHub provider proof; never submit OCI commands or deploy services."""
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener
from stage_context import Hold, REPO, check_env, require
from stage_evidence import inspect

API = 'https://api.github.com/repos/' + REPO

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise Hold('GITHUB_REDIRECT_REFUSED')

def get_json(path, token):
    require(re.fullmatch(r'/actions/runs/[1-9][0-9]{0,18}(?:/jobs\?per_page=100)?|'
                         r'/commits/[0-9a-f]{40}/check-runs\?per_page=100', path)
            is not None, 'UNEXPECTED_GITHUB_PATH')
    req = Request(API + path, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with build_opener(NoRedirect()).open(req, timeout=15) as response:
            body = response.read(350001)
    except (HTTPError, URLError, OSError, Hold):
        raise Hold('GITHUB_READ_UNVERIFIED') from None
    require(len(body) <= 350000, 'GITHUB_RESPONSE_TOO_LARGE')
    try:
        data = json.loads(body)
        require(isinstance(data, dict), 'GITHUB_JSON_INVALID')
        return data
    except (UnicodeDecodeError, ValueError):
        raise Hold('GITHUB_JSON_INVALID') from None

def main():
    try:
        env = dict(os.environ)
        sha, run_id = check_env(env)
        run = get_json(f'/actions/runs/{run_id}', env['GH_TOKEN'])
        jobs = get_json(f'/actions/runs/{run_id}/jobs?per_page=100', env['GH_TOKEN'])
        checks = get_json(f'/commits/{sha}/check-runs?per_page=100', env['GH_TOKEN'])
        inspect(run, jobs, checks, sha, run_id)
        folder = Path(env['RUNNER_TEMP']) / 'retally-oci-stage'
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        dest = folder / 'oci-synthetic-stage-readiness.json'
        flags = os.O_WRONLY | os.O_EXCL | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(dest, flags, 0o600), 'w') as f:
            json.dump({'source_sha': sha, 'canary_run_id': run_id,
                       'stage_readiness': 'PASS', 'remote_deployment': 'NOT_EXECUTED',
                       'customer_release': 'HOLD'}, f, sort_keys=True)
            f.flush(); os.fsync(f.fileno())
    except (Hold, KeyError, OSError) as e:
        print('RETALLY SYNTHETIC STAGE: HOLD ' +
              (str(e) if isinstance(e, Hold) else 'RECEIPT_FAILURE'))
        return 2
    print('RETALLY SYNTHETIC STAGE: READINESS PASS, no remote deployment performed')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
