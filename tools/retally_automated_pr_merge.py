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
import re
from pathlib import Path
import sys
import time
from urllib.parse import quote

from tools.retally_automated_pr_proposal import REPO, gh
from tools.retally_writer_proposal_policy import (
    COMMIT_SHA, PROPOSAL_BRANCH, ProposalHold, allowed_path, generated_manifest,
    verify_proposal,
)

GATE_WORKFLOW = "repository-release-gate.yml"
REQUIRED_JOBS = frozenset({
    "ai-business-os", "freight", "recoveryworks",
    "technology-intelligence", "release-gate",
})


def guarded_target(lane: str, number: int, head_sha: str, base_sha: str,
                   *, require_current_main: bool = True):
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
    if require_current_main and _current_main_sha() != base_sha:
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


def dispatch_and_verify(branch: str, sha: str, *, deadline: float | None = None) -> int:
    if deadline is not None and time.monotonic() + 15 >= deadline:
        raise ProposalHold("No remaining runtime budget to dispatch proof CI")
    since = dt.datetime.now(dt.timezone.utc)
    gh("POST", f"repos/{REPO}/actions/workflows/{GATE_WORKFLOW}/dispatches",
       {"ref": branch})
    print("Exact-head CI workflow dispatch accepted", flush=True)
    for attempt in range(95):
        if deadline is not None and time.monotonic() + 15 >= deadline:
            raise ProposalHold("Bounded total proof-CI runtime exhausted")
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



MAX_RECONCILE_COMMITS = 12
MAX_RECONCILE_FILES = 200
MAX_TOTAL_RECONCILE_SECONDS = 480
MAX_TOTAL_PROOF_SECONDS = 1650  # 27.5 minutes within a 30-minute job
PROOF_BRANCH = re.compile(r"automation/retally-proof-([1-9][0-9]{3,15})-([1-9][0-9]{0,3})")


def _current_main_sha() -> str:
    response = gh("GET", "repos/" + REPO + "/branches/main")
    sha = (response.get("commit", {}).get("sha")
           if isinstance(response, dict) else None)
    if not isinstance(sha, str) or COMMIT_SHA.fullmatch(sha) is None:
        raise ProposalHold("Unable to verify the exact current main commit")
    return sha


def _unrelated_main_changes(lane: str, original_base: str,
                            latest_main: str, changed_files: tuple[str, ...]) -> None:
    """Permit one proof build only for small, independent new main changes."""
    if original_base == latest_main:
        raise ProposalHold("No main advancement requiring a proof replay")
    result = gh("GET", f"repos/{REPO}/compare/{original_base}...{latest_main}")
    if (not isinstance(result, dict) or result.get("status") != "ahead"
        or result.get("behind_by") != 0
        or not isinstance(result.get("ahead_by"), int)
        or not 1 <= result["ahead_by"] <= MAX_RECONCILE_COMMITS
        or not isinstance(result.get("files"), list)
        or not 1 <= len(result["files"]) < MAX_RECONCILE_FILES):
        raise ProposalHold("Cannot prove a bounded and linear current-main advancement")
    seen = set()
    ti_files = generated_manifest() if lane == "technology" else frozenset()
    for item in result["files"]:
        path = item.get("filename") if isinstance(item, dict) else None
        if not isinstance(path, str) or path in seen:
            raise ProposalHold("Main advancement has ambiguous changed paths")
        seen.add(path)
        if (path in changed_files or path.startswith((".github/", "tools/", "tests/"))
            or (lane == "technology" and path.startswith("intelligence/"))
            or allowed_path(lane, path, ti_paths=ti_files)):
            raise ProposalHold("Current main changed a proposed output or writer dependency")
    # All other new-main files are added to the *tested* merge tree; do not
    # assume that separately passing old CI is sufficient.


def _proof_branch_from_run() -> str:
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    branch = "automation/retally-proof-" + run_id + "-" + attempt
    if PROOF_BRANCH.fullmatch(branch) is None:
        raise ProposalHold("Cannot construct one trusted, run-specific proof branch")
    return branch


def _prove_and_merge_updated_main(
    lane: str, number: int, head_sha: str, base_sha: str,
    approved_files: tuple[str, ...], *, start_time: float,
) -> dict[str, object]:
    """Never rebase/force a source branch; test exact combined tree on isolated ref."""
    if time.monotonic() - start_time >= MAX_TOTAL_RECONCILE_SECONDS:
        raise ProposalHold("Proof retry budget exceeded after source CI")
    latest_main = _current_main_sha()
    _unrelated_main_changes(lane, base_sha, latest_main, approved_files)
    proof_branch = _proof_branch_from_run()
    ref = "refs/heads/" + proof_branch
    # Creating this unique branch cannot write main or overwrite a prior
    # attestation. A second invocation with the same run ID must fail closed.
    ref_result = gh("POST", f"repos/{REPO}/git/refs",
                    {"ref": ref, "sha": latest_main})
    if (not isinstance(ref_result, dict)
        or ref_result.get("ref") != ref
        or ref_result.get("object", {}).get("sha") != latest_main):
        raise ProposalHold("GitHub did not bind unique proof branch to frozen main")
    if _current_main_sha() != latest_main:
        raise ProposalHold("Main advanced during proof branch preparation")

    proof = gh("POST", f"repos/{REPO}/merges", {
        "base": proof_branch, "head": head_sha,
        "commit_message": "TEST_ONLY RETALLY scoped evidence merge proof; "
                          "not customer or production release",
    })
    proof_sha = proof.get("sha") if isinstance(proof, dict) else None
    if not isinstance(proof_sha, str) or COMMIT_SHA.fullmatch(proof_sha) is None:
        raise ProposalHold("Provider did not produce an immutable proof merge")
    proof_commit = gh("GET", f"repos/{REPO}/git/commits/{proof_sha}")
    parents = proof_commit.get("parents") if isinstance(proof_commit, dict) else None
    proof_tree = proof_commit.get("tree", {}).get("sha") if isinstance(proof_commit, dict) else None
    if (not isinstance(parents, list) or len(parents) != 2
        or [x.get("sha") for x in parents] != [latest_main, head_sha]
        or not isinstance(proof_tree, str)
        or COMMIT_SHA.fullmatch(proof_tree) is None):
        raise ProposalHold("Proof commit has wrong parents or unverifiable tree")
    changes = gh("GET", f"repos/{REPO}/compare/{latest_main}...{proof_sha}")
    items = changes.get("files") if isinstance(changes, dict) else None
    if (not isinstance(changes, dict) or changes.get("status") != "ahead"
        or changes.get("ahead_by") != 1 or changes.get("behind_by") != 0
        or not isinstance(items, list) or len(items) != len(approved_files)
        or {x.get("filename") for x in items if isinstance(x, dict)}
             != set(approved_files)
        or any(not isinstance(x, dict) or x.get("status") not in ("added", "modified")
               for x in items)):
        raise ProposalHold("Isolated proof introduced files outside original scoped PR")

    # Crucial: a newly dispatched five-lane gate runs on the actual merged
    # tree, not the outdated bot proposal, and has a fresh exact SHA.
    run_id = dispatch_and_verify(
        proof_branch, proof_sha, deadline=start_time + MAX_TOTAL_PROOF_SECONDS)
    guarded_target(lane, number, head_sha, base_sha,
                   require_current_main=False)
    if _current_main_sha() != latest_main:
        raise ProposalHold("Main advanced during merged-tree proof CI")
    response = gh("PUT", f"repos/{REPO}/pulls/{number}/merge", {
        "sha": head_sha, "merge_method": "merge",
        "commit_title": f"CI-proofed generated {lane} evidence refresh",
        "commit_message": "Merged tree proven with five fresh release-gate jobs. "
                          "No human code reviewer, no customer or production release.",
    })
    merge_sha = response.get("sha") if isinstance(response, dict) else None
    if (not isinstance(response, dict) or response.get("merged") is not True
        or not isinstance(merge_sha, str)
        or COMMIT_SHA.fullmatch(merge_sha) is None):
        raise ProposalHold("GitHub did not acknowledge the reconciled merge")
    merged_commit = gh("GET", f"repos/{REPO}/git/commits/{merge_sha}")
    merged_tree = (merged_commit.get("tree", {}).get("sha")
                   if isinstance(merged_commit, dict) else None)
    if merged_tree != proof_tree:
        raise ProposalHold("CRITICAL: resulting main tree differs from CI-proven tree")
    return {
        "result": "MERGED_WITH_RECONCILED_TREE_CI", "lane": lane,
        "pr_number": number, "head_sha": head_sha, "merged_sha": merge_sha,
        "proof_sha": proof_sha, "proof_branch": proof_branch,
        "tested_main_sha": latest_main, "ci_run_id": run_id,
        "files": len(approved_files), "customer_release": "HOLD",
    }


def integrate(lane: str, number: int, head_sha: str, base_sha: str):
    started = time.monotonic()
    # First authenticate the frozen bot PR and exact source scope, even when
    # another publisher has advanced main before this run starts.
    proposal, approved = guarded_target(
        lane, number, head_sha, base_sha, require_current_main=False)
    if _current_main_sha() != base_sha:
        return _prove_and_merge_updated_main(
            lane, number, head_sha, base_sha, approved.files,
            start_time=started)
    run_id = dispatch_and_verify(proposal["head"]["ref"], head_sha)
    # Re-evaluate every mutable remote authority after a long-running CI.
    if _current_main_sha() != base_sha:
        return _prove_and_merge_updated_main(
            lane, number, head_sha, base_sha, approved.files,
            start_time=started)
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
