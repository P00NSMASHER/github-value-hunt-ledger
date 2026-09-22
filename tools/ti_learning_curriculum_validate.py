#!/usr/bin/env python3
"""Fail-closed validation for the generated hunter learning curriculum."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.learning_curriculum import (
    validate_learning_curriculum,
)

PATH = ROOT / "intelligence" / "learning_curriculum.json"


def main() -> int:
    if not PATH.exists():
        raise SystemExit(
            "missing intelligence/learning_curriculum.json"
        )

    data = json.loads(
        PATH.read_text(encoding="utf-8")
    )
    errors = validate_learning_curriculum(data)
    if errors:
        raise SystemExit(
            "learning curriculum invalid: "
            + "; ".join(errors)
        )

    recs = data.get(
        "recommended_measurements"
    ) or []
    for rec in recs:
        if rec.get("requires_generated_claim") is not True:
            raise SystemExit(
                "measurement recommendation lacks generated-claim gate"
            )
        if rec.get("phase") == "confirm_measurement":
            confirm = rec.get("confirm") or {}
            if confirm.get("ready") is True:
                raise SystemExit(
                    "confirm-ready strategy must not be remeasured"
                )

    print(PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
