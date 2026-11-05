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
    if receipt.get("schema_version") != 1 or receipt.get("worker_id") != worker["id"]:
        raise AcceptanceError("Unrecognized schema or worker")
    repo, sha = receipt.get("target_repository"), receipt.get("target_main_sha")
    pr_id, run_id = receipt.get("merged_pr_number"), receipt.get("independent_ci_run_id")
    if repo != worker["target_repository"] or not REPO.fullmatch(str(repo)):
        raise AcceptanceError("Target outside assigned repository")
    if not isinstance(sha, str) or not HEX.fullmatch(sha):
        raise AcceptanceError("Missing exact target main SHA")
    if (not isinstance(pr_id, int) or isinstance(pr_id, bool) or pr_id < 1
        or not isinstance(run_id, int) or isinstance(run_id, bool) or run_id < 1):
        raise AcceptanceError("Actual merged PR and CI run IDs required")
    if receipt.get("claimed_outcome") != "CI_VERIFIED_TARGET_CHANGE":
        raise AcceptanceError("Unsupported outcome claim")
    pr = api.get("/repos/" + repo + "/pulls/" + str(pr_id))
    branch = api.get("/repos/" + repo + "/branches/main")
    ci = api.get("/repos/" + repo + "/actions/runs/" + str(run_id))
    if (pr.get("merged") is not True or not pr.get("merged_at")
        or pr.get("merge_commit_sha") != sha
        or (pr.get("base") or {}).get("ref") != "main"
        or int(pr.get("changed_files") or 0) < 1):
        raise AcceptanceError("Changed target PR is not proven merged on main")
    if (branch.get("name") != "main" or (branch.get("commit") or {}).get("sha") != sha):
        raise AcceptanceError("Target main is not exact claimed commit")
    if (ci.get("head_sha") != sha or ci.get("head_branch") != "main"
        or ci.get("event") != "push"
        or ci.get("status") != "completed" or ci.get("conclusion") != "success"
        or (ci.get("repository") or {}).get("full_name") != repo
        or not ci.get("html_url")):
        raise AcceptanceError("Independent passing push-to-main CI not proven")
    try:
        merged_at = dt.datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
        checked_at = dt.datetime.fromisoformat(ci["created_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise AcceptanceError("Missing independent event timestamps") from exc
    if checked_at < merged_at - dt.timedelta(minutes=2):
        raise AcceptanceError("CI run predates target merge")
    return {
        "status": "ACCEPTED_CI_VERIFIED_TARGET_CHANGE",
        "worker_id": worker["id"],
        "target_repository": repo,
        "target_main_sha": sha,
        "merged_pr_url": pr.get("html_url"),
        "ci_run_url": ci["html_url"],
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
