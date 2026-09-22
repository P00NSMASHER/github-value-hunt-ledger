#!/usr/bin/env python3
"""Generate the advisory hunter repair workbench from learning evidence."""

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

from production.repair_queue import build_repair_queue


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_failure_packets(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    packets: list[dict[str, Any]] = []
    for file_path in sorted(path.glob("*.json")):
        value = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{file_path}: expected JSON object")
        value = dict(value)
        value["_source_file"] = str(file_path)
        packets.append(value)
    return packets


def source_sha(
    learning_state: Any,
    failure_packets: Any,
    training_environment: Any,
) -> str:
    payload = json.dumps(
        {
            "learning_state": learning_state,
            "failure_packets": failure_packets,
            "training_environment": training_environment,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def render_markdown(queue: dict[str, Any]) -> str:
    summary = queue["summary"]
    lines = [
        "# Hunter Repair Workbench",
        "",
        "Generated advisory queue for bounded hunter-system repair. "
        "**This file does not authorize automatic mutation or promotion.**",
        "",
        "## Summary",
        "",
        f"- Tasks: **{summary['tasks']}**",
        f"- Ready for bounded repair: **{summary['ready_for_repair']}**",
        f"- Needs reproduction first: **{summary['needs_reproduction']}**",
        f"- Blocked source packets: **{summary['blocked_sources']}**",
        "",
        "## Active tasks",
        "",
    ]
    if not queue["tasks"]:
        lines.append("- No repair task currently has sufficient evidence.")
    for task in queue["tasks"]:
        target = task["target"]
        source = task["source"]
        lines += [
            f"### {task['repair_task_id']} — {task['state']}",
            "",
            f"- Priority: **{task['priority_score']}**",
            f"- Target: {target['type']} / {target['id']}",
            f"- Source: {source['kind']} / {source['id']}",
            f"- Failure class: {task['failure_class']}",
            f"- Observation: {task['failure_observation']}",
        ]
        if task["confirm_failure_refs"]:
            refs = ", ".join(
                str(row.get("run_id"))
                for row in task["confirm_failure_refs"][:5]
            )
            lines.append(f"- Negative confirm runs: {refs}")
        if task["regression_test_requirement"]:
            lines.append(
                "- Regression-test requirement: "
                f"{task['regression_test_requirement']}"
            )
        lines.append(f"- Next action: {task['next_action']}")
        lines.append("")

    if queue["blocked_sources"]:
        lines += ["## Blocked source packets", ""]
        for row in queue["blocked_sources"]:
            lines.append(
                f"- {row['source_id']}: "
                + ", ".join(row["reasons"])
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--learning-state",
        default="intelligence/LEARNING_STATE.json",
    )
    parser.add_argument(
        "--training-environment",
        default="intelligence/TRAINING_ENVIRONMENT.json",
    )
    parser.add_argument(
        "--failure-dir",
        default="intelligence/learning_failure_spool",
    )
    parser.add_argument(
        "--json-output",
        default="intelligence/REPAIR_QUEUE.json",
    )
    parser.add_argument(
        "--markdown-output",
        default="intelligence/REPAIR_QUEUE.md",
    )
    args = parser.parse_args()

    learning_state = read_json(Path(args.learning_state), {})
    training_environment = read_json(
        Path(args.training_environment),
        {},
    )
    failures = read_failure_packets(Path(args.failure_dir))
    queue = build_repair_queue(
        learning_state,
        failures,
        training_environment,
    )
    queue["source_snapshot_sha256"] = source_sha(
        learning_state,
        failures,
        training_environment,
    )

    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(queue, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path = Path(args.markdown_output)
    md_path.write_text(
        render_markdown(queue) + "\n",
        encoding="utf-8",
    )
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
