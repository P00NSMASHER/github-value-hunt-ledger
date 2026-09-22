"""RecoveryOS custody, completeness, build-provenance, and public-transparency controls.

These controls are additive to the hostile-examination packet. They deliberately
separate cryptographic facts (hashes, Merkle roots) from operational attestations
(object-lock/WORM custody, population completeness, build-system identity).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping

from .assurance import CaseProofBundle, HostileExaminationPacket, verify_case_bundle
from .models import canonical_hash


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _iso(name: str, value: str) -> str:
    text = _required(name, value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone")
    return text


def _dt(name: str, value: str) -> datetime:
    return datetime.fromisoformat(_iso(name, value).replace("Z", "+00:00"))


def _nonnegative_int(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer")
    return value


def _hash_tuple(values: Iterable[str]) -> str:
    return canonical_hash({"schema": 1, "values": sorted(values)})


@dataclass(frozen=True)
class RetainedSourceObject:
    """Custody record for one retained source object.

    immutable_storage_verified is an operational assertion. For it to be true,
    provider_attestation_hash and retention_control_id must also be present.
    RecoveryOS does not infer object-lock state from a storage URI.
    """

    source_id: str
    role: str
    source_hash: str
    size_bytes: int
    storage_uri: str
    retained_at: str
    retention_mode: str
    retention_control_id: str | None
    provider_attestation_hash: str | None
    immutable_storage_verified: bool
    retain_until: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("source_id", "role", "source_hash", "storage_uri", "retention_mode"):
            _required(name, getattr(self, name))
        if self.role not in {"authority", "evidence"}:
            raise ValueError("retained source role must be authority or evidence")
        _nonnegative_int("size_bytes", self.size_bytes)
        retained = _dt("retained_at", self.retained_at)
        if self.retain_until is not None:
            until = _dt("retain_until", self.retain_until)
            if until < retained:
                raise ValueError("retain_until cannot precede retained_at")
        if type(self.immutable_storage_verified) is not bool:
            raise ValueError("immutable_storage_verified must be boolean")
        if self.immutable_storage_verified:
            _required("retention_control_id", self.retention_control_id or "")
            _required(
                "provider_attestation_hash",
                self.provider_attestation_hash or "",
            )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class SourceRetentionManifest:
    case_bundle_hash: str
    finding_proof_hash: str
    entries: tuple[RetainedSourceObject, ...]
    created_at: str
    created_by: str
    manifest_hash: str

    def __post_init__(self) -> None:
        for name in ("case_bundle_hash", "finding_proof_hash", "created_by", "manifest_hash"):
            _required(name, getattr(self, name))
        _iso("created_at", self.created_at)
        if not self.entries:
            raise ValueError("retention manifest requires retained source entries")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "case_bundle_hash": self.case_bundle_hash,
            "finding_proof_hash": self.finding_proof_hash,
            "entries": [
                {**asdict(item), "proof_hash": item.proof_hash}
                for item in sorted(
                    self.entries,
                    key=lambda item: (item.role, item.source_id),
                )
            ],
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.manifest_hash:
            raise ValueError("source retention manifest hash mismatch")


def freeze_source_retention(
    bundle: CaseProofBundle,
    *,
    entries: Iterable[RetainedSourceObject],
    created_at: str,
    created_by: str,
    require_immutable: bool = True,
) -> SourceRetentionManifest:
    """Bind retained source custody records to every load-bearing case source."""
    verify_case_bundle(bundle)
    created_at = _iso("created_at", created_at)
    created_by = _required("created_by", created_by)
    entry_tuple = tuple(sorted(entries, key=lambda item: (item.role, item.source_id)))

    expected = {
        ("authority", bundle.authority.authority_id): bundle.authority.source_hash,
        **{
            ("evidence", item.evidence_id): item.source_hash
            for item in bundle.source_attestations
        },
    }
    observed: dict[tuple[str, str], str] = {}
    for item in entry_tuple:
        key = (item.role, item.source_id)
        if key in observed:
            raise ValueError(f"duplicate retained source entry: {key!r}")
        observed[key] = item.source_hash
        if _dt("entry.retained_at", item.retained_at) > _dt("manifest.created_at", created_at):
            raise ValueError("retained source cannot postdate retention manifest")
        if require_immutable and not item.immutable_storage_verified:
            raise ValueError("high-value retention manifest requires verified immutable storage")
    if observed != expected:
        raise ValueError("retention manifest source set/hash mismatch")

    body = {
        "schema": 1,
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "entries": [
            {**asdict(item), "proof_hash": item.proof_hash}
            for item in entry_tuple
        ],
        "created_at": created_at,
        "created_by": created_by,
    }
    return SourceRetentionManifest(
        case_bundle_hash=bundle.bundle_hash,
        finding_proof_hash=bundle.finding.proof_hash,
        entries=entry_tuple,
        created_at=created_at,
        created_by=created_by,
        manifest_hash=canonical_hash(body),
    )


def verify_source_retention(
    manifest: SourceRetentionManifest,
    bundle: CaseProofBundle,
    *,
    require_immutable: bool = True,
) -> None:
    verify_case_bundle(bundle)
    manifest.verify_integrity()
    if manifest.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("retention manifest case bundle mismatch")
    if manifest.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("retention manifest finding mismatch")
    expected = {
        ("authority", bundle.authority.authority_id): bundle.authority.source_hash,
        **{
            ("evidence", item.evidence_id): item.source_hash
            for item in bundle.source_attestations
        },
    }
    observed = {
        (item.role, item.source_id): item.source_hash
        for item in manifest.entries
    }
    if observed != expected:
        raise ValueError("retention manifest source set/hash mismatch")
    if require_immutable and not all(
        item.immutable_storage_verified for item in manifest.entries
    ):
        raise ValueError("retention manifest contains unverified mutable storage")


@dataclass(frozen=True)
class PopulationSegment:
    segment_id: str
    source_export_hash: str
    selection_rule: str
    record_count: int
    included_record_count: int
    excluded_record_count: int
    control_total_hash: str
    included_ids_hash: str
    excluded_ids_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "segment_id",
            "source_export_hash",
            "selection_rule",
            "control_total_hash",
            "included_ids_hash",
            "excluded_ids_hash",
        ):
            _required(name, getattr(self, name))
        _nonnegative_int("record_count", self.record_count)
        _nonnegative_int("included_record_count", self.included_record_count)
        _nonnegative_int("excluded_record_count", self.excluded_record_count)
        if self.included_record_count + self.excluded_record_count != self.record_count:
            raise ValueError("population segment counts do not reconcile")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class NegativeEvidenceSearch:
    search_id: str
    scope: str
    method: str
    searched_source_hashes: tuple[str, ...]
    contrary_evidence_hashes: tuple[str, ...]
    searched_at: str
    searched_by: str
    conclusion: str
    resolved: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("search_id", "scope", "method", "searched_by", "conclusion"):
            _required(name, getattr(self, name))
        _iso("searched_at", self.searched_at)
        if type(self.resolved) is not bool:
            raise ValueError("negative-evidence search resolved must be boolean")
        if not self.searched_source_hashes:
            raise ValueError("negative-evidence search requires searched sources")
        for value in self.searched_source_hashes:
            _required("searched_source_hash", value)
        for value in self.contrary_evidence_hashes:
            _required("contrary_evidence_hash", value)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            **asdict(self),
            "searched_source_hashes": sorted(self.searched_source_hashes),
            "contrary_evidence_hashes": sorted(self.contrary_evidence_hashes),
        })


@dataclass(frozen=True)
class CaseCompletenessManifest:
    case_bundle_hash: str
    finding_proof_hash: str
    input_manifest_hash: str
    populations: tuple[PopulationSegment, ...]
    negative_searches: tuple[NegativeEvidenceSearch, ...]
    created_at: str
    created_by: str
    manifest_hash: str

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "case_bundle_hash": self.case_bundle_hash,
            "finding_proof_hash": self.finding_proof_hash,
            "input_manifest_hash": self.input_manifest_hash,
            "populations": [
                {**asdict(item), "proof_hash": item.proof_hash}
                for item in sorted(self.populations, key=lambda item: item.segment_id)
            ],
            "negative_searches": [
                {
                    **asdict(item),
                    "searched_source_hashes": sorted(item.searched_source_hashes),
                    "contrary_evidence_hashes": sorted(item.contrary_evidence_hashes),
                    "proof_hash": item.proof_hash,
                }
                for item in sorted(
                    self.negative_searches,
                    key=lambda item: item.search_id,
                )
            ],
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.manifest_hash:
            raise ValueError("case completeness manifest hash mismatch")


def freeze_case_completeness(
    bundle: CaseProofBundle,
    *,
    populations: Iterable[PopulationSegment],
    negative_searches: Iterable[NegativeEvidenceSearch],
    created_at: str,
    created_by: str,
) -> CaseCompletenessManifest:
    """Freeze population coverage and explicit negative/contrary-evidence search."""
    verify_case_bundle(bundle)
    created_at = _iso("created_at", created_at)
    created_by = _required("created_by", created_by)
    population_tuple = tuple(sorted(populations, key=lambda item: item.segment_id))
    search_tuple = tuple(sorted(negative_searches, key=lambda item: item.search_id))
    if not population_tuple:
        raise ValueError("completeness manifest requires at least one population segment")
    if not search_tuple:
        raise ValueError("completeness manifest requires negative-evidence search")
    if len({item.segment_id for item in population_tuple}) != len(population_tuple):
        raise ValueError("duplicate population segment_id")
    if len({item.search_id for item in search_tuple}) != len(search_tuple):
        raise ValueError("duplicate negative-evidence search_id")
    if not all(item.resolved for item in search_tuple):
        raise ValueError("all negative-evidence searches must be resolved")
    latest = max(
        *(_dt("negative_search.searched_at", item.searched_at) for item in search_tuple),
        _dt("bundle.created_at", bundle.created_at),
    )
    if _dt("created_at", created_at) < latest:
        raise ValueError("completeness manifest predates case/search evidence")

    body = {
        "schema": 1,
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "input_manifest_hash": bundle.calculation.input_manifest_hash,
        "populations": [
            {**asdict(item), "proof_hash": item.proof_hash}
            for item in population_tuple
        ],
        "negative_searches": [
            {
                **asdict(item),
                "searched_source_hashes": sorted(item.searched_source_hashes),
                "contrary_evidence_hashes": sorted(item.contrary_evidence_hashes),
                "proof_hash": item.proof_hash,
            }
            for item in search_tuple
        ],
        "created_at": created_at,
        "created_by": created_by,
    }
    return CaseCompletenessManifest(
        case_bundle_hash=bundle.bundle_hash,
        finding_proof_hash=bundle.finding.proof_hash,
        input_manifest_hash=bundle.calculation.input_manifest_hash,
        populations=population_tuple,
        negative_searches=search_tuple,
        created_at=created_at,
        created_by=created_by,
        manifest_hash=canonical_hash(body),
    )


def verify_case_completeness(
    manifest: CaseCompletenessManifest,
    bundle: CaseProofBundle,
) -> None:
    verify_case_bundle(bundle)
    manifest.verify_integrity()
    if manifest.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("completeness manifest case bundle mismatch")
    if manifest.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("completeness manifest finding mismatch")
    if manifest.input_manifest_hash != bundle.calculation.input_manifest_hash:
        raise ValueError("completeness manifest input population mismatch")
    if not manifest.populations:
        raise ValueError("completeness manifest lacks source populations")
    if not manifest.negative_searches or not all(
        item.resolved for item in manifest.negative_searches
    ):
        raise ValueError("completeness manifest lacks resolved negative-evidence search")


@dataclass(frozen=True)
class BuildProvenanceAttestation:
    calculator_id: str
    calculator_version: str
    code_commit_sha: str
    repository: str
    build_system: str
    workflow_identity: str
    workflow_run_id: str
    dependency_lock_hash: str
    source_tree_hash: str
    build_artifact_hash: str
    tests_passed: bool
    built_at: str
    attested_at: str
    attested_by: str
    attestation_hash: str

    def __post_init__(self) -> None:
        for name in (
            "calculator_id",
            "calculator_version",
            "code_commit_sha",
            "repository",
            "build_system",
            "workflow_identity",
            "workflow_run_id",
            "dependency_lock_hash",
            "source_tree_hash",
            "build_artifact_hash",
            "attested_by",
            "attestation_hash",
        ):
            _required(name, getattr(self, name))
        built = _dt("built_at", self.built_at)
        attested = _dt("attested_at", self.attested_at)
        if attested < built:
            raise ValueError("build attestation cannot predate build")
        if type(self.tests_passed) is not bool:
            raise ValueError("tests_passed must be boolean")

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            **{
                key: value
                for key, value in asdict(self).items()
                if key != "attestation_hash"
            },
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.attestation_hash:
            raise ValueError("build provenance attestation hash mismatch")


def create_build_provenance_attestation(
    bundle: CaseProofBundle,
    *,
    repository: str,
    build_system: str,
    workflow_identity: str,
    workflow_run_id: str,
    dependency_lock_hash: str,
    source_tree_hash: str,
    build_artifact_hash: str,
    tests_passed: bool,
    built_at: str,
    attested_at: str,
    attested_by: str,
) -> BuildProvenanceAttestation:
    verify_case_bundle(bundle)
    if not tests_passed:
        raise ValueError("high-value build provenance requires passing tests")
    body = {
        "schema": 1,
        "calculator_id": bundle.calculation.calculator_id,
        "calculator_version": bundle.calculation.calculator_version,
        "code_commit_sha": bundle.calculation.code_commit_sha,
        "repository": _required("repository", repository),
        "build_system": _required("build_system", build_system),
        "workflow_identity": _required("workflow_identity", workflow_identity),
        "workflow_run_id": _required("workflow_run_id", workflow_run_id),
        "dependency_lock_hash": _required("dependency_lock_hash", dependency_lock_hash),
        "source_tree_hash": _required("source_tree_hash", source_tree_hash),
        "build_artifact_hash": _required("build_artifact_hash", build_artifact_hash),
        "tests_passed": True,
        "built_at": _iso("built_at", built_at),
        "attested_at": _iso("attested_at", attested_at),
        "attested_by": _required("attested_by", attested_by),
    }
    if _dt("attested_at", body["attested_at"]) < _dt("built_at", body["built_at"]):
        raise ValueError("build attestation cannot predate build")
    return BuildProvenanceAttestation(
        **{key: value for key, value in body.items() if key != "schema"},
        attestation_hash=canonical_hash(body),
    )


def verify_build_provenance(
    attestation: BuildProvenanceAttestation,
    bundle: CaseProofBundle,
) -> None:
    verify_case_bundle(bundle)
    attestation.verify_integrity()
    if attestation.calculator_id != bundle.calculation.calculator_id:
        raise ValueError("build provenance calculator mismatch")
    if attestation.calculator_version != bundle.calculation.calculator_version:
        raise ValueError("build provenance calculator version mismatch")
    if attestation.code_commit_sha != bundle.calculation.code_commit_sha:
        raise ValueError("build provenance code commit mismatch")
    if not attestation.tests_passed:
        raise ValueError("build provenance tests did not pass")


def _merkle_parent(left: str, right: str) -> str:
    return canonical_hash({"schema": 1, "left": left, "right": right})


def merkle_root(leaves: Iterable[str]) -> str:
    """Deterministic binary Merkle root over sorted public leaf hashes."""
    level = sorted(_required("leaf_hash", value) for value in leaves)
    if not level:
        raise ValueError("Merkle tree requires at least one leaf")
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            _merkle_parent(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        ]
    return level[0]


@dataclass(frozen=True)
class PublicVerificationRecord:
    """Privacy-preserving transparency record safe to publish.

    This record proves internal consistency of disclosed hashes. It does not by
    itself authenticate RecoveryWorks as the publisher; authenticity should be
    added by an external asymmetric-signature/transparency service.
    """

    record_id: str
    case_bundle_hash: str
    finding_proof_hash: str
    hostile_packet_hash: str
    retention_manifest_hash: str
    completeness_manifest_hash: str
    build_attestation_hash: str
    journal_head_hash: str
    merkle_root_hash: str
    published_at: str
    publisher_id: str
    record_hash: str

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            **{
                key: value
                for key, value in asdict(self).items()
                if key != "record_hash"
            },
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.record_hash:
            raise ValueError("public verification record hash mismatch")


def hostile_packet_hash(packet: HostileExaminationPacket) -> str:
    return canonical_hash({
        "schema": 1,
        **packet.integrity_body(),
        "packet_signature_hex": packet.packet_signature_hex,
    })


def create_public_verification_record(
    bundle: CaseProofBundle,
    packet: HostileExaminationPacket,
    retention: SourceRetentionManifest,
    completeness: CaseCompletenessManifest,
    build: BuildProvenanceAttestation,
    *,
    journal_head_hash: str,
    record_id: str,
    published_at: str,
    publisher_id: str,
) -> PublicVerificationRecord:
    """Create a publishable hash-only transparency record for a frozen case."""
    verify_case_bundle(bundle)
    verify_source_retention(retention, bundle)
    verify_case_completeness(completeness, bundle)
    verify_build_provenance(build, bundle)
    if packet.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("public record hostile packet case mismatch")
    if packet.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("public record hostile packet finding mismatch")
    if packet.journal_head_hash != journal_head_hash:
        raise ValueError("public record journal head mismatch")

    packet_hash = hostile_packet_hash(packet)
    leaves = (
        bundle.bundle_hash,
        bundle.finding.proof_hash,
        packet_hash,
        retention.manifest_hash,
        completeness.manifest_hash,
        build.attestation_hash,
        journal_head_hash,
    )
    root = merkle_root(leaves)
    body = {
        "schema": 1,
        "record_id": _required("record_id", record_id),
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "hostile_packet_hash": packet_hash,
        "retention_manifest_hash": retention.manifest_hash,
        "completeness_manifest_hash": completeness.manifest_hash,
        "build_attestation_hash": build.attestation_hash,
        "journal_head_hash": _required("journal_head_hash", journal_head_hash),
        "merkle_root_hash": root,
        "published_at": _iso("published_at", published_at),
        "publisher_id": _required("publisher_id", publisher_id),
    }
    return PublicVerificationRecord(
        **{key: value for key, value in body.items() if key != "schema"},
        record_hash=canonical_hash(body),
    )


def verify_public_verification_record(
    record: PublicVerificationRecord,
    bundle: CaseProofBundle,
    packet: HostileExaminationPacket,
    retention: SourceRetentionManifest,
    completeness: CaseCompletenessManifest,
    build: BuildProvenanceAttestation,
    *,
    journal_head_hash: str,
) -> None:
    """Verify the public transparency record without exposing private source bytes."""
    record.verify_integrity()
    verify_case_bundle(bundle)
    verify_source_retention(retention, bundle)
    verify_case_completeness(completeness, bundle)
    verify_build_provenance(build, bundle)
    expected_packet_hash = hostile_packet_hash(packet)
    fields = {
        "case_bundle_hash": bundle.bundle_hash,
        "finding_proof_hash": bundle.finding.proof_hash,
        "hostile_packet_hash": expected_packet_hash,
        "retention_manifest_hash": retention.manifest_hash,
        "completeness_manifest_hash": completeness.manifest_hash,
        "build_attestation_hash": build.attestation_hash,
        "journal_head_hash": journal_head_hash,
    }
    for name, expected in fields.items():
        if getattr(record, name) != expected:
            raise ValueError(f"public verification record {name} mismatch")
    expected_root = merkle_root(fields.values())
    if record.merkle_root_hash != expected_root:
        raise ValueError("public verification Merkle root mismatch")
