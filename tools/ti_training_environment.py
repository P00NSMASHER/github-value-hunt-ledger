#!/usr/bin/env python3
"""Compile canonical hunter telemetry into an offline training environment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.blind_partition import receipt_partition_map
from production.training_environment import build_training_environment


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{path}:{line_no}: invalid JSON: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"{path}:{line_no}: expected JSON object"
            )
        rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-runs",
        default="intelligence/search_runs.jsonl",
    )
    parser.add_argument(
        "--outcomes",
        default="intelligence/outcomes.jsonl",
    )
    parser.add_argument(
        "--split-receipts",
        default="intelligence/training_split_receipts.jsonl",
    )
    parser.add_argument(
        "--write",
        default="intelligence/TRAINING_ENVIRONMENT.json",
    )
    parser.add_argument(
        "--episodes",
        default="intelligence/training_episodes.jsonl",
    )
    args = parser.parse_args()

    environment = build_training_environment(
        load_jsonl(Path(args.search_runs)),
        load_jsonl(Path(args.outcomes)),
        split_receipts=receipt_partition_map(
            load_jsonl(Path(args.split_receipts))
        ),
    )

    output_path = Path(args.write)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            environment,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    episodes_path = Path(args.episodes)
    episodes_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    episodes_path.write_text(
        "".join(
            json.dumps(
                episode,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for episode in environment["episodes"]
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            environment["summary"],
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
