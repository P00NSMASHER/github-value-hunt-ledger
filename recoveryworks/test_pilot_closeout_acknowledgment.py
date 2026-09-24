from __future__ import annotations

import unittest

from recoveryworks.pilot_closeout import build_pilot_closeout_snapshot
from recoveryworks.pilot_closeout_acknowledgment import (
    ContinuationInterest,
    build_external_buyer_closeout_receipt,
    verify_buyer_closeout_acknowledgment,
)
from recoveryworks.test_pilot_closeout import charter_and_kickoff, report


def closeout():
    charter,kickoff=charter_and_kickoff()
    snapshot=build_pilot_closeout_snapshot(
        charter,kickoff,report(recovered=10000,validated=50000,savings=250000),
        buyer_review_evidence_hash="3"*64,
        reviewed_at="2026-09-24T16:00:00Z")
    return charter,snapshot


def receipt(charter,snapshot,**overrides):
    values={
        "buyer_reviewer_id":"buyer-controller",
        "acknowledged_at":"2026-09-24T16:15:00Z",
        "recovered_cash_cents":snapshot.recovered_cash_cents,
        "validated_recovery_cents":snapshot.validated_recovery_cents,
        "prospective_savings_cents":snapshot.prospective_savings_cents,
        "realized_savings_cents":snapshot.realized_savings_cents,
        "anomaly_exposure_cents":snapshot.anomaly_exposure_cents,
        "reconciliation_drift_cents":snapshot.reconciliation_drift_cents,
        "accepts_recovery_outcomes":True,
        "accepts_savings_outcomes":True,
        "open_dispute_count":0,
        "continuation_interest":ContinuationInterest.REVIEW_MONTHLY_ASSURANCE,
        "source_hash":"4"*64,
        "source_locator":"buyer://closeout/ack-1",
        "verified":True,
    }
    values.update(overrides)
    return build_external_buyer_closeout_receipt(snapshot,charter,**values)


class PilotCloseoutAcknowledgmentTests(unittest.TestCase):
    def test_verified_exact_buyer_receipt_acknowledges_closeout_only(self):
        charter,snapshot=closeout()
        ack=verify_buyer_closeout_acknowledgment(
            snapshot,charter,receipt(charter,snapshot))
        self.assertEqual(ack.as_dict()["state"],"PILOT_CLOSEOUT_ACKNOWLEDGED")
        self.assertIs(
            ack.continuation_interest,
            ContinuationInterest.REVIEW_MONTHLY_ASSURANCE)
        self.assertFalse(ack.continuation_authorized)
        self.assertFalse(ack.invoice_authorized)
        self.assertFalse(ack.payment_due_asserted)

    def test_amount_drift_or_open_dispute_fails_closed(self):
        charter,snapshot=closeout()
        wrong=receipt(
            charter,snapshot,recovered_cash_cents=snapshot.recovered_cash_cents+1)
        with self.assertRaisesRegex(ValueError,"recovered_cash_cents mismatch"):
            verify_buyer_closeout_acknowledgment(snapshot,charter,wrong)
        disputed=receipt(charter,snapshot,open_dispute_count=1)
        with self.assertRaisesRegex(ValueError,"unresolved disputes"):
            verify_buyer_closeout_acknowledgment(snapshot,charter,disputed)

    def test_unverified_external_receipt_cannot_be_constructed(self):
        charter,snapshot=closeout()
        with self.assertRaisesRegex(ValueError,"must be externally verified"):
            receipt(charter,snapshot,verified=False)


if __name__=="__main__":
    unittest.main()
