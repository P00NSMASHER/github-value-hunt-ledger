#!/usr/bin/env python3
"""Generate repair-candidate intake and skill-evaluation workbench artifacts."""

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

from production.repair_intake import build_repair_candidate_intake


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
        "# Skill Evaluation Queue",
        "",
        "Generated from immutable repair-candidate submissions. "
        "**This queue cannot write or globally promote a skill.**",
        "",
        "## Summary",
        "",
        f"- Submitted: **{summary['submitted']}**",
        f"- Ready for skill evaluation: **{summary['ready_for_skill_eval']}**",
        f"- Rejected after repair assessment: **{summary['rejected']}**",
        f"- Blocked at intake: **{summary['blocked']}**",
        "",
        "## Ready evaluations",
        "",
    ]
    if not state["skill_eval_queue"]:
        lines.append("- No repair candidate is ready for skill evaluation.")
    for row in state["skill_eval_queue"]:
        req = row["required_evaluation"]
        lines += [
            f"### {row['skill_eval_id']}",
            "",
            f"- Repair candidate: {row['repair_candidate_id']}",
            f"- Artifact: {row['artifact_id']}",
            f"- Baseline → candidate: {row['baseline_version']} → {row['candidate_version']}",
            f"- Minimum mutate-dev examples: {req['mutate_dev_examples_min']}",
            f"- Minimum promotion-test examples: {req['promotion_test_examples_min']}",
            f"- Minimum held-out score delta: {req['min_score_delta']:+.3f}",
            "- Hard regressions allowed: 0",
            "- Split fingerprints must be disjoint and provenance complete.",
            "- Adversarial, adjacent-domain, curator and canary gates still apply.",
            "",
        ]

    if state["blocked_submissions"]:
        lines += ["## Blocked submissions", ""]
        for row in state["blocked_submissions"]:
            lines.append(
                f"- {row.get('repair_candidate_id')}: "
                + ", ".join(row.get("reasons") or [])
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repair-queue",
        default="intelligence/REPAIR_QUEUE.json",
    )
    parser.add_argument(
        "--candidate-dir",
        default="intelligence/repair_candidate_spool",
    )
    parser.add_argument(
        "--json-output",
        default="intelligence/REPAIR_CANDIDATE_INTAKE.json",
    )
    parser.add_argument(
        "--markdown-output",
        default="intelligence/SKILL_EVAL_QUEUE.md",
    )
    args = parser.parse_args()

    repair_queue = read_json(Path(args.repair_queue), {})
    packets = read_packets(Path(args.candidate_dir))
    state = build_repair_candidate_intake(repair_queue, packets)
    state["source_snapshot_sha256"] = stable_hash(
        {
            "repair_queue": repair_queue,
            "candidate_packets": packets,
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
