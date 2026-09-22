#!/usr/bin/env python3
"""Generate skill-promotion result intake and global review queue."""

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

from production.skill_promotion_intake import (
    build_skill_promotion_result_intake,
)


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
        "# Global Skill Review Queue",
        "",
        "Generated from machine-validated promotion evidence. "
        "**GLOBAL_ELIGIBLE is not GLOBAL. Integrator approval is still required.**",
        "",
        "## Summary",
        "",
        f"- Submitted promotion packets: **{summary['submitted']}**",
        f"- Staged: **{summary['staged']}**",
        f"- Verified: **{summary['verified']}**",
        f"- Canary: **{summary['canary']}**",
        f"- Quarantined: **{summary['quarantined']}**",
        f"- Global eligible: **{summary['global_eligible']}**",
        f"- Blocked: **{summary['blocked']}**",
        "",
        "## Global-eligible mutations",
        "",
    ]
    if not state["global_review_queue"]:
        lines.append("- No mutation currently satisfies all promotion evidence gates.")
    for row in state["global_review_queue"]:
        lines += [
            f"### {row['global_review_id']}",
            "",
            f"- Artifact: {row['artifact_id']}",
            f"- Candidate version: {row['candidate_version']}",
            f"- Promotion result: {row['skill_promotion_result_id']}",
            "- Integrator approval required: yes",
            "- Automatic global promotion: disabled",
            "",
        ]

    if state["blocked_submissions"]:
        lines += ["## Blocked promotion submissions", ""]
        for row in state["blocked_submissions"]:
            lines.append(
                f"- {row.get('skill_promotion_result_id')}: "
                + ", ".join(row.get("reasons") or [])
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skill-eval-intake",
        default="intelligence/SKILL_EVAL_RESULT_INTAKE.json",
    )
    parser.add_argument(
        "--result-dir",
        default="intelligence/skill_promotion_result_spool",
    )
    parser.add_argument(
        "--json-output",
        default="intelligence/SKILL_PROMOTION_RESULT_INTAKE.json",
    )
    parser.add_argument(
        "--markdown-output",
        default="intelligence/GLOBAL_SKILL_REVIEW_QUEUE.md",
    )
    args = parser.parse_args()

    skill_eval_intake = read_json(Path(args.skill_eval_intake), {})
    packets = read_packets(Path(args.result_dir))
    state = build_skill_promotion_result_intake(
        skill_eval_intake,
        packets,
    )
    state["source_snapshot_sha256"] = stable_hash(
        {
            "skill_eval_intake": skill_eval_intake,
            "result_packets": packets,
        }
    )

    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "
",
        encoding="utf-8",
    )
    md_path = Path(args.markdown_output)
    md_path.write_text(
        render_markdown(state) + "
",
        encoding="utf-8",
    )
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
