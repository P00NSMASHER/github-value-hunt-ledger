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
)
from recoveryworks.models import canonical_hash
from recoveryworks.payment_reconciliation import (
    InvoiceSettlementState,
    SettlementEventType,
    build_external_payment_settlement_receipt,
    reconcile_invoice_payment,
)
from recoveryworks.test_commercial_agreement_gate import fixture


def issued_invoice():
    charter,snapshot,ack,agreement=fixture(
        diagnostic_fee_cents=10000,
        recovered_cash_success_fee_bps=0)
    ready=build_commercial_fee_draft_readiness(
        charter,snapshot,ack,agreement)
    draft=build_unissued_billing_draft(
        agreement,ready,draft_reference="DRAFT-PAY",
        created_at="2026-09-24T17:00:00Z")
    handoff=prepare_invoice_issuance_handoff(
        draft,agreement,ready,issuer_id="billing-system",
        issued_at="2026-09-24T17:05:00Z")
    values={
        "handoff_id":handoff.handoff_id,
        "handoff_proof_hash":handoff.proof_hash,
        "issuer_id":handoff.issuer_id,
        "external_invoice_id":"inv-pay",
        "external_invoice_reference":"RW-PAY",
        "issued_at":"2026-09-24T17:06:00Z",
        "delivered_at":"2026-09-24T17:07:00Z",
        "due_at":handoff.due_at,
        "currency":handoff.currency,
        "total_cents":handoff.invoice_total_cents,
        "line_item_proof_hashes":handoff.line_item_proof_hashes,
        "delivery_evidence_hash":"1"*64,
        "source_hash":"2"*64,
        "source_locator":"billing://inv-pay",
        "verified":True,
        "issued_by_external_system":True,
        "delivered_to_buyer":True,
        "payment_due_asserted_by_external_system":True,
        "payment_received":False,
        "payment_collection_performed_by_recoveryworks":False,
    }
    ident={"schema":1,**values,
           "line_item_proof_hashes":list(values["line_item_proof_hashes"])}
    receipt=ExternalInvoiceIssuanceReceipt(
        receipt_id="recoveryworks-external-invoice-receipt:"
        +canonical_hash(ident),**values)
    return verify_external_invoice_issuance(handoff,receipt)


class PaymentReconciliationTests(unittest.TestCase):
    def test_partial_then_full_external_cash_reconciliation(self):
        invoice=issued_invoice()
        p1=build_external_payment_settlement_receipt(
            invoice,event_type=SettlementEventType.CREDIT,
            settlement_reference="bank-1",
            observed_at="2026-09-25T12:00:00Z",
            gross_cents=4000,fee_cents=100,
            invoice_applied_delta_cents=4000,
            reverses_settlement_reference=None,
            source_hash="3"*64,source_locator="bank://settlement/1",
            verified=True)
        partial=reconcile_invoice_payment(
            invoice,(p1,),reconciled_at="2026-09-25T12:01:00Z")
        self.assertIs(
            partial.settlement_state,InvoiceSettlementState.PARTIALLY_PAID)
        self.assertEqual(partial.remaining_cents,6000)
        p2=build_external_payment_settlement_receipt(
            invoice,event_type=SettlementEventType.CREDIT,
            settlement_reference="bank-2",
            observed_at="2026-09-26T12:00:00Z",
            gross_cents=6000,fee_cents=100,
            invoice_applied_delta_cents=6000,
            reverses_settlement_reference=None,
            source_hash="4"*64,source_locator="bank://settlement/2",
            verified=True)
        paid=reconcile_invoice_payment(
            invoice,(p1,p2),reconciled_at="2026-09-26T12:01:00Z")
        self.assertIs(paid.settlement_state,InvoiceSettlementState.PAID)
        self.assertEqual(paid.applied_cents,10000)
        self.assertEqual(paid.net_cash_cents,9800)
        self.assertFalse(paid.payment_collection_performed_by_recoveryworks)

    def test_reversal_reopens_paid_invoice(self):
        invoice=issued_invoice()
        credit=build_external_payment_settlement_receipt(
            invoice,event_type=SettlementEventType.CREDIT,
            settlement_reference="bank-full",
            observed_at="2026-09-25T12:00:00Z",
            gross_cents=10000,fee_cents=0,
            invoice_applied_delta_cents=10000,
            reverses_settlement_reference=None,
            source_hash="5"*64,source_locator="bank://full",verified=True)
        reversal=build_external_payment_settlement_receipt(
            invoice,event_type=SettlementEventType.REVERSAL,
            settlement_reference="bank-reversal",
            observed_at="2026-09-26T12:00:00Z",
            gross_cents=2500,fee_cents=0,
            invoice_applied_delta_cents=-2500,
            reverses_settlement_reference="bank-full",
            source_hash="6"*64,source_locator="bank://reversal",verified=True)
        result=reconcile_invoice_payment(
            invoice,(credit,reversal),
            reconciled_at="2026-09-26T12:01:00Z")
        self.assertIs(
            result.settlement_state,InvoiceSettlementState.PARTIALLY_PAID)
        self.assertEqual(result.applied_cents,7500)
        self.assertEqual(result.remaining_cents,2500)

    def test_duplicate_overallocation_and_provider_only_status_fail_closed(self):
        invoice=issued_invoice()
        credit=build_external_payment_settlement_receipt(
            invoice,event_type=SettlementEventType.CREDIT,
            settlement_reference="dup",
            observed_at="2026-09-25T12:00:00Z",
            gross_cents=6000,fee_cents=0,
            invoice_applied_delta_cents=6000,
            reverses_settlement_reference=None,
            source_hash="7"*64,source_locator="bank://dup",verified=True)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            reconcile_invoice_payment(
                invoice,(credit,credit),
                reconciled_at="2026-09-25T12:01:00Z")
        with self.assertRaisesRegex(ValueError,"cash-settlement evidence"):
            from recoveryworks.payment_reconciliation import ExternalPaymentSettlementReceipt
            ident=credit._identity()
            ident["provider_accounting_only"]=True
            ExternalPaymentSettlementReceipt(
                receipt_id="recoveryworks-payment-settlement:"+canonical_hash(ident),
                **{
                    **{k:v for k,v in ident.items() if k!="schema"},
                    "event_type":SettlementEventType.CREDIT,
                })


if __name__=="__main__":
    unittest.main()
