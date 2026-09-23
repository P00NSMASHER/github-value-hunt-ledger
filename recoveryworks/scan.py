"""Frozen Recovery Scan 360 manifests and deterministic scan batches."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .engine import RecoveryEngine, RecoveryObservation
from .models import Branch, RecoveryFinding, canonical_hash, normalize_source_hash


@dataclass(frozen=True)
class SourceManifestEntry:
    source_id: str
    branch: Branch
    source_hash: str
    locator: str
    kind: str

    def __post_init__(self) -> None:
        for name in ("source_id", "locator", "kind"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        if not isinstance(self.branch, Branch):
            raise ValueError("branch must be a Branch")
        object.__setattr__(
            self,
            "source_hash",
            normalize_source_hash(self.source_hash),
        )


@dataclass(frozen=True)
class RecoveryScanManifest:
    scan_id: str
    client_id: str
    branches: tuple[Branch, ...]
    selection_rule: str
    sources: tuple[SourceManifestEntry, ...]
    manifest_hash: str


@dataclass(frozen=True)
class RecoveryScanBatch:
    manifest: RecoveryScanManifest
    findings: tuple[RecoveryFinding, ...]
    batch_hash: str


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def freeze_scan(
    *,
    scan_id: str,
    client_id: str,
    branches: Iterable[Branch],
    selection_rule: str,
    sources: Iterable[SourceManifestEntry],
) -> RecoveryScanManifest:
    scan_id = _required("scan_id", scan_id)
    client_id = _required("client_id", client_id)
    selection_rule = _required("selection_rule", selection_rule)
    branch_tuple = tuple(sorted(set(branches), key=lambda b: b.value))
    if not branch_tuple:
        raise ValueError("at least one branch is required")

    supplied_sources = tuple(sources)
    if not all(isinstance(source, SourceManifestEntry) for source in supplied_sources):
        raise ValueError("sources must contain only SourceManifestEntry values")
    source_tuple = tuple(
        sorted(supplied_sources, key=lambda s: (s.branch.value, s.source_id))
    )
    seen: set[str] = set()
    for source in source_tuple:
        if source.source_id in seen:
            raise ValueError(f"duplicate source_id: {source.source_id}")
        seen.add(source.source_id)
        if source.branch not in branch_tuple:
            raise ValueError("source branch is outside scan scope")

    body = {
        "schema": 1,
        "scan_id": scan_id,
        "client_id": client_id,
        "branches": [branch.value for branch in branch_tuple],
        "selection_rule": selection_rule,
        "sources": [
            {**asdict(source), "branch": source.branch.value}
            for source in source_tuple
        ],
    }
    return RecoveryScanManifest(
        scan_id=scan_id,
        client_id=client_id,
        branches=branch_tuple,
        selection_rule=selection_rule,
        sources=source_tuple,
        manifest_hash=canonical_hash(body),
    )


def run_scan(
    manifest: RecoveryScanManifest,
    observations: Iterable[RecoveryObservation],
    *,
    engine: RecoveryEngine | None = None,
) -> RecoveryScanBatch:
    normalized = tuple(observations)
    for observation in normalized:
        if observation.client_id != manifest.client_id:
            raise ValueError("observation client_id does not match frozen scan")
        if observation.branch not in manifest.branches:
            raise ValueError("observation branch is outside frozen scan scope")
    findings = (engine or RecoveryEngine()).scan(normalized)
    body = {
        "schema": 1,
        "manifest_hash": manifest.manifest_hash,
        "finding_proof_hashes": sorted(finding.proof_hash for finding in findings),
    }
    return RecoveryScanBatch(
        manifest=manifest,
        findings=findings,
        batch_hash=canonical_hash(body),
    )
