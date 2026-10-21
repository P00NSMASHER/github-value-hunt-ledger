#!/usr/bin/env python3
"""Freeze the changed operations of an authorized GitHub push payload.

The legacy Integrator and Catalog helpers replayed *every* instruction from
their old payload on each new payload push. Missing historical markers could
silently append old, now-stale advice to current source files. This module
extracts only new instructions from the exact triggering commit vs its parent.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from tools.retally_writer_proposal_policy import allowed_path

COMMIT = re.compile(r"[a-f0-9]{40}\Z")
OPERATION = re.compile(r"^=== (APPEND|REPLACE|SUBSTITUTE) ([^\r\n]+?) ===$", re.M)
PATHS = {
    "catalog": ".github/catalog_append_payload.json",
    "integrator": ".github/integrator_sync_payload.md",
}
MAX_BYTES = 1_000_000
MAX_INCREMENT = 100_000


class Refused(ValueError):
    """No target mutation may occur after an ambiguous payload update."""


def ensure(ok: bool, why: str) -> None:
    if not ok:
        raise Refused(why)


def _object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        ensure(key not in result, "Duplicate JSON instruction key")
        result[key] = value
    return result


def _read_catalog(raw: str) -> dict:
    try:
        parsed = json.loads(raw, object_pairs_hook=_object_without_duplicate_keys)
    except (TypeError, ValueError) as exc:
        raise Refused("Cannot parse unambiguous Catalog payload") from None
    ensure(isinstance(parsed, dict) and set(parsed) == {"marker", "append"},
           "Catalog payload schema changed unexpectedly")
    marker, append = parsed["marker"], parsed["append"]
    ensure(isinstance(marker, str) and 0 < len(marker) <= 500 and
           "\n" not in marker and "\r" not in marker,
           "Catalog marker is absent or unsafe")
    ensure(isinstance(append, dict), "Catalog append operations are not an object")
    for path, body in append.items():
        ensure(isinstance(body, str) and bool(body.strip()) and len(body) <= MAX_INCREMENT
               and allowed_path("catalog", path, ti_paths=frozenset()),
               "Catalog payload contains an invalid or executable target")
    return parsed


def catalog_delta(previous: str, current: str) -> tuple[str, int]:
    old, new = _read_catalog(previous), _read_catalog(current)
    before, after = old["append"], new["append"]
    ensure(bool(before) and len(after) > len(before) and len(after) <= 128,
           "Catalog has no newly appended, distinct operation")
    ensure(all(path in after and after[path] == body for path, body in before.items()),
           "Existing Catalog instruction was changed or deleted")
    added = {path: after[path] for path in after if path not in before}
    ensure(0 < len(added) <= 16, "Catalog increment is too large")
    result = {"marker": new["marker"], "append": added}
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n", len(added)


def _integrator_header(raw: str) -> str:
    ensure(isinstance(raw, str) and raw.startswith("MARKER: "),
           "Integrator payload has no first-line marker")
    first = raw.splitlines()[0]
    marker = first[len("MARKER: "):].strip()
    ensure(bool(marker) and len(marker) <= 500 and "\r" not in marker,
           "Integrator marker is invalid")
    return first


def integrator_delta(previous: str, current: str) -> tuple[str, int]:
    header = _integrator_header(previous)
    ensure(_integrator_header(current) == header and
           current.startswith(previous) and len(current) > len(previous),
           "Integrator payload is not an exact append-only extension")
    suffix = current[len(previous):]
    ensure(len(suffix.encode("utf-8")) <= MAX_INCREMENT,
           "Integrator newly appended section is too large")
    # Appended instructions must begin at a section boundary, not silently
    # change the body of the preceding historical instruction.
    ensure(suffix.startswith("\n") and not suffix.startswith("\n\n\n"),
           "Integrator increment does not begin after a clean line break")
    new_operations = suffix.lstrip("\r\n")
    match = list(OPERATION.finditer(new_operations))
    ensure(match and match[0].start() == 0 and len(match) <= 16,
           "Integrator increment lacks exact new operations")
    for item in match:
        path = item.group(2)
        ensure(allowed_path("integrator", path, ti_paths=frozenset()),
               "Integrator increment target is outside approved evidence files")
    for index, item in enumerate(match):
        body_start = item.end()
        body_end = match[index + 1].start() if index + 1 < len(match) else len(new_operations)
        ensure(bool(new_operations[body_start:body_end].strip()),
               "Integrator new operation is empty")
    return header + "\n" + new_operations.rstrip() + "\n", len(match)


def _git_source(repo: Path, sha: str, kind: str) -> str:
    ensure(COMMIT.fullmatch(sha or "") is not None and sha != "0" * 40,
           "Source event has no exact nonzero Git SHA")
    try:
        proc = subprocess.run(
            ["git", "show", sha + ":" + PATHS[kind]], cwd=repo, check=False,
            capture_output=True, timeout=20,
        )
        ensure(proc.returncode == 0 and 0 < len(proc.stdout) <= MAX_BYTES,
               "A frozen GitHub payload revision cannot be read")
        return proc.stdout.decode("utf-8", errors="strict")
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        raise Refused("GitHub source payload read or UTF-8 validation failed") from None


def extract_event_delta(kind: str, before: str, after: str,
                        frozen_input: Path, *, repo: Path) -> tuple[str, int]:
    ensure(kind in PATHS, "Unexpected payload type")
    ensure(before != after, "GitHub event has no source revision change")
    ensure(frozen_input.is_file() and not frozen_input.is_symlink(),
           "Frozen triggered payload missing or symlinked")
    try:
        frozen = frozen_input.read_bytes()
        ensure(0 < len(frozen) <= MAX_BYTES, "Frozen payload exceeds safe budget")
        frozen_text = frozen.decode("utf-8", errors="strict")
    except (OSError, UnicodeError):
        raise Refused("Frozen triggered payload is not valid UTF-8") from None
    previous = _git_source(repo, before, kind)
    current = _git_source(repo, after, kind)
    ensure(current == frozen_text,
           "Frozen event payload differs from its exact triggered commit")
    if kind == "catalog":
        return catalog_delta(previous, current)
    return integrator_delta(previous, current)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=sorted(PATHS), required=True)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    delta, count = extract_event_delta(
        args.kind, args.before, args.after, args.input, repo=repo,
    )
    ensure(not args.output.exists() and not args.output.is_symlink(),
           "Incremental output already exists or is a symlink")
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(delta)
        handle.flush()
        os.fsync(handle.fileno())
    print("RETALLY_INCREMENTAL_PAYLOAD_ACCEPTED kind=" + args.kind +
          " operations=" + str(count))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refused, OSError) as exc:
        print("RETALLY_INCREMENTAL_PAYLOAD_HOLD: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
