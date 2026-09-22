#!/usr/bin/env python3
"""Generate advisory precommit packets for adaptive learning measurements."""

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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    curriculum_path = INTEL / "learning_curriculum.json"
    seeds_path = INTEL / "search_seeds.jsonl"
    curriculum = load_json(curriculum_path)
    seeds = load_jsonl(seeds_path)

    bundle = build_measurement_packets(
        curriculum,
        seeds,
        curriculum_sha=hashlib.sha256(
            curriculum_path.read_bytes()
        ).hexdigest(),
        seeds_sha=hashlib.sha256(
            seeds_path.read_bytes()
        ).hexdigest(),
    )
    errors = validate_measurement_packets(bundle)
    if errors:
        raise SystemExit(
            "learning measurement packets invalid: "
            + "; ".join(errors)
        )

    json_path = INTEL / "learning_measurement_packets.json"
    json_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# LEARNING MEASUREMENT PRECOMMIT PACKETS",
        "",
        (
            "Advisory packets that freeze **what** to measure before "
            "execution. They do not activate work, assign a worker, or "
            "reveal/choose train versus confirm membership."
        ),
        "",
        "- Mode: **precommit_only**",
        "- Policy effect: **none**",
        "- Activates work: **false**",
        "- Requires normal generated assignment/claim: **yes**",
        "- Manual work can complete a packet: **no**",
        "- Partition remains unknown until canonical ingestion.",
        "",
        "## Packets",
        "",
        "| Packet | Strategy | Phase | Seed | Objective |",
        "|---|---|---|---|---|",
    ]
    for packet in bundle["packets"]:
        seed = packet["seed"]
        lines.append(
            f"| {packet['packet_id']} | {packet['strategy_id']} | "
            f"{packet['measurement_phase']} | {seed['seed_id']} | "
            f"{seed.get('search_objective_id') or '—'} |"
        )
    if not bundle["packets"]:
        lines.append("| — | — | — | — | — |")

    lines += [
        "",
        "## Execution boundary",
        "",
        (
            "These packets become executable only after the user explicitly "
            "resumes hunters and the normal generated assignment/claim path "
            "selects the work. Never select, release, retry, or substitute a "
            "packet based on its eventual train/confirm partition."
        ),
        "",
    ]
    if bundle["unpaired_recommendations"]:
        lines += [
            "## Unpaired recommendations",
            "",
        ]
        for row in bundle["unpaired_recommendations"]:
            lines.append(
                f"- {row['strategy_id']}: {row['reason']}"
            )
        lines.append("")

    (INTEL / "LEARNING_MEASUREMENT_PACKETS.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "packets": len(bundle["packets"]),
                "unpaired": len(
                    bundle["unpaired_recommendations"]
                ),
                "activates_work": bundle["activates_work"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
