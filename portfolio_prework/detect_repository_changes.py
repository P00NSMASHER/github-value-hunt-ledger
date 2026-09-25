#!/usr/bin/env python3
"""Detect repository changes relative to a prior portfolio snapshot.

The detector is deliberately cheap:
1. read the prior snapshot;
2. fetch only each repository's current default-branch HEAD;
3. stop immediately for unchanged repositories;
4. call GitHub's compare endpoint only for repositories whose HEAD changed.

It never modifies downstream repositories.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = "1.0.0"
USER_AGENT = "portfolio-brain-delta/1.0"
JsonGetter = Callable[[str, str | None], Any]


def _api_get(url: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {body[:500]}") from exc


def _quoted_repo(full_name: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="") for part in full_name.split("/", 1))


def _current_head(
    full_name: str,
    default_branch: str,
    *,
    api_base: str,
    token: str | None,
    get_json: JsonGetter,
) -> str:
    repo = _quoted_repo(full_name)
    branch = urllib.parse.quote(default_branch, safe="")
    payload = get_json(f"{api_base}/repos/{repo}/branches/{branch}", token)
    return payload["commit"]["sha"]


def _compare(
    full_name: str,
    base_sha: str,
    head_sha: str,
    *,
    api_base: str,
    token: str | None,
    get_json: JsonGetter,
) -> dict[str, Any]:
    repo = _quoted_repo(full_name)
    compare_ref = f"{urllib.parse.quote(base_sha, safe='')}...{urllib.parse.quote(head_sha, safe='')}"
    payload = get_json(f"{api_base}/repos/{repo}/compare/{compare_ref}", token)
    files = []
    for item in payload.get("files") or []:
        files.append({
            "path": item.get("filename"),
            "status": item.get("status"),
            "additions": item.get("additions"),
            "deletions": item.get("deletions"),
            "changes": item.get("changes"),
            "previous_path": item.get("previous_filename"),
        })
    return {
        "compare_status": payload.get("status"),
        "ahead_by": payload.get("ahead_by"),
        "behind_by": payload.get("behind_by"),
        "total_commits": payload.get("total_commits"),
        "changed_file_count": len(files),
        "changed_files": files,
    }


def detect_changes(
    snapshot: dict[str, Any],
    *,
    api_base: str = "https://api.github.com",
    token: str | None = None,
    observed_at: str | None = None,
    include_file_deltas: bool = True,
    get_json: JsonGetter = _api_get,
) -> dict[str, Any]:
    if observed_at is None:
        observed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    results = []
    errors = []
    for prior in sorted(snapshot.get("repositories") or [], key=lambda item: item["full_name"].lower()):
        full_name = prior["full_name"]
        default_branch = prior["default_branch"]
        baseline_sha = prior["head_sha"]
        try:
            current_sha = _current_head(
                full_name,
                default_branch,
                api_base=api_base.rstrip("/"),
                token=token,
                get_json=get_json,
            )
            if current_sha == baseline_sha:
                results.append({
                    "repo_id": prior.get("repo_id"),
                    "full_name": full_name,
                    "default_branch": default_branch,
                    "baseline_head_sha": baseline_sha,
                    "current_head_sha": current_sha,
                    "status": "UNCHANGED",
                    "requires_deep_inspection": False,
                    "compare": None,
                })
                continue

            comparison = None
            if include_file_deltas:
                comparison = _compare(
                    full_name,
                    baseline_sha,
                    current_sha,
                    api_base=api_base.rstrip("/"),
                    token=token,
                    get_json=get_json,
                )
            results.append({
                "repo_id": prior.get("repo_id"),
                "full_name": full_name,
                "default_branch": default_branch,
                "baseline_head_sha": baseline_sha,
                "current_head_sha": current_sha,
                "status": "CHANGED",
                "requires_deep_inspection": True,
                "compare": comparison,
            })
        except Exception as exc:
            errors.append({
                "repo_id": prior.get("repo_id"),
                "full_name": full_name,
                "error": str(exc),
            })

    unchanged = sum(1 for item in results if item["status"] == "UNCHANGED")
    changed = sum(1 for item in results if item["status"] == "CHANGED")
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline_observed_at": snapshot.get("observed_at"),
        "observed_at": observed_at,
        "repository_count": len(snapshot.get("repositories") or []),
        "unchanged_count": unchanged,
        "changed_count": changed,
        "error_count": len(errors),
        "repositories": results,
        "errors": errors,
    }


def render_markdown(delta: dict[str, Any]) -> str:
    rows = []
    for item in delta["repositories"]:
        compare = item.get("compare") or {}
        file_count = compare.get("changed_file_count")
        rows.append(
            f"| {item.get('repo_id') or '—'} | \`{item['full_name']}\` | "
            f"{item['status']} | {file_count if file_count is not None else '—'} | "
            f"{'YES' if item['requires_deep_inspection'] else 'NO'} |"
        )

    changed_sections = []
    for item in delta["repositories"]:
        if item["status"] != "CHANGED":
            continue
        compare = item.get("compare") or {}
        files = compare.get("changed_files") or []
        listing = "\n".join(
            f"- \`{f['path']}\` ({f.get('status') or 'unknown'}, +{f.get('additions') or 0}/-{f.get('deletions') or 0})"
            for f in files
        ) or "- File-level comparison was not requested."
        changed_sections.append(
            f"## {item['full_name']}\n\n"
            f"Baseline: \`{item['baseline_head_sha']}\`\n\n"
            f"Current: \`{item['current_head_sha']}\`\n\n"
            f"{listing}"
        )

    errors = ""
    if delta.get("errors"):
        errors = "\n## Errors\n\n" + "\n".join(
            f"- \`{item['full_name']}\`: {item['error']}" for item in delta["errors"]
        )

    detail = "\n\n".join(changed_sections)
    if detail:
        detail = "\n\n# Changed repository details\n\n" + detail

    return (
        "# Portfolio Repository Delta\n\n"
        f"Baseline snapshot: \`{delta.get('baseline_observed_at')}\`\n\n"
        f"Observed: \`{delta['observed_at']}\`\n\n"
        f"- Unchanged: **{delta['unchanged_count']}**\n"
        f"- Changed: **{delta['changed_count']}**\n"
        f"- Errors: **{delta['error_count']}**\n\n"
        "| ID | Repository | Status | Changed files | Deep inspection? |\n"
        "|---|---|---|---:|---|\n"
        + "\n".join(rows)
        + detail
        + errors
        + "\n\nUnchanged repositories should not be re-read during normal Portfolio Brain reconnaissance.\n"
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="portfolio_prework/repository_snapshot.json")
    parser.add_argument("--json-out", default="portfolio_prework/repository_delta.json")
    parser.add_argument("--md-out", default="portfolio_prework/REPOSITORY_DELTA.md")
    parser.add_argument("--api-base", default="https://api.github.com")
    parser.add_argument("--no-file-deltas", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    delta = detect_changes(
        snapshot,
        api_base=args.api_base,
        token=os.environ.get("GITHUB_TOKEN"),
        include_file_deltas=not args.no_file_deltas,
    )
    _write_text(Path(args.json_out), json.dumps(delta, indent=2, sort_keys=True) + "\n")
    _write_text(Path(args.md_out), render_markdown(delta))
    print(
        f"delta: unchanged={delta['unchanged_count']} "
        f"changed={delta['changed_count']} errors={delta['error_count']}"
    )
    if args.strict and delta["errors"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
