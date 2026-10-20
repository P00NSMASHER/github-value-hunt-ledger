"""Rotate/revoke role credentials as the local workspace filesystem administrator."""
from __future__ import annotations
import argparse
from .workbench import Workspace, ROLES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--role', required=True, choices=ROLES)
    parser.add_argument('--revoke', action='store_true')
    parser.add_argument('--hours', type=int, default=24)
    parser.add_argument('--reason', required=True)
    args = parser.parse_args(argv)
    result = Workspace(args.workspace).manage_credential(
        args.role, revoke=args.revoke, hours=args.hours, reason=args.reason)
    print(f"Credential {result['operation']} completed for {result['role']}. "
          'Current keys are available only in the private credentials.json file.')


if __name__ == '__main__':
    main()
