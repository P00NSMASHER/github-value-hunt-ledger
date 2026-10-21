"""Evidence-bound launch checklist for the seven RETALLY branches.

This checks recorded evidence integrity, not the truth of a reviewer's assertions.
It never authorizes claims or changes ledger state.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from .cli import write_private_json
from .private_io import atomic_private_write

BRANCHES = ('freight', 'ap', 'warranty_credit', 'procurement', 'rebate', 'parcel', 'utility')
GATES = ('authorized_scope', 'source_completeness', 'rule_review', 'unseen_case_benchmark',
         'overlap_review', 'customer_workflow', 'security_restore', 'realized_recovery', 'unit_economics')


def template(client_id: str) -> dict:
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError('client_id required')
    return {'schema_version': 1, 'client_id': client_id.strip(), 'branches': {
        branch: {gate: {'reviewer_id': '', 'independent_reviewer_id': '', 'decision': 'pending',
                        'evidence_path': '', 'sha256': '', 'scope': '', 'reviewed_at': ''}
                 for gate in GATES} for branch in BRANCHES}}


def assess(manifest: dict, root: Path) -> dict:
    from datetime import datetime, timezone
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('client_id'), str) or not manifest['client_id'].strip():
        raise ValueError('unsupported manifest or missing client_id')
    root = root.resolve()
    output = {'client_id': manifest['client_id'], 'commercially_certified': False,
              'meaning': 'Recorded evidence checks only; independent substantive review remains required.', 'branches': {}}
    branches = manifest.get('branches', {})
    if not isinstance(branches, dict):
        raise ValueError('branches must be an object')
    for branch in BRANCHES:
        checks = {}
        records = branches.get(branch, {})
        if not isinstance(records, dict):
            records = {}
        for gate in GATES:
            record = records.get(gate, {})
            issues = []
            if not isinstance(record, dict):
                record = {}
            if record.get('decision') != 'accepted':
                issues.append('review pending or rejected')
            reviewer = record.get('reviewer_id')
            independent = record.get('independent_reviewer_id')
            if not isinstance(reviewer, str) or not reviewer.strip():
                issues.append('reviewer missing')
            if not isinstance(independent, str) or not independent.strip() or independent.strip() == (reviewer.strip() if isinstance(reviewer, str) else reviewer):
                issues.append('distinct independent reviewer missing')
            if not isinstance(record.get('scope'), str) or not record['scope'].strip():
                issues.append('reviewed scope missing')
            try:
                reviewed = datetime.fromisoformat(record.get('reviewed_at', '').replace('Z', '+00:00'))
                if reviewed.tzinfo is None or reviewed > datetime.now(timezone.utc):
                    raise ValueError('invalid review date')
            except (ValueError, TypeError, AttributeError):
                issues.append('valid timezone-aware past review date required')
            try:
                relative = Path(record.get('evidence_path', ''))
                source = (root / relative).resolve()
                if relative.is_absolute() or not source.is_relative_to(root) or not source.is_file():
                    raise ValueError('evidence must be a file within the private workspace')
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                if digest != record.get('sha256'):
                    raise ValueError('evidence missing or changed since review')
            except (OSError, ValueError, TypeError) as exc:
                issues.append(str(exc))
            checks[gate] = {'recorded_review_valid': not issues, 'issues': issues}
        output['branches'][branch] = {'status': 'REVIEW_RECORDS_COMPLETE' if all(
            check['recorded_review_valid'] for check in checks.values()) else 'BLOCKED', 'gates': checks}
    return output


def render(result: dict) -> str:
    escape = html.escape
    rows = []
    for branch, record in result['branches'].items():
        cells = ''.join('<td>' + ('Recorded' if check['recorded_review_valid'] else
                    '<details><summary>Blocked</summary>' + escape('; '.join(check['issues'])) + '</details>') + '</td>'
                    for check in record['gates'].values())
        rows.append('<tr><th>' + escape(branch) + '</th>' + cells + '</tr>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>RETALLY seven-branch launch review</title><style>'
            'body{font:16px system-ui;margin:2rem;color:#172b3a;background:#f7f9fc}'
            'table{border-collapse:collapse;background:white}td,th{padding:12px;border:1px solid #ccd5df;text-align:left}'
            'summary{cursor:pointer;color:#8b3000}details{max-width:240px}main{overflow:auto}</style>'
            '<h1>RETALLY seven-branch launch review</h1><p>Client: ' + escape(result['client_id']) + '</p>'
            '<p>Evidence integrity and review records only. This report does not certify customer readiness, '
            'authorize claims, or prove that recovered cash was received.</p><main><table><thead><tr><th>Branch</th>'
            + ''.join('<th>' + escape(g.replace('_', ' ')) + '</th>' for g in GATES)
            + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></main></html>')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--client', required=True)
    init.add_argument('--manifest', required=True)
    check = sub.add_parser('check')
    check.add_argument('--manifest', required=True)
    check.add_argument('--report', required=True)
    check.add_argument('--html', required=True)
    args = parser.parse_args(argv)
    path = Path(args.manifest)
    if args.command == 'init':
        if path.exists():
            raise ValueError('refusing to overwrite existing review manifest')
        write_private_json(path, template(args.client))
        return 0
    result = assess(json.loads(path.read_text()), path.parent)
    write_private_json(Path(args.report), result)
    atomic_private_write(Path(args.html), render(result).encode())
    print('Seven-branch evidence report written; no commercial certification issued.')
    return 0 if all(b['status'] == 'REVIEW_RECORDS_COMPLETE' for b in result['branches'].values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
