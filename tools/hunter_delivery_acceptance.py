#!/usr/bin/env python3
"""Fail-closed readback of independently tested merged target changes.

Successful review establishes CI-verified target source change only.
It never establishes revenue, novelty, adoption, deployment or source reuse.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from tools.hunter_source_inspection import GitHubReadOnly, REPO, HEX
from tools.public_repo_scout import validate_manifest


class AcceptanceError(ValueError):
    pass


def verify_delivery(receipt: dict, worker: dict, api) -> dict:
    """Validate completed code changes against live merged source and two distinct CI workflows."""
    if receipt.get("schema_version") != 1 or receipt.get("worker_id") != worker["id"]:
        raise AcceptanceError("Unrecognized schema or worker")
    repo, sha = receipt.get("target_repository"), receipt.get("target_main_sha")
    pr_id = receipt.get("merged_pr_number")
    test_id = receipt.get("test_ci_run_id")
    verify_id = receipt.get("independent_ci_run_id")
    required_steps = receipt.get("required_test_steps")
    if repo != worker["target_repository"] or not REPO.fullmatch(str(repo)):
        raise AcceptanceError("Target outside assigned repository")
    if not isinstance(sha, str) or not HEX.fullmatch(sha):
        raise AcceptanceError("Missing exact target main SHA")
    if (not isinstance(pr_id, int) or isinstance(pr_id, bool) or pr_id < 1
        or not isinstance(test_id, int) or isinstance(test_id, bool) or test_id < 1
        or not isinstance(verify_id, int) or isinstance(verify_id, bool) or verify_id < 1
        or test_id == verify_id):
        raise AcceptanceError("Actual merged PR and separate test/verifier run IDs required")
    if (not isinstance(required_steps, list) or not 1 <= len(required_steps) <= 10
        or any(not isinstance(x, str) or len(x.strip()) < 6 or len(x) > 160
               for x in required_steps)
        or len(set(required_steps)) != len(required_steps)
        or not any(any(term in step.lower() for term in
                       ("test", "verify", "acceptance", "regression"))
                   for step in required_steps)):
        raise AcceptanceError("Specific named passing test/verification steps required")
    if receipt.get("claimed_outcome") != "CI_VERIFIED_TARGET_CHANGE":
        raise AcceptanceError("Unsupported outcome claim")
    for metric in ("revenue_usd", "trading_profit_usd", "engineering_hours_saved",
                   "scientific_novelty", "customer_conversions"):
        if receipt.get(metric) not in (None, "UNKNOWN"):
            raise AcceptanceError("Real-world measurement requires independent external evidence")
    pr = api.get("/repos/" + repo + "/pulls/" + str(pr_id))
    branch = api.get("/repos/" + repo + "/branches/main")
    if (pr.get("merged") is not True or not pr.get("merged_at")
        or pr.get("merge_commit_sha") != sha
        or (pr.get("base") or {}).get("ref") != "main"
        or int(pr.get("changed_files") or 0) < 1):
        raise AcceptanceError("Changed target PR is not proven merged on main")
    if branch.get("name") != "main" or (branch.get("commit") or {}).get("sha") != sha:
        raise AcceptanceError("Target main is not exact claimed commit")
    try:
        merged_at = dt.datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise AcceptanceError("Missing target merge timestamp") from exc

    def successful_run(run_id: int, label: str) -> dict:
        ci = api.get("/repos/" + repo + "/actions/runs/" + str(run_id))
        if (ci.get("head_sha") != sha or ci.get("head_branch") != "main"
            or ci.get("event") != "push" or ci.get("status") != "completed"
            or ci.get("conclusion") != "success"
            or (ci.get("repository") or {}).get("full_name") != repo
            or not ci.get("html_url") or not ci.get("workflow_id")):
            raise AcceptanceError(label + " successful exact-head push CI not proven")
        try:
            checked_at = dt.datetime.fromisoformat(ci["created_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError) as exc:
            raise AcceptanceError(label + " lacks independent timestamp") from exc
        if checked_at < merged_at - dt.timedelta(minutes=2):
            raise AcceptanceError(label + " predates the claimed target merge")
        return ci

    test = successful_run(test_id, "Target tests")
    verified = successful_run(verify_id, "Independent verifier")
    if test["workflow_id"] == verified["workflow_id"]:
        raise AcceptanceError("Test and verifier runs must be distinct workflows")
    jobs = api.get("/repos/" + repo + "/actions/runs/" + str(test_id) + "/jobs?per_page=100")
    if not isinstance(jobs.get("jobs"), list):
        raise AcceptanceError("Target test steps cannot be independently read")
    passed = {step.get("name") for job in jobs["jobs"]
              if job.get("conclusion") == "success"
              for step in job.get("steps", [])
              if isinstance(step, dict) and step.get("conclusion") == "success"}
    if not set(required_steps).issubset(passed):
        raise AcceptanceError("Required named acceptance tests did not pass at target SHA")
    return {
        "status": "ACCEPTED_CI_VERIFIED_TARGET_CHANGE",
        "worker_id": worker["id"],
        "target_repository": repo,
        "target_main_sha": sha,
        "merged_pr_url": pr.get("html_url"),
        "target_test_run_url": test["html_url"],
        "independent_ci_run_url": verified["html_url"],
        "passed_test_steps": required_steps,
        "source_reuse": "UNKNOWN",
        "production_deployment": "UNKNOWN",
        "revenue": "UNKNOWN",
        "trading_edge": "UNKNOWN",
        "scientific_novelty": "UNKNOWN",
        "engineering_time_saved": "UNKNOWN",
    }



def evaluate_receipts(manifest: dict, records: list[dict], api) -> dict:
    validate_manifest(manifest)
    workers = {w["id"]: w for w in manifest["workers"]}
    accepted, rejected, seen = [], [], set()
    for index, receipt in enumerate(records):
        worker_id = receipt.get("worker_id") if isinstance(receipt, dict) else None
        identity = (worker_id, receipt.get("target_repository"),
                    receipt.get("target_main_sha")) if isinstance(receipt, dict) else (index,)
        if identity in seen:
            rejected.append({"index": index, "reason": "Duplicate target revision receipt"})
            continue
        seen.add(identity)
        try:
            if worker_id not in workers:
                raise AcceptanceError("Unassigned Hunter")
            accepted.append(verify_delivery(receipt, workers[worker_id], api))
        except (AcceptanceError, OSError, ValueError, KeyError) as exc:
            rejected.append({"index": index, "worker_id": worker_id, "reason": str(exc)[:250]})
    return {"authority": "LIVE_GITHUB_READBACK_ONLY",
            "accepted_technical_changes": len(accepted),
            "rejected_claims": len(rejected),
            "accepted": accepted, "rejected": rejected,
            "independent_real_world_outcomes": "NOT_ESTABLISHED"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="automation/hunter_schedule.json")
    p.add_argument("--receipt-root", default="intelligence/hunter_delivery_receipts")
    p.add_argument("--output", default="hunter-delivery-acceptance.json")
    args = p.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    root = Path(args.receipt_root)
    records = [json.loads(f.read_text(encoding="utf-8"))
               for f in sorted(root.glob("*.json"))] if root.is_dir() else []
    report = evaluate_receipts(manifest, records,
                               GitHubReadOnly(os.getenv("GITHUB_TOKEN", "")))
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"accepted_technical_changes": report["accepted_technical_changes"],
                      "rejected_claims": report["rejected_claims"]}, sort_keys=True))
    return 2 if report["rejected_claims"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
