#!/usr/bin/env python3
"""Fail-closed validation for hunter restart readiness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.restart_readiness import (
    validate_restart_readiness,
)

PATH = ROOT / "intelligence" / "HUNTER_RESTART_READINESS.json"


def main() -> int:
    if not PATH.exists():
        raise SystemExit(
            "missing intelligence/HUNTER_RESTART_READINESS.json"
        )
    report = json.loads(
        PATH.read_text(encoding="utf-8")
    )
    errors = validate_restart_readiness(report)
    if errors:
        raise SystemExit(
            "restart readiness invalid: "
            + "; ".join(errors)
        )

    if report.get("activates_work") is not False:
        raise SystemExit("readiness must never activate work")
    if report.get("changes_automation_state") is not False:
        raise SystemExit(
            "readiness must never change automation state"
        )
    if report.get("state") == "READY_FOR_CANARY_ACTIVATION":
        raise SystemExit(
            "machine report may not self-authorize activation"
        )

    print(PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
