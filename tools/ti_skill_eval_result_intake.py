#!/usr/bin/env python3
"""Generate skill-evaluation result intake and staged promotion queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.skill_eval_intake import build_skill_eval_result_intake


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_packets(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for file_path in sorted(path.glob("*.json")):
        value = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{file_path}: expected JSON object")
        value = dict(value)
        value["_source_file"] = str(file_path)
        rows.append(value)
    return rows


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def render_markdown(state: dict[str, Any]) -> str:
    summary = state["summary"]
    lines = [
        "# Skill Promotion Queue",
        "",
        "Generated from independently evaluated repair candidates. "
        "**A staged mutation is not globally promoted.**",
        "",
        "## Summary",
        "",
        f"- Submitted evaluations: **{summary['submitted']}**",
        f"- Staged mutations: **{summary['staged_mutations']}**",
        f"- Rejected evaluations: **{summary['rejected']}**",
        f"- Blocked submissions: **{summary['blocked']}**",
        "",
        "## Staged mutations awaiting promotion evidence",
        "",
    ]
    if not state["skill_promotion_queue"]:
        lines.append("- No mutation currently satisfies the independent skill-evaluation gate.")
    for row in state["skill_promotion_queue"]:
        req = row["required_promotion_evidence"]
        lines += [
            f"### {row['skill_promotion_id']}",
            "",
            f"- Evaluation result: {row['skill_eval_result_id']}",
            f"- Artifact: {row['artifact_id']}",
            f"- Candidate version: {row['candidate_version']}",
            f"- Distinct success tasks required: {req['distinct_success_tasks_min']}",
            f"- Held-out tasks required: {req['heldout_tasks_min']} at 100% pass",
            "- Held-out regressions allowed: 0",
            "- Adversarial task pass required",
            "- Adjacent-domain transfer pass required",
            "- Curator approval required before canary",
            f"- Canary hunters required: {req['canary_hunters_min']} with zero regressions",
            "- Automatic global promotion: disabled",
            "",
        ]

    if state["blocked_submissions"]:
        lines += ["## Blocked evaluation submissions", ""]
        for row in state["blocked_submissions"]:
            lines.append(
                f"- {row.get('skill_eval_result_id')}: "
                + ", ".join(row.get("reasons") or [])
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repair-candidate-intake",
        default="intelligence/REPAIR_CANDIDATE_INTAKE.json",
    )
    parser.add_argument(
        "--result-dir",
        default="intelligence/skill_eval_result_spool",
    )
    parser.add_argument(
        "--json-output",
        default="intelligence/SKILL_EVAL_RESULT_INTAKE.json",
    )
    parser.add_argument(
        "--markdown-output",
        default="intelligence/SKILL_PROMOTION_QUEUE.md",
    )
    args = parser.parse_args()

    repair_intake = read_json(
        Path(args.repair_candidate_intake),
        {},
    )
    packets = read_packets(Path(args.result_dir))
    state = build_skill_eval_result_intake(
        repair_intake,
        packets,
    )
    state["source_snapshot_sha256"] = stable_hash(
        {
            "repair_candidate_intake": repair_intake,
            "result_packets": packets,
        }
    )

    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path = Path(args.markdown_output)
    md_path.write_text(
        render_markdown(state) + "\n",
        encoding="utf-8",
    )
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
