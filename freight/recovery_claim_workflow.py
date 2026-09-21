"""Deterministic recovery-claim issuance from proof-bound buyer reviews.

Only CONFIRMED buyer-review-ready findings become recovery claims. False-positive
and unresolved reviews never produce claims. Incumbent-preidentified findings
are fee-disqualified automatically from the sealed incumbent output; callers do
not choose that flag.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum

from freight.buyer_review_workflow import (
    BuyerReviewBatch,
    BuyerReviewDecisionInput,
    BuyerReviewState,
    build_buyer_review_batch,
)
from freight.contracts import IncumbentOutput, TruthManifest, VALIDATED, canonical_hash
from freight.pilot_reporting import ReviewDisposition
from freight.review_packet import ReviewPacket
from freight.review_routing import ReviewRouting
from freight.settlement_report import ClaimFindingBinding
from freight.settlement_store import RecoveryClaim, SettlementStore


class RecoveryClaimBatchState(str, Enum):
    NO_CONFIRMED_CLAIMS = "NO_CONFIRMED_CLAIMS"
    CLAIMS_READY = "CLAIMS_READY"


@dataclass(frozen=True)
class RecoveryClaimRecord:
    claim_id: str
    finding_id: str
    finding_proof_hash: str
    review_hash: str
    reference: str
    payer_id: str
    payee_id: str
    currency: str
    amount_cents: int
    issued_at: str
    incumbent_preidentified: bool
    fee_disqualified: bool
    record_hash: str


@dataclass(frozen=True)
class RecoveryClaimPersistenceReceipt:
    buyer_id: str
    business_unit: str
    claim_batch_hash: str
    attempted_claim_count: int
    created_claim_count: int
    already_present_count: int
    claim_ids: tuple[str, ...]
    receipt_hash: str


@dataclass(frozen=True)
class RecoveryClaimBatch:
    buyer_id: str
    business_unit: str
    truth_hash: str
    incumbent_output_hash: str
    buyer_review_batch_hash: str
    issued_at: str
    state: str
    confirmed_review_count: int
    claim_count: int
    fee_disqualified_count: int
    records: tuple[RecoveryClaimRecord, ...]
    claims: tuple[RecoveryClaim, ...]
    bindings: tuple[ClaimFindingBinding, ...]
    batch_hash: str


def _timestamp(value: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("issued_at is required")
    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("issued_at must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("issued_at must be timezone-aware ISO-8601")
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return canonical, parsed


def _verify_incumbent(truth: TruthManifest, incumbent: IncumbentOutput) -> None:
    if (incumbent.buyer_id, incumbent.business_unit) != (
        truth.buyer_id,
        truth.business_unit,
    ):
        raise ValueError("incumbent output scope mismatch")
    if incumbent.truth_hash != truth.truth_hash:
        raise ValueError("incumbent output truth hash mismatch")
    if incumbent.population_hash != truth.population_hash:
        raise ValueError("incumbent output population hash mismatch")
    body = {"schema": 2, **asdict(incumbent)}
    body.pop("output_hash")
    if canonical_hash(body) != incumbent.output_hash:
        raise ValueError("incumbent output hash mismatch")
    finding_ids = {finding.finding_id for finding in truth.findings}
    unknown = sorted(set(incumbent.finding_ids) - finding_ids)
    if unknown:
        raise ValueError("incumbent output references unknown finding: " + unknown[0])


def _verify_buyer_review_batch(
    *,
    batch: BuyerReviewBatch,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    truth: TruthManifest,
) -> None:
    decisions = tuple(
        BuyerReviewDecisionInput(
            case_hash=record.case_hash,
            disposition=ReviewDisposition(record.disposition),
            reviewer_minutes=record.reviewer_minutes,
            reviewed_at=record.reviewed_at,
        )
        for record in batch.records
    )
    expected = build_buyer_review_batch(
        review_packet=review_packet,
        review_routing=review_routing,
        truth=truth,
        reviewer_role=batch.reviewer_role,
        decisions=decisions,
    )
    if expected != batch:
        raise ValueError("buyer review batch does not match current review proofs")


def build_recovery_claim_batch(
    *,
    truth: TruthManifest,
    incumbent: IncumbentOutput,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    buyer_review: BuyerReviewBatch,
    issued_at: str,
) -> RecoveryClaimBatch:
    _verify_buyer_review_batch(
        batch=buyer_review,
        review_packet=review_packet,
        review_routing=review_routing,
        truth=truth,
    )
    _verify_incumbent(truth, incumbent)

    if buyer_review.state == BuyerReviewState.PARTIAL.value:
        raise ValueError("buyer review must be COMPLETE before recovery claim issuance")
    if buyer_review.truth_hash != truth.truth_hash:
        raise ValueError("buyer review truth hash mismatch")

    canonical_issued_at, issued_dt = _timestamp(issued_at)
    finding_index = {finding.finding_id: finding for finding in truth.findings}
    incumbent_ids = set(incumbent.finding_ids)

    records: list[RecoveryClaimRecord] = []
    claims: list[RecoveryClaim] = []
    bindings: list[ClaimFindingBinding] = []

    for review_record, finding_review in zip(
        buyer_review.records,
        buyer_review.finding_reviews,
        strict=True,
    ):
        if review_record.review_hash != finding_review.review_hash:
            raise ValueError("buyer review record/review hash mismatch")
        if review_record.disposition != finding_review.disposition.value:
            raise ValueError("buyer review record disposition mismatch")

        review_time = datetime.fromisoformat(
            review_record.reviewed_at.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if issued_dt < review_time:
            raise ValueError("recovery claim cannot be issued before buyer review")

        if finding_review.disposition is not ReviewDisposition.CONFIRMED:
            continue

        finding = finding_index.get(review_record.finding_id)
        if finding is None:
            raise ValueError("confirmed buyer review references unknown finding")
        if finding.status != VALIDATED or finding.validated_cents <= 0:
            raise ValueError("recovery claim requires a positive VALIDATED finding")
        if finding.proof_hash != review_record.finding_proof_hash:
            raise ValueError("confirmed buyer review proof does not match finding")

        fee_disqualified = finding.finding_id in incumbent_ids
        claim_id = "claim:" + finding.proof_hash
        claim = RecoveryClaim(
            claim_id=claim_id,
            reference=finding.invoice_id,
            payer_id=finding.carrier_id,
            payee_id=finding.customer_id,
            currency=finding.currency,
            amount_cents=finding.validated_cents,
            issued_at=canonical_issued_at,
            source_hash=finding.proof_hash,
            fee_disqualified=fee_disqualified,
        )
        binding = ClaimFindingBinding(
            claim_id=claim_id,
            finding_id=finding.finding_id,
            finding_proof_hash=finding.proof_hash,
        )
        record_body = {
            "schema": 1,
            "truth_hash": truth.truth_hash,
            "incumbent_output_hash": incumbent.output_hash,
            "buyer_review_batch_hash": buyer_review.batch_hash,
            "claim_id": claim_id,
            "finding_id": finding.finding_id,
            "finding_proof_hash": finding.proof_hash,
            "review_hash": review_record.review_hash,
            "reference": finding.invoice_id,
            "payer_id": finding.carrier_id,
            "payee_id": finding.customer_id,
            "currency": finding.currency,
            "amount_cents": finding.validated_cents,
            "issued_at": canonical_issued_at,
            "incumbent_preidentified": fee_disqualified,
            "fee_disqualified": fee_disqualified,
        }
        records.append(RecoveryClaimRecord(
            claim_id=claim_id,
            finding_id=finding.finding_id,
            finding_proof_hash=finding.proof_hash,
            review_hash=review_record.review_hash,
            reference=finding.invoice_id,
            payer_id=finding.carrier_id,
            payee_id=finding.customer_id,
            currency=finding.currency,
            amount_cents=finding.validated_cents,
            issued_at=canonical_issued_at,
            incumbent_preidentified=fee_disqualified,
            fee_disqualified=fee_disqualified,
            record_hash=canonical_hash(record_body),
        ))
        claims.append(claim)
        bindings.append(binding)

    records_tuple = tuple(records)
    claims_tuple = tuple(claims)
    bindings_tuple = tuple(bindings)
    state = (
        RecoveryClaimBatchState.CLAIMS_READY
        if claims_tuple
        else RecoveryClaimBatchState.NO_CONFIRMED_CLAIMS
    )
    body = {
        "schema": 1,
        "buyer_id": truth.buyer_id,
        "business_unit": truth.business_unit,
        "truth_hash": truth.truth_hash,
        "incumbent_output_hash": incumbent.output_hash,
        "buyer_review_batch_hash": buyer_review.batch_hash,
        "issued_at": canonical_issued_at,
        "state": state.value,
        "confirmed_review_count": buyer_review.confirmed_count,
        "claim_count": len(claims_tuple),
        "fee_disqualified_count": sum(record.fee_disqualified for record in records_tuple),
        "records": [asdict(record) for record in records_tuple],
        "bindings": [asdict(binding) for binding in bindings_tuple],
    }
    return RecoveryClaimBatch(
        buyer_id=truth.buyer_id,
        business_unit=truth.business_unit,
        truth_hash=truth.truth_hash,
        incumbent_output_hash=incumbent.output_hash,
        buyer_review_batch_hash=buyer_review.batch_hash,
        issued_at=canonical_issued_at,
        state=state.value,
        confirmed_review_count=buyer_review.confirmed_count,
        claim_count=len(claims_tuple),
        fee_disqualified_count=sum(record.fee_disqualified for record in records_tuple),
        records=records_tuple,
        claims=claims_tuple,
        bindings=bindings_tuple,
        batch_hash=canonical_hash(body),
    )





def _verify_recovery_claim_batch(batch: RecoveryClaimBatch) -> None:
    if not isinstance(batch, RecoveryClaimBatch):
        raise ValueError("batch must be a RecoveryClaimBatch")
    if not (
        len(batch.records) == len(batch.claims) == len(batch.bindings) == batch.claim_count
    ):
        raise ValueError("recovery claim batch cardinality mismatch")

    for record, claim, binding in zip(
        batch.records,
        batch.claims,
        batch.bindings,
        strict=True,
    ):
        if (
            record.claim_id != claim.claim_id
            or record.claim_id != binding.claim_id
            or record.finding_id != binding.finding_id
            or record.finding_proof_hash != binding.finding_proof_hash
            or record.finding_proof_hash != claim.source_hash
        ):
            raise ValueError("recovery claim record/claim/binding mismatch")
        if (
            record.reference != claim.reference
            or record.payer_id != claim.payer_id
            or record.payee_id != claim.payee_id
            or record.currency != claim.currency
            or record.amount_cents != claim.amount_cents
            or record.issued_at != claim.issued_at
            or record.fee_disqualified != claim.fee_disqualified
            or record.incumbent_preidentified != claim.fee_disqualified
        ):
            raise ValueError("recovery claim record does not match persisted claim")
        record_body = {
            "schema": 1,
            "truth_hash": batch.truth_hash,
            "incumbent_output_hash": batch.incumbent_output_hash,
            "buyer_review_batch_hash": batch.buyer_review_batch_hash,
            "claim_id": record.claim_id,
            "finding_id": record.finding_id,
            "finding_proof_hash": record.finding_proof_hash,
            "review_hash": record.review_hash,
            "reference": record.reference,
            "payer_id": record.payer_id,
            "payee_id": record.payee_id,
            "currency": record.currency,
            "amount_cents": record.amount_cents,
            "issued_at": record.issued_at,
            "incumbent_preidentified": record.incumbent_preidentified,
            "fee_disqualified": record.fee_disqualified,
        }
        if canonical_hash(record_body) != record.record_hash:
            raise ValueError("recovery claim record hash mismatch")

    if batch.confirmed_review_count < batch.claim_count:
        raise ValueError("claim count cannot exceed confirmed review count")
    if batch.fee_disqualified_count != sum(
        record.fee_disqualified for record in batch.records
    ):
        raise ValueError("recovery claim fee-disqualified count mismatch")
    expected_state = (
        RecoveryClaimBatchState.CLAIMS_READY.value
        if batch.claims
        else RecoveryClaimBatchState.NO_CONFIRMED_CLAIMS.value
    )
    if batch.state != expected_state:
        raise ValueError("recovery claim batch state mismatch")

    body = {
        "schema": 1,
        "buyer_id": batch.buyer_id,
        "business_unit": batch.business_unit,
        "truth_hash": batch.truth_hash,
        "incumbent_output_hash": batch.incumbent_output_hash,
        "buyer_review_batch_hash": batch.buyer_review_batch_hash,
        "issued_at": batch.issued_at,
        "state": batch.state,
        "confirmed_review_count": batch.confirmed_review_count,
        "claim_count": batch.claim_count,
        "fee_disqualified_count": batch.fee_disqualified_count,
        "records": [asdict(record) for record in batch.records],
        "bindings": [asdict(binding) for binding in batch.bindings],
    }
    if canonical_hash(body) != batch.batch_hash:
        raise ValueError("recovery claim batch hash mismatch")


def persist_recovery_claim_batch(
    store: SettlementStore,
    batch: RecoveryClaimBatch,
) -> RecoveryClaimPersistenceReceipt:
    _verify_recovery_claim_batch(batch)
    if (store.buyer_id, store.business_unit) != (
        batch.buyer_id,
        batch.business_unit,
    ):
        raise ValueError("settlement store scope mismatch with recovery claim batch")

    results = store.create_claims(batch.claims)
    created = sum(results)
    already_present = len(results) - created
    claim_ids = tuple(claim.claim_id for claim in batch.claims)
    body = {
        "schema": 1,
        "buyer_id": batch.buyer_id,
        "business_unit": batch.business_unit,
        "claim_batch_hash": batch.batch_hash,
        "attempted_claim_count": len(results),
        "created_claim_count": created,
        "already_present_count": already_present,
        "claim_ids": claim_ids,
    }
    return RecoveryClaimPersistenceReceipt(
        buyer_id=batch.buyer_id,
        business_unit=batch.business_unit,
        claim_batch_hash=batch.batch_hash,
        attempted_claim_count=len(results),
        created_claim_count=created,
        already_present_count=already_present,
        claim_ids=claim_ids,
        receipt_hash=canonical_hash(body),
    )


def render_recovery_claim_batch_markdown(batch: RecoveryClaimBatch) -> str:
    lines = [
        "# Freight Recovery — Recovery Claim Batch",
        "",
        f"- Buyer: **{batch.buyer_id}**",
        f"- Business unit: **{batch.business_unit}**",
        f"- State: **{batch.state}**",
        f"- Confirmed buyer reviews: **{batch.confirmed_review_count}**",
        f"- Recovery claims: **{batch.claim_count}**",
        f"- Incumbent / fee-disqualified claims: **{batch.fee_disqualified_count}**",
        f"- Issued at: **{batch.issued_at}**",
        f"- Batch hash: `{batch.batch_hash}`",
        "",
        "Claims are created only from CONFIRMED proof-bound buyer reviews.",
        "Incumbent-preidentified findings are fee-disqualified automatically.",
        "This artifact does not prove settlement, recovery, or realized savings.",
        "",
    ]
    for record in batch.records:
        lines.extend([
            f"## {record.claim_id}",
            "",
            f"- Finding: `{record.finding_id}`",
            f"- Currency / amount: **{record.currency} {record.amount_cents / 100:,.2f}**",
            f"- Reference: `{record.reference}`",
            f"- Payer / payee: `{record.payer_id}` → `{record.payee_id}`",
            f"- Fee disqualified: **{'yes' if record.fee_disqualified else 'no'}**",
            f"- Finding proof: `{record.finding_proof_hash}`",
            f"- Buyer review proof: `{record.review_hash}`",
            f"- Claim record proof: `{record.record_hash}`",
            "",
        ])
    return "\n".join(lines)
