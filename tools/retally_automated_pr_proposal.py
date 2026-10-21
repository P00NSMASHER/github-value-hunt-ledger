#!/usr/bin/env python3
"""Publish one generated RETALLY evidence snapshot as a guarded GitHub PR.

No direct push to main, no unreviewed financial claims and no privileged API
surface outside the exact repository. An external trusted workflow_dispatch
controller (not a GITHUB_TOKEN-created PR event) runs real CI before merge.
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
CONTROLLER = "retally-generated-pr-merge.yml"
ALLOWED_EVENTS = frozenset({"schedule", "workflow_dispatch", "push"})


def gh(method: str, path: str, payload: dict | None = None):
    if not (path.startswith("repos/" + REPO + "/") and
            method in ("GET", "POST")):
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
    if os.environ.get("GITHUB_EVENT_NAME") not in ALLOWED_EVENTS:
        raise ProposalHold("Unsupported automation trigger")
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
    requests = gh("GET", "repos/" + REPO
                  + "/pulls?state=open&head=P00NSMASHER%3A"
                  + branch.replace("/", "%2F") + "&per_page=5")
    if not isinstance(requests, list) or len(requests) > 1:
        raise ProposalHold("Cannot uniquely identify an existing generated PR")
    if requests:
        number = requests[0]["number"]
        result = requests[0]
    else:
        try:
            result = gh("POST", "repos/" + REPO + "/pulls", {
                "head": branch, "base": "main",
                "title": "Automated " + lane + " evidence refresh (GitHub run "
                         + os.environ["GITHUB_RUN_ID"] + ")",
                "body": "A source-scoped generated proposal only. Automatic integration "
                        "requires independently executed exact-SHA repository release "
                        "CI via an explicit workflow dispatch. No independent human code "
                        "review needed; no customer financial/source authority is implied.",
                "draft": False,
            })
        except ProposalHold:
            raise ProposalHold("GitHub token could not open a PR; preserve the "
                               "isolated evidence branch and check repository "
                               "Actions PR permissions") from None
        if not isinstance(result, dict):
            raise ProposalHold("Created PR did not return a structured receipt")
        number = result.get("number")
    if type(number) is not int or number <= 0:
        raise ProposalHold("PR identification is missing")
    actual = gh("GET", f"repos/{REPO}/pulls/{number}")
    if (not isinstance(actual, dict) or actual.get("state") != "open"
        or actual.get("head", {}).get("sha") != head
        or actual.get("head", {}).get("repo", {}).get("full_name") != REPO
        or actual.get("base", {}).get("sha") != base
        or actual.get("base", {}).get("ref") != "main"):
        raise ProposalHold("Generated PR head/base changed before dispatch")

    # GITHUB_TOKEN-created PRs do NOT trigger normal pull_request CI. Sending
    # a trusted workflow_dispatch is an essential step, not optional fallback.
    gh("POST", f"repos/{REPO}/actions/workflows/{CONTROLLER}/dispatches", {
        "ref": "main",
        "inputs": {
            "pr_number": str(number), "lane": lane,
            "head_sha": head, "base_sha": base,
        },
    })
    return {
        "proposal_pr_number": number, "lane": lane,
        "base_sha": base, "head_sha": head,
        "changed_files": len(verified.files),
        "merge_status": "PENDING_GUARDED_CI",
        "customer_release": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--base-sha", required=True)
    ap.add_argument("--head-sha", required=True)
    args = ap.parse_args()
    result = propose(args.lane, args.branch, args.base_sha, args.head_sha)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProposalHold, OSError, KeyError, ValueError, TypeError) as exc:
        print("RETALLY PROPOSAL HOLD: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
