#!/usr/bin/env python3
"""Validate generated hunter learning measurement precommit packets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.learning_measurement_packets import (
    validate_measurement_packets,
)

PATH = ROOT / "intelligence" / "learning_measurement_packets.json"


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
    print(PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
