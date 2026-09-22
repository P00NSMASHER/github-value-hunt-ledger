"""Local command-line entry point for Recovery Scan 360 JSON payloads."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .io import run_scan_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="recoveryworks")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="run a frozen Recovery Scan 360 payload")
    scan.add_argument("input", type=Path)
    scan.add_argument("--output", "-o", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "scan":
        raise ValueError("unsupported command")

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = run_scan_payload(payload)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
