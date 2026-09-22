#!/usr/bin/env python3
"""Persist generated intelligence safely under concurrent main-branch writers."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / ".github" / "technology-intelligence-generated-files.txt"
)


def run(
    repo: Path,
    args: Sequence[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        cwd=repo,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if check and result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def git(
    repo: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return run(repo, ["git", *args], check=check)


def read_manifest(path: Path) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if value.startswith("/") or ".." in Path(value).parts:
            raise ValueError(f"unsafe generated path: {value}")
        if value in seen:
            raise ValueError(f"duplicate generated path: {value}")
        seen.add(value)
        rows.append(value)
    if not rows:
        raise ValueError("generated artifact manifest is empty")
    return rows


def path_is_tracked(repo: Path, path: str) -> bool:
    return (
        git(
            repo,
            "ls-files",
            "--error-unmatch",
            "--",
            path,
            check=False,
        ).returncode
        == 0
    )


def stage_generated(repo: Path, paths: Sequence[str]) -> None:
    for path in paths:
        if (repo / path).exists() or path_is_tracked(repo, path):
            git(repo, "add", "-A", "--", path)


def default_rebuild(repo: Path) -> None:
    run(
        repo,
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_ti_*.py",
        ],
    )
    run(repo, [sys.executable, "tools/ti_build.py"])
    git(repo, "diff", "--check")


def is_non_fast_forward_failure(result: subprocess.CompletedProcess[str]) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    return (
        "fetch first" in text
        or "non-fast-forward" in text
        or ("rejected" in text and "head -> main" in text)
    )


def persist_generated(
    repo: Path,
    generated_paths: Sequence[str],
    *,
    max_attempts: int = 5,
    rebuild_fn: Callable[[Path], None] = default_rebuild,
    before_push: Callable[[int], None] | None = None,
    clean_untracked_on_rebuild: bool = False,
) -> dict[str, object]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    git(repo, "config", "user.name", "github-actions[bot]")
    git(
        repo,
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )

    rebuilt_attempts = 0
    for attempt in range(1, max_attempts + 1):
        git(repo, "fetch", "origin", "main")
        local_head = git(repo, "rev-parse", "HEAD").stdout.strip()
        remote_head = git(repo, "rev-parse", "origin/main").stdout.strip()

        if local_head != remote_head:
            git(repo, "reset", "--hard", "origin/main")
            if clean_untracked_on_rebuild:
                git(repo, "clean", "-fd")
            rebuild_fn(repo)
            rebuilt_attempts += 1

        git(repo, "diff", "--check")
        stage_generated(repo, generated_paths)

        if git(repo, "diff", "--cached", "--quiet", check=False).returncode == 0:
            return {
                "status": "clean",
                "attempts": attempt,
                "rebuilt_attempts": rebuilt_attempts,
                "head_sha": git(repo, "rev-parse", "HEAD").stdout.strip(),
            }

        git(
            repo,
            "commit",
            "-m",
            "chore: refresh technology intelligence [skip ci]",
        )

        if before_push is not None:
            before_push(attempt)

        pushed = git(
            repo,
            "push",
            "origin",
            "HEAD:main",
            check=False,
        )
        if pushed.returncode == 0:
            return {
                "status": "pushed",
                "attempts": attempt,
                "rebuilt_attempts": rebuilt_attempts,
                "head_sha": git(repo, "rev-parse", "HEAD").stdout.strip(),
            }

        if not is_non_fast_forward_failure(pushed):
            raise RuntimeError(
                "generated intelligence push failed for a non-retryable reason:\n"
                + pushed.stdout
                + pushed.stderr
            )

        if attempt == max_attempts:
            raise RuntimeError(
                f"generated intelligence push lost {max_attempts} "
                "consecutive non-fast-forward races"
            )

    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--clean-untracked-on-rebuild",
        action="store_true",
        help=(
            "After a lost push race, remove untracked files/directories "
            "before rebuilding from fresh origin/main. Intended for "
            "ephemeral CI workspaces."
        ),
    )
    args = parser.parse_args()

    paths = read_manifest(args.manifest)
    result = persist_generated(
        ROOT,
        paths,
        max_attempts=args.max_attempts,
        clean_untracked_on_rebuild=args.clean_untracked_on_rebuild,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
