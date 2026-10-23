#!/usr/bin/env python3
"""Emit a non-executing synthetic-only staging and rollback plan."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


class Hold(Exception):
    pass


def make_plan(receipt: dict) -> dict:
    if (receipt.get('stage_readiness') != 'PASS' or
            receipt.get('remote_deployment') != 'NOT_EXECUTED' or
            receipt.get('customer_release') != 'HOLD' or
            re.fullmatch(r'[0-9a-f]{40}', receipt.get('source_sha', '')) is None):
        raise Hold('VALIDATED_SYNTHETIC_STAGE_RECEIPT_REQUIRED')
    sha = receipt['source_sha']
    return {
        'source_sha': sha,
        'release': 'SYNTHETIC_ONLY',
        'operations_performed': False,
        'services_started': False,
        'public_access_enabled': False,
        'customer_release': 'HOLD',
        'operator_steps': [
            'Reconcile original Oracle command receipt; never retry unknown execution.',
            'Require successful manual GitHub-hosted canary for the exact SHA.',
            'Verify existing E2 Micro instance metadata and zero inbound network rules.',
            'Checkout exactly ' + sha + ' into a clean Git worktree.',
            'After separate host approval use RETALLY_MICRO_HOST=1 bash deployment/oracle-always-free/install-staging.sh ' + sha,
            'Installer must leave the synthetic service stopped and disabled.',
            'Verify immutable release pointer, isolated synthetic workspace, and encrypted recovery.',
            'Refuse any unexpected state. Leave customer data, DNS and Cloudflare Access unchanged.',
        ],
        'rollback': [
            'Keep the prior known-good release and original evidence intact.',
            'Before rollback compare prior/current source SHAs with readlink /opt/retally/current.',
            'Only authorized operators may atomically restore the known-good release pointer.',
            'Re-run offline synthetic health; no automatic retries or public service start.',
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    try:
        result = make_plan(json.loads(Path(args.receipt).read_text(encoding='utf-8')))
    except (ValueError, OSError, Hold) as exc:
        print('STAGING PLAN: HOLD ' + (str(exc) if isinstance(exc, Hold) else 'INVALID_RECEIPT'))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
