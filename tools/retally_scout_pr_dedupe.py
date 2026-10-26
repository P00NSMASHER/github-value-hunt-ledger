#!/usr/bin/env python3
"""Fail-closed semantic deduplication for pending Scout evidence PRs.

This tool never merges, closes, or edits a PR. It runs before a generated commit:
the same semantic candidate snapshot must have at most one open proposal.
Runtime diagnostics remain in Actions logs, not in the evidence identity.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "P00NSMASHER/github-value-hunt-ledger"
MARKER = re.compile(r"<!-- scout-semantic-sha256:([a-f0-9]{64}) -->")
SCOUT_PATH = re.compile(r"intelligence/scout_queue/HUNTER-[0-9]{2}\.json\Z")
TOP_RUNTIME = frozenset({"generated_at", "api_metrics", "search_diagnostics"})
CANDIDATE_RUNTIME = frozenset({"pushed_at", "size_kb", "stars", "forks"})


def evidence_value(path: str, content: str):
    """Canonical *material* evidence, not observed-at or API-cost telemetry."""
    if path == "automation/SCOUT_DIGEST.md":
        lines = [line for line in content.splitlines()
                 if not line.startswith("Generated: ")]
        return "\n".join(lines).rstrip() + "\n"
    if not SCOUT_PATH.fullmatch(path):
        raise ValueError(f"File is outside the Scout evidence scope: {path}")
    record = json.loads(content)
    if not isinstance(record, dict):
        raise ValueError("Scout queue must be a JSON object")
    evidence = {k: v for k, v in record.items() if k not in TOP_RUNTIME}
    candidates = evidence.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Scout candidates must be a list")
    stable = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Invalid Scout candidate")
        if not candidate.get("repository") or not candidate.get("exact_revision"):
            raise ValueError("Scout candidate lacks immutable revision identity")
        stable.append({k: v for k, v in candidate.items()
                       if k not in CANDIDATE_RUNTIME})
    evidence["candidates"] = stable
    return evidence


def semantic_fingerprint(contents: dict[str, str]) -> str:
    if not contents:
        raise ValueError("Cannot fingerprint an empty Scout proposal")
    canonical = {path: evidence_value(path, contents[path])
                 for path in sorted(contents)}
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def staged_contents() -> dict[str, str]:
    files = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        check=True, capture_output=True,
    ).stdout.split(b"\x00")
    paths = [entry.decode("utf-8") for entry in files if entry]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate staged paths")
    contents = {}
    for path in paths:
        if path != "automation/SCOUT_DIGEST.md" and not SCOUT_PATH.fullmatch(path):
            raise ValueError("Unexpected staged Scout file")
        contents[path] = subprocess.run(
            ["git", "show", ":" + path], check=True,
            capture_output=True, text=True, encoding="utf-8",
        ).stdout
    return contents


def open_proposals(token: str):
    """Read all pages; an API failure must never masquerade as no duplicates."""
    if not token:
        raise ValueError("GitHub token required to check open Scout proposals")
    for page in range(1, 21):
        query = urllib.parse.urlencode(
            {"state": "open", "per_page": 100, "page": page})
        url = f"https://api.github.com/repos/{REPO}/pulls?{query}"
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "retally-scout-evidence-dedupe/1",
        })
        with urllib.request.urlopen(request, timeout=30) as reply:
            proposals = json.load(reply)
        if not isinstance(proposals, list):
            raise ValueError("Incomplete GitHub PR enumeration")
        for proposal in proposals:
            yield proposal
        if len(proposals) < 100:
            return
    raise ValueError("Open PR list exceeds the bounded enumeration limit")


def matching_open_proposal(fingerprint: str, proposals) -> int | None:
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise ValueError("Malformed open PR entry")
        head, base = proposal.get("head") or {}, proposal.get("base") or {}
        if (proposal.get("state") != "open"
                or base.get("ref") != "main"
                or (head.get("repo") or {}).get("full_name") != REPO
                or not re.fullmatch(r"automation/retally-scout-[0-9]+-[0-9]+",
                                    str(head.get("ref", "")))
                or not str(proposal.get("title") or "").startswith(
                    "Automated scout evidence refresh ")):
            continue
        marker = MARKER.search(proposal.get("body") or "")
        if marker and marker.group(1) == fingerprint:
            number = proposal.get("number")
            if type(number) is not int or number <= 0:
                raise ValueError("Matching open PR has invalid identity")
            return number
    return None


def main() -> int:
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("Unexpected repository for Scout deduplication")
    data = staged_contents()
    if not data:
        raise ValueError("No staged Scout evidence")
    fingerprint = semantic_fingerprint(data)
    duplicate = matching_open_proposal(
        fingerprint, open_proposals(os.environ.get("GITHUB_TOKEN") or ""))
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        raise ValueError("GitHub Actions output path required")
    with Path(output).open("a", encoding="utf-8") as sink:
        sink.write(f"semantic_fingerprint={fingerprint}\n")
        sink.write(f"proposal_duplicate={'true' if duplicate else 'false'}\n")
        if duplicate:
            sink.write(f"duplicate_pr={duplicate}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as sink:
            sink.write(f"\nScout semantic fingerprint: {fingerprint}\n")
            if duplicate:
                sink.write(f"Suppressed repeat of pending PR #{duplicate}.\n")
    print(f"scout fingerprint={fingerprint}; "
          + (f"existing open PR #{duplicate}, no proposal needed"
             if duplicate else "new material evidence proposal"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError,
            urllib.error.URLError) as exc:
        print(f"SCOUT DEDUPE HOLD: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2)
