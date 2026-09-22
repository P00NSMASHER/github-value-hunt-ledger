"""Validate and report the pinned elite-source ingestion portfolio."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "intelligence" / "ELITE_SOURCE_INGESTION.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
VALID_STATES = {"QUEUED", "STARTED", "MAPPED", "INTEGRATED", "DEFERRED", "BLOCKED"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_registry(payload)
    return payload


def validate_registry(payload: dict) -> None:
    if payload.get("schema_version") != 1:
        raise ValueError("elite registry must use schema_version 1")
    rows = payload.get("sources")
    if not isinstance(rows, list) or not rows:
        raise ValueError("elite registry requires non-empty sources")

    source_ids: set[str] = set()
    pins: set[tuple[str, str]] = set()
    for row in rows:
        source_id = row.get("source_id")
        repository = row.get("repository")
        revision = row.get("revision")
        score = row.get("score")
        priority = row.get("priority")
        status = row.get("status")
        target = row.get("integration_target")
        tier = row.get("source_tier")

        if not isinstance(source_id, str) or not source_id:
            raise ValueError("source_id is required")
        if source_id in source_ids:
            raise ValueError(f"duplicate source_id: {source_id}")
        source_ids.add(source_id)

        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ValueError(f"{source_id}: repository must be owner/name")
        if not isinstance(revision, str) or not SHA40.fullmatch(revision):
            raise ValueError(f"{source_id}: exact 40-character revision required")
        pin = (repository.casefold(), revision)
        if pin in pins:
            raise ValueError(f"{source_id}: duplicate repository+revision pin")
        pins.add(pin)

        if type(score) is not int or score < 0 or score > 30:
            raise ValueError(f"{source_id}: invalid score")
        if score < 28 and tier != "MASTER_UNIQUE":
            raise ValueError(f"{source_id}: sub-28 source needs MASTER_UNIQUE justification")
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"{source_id}: invalid priority")
        if status not in VALID_STATES:
            raise ValueError(f"{source_id}: invalid status")
        if not isinstance(target, str) or not target:
            raise ValueError(f"{source_id}: integration_target is required")


def summarize(payload: dict) -> dict:
    rows = payload["sources"]
    return {
        "sources": len(rows),
        "by_status": dict(sorted(Counter(r["status"] for r in rows).items())),
        "by_priority": dict(sorted(Counter(r["priority"] for r in rows).items())),
        "by_target": dict(sorted(Counter(r["integration_target"] for r in rows).items())),
        "p0_open": sum(r["priority"] == "P0" and r["status"] in {"QUEUED", "STARTED"} for r in rows),
        "started": [r["source_id"] for r in rows if r["status"] == "STARTED"],
    }


def ordered_queue(payload: dict) -> list[dict]:
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    state_rank = {"STARTED": 0, "QUEUED": 1, "MAPPED": 2, "INTEGRATED": 3, "BLOCKED": 4, "DEFERRED": 5}
    return sorted(
        payload["sources"],
        key=lambda r: (rank[r["priority"]], state_rank[r["status"]], -r["score"], r["integration_target"], r["repository"]),
    )


def render_markdown(payload: dict) -> str:
    summary = summarize(payload)
    lines = [
        "# Elite source ingestion queue",
        "",
        f"Pinned sources: **{summary['sources']}**. P0 open: **{summary['p0_open']}**.",
        "",
        "This queue is an integration plan, not proof that a source is installed, correct, production-safe, or commercially validated.",
        "",
        "## Summary",
        "",
        f"- Status: {summary['by_status']}",
        f"- Priority: {summary['by_priority']}",
        f"- Targets: {summary['by_target']}",
        "",
        "## Queue",
        "",
        "| Priority | State | Score | Source | Target | Revision |",
        "|---|---|---:|---|---|---|",
    ]
    for row in ordered_queue(payload):
        lines.append(
            f"| {row['priority']} | {row['status']} | {row['score']} | "
            f"{row['repository']} | {row['integration_target']} | `{row['revision'][:12]}` |"
        )
    lines += ["", "## Invariants", ""]
    lines += [f"- {rule}" for rule in payload.get("policy", [])]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    payload = load_registry(args.registry)
    if args.format == "markdown":
        print(render_markdown(payload), end="")
    else:
        print(json.dumps(summarize(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
