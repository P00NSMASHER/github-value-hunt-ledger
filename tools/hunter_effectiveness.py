#!/usr/bin/env python3
"""Evidence-only hunter effectiveness report. A candidate is never an outcome."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from tools.public_repo_scout import validate_manifest


def describe_worker(worker: dict, queue_root: Path, scope: str) -> dict:
    """Read only a current-scope queue. Never infer execution from a stale file."""
    record = {
        "id": worker["id"],
        "project": worker["project"],
        "status": "NOT_OBSERVED_IN_SCOPE",
        "candidates": None,
        "last_material_snapshot": None,
        "queue_path": None,
        "verified_integration": "UNKNOWN",
        "measured_result": "UNKNOWN",
    }
    path = queue_root / (worker["id"] + ".json")
    if not path.exists():
        return record
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        record["status"] = "INVALID_QUEUE"
        return record
    if saved.get("scope_version") != scope:
        return record
    if (saved.get("worker_id") != worker["id"] or
        saved.get("project") != worker["project"] or
        saved.get("target_repository") != worker["target_repository"] or
        saved.get("mission") != worker["mission"] or
        saved.get("evidence_gate") != worker.get("evidence_gate")):
        record["status"] = "INVALID_QUEUE"
        return record
    candidates = saved.get("candidates")
    diagnostics = saved.get("search_diagnostics")
    if not isinstance(candidates, list) or not isinstance(diagnostics, list):
        record["status"] = "INVALID_QUEUE"
        return record
    if saved.get("candidate_count") != len(candidates):
        record["status"] = "INVALID_QUEUE"
        return record
    observed = saved.get("generated_at")
    try:
        parsed = dt.datetime.fromisoformat(str(observed).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timestamp has no time zone")
    except (ValueError, TypeError):
        record["status"] = "INVALID_QUEUE"
        return record
    record["last_material_snapshot"] = observed
    record["queue_path"] = "../intelligence/scout_queue/" + path.name
    record["candidates"] = len(candidates)
    if any(isinstance(item, dict) and item.get("error") for item in diagnostics):
        record["status"] = "SOURCE_ERROR"
    elif any(not isinstance(item, dict) or
             item.get("status") != "PRE_VERIFICATION_CANDIDATE" or
             not item.get("repository") or
             not item.get("exact_revision") for item in candidates):
        record["status"] = "INVALID_QUEUE"
    elif not candidates and diagnostics and all(isinstance(item, dict) and
                                                item.get("returned") == 0 for item in diagnostics):
        record["status"] = "NO_SEARCH_MATCHES"
    else:
        record["status"] = ("UNREVIEWED_CANDIDATES" if candidates
                            else "NO_NEW_CANDIDATES")
    return record


def collect(manifest: dict, queue_root: Path) -> dict:
    scope = validate_manifest(manifest)
    records = [describe_worker(w, queue_root, scope)
               for w in manifest["workers"]]
    return {
        "scope_version": scope,
        "workers": records,
        "current_scope_queue_count":
            sum(r["last_material_snapshot"] is not None for r in records),
        "unreviewed_candidate_count":
            sum(r["candidates"] or 0 for r in records
                if r["status"] == "UNREVIEWED_CANDIDATES"),
    }


def render(report: dict) -> str:
    rows = [
        "# Hunter effectiveness — evidence only",
        "",
        "Scope: " + report["scope_version"],
        "",
        "This tracks discovery snapshots, not proof of scheduled execution.",
        "Only an actual GitHub Actions schedule-event run proves a scheduled invocation.",
        "A green CI check, research candidate, or PR is **not** a live integration,",
        "scientific novelty finding, trading edge, payment, or saved engineering time.",
        "",
        "Current-scope queues: " + str(report["current_scope_queue_count"]) +
        "/14; unreviewed candidates: " + str(report["unreviewed_candidate_count"]),
        "",
        "| Hunter | Project | Latest recorded source state | Candidates | Last material snapshot (UTC) | Verified integration | Measured outcome |",
        "|---|---|---|---:|---|---|---|",
    ]
    for r in report["workers"]:
        count = str(r["candidates"]) if r["candidates"] is not None else "UNKNOWN"
        snapshot = r["last_material_snapshot"] or "UNKNOWN"
        state = r["status"]
        if r["queue_path"]:
            state = "[" + state + "](" + r["queue_path"] + ")"
        rows.append("| " + r["id"] + " | " + r["project"] +
                    " | " + state + " | " + count + " | " + snapshot +
                    " | " + r["verified_integration"] + " | " +
                    r["measured_result"] + " |")
    rows += [
        "",
        "## Independent outcome acceptance",
        "",
        "No verified deployment, payment, trading performance, original discovery,",
        "social conversion or saved engineering hours can be inferred from these",
        "GitHub search snapshots. Those outcomes remain **UNKNOWN** until separately",
        "linked to independent acceptance evidence and real-world measurements.",
        "",
        "Snapshots record material evidence changes; an unchanged snapshot date",
        "does not imply that a scheduled scan failed to execute.",
        "",
    ]
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="automation/hunter_schedule.json")
    parser.add_argument("--queue-root", default="intelligence/scout_queue")
    parser.add_argument("--output", default="automation/HUNTER_EFFECTIVENESS.md")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = collect(manifest, Path(args.queue_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = render(report)
    if not output.exists() or output.read_text(encoding="utf-8") != content:
        output.write_text(content, encoding="utf-8")
    print(json.dumps({
        "scope_version": report["scope_version"],
        "current_scope_queue_count": report["current_scope_queue_count"],
        "unreviewed_candidate_count": report["unreviewed_candidate_count"],
        "verified_outcomes": "UNKNOWN",
        "output": str(output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
