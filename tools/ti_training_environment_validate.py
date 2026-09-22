#!/usr/bin/env python3
"""Fail-closed validation for the generated hunter training environment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.training_environment import validate_training_environment

ENV_PATH = ROOT / "intelligence" / "TRAINING_ENVIRONMENT.json"
EPISODES_PATH = ROOT / "intelligence" / "training_episodes.jsonl"


def main() -> int:
    if not ENV_PATH.exists():
        raise SystemExit(
            "missing intelligence/TRAINING_ENVIRONMENT.json"
        )
    if not EPISODES_PATH.exists():
        raise SystemExit(
            "missing intelligence/training_episodes.jsonl"
        )

    environment = json.loads(
        ENV_PATH.read_text(encoding="utf-8")
    )
    errors = validate_training_environment(
        environment
    )
    if errors:
        raise SystemExit(
            "training environment invalid: "
            + "; ".join(errors)
        )

    episode_rows = [
        json.loads(raw)
        for raw in EPISODES_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if raw.strip()
    ]
    if episode_rows != environment.get(
        "episodes",
        [],
    ):
        raise SystemExit(
            "training_episodes.jsonl does not match "
            "TRAINING_ENVIRONMENT.json"
        )

    summary = environment.get("summary") or {}
    if summary.get("episodes") != len(
        episode_rows
    ):
        raise SystemExit(
            "training episode count mismatch"
        )

    if (
        environment.get("split_policy") or {}
    ).get("benchmark") != "evaluation_only":
        raise SystemExit(
            "benchmark records must remain evaluation only"
        )

    print(ENV_PATH)
    print(EPISODES_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
