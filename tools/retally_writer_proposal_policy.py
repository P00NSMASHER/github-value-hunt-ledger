"""Exact-path gates for RETALLY's four GitHub-managed evidence writers.

This module has no provider credentials, network calls or mutation functions.
It validates a proposed update before ANY GitHub PR/merge automation can use it.
Existing production writers remain unchanged until an Actions-token canary
proves creation, workflow_dispatch CI and merge.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
TI_MANIFEST = ROOT / ".github/technology-intelligence-generated-files.txt"
LANES = ("scout", "catalog", "integrator", "technology")
COMMIT_SHA = re.compile(r"[a-f0-9]{40}\Z")
SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]{1,255}\Z")
PROPOSAL_BRANCH = re.compile(
    r"automation/retally-(scout|catalog|integrator|technology)-"
    r"([1-9][0-9]{3,15})-([1-9][0-9]{0,3})\Z"
)
SCOUT_EXACT = {"automation/SCOUT_DIGEST.md"}
SCOUT_PREFIXES = ("intelligence/scout_queue/",)
CATALOG_EXACT = {
    "CAPABILITIES.md", "COMPONENTS.md", "DATASETS.md",
    "OPPORTUNITIES.md", "REJECTED.md", "SEARCH_QUEUE.md",
    "TECHNOLOGY_RADAR.md",
}
CATALOG_PREFIXES = ("hunters/", "lanes/", "referrals/")
INTEGRATOR_EXACT = {
    "MASTER.md", "COMBINATIONS.md", "CAPABILITIES.md",
    "COMPONENTS.md", "DATASETS.md", "EXPERIMENTS.md",
    "KNOWLEDGE_GRAPH.md", "OPPORTUNITIES.md", "OUTCOMES.md",
    "REJECTED.md", "SEARCH_QUEUE.md", "SEARCH_SKILLS.md",
    "TECHNOLOGY_RADAR.md", "README.md",
}
INTEGRATOR_PREFIXES = ("hunters/", "lanes/", "referrals/", "production/shadow/")
DATA_EXTENSIONS = {".md", ".json", ".jsonl", ".txt", ".csv"}


class ProposalHold(ValueError):
    """Refuse integration; never silently skip or weaken a configured gate."""


def safe_relative_file(path: str) -> bool:
    if not isinstance(path, str) or SAFE_PATH.fullmatch(path) is None:
        return False
    if path.startswith("/") or "//" in path or "\\" in path or path.endswith("/"):
        return False
    parts = path.split("/")
    if any(part in ("", ".", "..") or part.startswith(".") for part in parts):
        return False
    if any(part.endswith((".lock", ".key", ".pem", ".p12", ".sqlite", ".db", ".py"))
           for part in (parts[-1],)):
        return False
    return True


def generated_manifest(manifest: Path = TI_MANIFEST) -> frozenset[str]:
    lines = manifest.read_text(encoding="utf-8").splitlines()
    values = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not values or len(values) != len(set(values)):
        raise ProposalHold("TI manifest is empty or duplicates a file path")
    if any(not safe_relative_file(x) or not x.startswith("intelligence/")
           or Path(x).suffix.lower() not in DATA_EXTENSIONS for x in values):
        raise ProposalHold("TI manifest allows an unsafe generated file path")
    return frozenset(values)


def allowed_path(lane: str, path: str, *, ti_paths: frozenset[str]) -> bool:
    if lane not in LANES or not safe_relative_file(path):
        return False
    extension = Path(path).suffix.lower()
    if extension not in DATA_EXTENSIONS:
        return False
    if lane == "technology":
        return path in ti_paths
    if lane == "scout":
        return path in SCOUT_EXACT or (
            path.startswith(SCOUT_PREFIXES) and extension == ".json"
        )
    if lane == "catalog":
        return path in CATALOG_EXACT or path.startswith(CATALOG_PREFIXES)
    if lane == "integrator":
        return path in INTEGRATOR_EXACT or path.startswith(INTEGRATOR_PREFIXES)
    return False


def branch_for_run(lane: str, run_id: str, run_attempt: str) -> str:
    if lane not in LANES:
        raise ProposalHold("Unknown writer lane")
    try:
        branch = f"automation/retally-{lane}-{int(run_id)}-{int(run_attempt)}"
    except (ValueError, TypeError, OverflowError):
        raise ProposalHold("GitHub run ID or attempt is not numeric") from None
    if not PROPOSAL_BRANCH.fullmatch(branch):
        raise ProposalHold("GitHub writer branch format is not authorized")
    return branch


@dataclass(frozen=True)
class VerifiedProposal:
    lane: str
    branch: str
    base_sha: str
    head_sha: str
    files: tuple[str, ...]


def verify_proposal(
    lane: str,
    branch: str,
    base_sha: str,
    head_sha: str,
    first_parent: str,
    files: Iterable[str] | Mapping[str, str],
    *,
    manifest: Path = TI_MANIFEST,
) -> VerifiedProposal:
    if lane not in LANES:
        raise ProposalHold("Unknown writer lane")
    m = PROPOSAL_BRANCH.fullmatch(branch)
    if m is None or m.group(1) != lane:
        raise ProposalHold("Proposal must use exact lane-specific run branch")
    if (not isinstance(base_sha, str) or COMMIT_SHA.fullmatch(base_sha) is None
        or not isinstance(head_sha, str) or COMMIT_SHA.fullmatch(head_sha) is None
        or first_parent != base_sha or head_sha == base_sha):
        raise ProposalHold("Proposal is not exactly based on the current main commit")
    if isinstance(files, Mapping):
        if any(status not in {"added", "modified"} for status in files.values()):
            raise ProposalHold("Proposal deletes/renames source; owner reconciliation needed")
        paths = tuple(files)
    else:
        paths = tuple(files)
    if not paths or len(paths) > 512 or len(paths) != len(set(paths)):
        raise ProposalHold("Missing, excessive or duplicate proposed files")
    allowed = generated_manifest(manifest) if lane == "technology" else frozenset()
    for path in paths:
        if not allowed_path(lane, path, ti_paths=allowed):
            raise ProposalHold("Proposal modifies a file outside its exact writer scope")
    return VerifiedProposal(lane, branch, base_sha, head_sha, paths)
