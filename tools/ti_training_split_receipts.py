#!/usr/bin/env python3
"""Assign post-run blinded train/confirm receipts to trusted generated claims."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.blind_partition import (
    build_partition_receipts,
    trusted_claim_id,
)


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
    p = argparse.ArgumentParser()
    p.add_argument("--search-runs", default="intelligence/search_runs.jsonl")
    p.add_argument(
        "--receipts",
        default="intelligence/training_split_receipts.jsonl",
    )
    p.add_argument(
        "--status",
        default="intelligence/TRAINING_SPLIT_STATUS.json",
    )
    args = p.parse_args()

    runs = load_jsonl(Path(args.search_runs))
    receipts_path = Path(args.receipts)
    existing = load_jsonl(receipts_path)
    secret = os.environ.get("TI_TRAINING_SPLIT_KEY")

    receipts, issues = build_partition_receipts(
        runs,
        existing,
        secret=secret,
    )

    receipts_path.parent.mkdir(parents=True, exist_ok=True)
    receipts_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in receipts
        ),
        encoding="utf-8",
    )

    trusted_claims = {
        claim_id
        for run in runs
        if (claim_id := trusted_claim_id(run))
    }
    receipted_claims = {
        str(row.get("execution_claim_id"))
        for row in receipts
        if row.get("execution_claim_id")
    }
    pending = sorted(trusted_claims - receipted_claims)
    status = {
        "schema_version": 1,
        "partition_method": "hmac-sha256-v1",
        "secret_available": bool(secret),
        "trusted_generated_runs": len(trusted_claims),
        "receipts": len(receipts),
        "train_receipts": sum(
            1 for row in receipts if row.get("partition") == "train"
        ),
        "confirm_receipts": sum(
            1 for row in receipts if row.get("partition") == "confirm"
        ),
        "pending_claim_ids": pending,
        "issues": issues,
        "worker_visibility_rule": (
            "partition is assigned only after canonical run intake; "
            "workers must not receive the HMAC key"
        ),
    }
    Path(args.status).write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
