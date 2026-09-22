#!/usr/bin/env python3
"""Generate a non-activating readiness report for a future hunter restart."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.restart_readiness import (
    build_restart_readiness,
    validate_restart_readiness,
)

INTEL = ROOT / "intelligence"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    split_status = load_json(
        INTEL / "TRAINING_SPLIT_STATUS.json"
    )
    activation_metrics = load_json(
        INTEL / "activation_metrics.json"
    )
    packets = load_json(
        INTEL / "learning_measurement_packets.json"
    )
    execution_claim_history = load_jsonl(
        INTEL / "execution_claim_history.jsonl"
    )
    scoreboard = (
        ROOT / "benchmark" / "SCOREBOARD.md"
    ).read_text(encoding="utf-8")

    shadow_results = {}
    for lane in ("ai", "science", "commercial"):
        path = (
            ROOT
            / "production"
            / "shadow"
            / "results"
            / f"{lane}.md"
        )
        shadow_results[lane] = (
            path.read_text(encoding="utf-8")
            if path.exists()
            else ""
        )

    report = build_restart_readiness(
        split_status=split_status,
        activation_metrics=activation_metrics,
        packets=packets,
        scoreboard_text=scoreboard,
        shadow_results=shadow_results,
        execution_claim_history=execution_claim_history,
    )
    errors = validate_restart_readiness(report)
    if errors:
        raise SystemExit(
            "restart readiness invalid: "
            + "; ".join(errors)
        )

    json_path = INTEL / "HUNTER_RESTART_READINESS.json"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# HUNTER RESTART READINESS",
        "",
        (
            "Repository-side readiness for a future adaptive-learning "
            "hunter canary. **This report never activates work or "
            "changes scheduled tasks.**"
        ),
        "",
        f"- State: **{report['state']}**",
        "- Explicit user approval required: **yes**",
        (
            f"- Precommitted measurement packets: "
            f"**{report['canary']['packet_count']}**"
        ),
        (
            f"- Frozen benchmark matched: "
            f"**{report['evidence']['matched_benchmark_tasks']}/"
            f"{report['evidence']['required_matched_benchmark_tasks']}**"
        ),
        (
            "- Unmatched benchmark tasks: **"
            + (
                ", ".join(
                    report["evidence"][
                        "unmatched_benchmark_task_ids"
                    ]
                )
                or "none"
            )
            + "**"
        ),
        (
            f"- Shadow runs: **{report['evidence']['shadow_runs_total']}** "
            f"(required {report['evidence']['required_shadow_runs']})"
        ),
        (
            f"- Split key commitment active: "
            f"**{str(report['evidence']['split_key_commitment_active']).lower()}**"
        ),
        (
            f"- Split secret available to workflow: "
            f"**{str(report['evidence']['split_secret_available']).lower()}**"
        ),
        (
            f"- Pending split claims: "
            f"**{report['evidence']['pending_split_claims']}**"
        ),
        (
            f"- Current generated activations: "
            f"**{report['evidence']['current_activations']}**"
        ),
        (
            f"- Active generated claims: "
            f"**{report['evidence']['active_generated_claim_count']}**"
        ),
        "",
        "## Machine gates",
        "",
        "| Gate | State |",
        "|---|---|",
    ]
    for key, value in report["gates"].items():
        lines.append(
            f"| {key} | "
            f"{'PASS' if value else 'BLOCKED'} |"
        )

    lines += ["", "## Blockers", ""]
    if report["blockers"]:
        for blocker in report["blockers"]:
            lines.append(
                f"- **{blocker['code']}** — "
                f"{blocker['action']}"
            )
    else:
        lines.append(
            "- No machine blocker. Remain paused until the user "
            "explicitly approves canary activation."
        )

    lines += [
        "",
        "## Canary contract after explicit approval",
        "",
        (
            "- At most three precommitted packet runs in the "
            "initial canary."
        ),
        "- Exactly one normal generated claim per packet.",
        (
            "- No manual completion, partition probing, release, "
            "substitution or retry to influence train/confirm."
        ),
        (
            "- Require canonical ingestion and a secret-keyed split "
            "receipt before the run can affect learning."
        ),
        (
            "- Rebuild learning state after each canonical run; "
            "do not infer success from packet execution alone."
        ),
        "",
    ]

    (INTEL / "HUNTER_RESTART_READINESS.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "state": report["state"],
                "blockers": [
                    row["code"]
                    for row in report["blockers"]
                ],
                "packets": report["canary"][
                    "packet_count"
                ],
                "activates_work": report[
                    "activates_work"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
