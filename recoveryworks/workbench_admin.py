"""Local administrator setup and restore; never expose these commands over HTTP."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .workbench import Workspace


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('init')
    create.add_argument('--workspace', required=True)
    create.add_argument('--client', required=True)
    create.add_argument('--currency', default='USD')
    create.add_argument('--live', action='store_true', help='create an empty live workspace; no synthetic authorization shortcuts')
    restore = commands.add_parser('restore')
    restore.add_argument('--snapshot', required=True)
    restore.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    if args.command == 'init':
        workspace, _ = Workspace.create(args.workspace, args.client, simulation=not args.live, currency=args.currency)
        print('Empty ' + ('simulation' if workspace.meta['simulation'] else 'live') +
              ' workspace created. Role keys are in private credentials.json. Customer scope and source review are required before scanning.')
    else:
        snapshot = json.loads(Path(args.snapshot).read_text())
        Workspace.restore_snapshot(snapshot, args.destination)
        print('Snapshot restored to a new workspace. Saved keys are disabled. Use workbench_credentials to issue fresh role keys.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
