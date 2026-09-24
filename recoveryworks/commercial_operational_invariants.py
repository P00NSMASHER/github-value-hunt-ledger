"""End-to-end commercial and operational invariant verification.

The verifier is intentionally read-only. It spans the exact proof chain from
pilot kickoff authorization through closeout, finalized agreement, billing,
independent settlement, and recurring-assurance activation. It does not repair
or mutate state: any broken binding is surfaced as a blocking invariant.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from recoveryworks.billing_draft import UnissuedBillingDraft
from recoveryworks.billing_issuance import (
    ExternalInvoiceIssuanceReceipt,
    InvoiceIssuanceHandoff,
    VerifiedIssuedInvoice,
)
from recoveryworks.commercial_agreement_gate import (
    CommercialFeeDraftReadiness,
    FinalizedCommercialAgreementReceipt,
)
from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.payment_reconciliation import (
    ExternalPaymentSettlementReceipt,
    InvoicePaymentReconciliation,
    reconcile_invoice_payment,
)
from recoveryworks.pilot_charter import RecoveryWorksPilotCharter
from recoveryworks.pilot_closeout import PilotCloseoutSnapshot
from recoveryworks.pilot_closeout_acknowledgment import PilotCloseoutAcknowledgment
from recoveryworks.pilot_kickoff import (
    ExternalPilotKickoffAuthorization,
    PilotKickoffGate,
)
from recoveryworks.recurring_assurance_activation import (
    ExternalRecurringAssuranceAuthorizationReceipt,
    RecurringAssuranceActivationReadiness,
)
from recoveryworks.recurring_assurance_lifecycle import (
    RecurringAssuranceServiceActivationReceipt,
    RecurringAssuranceServiceLifecycle,
)


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


class CommercialOperationalInvariantState(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CommercialOperationalInvariantCheck:
    code: str
    passed: bool
    detail: str
    evidence_proof_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("invariant check code is required")
        if type(self.passed) is not bool:
            raise ValueError("invariant check passed must be boolean")
        hashes = tuple(
            sorted(
                normalize_sha256("evidence_proof_hash", value)
                for value in self.evidence_proof_hashes
            )
        )
        object.__setattr__(self, "evidence_proof_hashes", hashes)

    @property
    def proof_hash(self) -> str:
        return canonical_hash(
            {
                "schema": 1,
                "code": self.code,
                "passed": self.passed,
                "detail": self.detail,
                "evidence_proof_hashes": list(self.evidence_proof_hashes),
            }
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "passed": self.passed,
            "detail": self.detail,
            "evidence_proof_hashes": list(self.evidence_proof_hashes),
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class CommercialOperationalInvariantReport:
    report_id: str
    checked_at: str
    engagement_id: str
    buyer_id: str
    state: CommercialOperationalInvariantState
    artifact_proof_hashes: tuple[tuple[str, str], ...]
    checks: tuple[CommercialOperationalInvariantCheck, ...]
    external_actions_performed: bool = False
    automatic_repair_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "checked_at", normalize_utc_timestamp("checked_at", self.checked_at)
        )
        if not isinstance(self.state, CommercialOperationalInvariantState):
            raise ValueError("state must be CommercialOperationalInvariantState")
        artifacts = tuple(
            sorted(
                (
                    str(name),
                    normalize_sha256("artifact_proof_hash", proof_hash),
                )
                for name, proof_hash in self.artifact_proof_hashes
            )
        )
        if not artifacts:
            raise ValueError("invariant report requires artifact proofs")
        object.__setattr__(self, "artifact_proof_hashes", artifacts)
        checks = tuple(sorted(self.checks, key=lambda item: item.code))
        if not checks:
            raise ValueError("invariant report requires checks")
        object.__setattr__(self, "checks", checks)
        expected_state = (
            CommercialOperationalInvariantState.PASS
            if all(check.passed for check in checks)
            else CommercialOperationalInvariantState.BLOCKED
        )
        if self.state is not expected_state:
            raise ValueError("invariant report state does not match checks")
        if self.external_actions_performed or self.automatic_repair_performed:
            raise ValueError("commercial invariant verification must remain read-only")
        expected = "recoveryworks-commercial-operational-invariants:" + canonical_hash(
            self._identity()
        )
        if self.report_id != expected:
            raise ValueError("report_id does not bind commercial invariant report")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "checked_at": self.checked_at,
            "engagement_id": self.engagement_id,
            "buyer_id": self.buyer_id,
            "state": self.state.value,
            "artifact_proof_hashes": [
                {"name": name, "proof_hash": proof_hash}
                for name, proof_hash in self.artifact_proof_hashes
            ],
            "check_hashes": [check.proof_hash for check in self.checks],
            "external_actions_performed": False,
            "automatic_repair_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    @property
    def failed_codes(self) -> tuple[str, ...]:
        return tuple(check.code for check in self.checks if not check.passed)

    def require_pass(self) -> None:
        if self.state is CommercialOperationalInvariantState.BLOCKED:
            raise ValueError(
                "commercial operational invariants blocked: "
                + ", ".join(self.failed_codes)
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "report_id": self.report_id,
            "proof_hash": self.proof_hash,
            "checks": [check.as_dict() for check in self.checks],
            "failed_codes": list(self.failed_codes),
        }


def _check(
    code: str,
    passed: bool,
    detail: str,
    *proof_hashes: str,
) -> CommercialOperationalInvariantCheck:
    return CommercialOperationalInvariantCheck(
        code=code,
        passed=bool(passed),
        detail=detail,
        evidence_proof_hashes=tuple(proof_hashes),
    )


def _all_false(value: Any, names: tuple[str, ...]) -> bool:
    return all(getattr(value, name) is False for name in names)


def verify_commercial_operational_invariants(
    *,
    charter: RecoveryWorksPilotCharter,
    kickoff_authorization: ExternalPilotKickoffAuthorization,
    kickoff_gate: PilotKickoffGate,
    closeout: PilotCloseoutSnapshot,
    closeout_acknowledgment: PilotCloseoutAcknowledgment,
    agreement: FinalizedCommercialAgreementReceipt,
    fee_readiness: CommercialFeeDraftReadiness,
    billing_draft: UnissuedBillingDraft,
    invoice_handoff: InvoiceIssuanceHandoff,
    invoice_receipt: ExternalInvoiceIssuanceReceipt,
    issued_invoice: VerifiedIssuedInvoice,
    settlement_receipts: tuple[ExternalPaymentSettlementReceipt, ...],
    payment_reconciliation: InvoicePaymentReconciliation,
    recurring_authorization: ExternalRecurringAssuranceAuthorizationReceipt,
    recurring_readiness: RecurringAssuranceActivationReadiness,
    recurring_activation: RecurringAssuranceServiceActivationReceipt,
    recurring_lifecycle: RecurringAssuranceServiceLifecycle,
    checked_at: str,
) -> CommercialOperationalInvariantReport:
    checked_at = normalize_utc_timestamp("checked_at", checked_at)
    checks: list[CommercialOperationalInvariantCheck] = []

    charter_hash = charter.proof_hash
    kickoff_auth_hash = kickoff_authorization.proof_hash
    kickoff_hash = kickoff_gate.proof_hash
    closeout_hash = closeout.proof_hash
    ack_hash = closeout_acknowledgment.proof_hash
    agreement_hash = agreement.proof_hash
    readiness_hash = fee_readiness.proof_hash
    draft_hash = billing_draft.proof_hash
    handoff_hash = invoice_handoff.proof_hash
    invoice_receipt_hash = invoice_receipt.proof_hash
    invoice_hash = issued_invoice.proof_hash
    reconciliation_hash = payment_reconciliation.proof_hash
    recurring_auth_hash = recurring_authorization.proof_hash
    recurring_ready_hash = recurring_readiness.proof_hash
    recurring_activation_hash = recurring_activation.proof_hash
    recurring_lifecycle_hash = recurring_lifecycle.proof_hash

    pilot_scope_ok = (
        kickoff_authorization.charter_id == charter.charter_id
        and kickoff_authorization.charter_proof_hash == charter_hash
        and kickoff_authorization.engagement_id == charter.engagement_id
        and kickoff_authorization.buyer_id == charter.buyer_id
        and tuple(kickoff_authorization.billing_account_scope)
            == tuple(sorted(charter.billing_account_scope))
        and tuple(kickoff_authorization.provider_scope)
            == tuple(sorted(x.lower() for x in charter.provider_scope))
        and kickoff_authorization.source_date_start == charter.source_date_start
        and kickoff_authorization.source_date_end == charter.source_date_end
        and kickoff_gate.charter_id == charter.charter_id
        and kickoff_gate.charter_proof_hash == charter_hash
        and kickoff_gate.kickoff_authorization_proof_hash == kickoff_auth_hash
        and kickoff_gate.engagement_id == charter.engagement_id
        and kickoff_gate.buyer_id == charter.buyer_id
    )
    checks.append(
        _check(
            "PILOT_AUTHORIZATION_BINDING",
            pilot_scope_ok,
            "Kickoff authorization and gate bind the exact charter, buyer, scope, and proof."
            if pilot_scope_ok
            else "Pilot authorization/gate proof or scope binding is inconsistent.",
            charter_hash,
            kickoff_auth_hash,
            kickoff_hash,
        )
    )

    pilot_no_escalation = (
        kickoff_authorization.verified is True
        and kickoff_authorization.customer_data_processing_authorized is True
        and kickoff_authorization.kickoff_authorized is True
        and _all_false(
            kickoff_authorization,
            (
                "outreach_authorized",
                "external_action_authorized",
                "provider_mutation_authorized",
                "invoice_authorized",
                "payment_collection_authorized",
            ),
        )
        and _all_false(
            kickoff_gate,
            (
                "external_action_authorized",
                "provider_mutation_authorized",
                "outreach_authorized",
                "invoice_authorized",
                "payment_collection_authorized",
            ),
        )
    )
    checks.append(
        _check(
            "PILOT_AUTHORIZATION_NO_ESCALATION",
            pilot_no_escalation,
            "Pilot authorization remains read-only and cannot smuggle downstream authority."
            if pilot_no_escalation
            else "Pilot authorization contains a consequential-action escalation.",
            kickoff_auth_hash,
            kickoff_hash,
        )
    )

    closeout_binding_ok = (
        closeout.charter_id == charter.charter_id
        and closeout.charter_proof_hash == charter_hash
        and closeout.kickoff_gate_proof_hash == kickoff_hash
        and closeout_acknowledgment.closeout_proof_hash == closeout_hash
        and closeout_acknowledgment.engagement_id == charter.engagement_id
        and closeout_acknowledgment.buyer_id == charter.buyer_id
    )
    checks.append(
        _check(
            "CLOSEOUT_PROOF_CHAIN",
            closeout_binding_ok,
            "Closeout and buyer acknowledgment bind the exact authorized pilot."
            if closeout_binding_ok
            else "Closeout or acknowledgment bypasses the authorized pilot proof chain.",
            kickoff_hash,
            closeout_hash,
            ack_hash,
        )
    )

    closeout_no_escalation = (
        _all_false(
            closeout,
            (
                "continuation_authorized",
                "invoice_created",
                "payment_due_asserted",
                "payment_received",
                "external_action_authorized",
            ),
        )
        and _all_false(
            closeout_acknowledgment,
            (
                "continuation_authorized",
                "invoice_authorized",
                "payment_due_asserted",
            ),
        )
    )
    checks.append(
        _check(
            "CLOSEOUT_NO_COMMERCIAL_ESCALATION",
            closeout_no_escalation,
            "Closeout and acknowledgment do not self-authorize billing or continuation."
            if closeout_no_escalation
            else "Closeout surfaces contain unauthorized commercial escalation.",
            closeout_hash,
            ack_hash,
        )
    )

    agreement_binding_ok = (
        agreement.charter_id == charter.charter_id
        and agreement.charter_proof_hash == charter_hash
        and agreement.closeout_acknowledgment_proof_hash == ack_hash
        and agreement.engagement_id == charter.engagement_id
        and agreement.buyer_id == charter.buyer_id
        and agreement.verified is True
        and agreement.externally_finalized is True
    )
    checks.append(
        _check(
            "FINALIZED_AGREEMENT_BINDING",
            agreement_binding_ok,
            "Finalized external agreement binds the exact charter and buyer closeout acknowledgment."
            if agreement_binding_ok
            else "Finalized agreement binding, buyer scope, or external verification is inconsistent.",
            charter_hash,
            ack_hash,
            agreement_hash,
        )
    )

    expected_success_fee = (
        closeout.recovered_cash_cents
        * fee_readiness.recovered_cash_success_fee_bps_agreed
    ) // 10000
    amount_surface_ok = (
        fee_readiness.agreement_receipt_proof_hash == agreement_hash
        and fee_readiness.closeout_acknowledgment_proof_hash == ack_hash
        and fee_readiness.closeout_proof_hash == closeout_hash
        and fee_readiness.engagement_id == charter.engagement_id
        and fee_readiness.buyer_id == charter.buyer_id
        and fee_readiness.currency == closeout.currency == agreement.currency
        and fee_readiness.recovered_cash_cents == closeout.recovered_cash_cents
        and fee_readiness.recovered_cash_success_fee_cents == expected_success_fee
        and fee_readiness.closeout_fee_total_cents
            == fee_readiness.diagnostic_fee_cents_agreed + expected_success_fee
    )
    checks.append(
        _check(
            "RECOVERED_CASH_AMOUNT_SURFACE",
            amount_surface_ok,
            "Success-fee arithmetic uses verified recovered cash only."
            if amount_surface_ok
            else "Recovered/validated/savings amount surfaces or fee arithmetic are confused.",
            closeout_hash,
            agreement_hash,
            readiness_hash,
        )
    )

    draft_binding_ok = (
        billing_draft.agreement_receipt_proof_hash == agreement_hash
        and billing_draft.fee_readiness_proof_hash == readiness_hash
        and billing_draft.engagement_id == charter.engagement_id
        and billing_draft.buyer_id == charter.buyer_id
        and billing_draft.currency == agreement.currency
        and billing_draft.total_cents == fee_readiness.closeout_fee_total_cents
        and billing_draft.monthly_assurance_option_cents
            == fee_readiness.monthly_assurance_fee_cents_agreed
        and _all_false(
            billing_draft,
            (
                "issued",
                "sent",
                "payment_due_asserted",
                "payment_received",
                "payment_instructions_included",
                "external_commitment_created",
            ),
        )
    )
    checks.append(
        _check(
            "BILLING_DRAFT_BINDING",
            draft_binding_ok,
            "Billing draft binds exact agreement/readiness and remains unissued."
            if draft_binding_ok
            else "Billing draft proof, amount, scope, or non-issued state is inconsistent.",
            agreement_hash,
            readiness_hash,
            draft_hash,
        )
    )

    expected_line_hashes = tuple(item.proof_hash for item in billing_draft.line_items)
    handoff_binding_ok = (
        invoice_handoff.draft_id == billing_draft.draft_id
        and invoice_handoff.draft_proof_hash == draft_hash
        and invoice_handoff.agreement_receipt_proof_hash == agreement_hash
        and invoice_handoff.fee_readiness_proof_hash == readiness_hash
        and invoice_handoff.engagement_id == charter.engagement_id
        and invoice_handoff.buyer_id == charter.buyer_id
        and invoice_handoff.currency == agreement.currency
        and invoice_handoff.invoice_total_cents == billing_draft.total_cents
        and invoice_handoff.line_item_proof_hashes == expected_line_hashes
        and _all_false(
            invoice_handoff,
            (
                "issuance_performed_by_recoveryworks",
                "payment_collection_enabled",
                "payment_instructions_embedded",
            ),
        )
    )
    checks.append(
        _check(
            "INVOICE_HANDOFF_BINDING",
            handoff_binding_ok,
            "Invoice handoff binds the exact unissued draft without RecoveryWorks issuance authority."
            if handoff_binding_ok
            else "Invoice handoff proof, amount, scope, or authority is inconsistent.",
            draft_hash,
            handoff_hash,
        )
    )

    external_invoice_ok = (
        invoice_receipt.handoff_id == invoice_handoff.handoff_id
        and invoice_receipt.handoff_proof_hash == handoff_hash
        and invoice_receipt.issuer_id == invoice_handoff.issuer_id
        and invoice_receipt.currency == invoice_handoff.currency
        and invoice_receipt.total_cents == invoice_handoff.invoice_total_cents
        and invoice_receipt.line_item_proof_hashes
            == invoice_handoff.line_item_proof_hashes
        and invoice_receipt.due_at == invoice_handoff.due_at
        and invoice_receipt.verified is True
        and invoice_receipt.issued_by_external_system is True
        and invoice_receipt.delivered_to_buyer is True
        and invoice_receipt.payment_due_asserted_by_external_system is True
        and invoice_receipt.payment_received is False
        and invoice_receipt.payment_collection_performed_by_recoveryworks is False
        and issued_invoice.handoff_proof_hash == handoff_hash
        and issued_invoice.issuance_receipt_proof_hash == invoice_receipt_hash
        and issued_invoice.engagement_id == charter.engagement_id
        and issued_invoice.buyer_id == charter.buyer_id
        and issued_invoice.currency == agreement.currency
        and issued_invoice.total_cents == invoice_handoff.invoice_total_cents
        and issued_invoice.external_invoice_id == invoice_receipt.external_invoice_id
    )
    checks.append(
        _check(
            "EXTERNAL_INVOICE_BINDING",
            external_invoice_ok,
            "Verified invoice is derived only from the exact external issuance/delivery receipt."
            if external_invoice_ok
            else "Invoice issuance, delivery, amount, or buyer proof chain is inconsistent.",
            handoff_hash,
            invoice_receipt_hash,
            invoice_hash,
        )
    )

    settlement_recomputed = None
    settlement_error = None
    try:
        settlement_recomputed = reconcile_invoice_payment(
            issued_invoice,
            tuple(settlement_receipts),
            reconciled_at=payment_reconciliation.reconciled_at,
        )
    except (TypeError, ValueError) as exc:
        settlement_error = str(exc)
    settlement_ok = (
        settlement_recomputed is not None
        and bool(settlement_receipts)
        and settlement_recomputed.proof_hash == reconciliation_hash
        and payment_reconciliation.issued_invoice_id == issued_invoice.issued_invoice_id
        and payment_reconciliation.issued_invoice_proof_hash == invoice_hash
        and payment_reconciliation.external_invoice_id == issued_invoice.external_invoice_id
        and payment_reconciliation.buyer_id == charter.buyer_id
        and payment_reconciliation.currency == agreement.currency
        and payment_reconciliation.invoice_total_cents == issued_invoice.total_cents
        and payment_reconciliation.independent_cash_evidence_verified is True
        and payment_reconciliation.payment_collection_performed_by_recoveryworks is False
    )
    settlement_detail = (
        "Independent settlement receipts deterministically reproduce the recorded reconciliation."
        if settlement_ok
        else "Independent settlement proof does not reproduce the recorded reconciliation"
        + (f": {settlement_error}" if settlement_error else ".")
    )
    settlement_hashes = tuple(receipt.proof_hash for receipt in settlement_receipts)
    checks.append(
        _check(
            "INDEPENDENT_SETTLEMENT_RECONCILIATION",
            settlement_ok,
            settlement_detail,
            invoice_hash,
            *settlement_hashes,
            reconciliation_hash,
        )
    )

    recurring_auth_ok = (
        recurring_authorization.agreement_receipt_proof_hash == agreement_hash
        and recurring_authorization.closeout_acknowledgment_proof_hash == ack_hash
        and recurring_authorization.charter_proof_hash == charter_hash
        and recurring_authorization.engagement_id == charter.engagement_id
        and recurring_authorization.buyer_id == charter.buyer_id
        and recurring_authorization.business_unit == charter.business_unit
        and recurring_authorization.billing_account_scope
            == tuple(sorted(charter.billing_account_scope))
        and recurring_authorization.provider_scope
            == tuple(sorted(x.lower() for x in charter.provider_scope))
        and recurring_authorization.currency == agreement.currency
        and recurring_authorization.monthly_assurance_fee_cents
            == agreement.monthly_assurance_fee_cents
        and recurring_authorization.verified is True
        and recurring_authorization.externally_authorized is True
        and recurring_authorization.monthly_cadence_authorized is True
        and _all_false(
            recurring_authorization,
            (
                "provider_write_access_authorized",
                "automatic_invoice_authorized",
                "customer_scope_expansion_authorized",
                "created_by_recoveryworks",
            ),
        )
    )
    checks.append(
        _check(
            "RECURRING_AUTHORIZATION_BINDING",
            recurring_auth_ok,
            "Recurring authorization binds the exact agreement, buyer, scope, and monthly terms."
            if recurring_auth_ok
            else "Recurring authorization proof, scope, amount, or authority is inconsistent.",
            agreement_hash,
            ack_hash,
            recurring_auth_hash,
        )
    )

    recurring_ready_ok = (
        recurring_readiness.authorization_receipt_proof_hash == recurring_auth_hash
        and recurring_readiness.agreement_receipt_proof_hash == agreement_hash
        and recurring_readiness.closeout_acknowledgment_proof_hash == ack_hash
        and recurring_readiness.charter_proof_hash == charter_hash
        and recurring_readiness.engagement_id == charter.engagement_id
        and recurring_readiness.buyer_id == charter.buyer_id
        and recurring_readiness.business_unit == charter.business_unit
        and recurring_readiness.billing_account_scope
            == recurring_authorization.billing_account_scope
        and recurring_readiness.provider_scope == recurring_authorization.provider_scope
        and recurring_readiness.currency == agreement.currency
        and recurring_readiness.monthly_assurance_fee_cents
            == agreement.monthly_assurance_fee_cents
        and _all_false(
            recurring_readiness,
            (
                "service_started",
                "invoice_schedule_started",
                "provider_calls_started",
                "provider_mutation_authorized",
                "external_action_performed",
            ),
        )
    )
    checks.append(
        _check(
            "RECURRING_READINESS_BINDING",
            recurring_ready_ok,
            "Recurring readiness is a non-action state bound to exact external authorization."
            if recurring_ready_ok
            else "Recurring readiness bypasses authorization, scope, terms, or non-action state.",
            recurring_auth_hash,
            recurring_ready_hash,
        )
    )

    recurring_lifecycle_ok = (
        recurring_activation.readiness_id == recurring_readiness.readiness_id
        and recurring_activation.readiness_proof_hash == recurring_ready_hash
        and recurring_activation.authorization_receipt_proof_hash == recurring_auth_hash
        and recurring_activation.agreement_receipt_proof_hash == agreement_hash
        and recurring_activation.closeout_acknowledgment_proof_hash == ack_hash
        and recurring_activation.charter_proof_hash == charter_hash
        and recurring_activation.engagement_id == charter.engagement_id
        and recurring_activation.buyer_id == charter.buyer_id
        and recurring_lifecycle.readiness_id == recurring_readiness.readiness_id
        and recurring_lifecycle.readiness_proof_hash == recurring_ready_hash
        and recurring_lifecycle.activation_receipt_proof_hash
            == recurring_activation_hash
        and recurring_lifecycle.engagement_id == charter.engagement_id
        and recurring_lifecycle.buyer_id == charter.buyer_id
        and _all_false(
            recurring_activation,
            (
                "automatic_invoice_schedule_enabled",
                "provider_mutation_enabled",
                "customer_scope_mutation_enabled",
                "external_actions_performed",
            ),
        )
        and _all_false(
            recurring_lifecycle,
            (
                "automatic_invoice_schedule_enabled",
                "provider_mutation_enabled",
                "customer_scope_mutation_enabled",
                "external_actions_performed",
            ),
        )
    )
    checks.append(
        _check(
            "RECURRING_LIFECYCLE_BINDING",
            recurring_lifecycle_ok,
            "Recurring service lifecycle binds exact readiness/activation without automatic consequences."
            if recurring_lifecycle_ok
            else "Recurring lifecycle skips or substitutes a readiness/activation proof.",
            recurring_ready_hash,
            recurring_activation_hash,
            recurring_lifecycle_hash,
        )
    )

    chronology_values = (
        kickoff_authorization.authorized_at,
        kickoff_gate.checked_at,
        closeout.reviewed_at,
        closeout_acknowledgment.acknowledged_at,
        agreement.effective_at,
        billing_draft.created_at,
        invoice_handoff.issued_at,
        invoice_receipt.issued_at,
        invoice_receipt.delivered_at,
        payment_reconciliation.reconciled_at,
        recurring_activation.activated_at,
        checked_at,
    )
    chronology_ok = all(
        _instant(left) <= _instant(right)
        for left, right in zip(chronology_values, chronology_values[1:])
    )
    authorization_current = (
        _instant(kickoff_gate.checked_at) < _instant(kickoff_authorization.expires_at)
        and _instant(closeout.reviewed_at) < _instant(kickoff_authorization.expires_at)
    )
    recurring_window_current = (
        _instant(recurring_authorization.service_start_at)
        <= _instant(recurring_activation.activated_at)
        < _instant(recurring_authorization.service_end_at)
    )
    checks.append(
        _check(
            "LIFECYCLE_CHRONOLOGY_AND_FRESHNESS",
            chronology_ok and authorization_current and recurring_window_current,
            "Lifecycle chronology is monotonic; pilot and recurring authorizations are current at use."
            if chronology_ok and authorization_current and recurring_window_current
            else "Lifecycle chronology is skipped, replayed, future-dated, or uses stale authorization.",
            kickoff_auth_hash,
            kickoff_hash,
            closeout_hash,
            agreement_hash,
            invoice_hash,
            reconciliation_hash,
            recurring_auth_hash,
            recurring_activation_hash,
        )
    )

    artifact_hashes = tuple(
        sorted(
            (
                ("charter", charter_hash),
                ("kickoff_authorization", kickoff_auth_hash),
                ("kickoff_gate", kickoff_hash),
                ("closeout", closeout_hash),
                ("closeout_acknowledgment", ack_hash),
                ("agreement", agreement_hash),
                ("fee_readiness", readiness_hash),
                ("billing_draft", draft_hash),
                ("invoice_handoff", handoff_hash),
                ("invoice_receipt", invoice_receipt_hash),
                ("issued_invoice", invoice_hash),
                ("payment_reconciliation", reconciliation_hash),
                ("recurring_authorization", recurring_auth_hash),
                ("recurring_readiness", recurring_ready_hash),
                ("recurring_activation", recurring_activation_hash),
                ("recurring_lifecycle", recurring_lifecycle_hash),
            )
        )
    )
    state = (
        CommercialOperationalInvariantState.PASS
        if all(check.passed for check in checks)
        else CommercialOperationalInvariantState.BLOCKED
    )
    check_tuple = tuple(sorted(checks, key=lambda item: item.code))
    identity = {
        "schema": 1,
        "checked_at": checked_at,
        "engagement_id": charter.engagement_id,
        "buyer_id": charter.buyer_id,
        "state": state.value,
        "artifact_proof_hashes": [
            {"name": name, "proof_hash": proof_hash}
            for name, proof_hash in artifact_hashes
        ],
        "check_hashes": [check.proof_hash for check in check_tuple],
        "external_actions_performed": False,
        "automatic_repair_performed": False,
    }
    return CommercialOperationalInvariantReport(
        report_id="recoveryworks-commercial-operational-invariants:"
        + canonical_hash(identity),
        checked_at=checked_at,
        engagement_id=charter.engagement_id,
        buyer_id=charter.buyer_id,
        state=state,
        artifact_proof_hashes=artifact_hashes,
        checks=check_tuple,
        external_actions_performed=False,
        automatic_repair_performed=False,
    )
