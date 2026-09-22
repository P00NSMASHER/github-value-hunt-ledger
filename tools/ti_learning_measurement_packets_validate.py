#!/usr/bin/env python3
"""Validate generated hunter learning measurement precommit packets."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.learning_measurement_packets import (
    build_measurement_packets,
    validate_measurement_packets,
)

INTEL = ROOT / "intelligence"
PATH = INTEL / "learning_measurement_packets.json"
CURRICULUM = INTEL / "learning_curriculum.json"
SEEDS = INTEL / "search_seeds.jsonl"


def main() -> int:
    if not PATH.exists():
        raise SystemExit(
            "missing intelligence/learning_measurement_packets.json"
        )
    bundle = json.loads(PATH.read_text(encoding="utf-8"))
    errors = validate_measurement_packets(bundle)
    if errors:
        raise SystemExit(
            "learning measurement packets invalid: "
            + "; ".join(errors)
        )
    if bundle.get("unpaired_recommendations"):
        raise SystemExit(
            "every recommended measurement must pair to an authorized seed"
        )

    curriculum = json.loads(
        CURRICULUM.read_text(encoding="utf-8")
    )
    seeds = [
        json.loads(line)
        for line in SEEDS.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    expected = build_measurement_packets(
        curriculum,
        seeds,
        curriculum_sha=hashlib.sha256(
            CURRICULUM.read_bytes()
        ).hexdigest(),
        seeds_sha=hashlib.sha256(
            SEEDS.read_bytes()
        ).hexdigest(),
    )
    if bundle != expected:
        raise SystemExit(
            "persisted learning measurement packets are stale "
            "relative to current curriculum/seeds"
        )

    print(PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
