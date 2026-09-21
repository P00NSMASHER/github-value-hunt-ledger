"""Single-call deterministic audit workflow for Freight Recovery.

This module composes the controlled pre-review audit path:
invoice CSV -> frozen population -> rule CSVs -> Finding Factory -> review queue
-> reviewer packet -> canonical audit-run manifest.

It does not perform buyer review, external carrier action, or settlement.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from freight.audit_run_manifest import AuditRunManifest, build_audit_run_manifest
from freight.finding_factory import FindingFactoryBatch, REVIEW, VALIDATED, derive_batch
from freight.invoice_csv_adapter import InvoiceChargeCSVBatch, parse_invoice_charge_csv
from freight.population_builder import PopulationBuild, build_population_from_charge_batch
from freight.review_packet import ReviewPacket, build_review_packet
from freight.review_queue import ReviewQueue, build_review_queue
from freight.review_routing import ReviewRouting, route_review_packet
from freight.rule_csv_adapter import ChargeRuleCSVBatch, parse_charge_rule_csv


class AuditWorkflowState(str, Enum):
    CLEAN = "CLEAN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


class AuditWorkflowStage(str, Enum):
    INVOICE_INGEST = "INVOICE_INGEST"
    POPULATION_FREEZE = "POPULATION_FREEZE"
    RULE_INGEST = "RULE_INGEST"
    FINDING_DERIVATION = "FINDING_DERIVATION"
    REVIEW_QUEUE = "REVIEW_QUEUE"
    REVIEW_PACKET = "REVIEW_PACKET"
    REVIEW_ROUTING = "REVIEW_ROUTING"
    RUN_MANIFEST = "RUN_MANIFEST"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class RuleCSVInput:
    filename: str
    data: bytes
    customer_id: str
    carrier_id: str
    currency: str
    authority_document_id: str
    source_document_sha256: str | None
    verified_controlling_authority: bool
    source_document_data: bytes | None = None


@dataclass(frozen=True)
class CurrencyDiscrepancy:
    currency: str
    validated_discrepancy_cents: int
    review_discrepancy_cents: int


@dataclass(frozen=True)
class AuditWorkflowArtifacts:
    invoice_batch: InvoiceChargeCSVBatch
    population_build: PopulationBuild
    rule_batches: tuple[ChargeRuleCSVBatch, ...]
    factory: FindingFactoryBatch
    review_queue: ReviewQueue
    review_packet: ReviewPacket
    review_routing: ReviewRouting
    manifest: AuditRunManifest


@dataclass(frozen=True)
class AuditWorkflowSummary:
    buyer_id: str
    business_unit: str
    state: str
    run_hash: str
    charge_count: int
    invoice_count: int
    rule_count: int
    clear_count: int
    validated_finding_count: int
    review_finding_count: int
    review_case_count: int
    review_route: str
    buyer_review_case_count: int
    evidence_remediation_case_count: int
    rerun_required: bool
    review_routing_hash: str
    currency_discrepancies: tuple[CurrencyDiscrepancy, ...]
    summary_currency: str | None
    validated_discrepancy_cents: int | None
    review_discrepancy_cents: int | None
    unknown_expected_count: int


@dataclass(frozen=True)
class AuditWorkflowResult:
    state: str
    stage: str
    error_code: str | None
    error_message: str | None
    summary: AuditWorkflowSummary | None
    artifacts: AuditWorkflowArtifacts | None


def _source_document_sha256(spec: RuleCSVInput) -> str:
    if spec.source_document_data is not None:
        if not isinstance(spec.source_document_data, (bytes, bytearray)):
            raise ValueError("source_document_data must be bytes")
        computed = hashlib.sha256(bytes(spec.source_document_data)).hexdigest()
        if spec.source_document_sha256 is not None and spec.source_document_sha256 != computed:
            raise ValueError("source_document_sha256 does not match source_document_data")
        return computed
    if spec.source_document_sha256 is None:
        raise ValueError("source_document_sha256 or source_document_data is required")
    return spec.source_document_sha256


def _blocked(stage: AuditWorkflowStage, code: str, exc: ValueError) -> AuditWorkflowResult:
    return AuditWorkflowResult(
        state=AuditWorkflowState.BLOCKED.value,
        stage=stage.value,
        error_code=code,
        error_message=str(exc),
        summary=None,
        artifacts=None,
    )


def _summary(
    *,
    state: AuditWorkflowState,
    manifest: AuditRunManifest,
    invoice_batch: InvoiceChargeCSVBatch,
    factory: FindingFactoryBatch,
    review_routing: ReviewRouting,
) -> AuditWorkflowSummary:
    validated_findings = [f for f in factory.truth.findings if f.status == VALIDATED]
    review_findings = [f for f in factory.truth.findings if f.status == REVIEW]
    currency_by_charge = {charge.charge_id: charge.currency for charge in invoice_batch.charges}
    totals: dict[str, dict[str, int]] = {
        currency: {"validated": 0, "review": 0}
        for currency in sorted(set(currency_by_charge.values()))
    }
    for item in factory.derivations:
        currency = currency_by_charge[item.charge_id]
        if item.decision == VALIDATED:
            totals[currency]["validated"] += item.variance_cents or 0
        elif item.decision == REVIEW and item.expected_cents is not None:
            totals[currency]["review"] += item.variance_cents or 0

    currency_discrepancies = tuple(
        CurrencyDiscrepancy(
            currency=currency,
            validated_discrepancy_cents=totals[currency]["validated"],
            review_discrepancy_cents=totals[currency]["review"],
        )
        for currency in sorted(totals)
    )
    summary_currency = (
        currency_discrepancies[0].currency
        if len(currency_discrepancies) == 1
        else None
    )
    single = currency_discrepancies[0] if summary_currency is not None else None
    unknown_expected = sum(
        item.expected_cents is None
        for item in factory.derivations
        if item.decision == REVIEW
    )
    return AuditWorkflowSummary(
        buyer_id=manifest.buyer_id,
        business_unit=manifest.business_unit,
        state=state.value,
        run_hash=manifest.run_hash,
        charge_count=manifest.charge_count,
        invoice_count=manifest.invoice_count,
        rule_count=manifest.rule_count,
        clear_count=factory.clear_count,
        validated_finding_count=len(validated_findings),
        review_finding_count=len(review_findings),
        review_case_count=manifest.review_case_count,
        review_route=review_routing.route,
        buyer_review_case_count=review_routing.buyer_review_case_count,
        evidence_remediation_case_count=review_routing.evidence_remediation_case_count,
        rerun_required=review_routing.rerun_required,
        review_routing_hash=review_routing.routing_hash,
        currency_discrepancies=currency_discrepancies,
        summary_currency=summary_currency,
        validated_discrepancy_cents=(
            single.validated_discrepancy_cents if single is not None else None
        ),
        review_discrepancy_cents=(
            single.review_discrepancy_cents if single is not None else None
        ),
        unknown_expected_count=unknown_expected,
    )


def run_audit_workflow(
    *,
    invoice_filename: str,
    invoice_data: bytes,
    buyer_id: str,
    business_unit: str,
    selection_rule: str,
    rule_inputs: Iterable[RuleCSVInput] = (),
) -> AuditWorkflowResult:
    try:
        invoice_batch = parse_invoice_charge_csv(
            filename=invoice_filename,
            data=invoice_data,
            buyer_id=buyer_id,
            business_unit=business_unit,
        )
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.INVOICE_INGEST, "INVOICE_INGEST_FAILED", exc)

    try:
        population_build = build_population_from_charge_batch(
            invoice_batch,
            selection_rule=selection_rule,
        )
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.POPULATION_FREEZE, "POPULATION_FREEZE_FAILED", exc)

    rule_batches: list[ChargeRuleCSVBatch] = []
    for index, spec in enumerate(tuple(rule_inputs), 1):
        try:
            batch = parse_charge_rule_csv(
                filename=spec.filename,
                data=spec.data,
                buyer_id=invoice_batch.buyer_id,
                business_unit=invoice_batch.business_unit,
                customer_id=spec.customer_id,
                carrier_id=spec.carrier_id,
                currency=spec.currency,
                authority_document_id=spec.authority_document_id,
                source_document_sha256=_source_document_sha256(spec),
                verified_controlling_authority=spec.verified_controlling_authority,
            )
        except ValueError as exc:
            return _blocked(
                AuditWorkflowStage.RULE_INGEST,
                "RULE_INGEST_FAILED",
                ValueError(f"rule batch {index}: {exc}"),
            )
        rule_batches.append(batch)

    rules = tuple(rule for batch in rule_batches for rule in batch.rules)
    try:
        factory = derive_batch(
            population_build.population,
            invoice_batch.charges,
            rules,
        )
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.FINDING_DERIVATION, "FINDING_DERIVATION_FAILED", exc)

    try:
        review_queue = build_review_queue(factory)
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.REVIEW_QUEUE, "REVIEW_QUEUE_FAILED", exc)

    try:
        review_packet = build_review_packet(
            factory,
            review_queue,
            invoice_batch.charges,
            rules,
        )
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.REVIEW_PACKET, "REVIEW_PACKET_FAILED", exc)

    try:
        review_routing = route_review_packet(review_packet)
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.REVIEW_ROUTING, "REVIEW_ROUTING_FAILED", exc)

    try:
        manifest = build_audit_run_manifest(
            invoice_batch=invoice_batch,
            population_build=population_build,
            rule_batches=tuple(rule_batches),
            factory=factory,
            review_queue=review_queue,
            review_packet=review_packet,
        )
    except ValueError as exc:
        return _blocked(AuditWorkflowStage.RUN_MANIFEST, "RUN_MANIFEST_FAILED", exc)

    state = (
        AuditWorkflowState.CLEAN
        if manifest.review_case_count == 0
        else AuditWorkflowState.REVIEW_REQUIRED
    )
    artifacts = AuditWorkflowArtifacts(
        invoice_batch=invoice_batch,
        population_build=population_build,
        rule_batches=tuple(rule_batches),
        factory=factory,
        review_queue=review_queue,
        review_packet=review_packet,
        review_routing=review_routing,
        manifest=manifest,
    )
    return AuditWorkflowResult(
        state=state.value,
        stage=AuditWorkflowStage.COMPLETE.value,
        error_code=None,
        error_message=None,
        summary=_summary(
            state=state,
            manifest=manifest,
            invoice_batch=invoice_batch,
            factory=factory,
            review_routing=review_routing,
        ),
        artifacts=artifacts,
    )


def render_workflow_summary(result: AuditWorkflowResult) -> str:
    if result.state == AuditWorkflowState.BLOCKED.value:
        return "\n".join([
            "# Freight Recovery — Audit Workflow",
            "",
            f"- State: **{result.state}**",
            f"- Blocked stage: **{result.stage}**",
            f"- Error code: **{result.error_code}**",
            f"- Reason: {result.error_message}",
            "",
            "No audit-run manifest was issued.",
            "",
        ])

    assert result.summary is not None
    summary = result.summary
    return "\n".join([
        "# Freight Recovery — Audit Workflow",
        "",
        f"- State: **{summary.state}**",
        f"- Buyer: **{summary.buyer_id}**",
        f"- Business unit: **{summary.business_unit}**",
        f"- Audit run: `{summary.run_hash}`",
        "",
        "## Scope",
        f"- Invoice/shipment rows: **{summary.invoice_count}**",
        f"- Charge rows: **{summary.charge_count}**",
        f"- Normalized rules: **{summary.rule_count}**",
        "",
        "## Audit result",
        f"- Clear charges: **{summary.clear_count}**",
        f"- Validated findings requiring human review: **{summary.validated_finding_count}**",
        f"- Review findings: **{summary.review_finding_count}**",
        f"- Reviewer work cases: **{summary.review_case_count}**",
        f"- Review route: **{summary.review_route}**",
        f"- Buyer-review-ready cases: **{summary.buyer_review_case_count}**",
        f"- Evidence-remediation cases: **{summary.evidence_remediation_case_count}**",
        "- Rerun required for remediation cases: **" + ("yes" if summary.rerun_required else "no") + "**",
        f"- Review routing hash: `{summary.review_routing_hash}`",
        f"- Review cases without an established expected amount: **{summary.unknown_expected_count}**",
        "",
        "## Discrepancy by currency",
        *[
            "- " + item.currency
            + " — Validated discrepancy: **"
            + item.currency + " " + format(item.validated_discrepancy_cents / 100, ",.2f")
            + "**; review discrepancy with a calculable expected amount: **"
            + item.currency + " " + format(item.review_discrepancy_cents / 100, ",.2f")
            + "**"
            for item in summary.currency_discrepancies
        ],
        "",
        "Discrepancy amounts are not realized savings. Human review and later settlement proof remain separate.",
        "",
    ])
