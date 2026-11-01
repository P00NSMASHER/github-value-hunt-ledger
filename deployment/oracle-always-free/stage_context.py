"""Fixed GitHub identity and owner-approved commit for OCI synthetic staging."""
import re

REPO = 'P00NSMASHER/github-value-hunt-ledger'
REPO_ID = '1376771019'
OWNER_ID = '22281248'
WORKFLOW = REPO + '/.github/workflows/retally-oci-synthetic-stage-readiness.yml@refs/heads/main'
CANARY_PATH = '.github/workflows/retally-oci-runcommand-canary.yml'
CANARY_WORKFLOW_ID = 392429059
REQUIRED_JOBS = ('validate-offline', 'run-synthetic-canary')
REQUIRED_CHECKS = ('release-gate', 'oracle-staging-template', 'oracle-micro-memory-rehearsal')

class Hold(Exception):
    pass

def require(ok, code):
    if not ok: raise Hold(code)

def check_env(env):
    checks = {
        'GITHUB_REPOSITORY': REPO, 'GITHUB_REPOSITORY_ID': REPO_ID,
        'GITHUB_REPOSITORY_OWNER_ID': OWNER_ID, 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_WORKFLOW_REF': WORKFLOW, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'RETALLY_OCI_SYNTHETIC_STAGE_ENABLED': 'true',
        'RETALLY_OCI_RUN_COMMAND_ENABLED': 'true',
    }
    require(all(env.get(k) == v for k, v in checks.items()), 'WRONG_CONTEXT_OR_DISABLED')
    sha = env.get('GITHUB_SHA', '')
    require(re.fullmatch(r'[0-9a-f]{40}', sha) is not None and
            env.get('GITHUB_INPUT_EXPECTED_SHA') == sha and
            env.get('RETALLY_OCI_SYNTHETIC_STAGE_APPROVED_SHA') == sha,
            'SHA_NOT_EXACTLY_APPROVED')
    run_id = env.get('GITHUB_INPUT_CANARY_RUN_ID', '')
    require(re.fullmatch(r'[1-9][0-9]{0,18}', run_id) is not None,
            'INVALID_CANARY_RUN_ID')
    require(bool(env.get('GH_TOKEN')), 'READ_ONLY_GITHUB_TOKEN_MISSING')
    return sha, int(run_id)
