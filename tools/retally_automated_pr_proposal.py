#!/usr/bin/env python3
"""Prepare the validated handoff for one App-authored RETALLY evidence PR.

No direct push to main, no unreviewed financial claims and no privileged API
surface outside the exact repository. An external trusted workflow_dispatch
controller verifies pull_request CI and independently dispatches exact-head CI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from tools.retally_writer_proposal_policy import (
    ProposalHold, branch_for_run, verify_proposal,
)

REPO = "P00NSMASHER/github-value-hunt-ledger"
ALLOWED_EVENTS = frozenset({"schedule", "workflow_dispatch", "push",
                            "repository_dispatch"})


def verify_event_authority(event: str, base: str) -> None:
    """Keep recovery admission identical to the workflow's fail-closed route."""
    if event != "repository_dispatch":
        return
    if os.environ.get("GITHUB_ACTOR") != "portfolio-brain-v8-runtime[bot]":
        raise ProposalHold("Unauthorized recovery actor")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    try:
        payload = json.loads(Path(event_path or "").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ProposalHold("Recovery event evidence unavailable") from None
    client = payload.get("client_payload") if isinstance(payload, dict) else None
    worker = client.get("worker") if isinstance(client, dict) else None
    expected_main = client.get("expected_main") if isinstance(client, dict) else None
    if (not re.fullmatch(r"(?:HUNTER-(0[1-9]|1[0-4])|INTEGRATOR)", str(worker or "")) or
            expected_main != base or os.environ.get("GITHUB_SHA") != base):
        raise ProposalHold("Recovery event is not exact-main worker authority")


def merge_denial(stdout: str, stderr: str) -> str:
    # GitHub response bodies and CLI stderr may contain private values. Only
    # expose the numeric HTTP status and fixed descriptions of recognized errors.
    try:
        error = json.loads(stdout)
    except ValueError:
        error = {}
    status = re.search(r"\(HTTP ([45][0-9]{2})\)", stderr)
    message = str(error.get("message", "")).lower() if isinstance(error, dict) else ""
    reason = "unmet condition unknown"
    if "required status check" in message and "release-gate" in message:
        reason = "required release-gate was not accepted"
    elif "resource not accessible by integration" in message:
        reason = "GitHub denied this installation access"
    elif "head branch was modified" in message or "head sha" in message and "match" in message:
        reason = "PR head changed"
    elif "review" in message and ("required" in message or "approving" in message):
        reason = "required PR review is missing"
    return f"Protected PR merge denied (HTTP {status[1] if status else 'unknown'}): {reason}"


def gh(method: str, path: str, payload: dict | None = None):
    if not (path.startswith("repos/" + REPO + "/") and
            method in ("GET", "POST", "PUT")):
        raise ProposalHold("Unapproved repository API request")
    args = ["gh", "api", "--method", method, path]
    if payload is not None:
        args.extend(["--input", "-"])
    try:
        result = subprocess.run(
            args, input=json.dumps(payload) if payload is not None else None,
            capture_output=True, text=True, check=False, timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ProposalHold("GitHub API did not respond safely") from None
    # Never print API stderr: it may contain auth headers or sensitive request details.
    if result.returncode:
        if method == "PUT" and re.fullmatch(rf"repos/{re.escape(REPO)}/pulls/[1-9][0-9]*/merge", path):
            raise ProposalHold(merge_denial(result.stdout, result.stderr))
        raise ProposalHold("GitHub API denied proposed operation: "
                           + method + " in scoped repository")
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise ProposalHold("GitHub API response is not valid JSON") from None


def checked_proposal_state(lane: str, branch: str, base: str, head: str):
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ProposalHold("Wrong GitHub repository")
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event not in ALLOWED_EVENTS:
        raise ProposalHold("Unsupported automation trigger")
    verify_event_authority(str(event), base)
    if not os.environ.get("GH_TOKEN"):
        raise ProposalHold("GitHub Actions token not available")
    expected = branch_for_run(
        lane, os.environ.get("GITHUB_RUN_ID", ""),
        os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    )
    if branch != expected:
        raise ProposalHold("Proposal branch not bound to this exact workflow run")

    main = gh("GET", "repos/" + REPO + "/branches/main")
    if not isinstance(main, dict) or main.get("commit", {}).get("sha") != base:
        raise ProposalHold("Main changed before proposal: isolated branch retained")
    pr_commit = gh("GET", f"repos/{REPO}/git/commits/{head}")
    parents = pr_commit.get("parents") if isinstance(pr_commit, dict) else None
    if not isinstance(parents, list) or len(parents) != 1:
        raise ProposalHold("Generated commit has multiple/missing parents")
    first_parent = parents[0].get("sha")
    compare = gh("GET", f"repos/{REPO}/compare/{base}...{head}")
    if not isinstance(compare, dict) or compare.get("status") != "ahead":
        raise ProposalHold("Remote comparison is not a single forward-only proposal")
    if compare.get("ahead_by") != 1 or compare.get("behind_by") != 0:
        raise ProposalHold("Proposal unexpectedly contains additional commits or base drift")
    changed = compare.get("files")
    if not isinstance(changed, list):
        raise ProposalHold("No complete remote file population available")
    files = {item.get("filename"): item.get("status") for item in changed
             if isinstance(item, dict)}
    if len(files) != len(changed):
        raise ProposalHold("Remote comparison contains duplicate or malformed files")
    return verify_proposal(
        lane, branch, base, head, first_parent, files,
    )


def propose(lane: str, branch: str, base: str, head: str):
    verified = checked_proposal_state(lane, branch, base, head)
    fingerprint = os.environ.get("SCOUT_SEMANTIC_FINGERPRINT", "") if lane == "scout" else ""
    if lane == "scout" and re.fullmatch(r"[a-f0-9]{64}", fingerprint) is None:
        raise ProposalHold("Scout proposal lacks its validated semantic fingerprint")
    return {
        "version": 1, "lane": lane, "branch": branch, "base": base, "head": head,
        "file_count": len(verified.files), "scout_fingerprint": fingerprint,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--base-sha", required=True)
    ap.add_argument("--head-sha", required=True)
    args = ap.parse_args()
    result = propose(args.lane, args.branch, args.base_sha, args.head_sha)
    path = Path(os.environ["RUNNER_TEMP"]) / "retally-app-request.json"
    path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Validated {result['file_count']} files for App proposal {args.branch} at {args.head_sha}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProposalHold, OSError, KeyError, ValueError, TypeError) as exc:
        print("RETALLY PROPOSAL HOLD: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
