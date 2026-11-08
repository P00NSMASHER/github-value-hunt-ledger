#!/usr/bin/env python3
"""Fail-closed, GitHub-native Hunter fleet health evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

REPO = "P00NSMASHER/github-value-hunt-ledger"
WORKERS = tuple(f"HUNTER-{i:02d}" for i in range(1, 15))


def api(path: str):
    if not path.startswith(f"/repos/{REPO}/"):
        raise ValueError("API path outside Hunter repository")
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "hunter-fleet-health/1"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(
            "https://api.github.com" + path, headers=headers), timeout=30) as reply:
        return json.load(reply)



def inspect_workflow_receipt(run: dict, read_api=api) -> dict:
    """Inspect actual Actions job AND uploaded artifact, not the parent green badge."""
    run_id = run.get("id")
    evidence = {"run_id": run_id, "event": run.get("event"),
                "status": "NOT_PROVEN", "verified": False}
    if type(run_id) is not int or run_id < 1:
        evidence["status"] = "INVALID_RUN_ID"
        return evidence
    try:
        jobs_result = read_api(
            f"/repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")
        jobs = jobs_result.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError("Job listing unavailable")
        job = next((job for job in jobs
                    if job.get("name") == "candidate-inspection"), None)
        if job is None:
            evidence["status"] = "INSPECTION_JOB_MISSING"
            return evidence
        if job.get("conclusion") == "skipped":
            evidence["status"] = "INSPECTION_SKIPPED"
            return evidence
        if (run.get("status") != "completed" or
            run.get("conclusion") != "success" or
            job.get("conclusion") != "success"):
            evidence["status"] = "INSPECTION_JOB_FAILED"
            return evidence
        artifacts_result = read_api(
            f"/repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100")
        artifacts = artifacts_result.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("Artifact listing unavailable")
        attempt = run.get("run_attempt") or 1
        expected_name = f"hunter-inspection-{run_id}-{attempt}"
        artifact = next(
            (a for a in artifacts
             if a.get("name") == expected_name and
             a.get("expired") is False and
             type(a.get("size_in_bytes")) is int and
             a["size_in_bytes"] > 0), None
        )
        if artifact is None:
            evidence["status"] = "INSPECTION_ARTIFACT_MISSING"
            return evidence
        evidence.update({
            "status": "INSPECTION_JOB_AND_ARTIFACT_VERIFIED",
            "verified": True,
            "artifact_id": artifact.get("id"),
            "artifact_name": expected_name,
            "job_id": job.get("id"),
            "run_url": run.get("html_url"),
        })
    except Exception:
        # API outages or malformed responses cannot manufacture green evidence.
        evidence["status"] = "INSPECTION_READBACK_FAILED"
    return evidence



def is_integrator_run(run: dict) -> bool:
    """Only an exact first-party integrator run can omit source inspection."""
    name = run.get("display_title") or run.get("name")
    event = run.get("event")
    if not isinstance(name, str) or run.get("head_branch") != "main":
        return False
    if (run.get("head_repository") or {}).get("full_name") != REPO:
        return False
    if event == "schedule":
        return name == "Hunter 7 4,16 * * * slot=native"
    return (event == "repository_dispatch"
            and (run.get("actor") or {}).get("login") == "portfolio-brain-v8-runtime[bot]"
            and re.fullmatch(
                r"Hunter INTEGRATOR slot=20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:00Z",
                name,
            ) is not None)


def inspect_integrator_receipt(run: dict, read_api=api) -> dict:
    """Validate a real Integrator execution receipt, never a source-inspection pass."""
    run_id = run.get("id")
    proof = {"run_id": run_id, "status": "INTEGRATOR_RECEIPT_UNVERIFIED",
             "scout_receipt_verified": False, "delivery_verified": False,
             "parent_conclusion": run.get("conclusion")}
    if not is_integrator_run(run) or type(run_id) is not int or run_id <= 0:
        return proof
    try:
        jobs = read_api(
            f"/repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100").get("jobs")
        if not isinstance(jobs, list):
            return proof
        scout = [j for j in jobs if j.get("name") == "scout"]
        inspector = [j for j in jobs if j.get("name") == "candidate-inspection"]
        if (len(scout) != 1 or len(inspector) != 1
                or scout[0].get("conclusion") != "success"
                or inspector[0].get("conclusion") != "skipped"
                or run.get("status") != "completed"):
            return proof
        artifacts = read_api(
            f"/repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100").get("artifacts")
        if not isinstance(artifacts, list):
            return proof
        attempt = run.get("run_attempt") or 1
        label = f"hunter-integrator-{run_id}-{attempt}"
        valid = [a for a in artifacts if a.get("name") == label
                 and a.get("expired") is False
                 and type(a.get("size_in_bytes")) is int and a["size_in_bytes"] > 0]
        if len(valid) != 1:
            return proof
        proof.update(status="INTEGRATOR_SCOUT_RECEIPT_VERIFIED",
                     scout_receipt_verified=True,
                     delivery_verified=(run.get("conclusion") == "success"),
                     artifact_id=valid[0].get("id"))
    except Exception:
        # Missing provider evidence must not masquerade as an eligible skip.
        return proof
    return proof


def inspect_recent_scout_delivery(runs: list[dict], now: dt.datetime,
                                  read_api=api) -> dict:
    """Sample 2 scheduled workers and the latest recovery, with bounded API reads.

    The integrator's scheduled scout deliberately skips the inspection job.
    Sample results are evidence of these runs only, never the whole 14-worker
    population or independently accepted downstream work.
    """
    recent = []
    for run in runs:
        try:
            created = dt.datetime.fromisoformat(
                run["created_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        age = (now - created).total_seconds()
        if 0 <= age <= 18 * 3600 and run.get("status") == "completed":
            recent.append(run)
    recent.sort(key=lambda run: run["created_at"], reverse=True)
    result = {}
    for event, required, max_review in (
        ("schedule", 2, 12),
        ("repository_dispatch", 1, 4),
    ):
        receipts = []
        integrators = []
        scanned = 0
        for run in recent:
            if run.get("event") != event or scanned >= max_review:
                continue
            scanned += 1
            proof = inspect_workflow_receipt(run, read_api)
            if proof["status"] == "INSPECTION_SKIPPED" and is_integrator_run(run):
                integrator = inspect_integrator_receipt(run, read_api)
                integrators.append(integrator)
                if integrator["scout_receipt_verified"]:
                    continue  # A proven integrator is NOT a candidate inspector.
                proof = {**proof, "status": "INTEGRATOR_RECEIPT_UNVERIFIED"}
            receipts.append(proof)
            if len(receipts) >= required:
                break
        result[event] = {
            "required": required,
            "scanned": scanned,
            "proofs": receipts,
            "integrators": integrators,
            "verified": len(receipts) == required and all(
                proof["verified"] for proof in receipts),
        }
    return result


def evaluate(runs: list[dict], queues: dict[str, dict], digest: str,
             now: dt.datetime, open_prs: list[dict], inject_failure=False,
             inspections: dict | None = None) -> dict:
    current = {w for w, q in queues.items()
               if w in WORKERS and q.get("scope_version") == "active-projects-2026-11-v2"}
    recent = [r for r in runs if (now - dt.datetime.fromisoformat(
        r["created_at"].replace("Z", "+00:00"))).total_seconds() <= 18 * 3600]
    scheduled = [r for r in recent if r.get("event") == "schedule"]
    latest_cycle = sorted(scheduled, key=lambda r: r["created_at"], reverse=True)[:15]
    recovery = [r for r in recent if r.get("event") == "repository_dispatch"]
    digest_queues = re.search(r"Queue snapshots read: (\d+)", digest)
    digest_candidates = re.search(r"Unique exact-revision candidates: (\d+)", digest)
    generated = [p for p in open_prs if re.fullmatch(
        r"automation/retally-(scout|catalog|integrator|technology)-.*",
        str((p.get("head") or {}).get("ref", "")))]
    checks = {
        "assignments": set(queues).issubset(set(WORKERS)),
        "scheduled_recent": len(scheduled) >= 15,
        "scheduled_success": len(latest_cycle) == 15 and all(
            r.get("conclusion") == "success" for r in latest_cycle),
        "recovery_demonstrated": any(r.get("conclusion") == "success" for r in recovery),
        "queues_current": current == set(WORKERS),
        "integrator_complete": bool(digest_queues) and int(digest_queues.group(1)) == 14,
        "integrator_count_present": bool(digest_candidates),
        "generated_pr_backlog_clear": not generated,
    }
    if inspections is not None:
        checks["scheduled_inspection_delivery"] = bool(
            (inspections.get("schedule") or {}).get("verified"))
        checks["recovery_inspection_delivery"] = bool(
            (inspections.get("repository_dispatch") or {}).get("verified"))
    # A completed integrator scout can still fail its PR handoff; make that
    # independently visible instead of laundering it into green inspection.
    integrators = (inspections or {}).get("repository_dispatch", {}).get("integrators", [])
    if integrators:
        checks["integrator_recovery_delivery"] = bool(integrators[0]["delivery_verified"])
    if inject_failure:
        checks["injected_failure_detected"] = False
    return {
        "observed_at": now.isoformat(), "checks": checks,
        "health_percent": round(100 * sum(checks.values()) / len(checks), 1),
        "healthy": all(checks.values()), "current_queues": sorted(current),
        "recent_scheduled": len(scheduled), "recent_recovery": len(recovery),
        "recent_recovery_success": sum(r.get("conclusion") == "success" for r in recovery),
        "generated_open_prs": [p.get("number") for p in generated],
        "digest_candidates": int(digest_candidates.group(1)) if digest_candidates else None,
        "inspection_delivery": inspections,
    }



def governed_runtime_truth(root: Path) -> dict:
    """Do not let green source scouting imply enabled/adopted V16 workers.

    Uses only publicly inspectable non-gold benchmark and runtime data.
    Does not read ChatGPT task state or authorize an activation.
    """
    from tools.ti_benchmark_receipt_guard import (
        SCORE_ROW, RESULT_ROW, validate_benchmark_receipts,
    )

    text = (root / "benchmark/SCOREBOARD.md").read_text(encoding="utf-8")
    benchmark = validate_benchmark_receipts(root, text)
    scored = {(task, arm.upper()) for task, arm in SCORE_ROW.findall(text)}
    source_results = set()
    for number in range(1, 8):
        for arm in ("CONTROL", "EXPERIMENT"):
            path = root / "benchmark/results" / f"pair{number}-{arm.lower()}.md"
            for task in RESULT_ROW.findall(path.read_text(encoding="utf-8")):
                source_results.add((task, arm))
    pending_score = sorted(
        f"{task}/{arm}" for task, arm in (source_results - scored)
    )
    readiness = json.loads(
        (root / "intelligence/HUNTER_RESTART_READINESS.json")
        .read_text(encoding="utf-8")
    )
    policy = json.loads(
        (root / "intelligence/hunter_runtime_policy.json")
        .read_text(encoding="utf-8")
    )
    activation = json.loads(
        (root / "intelligence/activation_metrics.json")
        .read_text(encoding="utf-8")
    )
    scored_count = benchmark["matched_scored_tasks"]
    readiness_count = (readiness.get("evidence") or {}).get(
        "matched_benchmark_tasks"
    )
    mode = policy.get("mode", "UNKNOWN")
    active = bool(activation.get("runtime_activation_enabled"))
    activations = int(activation.get("current_activations") or 0)
    return {
        "evidence_scope": "SOURCE_SNAPSHOT_NOT_CHATGPT_TASK_STATUS",
        "scored_matched_tasks": scored_count,
        "required_matched_tasks": benchmark["frozen_task_count"],
        "raw_result_arms_unscored": pending_score,
        "benchmark_snapshot_consistent": readiness_count == scored_count,
        "readiness_state": readiness.get("state", "UNKNOWN"),
        "readiness_blockers": [
            item.get("code")
            for item in readiness.get("blockers") or []
            if isinstance(item, dict)
        ],
        "adaptive_runtime_mode": mode,
        "generated_activation_enabled": active,
        "current_generated_activations": activations,
        "source_inspection_not_equivalent_to_completed_work": True,
        "chatgpt_task_health": "NOT_OBSERVABLE_FROM_GITHUB",
        "full_worker_runtime_verified": "NOT_ESTABLISHED",
        "worker_claim_and_delivery_proof": "NOT_EVALUATED_BY_THIS_HEALTH_PROBE",
    }


def render(report: dict) -> str:
    rows = ["# Hunter fleet health", "", f"Observed: {report['observed_at']}",
            f"Scouting operational gates: {report['health_percent']}%", "",
            "| Gate | Result |", "|---|---|"]
    rows += [f"| {name} | {'PASS' if value else 'FAIL'} |"
             for name, value in report["checks"].items()]
    rows += ["", f"Current queues: {len(report['current_queues'])}/14",
             f"Recent scheduled runs: {report['recent_scheduled']}",
             f"Recent recovery successes: {report['recent_recovery_success']}/{report['recent_recovery']}",
             "", "A candidate or green run is not a verified real-world outcome.", ""]
    inspections = report.get("inspection_delivery")
    if inspections:
        rows += ["## Inspected execution proof (bounded samples)", ""]
        for event, label in (
            ("schedule", "Scheduled scouts"),
            ("repository_dispatch", "Recovery dispatches"),
        ):
            item = inspections.get(event) or {}
            rows.append(
                f"- {label}: **{'PASS' if item.get('verified') else 'FAIL'}** "
                f"({len(item.get('proofs') or [])}/{item.get('required', 0)} sampled)"
            )
            for proof in item.get("proofs") or []:
                rows.append(
                    f"  - Run {proof.get('run_id')}: {proof.get('status')}; "
                    f"artifact {proof.get('artifact_id', 'none')}"
                )
            for integrator in item.get("integrators") or []:
                rows.append(
                    f"  - Integrator {integrator.get('run_id')}: {integrator.get('status')}; "
                    f"proposal delivery {integrator.get('parent_conclusion')}; "
                    f"artifact {integrator.get('artifact_id', 'none')}"
                )
        rows += ["", "Sampled proof is not comprehensive coverage or a target integration.", ""]
    runtime = report.get("governed_runtime")
    if runtime:
        rows += [
            "## Adaptive-worker readiness (separate from healthy scouting)",
            "",
            f"Matched benchmark scored: **{runtime['scored_matched_tasks']}/{runtime['required_matched_tasks']}**",
            "Raw experiment results awaiting independent scoring: " +
                (", ".join(runtime['raw_result_arms_unscored']) or "none"),
            f"Readiness report: **{runtime['readiness_state']}**",
            f"Activation policy: **{runtime['adaptive_runtime_mode']}**",
            f"Current generated activations: **{runtime['current_generated_activations']}**",
            "Current runtime activation verified: **" +
                str(runtime['full_worker_runtime_verified']).lower() + "**",
            "Readiness snapshot consistent with scoreboard: **" +
                str(runtime['benchmark_snapshot_consistent']).lower() + "**",
            "ChatGPT automation enabled/failed status: NOT OBSERVABLE from GitHub alone.",
            "",
            "The operational percentage above measures scouting only, not full Hunter autonomy.",
            "Completion, revenue, trading performance and scientific novelty require separate evidence.",
            "",
        ]
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-json", default="hunter-fleet-health.json")
    ap.add_argument("--output-md", default="hunter-fleet-health.md")
    ap.add_argument("--inject-failure", action="store_true")
    args = ap.parse_args()
    runs = api(f"/repos/{REPO}/actions/workflows/public-repo-hunter.yml/runs?per_page=100")["workflow_runs"]
    prs = api(f"/repos/{REPO}/pulls?state=open&per_page=100")
    queues = {}
    for path in Path("intelligence/scout_queue").glob("HUNTER-*.json"):
        queues[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    digest = Path("automation/SCOUT_DIGEST.md").read_text(encoding="utf-8")
    observed_now = dt.datetime.now(dt.timezone.utc)
    inspections = inspect_recent_scout_delivery(runs, observed_now)
    report = evaluate(runs, queues, digest, observed_now, prs,
                      args.inject_failure, inspections=inspections)
    report["governed_runtime"] = governed_runtime_truth(Path.cwd())
    Path(args.output_json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    Path(args.output_md).write_text(render(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
