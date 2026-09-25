#!/usr/bin/env python3
"""Validate the durable Business OS -> Hunter seed feed."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ai_business_os.hunter_bridge import PUBLIC_TECHNICAL_SOURCE_TYPES

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "intelligence" / "business_os_hunter_seeds.jsonl"


def load_rows():
    if not PATH.exists():
        return []
    return [
        json.loads(line)
        for line in PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    rows = load_rows()
    seen_seed_ids = set()
    seen_work_ids = set()
    for index, row in enumerate(rows, 1):
        prefix = f"business_os_hunter_seeds.jsonl:{index}"
        seed_id = row.get("seed_id")
        if not isinstance(seed_id, str) or not re.fullmatch(r"BOS:[a-z0-9-]+:[a-z0-9-]+:[0-9a-f]{12}", seed_id):
            raise SystemExit(f"{prefix}: invalid seed_id")
        if seed_id in seen_seed_ids:
            raise SystemExit(f"{prefix}: duplicate seed_id")
        seen_seed_ids.add(seed_id)

        work_id = row.get("business_os_work_id")
        if not isinstance(work_id, str) or not work_id:
            raise SystemExit(f"{prefix}: missing business_os_work_id")
        if work_id in seen_work_ids:
            raise SystemExit(f"{prefix}: duplicate business_os_work_id")
        seen_work_ids.add(work_id)

        if row.get("seed_type") != "business_os_gap":
            raise SystemExit(f"{prefix}: wrong seed_type")
        if row.get("work_action") != "search":
            raise SystemExit(f"{prefix}: only search is allowed")
        if row.get("required_source_type") not in PUBLIC_TECHNICAL_SOURCE_TYPES:
            raise SystemExit(f"{prefix}: source type is not public technical")
        if row.get("planning_only") is not True:
            raise SystemExit(f"{prefix}: planning_only must be true")
        if row.get("external_write_allowed") is not False:
            raise SystemExit(f"{prefix}: external writes must be false")
        if row.get("human_approval_required_for_external_write") is not True:
            raise SystemExit(f"{prefix}: external writes must be human-gated")
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("business_os_plan_hash", ""))):
            raise SystemExit(f"{prefix}: invalid Business OS plan hash")
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("business_os_seed_hash", ""))):
            raise SystemExit(f"{prefix}: invalid seed hash")
        priority = row.get("priority")
        if not isinstance(priority, int) or not 0 <= priority <= 100:
            raise SystemExit(f"{prefix}: invalid priority")
        instructions = row.get("instructions")
        if not isinstance(instructions, dict) or not instructions.get("acceptance_target"):
            raise SystemExit(f"{prefix}: missing bounded acceptance target")
        if not instructions.get("verification_gate") or not instructions.get("stop_conditions"):
            raise SystemExit(f"{prefix}: missing verification/STOP gates")
        if not isinstance(row.get("queries"), list) or not row["queries"]:
            raise SystemExit(f"{prefix}: missing bounded queries")
    print(f"OK business_os_hunter_seeds={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
