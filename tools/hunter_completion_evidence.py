#!/usr/bin/env python3
"""Fail-closed acceptance of completed Hunter integrations using live GitHub receipts.

Source scouting and read-only inspections do not qualify as completed work.
A COMPLETE entry must reference a merged target commit and successful, distinct
test and verifier workflows on that exact commit. Real-world metrics require
a separate independently validated external measurement and are never inferred here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

from tools.hunter_source_inspection import GitHubRead, REPO, SHA

WORKER = re.compile(r"^HUNTER-(0[1-9]|1[0-4])$")
ALLOWED_METRICS = (None, "UNKNOWN")

class AcceptanceError(ValueError):
    pass

def require(ok: bool, why: str) -> None:
    if not ok:
        raise AcceptanceError(why)

def validate_shape(row: dict) -> None:
    require(isinstance(row, dict) and row.get("schema_version") == 1, "unsupported receipt schema")
    require(row.get("status") == "COMPLETE", "only COMPLETE claims are admissible")
    require(bool(WORKER.fullmatch(str(row.get("worker_id") or ""))), "unrecognized worker")
    require(bool(REPO.fullmatch(str(row.get("source_repository") or ""))), "source repository invalid")
    require(bool(SHA.fullmatch(str(row.get("source_exact_revision") or ""))), "source SHA must be immutable")
    require(bool(REPO.fullmatch(str(row.get("target_repository") or ""))), "target repository invalid")
    require(bool(SHA.fullmatch(str(row.get("target_commit_sha") or ""))), "target SHA must be immutable")
    require(str(row["target_repository"]).startswith("P00NSMASHER/"), "target is outside owner scope")
    require(type(row.get("merged_pr_number")) is int and row["merged_pr_number"] > 0, "merged PR number required")
    for key in ("test_run_id", "verifier_run_id"):
        require(type(row.get(key)) is int and row[key] > 0, key + " required")
    require(row["test_run_id"] != row["verifier_run_id"], "verifier cannot be the same run as builder")
    steps = row.get("required_test_steps")
    require(isinstance(steps, list) and 1 <= len(steps) <= 10 and
            len(steps) == len(set(str(x) for x in steps)) and
            all(isinstance(x, str) and 3 <= len(x) <= 160 for x in steps),
            "named target acceptance steps required")
    require(row.get("external_outcome") in ALLOWED_METRICS and
            row.get("revenue_usd") in ALLOWED_METRICS and
            row.get("trading_profit_usd") in ALLOWED_METRICS and
            row.get("engineering_hours_saved") in ALLOWED_METRICS and
            row.get("scientific_novelty") in ALLOWED_METRICS,
            "real-world claims need a separate external measurement verifier")

def verify_live(row: dict, github: GitHubRead) -> dict:
    validate_shape(row)
    target, sha = row["target_repository"], row["target_commit_sha"]
    source, source_sha = row["source_repository"], row["source_exact_revision"]
    original = github.get(f"/repos/{source}/git/commits/{source_sha}")
    require(original.get("sha") == source_sha, "source exact revision is not retrievable")
    pr = github.get(f"/repos/{target}/pulls/{row['merged_pr_number']}")
    require(pr.get("merged") is True and pr.get("state") == "closed" and
            pr.get("merge_commit_sha") == sha, "target commit is not verified as merged PR")
    results = []
    for name in ("test_run_id", "verifier_run_id"):
        run_id = row[name]
        run = github.get(f"/repos/{target}/actions/runs/{run_id}")
        require(run.get("head_sha") == sha and
                run.get("conclusion") == "success" and
                run.get("status") == "completed" and
                (run.get("repository") or {}).get("full_name") == target,
                name + " does not prove successful exact-head execution")
        jobs = github.get(f"/repos/{target}/actions/runs/{run_id}/jobs?per_page=100")
        require(isinstance(jobs.get("jobs"), list) and jobs["jobs"], name + " has no inspectable jobs")
        complete = [job for job in jobs["jobs"] if job.get("conclusion") == "success"]
        require(complete, name + " has no passing jobs")
        steps = {step.get("name") for job in complete for step in job.get("steps", [])
                 if step.get("conclusion") == "success"}
        if name == "test_run_id":
            require(set(row["required_test_steps"]).issubset(steps),
                    "named acceptance steps did not pass on the exact target commit")
        results.append({"run_id": run_id, "workflow_id": run.get("workflow_id"),
                        "run_url": run.get("html_url"), "head_sha": run["head_sha"]})
    require(results[0]["workflow_id"] is not None and
            results[1]["workflow_id"] is not None and
            results[0]["workflow_id"] != results[1]["workflow_id"],
            "testing and independent verification must use distinct workflows")
    return {"worker_id": row["worker_id"], "status": "VERIFIED_CODE_INTEGRATION",
            "target_repository": target, "target_commit_sha": sha,
            "merged_pr_number": row["merged_pr_number"], "live_evidence": results,
            "real_world_outcomes": "UNKNOWN", "checks_confirmed": True}

def verify_dir(directory: Path, github: GitHubRead) -> dict:
    entries = sorted(directory.glob("*.json")) if directory.exists() else []
    accepted = []
    for path in entries:
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            accepted.append(verify_live(row, github))
        except Exception as exc:
            raise AcceptanceError(f"{path.name}: {str(exc)}") from exc
    return {"schema_version": 1, "accepted_integrations": len(accepted),
            "accepted": accepted, "real_world_outcomes": "UNKNOWN",
            "empty_is_not_a_completed_outcome": True}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="intelligence/hunter_completion_receipts")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    try:
        report = verify_dir(Path(args.directory), GitHubRead(os.getenv("GITHUB_TOKEN") or ""))
    except AcceptanceError as exc:
        print(json.dumps({"accepted": False, "error": str(exc)}))
        return 2
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"accepted_integrations": report["accepted_integrations"],
                      "real_world_outcomes": "UNKNOWN"}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
