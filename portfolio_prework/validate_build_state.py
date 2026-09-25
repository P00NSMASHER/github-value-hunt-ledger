#!/usr/bin/env python3
"""Validate Portfolio Brain durable build state using only the standard library.

This intentionally validates the invariants that matter for resumability even
when a JSON Schema package is not installed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PHASES = {"parallel_prework", "architecture_build", "canary", "operational"}
INSPECTION = {"UNINSPECTED", "UNCHANGED", "CHANGED", "INSPECTED", "ERROR"}
TEST_STATUS = {"PASS", "FAIL", "SKIP", "PENDING"}
DECISION_STATUS = {"PROVISIONAL", "ACCEPTED", "SUPERSEDED", "REJECTED"}
BLOCKER_STATUS = {"OPEN", "RESOLVED", "DEFERRED"}


class ValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_state(state: dict[str, Any]) -> None:
    required = {
        "schema_version","architecture_version","state_id","working_branch","phase",
        "current_step","completed_steps","repositories","decisions","artifacts",
        "tests","blockers","next_action","updated_at"
    }
    missing = required - set(state)
    _require(not missing, f"missing required keys: {sorted(missing)}")
    _require(SEMVER_RE.fullmatch(state["schema_version"]) is not None, "schema_version must be semver")
    _require(state["phase"] in PHASES, f"invalid phase: {state['phase']}")
    _require(isinstance(state["current_step"], int) and state["current_step"] >= 0, "current_step must be nonnegative integer")

    completed = state["completed_steps"]
    _require(isinstance(completed, list), "completed_steps must be a list")
    _require(len(completed) == len(set(completed)), "completed_steps must be unique")
    _require(all(isinstance(x, int) and x >= 0 for x in completed), "completed_steps entries must be nonnegative integers")
    _require(all(x < state["current_step"] for x in completed), "completed step cannot be current/future step")

    repos = state["repositories"]
    _require(isinstance(repos, dict), "repositories must be an object")
    for repo_id, item in repos.items():
        _require(repo_id.startswith("REPO-"), f"invalid repository id: {repo_id}")
        _require("/" in item["full_name"], f"invalid full_name for {repo_id}")
        sha = item.get("last_inspected_sha")
        _require(sha is None or SHA_RE.fullmatch(sha) is not None, f"invalid SHA for {repo_id}")
        _require(item["inspection_status"] in INSPECTION, f"invalid inspection status for {repo_id}")

    decision_ids = []
    for item in state["decisions"]:
        decision_ids.append(item["decision_id"])
        _require(item["status"] in DECISION_STATUS, f"invalid decision status: {item['decision_id']}")
        _require(isinstance(item["evidence_refs"], list), f"evidence_refs must be list: {item['decision_id']}")
    _require(len(decision_ids) == len(set(decision_ids)), "decision IDs must be unique")

    artifact_paths = []
    for item in state["artifacts"]:
        artifact_paths.append(item["path"])
        _require(isinstance(item["step"], int) and item["step"] >= 0, f"invalid artifact step: {item['path']}")
        sha = item.get("commit_sha")
        _require(sha is None or SHA_RE.fullmatch(sha) is not None, f"invalid artifact SHA: {item['path']}")
    _require(len(artifact_paths) == len(set(artifact_paths)), "artifact paths must be unique")

    for item in state["tests"]:
        _require(item["status"] in TEST_STATUS, f"invalid test status: {item['name']}")
        _require(isinstance(item["step"], int) and item["step"] >= 0, f"invalid test step: {item['name']}")

    blocker_ids = []
    for item in state["blockers"]:
        blocker_ids.append(item["blocker_id"])
        _require(item["status"] in BLOCKER_STATUS, f"invalid blocker status: {item['blocker_id']}")
    _require(len(blocker_ids) == len(set(blocker_ids)), "blocker IDs must be unique")

    next_action = state["next_action"]
    if next_action is not None:
        _require(next_action["step"] == state["current_step"], "next_action.step must equal current_step")
        _require(bool(next_action["summary"].strip()), "next_action.summary cannot be empty")

    _require(bool(state["updated_at"]), "updated_at is required")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="portfolio_prework/PORTFOLIO_BUILD_STATE.json")
    args = parser.parse_args(argv)
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    validate_state(state)
    print(
        f"valid build state: step={state['current_step']} "
        f"completed={len(state['completed_steps'])} repos={len(state['repositories'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
