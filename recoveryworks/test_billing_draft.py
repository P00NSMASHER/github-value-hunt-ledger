from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.billing_draft import (
    build_unissued_billing_draft,
    write_unissued_billing_draft,
)
from recoveryworks.commercial_agreement_gate import (
    build_commercial_fee_draft_readiness,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.test_commercial_agreement_gate import fixture


class BillingDraftTests(unittest.TestCase):
    def test_draft_contains_only_agreement_supported_closeout_fees(self):
        charter,snapshot,ack,agreement=fixture(
            diagnostic_fee_cents=500000,
            recovered_cash_success_fee_bps=2500,
            monthly_assurance_fee_cents=300000,
            monthly_assurance_separately_accepted=True)
        ready=build_commercial_fee_draft_readiness(
            charter,snapshot,ack,agreement)
        draft=build_unissued_billing_draft(
            agreement,ready,draft_reference="DRAFT-ENG-001",
            created_at="2026-09-24T17:00:00Z")
        self.assertEqual(draft.total_cents,502500)
        self.assertEqual(
            [x.code for x in draft.line_items],
            ["PILOT_DIAGNOSTIC_FEE","VERIFIED_RECOVERED_CASH_SUCCESS_FEE"])
        self.assertEqual(draft.monthly_assurance_option_cents,300000)
        self.assertTrue(draft.monthly_assurance_separately_accepted)
        self.assertEqual(draft.as_dict()["state"],"DRAFT_NOT_ISSUED")
        self.assertFalse(draft.issued)
        self.assertFalse(draft.sent)
        self.assertFalse(draft.payment_due_asserted)
        self.assertFalse(draft.payment_received)
        self.assertFalse(draft.payment_instructions_included)

    def test_validated_recovery_and_savings_never_become_line_items(self):
        charter,snapshot,ack,agreement=fixture(
            diagnostic_fee_cents=0,
            recovered_cash_success_fee_bps=1000,
            monthly_assurance_fee_cents=999999,
            monthly_assurance_separately_accepted=False)
        ready=build_commercial_fee_draft_readiness(
            charter,snapshot,ack,agreement)
        draft=build_unissued_billing_draft(
            agreement,ready,draft_reference="DRAFT-2",
            created_at="2026-09-24T17:00:00Z")
        self.assertEqual(snapshot.validated_recovery_cents,50000)
        self.assertEqual(snapshot.prospective_savings_cents,250000)
        self.assertEqual(draft.total_cents,1000)
        self.assertEqual(len(draft.line_items),1)
        self.assertEqual(
            draft.line_items[0].code,
            "VERIFIED_RECOVERED_CASH_SUCCESS_FEE")

    def test_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            charter,snapshot,ack,agreement=fixture()
            ready=build_commercial_fee_draft_readiness(
                charter,snapshot,ack,agreement)
            draft=build_unissued_billing_draft(
                agreement,ready,draft_reference="DRAFT-PRIVATE",
                created_at="2026-09-24T17:00:00Z")
            jp=Path(d)/"private"/"billing-draft.json"
            mp=Path(d)/"private"/"billing-draft.md"
            write_unissued_billing_draft(draft,json_path=jp,markdown_path=mp)
            self.assertTrue(private_permissions_verified(jp))
            self.assertTrue(private_permissions_verified(mp))
            self.assertIn(
                "NOT ISSUED",mp.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
