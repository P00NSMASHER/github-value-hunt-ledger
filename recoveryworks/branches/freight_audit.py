"""RecoveryOS adapter for the pinned freight-audit domain engine.

Step 1 vendors the deterministic rule engine at a fixed upstream commit.
Step 2 maps every domain finding into RecoveryOS evidence while keeping the
third-party engine outside the money-bearing authority boundary.

Important invariants:
- every upstream finding gets a deterministic EvidenceRef;
- only positive broker-overpayment candidates become RecoveryObservation values;
- carrier-underbilling and non-monetary warnings remain evidence-only;
- a verified controlling RuleRef is never synthesized from engine output;
- overlapping rules are conservatively de-duplicated by normalized charge
  category, with aggregate invoice mismatch used only for unexplained residual;
- source/integrity gaps force REVIEW by withholding the controlling rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef, canonical_hash

from .freight_authority import FreightAuthorityContext, resolve_freight_authority

from .freight_audit_vendor import (
    CarrierInvoice,
    EngineConfig,
    Finding,
    FindingType,
    LineItem,
    MatchEngine,
    MatchResult,
    ProofOfDelivery,
    RateConfirmation,
    Severity,
    is_same_load,
    normalize_category,
)

UPSTREAM_REPOSITORY = "aiparallel0/freight-audit"
UPSTREAM_COMMIT = "e7869162cf9cb23f6d520a0cd71f87cf973d8c28"
ENGINE_ID = f"{UPSTREAM_REPOSITORY}:src/freight_audit/match.py"

_SPECIFIC_MONEY_TYPES = frozenset({
    FindingType.LINE_OVERCHARGE,
    FindingType.UNAUTHORIZED_ACCESSORIAL,
    FindingType.DUPLICATE_LINE,
    FindingType.ACCESSORIAL_OVER_CAP,
})
_INTEGRITY_BLOCKERS = frozenset({
    FindingType.MISSING_DOC,
    FindingType.LOAD_ID_MISMATCH,
    FindingType.BAD_POD_DATA,
})
_TYPE_PRIORITY = {
    FindingType.DUPLICATE_LINE: 4,
    FindingType.ACCESSORIAL_OVER_CAP: 3,
    FindingType.UNAUTHORIZED_ACCESSORIAL: 2,
    FindingType.LINE_OVERCHARGE: 1,
}
_CATEGORY_QUOTED_RE = re.compile(r"^'([^']+)' charge")
_CATEGORY_PAREN_RE = re.compile(r"\(([^()]+)\)\s+billed")


class FreightAuditDisposition(str, Enum):
    OBSERVATION = "OBSERVATION"
    SUPPRESSED_OVERLAP = "SUPPRESSED_OVERLAP"
    EVIDENCE_ONLY = "EVIDENCE_ONLY"
    OUT_OF_SCOPE_DIRECTION = "OUT_OF_SCOPE_DIRECTION"


@dataclass(frozen=True)
class FreightAuditDomainResult:
    match: MatchResult
    engine_id: str = ENGINE_ID
    engine_commit: str = UPSTREAM_COMMIT

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(self.match.findings)

    @property
    def load_id(self) -> str:
        return self.match.load_id

    @property
    def severity(self) -> Severity:
        return self.match.severity

    @property
    def net_money_impact_cents(self) -> int:
        return self.match.net_money_impact_cents

    @property
    def auto_approvable(self) -> bool:
        return self.match.auto_approvable


@dataclass(frozen=True)
class FreightAuditEvidenceBundle:
    """Proof-bearing source documents supplied by RecoveryOS intake."""

    invoice: EvidenceRef | None
    rate_confirmation: EvidenceRef | None = None
    pod: EvidenceRef | None = None

    def available(self) -> tuple[EvidenceRef, ...]:
        return tuple(
            item for item in (self.invoice, self.rate_confirmation, self.pod)
            if item is not None
        )


@dataclass(frozen=True)
class MappedFreightAuditFinding:
    index: int
    finding_type: FindingType
    severity: Severity
    message: str
    original_money_impact_cents: int
    allocated_candidate_cents: int
    normalized_category: str | None
    disposition: FreightAuditDisposition
    candidate_evidence: EvidenceRef
    source_evidence: tuple[EvidenceRef, ...]
    authority_evidence: tuple[EvidenceRef, ...]
    authority_blockers: tuple[str, ...]
    authority_resolution_hash: str | None
    observation: RecoveryObservation | None
    suppression_reason: str | None = None


@dataclass(frozen=True)
class FreightAuditRecoveryMapping:
    load_id: str
    engine_id: str
    engine_commit: str
    mapped_findings: tuple[MappedFreightAuditFinding, ...]
    observations: tuple[RecoveryObservation, ...]
    integrity_blockers: tuple[str, ...]

    @property
    def candidate_recovery_cents(self) -> int:
        return sum(
            item.allocated_candidate_cents
            for item in self.mapped_findings
            if item.disposition is FreightAuditDisposition.OBSERVATION
        )


class FreightAuditDomainAdapter:
    """Run the pinned deterministic freight audit without crossing the proof boundary."""

    engine_id = ENGINE_ID
    engine_commit = UPSTREAM_COMMIT

    def __init__(self, config: EngineConfig | None = None):
        self._engine = MatchEngine(config)

    def audit(
        self,
        rate_confirmation: RateConfirmation | None,
        invoice: CarrierInvoice | None,
        pod: ProofOfDelivery | None,
    ) -> FreightAuditDomainResult:
        return FreightAuditDomainResult(
            self._engine.match(rate_confirmation, invoice, pod)
        )


def _finding_category(finding: Finding) -> str | None:
    """Recover the normalized category from the pinned engine message contract."""
    message = finding.message.strip()
    category: str | None = None

    if finding.type is FindingType.DUPLICATE_LINE:
        match = _CATEGORY_QUOTED_RE.search(message)
        category = match.group(1) if match else None
    elif finding.type is FindingType.UNAUTHORIZED_ACCESSORIAL:
        match = _CATEGORY_PAREN_RE.search(message)
        category = match.group(1) if match else None
    elif finding.type in {
        FindingType.LINE_OVERCHARGE,
        FindingType.ACCESSORIAL_OVER_CAP,
    }:
        category = message.split(" billed ", 1)[0] if " billed " in message else None

    if not category:
        return None
    normalized = normalize_category(category)
    if normalized != "other":
        return normalized
    raw = category.strip().lower()
    return raw or None


def _candidate_evidence(
    result: FreightAuditDomainResult,
    index: int,
    finding: Finding,
) -> EvidenceRef:
    body = {
        "schema": 1,
        "engine_id": result.engine_id,
        "engine_commit": result.engine_commit,
        "load_id": result.load_id,
        "index": index,
        "type": finding.type.value,
        "severity": finding.severity.value,
        "message": finding.message,
        "money_impact_cents": finding.money_impact_cents,
    }
    digest = canonical_hash(body)
    return EvidenceRef(
        evidence_id=f"freight-audit:{digest}",
        source_hash=digest,
        locator=(
            f"freight-audit://{result.engine_commit}/"
            f"{result.load_id}/{index}/{finding.type.value}"
        ),
        kind="freight_audit_candidate",
        verified=True,
        metadata={
            "engine_id": result.engine_id,
            "engine_commit": result.engine_commit,
            "finding_type": finding.type.value,
            "severity": finding.severity.value,
            "money_impact_cents": finding.money_impact_cents,
        },
    )


def _source_evidence_for(
    finding: Finding,
    bundle: FreightAuditEvidenceBundle,
) -> tuple[EvidenceRef, ...]:
    required: tuple[EvidenceRef | None, ...]
    if finding.type in {
        FindingType.TOTAL_MISMATCH,
        FindingType.LINE_OVERCHARGE,
        FindingType.UNAUTHORIZED_ACCESSORIAL,
        FindingType.ACCESSORIAL_OVER_CAP,
    }:
        required = (bundle.invoice, bundle.rate_confirmation)
    elif finding.type in {
        FindingType.DETENTION_UNDERBILLED,
        FindingType.DETENTION_UNSUPPORTED,
        FindingType.MULTIPLE_DETENTION_LINES,
    }:
        required = (bundle.invoice, bundle.rate_confirmation, bundle.pod)
    elif finding.type is FindingType.BAD_POD_DATA:
        required = (bundle.pod,)
    elif finding.type is FindingType.LOAD_ID_MISMATCH:
        required = (bundle.invoice, bundle.rate_confirmation, bundle.pod)
    elif finding.type in {
        FindingType.DUPLICATE_LINE,
        FindingType.ZERO_AMOUNT_ACCESSORIAL,
        FindingType.MISSING_POD,
    }:
        required = (bundle.invoice,)
    else:
        required = (bundle.invoice, bundle.rate_confirmation, bundle.pod)
    return tuple(item for item in required if item is not None)


def _required_sources_complete(
    finding: Finding,
    bundle: FreightAuditEvidenceBundle,
) -> bool:
    if finding.type in {
        FindingType.TOTAL_MISMATCH,
        FindingType.LINE_OVERCHARGE,
        FindingType.UNAUTHORIZED_ACCESSORIAL,
        FindingType.ACCESSORIAL_OVER_CAP,
    }:
        return bundle.invoice is not None and bundle.rate_confirmation is not None
    if finding.type is FindingType.DUPLICATE_LINE:
        return bundle.invoice is not None
    return bool(_source_evidence_for(finding, bundle))


def _dedup_allocations(
    findings: tuple[Finding, ...],
) -> tuple[dict[int, int], dict[int, str]]:
    """Allocate money once while preserving every upstream finding as evidence."""
    allocations: dict[int, int] = {}
    suppressed: dict[int, str] = {}

    grouped: dict[str, dict[FindingType, list[int]]] = {}
    totals: dict[tuple[str, FindingType], int] = {}
    total_mismatch_indices: list[int] = []

    for index, finding in enumerate(findings):
        if finding.money_impact_cents <= 0:
            continue
        if finding.type is FindingType.TOTAL_MISMATCH:
            total_mismatch_indices.append(index)
            continue
        if finding.type not in _SPECIFIC_MONEY_TYPES:
            continue

        category = _finding_category(finding) or "__unknown__"
        grouped.setdefault(category, {}).setdefault(finding.type, []).append(index)
        key = (category, finding.type)
        totals[key] = totals.get(key, 0) + finding.money_impact_cents

    explained = 0
    for category, by_type in grouped.items():
        winning_type = max(
            by_type,
            key=lambda kind: (
                totals[(category, kind)],
                _TYPE_PRIORITY.get(kind, 0),
            ),
        )
        for kind, indices in by_type.items():
            if kind is winning_type:
                for index in indices:
                    amount = findings[index].money_impact_cents
                    allocations[index] = amount
                    explained += amount
            else:
                for index in indices:
                    suppressed[index] = (
                        f"overlaps {winning_type.value} for category {category}"
                    )

    if total_mismatch_indices:
        strongest_total_index = max(
            total_mismatch_indices,
            key=lambda index: findings[index].money_impact_cents,
        )
        total_amount = findings[strongest_total_index].money_impact_cents
        residual = max(total_amount - explained, 0)
        if residual:
            allocations[strongest_total_index] = residual
        else:
            suppressed[strongest_total_index] = (
                "aggregate invoice mismatch fully explained by specific findings"
            )
        for index in total_mismatch_indices:
            if index != strongest_total_index:
                suppressed[index] = "duplicate aggregate invoice mismatch"

    return allocations, suppressed


def map_freight_audit_to_recovery(
    result: FreightAuditDomainResult,
    *,
    client_id: str,
    counterparty_id: str,
    currency: str,
    evidence: FreightAuditEvidenceBundle,
    controlling_rule: RuleRef | None = None,
    authority_context: FreightAuthorityContext | None = None,
) -> FreightAuditRecoveryMapping:
    """Map pinned engine output into RecoveryOS evidence and observations.

    The controlling rule must come from RecoveryOS authority review. Engine rule
    names/messages are never promoted into controlling authority.

    Money-bearing observations use component-delta semantics: expected=0 and
    actual=allocated candidate cents. Source totals remain in metadata, avoiding
    invented line-level expected values that the upstream Finding does not expose.
    """
    if controlling_rule is not None and authority_context is not None:
        raise ValueError("provide controlling_rule or authority_context, not both")

    findings = result.findings
    allocations, suppressed = _dedup_allocations(findings)
    integrity = tuple(
        finding.type.value
        for finding in findings
        if finding.type in _INTEGRITY_BLOCKERS
    )

    mapped: list[MappedFreightAuditFinding] = []
    observations: list[RecoveryObservation] = []

    for index, finding in enumerate(findings):
        candidate_ref = _candidate_evidence(result, index, finding)
        source_refs = _source_evidence_for(finding, evidence)
        category = _finding_category(finding)
        amount = allocations.get(index, 0)

        disposition = FreightAuditDisposition.EVIDENCE_ONLY
        suppression_reason: str | None = None
        observation: RecoveryObservation | None = None
        authority_evidence: tuple[EvidenceRef, ...] = ()
        authority_blockers: tuple[str, ...] = ()
        authority_resolution_hash: str | None = None
        matched_rule_hashes: tuple[str, ...] = ()

        if finding.money_impact_cents < 0:
            disposition = FreightAuditDisposition.OUT_OF_SCOPE_DIRECTION
            suppression_reason = (
                "carrier-underbilling is not broker-overpayment FreightRecovery"
            )
        elif index in suppressed:
            disposition = FreightAuditDisposition.SUPPRESSED_OVERLAP
            suppression_reason = suppressed[index]
        elif amount > 0:
            disposition = FreightAuditDisposition.OBSERVATION
            proof_complete = _required_sources_complete(finding, evidence)
            verified_sources = proof_complete and all(
                ref.verified for ref in source_refs
            )
            resolved_rule: RuleRef | None = controlling_rule
            if authority_context is not None:
                authority_resolution = resolve_freight_authority(
                    authority_context,
                    finding_type=finding.type,
                    normalized_category=category,
                )
                resolved_rule = authority_resolution.rule
                authority_evidence = authority_resolution.evidence
                authority_blockers = authority_resolution.blockers
                authority_resolution_hash = authority_resolution.authority_hash
                matched_rule_hashes = authority_resolution.matched_rule_hashes

            effective_rule = (
                resolved_rule
                if (
                    resolved_rule is not None
                    and verified_sources
                    and not integrity
                    and not authority_blockers
                )
                else None
            )
            observation = RecoveryObservation(
                branch=Branch.FREIGHT,
                client_id=client_id,
                counterparty_id=counterparty_id,
                reference=f"{result.load_id}:{index}:{finding.type.value}",
                currency=currency,
                expected_cents=0,
                actual_cents=amount,
                rule=effective_rule,
                evidence=(candidate_ref, *source_refs, *authority_evidence),
                reason=f"FREIGHT_AUDIT_{finding.type.value.upper()}",
                confidence_basis=(
                    "pinned deterministic freight-audit engine; "
                    "RecoveryOS source hashes + controlling authority required "
                    "for VALIDATED state"
                ),
                metadata={
                    "engine_id": result.engine_id,
                    "engine_commit": result.engine_commit,
                    "load_id": result.load_id,
                    "finding_index": index,
                    "finding_type": finding.type.value,
                    "severity": finding.severity.value,
                    "normalized_category": category,
                    "original_money_impact_cents": finding.money_impact_cents,
                    "allocated_candidate_cents": amount,
                    "source_invoice_total_cents": (
                        result.match.invoice.billed_total_cents
                        if result.match.invoice is not None else None
                    ),
                    "source_rate_total_cents": (
                        result.match.rate_con.agreed_total_cents
                        if result.match.rate_con is not None else None
                    ),
                    "integrity_blockers": list(integrity),
                    "authority_blockers": list(authority_blockers),
                    "authority_resolution_hash": authority_resolution_hash,
                    "matched_authority_rule_hashes": list(matched_rule_hashes),
                },
            )
            observations.append(observation)

        mapped.append(MappedFreightAuditFinding(
            index=index,
            finding_type=finding.type,
            severity=finding.severity,
            message=finding.message,
            original_money_impact_cents=finding.money_impact_cents,
            allocated_candidate_cents=amount,
            normalized_category=category,
            disposition=disposition,
            candidate_evidence=candidate_ref,
            source_evidence=source_refs,
            authority_evidence=authority_evidence,
            authority_blockers=authority_blockers,
            authority_resolution_hash=authority_resolution_hash,
            observation=observation,
            suppression_reason=suppression_reason,
        ))

    return FreightAuditRecoveryMapping(
        load_id=result.load_id,
        engine_id=result.engine_id,
        engine_commit=result.engine_commit,
        mapped_findings=tuple(mapped),
        observations=tuple(observations),
        integrity_blockers=integrity,
    )


__all__ = [
    "CarrierInvoice",
    "ENGINE_ID",
    "EngineConfig",
    "Finding",
    "FindingType",
    "FreightAuditDisposition",
    "FreightAuditDomainAdapter",
    "FreightAuditDomainResult",
    "FreightAuthorityContext",
    "FreightAuditEvidenceBundle",
    "FreightAuditRecoveryMapping",
    "LineItem",
    "MappedFreightAuditFinding",
    "MatchResult",
    "ProofOfDelivery",
    "RateConfirmation",
    "Severity",
    "UPSTREAM_COMMIT",
    "UPSTREAM_REPOSITORY",
    "is_same_load",
    "map_freight_audit_to_recovery",
    "normalize_category",
]
