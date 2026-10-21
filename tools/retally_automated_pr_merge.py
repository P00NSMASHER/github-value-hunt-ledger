#!/usr/bin/env python3
"""Guarded bot PR integration after real branch-specific GitHub CI success.

This runs ONLY in a trusted workflow_dispatch job on main. It does not merge
general user PRs, allow arbitrary files, bypass rulesets, use human approvals,
or perform an external/customer operation.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote

from tools.retally_automated_pr_proposal import REPO, gh
from tools.retally_writer_proposal_policy import (
    COMMIT_SHA, PROPOSAL_BRANCH, ProposalHold, verify_proposal,
)

GATE_WORKFLOW = "repository-release-gate.yml"
REQUIRED_JOBS = frozenset({
    "ai-business-os", "freight", "recoveryworks",
    "technology-intelligence", "release-gate",
})


def guarded_target(lane: str, number: int, head_sha: str, base_sha: str):
    if type(number) is not int or number < 1:
        raise ProposalHold("Missing numeric proposal PR")
    if (COMMIT_SHA.fullmatch(head_sha or "") is None or
            COMMIT_SHA.fullmatch(base_sha or "") is None):
        raise ProposalHold("Both base and head must be exact SHA-1")
    pr = gh("GET", f"repos/{REPO}/pulls/{number}")
    if (not isinstance(pr, dict) or pr.get("state") != "open"
        or pr.get("draft") is True or pr.get("merged") is True):
        raise ProposalHold("Target is not an open, non-draft proposal PR")
    ref = pr.get("head", {}).get("ref")
    m = PROPOSAL_BRANCH.fullmatch(ref or "")
    if m is None or m.group(1) != lane:
        raise ProposalHold("Target head is not an approved generated writer branch")
    if (pr.get("head", {}).get("sha") != head_sha
        or pr.get("head", {}).get("repo", {}).get("full_name") != REPO
        or pr.get("base", {}).get("ref") != "main"
        or pr.get("base", {}).get("sha") != base_sha):
        raise ProposalHold("Proposal head, repository, or target main changed")
    owner = pr.get("user") or {}
    if owner.get("login") != "github-actions[bot]":
        raise ProposalHold("Only GitHub Actions-authored proposal PRs qualify")
    main = gh("GET", "repos/" + REPO + "/branches/main")
    if main.get("commit", {}).get("sha") != base_sha:
        raise ProposalHold("Main advanced: leave proposal open for reconciliation")
    commit = gh("GET", f"repos/{REPO}/git/commits/{head_sha}")
    parents = commit.get("parents") if isinstance(commit, dict) else None
    if not isinstance(parents, list) or len(parents) != 1:
        raise ProposalHold("Generated commit is not a single-parent snapshot")
    first_parent = parents[0].get("sha")
    changes = gh("GET", f"repos/{REPO}/compare/{base_sha}...{head_sha}")
    if (not isinstance(changes, dict) or changes.get("status") != "ahead"
        or changes.get("ahead_by") != 1 or changes.get("behind_by") != 0
        or not isinstance(changes.get("files"), list)):
        raise ProposalHold("Generated commit is not exactly one forward-only change")
    files = changes["files"]
    if len(files) >= 300 or len(files) != pr.get("changed_files"):
        raise ProposalHold("Changed file count is incomplete or too large")
    metadata = {entry.get("filename"): entry.get("status") for entry in files
                if isinstance(entry, dict)}
    if len(metadata) != len(files):
        raise ProposalHold("Unsafe or duplicate file population")
    approved = verify_proposal(lane, ref, base_sha, head_sha, first_parent, metadata)
    return pr, approved


def completed_release_jobs(jobs: list[dict]) -> bool:
    if not isinstance(jobs, list):
        return False
    found = {x.get("name"): x.get("conclusion") for x in jobs
             if isinstance(x, dict)}
    return all(found.get(x) == "success" for x in REQUIRED_JOBS)


def match_fresh_run(runs: list[dict], branch: str, sha: str, started: dt.datetime):
    if not isinstance(runs, list):
        return None
    for r in runs:
        if not isinstance(r, dict):
            continue
        if r.get("event") != "workflow_dispatch":
            continue
        if r.get("head_sha") != sha or r.get("head_branch") != branch:
            continue
        try:
            created = dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, AttributeError, ValueError):
            continue
        if created >= started - dt.timedelta(seconds=5):
            return r
    return None


def dispatch_and_verify(branch: str, sha: str) -> int:
    since = dt.datetime.now(dt.timezone.utc)
    gh("POST", f"repos/{REPO}/actions/workflows/{GATE_WORKFLOW}/dispatches",
       {"ref": branch})
    print("Exact-head CI workflow dispatch accepted", flush=True)
    for attempt in range(95):
        time.sleep(15)
        listing = gh("GET", f"repos/{REPO}/actions/workflows/{GATE_WORKFLOW}/runs"
                     "?event=workflow_dispatch&branch=" + quote(branch, safe="")
                     + "&per_page=25")
        item = match_fresh_run((listing or {}).get("workflow_runs", []),
                               branch, sha, since)
        if not item:
            continue
        run_id = item["id"]
        state = gh("GET", f"repos/{REPO}/actions/runs/{run_id}")
        if state.get("head_sha") != sha or state.get("event") != "workflow_dispatch":
            raise ProposalHold("Dispatched CI run lost its exact-source identity")
        if state.get("status") != "completed":
            continue
        if state.get("conclusion") != "success":
            raise ProposalHold("Generated PR release gate failed; run " + str(run_id))
        jobs = gh("GET", f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")
        if not completed_release_jobs((jobs or {}).get("jobs", [])):
            raise ProposalHold("One of the five actual release jobs did not pass")
        return run_id
    raise ProposalHold("CI did not produce exact-source acceptance in bounded window")


def integrate(lane: str, number: int, head_sha: str, base_sha: str):
    proposal, approved = guarded_target(lane, number, head_sha, base_sha)
    run_id = dispatch_and_verify(proposal["head"]["ref"], head_sha)
    # Re-evaluate every mutable remote authority after a long-running CI.
    guarded_target(lane, number, head_sha, base_sha)
    response = gh("PUT", f"repos/{REPO}/pulls/{number}/merge", {
        "sha": head_sha,
        "merge_method": "merge",
        "commit_title": f"Automated source-verified {lane} evidence refresh",
        "commit_message": "Owner-authorized, scoped evidence-only PR. "
                          "The five exact-head repository release jobs passed. "
                          "Financial/customer release evidence remains HOLD.",
    })
    if not isinstance(response, dict) or response.get("merged") is not True:
        raise ProposalHold("GitHub PR merge was not positively acknowledged")
    result_sha = response.get("sha")
    if COMMIT_SHA.fullmatch(result_sha or "") is None:
        raise ProposalHold("Merge returned no immutable resulting commit")
    return {
        "result": "MERGED_WITH_ACTUAL_CI", "lane": lane,
        "pr_number": number, "head_sha": head_sha,
        "merged_sha": result_sha, "ci_run_id": run_id,
        "files": len(approved.files), "customer_release": "HOLD",
    }


def main() -> int:
    if (os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("GITHUB_ACTOR") != "github-actions[bot]"
        or not os.environ.get("GH_TOKEN")):
        raise ProposalHold("Only bot-dispatched trusted main workflow may merge")
    result = integrate(
        os.environ.get("INPUT_LANE", ""),
        int(os.environ.get("INPUT_PR_NUMBER", "0")),
        os.environ.get("INPUT_HEAD_SHA", ""),
        os.environ.get("INPUT_BASE_SHA", ""),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProposalHold, ValueError, KeyError, TypeError, OSError) as exc:
        print("RETALLY GUARDED MERGE HOLD: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
