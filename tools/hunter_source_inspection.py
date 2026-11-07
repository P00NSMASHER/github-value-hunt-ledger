#!/usr/bin/env python3
"""Bounded, read-only source review for existing Hunter scout queues.

This stage does not claim/activate the paused V16 runtime and never executes
third-party code or claims integration, revenue, novelty or measured savings.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

from tools.public_repo_scout import validate_manifest

HEX = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SOURCE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java")
SOURCE_DIR = {"src", "lib", "app", "cmd", "internal", "packages"}
TEST_DIR = {"test", "tests", "__tests__", "spec", "specs"}
MAX_BLOB = 65536


class InspectionError(ValueError):
    pass


class GitHubReadOnly:
    def __init__(self, token: str):
        if not token:
            raise InspectionError("GitHub read-only token required")
        self.token = token

    def get(self, path: str) -> dict:
        if not path.startswith("/repos/") or "://" in path:
            raise InspectionError("Only GitHub repository API paths are permitted")
        request = urllib.request.Request(
            "https://api.github.com" + path,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "hunter-source-review/1",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read(8_000_001)
        if len(payload) > 8_000_000:
            raise InspectionError("Source response exceeds size budget")
        record = json.loads(payload)
        if not isinstance(record, dict):
            raise InspectionError("GitHub response must be an object")
        return record


def eligible_path(path: object, test: bool) -> bool:
    if not isinstance(path, str) or not path.lower().endswith(SOURCE_EXT):
        return False
    parts = path.lower().split("/")
    if (any(p in ("", ".", "..", "vendor", "node_modules", "dist", "build")
            for p in parts)):
        return False
    filename = parts[-1]
    is_test = (bool(set(parts[:-1]) & TEST_DIR) or
               filename.startswith("test_") or ".test." in filename or
               ".spec." in filename or filename.endswith("_test.go"))
    if test:
        return is_test
    return bool(set(parts[:-1]) & SOURCE_DIR) and not is_test


def verify_blob(api, repo: str, entry: dict) -> dict:
    size, sha = entry.get("size"), entry.get("sha")
    if (not isinstance(size, int) or not 0 < size <= MAX_BLOB or
        not isinstance(sha, str) or not HEX.fullmatch(sha)):
        raise InspectionError("Blob size/hash is outside source-review budget")
    obj = api.get("/repos/" + repo + "/git/blobs/" + sha)
    if obj.get("encoding") != "base64":
        raise InspectionError("Unsupported source blob encoding")
    raw = base64.b64decode(obj.get("content", ""), validate=False)
    if len(raw) != size or obj.get("sha") != sha:
        raise InspectionError("Source blob size/revision mismatch")
    identity = hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw).hexdigest()
    if identity != sha:
        raise InspectionError("Git object integrity verification failed")
    return {"path": entry["path"], "git_blob_sha": sha,
            "content_sha256": hashlib.sha256(raw).hexdigest(), "bytes": size}


def inspect_candidate(candidate: dict, api) -> dict:
    repo, revision = candidate.get("repository"), candidate.get("exact_revision")
    if (not isinstance(repo, str) or not REPO.fullmatch(repo) or
        not isinstance(revision, str) or not HEX.fullmatch(revision)):
        raise InspectionError("Invalid repository or immutable source commit")
    if candidate.get("status") != "PRE_VERIFICATION_CANDIDATE" or candidate.get("archived"):
        raise InspectionError("Candidate is not eligible for source inspection")
    license_id = candidate.get("published_license_spdx")
    if not isinstance(license_id, str) or license_id in ("", "UNKNOWN", "NOASSERTION"):
        raise InspectionError("Published license metadata unavailable; rights remain unknown")
    commit = api.get("/repos/" + repo + "/git/commits/" + revision)
    if commit.get("sha") != revision:
        raise InspectionError("Exact source commit mismatch")
    tree_sha = (commit.get("tree") or {}).get("sha")
    if not isinstance(tree_sha, str) or not HEX.fullmatch(tree_sha):
        raise InspectionError("Exact source tree missing")
    tree = api.get("/repos/" + repo + "/git/trees/" + tree_sha + "?recursive=1")
    if tree.get("sha") != tree_sha or tree.get("truncated"):
        raise InspectionError("Source tree did not resolve completely")
    entries = tree.get("tree")
    if not isinstance(entries, list) or len(entries) > 20000:
        raise InspectionError("Source inventory exceeds bounded review")
    blobs = [e for e in entries if isinstance(e, dict) and e.get("type") == "blob"
             and isinstance(e.get("size"), int) and 0 < e["size"] <= MAX_BLOB]
    source = next((e for e in blobs if eligible_path(e.get("path"), False)), None)
    test = next((e for e in blobs if eligible_path(e.get("path"), True)), None)
    if source is None or test is None:
        raise InspectionError("No inspectable source and test pair")
    return {
        "state": "SOURCE_INSPECTED_NOT_TESTED",
        "source_repository": repo,
        "source_revision": revision,
        "tree_sha": tree_sha,
        "published_license_metadata": license_id,
        "rights_review": "REQUIRED",
        "source_file": verify_blob(api, repo, source),
        "test_file": verify_blob(api, repo, test),
        "source_code_executed": False,
        "integration": "UNKNOWN",
        "measured_result": "UNKNOWN",
    }


def inspect_worker(worker: dict, queue: dict, api, max_attempts: int = 3) -> dict:
    result = {"worker_id": worker["id"], "project": worker["project"],
              "state": "NOT_INSPECTED", "attempts": [],
              "accepted_deliveries": 0}
    for key, value in {
        "worker_id": worker["id"],
        "project": worker["project"],
        "target_repository": worker["target_repository"],
        "mission": worker["mission"],
        "evidence_gate": worker.get("evidence_gate"),
    }.items():
        if queue.get(key) != value:
            result["state"] = "INVALID_QUEUE_BINDING"
            return result
    candidates = queue.get("candidates")
    if not isinstance(candidates, list) or queue.get("candidate_count") != len(candidates):
        result["state"] = "INVALID_QUEUE_STRUCTURE"
        return result
    if not candidates:
        result["state"] = "NO_CANDIDATES"
        return result
    for candidate in sorted(candidates, key=lambda c: -int(c.get("triage_score") or 0))[:max_attempts]:
        attempt = {"repository": candidate.get("repository"),
                   "source_revision": candidate.get("exact_revision")}
        try:
            result["evidence"] = inspect_candidate(candidate, api)
            result["state"] = "SOURCE_INSPECTED_NOT_TESTED"
            result["attempts"].append({**attempt, "status": "INSPECTED"})
            return result
        except (InspectionError, OSError, ValueError, KeyError) as exc:
            result["attempts"].append({**attempt, "status": "UNVERIFIED",
                                       "reason": str(exc)[:200]})
    result["state"] = "NO_SOURCE_VERIFIED"
    return result


def run(manifest: dict, root: Path, worker_id: str, api) -> dict:
    scope = validate_manifest(manifest)
    workers = [w for w in manifest["workers"]
               if worker_id == "ALL" or w["id"] == worker_id]
    if not workers:
        raise InspectionError("Invalid worker scope")
    results = []
    for worker in workers:
        path = root / (worker["id"] + ".json")
        if not path.is_file():
            results.append({"worker_id": worker["id"], "state": "MISSING_QUEUE"})
            continue
        queue_bytes = path.read_bytes()
        queue = json.loads(queue_bytes.decode("utf-8"))
        if queue.get("scope_version") != scope:
            results.append({"worker_id": worker["id"], "state": "STALE_QUEUE_SCOPE"})
            continue
        inspected = inspect_worker(worker, queue, api)
        inspected["queue_sha256"] = hashlib.sha256(queue_bytes).hexdigest()
        inspected["queue_generated_at"] = queue.get("generated_at")
        inspected["queue_candidate_count"] = queue.get("candidate_count")
        results.append(inspected)
    return {
        "schema_version": 1,
        "authority": "READ_ONLY_INSPECTION_NOT_V16_CLAIM",
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "workflow_sha": os.environ.get("GITHUB_SHA"),
        "scope_version": scope,
        "workers": results,
        "completed_work": 0,
        "verified_real_world_outcomes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="automation/hunter_schedule.json")
    parser.add_argument("--queue-root", default="intelligence/scout_queue")
    parser.add_argument("--worker", required=True)
    parser.add_argument("--output", default="hunter-source-inspection.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = run(manifest, Path(args.queue_root), args.worker,
                 GitHubReadOnly(os.getenv("GITHUB_TOKEN", "")))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"review_states": {w["worker_id"]: w["state"]
                                        for w in result["workers"]},
                      "completed_work": 0}, sort_keys=True))
    return 2 if any(w["state"] in ("MISSING_QUEUE", "STALE_QUEUE_SCOPE",
                                  "INVALID_QUEUE_BINDING", "INVALID_QUEUE_STRUCTURE")
                    for w in result["workers"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
