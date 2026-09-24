from __future__ import annotations

import unittest

from recoveryworks.billing_draft import build_unissued_billing_draft
from recoveryworks.billing_issuance import (
    ExternalInvoiceIssuanceReceipt,
    prepare_invoice_issuance_handoff,
    verify_external_invoice_issuance,
)
from recoveryworks.commercial_agreement_gate import (
    build_commercial_fee_draft_readiness,
    build_external_finalized_commercial_agreement,
)
from recoveryworks.commercial_operational_invariants import (
    CommercialOperationalInvariantState,
    verify_commercial_operational_invariants,
)
from recoveryworks.models import canonical_hash
from recoveryworks.payment_reconciliation import (
    SettlementEventType,
    build_external_payment_settlement_receipt,
    reconcile_invoice_payment,
)
from recoveryworks.pilot_closeout import build_pilot_closeout_snapshot
from recoveryworks.pilot_closeout_acknowledgment import (
    ContinuationInterest,
    build_external_buyer_closeout_receipt,
    verify_buyer_closeout_acknowledgment,
)
from recoveryworks.pilot_kickoff import build_external_pilot_kickoff_authorization
from recoveryworks.recurring_assurance_activation import (
    build_external_recurring_assurance_authorization,
    build_recurring_assurance_activation_readiness,
)
from recoveryworks.recurring_assurance_lifecycle import (
    build_recurring_assurance_service_activation,
    build_recurring_assurance_service_lifecycle,
)
from recoveryworks.test_pilot_closeout import charter_and_kickoff, report


def full_chain():
    charter, kickoff = charter_and_kickoff()
    kickoff_authorization = build_external_pilot_kickoff_authorization(
        charter,
        authorized_by="buyer-controller",
        authorized_at="2026-09-24T14:00:00Z",
        expires_at="2026-09-25T14:00:00Z",
        retention_until="2026-10-31T23:59:59Z",
        source_hash="1" * 64,
        source_locator="buyer://authorization/kickoff",
        verified=True,
    )
    assert kickoff.kickoff_authorization_proof_hash == kickoff_authorization.proof_hash

    closeout = build_pilot_closeout_snapshot(
        charter,
        kickoff,
        report(recovered=10000, validated=50000, savings=250000),
        buyer_review_evidence_hash="3" * 64,
        reviewed_at="2026-09-24T16:00:00Z",
    )
    buyer_receipt = build_external_buyer_closeout_receipt(
        closeout,
        charter,
        buyer_reviewer_id="buyer-controller",
        acknowledged_at="2026-09-24T16:15:00Z",
        recovered_cash_cents=closeout.recovered_cash_cents,
        validated_recovery_cents=closeout.validated_recovery_cents,
        prospective_savings_cents=closeout.prospective_savings_cents,
        realized_savings_cents=closeout.realized_savings_cents,
        anomaly_exposure_cents=closeout.anomaly_exposure_cents,
        reconciliation_drift_cents=closeout.reconciliation_drift_cents,
        accepts_recovery_outcomes=True,
        accepts_savings_outcomes=True,
        open_dispute_count=0,
        continuation_interest=ContinuationInterest.REVIEW_MONTHLY_ASSURANCE,
        source_hash="4" * 64,
        source_locator="buyer://closeout/ack-1",
        verified=True,
    )
    acknowledgment = verify_buyer_closeout_acknowledgment(
        closeout, charter, buyer_receipt
    )

    agreement = build_external_finalized_commercial_agreement(
        charter,
        acknowledgment,
        agreement_reference="agreement-e2e-001",
        currency="USD",
        diagnostic_fee_cents=500000,
        recovered_cash_success_fee_bps=2500,
        monthly_assurance_fee_cents=300000,
        payment_terms_days=30,
        diagnostic_fee_applicable=True,
        success_fee_applicable=True,
        monthly_assurance_separately_accepted=True,
        effective_at="2026-09-24T16:30:00Z",
        source_hash="5" * 64,
        source_locator="agreement://e2e/001",
        verified=True,
        externally_finalized=True,
    )
    fee_readiness = build_commercial_fee_draft_readiness(
        charter, closeout, acknowledgment, agreement
    )
    billing_draft = build_unissued_billing_draft(
        agreement,
        fee_readiness,
        draft_reference="DRAFT-E2E-001",
        created_at="2026-09-24T17:00:00Z",
    )
    invoice_handoff = prepare_invoice_issuance_handoff(
        billing_draft,
        agreement,
        fee_readiness,
        issuer_id="billing-system-e2e",
        issued_at="2026-09-24T17:05:00Z",
    )
    receipt_values = {
        "handoff_id": invoice_handoff.handoff_id,
        "handoff_proof_hash": invoice_handoff.proof_hash,
        "issuer_id": invoice_handoff.issuer_id,
        "external_invoice_id": "inv-e2e-001",
        "external_invoice_reference": "RW-E2E-001",
        "issued_at": "2026-09-24T17:06:00Z",
        "delivered_at": "2026-09-24T17:07:00Z",
        "due_at": invoice_handoff.due_at,
        "currency": invoice_handoff.currency,
        "total_cents": invoice_handoff.invoice_total_cents,
        "line_item_proof_hashes": invoice_handoff.line_item_proof_hashes,
        "delivery_evidence_hash": "6" * 64,
        "source_hash": "7" * 64,
        "source_locator": "billing://invoice/inv-e2e-001",
        "verified": True,
        "issued_by_external_system": True,
        "delivered_to_buyer": True,
        "payment_due_asserted_by_external_system": True,
        "payment_received": False,
        "payment_collection_performed_by_recoveryworks": False,
    }
    receipt_identity = {
        "schema": 1,
        **receipt_values,
        "line_item_proof_hashes": list(receipt_values["line_item_proof_hashes"]),
    }
    invoice_receipt = ExternalInvoiceIssuanceReceipt(
        receipt_id="recoveryworks-external-invoice-receipt:"
        + canonical_hash(receipt_identity),
        **receipt_values,
    )
    issued_invoice = verify_external_invoice_issuance(
        invoice_handoff, invoice_receipt
    )

    settlement_receipt = build_external_payment_settlement_receipt(
        issued_invoice,
        event_type=SettlementEventType.CREDIT,
        settlement_reference="bank-e2e-001",
        observed_at="2026-09-25T12:00:00Z",
        gross_cents=issued_invoice.total_cents,
        fee_cents=100,
        invoice_applied_delta_cents=issued_invoice.total_cents,
        reverses_settlement_reference=None,
        source_hash="8" * 64,
        source_locator="bank://settlement/e2e-001",
        verified=True,
    )
    reconciliation = reconcile_invoice_payment(
        issued_invoice,
        (settlement_receipt,),
        reconciled_at="2026-09-25T12:01:00Z",
    )

    recurring_authorization = build_external_recurring_assurance_authorization(
        charter,
        acknowledgment,
        agreement,
        service_start_at="2026-10-01T00:00:00Z",
        service_end_at="2027-10-01T00:00:00Z",
        authorization_reference="buyer-recurring-e2e-001",
        source_hash="9" * 64,
        source_locator="buyer://monthly-assurance/e2e-001",
        verified=True,
        externally_authorized=True,
    )
    recurring_readiness = build_recurring_assurance_activation_readiness(
        charter, acknowledgment, agreement, recurring_authorization
    )
    recurring_activation = build_recurring_assurance_service_activation(
        recurring_readiness,
        activated_at="2026-10-01T00:00:00Z",
        operator_id="operator-e2e",
        activation_reference="activate-e2e-001",
        internal_operator_authorized=True,
    )
    recurring_lifecycle = build_recurring_assurance_service_lifecycle(
        recurring_readiness, recurring_activation
    )
    return {
        "charter": charter,
        "kickoff_authorization": kickoff_authorization,
        "kickoff_gate": kickoff,
        "closeout": closeout,
        "closeout_acknowledgment": acknowledgment,
        "agreement": agreement,
        "fee_readiness": fee_readiness,
        "billing_draft": billing_draft,
        "invoice_handoff": invoice_handoff,
        "invoice_receipt": invoice_receipt,
        "issued_invoice": issued_invoice,
        "settlement_receipts": (settlement_receipt,),
        "payment_reconciliation": reconciliation,
        "recurring_authorization": recurring_authorization,
        "recurring_readiness": recurring_readiness,
        "recurring_activation": recurring_activation,
        "recurring_lifecycle": recurring_lifecycle,
        "checked_at": "2026-10-01T00:05:00Z",
    }


class CommercialOperationalInvariantTests(unittest.TestCase):
    def test_exact_end_to_end_chain_passes(self):
        chain = full_chain()
        result = verify_commercial_operational_invariants(**chain)
        self.assertIs(result.state, CommercialOperationalInvariantState.PASS)
        self.assertEqual(result.failed_codes, ())
        self.assertTrue(all(check.passed for check in result.checks))
        self.assertFalse(result.external_actions_performed)
        self.assertFalse(result.automatic_repair_performed)
        result.require_pass()

    def test_cross_buyer_substitution_is_blocked(self):
        chain = full_chain()
        object.__setattr__(chain["issued_invoice"], "buyer_id", "other-buyer")
        result = verify_commercial_operational_invariants(**chain)
        self.assertIs(result.state, CommercialOperationalInvariantState.BLOCKED)
        self.assertIn("EXTERNAL_INVOICE_BINDING", result.failed_codes)
        self.assertIn("INDEPENDENT_SETTLEMENT_RECONCILIATION", result.failed_codes)
        with self.assertRaisesRegex(ValueError, "commercial operational invariants blocked"):
            result.require_pass()

    def test_validated_recovery_cannot_replace_recovered_cash_surface(self):
        chain = full_chain()
        object.__setattr__(
            chain["fee_readiness"],
            "recovered_cash_cents",
            chain["closeout"].validated_recovery_cents,
        )
        result = verify_commercial_operational_invariants(**chain)
        self.assertIs(result.state, CommercialOperationalInvariantState.BLOCKED)
        self.assertIn("RECOVERED_CASH_AMOUNT_SURFACE", result.failed_codes)
        self.assertIn("BILLING_DRAFT_BINDING", result.failed_codes)

    def test_recurring_activation_cannot_substitute_readiness(self):
        chain = full_chain()
        object.__setattr__(
            chain["recurring_activation"],
            "readiness_proof_hash",
            "f" * 64,
        )
        result = verify_commercial_operational_invariants(**chain)
        self.assertIs(result.state, CommercialOperationalInvariantState.BLOCKED)
        self.assertIn("RECURRING_LIFECYCLE_BINDING", result.failed_codes)


if __name__ == "__main__":
    unittest.main()
