#!/usr/bin/env python3
"""Build a compact, machine-readable snapshot of Portfolio Brain repositories.

Uses only the Python standard library. The GitHub token is optional for public
repositories but strongly recommended to avoid unauthenticated rate limits.

This tool is intentionally descriptive: it reads repository metadata and trees
but never modifies a downstream repository.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = "1.0.0"
USER_AGENT = "portfolio-brain-snapshot/1.0"
DEPENDENCY_BASENAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "poetry.lock",
    "pdm.lock",
    "pipfile",
    "pipfile.lock",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "gemfile",
    "gemfile.lock",
    "composer.json",
    "composer.lock",
}
DEPENDENCY_PATTERNS = (
    re.compile(r"(^|/)requirements[^/]*(\.txt|\.lock)$", re.I),
    re.compile(r"(^|/)environment[^/]*\.ya?ml$", re.I),
)
TEST_PATTERNS = (
    re.compile(r"(^|/)(tests?|specs?)(/|$)", re.I),
    re.compile(r"(^|/)test_[^/]+\.py$", re.I),
    re.compile(r"(^|/)[^/]+_(test|tests)\.py$", re.I),
    re.compile(r"(^|/)[^/]+\.(test|spec)\.[^.]+$", re.I),
)

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


def _is_dependency_manifest(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].lower()
    if base in DEPENDENCY_BASENAMES:
        return True
    return any(pattern.search(path) for pattern in DEPENDENCY_PATTERNS)


def _is_test_path(path: str) -> bool:
    return any(pattern.search(path) for pattern in TEST_PATTERNS)


def classify_paths(paths: list[str]) -> dict[str, list[str]]:
    ordered = sorted(set(paths))
    return {
        "workflow_paths": [p for p in ordered if p.startswith(".github/workflows/") and p.lower().endswith((".yml", ".yaml"))],
        "test_paths": [p for p in ordered if _is_test_path(p)],
        "dependency_manifest_paths": [p for p in ordered if _is_dependency_manifest(p)],
        "readme_paths": [p for p in ordered if p.rsplit("/", 1)[-1].lower() in {"readme", "readme.md", "readme.txt", "readme.rst"}],
    }


def summarize_tree(tree_payload: dict[str, Any]) -> dict[str, Any]:
    entries = tree_payload.get("tree") or []
    blobs = [item for item in entries if item.get("type") == "blob" and item.get("path")]
    dirs = [item for item in entries if item.get("type") == "tree" and item.get("path")]
    paths = [item["path"] for item in blobs]
    top_counts: Counter[str] = Counter()
    total_bytes = 0
    for item in blobs:
        path = item["path"]
        top = path.split("/", 1)[0] if "/" in path else "(root)"
        top_counts[top] += 1
        total_bytes += int(item.get("size") or 0)
    classes = classify_paths(paths)
    return {
        "tree_truncated": bool(tree_payload.get("truncated")),
        "file_count": len(blobs),
        "directory_count": len(dirs),
        "known_blob_bytes": total_bytes,
        "top_level_file_counts": dict(sorted(top_counts.items())),
        **classes,
    }


def snapshot_repository(
    entry: dict[str, Any],
    *,
    api_base: str,
    token: str | None,
    get_json: JsonGetter = _api_get,
) -> dict[str, Any]:
    full_name = entry["full_name"]
    quoted_repo = "/".join(urllib.parse.quote(part, safe="") for part in full_name.split("/", 1))
    meta = get_json(f"{api_base}/repos/{quoted_repo}", token)
    default_branch = meta["default_branch"]
    quoted_branch = urllib.parse.quote(default_branch, safe="")
    branch = get_json(f"{api_base}/repos/{quoted_repo}/branches/{quoted_branch}", token)
    head_sha = branch["commit"]["sha"]
    tree = get_json(f"{api_base}/repos/{quoted_repo}/git/trees/{head_sha}?recursive=1", token)
    summary = summarize_tree(tree)
    return {
        "repo_id": entry.get("repo_id"),
        "project_ids": sorted(entry.get("project_ids") or []),
        "full_name": full_name,
        "default_branch": default_branch,
        "head_sha": head_sha,
        "visibility": meta.get("visibility"),
        "archived": bool(meta.get("archived")),
        "language": meta.get("language"),
        "github_size_kb": meta.get("size"),
        "updated_at": meta.get("updated_at"),
        "pushed_at": meta.get("pushed_at"),
        **summary,
    }


def build_snapshot(
    config: dict[str, Any],
    *,
    api_base: str = "https://api.github.com",
    token: str | None = None,
    observed_at: str | None = None,
    get_json: JsonGetter = _api_get,
) -> dict[str, Any]:
    if observed_at is None:
        observed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    repositories = []
    errors = []
    for entry in sorted(config.get("repositories") or [], key=lambda item: item["full_name"].lower()):
        try:
            repositories.append(
                snapshot_repository(entry, api_base=api_base.rstrip("/"), token=token, get_json=get_json)
            )
        except Exception as exc:  # preserve an explicit gap rather than silently dropping a repository
            errors.append({
                "repo_id": entry.get("repo_id"),
                "full_name": entry.get("full_name"),
                "error": str(exc),
            })
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "repository_count_requested": len(config.get("repositories") or []),
        "repository_count_snapshotted": len(repositories),
        "repository_count_failed": len(errors),
        "repositories": repositories,
        "errors": errors,
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    rows = []
    for item in snapshot["repositories"]:
        rows.append(
            f"| {item.get('repo_id') or '—'} | `{item['full_name']}` | "
            f"`{item['head_sha']}` | {item['file_count']} | "
            f"{len(item['workflow_paths'])} | {len(item['test_paths'])} | "
            f"{len(item['dependency_manifest_paths'])} |"
        )
    error_block = ""
    if snapshot.get("errors"):
        error_lines = "\n".join(
            f"- `{item.get('full_name')}`: {item.get('error')}" for item in snapshot["errors"]
        )
        error_block = f"\n## Snapshot gaps\n\n{error_lines}\n"
    return (
        "# Portfolio Repository Snapshot\n\n"
        f"Observed: `{snapshot['observed_at']}`\n\n"
        f"Captured **{snapshot['repository_count_snapshotted']} / "
        f"{snapshot['repository_count_requested']}** configured repositories.\n\n"
        "| ID | Repository | HEAD | Files | Workflows | Test paths | Dependency manifests |\n"
        "|---|---|---|---:|---:|---:|---:|\n"
        + "\n".join(rows)
        + "\n"
        + error_block
        + "\nThis snapshot is descriptive evidence for architecture work. It does not modify downstream repositories.\n"
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="portfolio_prework/snapshot_repos.json")
    parser.add_argument("--json-out", default="portfolio_prework/repository_snapshot.json")
    parser.add_argument("--md-out", default="portfolio_prework/REPOSITORY_SNAPSHOT.md")
    parser.add_argument("--api-base", default="https://api.github.com")
    parser.add_argument("--observed-at", default=None)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any configured repository cannot be snapshotted.")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    snapshot = build_snapshot(
        config,
        api_base=args.api_base,
        token=os.environ.get("GITHUB_TOKEN"),
        observed_at=args.observed_at,
    )
    _write_text(Path(args.json_out), json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    _write_text(Path(args.md_out), render_markdown(snapshot))
    print(
        f"snapshot: {snapshot['repository_count_snapshotted']}/"
        f"{snapshot['repository_count_requested']} repositories; "
        f"errors={snapshot['repository_count_failed']}"
    )
    if args.strict and snapshot["errors"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
