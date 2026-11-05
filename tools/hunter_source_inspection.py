#!/usr/bin/env python3
"""Read-only execution lane for public-source Hunter evidence; never a claim or deployment."""
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

SCOPE = "active-projects-2026-11-v2"
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[a-f0-9]{40}$")
CODE_EXT = (".py", ".rs", ".go", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
AVOID = {"node_modules", "vendor", "dist", "build", ".git", ".next", "fixtures", "generated"}
NOT_LICENSED = {"", "UNKNOWN", "NOASSERTION", "NONE"}
MAX_FILES = 12000
MAX_BLOB = 32000

class SourceError(ValueError):
    pass

class GitHubRead:
    def __init__(self, token: str = ""):
        self.token = token

    def get(self, route: str) -> dict:
        if not route.startswith("/repos/") or "://" in route or "\\" in route:
            raise SourceError("GitHub route rejected")
        headers = {"Accept": "application/vnd.github+json",
                   "User-Agent": "retally-hunter-source-inspection/1",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request("https://api.github.com" + route, headers=headers)
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read(12_000_001)
        if len(payload) > 12_000_000:
            raise SourceError("GitHub response exceeds inspection budget")
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise SourceError("GitHub response is not an object")
        return result

def roster(manifest: dict) -> list[dict]:
    workers = manifest.get("workers")
    ids = [f"HUNTER-{i:02d}" for i in range(1, 15)]
    if (manifest.get("scope_version") != SCOPE or
            not isinstance(workers, list) or
            [w.get("id") for w in workers] != ids):
        raise SourceError("exact 14-worker active scope required")
    return workers

def load_queue(worker: dict, root: Path) -> dict:
    p = root / (worker["id"] + ".json")
    q = json.loads(p.read_text(encoding="utf-8"))
    for key, expected in (("worker_id", worker["id"]),
                          ("scope_version", SCOPE),
                          ("project", worker["project"]),
                          ("target_repository", worker["target_repository"]),
                          ("mission", worker["mission"])):
        if q.get(key) != expected:
            raise SourceError(f"{worker['id']}: queue {key} conflicts with manifest")
    if q.get("evidence_gate") != worker.get("evidence_gate"):
        raise SourceError("queue evidence gate differs from current assignment")
    if not isinstance(q.get("candidates"), list) or q.get("candidate_count") != len(q["candidates"]):
        raise SourceError("queue candidate count or format invalid")
    return q

def choose(manifest: dict, root: Path, requested: str, seed: int) -> tuple[dict, dict]:
    workers = roster(manifest)
    if requested != "AUTO":
        selected = next((w for w in workers if w["id"] == requested), None)
        if selected is None:
            raise SourceError("unrecognized worker")
        return selected, load_queue(selected, root)
    for offset in range(len(workers)):
        worker = workers[(seed + offset) % len(workers)]
        q = load_queue(worker, root)
        if any(isinstance(c, dict) and c.get("status") == "PRE_VERIFICATION_CANDIDATE"
               for c in q["candidates"]):
            return worker, q
    return workers[seed % len(workers)], load_queue(workers[seed % len(workers)], root)

def candidates(queue: dict) -> list[dict]:
    valid = []
    for c in queue["candidates"]:
        if not isinstance(c, dict) or c.get("status") != "PRE_VERIFICATION_CANDIDATE":
            continue
        repo, sha = str(c.get("repository") or ""), str(c.get("exact_revision") or "")
        if not REPO.fullmatch(repo) or not SHA.fullmatch(sha):
            continue
        if c.get("risk_flags") or c.get("archived"):
            continue
        if str(c.get("published_license_spdx") or "").upper() in NOT_LICENSED:
            continue
        valid.append(c)
    return sorted(valid, key=lambda c: (-int(c.get("triage_score") or 0), c["repository"]))[:3]

def source_paths(tree: dict) -> tuple[str | None, str | None, str | None, bool]:
    entries = tree.get("tree")
    if not isinstance(entries, list) or len(entries) > MAX_FILES:
        raise SourceError("source tree unavailable or exceeds entry budget")
    safe = []
    for item in entries:
        path = str(item.get("path") or "")
        parts = path.lower().split("/")
        size = int(item.get("size") or 0)
        if (item.get("type") != "blob" or not SHA.fullmatch(str(item.get("sha") or ""))
                or any(p in AVOID for p in parts) or size < 50 or size > MAX_BLOB
                or not path.endswith(CODE_EXT) or path.lower().endswith(".min.js")):
            continue
        safe.append((path, item["sha"]))
    safe.sort()
    def is_test(path: str) -> bool:
        name = path.lower().split("/")[-1]
        return ("test" in path.lower().split("/")[:-1] or
                "tests" in path.lower().split("/")[:-1] or
                "__tests__" in path.lower().split("/")[:-1] or
                name.startswith("test_") or ".test." in name or ".spec." in name)
    tests = [v for v in safe if is_test(v[0])]
    impl = [v for v in safe if not is_test(v[0])]
    if not impl or not tests:
        return None, None, None, bool(tree.get("truncated"))
    impl.sort(key=lambda v: (not any(x in v[0].lower().split("/") for x in ("src", "lib", "crates", "app", "pkg")), len(v[0]), v[0]))
    license_entry = next((v for v in entries if v.get("type") == "blob" and
                          str(v.get("path") or "").upper() in
                          ("LICENSE", "LICENSE.MD", "LICENSE.TXT", "COPYING") and
                          int(v.get("size") or 0) <= MAX_BLOB), None)
    return impl[0], tests[0], license_entry, bool(tree.get("truncated"))

def inspected_blob(api: GitHubRead, repository: str, entry: dict | tuple) -> dict:
    if isinstance(entry, tuple):
        path, sha = entry
    else:
        path, sha = entry["path"], entry["sha"]
    if not SHA.fullmatch(str(sha)):
        raise SourceError("untrusted tree blob SHA")
    blob = api.get(f"/repos/{repository}/git/blobs/{sha}")
    if blob.get("encoding") != "base64":
        raise SourceError("source blob was not returned as base64")
    content = base64.b64decode(blob.get("content") or "", validate=False)
    if len(content) > MAX_BLOB:
        raise SourceError("source blob exceeds inspection budget")
    git_oid = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    if git_oid != sha or str(blob.get("sha")) != sha:
        raise SourceError("source bytes do not match pinned git object")
    return {"path": path, "git_blob_sha": sha, "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content), "verified_git_blob": True}

def inspect_candidate(api: GitHubRead, candidate: dict) -> dict:
    repository, revision = candidate["repository"], candidate["exact_revision"]
    tree = api.get(f"/repos/{repository}/git/trees/{revision}?recursive=1")
    src, tests, lic, truncated = source_paths(tree)
    result = {"repository": repository, "exact_revision": revision,
              "published_license_spdx": candidate["published_license_spdx"],
              "tree_truncated": truncated, "rights_status": "REVIEW_REQUIRED",
              "inspected_files": []}
    if src is None or tests is None:
        result["status"] = "INSUFFICIENT_SOURCE_AND_TEST_PATHS"
        return result
    result["inspected_files"] = [inspected_blob(api, repository, src),
                                 inspected_blob(api, repository, tests)]
    if lic and SHA.fullmatch(str(lic.get("sha") or "")):
        result["inspected_files"].append(inspected_blob(api, repository, lic))
    result["status"] = "SOURCE_INSPECTED"
    return result

def execute(manifest: dict, queue_root: Path, requested: str, seed: int, api: GitHubRead) -> dict:
    worker, queue = choose(manifest, queue_root, requested, seed)
    attempts = []
    for candidate in candidates(queue):
        try:
            attempt = inspect_candidate(api, candidate)
        except Exception as exc:
            attempt = {"repository": candidate["repository"],
                       "exact_revision": candidate["exact_revision"],
                       "status": "SOURCE_UNAVAILABLE", "reason": str(exc)[:180]}
        attempts.append(attempt)
        if attempt["status"] == "SOURCE_INSPECTED":
            break
    return {"schema_version": 1, "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "scope_version": SCOPE, "worker_id": worker["id"],
            "mission": worker["mission"], "project": worker["project"],
            "target_repository": worker["target_repository"],
            "queue_generated_at": queue.get("generated_at"),
            "attempts": attempts, "source_inspected": bool(attempts and attempts[-1]["status"] == "SOURCE_INSPECTED"),
            "completion_status": "NOT_ACCEPTED", "target_integration": "UNKNOWN",
            "measured_outcome": "UNKNOWN", "generated_activation": False,
            "claim_issued": False, "external_writes": False,
            "upstream_scout_run": os.getenv("UPSTREAM_SCOUT_RUN") or None,
            "github_run_url": os.getenv("GITHUB_SERVER_URL", "https://github.com") + "/" +
                os.getenv("GITHUB_REPOSITORY", "P00NSMASHER/github-value-hunt-ledger") +
                "/actions/runs/" + os.getenv("GITHUB_RUN_ID", "0")}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="automation/hunter_schedule.json")
    p.add_argument("--queues", default="intelligence/scout_queue")
    p.add_argument("--worker", default="AUTO")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", default="hunter-source-inspection.json")
    args = p.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        result = execute(manifest, Path(args.queues), args.worker, args.seed,
                         GitHubRead(os.getenv("GITHUB_TOKEN") or ""))
    except Exception as exc:
        result = {"schema_version": 1, "completion_status": "NOT_ACCEPTED",
                  "source_inspected": False, "status": "WORKER_EXECUTION_FAILED",
                  "reason": str(exc)[:300], "generated_activation": False,
                  "claim_issued": False, "external_writes": False}
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"worker": result.get("worker_id"), "source_inspected": result["source_inspected"],
                      "completion_status": "NOT_ACCEPTED", "status": result.get("status", "EXECUTED")}))
    return 2 if result.get("status") == "WORKER_EXECUTION_FAILED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
