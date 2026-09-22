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
    build_key_commitment,
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
    p.add_argument(
        "--key-commitment",
        default="intelligence/TRAINING_SPLIT_KEY_COMMITMENT.json",
    )
    args = p.parse_args()

    runs = load_jsonl(Path(args.search_runs))
    receipts_path = Path(args.receipts)
    existing = load_jsonl(receipts_path)
    secret = os.environ.get("TI_TRAINING_SPLIT_KEY")
    commitment_path = Path(args.key_commitment)
    existing_commitment = (
        json.loads(commitment_path.read_text(encoding="utf-8"))
        if commitment_path.exists()
        else None
    )
    commitment, commitment_errors = build_key_commitment(
        runs,
        existing_commitment,
        secret=secret,
    )
    if commitment_errors:
        raise ValueError(
            "invalid split-key commitment: "
            + ", ".join(commitment_errors)
        )
    if commitment is not None:
        commitment_path.write_text(
            json.dumps(commitment, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    receipts, issues = build_partition_receipts(
        runs,
        existing,
        secret=secret,
        key_commitment=commitment,
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
        "key_commitment_active": commitment is not None,
        "activation_run_count": (
            commitment.get("activation_run_count")
            if commitment
            else None
        ),
        "key_commitment_sha256": (
            commitment.get("key_commitment_sha256")
            if commitment
            else None
        ),
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
