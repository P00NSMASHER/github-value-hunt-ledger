#!/usr/bin/env python3
"""Prove GitHub-native PR creation, explicit CI dispatch and SHA-guarded merge.

This is a one-time inert canary only. Never run on customer, source, or scheduled
writer branches. The sole permissible change is one synthetic Markdown receipt.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import quote

REPO = "P00NSMASHER/github-value-hunt-ledger"
OWNER = "P00NSMASHER"
WORKFLOW = "repository-release-gate.yml"
CANARY_BRANCH = re.compile(r"automation/retally-guard-canary-(20[0-9]{6})-([a-f0-9]{8})\Z")
REQUIRED_JOBS = frozenset({
    "ai-business-os", "freight", "recoveryworks", "technology-intelligence", "release-gate",
})
SENTINEL = "RETALLY GUARDED AUTO-MERGE CANARY - SYNTHETIC ONLY"


class Hold(RuntimeError):
    pass


def run(*args: str, input_text: str | None = None, cwd: Path | None = None) -> str:
    # Deliberately never include stdout/stderr in errors: they could contain a
    # redacted API response or authentication challenge.
    result = subprocess.run(
        list(args), input=input_text, text=True, capture_output=True,
        cwd=cwd, check=False, timeout=45,
    )
    if result.returncode:
        raise Hold("External command failed (" + args[0] + "; exit "
                   + str(result.returncode) + "). Canary remains unmerged.")
    return result.stdout.strip()


def api(method: str, endpoint: str, payload: dict | None = None):
    if not endpoint.startswith("repos/" + REPO + "/"):
        raise Hold("Refusing API outside exact permitted repository")
    args = ["gh", "api", "--method", method, endpoint,
            "-H", "Accept: application/vnd.github+json"]
    if payload is not None:
        args += ["--input", "-"]
    raw = run(*args, input_text=json.dumps(payload) if payload is not None else None)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        raise Hold("GitHub returned unparseable API response") from None


def assert_inert_change(branch: str, sha: str, repo: Path) -> str:
    found = CANARY_BRANCH.fullmatch(branch)
    if not found:
        raise Hold("Only a bounded synthetic canary branch is allowed")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Hold("Source SHA is not exact")
    rel = "automation/canary/guarded-" + found.group(1) + "-" + found.group(2) + ".md"
    parents = run("git", "rev-list", "--parents", "-n", "1", sha, cwd=repo).split()
    if len(parents) != 2 or parents[0] != sha:
        raise Hold("Canary must have exactly one parent")
    base = run("git", "rev-parse", "refs/remotes/origin/main", cwd=repo)
    if parents[1] != base:
        raise Hold("Main advanced or canary is not based on exact current main")
    diff = run("git", "diff", "--name-only", base, sha, cwd=repo).splitlines()
    if diff != [rel]:
        raise Hold("Canary attempted to change non-synthetic files")
    path = repo / rel
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 512:
        raise Hold("Synthetic canary file is missing, unsafe or oversized")
    if SENTINEL not in path.read_text(encoding="utf-8"):
        raise Hold("Synthetic canary marker absent")
    if run("git", "status", "--porcelain", cwd=repo):
        raise Hold("Canary checkout is dirty")
    return base


def valid_release_jobs(jobs: list[dict]) -> bool:
    if not isinstance(jobs, list):
        return False
    found = {job.get("name"): job.get("conclusion")
             for job in jobs if isinstance(job, dict)}
    return all(found.get(name) == "success" for name in REQUIRED_JOBS)


def matching_run(runs: list[dict], branch: str, sha: str, created_after: dt.datetime):
    for item in runs:
        if not isinstance(item, dict):
            continue
        if item.get("event") != "workflow_dispatch":
            continue
        if item.get("head_sha") != sha or item.get("head_branch") != branch:
            continue
        try:
            created = dt.datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if created >= created_after - dt.timedelta(seconds=5):
            return item
    return None


def main() -> int:
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise Hold("Wrong repository")
    if os.environ.get("GITHUB_EVENT_NAME") != "push":
        raise Hold("Canary only permits a trusted branch push")
    if os.environ.get("GITHUB_ACTOR") != OWNER:
        raise Hold("Synthetic canary push must originate from repository owner")
    if not os.environ.get("GH_TOKEN"):
        raise Hold("Ephemeral GitHub Actions token unavailable")
    branch = os.environ.get("GITHUB_REF_NAME", "")
    sha = os.environ.get("GITHUB_SHA", "")
    checkout = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    run("git", "fetch", "--no-tags", "origin", "main", cwd=checkout)
    base_sha = assert_inert_change(branch, sha, checkout)

    current_main = api("GET", "repos/" + REPO + "/branches/main")
    if not isinstance(current_main, dict) or current_main.get("commit", {}).get("sha") != base_sha:
        raise Hold("Remote main changed since canary branch creation")

    open_prs = api("GET", "repos/" + REPO + "/pulls?state=open&head=" +
                   quote(OWNER + ":" + branch, safe=""))
    if not isinstance(open_prs, list):
        raise Hold("Unable to read existing canary proposals")
    if len(open_prs) > 1:
        raise Hold("Ambiguous duplicate canary pull requests")
    if open_prs:
        number = open_prs[0]["number"]
    else:
        try:
            reply = api("POST", "repos/" + REPO + "/pulls", {
                "title": "Synthetic guarded GitHub merge canary (" + branch + ")",
                "head": branch, "base": "main",
                "body": "One inert Markdown file only. Explicit release-gate dispatch "
                        "and exact-source merge; no customer or production impact.",
            })
        except Hold:
            raise Hold("GitHub Actions PR creation was unavailable. "
                       "The canary branch remains isolated; check Actions PR permissions.") from None
        if not isinstance(reply, dict) or type(reply.get("number")) is not int:
            raise Hold("GitHub PR creation returned no unique number")
        number = reply["number"]
    proposal = api("GET", f"repos/{REPO}/pulls/{number}")
    if (not isinstance(proposal, dict)
        or proposal.get("head", {}).get("sha") != sha
        or proposal.get("base", {}).get("ref") != "main"
        or proposal.get("head", {}).get("repo", {}).get("full_name") != REPO):
        raise Hold("PR head or base did not match frozen canary")
    print("Canary PR #", number, "created on exact SHA", sha[:10], flush=True)

    dispatched = dt.datetime.now(dt.timezone.utc)
    api("POST", f"repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
        {"ref": branch})
    print("Dispatched full release-gate workflow for exact canary ref", flush=True)
    run_id = None
    for _ in range(105):  # 105 x 15s = 26m15s, bounded under 32m job.
        time.sleep(15)
        listing = api("GET", f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs"
                      "?event=workflow_dispatch&branch=" + quote(branch, safe="")
                      + "&per_page=25")
        found = matching_run((listing or {}).get("workflow_runs", []),
                             branch, sha, dispatched)
        if found is None:
            continue
        run_id = found["id"]
        details = api("GET", f"repos/{REPO}/actions/runs/{run_id}")
        if details.get("head_sha") != sha or details.get("event") != "workflow_dispatch":
            raise Hold("Dispatched run provenance changed")
        if details.get("status") != "completed":
            continue
        if details.get("conclusion") != "success":
            raise Hold("Actual release gate did not pass, run " + str(run_id))
        jobs = api("GET", f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")
        if not valid_release_jobs((jobs or {}).get("jobs", [])):
            raise Hold("Release gate is missing one of the five passing jobs")
        break
    else:
        raise Hold("Timed out waiting for exact-SHA release-gate evidence")

    latest_main = api("GET", "repos/" + REPO + "/branches/main")
    latest_pr = api("GET", f"repos/{REPO}/pulls/{number}")
    if (latest_main.get("commit", {}).get("sha") != base_sha
        or latest_pr.get("head", {}).get("sha") != sha
        or latest_pr.get("base", {}).get("sha") != base_sha
        or latest_pr.get("state") != "open"):
        raise Hold("Main or PR moved during validation: leave canary unmerged")

    response = api("PUT", f"repos/{REPO}/pulls/{number}/merge",
                   {"sha": sha, "merge_method": "merge"})
    if not isinstance(response, dict) or response.get("merged") is not True:
        raise Hold("GitHub did not verify the guarded PR merge")
    print(json.dumps({
        "synthetic_only": True, "approved_tests": sorted(REQUIRED_JOBS),
        "release_gate_run": run_id, "canary_pr": number,
        "merged": True, "customer_release": "HOLD",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Hold, OSError, KeyError, TypeError, ValueError) as exc:
        print("GUARDED CANARY HOLD: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
