"""Reviewer-ready RecoveryOS freight case assembler.

This module packages the proof objects produced by the freight-audit integration
into a deterministic, human-readable review artifact. It is descriptive only:
it does not authorize contact, issue a claim, send a dispute, or assert realized
recovery.

The assembler deliberately consumes RecoveryFinding objects rather than the
legacy Freight FindingFactory truth path, so the imported freight-audit engine
remains inside the shared RecoveryOS proof/authority lifecycle.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from recoveryworks.models import (
    Branch,
    EvidenceRef,
    FindingState,
    RecoveryFinding,
    RuleRef,
    canonical_hash,
    thaw_json,
)

from .freight_audit import (
    FreightAuditDisposition,
    FreightAuditRecoveryMapping,
    MappedFreightAuditFinding,
)

REVIEW_VALIDATED_CANDIDATE = "REVIEW_VALIDATED_CANDIDATE"
RESOLVE_SOURCE_INTEGRITY = "RESOLVE_SOURCE_INTEGRITY"
RESOLVE_AUTHORITY = "RESOLVE_AUTHORITY"
VERIFY_SOURCE_EVIDENCE = "VERIFY_SOURCE_EVIDENCE"
INVESTIGATE_CANDIDATE = "INVESTIGATE_CANDIDATE"


@dataclass(frozen=True)
class FreightCaseEvidence:
    evidence_id: str
    role: str
    kind: str
    source_hash: str
    locator: str
    verified: bool
    evidence_proof_hash: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class FreightCaseAuthority:
    rule_id: str
    rule_proof_hash: str
    source_hash: str
    source_locator: str
    effective_from: str
    effective_to: str | None
    verified_controlling: bool
    charge_code: str | None
    pricing_model: str | None
    authority_document_id: str | None
    authority_document_source_hash: str | None
    fmc_envelope_status: str | None
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class FreightCaseCalculation:
    method: str
    currency: str
    source_invoice_total_cents: int | None
    source_authority_total_cents: int | None
    component_billed_cents: int | None
    component_expected_cents: int | None
    candidate_recovery_cents: int
    expression: str
    calculation_note: str


@dataclass(frozen=True)
class FreightReviewCase:
    case_id: str
    finding_id: str
    finding_proof_hash: str
    reference: str
    client_id: str
    counterparty_id: str
    load_id: str
    invoice_number: str | None
    invoice_load_id: str | None
    rate_confirmation_load_id: str | None
    pod_load_id: str | None
    invoice_carrier_name: str | None
    origin: str | None
    destination: str | None
    service_date: str | None
    finding_type: str
    normalized_category: str | None
    state: str
    action_hint: str
    reason: str
    confidence_basis: str
    original_engine_message: str
    original_engine_impact_cents: int
    calculation: FreightCaseCalculation
    authority: FreightCaseAuthority | None
    evidence: tuple[FreightCaseEvidence, ...]
    integrity_blockers: tuple[str, ...]
    authority_blockers: tuple[str, ...]
    authority_resolution_hash: str | None
    matched_authority_rule_hashes: tuple[str, ...]
    external_action_allowed: bool
    realized_recovery_asserted: bool
    case_hash: str


@dataclass(frozen=True)
class SupplementalFreightFinding:
    index: int
    finding_type: str
    severity: str
    message: str
    original_money_impact_cents: int
    allocated_candidate_cents: int
    normalized_category: str | None
    disposition: str
    suppression_reason: str | None
    candidate_evidence_hash: str
    supplemental_hash: str


@dataclass(frozen=True)
class FreightReviewPacket:
    engine_id: str
    engine_commit: str
    load_id: str
    case_count: int
    supplemental_finding_count: int
    candidate_recovery_cents: int
    validated_candidate_cents: int
    review_candidate_cents: int
    cases: tuple[FreightReviewCase, ...]
    supplemental_findings: tuple[SupplementalFreightFinding, ...]
    packet_hash: str


def _evidence_role(ref: EvidenceRef) -> str:
    if ref.kind == "freight_audit_candidate":
        return "DETECTOR_OUTPUT"
    if ref.kind in {
        "freight_authority_document",
        "freight_authority_envelope",
        "freight_contract_rate_page",
        "freight_contract_rate_query",
        "fmc_tariff_rule_source",
    }:
        return "AUTHORITY"
    return "SOURCE_DOCUMENT"


def _case_evidence(ref: EvidenceRef) -> FreightCaseEvidence:
    return FreightCaseEvidence(
        evidence_id=ref.evidence_id,
        role=_evidence_role(ref),
        kind=ref.kind,
        source_hash=ref.source_hash,
        locator=ref.locator,
        verified=ref.verified,
        evidence_proof_hash=ref.proof_hash,
        metadata=thaw_json(ref.metadata),
    )


def _case_authority(rule: RuleRef | None) -> FreightCaseAuthority | None:
    if rule is None:
        return None
    metadata = thaw_json(rule.metadata)
    return FreightCaseAuthority(
        rule_id=rule.rule_id,
        rule_proof_hash=rule.proof_hash,
        source_hash=rule.source_hash,
        source_locator=rule.source_locator,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
        verified_controlling=rule.verified_controlling,
        charge_code=metadata.get("charge_code"),
        pricing_model=metadata.get("pricing_model"),
        authority_document_id=metadata.get("authority_document_id"),
        authority_document_source_hash=metadata.get("document_source_hash"),
        fmc_envelope_status=metadata.get("fmc_envelope_status"),
        metadata=metadata,
    )


def _component_amounts(
    finding: RecoveryFinding,
) -> tuple[int | None, int | None, str]:
    """Return exact component billed/expected only when deterministic.

    RecoveryOS observations created by the freight-audit adapter intentionally
    store candidate delta semantics (expected=0, actual=allocated delta), so the
    case assembler reconstructs component amounts only from verified rule
    metadata whose pricing model makes the expected amount exact.
    """
    if finding.rule is None:
        return None, None, (
            "Expected component amount is not established because no verified "
            "controlling rule is attached."
        )

    meta = thaw_json(finding.rule.metadata)
    pricing_model = meta.get("pricing_model")
    candidate = finding.potential_recovery_cents

    if pricing_model == "INCLUDED":
        return candidate, 0, (
            "Controlling rule marks this charge as included; component billed "
            "amount equals the candidate overcharge."
        )
    if pricing_model == "FIXED" and type(meta.get("fixed_cents")) is int:
        expected = meta["fixed_cents"]
        return expected + candidate, expected, (
            "Component amount reconstructed from the verified fixed-cent rule "
            "plus the non-overlapping candidate variance."
        )

    return None, None, (
        "The controlling rule is verified, but this packet lacks the exact "
        "quantity/basis required to reconstruct a component billed/expected pair."
    )


def _calculation(finding: RecoveryFinding) -> FreightCaseCalculation:
    meta = thaw_json(finding.metadata)
    candidate = finding.potential_recovery_cents
    component_billed, component_expected, note = _component_amounts(finding)
    source_invoice_total = meta.get("source_invoice_total_cents")
    source_authority_total = meta.get("source_rate_total_cents")

    if component_billed is not None and component_expected is not None:
        method = "COMPONENT_EXPECTED_VS_BILLED"
        expression = (
            f"{component_billed} - {component_expected} = {candidate} cents"
        )
    else:
        method = "NON_OVERLAPPING_CANDIDATE_DELTA"
        expression = (
            f"allocated candidate variance = {candidate} cents "
            "(deduplicated before RecoveryOS evaluation)"
        )

    return FreightCaseCalculation(
        method=method,
        currency=finding.currency,
        source_invoice_total_cents=(
            source_invoice_total if type(source_invoice_total) is int else None
        ),
        source_authority_total_cents=(
            source_authority_total if type(source_authority_total) is int else None
        ),
        component_billed_cents=component_billed,
        component_expected_cents=component_expected,
        candidate_recovery_cents=candidate,
        expression=expression,
        calculation_note=note,
    )


def _action_hint(
    finding: RecoveryFinding,
    integrity_blockers: tuple[str, ...],
    authority_blockers: tuple[str, ...],
) -> str:
    if finding.state is FindingState.VALIDATED:
        return REVIEW_VALIDATED_CANDIDATE
    if integrity_blockers:
        return RESOLVE_SOURCE_INTEGRITY
    if authority_blockers or finding.rule is None:
        return RESOLVE_AUTHORITY
    if not all(ref.verified for ref in finding.evidence):
        return VERIFY_SOURCE_EVIDENCE
    return INVESTIGATE_CANDIDATE


def _mapped_by_reference(
    mapping: FreightAuditRecoveryMapping,
) -> dict[str, MappedFreightAuditFinding]:
    out: dict[str, MappedFreightAuditFinding] = {}
    for item in mapping.mapped_findings:
        if item.observation is None:
            continue
        reference = item.observation.reference
        if reference in out:
            raise ValueError("duplicate mapped RecoveryObservation reference")
        out[reference] = item
    return out


def _validate_finding_binding(
    mapping: FreightAuditRecoveryMapping,
    finding: RecoveryFinding,
    mapped: MappedFreightAuditFinding,
) -> None:
    if finding.branch is not Branch.FREIGHT:
        raise ValueError("case assembler accepts freight findings only")
    if mapped.observation is None:
        raise ValueError("mapped finding has no RecoveryObservation")
    if finding.reference != mapped.observation.reference:
        raise ValueError("finding reference does not match mapped observation")
    if finding.potential_recovery_cents != mapped.allocated_candidate_cents:
        raise ValueError("finding recovery amount does not match mapped allocation")

    metadata = thaw_json(finding.metadata)
    if metadata.get("engine_id") != mapping.engine_id:
        raise ValueError("finding engine_id does not match mapping")
    if metadata.get("engine_commit") != mapping.engine_commit:
        raise ValueError("finding engine_commit does not match mapping")
    if metadata.get("load_id") != mapping.load_id:
        raise ValueError("finding load_id does not match mapping")

    required_proofs = {
        mapped.candidate_evidence.proof_hash,
        *(ref.proof_hash for ref in mapped.source_evidence),
        *(ref.proof_hash for ref in mapped.authority_evidence),
    }
    finding_proofs = {ref.proof_hash for ref in finding.evidence}
    if not required_proofs.issubset(finding_proofs):
        raise ValueError("RecoveryFinding is missing mapped evidence")


def _build_case(
    mapping: FreightAuditRecoveryMapping,
    finding: RecoveryFinding,
    mapped: MappedFreightAuditFinding,
) -> FreightReviewCase:
    _validate_finding_binding(mapping, finding, mapped)
    metadata = thaw_json(finding.metadata)
    integrity_blockers = tuple(str(x) for x in metadata.get("integrity_blockers", ()))
    authority_blockers = tuple(str(x) for x in metadata.get("authority_blockers", ()))
    authority_resolution_hash = metadata.get("authority_resolution_hash")
    evidence = tuple(
        sorted(
            (_case_evidence(ref) for ref in finding.evidence),
            key=lambda item: (item.role, item.kind, item.evidence_id),
        )
    )
    authority = _case_authority(finding.rule)
    calculation = _calculation(finding)

    body = {
        "schema": 1,
        "finding_id": finding.finding_id,
        "finding_proof_hash": finding.proof_hash,
        "reference": finding.reference,
        "client_id": finding.client_id,
        "counterparty_id": finding.counterparty_id,
        "load_id": mapping.load_id,
        "invoice_number": metadata.get("invoice_number"),
        "invoice_load_id": metadata.get("invoice_load_id"),
        "rate_confirmation_load_id": metadata.get("rate_confirmation_load_id"),
        "pod_load_id": metadata.get("pod_load_id"),
        "invoice_carrier_name": metadata.get("invoice_carrier_name"),
        "origin": metadata.get("origin"),
        "destination": metadata.get("destination"),
        "service_date": metadata.get("service_date"),
        "finding_type": mapped.finding_type.value,
        "normalized_category": mapped.normalized_category,
        "state": finding.state.value,
        "action_hint": _action_hint(
            finding,
            integrity_blockers,
            authority_blockers,
        ),
        "reason": finding.reason,
        "confidence_basis": finding.confidence_basis,
        "original_engine_message": mapped.message,
        "original_engine_impact_cents": mapped.original_money_impact_cents,
        "calculation": asdict(calculation),
        "authority": asdict(authority) if authority else None,
        "evidence": [asdict(item) for item in evidence],
        "integrity_blockers": list(integrity_blockers),
        "authority_blockers": list(authority_blockers),
        "authority_resolution_hash": authority_resolution_hash,
        "matched_authority_rule_hashes": list(
            metadata.get("matched_authority_rule_hashes", ())
        ),
        "external_action_allowed": False,
        "realized_recovery_asserted": False,
    }
    case_hash = canonical_hash(body)
    return FreightReviewCase(
        case_id="freight-case:" + case_hash,
        finding_id=finding.finding_id,
        finding_proof_hash=finding.proof_hash,
        reference=finding.reference,
        client_id=finding.client_id,
        counterparty_id=finding.counterparty_id,
        load_id=mapping.load_id,
        invoice_number=(
            str(metadata.get("invoice_number"))
            if metadata.get("invoice_number") is not None else None
        ),
        invoice_load_id=(
            str(metadata.get("invoice_load_id"))
            if metadata.get("invoice_load_id") is not None else None
        ),
        rate_confirmation_load_id=(
            str(metadata.get("rate_confirmation_load_id"))
            if metadata.get("rate_confirmation_load_id") is not None else None
        ),
        pod_load_id=(
            str(metadata.get("pod_load_id"))
            if metadata.get("pod_load_id") is not None else None
        ),
        invoice_carrier_name=(
            str(metadata.get("invoice_carrier_name"))
            if metadata.get("invoice_carrier_name") is not None else None
        ),
        origin=(
            str(metadata.get("origin"))
            if metadata.get("origin") is not None else None
        ),
        destination=(
            str(metadata.get("destination"))
            if metadata.get("destination") is not None else None
        ),
        service_date=(
            str(metadata.get("service_date"))
            if metadata.get("service_date") is not None else None
        ),
        finding_type=mapped.finding_type.value,
        normalized_category=mapped.normalized_category,
        state=finding.state.value,
        action_hint=body["action_hint"],
        reason=finding.reason,
        confidence_basis=finding.confidence_basis,
        original_engine_message=mapped.message,
        original_engine_impact_cents=mapped.original_money_impact_cents,
        calculation=calculation,
        authority=authority,
        evidence=evidence,
        integrity_blockers=integrity_blockers,
        authority_blockers=authority_blockers,
        authority_resolution_hash=(
            str(authority_resolution_hash)
            if authority_resolution_hash is not None else None
        ),
        matched_authority_rule_hashes=tuple(
            str(item)
            for item in metadata.get("matched_authority_rule_hashes", ())
        ),
        external_action_allowed=False,
        realized_recovery_asserted=False,
        case_hash=case_hash,
    )


def _supplemental(
    item: MappedFreightAuditFinding,
) -> SupplementalFreightFinding:
    body = {
        "schema": 1,
        "index": item.index,
        "finding_type": item.finding_type.value,
        "severity": item.severity.value,
        "message": item.message,
        "original_money_impact_cents": item.original_money_impact_cents,
        "allocated_candidate_cents": item.allocated_candidate_cents,
        "normalized_category": item.normalized_category,
        "disposition": item.disposition.value,
        "suppression_reason": item.suppression_reason,
        "candidate_evidence_hash": item.candidate_evidence.proof_hash,
    }
    return SupplementalFreightFinding(
        index=item.index,
        finding_type=item.finding_type.value,
        severity=item.severity.value,
        message=item.message,
        original_money_impact_cents=item.original_money_impact_cents,
        allocated_candidate_cents=item.allocated_candidate_cents,
        normalized_category=item.normalized_category,
        disposition=item.disposition.value,
        suppression_reason=item.suppression_reason,
        candidate_evidence_hash=item.candidate_evidence.proof_hash,
        supplemental_hash=canonical_hash(body),
    )


def build_freight_review_packet(
    mapping: FreightAuditRecoveryMapping,
    findings: tuple[RecoveryFinding, ...],
) -> FreightReviewPacket:
    """Assemble all RecoveryOS freight cases plus non-money/suppressed context."""
    by_reference = _mapped_by_reference(mapping)
    case_list: list[FreightReviewCase] = []
    seen_findings: set[str] = set()

    for finding in findings:
        if finding.finding_id in seen_findings:
            raise ValueError("duplicate RecoveryFinding")
        seen_findings.add(finding.finding_id)
        mapped = by_reference.get(finding.reference)
        if mapped is None:
            raise ValueError("RecoveryFinding is not part of this freight mapping")
        case_list.append(_build_case(mapping, finding, mapped))

    expected_references = set(by_reference)
    supplied_references = {finding.reference for finding in findings}
    if supplied_references != expected_references:
        missing = sorted(expected_references - supplied_references)
        extra = sorted(supplied_references - expected_references)
        raise ValueError(
            "RecoveryFinding set does not match mapping observations; "
            f"missing={missing}; extra={extra}"
        )

    cases = tuple(sorted(case_list, key=lambda case: case.reference))
    supplemental = tuple(
        _supplemental(item)
        for item in mapping.mapped_findings
        if item.observation is None
    )

    candidate_total = sum(case.calculation.candidate_recovery_cents for case in cases)
    if candidate_total != mapping.candidate_recovery_cents:
        raise ValueError("assembled case total does not match mapped candidate total")

    validated_total = sum(
        case.calculation.candidate_recovery_cents
        for case in cases
        if case.state == FindingState.VALIDATED.value
    )
    review_total = candidate_total - validated_total

    body = {
        "schema": 1,
        "engine_id": mapping.engine_id,
        "engine_commit": mapping.engine_commit,
        "load_id": mapping.load_id,
        "case_count": len(cases),
        "supplemental_finding_count": len(supplemental),
        "candidate_recovery_cents": candidate_total,
        "validated_candidate_cents": validated_total,
        "review_candidate_cents": review_total,
        "cases": [asdict(case) for case in cases],
        "supplemental_findings": [asdict(item) for item in supplemental],
    }
    return FreightReviewPacket(
        engine_id=mapping.engine_id,
        engine_commit=mapping.engine_commit,
        load_id=mapping.load_id,
        case_count=len(cases),
        supplemental_finding_count=len(supplemental),
        candidate_recovery_cents=candidate_total,
        validated_candidate_cents=validated_total,
        review_candidate_cents=review_total,
        cases=cases,
        supplemental_findings=supplemental,
        packet_hash=canonical_hash(body),
    )


def verify_freight_review_packet(packet: FreightReviewPacket) -> None:
    """Recompute every case hash and the outer packet hash."""
    for case in packet.cases:
        case_body = {
            "schema": 1,
            "finding_id": case.finding_id,
            "finding_proof_hash": case.finding_proof_hash,
            "reference": case.reference,
            "client_id": case.client_id,
            "counterparty_id": case.counterparty_id,
            "load_id": case.load_id,
            "invoice_number": case.invoice_number,
            "invoice_load_id": case.invoice_load_id,
            "rate_confirmation_load_id": case.rate_confirmation_load_id,
            "pod_load_id": case.pod_load_id,
            "invoice_carrier_name": case.invoice_carrier_name,
            "origin": case.origin,
            "destination": case.destination,
            "service_date": case.service_date,
            "finding_type": case.finding_type,
            "normalized_category": case.normalized_category,
            "state": case.state,
            "action_hint": case.action_hint,
            "reason": case.reason,
            "confidence_basis": case.confidence_basis,
            "original_engine_message": case.original_engine_message,
            "original_engine_impact_cents": case.original_engine_impact_cents,
            "calculation": asdict(case.calculation),
            "authority": asdict(case.authority) if case.authority else None,
            "evidence": [asdict(item) for item in case.evidence],
            "integrity_blockers": list(case.integrity_blockers),
            "authority_blockers": list(case.authority_blockers),
            "authority_resolution_hash": case.authority_resolution_hash,
            "matched_authority_rule_hashes": list(case.matched_authority_rule_hashes),
            "external_action_allowed": case.external_action_allowed,
            "realized_recovery_asserted": case.realized_recovery_asserted,
        }
        expected_case_hash = canonical_hash(case_body)
        if expected_case_hash != case.case_hash:
            raise ValueError("freight review case hash mismatch: " + case.case_id)
        if case.case_id != "freight-case:" + expected_case_hash:
            raise ValueError("freight review case id/hash mismatch: " + case.case_id)

    packet_body = {
        "schema": 1,
        "engine_id": packet.engine_id,
        "engine_commit": packet.engine_commit,
        "load_id": packet.load_id,
        "case_count": packet.case_count,
        "supplemental_finding_count": packet.supplemental_finding_count,
        "candidate_recovery_cents": packet.candidate_recovery_cents,
        "validated_candidate_cents": packet.validated_candidate_cents,
        "review_candidate_cents": packet.review_candidate_cents,
        "cases": [asdict(case) for case in packet.cases],
        "supplemental_findings": [asdict(item) for item in packet.supplemental_findings],
    }
    if canonical_hash(packet_body) != packet.packet_hash:
        raise ValueError("freight review packet hash mismatch")


def freight_review_packet_as_dict(packet: FreightReviewPacket) -> dict[str, Any]:
    return asdict(packet)


def _money(currency: str, cents: int | None) -> str:
    if cents is None:
        return "Not established"
    return f"{currency} {cents / 100:,.2f}"


def render_freight_review_packet_markdown(packet: FreightReviewPacket) -> str:
    packet_currency = packet.cases[0].calculation.currency if packet.cases else "USD"
    lines = [
        "# RecoveryOS — Freight Evidence Packet",
        "",
        f"- Load: `{packet.load_id}`",
        f"- Engine revision: `{packet.engine_commit}`",
        f"- Case count: **{packet.case_count}**",
        f"- Candidate total: **{_money(packet_currency, packet.candidate_recovery_cents)}**",
        f"- Validated candidate total: **{_money(packet_currency, packet.validated_candidate_cents)}**",
        f"- Review-state candidate total: **{_money(packet_currency, packet.review_candidate_cents)}**",
        f"- Packet hash: `{packet.packet_hash}`",
        "",
        "These are reviewer work items, not realized recoveries and not authorization to contact a counterparty.",
        "",
    ]

    for position, case in enumerate(packet.cases, 1):
        currency = case.calculation.currency
        lines.extend([
            f"## {position}. {case.finding_type} — {case.state}",
            "",
            f"- Case: `{case.case_id}`",
            f"- Finding: `{case.finding_id}`",
            f"- Required action: **{case.action_hint}**",
            f"- Invoice: **{case.invoice_number or 'not established'}**",
            f"- Canonical load: **{case.load_id}**",
            f"- Invoice load ID: **{case.invoice_load_id or 'not established'}**",
            f"- Rate-confirmation load ID: **{case.rate_confirmation_load_id or 'not established'}**",
            f"- POD load ID: **{case.pod_load_id or 'not established'}**",
            f"- Carrier: **{case.invoice_carrier_name or case.counterparty_id}**",
            f"- Lane: **{case.origin or 'unknown'} → {case.destination or 'unknown'}**",
            f"- Service date: **{case.service_date or 'not established'}**",
            f"- Category: **{case.normalized_category or 'unclassified'}**",
            f"- Candidate recovery: **{_money(currency, case.calculation.candidate_recovery_cents)}**",
            f"- Component billed: **{_money(currency, case.calculation.component_billed_cents)}**",
            f"- Component expected: **{_money(currency, case.calculation.component_expected_cents)}**",
            f"- Source invoice total: **{_money(currency, case.calculation.source_invoice_total_cents)}**",
            f"- Source authority/rate total: **{_money(currency, case.calculation.source_authority_total_cents)}**",
            f"- Calculation: `{case.calculation.expression}`",
            f"- Engine finding: {case.original_engine_message}",
            f"- Confidence basis: {case.confidence_basis}",
        ])

        if case.integrity_blockers:
            lines.append("- Integrity blockers: **" + ", ".join(case.integrity_blockers) + "**")
        if case.authority_blockers:
            lines.append("- Authority blockers: **" + ", ".join(case.authority_blockers) + "**")
        if case.matched_authority_rule_hashes:
            lines.append(
                "- Matched authority rule hashes: "
                + ", ".join(f"`{item}`" for item in case.matched_authority_rule_hashes)
            )

        lines.extend(["", "### Governing authority"])
        if case.authority is None:
            lines.append("- No verified controlling authority is attached.")
        else:
            lines.extend([
                f"- Rule: `{case.authority.rule_id}`",
                f"- Effective: **{case.authority.effective_from} to {case.authority.effective_to or 'open-ended'}**",
                f"- Charge code: **{case.authority.charge_code or 'not specified'}**",
                f"- Pricing model: **{case.authority.pricing_model or 'not specified'}**",
                f"- Source hash: `{case.authority.source_hash}`",
                f"- Rule proof: `{case.authority.rule_proof_hash}`",
            ])
            if case.authority.fmc_envelope_status:
                lines.append(
                    f"- FMC authority envelope: **{case.authority.fmc_envelope_status}**"
                )

        lines.extend(["", "### Evidence"])
        for evidence in case.evidence:
            status = "verified" if evidence.verified else "unverified"
            lines.append(
                f"- **{evidence.role} / {evidence.kind}** — {status} — "
                f"`{evidence.source_hash}` — {evidence.locator}"
            )
        lines.append("")

    if packet.supplemental_findings:
        lines.extend([
            "## Supplemental / non-counted findings",
            "",
            "These findings are retained for context but do not add to candidate recovery totals.",
            "",
        ])
        for item in packet.supplemental_findings:
            reason = f" — {item.suppression_reason}" if item.suppression_reason else ""
            lines.append(
                f"- **{item.finding_type}** / {item.disposition}: "
                f"{item.message}{reason}"
            )

    return "\\n".join(lines)


__all__ = [
    "FreightCaseAuthority",
    "FreightCaseCalculation",
    "FreightCaseEvidence",
    "FreightReviewCase",
    "FreightReviewPacket",
    "SupplementalFreightFinding",
    "build_freight_review_packet",
    "freight_review_packet_as_dict",
    "render_freight_review_packet_markdown",
    "verify_freight_review_packet",
]
