"""Read-only private-workspace health checks; no remote telemetry or customer data output."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from .private_io import private_file_lock, private_permissions_verified
from .workbench import Workspace, ROLES


def check_workspace(root):
    root = Path(root).resolve()
    checks = []
    def record(name, ok, detail):
        checks.append({'check': name, 'ok': bool(ok), 'detail': detail})
    try:
        workspace = Workspace(root)
        with private_file_lock(root / '.workspace.lock'):
            metadata = json.loads((root / 'workspace.json').read_text())
            ledger = workspace.store.load()
            record('journal_replay', True, 'journal and ledger replay verified' if ledger else 'empty ledger')
            paths = [root / 'workspace.json', root / 'intake.json']
            paths.extend(p for p in (root / 'credentials.json', root / 'ledger.json') if p.exists())
            paths.extend(p for p in (root / 'sources').glob('*') if p.is_file())
            record('private_file_permissions', all(private_permissions_verified(p) for p in paths), 'owner-only file permissions')
            intact = True
            intake = workspace._intake()
            for source in list(intake['sources'].values()) + list(intake.get('documents', {}).values()):
                for path, key in ((root / source['path'], 'normalized_sha256'),
                                  (root / 'sources' / (source['id'] + '.original'), 'raw_sha256')):
                    intact &= path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == source[key]
            record('source_integrity', intact, 'original and normalized source/document hashes')
            valid_roles = set()
            for entry in metadata['tokens'].values():
                try:
                    expiry = datetime.fromisoformat(entry['expires_at'].replace('Z', '+00:00'))
                    if expiry.tzinfo is not None and expiry > datetime.now(timezone.utc):
                        valid_roles.add(entry['role'])
                except (KeyError, TypeError, ValueError, AttributeError):
                    pass
            record('active_role_credentials', set(ROLES) <= valid_roles, 'all four roles have unexpired access')
            statuses = workspace.onboarding_status(intake)
            active = {source['branch'] for source in intake['sources'].values()}
            record('active_branch_intake', bool(active) and all(statuses[b]['analysis_ready'] for b in active),
                   'exact customer scope and independent source review for active branches')
            backups = list((root / 'backups').glob('*.json'))
            backup_ok = False
            if backups:
                import tempfile
                latest = max(backups, key=lambda p: p.stat().st_mtime)
                snapshot = json.loads(latest.read_text())
                encoded = json.dumps(snapshot, sort_keys=True).encode()
                try:
                    captured = datetime.fromisoformat(snapshot.get('captured_at', '').replace('Z', '+00:00'))
                    age = (datetime.now(timezone.utc) - captured).total_seconds()
                    fresh = captured.tzinfo is not None and 0 <= age <= 86400
                except (ValueError, TypeError, AttributeError):
                    fresh = False
                # Copying/touching an old backup must not renew its recovery SLA.
                # Legacy snapshots remain restorable but need a fresh backup.
                if fresh and hashlib.sha256(encoded).hexdigest() == latest.stem:
                    with tempfile.TemporaryDirectory() as temporary:
                        Workspace.restore_snapshot(snapshot, Path(temporary) / 'restored')
                    backup_ok = True
            record('recent_verified_backup', backup_ok, 'backup within 24 hours passes an isolated restore rehearsal')
            record('free_disk', shutil.disk_usage(root).free >= 100 * 1024 * 1024, 'at least 100 MiB free')
            return {'schema': 1, 'healthy': all(c['ok'] for c in checks), 'simulation': metadata['simulation'],
                    'checks': checks, 'branch_analysis_ready': {b: v['analysis_ready'] for b, v in statuses.items()},
                    'production_certified': False}
    except Exception as exc:
        # Do not emit paths, financial records, credentials or raw exception text.
        record('workspace_readable', False, type(exc).__name__)
        return {'schema': 1, 'healthy': False, 'checks': checks, 'production_certified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    args = parser.parse_args(argv)
    report = check_workspace(args.workspace)
    print(json.dumps(report, indent=2))
    return 0 if report['healthy'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
