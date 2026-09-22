#!/usr/bin/env python3
"""Validate blinded training split receipts fail closed."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.blind_partition import validate_partition_receipts


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def main() -> int:
    runs = load_jsonl(ROOT / "intelligence" / "search_runs.jsonl")
    receipts = load_jsonl(
        ROOT / "intelligence" / "training_split_receipts.jsonl"
    )
    errors = validate_partition_receipts(
        receipts,
        runs,
        secret=os.environ.get("TI_TRAINING_SPLIT_KEY"),
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(ROOT / "intelligence" / "training_split_receipts.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
