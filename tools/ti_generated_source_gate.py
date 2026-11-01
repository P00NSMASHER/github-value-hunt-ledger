#!/usr/bin/env python3
"""Skip redundant technology regeneration only for proven derived-only main pushes.

This classifier neither modifies Git nor changes worker schedules. Unknown git
history or a malformed generated manifest conservatively REQUIRES regeneration.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ".github/technology-intelligence-generated-files.txt"
_SHA = re.compile(r"[0-9a-f]{40}\Z")


def generated_paths(root: Path = ROOT) -> frozenset[str]:
    values: set[str] = set()
    for line in (root / MANIFEST).read_text(encoding="utf-8").splitlines():
        path = line.strip()
        if not path or path.startswith("#"):
            continue
        parts = Path(path).parts
        if (path.startswith("/") or not parts or ".." in parts or
                "." in parts or "\\" in path or path in values):
            raise ValueError("invalid generated-file allowlist")
        values.add(path)
    if not values:
        raise ValueError("empty generated-file allowlist")
    return frozenset(values)


def changed_paths(before: str, after: str, root: Path = ROOT) -> tuple[str, ...]:
    if _SHA.fullmatch(before or "") is None or _SHA.fullmatch(after or "") is None:
        raise ValueError("invalid commit identities")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", before, after],
        cwd=root, capture_output=True, timeout=30, check=False,
    )
    if result.returncode:
        raise ValueError("unable to verify exact main push diff")
    raw = [part for part in result.stdout.split(b"\0") if part]
    names = tuple(part.decode("utf-8", "strict") for part in raw)
    if not names or len(names) != len(set(names)):
        raise ValueError("empty or ambiguous exact main push diff")
    return names


def requires_refresh(paths: tuple[str, ...], derived: frozenset[str]) -> bool:
    """Any non-generated input change warrants a normal source rebuild."""
    if not paths or not derived:
        return True
    return any(name not in derived for name in paths)


def decision(before: str, after: str, root: Path = ROOT) -> tuple[bool, str]:
    try:
        output = changed_paths(before, after, root)
        derived = generated_paths(root)
        refresh = requires_refresh(output, derived)
        return refresh, "source_changed" if refresh else "derived_only"
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        # Failure to prove generated-only changes must never skip a real update.
        return True, "unverified_delta_rebuild"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    options = parser.parse_args(argv)
    refresh, reason = decision(options.before, options.after)
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        raise SystemExit("GITHUB_OUTPUT required; cannot issue untracked decision")
    with open(output, "a", encoding="utf-8") as stream:
        stream.write("refresh=" + ("true" if refresh else "false") + "\n")
        stream.write("reason=" + reason + "\n")
    print("Technology regeneration: " + ("REQUIRED" if refresh else "SKIPPED") +
          " (" + reason + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
