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


def evaluate(runs: list[dict], queues: dict[str, dict], digest: str,
             now: dt.datetime, open_prs: list[dict], inject_failure=False) -> dict:
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
        "full_worker_runtime_verified": (
            mode == "measurement_canary"
            and active and activations > 0
            and readiness.get("state") == "AWAITING_EXPLICIT_USER_APPROVAL"
            and readiness_count == scored_count
        ),
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
    report = evaluate(runs, queues, digest, dt.datetime.now(dt.timezone.utc), prs,
                      args.inject_failure)
    report["governed_runtime"] = governed_runtime_truth(Path.cwd())
    Path(args.output_json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    Path(args.output_md).write_text(render(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
