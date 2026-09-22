"""Seven-figure assurance controls for RecoveryOS.

This module turns a VALIDATED finding into a frozen, content-addressed case
packet suitable for hostile internal/external examination. It deliberately
does not send claims or contact counterparties.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any, Iterable, Mapping

from .journal import finding_from_payload, finding_to_payload
from .models import EvidenceRef, FindingState, RecoveryFinding, RuleRef, canonical_hash

SEVEN_FIGURE_CENTS = 100_000_000


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _nonnegative_cents(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


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
    """Parse an offset-aware ISO-8601 timestamp for temporal consistency checks."""
    text = _iso(name, value)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _hash_bytes(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("artifact bytes are required")
    return hashlib.sha256(bytes(data)).hexdigest()


@dataclass(frozen=True)
class AuthoritySnapshot:
    authority_id: str
    authority_kind: str
    source_hash: str
    source_locator: str
    effective_from: str
    effective_to: str | None
    acquired_at: str
    verified_by: str
    verification_note: str
    jurisdiction: str | None = None
    supersedes_authority_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "authority_id", "authority_kind", "source_hash", "source_locator",
            "effective_from", "verified_by", "verification_note",
        ):
            _required(name, getattr(self, name))
        _iso("acquired_at", self.acquired_at)
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})

    def assert_binds(self, rule: RuleRef) -> None:
        if rule.source_hash != self.source_hash:
            raise ValueError("authority source_hash does not match controlling rule")
        if rule.source_locator != self.source_locator:
            raise ValueError("authority locator does not match controlling rule")
        if rule.effective_from != self.effective_from:
            raise ValueError("authority effective_from does not match controlling rule")
        if rule.effective_to != self.effective_to:
            raise ValueError("authority effective_to does not match controlling rule")
        if rule.jurisdiction and self.jurisdiction and rule.jurisdiction != self.jurisdiction:
            raise ValueError("authority jurisdiction does not match controlling rule")


class AuthorityRegistry:
    """Content-addressed registry of reviewed point-in-time authorities."""

    def __init__(self) -> None:
        self._by_id: dict[str, AuthoritySnapshot] = {}

    def register(self, snapshot: AuthoritySnapshot) -> AuthoritySnapshot:
        existing = self._by_id.get(snapshot.authority_id)
        if existing is not None:
            if existing.proof_hash != snapshot.proof_hash:
                raise ValueError(
                    "authority_id already exists with different immutable proof"
                )
            return existing
        if (
            snapshot.supersedes_authority_id is not None
            and snapshot.supersedes_authority_id not in self._by_id
        ):
            raise ValueError("superseded authority must be registered first")
        self._by_id[snapshot.authority_id] = snapshot
        return snapshot

    def get(self, authority_id: str) -> AuthoritySnapshot:
        try:
            return self._by_id[authority_id]
        except KeyError as exc:
            raise KeyError(f"unknown authority_id: {authority_id}") from exc

    def resolve_rule(self, rule: RuleRef) -> AuthoritySnapshot:
        matches: list[AuthoritySnapshot] = []
        for snapshot in self._by_id.values():
            try:
                snapshot.assert_binds(rule)
            except ValueError:
                continue
            matches.append(snapshot)
        if len(matches) != 1:
            raise ValueError(
                f"controlling rule must resolve to exactly one authority snapshot; "
                f"found {len(matches)}"
            )
        return matches[0]

    @property
    def registry_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "authorities": [
                {
                    "authority_id": item.authority_id,
                    "proof_hash": item.proof_hash,
                }
                for item in sorted(
                    self._by_id.values(),
                    key=lambda value: value.authority_id,
                )
            ],
        })

    def export(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "registry_hash": self.registry_hash,
            "authorities": [
                {**asdict(item), "proof_hash": item.proof_hash}
                for item in sorted(
                    self._by_id.values(),
                    key=lambda value: value.authority_id,
                )
            ],
        }

    @classmethod
    def from_export(cls, payload: Mapping[str, Any]) -> "AuthorityRegistry":
        if payload.get("schema") != 1:
            raise ValueError("unsupported authority registry schema")
        registry = cls()
        for raw in payload.get("authorities", []):
            proof_hash = raw.get("proof_hash")
            snapshot = AuthoritySnapshot(**{
                key: value for key, value in raw.items() if key != "proof_hash"
            })
            if proof_hash != snapshot.proof_hash:
                raise ValueError("authority snapshot proof hash mismatch")
            registry.register(snapshot)
        if payload.get("registry_hash") != registry.registry_hash:
            raise ValueError("authority registry hash mismatch")
        return registry


@dataclass(frozen=True)
class SourceAttestation:
    evidence_id: str
    source_hash: str
    locator: str
    acquisition_method: str
    acquired_at: str
    authenticated_by: str
    authentication_note: str
    verified_source: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "evidence_id", "source_hash", "locator", "acquisition_method",
            "authenticated_by", "authentication_note",
        ):
            _required(name, getattr(self, name))
        _iso("acquired_at", self.acquired_at)
        if type(self.verified_source) is not bool:
            raise ValueError("verified_source must be boolean")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})

    def assert_binds(self, evidence: EvidenceRef) -> None:
        if self.evidence_id != evidence.evidence_id:
            raise ValueError("source attestation evidence_id mismatch")
        if self.source_hash != evidence.source_hash:
            raise ValueError("source attestation source_hash mismatch")
        if self.locator != evidence.locator:
            raise ValueError("source attestation locator mismatch")
        if evidence.verified and not self.verified_source:
            raise ValueError("verified evidence requires verified source attestation")


@dataclass(frozen=True)
class CalculationManifest:
    calculator_id: str
    calculator_version: str
    code_commit_sha: str
    input_manifest_hash: str
    finding_proof_hash: str
    expected_cents: int
    actual_cents: int
    potential_recovery_cents: int
    trace_hash: str
    created_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "calculator_id", "calculator_version", "code_commit_sha",
            "input_manifest_hash", "finding_proof_hash", "trace_hash",
        ):
            _required(name, getattr(self, name))
        _iso("created_at", self.created_at)
        _nonnegative_cents("expected_cents", self.expected_cents)
        _nonnegative_cents("actual_cents", self.actual_cents)
        _nonnegative_cents("potential_recovery_cents", self.potential_recovery_cents)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})

    def assert_binds(self, finding: RecoveryFinding) -> None:
        if self.finding_proof_hash != finding.proof_hash:
            raise ValueError("calculation manifest finding hash mismatch")
        if self.expected_cents != finding.expected_cents:
            raise ValueError("calculation manifest expected amount mismatch")
        if self.actual_cents != finding.actual_cents:
            raise ValueError("calculation manifest actual amount mismatch")
        if self.potential_recovery_cents != finding.potential_recovery_cents:
            raise ValueError("calculation manifest recovery amount mismatch")


@dataclass(frozen=True)
class ReviewAttestation:
    review_id: str
    finding_proof_hash: str
    reviewer_id: str
    reviewer_role: str
    decision: str
    reviewed_at: str
    note: str
    qualification_basis: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "review_id", "finding_proof_hash", "reviewer_id", "reviewer_role",
            "decision", "note",
        ):
            _required(name, getattr(self, name))
        _iso("reviewed_at", self.reviewed_at)
        if self.decision not in {"APPROVE", "REJECT"}:
            raise ValueError("decision must be APPROVE or REJECT")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class ChallengeReview:
    challenge_id: str
    finding_proof_hash: str
    reviewer_id: str
    reviewed_at: str
    challenge: str
    conclusion: str
    resolved: bool
    contrary_evidence_hashes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "challenge_id", "finding_proof_hash", "reviewer_id",
            "challenge", "conclusion",
        ):
            _required(name, getattr(self, name))
        _iso("reviewed_at", self.reviewed_at)
        if type(self.resolved) is not bool:
            raise ValueError("resolved must be boolean")
        for item in self.contrary_evidence_hashes:
            _required("contrary_evidence_hash", item)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            **asdict(self),
            "contrary_evidence_hashes": sorted(self.contrary_evidence_hashes),
        })


@dataclass(frozen=True)
class DeadlineAssessment:
    assessment_id: str
    finding_proof_hash: str
    governing_source_hash: str
    source_locator: str
    trigger: str
    assessed_at: str
    assessed_by: str
    deadline_at: str | None
    conclusion: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "assessment_id", "finding_proof_hash", "governing_source_hash",
            "source_locator", "trigger", "assessed_by", "conclusion",
        ):
            _required(name, getattr(self, name))
        _iso("assessed_at", self.assessed_at)
        if self.deadline_at is not None:
            _iso("deadline_at", self.deadline_at)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class CaseProofBundle:
    schema: int
    finding: RecoveryFinding
    authority: AuthoritySnapshot
    source_attestations: tuple[SourceAttestation, ...]
    calculation: CalculationManifest
    reviews: tuple[ReviewAttestation, ...]
    challenges: tuple[ChallengeReview, ...]
    deadlines: tuple[DeadlineAssessment, ...]
    created_at: str
    created_by: str
    scan_batch_hash: str | None
    bundle_hash: str

    @property
    def high_value(self) -> bool:
        return self.finding.potential_recovery_cents >= SEVEN_FIGURE_CENTS


def _case_body(
    *,
    finding: RecoveryFinding,
    authority: AuthoritySnapshot,
    source_attestations: Iterable[SourceAttestation],
    calculation: CalculationManifest,
    reviews: Iterable[ReviewAttestation],
    challenges: Iterable[ChallengeReview],
    deadlines: Iterable[DeadlineAssessment],
    created_at: str,
    created_by: str,
    scan_batch_hash: str | None,
) -> dict[str, Any]:
    return {
        "schema": 1,
        "finding": finding_to_payload(finding),
        "authority": asdict(authority),
        "authority_hash": authority.proof_hash,
        "source_attestations": [
            {**asdict(item), "proof_hash": item.proof_hash}
            for item in sorted(source_attestations, key=lambda x: x.evidence_id)
        ],
        "calculation": {**asdict(calculation), "proof_hash": calculation.proof_hash},
        "reviews": [
            {**asdict(item), "proof_hash": item.proof_hash}
            for item in sorted(reviews, key=lambda x: x.review_id)
        ],
        "challenges": [
            {
                **asdict(item),
                "contrary_evidence_hashes": sorted(item.contrary_evidence_hashes),
                "proof_hash": item.proof_hash,
            }
            for item in sorted(challenges, key=lambda x: x.challenge_id)
        ],
        "deadlines": [
            {**asdict(item), "proof_hash": item.proof_hash}
            for item in sorted(deadlines, key=lambda x: x.assessment_id)
        ],
        "created_at": created_at,
        "created_by": created_by,
        "scan_batch_hash": scan_batch_hash,
    }


def freeze_case_proof(
    *,
    finding: RecoveryFinding,
    authority: AuthoritySnapshot,
    source_attestations: Iterable[SourceAttestation],
    calculation: CalculationManifest,
    reviews: Iterable[ReviewAttestation],
    challenges: Iterable[ChallengeReview] = (),
    deadlines: Iterable[DeadlineAssessment] = (),
    created_at: str,
    created_by: str,
    scan_batch_hash: str | None = None,
) -> CaseProofBundle:
    if finding.state is not FindingState.VALIDATED:
        raise ValueError("case proof may only freeze a VALIDATED finding")
    if finding.rule is None or not finding.rule.verified_controlling:
        raise ValueError("case proof requires a verified controlling rule")

    created_at = _iso("created_at", created_at)
    created_by = _required("created_by", created_by)
    if scan_batch_hash is not None:
        _required("scan_batch_hash", scan_batch_hash)

    authority.assert_binds(finding.rule)
    calculation.assert_binds(finding)

    source_tuple = tuple(sorted(source_attestations, key=lambda x: x.evidence_id))
    source_by_id = {item.evidence_id: item for item in source_tuple}
    if len(source_by_id) != len(source_tuple):
        raise ValueError("duplicate source attestation evidence_id")
    if set(source_by_id) != {item.evidence_id for item in finding.evidence}:
        raise ValueError("every load-bearing evidence item requires one source attestation")
    for evidence in finding.evidence:
        source_by_id[evidence.evidence_id].assert_binds(evidence)

    review_tuple = tuple(sorted(reviews, key=lambda x: x.review_id))
    if not review_tuple:
        raise ValueError("at least one review attestation is required")
    if any(item.finding_proof_hash != finding.proof_hash for item in review_tuple):
        raise ValueError("review attestation finding hash mismatch")
    approving = [item for item in review_tuple if item.decision == "APPROVE"]
    if not approving:
        raise ValueError("at least one approving review is required")
    reviewer_ids = [item.reviewer_id for item in approving]
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise ValueError("approving reviewers must be distinct")

    challenge_tuple = tuple(sorted(challenges, key=lambda x: x.challenge_id))
    if any(item.finding_proof_hash != finding.proof_hash for item in challenge_tuple):
        raise ValueError("challenge review finding hash mismatch")

    deadline_tuple = tuple(sorted(deadlines, key=lambda x: x.assessment_id))
    if any(item.finding_proof_hash != finding.proof_hash for item in deadline_tuple):
        raise ValueError("deadline assessment finding hash mismatch")

    # Hostile-examination temporal consistency. A review cannot logically
    # attest to evidence/calculation that did not yet exist, and a frozen case
    # cannot predate the attestations it claims to contain.
    freeze_time = _dt("created_at", created_at)
    authority_time = _dt("authority.acquired_at", authority.acquired_at)
    source_times = [
        _dt(f"source_attestation[{item.evidence_id}].acquired_at", item.acquired_at)
        for item in source_tuple
    ]
    calculation_time = _dt("calculation.created_at", calculation.created_at)
    latest_input_time = max([authority_time, *source_times])
    if calculation_time < latest_input_time:
        raise ValueError(
            "calculation cannot predate authority/source acquisition"
        )

    for item in review_tuple:
        reviewed = _dt(f"review[{item.review_id}].reviewed_at", item.reviewed_at)
        if reviewed < calculation_time:
            raise ValueError("review cannot predate calculation")
        if reviewed > freeze_time:
            raise ValueError("review cannot postdate case freeze")
    for item in challenge_tuple:
        reviewed = _dt(
            f"challenge[{item.challenge_id}].reviewed_at",
            item.reviewed_at,
        )
        if reviewed < calculation_time:
            raise ValueError("challenge review cannot predate calculation")
        if reviewed > freeze_time:
            raise ValueError("challenge review cannot postdate case freeze")
    for item in deadline_tuple:
        assessed = _dt(
            f"deadline[{item.assessment_id}].assessed_at",
            item.assessed_at,
        )
        if assessed < calculation_time:
            raise ValueError("deadline assessment cannot predate calculation")
        if assessed > freeze_time:
            raise ValueError("deadline assessment cannot postdate case freeze")
    if calculation_time > freeze_time:
        raise ValueError("calculation cannot postdate case freeze")

    if finding.potential_recovery_cents >= SEVEN_FIGURE_CENTS:
        if len(approving) < 2:
            raise ValueError("seven-figure finding requires two independent approving reviewers")
        if not challenge_tuple or not all(item.resolved for item in challenge_tuple):
            raise ValueError("seven-figure finding requires resolved adversarial challenge review")
        if not deadline_tuple:
            raise ValueError("seven-figure finding requires explicit deadline assessment")
        if not all(item.verified_source for item in source_tuple):
            raise ValueError("seven-figure finding requires authenticated source attestations")
        challenge_reviewers = {item.reviewer_id for item in challenge_tuple}
        if challenge_reviewers.intersection(set(reviewer_ids)):
            raise ValueError(
                "seven-figure adversarial reviewer must be independent "
                "of all approving reviewers"
            )

    body = _case_body(
        finding=finding,
        authority=authority,
        source_attestations=source_tuple,
        calculation=calculation,
        reviews=review_tuple,
        challenges=challenge_tuple,
        deadlines=deadline_tuple,
        created_at=created_at,
        created_by=created_by,
        scan_batch_hash=scan_batch_hash,
    )
    return CaseProofBundle(
        schema=1,
        finding=finding,
        authority=authority,
        source_attestations=source_tuple,
        calculation=calculation,
        reviews=review_tuple,
        challenges=challenge_tuple,
        deadlines=deadline_tuple,
        created_at=created_at,
        created_by=created_by,
        scan_batch_hash=scan_batch_hash,
        bundle_hash=canonical_hash(body),
    )


def verify_case_bundle(bundle: CaseProofBundle) -> None:
    rebuilt = freeze_case_proof(
        finding=bundle.finding,
        authority=bundle.authority,
        source_attestations=bundle.source_attestations,
        calculation=bundle.calculation,
        reviews=bundle.reviews,
        challenges=bundle.challenges,
        deadlines=bundle.deadlines,
        created_at=bundle.created_at,
        created_by=bundle.created_by,
        scan_batch_hash=bundle.scan_batch_hash,
    )
    if rebuilt.bundle_hash != bundle.bundle_hash:
        raise ValueError("case proof bundle hash mismatch")


@dataclass(frozen=True)
class ClientActionAuthorization:
    authorization_id: str
    case_bundle_hash: str
    finding_proof_hash: str
    client_actor_id: str
    approved_action_type: str
    authorized_at: str
    maximum_amount_cents: int
    note: str
    expires_at: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "authorization_id", "case_bundle_hash", "finding_proof_hash",
            "client_actor_id", "approved_action_type", "note",
        ):
            _required(name, getattr(self, name))
        authorized = _dt("authorized_at", self.authorized_at)
        if self.expires_at is not None:
            expires = _dt("expires_at", self.expires_at)
            if expires < authorized:
                raise ValueError("expires_at cannot precede authorized_at")
        _nonnegative_cents("maximum_amount_cents", self.maximum_amount_cents)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


def authorize_case_action(
    bundle: CaseProofBundle,
    *,
    authorization_id: str,
    client_actor_id: str,
    approved_action_type: str,
    authorized_at: str,
    maximum_amount_cents: int,
    note: str,
    expires_at: str | None = None,
) -> ClientActionAuthorization:
    verify_case_bundle(bundle)
    reviewer_ids = {item.reviewer_id for item in bundle.reviews}
    reviewer_ids.update(item.reviewer_id for item in bundle.challenges)
    if client_actor_id in reviewer_ids:
        raise ValueError("client authorizer must be independent of RecoveryWorks reviewers")
    if _dt("authorized_at", authorized_at) < _dt("bundle.created_at", bundle.created_at):
        raise ValueError("client authorization cannot predate frozen case")
    if maximum_amount_cents < bundle.finding.potential_recovery_cents:
        raise ValueError("authorization amount is below validated recovery amount")
    return ClientActionAuthorization(
        authorization_id=authorization_id,
        case_bundle_hash=bundle.bundle_hash,
        finding_proof_hash=bundle.finding.proof_hash,
        client_actor_id=client_actor_id,
        approved_action_type=approved_action_type,
        authorized_at=authorized_at,
        maximum_amount_cents=maximum_amount_cents,
        note=note,
        expires_at=expires_at,
    )


def verify_action_authorization(
    bundle: CaseProofBundle,
    authorization: ClientActionAuthorization,
) -> None:
    verify_case_bundle(bundle)
    if authorization.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("authorization case bundle hash mismatch")
    if authorization.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("authorization finding hash mismatch")
    reviewer_ids = {item.reviewer_id for item in bundle.reviews}
    reviewer_ids.update(item.reviewer_id for item in bundle.challenges)
    if authorization.client_actor_id in reviewer_ids:
        raise ValueError("client authorizer must be independent of reviewers")
    if _dt("authorization.authorized_at", authorization.authorized_at) < _dt(
        "bundle.created_at", bundle.created_at
    ):
        raise ValueError("client authorization cannot predate frozen case")
    if authorization.maximum_amount_cents < bundle.finding.potential_recovery_cents:
        raise ValueError("authorization amount is below validated recovery amount")


@dataclass(frozen=True)
class ExternalActionEnvelope:
    case_bundle_hash: str
    authorization_hash: str
    authorization_id: str
    finding_id: str
    finding_proof_hash: str
    approved_action_type: str
    artifact_kind: str
    artifact_hash: str
    artifact_locator: str
    artifact_size: int
    action_amount_cents: int
    prepared_by: str
    prepared_at: str
    envelope_hash: str

    def integrity_body(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "case_bundle_hash": self.case_bundle_hash,
            "authorization_hash": self.authorization_hash,
            "authorization_id": self.authorization_id,
            "finding_id": self.finding_id,
            "finding_proof_hash": self.finding_proof_hash,
            "approved_action_type": self.approved_action_type,
            "artifact_kind": self.artifact_kind,
            "artifact_hash": self.artifact_hash,
            "artifact_locator": self.artifact_locator,
            "artifact_size": self.artifact_size,
            "action_amount_cents": self.action_amount_cents,
            "prepared_by": self.prepared_by,
            "prepared_at": self.prepared_at,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.envelope_hash:
            raise ValueError("external action envelope hash mismatch")


def prepare_external_action(
    bundle: CaseProofBundle,
    authorization: ClientActionAuthorization,
    *,
    artifact_kind: str,
    artifact_bytes: bytes,
    artifact_locator: str,
    action_amount_cents: int,
    prepared_by: str,
    prepared_at: str,
) -> ExternalActionEnvelope:
    verify_action_authorization(bundle, authorization)
    _required("artifact_kind", artifact_kind)
    _required("artifact_locator", artifact_locator)
    _required("prepared_by", prepared_by)
    prepared_at = _iso("prepared_at", prepared_at)
    prepared_time = _dt("prepared_at", prepared_at)
    if prepared_time < _dt("authorization.authorized_at", authorization.authorized_at):
        raise ValueError("external action cannot predate client authorization")
    _nonnegative_cents("action_amount_cents", action_amount_cents)
    if action_amount_cents > authorization.maximum_amount_cents:
        raise ValueError("action amount exceeds client authorization")
    if action_amount_cents > bundle.finding.potential_recovery_cents:
        raise ValueError("action amount exceeds validated recovery amount")
    if authorization.expires_at is not None:
        expiry = datetime.fromisoformat(authorization.expires_at.replace("Z", "+00:00"))
        prepared = datetime.fromisoformat(prepared_at.replace("Z", "+00:00"))
        if prepared > expiry:
            raise ValueError("client authorization has expired")
    for assessment in bundle.deadlines:
        if assessment.deadline_at is None:
            continue
        deadline = datetime.fromisoformat(assessment.deadline_at.replace("Z", "+00:00"))
        prepared = datetime.fromisoformat(prepared_at.replace("Z", "+00:00"))
        if prepared > deadline:
            raise ValueError("external action is past an assessed deadline")

    body = {
        "schema": 1,
        "case_bundle_hash": bundle.bundle_hash,
        "authorization_hash": authorization.proof_hash,
        "authorization_id": authorization.authorization_id,
        "finding_id": bundle.finding.finding_id,
        "finding_proof_hash": bundle.finding.proof_hash,
        "approved_action_type": authorization.approved_action_type,
        "artifact_kind": artifact_kind,
        "artifact_hash": _hash_bytes(artifact_bytes),
        "artifact_locator": artifact_locator,
        "artifact_size": len(artifact_bytes),
        "action_amount_cents": action_amount_cents,
        "prepared_by": prepared_by,
        "prepared_at": prepared_at,
    }
    envelope_fields = {key: value for key, value in body.items() if key != "schema"}
    return ExternalActionEnvelope(
        **envelope_fields,
        envelope_hash=canonical_hash(body),
    )


def verify_external_action(
    envelope: ExternalActionEnvelope,
    bundle: CaseProofBundle,
    authorization: ClientActionAuthorization,
    *,
    artifact_bytes: bytes | None = None,
) -> None:
    envelope.verify_integrity()
    verify_action_authorization(bundle, authorization)
    if envelope.case_bundle_hash != bundle.bundle_hash:
        raise ValueError("external action case bundle mismatch")
    if envelope.authorization_hash != authorization.proof_hash:
        raise ValueError("external action authorization mismatch")
    if envelope.authorization_id != authorization.authorization_id:
        raise ValueError("external action authorization id mismatch")
    if envelope.finding_id != bundle.finding.finding_id:
        raise ValueError("external action finding id mismatch")
    if envelope.finding_proof_hash != bundle.finding.proof_hash:
        raise ValueError("external action finding proof mismatch")
    if envelope.approved_action_type != authorization.approved_action_type:
        raise ValueError("external action type differs from client authorization")
    if envelope.action_amount_cents > authorization.maximum_amount_cents:
        raise ValueError("external action exceeds authorized amount")
    if envelope.action_amount_cents > bundle.finding.potential_recovery_cents:
        raise ValueError("external action exceeds validated recovery amount")

    prepared = _dt("external_action.prepared_at", envelope.prepared_at)
    authorized = _dt("authorization.authorized_at", authorization.authorized_at)
    if prepared < authorized:
        raise ValueError("external action predates client authorization")
    if authorization.expires_at is not None:
        if prepared > _dt("authorization.expires_at", authorization.expires_at):
            raise ValueError("external action was prepared after authorization expiry")
    for assessment in bundle.deadlines:
        if assessment.deadline_at is None:
            continue
        if prepared > _dt(
            f"deadline[{assessment.assessment_id}].deadline_at",
            assessment.deadline_at,
        ):
            raise ValueError("external action is past an assessed deadline")

    if artifact_bytes is not None:
        if len(artifact_bytes) != envelope.artifact_size:
            raise ValueError("external action artifact size mismatch")
        if _hash_bytes(artifact_bytes) != envelope.artifact_hash:
            raise ValueError("external action artifact hash mismatch")


def case_bundle_to_payload(bundle: CaseProofBundle) -> dict[str, Any]:
    verify_case_bundle(bundle)
    return {
        **_case_body(
            finding=bundle.finding,
            authority=bundle.authority,
            source_attestations=bundle.source_attestations,
            calculation=bundle.calculation,
            reviews=bundle.reviews,
            challenges=bundle.challenges,
            deadlines=bundle.deadlines,
            created_at=bundle.created_at,
            created_by=bundle.created_by,
            scan_batch_hash=bundle.scan_batch_hash,
        ),
        "bundle_hash": bundle.bundle_hash,
    }


def case_bundle_from_payload(payload: Mapping[str, Any]) -> CaseProofBundle:
    finding = finding_from_payload(payload["finding"])
    authority_raw = dict(payload["authority"])
    authority = AuthoritySnapshot(**authority_raw)
    source_attestations = tuple(
        SourceAttestation(**{k: v for k, v in raw.items() if k != "proof_hash"})
        for raw in payload.get("source_attestations", [])
    )
    calculation = CalculationManifest(**{
        k: v for k, v in payload["calculation"].items() if k != "proof_hash"
    })
    reviews = tuple(
        ReviewAttestation(**{k: v for k, v in raw.items() if k != "proof_hash"})
        for raw in payload.get("reviews", [])
    )
    challenges = tuple(
        ChallengeReview(**{
            **{k: v for k, v in raw.items() if k != "proof_hash"},
            "contrary_evidence_hashes": tuple(raw.get("contrary_evidence_hashes", ())),
        })
        for raw in payload.get("challenges", [])
    )
    deadlines = tuple(
        DeadlineAssessment(**{k: v for k, v in raw.items() if k != "proof_hash"})
        for raw in payload.get("deadlines", [])
    )
    bundle = freeze_case_proof(
        finding=finding,
        authority=authority,
        source_attestations=source_attestations,
        calculation=calculation,
        reviews=reviews,
        challenges=challenges,
        deadlines=deadlines,
        created_at=payload["created_at"],
        created_by=payload["created_by"],
        scan_batch_hash=payload.get("scan_batch_hash"),
    )
    if payload.get("bundle_hash") != bundle.bundle_hash:
        raise ValueError("case proof bundle hash mismatch")
    return bundle


def authorization_to_payload(auth: ClientActionAuthorization) -> dict[str, Any]:
    return {**asdict(auth), "proof_hash": auth.proof_hash}


def authorization_from_payload(payload: Mapping[str, Any]) -> ClientActionAuthorization:
    auth = ClientActionAuthorization(**{
        k: v for k, v in payload.items() if k != "proof_hash"
    })
    if payload.get("proof_hash") != auth.proof_hash:
        raise ValueError("authorization proof hash mismatch")
    return auth


def external_action_to_payload(envelope: ExternalActionEnvelope) -> dict[str, Any]:
    envelope.verify_integrity()
    return asdict(envelope)


def external_action_from_payload(payload: Mapping[str, Any]) -> ExternalActionEnvelope:
    envelope = ExternalActionEnvelope(**dict(payload))
    envelope.verify_integrity()
    return envelope
