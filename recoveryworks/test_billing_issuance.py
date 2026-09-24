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
from recoveryworks.test_commercial_agreement_gate import fixture


class BillingIssuanceTests(unittest.TestCase):
    def setup(self):
        charter,snapshot,ack,agreement=fixture(
            diagnostic_fee_cents=500000,
            recovered_cash_success_fee_bps=2500)
        ready=build_commercial_fee_draft_readiness(
            charter,snapshot,ack,agreement)
        draft=build_unissued_billing_draft(
            agreement,ready,draft_reference="DRAFT-ISSUE",
            created_at="2026-09-24T17:00:00Z")
        handoff=prepare_invoice_issuance_handoff(
            draft,agreement,ready,issuer_id="billing-system-1",
            issued_at="2026-09-24T17:05:00Z")
        return agreement,ready,draft,handoff

    def receipt(self,handoff,**overrides):
        values={
            "handoff_id":handoff.handoff_id,
            "handoff_proof_hash":handoff.proof_hash,
            "issuer_id":handoff.issuer_id,
            "external_invoice_id":"inv-001",
            "external_invoice_reference":"RW-2026-0001",
            "issued_at":"2026-09-24T17:06:00Z",
            "delivered_at":"2026-09-24T17:07:00Z",
            "due_at":handoff.due_at,
            "currency":handoff.currency,
            "total_cents":handoff.invoice_total_cents,
            "line_item_proof_hashes":handoff.line_item_proof_hashes,
            "delivery_evidence_hash":"6"*64,
            "source_hash":"7"*64,
            "source_locator":"billing://invoice/inv-001",
            "verified":True,
            "issued_by_external_system":True,
            "delivered_to_buyer":True,
            "payment_due_asserted_by_external_system":True,
            "payment_received":False,
            "payment_collection_performed_by_recoveryworks":False,
        }
        values.update(overrides)
        ident={
            "schema":1,
            **values,
            "line_item_proof_hashes":list(values["line_item_proof_hashes"]),
            "verified":True,
            "issued_by_external_system":True,
            "delivered_to_buyer":True,
            "payment_due_asserted_by_external_system":True,
            "payment_received":False,
            "payment_collection_performed_by_recoveryworks":False,
        }
        return ExternalInvoiceIssuanceReceipt(
            receipt_id="recoveryworks-external-invoice-receipt:"
            +canonical_hash(ident),
            **values)

    def test_separate_issuer_receipt_creates_verified_due_invoice(self):
        _,_,_,handoff=self.setup()
        self.assertEqual(
            handoff.as_dict()["state"],"READY_FOR_SEPARATE_BILLING_ISSUER")
        issued=verify_external_invoice_issuance(
            handoff,self.receipt(handoff))
        self.assertEqual(
            issued.as_dict()["state"],"ISSUED_INVOICE_VERIFIED")
        self.assertTrue(issued.payment_due_verified)
        self.assertFalse(issued.payment_received)

    def test_amount_delivery_or_window_mismatch_fails_closed(self):
        _,_,_,handoff=self.setup()
        wrong=self.receipt(handoff,total_cents=handoff.invoice_total_cents+1)
        with self.assertRaisesRegex(ValueError,"total mismatch"):
            verify_external_invoice_issuance(handoff,wrong)
        with self.assertRaisesRegex(ValueError,"delivery"):
            self.receipt(handoff,delivered_to_buyer=False)

    def test_unverified_external_receipt_fails_closed(self):
        _,_,_,handoff=self.setup()
        with self.assertRaisesRegex(ValueError,"externally verified"):
            self.receipt(handoff,verified=False)


if __name__=="__main__":
    unittest.main()
