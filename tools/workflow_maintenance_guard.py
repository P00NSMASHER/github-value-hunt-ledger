#!/usr/bin/env python3
"""Fail-closed, read-only policy for the reviewed ledger workflow inventory.

This protects the largest active repository from unreviewed workflow growth,
added schedules, new token-write scopes and new privileged PR triggers. It does
not edit workflows or claim branch rulesets on other repositories.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "automation" / "WORKFLOW_MAINTENANCE_BASELINE.json"
WORKFLOW_DIR = ROOT / ".github" / "workflows"

WRITE_SCOPES = (
    "actions", "checks", "contents", "deployments", "discussions", "id-token",
    "issues", "packages", "pages", "pull-requests", "repository-projects",
    "security-events", "statuses", "attestations",
)
WRITE_RE = re.compile(
    r"(?m)^\s*(" + "|".join(re.escape(x) for x in WRITE_SCOPES)
    + r"):\s*write(?:\s*(?:#.*)?)?$"
)
CRON_RE = re.compile(r"(?m)^\s*-\s*cron:\s*['\"]?([^'\"\r\n]+)")
SCHEDULE_RE = re.compile(r"(?m)^  schedule:\s*$")
UNSAFE_EVENT_RE = re.compile(r"(?m)^\s*pull_request_target\s*:")
BROAD_PERMISSIONS_RE = re.compile(r"(?m)^\s*permissions:\s*write-all(?:\s*(?:#.*)?)?$")
INLINE_WRITE_RE = re.compile(r"(?m)^\s*permissions:\s*\{[^\n]*\bwrite\b")
SHELL_PIPE_RE = re.compile(
    r"(?i)\b(?:curl|wget)\b[^\n]{0,250}\|\s*(?:sudo\s+)?"
    r"(?:bash|sh)(?:\s|$)"
)


class WorkflowPolicyError(ValueError):
    """The workflow inventory drifted beyond its explicitly reviewed baseline."""


def load_baseline(path=BASELINE_PATH):
    with Path(path).open(encoding="utf-8") as stream:
        data = json.load(stream)
    if data.get("schema_version") != 1 or data.get("scope") != \
            "P00NSMASHER/github-value-hunt-ledger":
        raise WorkflowPolicyError("INVALID_WORKFLOW_BASELINE_IDENTITY")
    names = data.get("workflows")
    if not isinstance(names, list) or len(names) != len(set(names)) or \
            names != sorted(names) or any(
                not isinstance(n, str) or not n.endswith((".yml", ".yaml"))
                or "/" in n for n in names):
        raise WorkflowPolicyError("MALFORMED_WORKFLOW_FILE_ALLOWLIST")
    for key in ("approved_scheduled_workflows", "approved_write_scopes"):
        policies = data.get(key)
        if not isinstance(policies, dict) or any(k not in names for k in policies):
            raise WorkflowPolicyError("MALFORMED_" + key.upper())
    return data


def audit_workflows(workflow_dir, baseline):
    directory = Path(workflow_dir)
    names = sorted(f.name for f in directory.iterdir()
                   if f.is_file() and f.suffix in (".yml", ".yaml"))
    if names != baseline["workflows"]:
        extra = sorted(set(names) - set(baseline["workflows"]))
        missing = sorted(set(baseline["workflows"]) - set(names))
        raise WorkflowPolicyError(
            f"WORKFLOW_INVENTORY_DRIFT:added={extra}:missing={missing}"
        )

    checked = 0
    scheduled = 0
    privileged = 0
    schedule_policy = baseline["approved_scheduled_workflows"]
    writes_policy = baseline["approved_write_scopes"]
    for name in names:
        data = (directory / name).read_text(encoding="utf-8")
        # A comment must not grant authority to a new workflow.
        active = "\n".join(line for line in data.splitlines()
                           if not line.lstrip().startswith("#"))
        if UNSAFE_EVENT_RE.search(active):
            raise WorkflowPolicyError("PR_TARGET_NOT_REVIEWED:" + name)
        if BROAD_PERMISSIONS_RE.search(active) or INLINE_WRITE_RE.search(active):
            raise WorkflowPolicyError("BROAD_WORKFLOW_PERMISSIONS:" + name)
        if SHELL_PIPE_RE.search(active):
            raise WorkflowPolicyError("REMOTE_SHELL_PIPE_NOT_REVIEWED:" + name)
        crons = [match.strip() for match in CRON_RE.findall(active)]
        has_schedule = bool(SCHEDULE_RE.search(active))
        approved_crons = schedule_policy.get(name, [])
        if crons != approved_crons or has_schedule != bool(approved_crons):
            raise WorkflowPolicyError(
                f"UNREVIEWED_WORKFLOW_SCHEDULE:{name}:"
                f"actual={crons}:approved={approved_crons}"
            )
        writes = sorted(set(WRITE_RE.findall(active)))
        approved_writes = sorted(set(writes_policy.get(name, [])))
        if writes != approved_writes:
            raise WorkflowPolicyError(
                f"UNREVIEWED_WORKFLOW_WRITE_SCOPE:{name}:"
                f"actual={writes}:approved={approved_writes}"
            )
        scheduled += int(has_schedule)
        privileged += int(bool(writes))
        checked += 1
    return {
        "status": "reviewed-inventory-unchanged",
        "workflow_count": checked,
        "scheduled_workflows": scheduled,
        "workflows_with_write_scopes": privileged,
        "scope": baseline["scope"],
        "source_main_commit": baseline["source_main_commit"],
        "not_a_cross_repository_branch_ruleset": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit_workflows(WORKFLOW_DIR, load_baseline()),
                     sort_keys=True))
