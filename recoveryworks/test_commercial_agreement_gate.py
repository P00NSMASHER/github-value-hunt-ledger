from __future__ import annotations

import unittest

from recoveryworks.commercial_agreement_gate import (
    build_commercial_fee_draft_readiness,
    build_external_finalized_commercial_agreement,
)
from recoveryworks.pilot_closeout_acknowledgment import (
    verify_buyer_closeout_acknowledgment,
)
from recoveryworks.test_pilot_closeout_acknowledgment import closeout, receipt


def fixture(**agreement_overrides):
    charter,snapshot=closeout()
    ack=verify_buyer_closeout_acknowledgment(
        snapshot,charter,receipt(charter,snapshot))
    values={
        "agreement_reference":"agreement-001",
        "currency":"USD",
        "diagnostic_fee_cents":500000,
        "recovered_cash_success_fee_bps":2500,
        "monthly_assurance_fee_cents":300000,
        "payment_terms_days":30,
        "diagnostic_fee_applicable":True,
        "success_fee_applicable":True,
        "monthly_assurance_separately_accepted":False,
        "effective_at":"2026-09-24T16:30:00Z",
        "source_hash":"5"*64,
        "source_locator":"agreement://final/001",
        "verified":True,
        "externally_finalized":True,
    }
    values.update(agreement_overrides)
    agreement=build_external_finalized_commercial_agreement(
        charter,ack,**values)
    return charter,snapshot,ack,agreement


class CommercialAgreementGateTests(unittest.TestCase):
    def test_finalized_agreement_terms_drive_fee_readiness(self):
        charter,snapshot,ack,agreement=fixture()
        ready=build_commercial_fee_draft_readiness(
            charter,snapshot,ack,agreement)
        self.assertEqual(ready.recovered_cash_cents,10000)
        self.assertEqual(ready.recovered_cash_success_fee_cents,2500)
        self.assertEqual(ready.closeout_fee_total_cents,502500)
        self.assertTrue(ready.pricing_differs_from_charter_hypothesis)
        self.assertEqual(
            ready.as_dict()["state"],"COMMERCIAL_FEE_DRAFT_READY")
        self.assertFalse(ready.invoice_issuance_performed)
        self.assertFalse(ready.payment_due_asserted)
        self.assertFalse(ready.payment_collected)

    def test_success_fee_never_uses_validated_or_savings_amounts(self):
        charter,snapshot,ack,agreement=fixture(
            diagnostic_fee_cents=0,
            recovered_cash_success_fee_bps=5000)
        ready=build_commercial_fee_draft_readiness(
            charter,snapshot,ack,agreement)
        self.assertEqual(snapshot.validated_recovery_cents,50000)
        self.assertEqual(snapshot.prospective_savings_cents,250000)
        self.assertEqual(ready.recovered_cash_success_fee_cents,5000)
        self.assertEqual(ready.closeout_fee_total_cents,5000)

    def test_unverified_or_unfinalized_agreement_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"externally verified"):
            fixture(verified=False)
        with self.assertRaisesRegex(ValueError,"finalized external agreement"):
            fixture(externally_finalized=False)


if __name__=="__main__":
    unittest.main()
