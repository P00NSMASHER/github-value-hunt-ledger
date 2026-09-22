#!/usr/bin/env python3
"""Fail-closed validation for skill-evaluation result intake."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.skill_eval_intake import (
    validate_skill_eval_result_intake,
)

PATH = ROOT / "intelligence" / "SKILL_EVAL_RESULT_INTAKE.json"


def main() -> int:
    if not PATH.exists():
        raise SystemExit(
            "missing intelligence/SKILL_EVAL_RESULT_INTAKE.json"
        )

    state = json.loads(PATH.read_text(encoding="utf-8"))
    errors = validate_skill_eval_result_intake(state)
    source_hash = state.get("source_snapshot_sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        errors.append("invalid_source_snapshot_sha256")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
