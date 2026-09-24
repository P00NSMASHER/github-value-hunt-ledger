from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from recoveryworks.cloud_assurance_report import CloudAssuranceReport
from recoveryworks.pilot_charter import (
    build_recoveryworks_pilot_charter,
    pilot_charter_request_from_dict,
)
from recoveryworks.pilot_closeout import (
    build_pilot_closeout_snapshot,
    write_pilot_closeout_snapshot,
)
from recoveryworks.pilot_kickoff import (
    build_external_pilot_kickoff_authorization,
    build_pilot_kickoff_gate,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.test_pilot_charter import packet, request_dict


def charter_and_kickoff():
    charter = build_recoveryworks_pilot_charter(
        packet(), pilot_charter_request_from_dict(request_dict())
    )
    auth = build_external_pilot_kickoff_authorization(
        charter,
        authorized_by="buyer-controller",
        authorized_at="2026-09-24T14:00:00Z",
        expires_at="2026-09-25T14:00:00Z",
        retention_until="2026-10-31T23:59:59Z",
        source_hash="1"*64,
        source_locator="buyer://authorization/kickoff",
        verified=True,
    )
    kickoff = build_pilot_kickoff_gate(
        charter, auth, checked_at="2026-09-24T14:05:00Z"
    )
    return charter, kickoff


def report(recovered=10000, validated=50000, savings=250000):
    return CloudAssuranceReport(
        client_id="client",
        currency="USD",
        state_head_hash="2"*64,
        recovery_summary={
            "totals": {
                "potential_cents": 60000,
                "review_cents": 10000,
                "validated_cents": validated,
                "authorized_cents": 20000,
                "claimed_cents": 15000,
                "recovered_cents": recovered,
                "fee_cents": 0,
                "superseded_cents": 0,
            }
        },
        validated_recovery_packets=(),
        savings_summary={
            "estimated_savings_opportunity_cents": savings,
            "realized_savings_cents": 30000,
            "realized_measurement_count": 1,
        },
        savings_opportunities=(),
        diagnostics={
            "anomaly_count": 1,
            "estimated_anomaly_exposure_cents": 70000,
            "reconciliation_drift_count": 1,
            "reconciliation_drift_cents": 5000,
        },
        controls={
            "recovery_requires_verified_rule": True,
            "recovery_requires_verified_evidence": True,
            "estimated_savings_excluded_from_recovery": True,
            "anomaly_exposure_excluded_from_savings": True,
            "realized_savings_requires_verified_measurement": True,
            "cloud_mutation_authorized_by_report": False,
            "external_recovery_action_authorized_by_report": False,
        },
    )


class PilotCloseoutTests(unittest.TestCase):
    def test_success_fee_arithmetic_uses_recovered_cash_only(self):
        charter,kickoff=charter_and_kickoff()
        closeout=build_pilot_closeout_snapshot(
            charter,kickoff,report(recovered=10000,validated=500000,savings=999999),
            buyer_review_evidence_hash="3"*64,
            reviewed_at="2026-09-24T16:00:00Z")
        self.assertEqual(
            closeout.recovered_cash_success_fee_cents_arithmetic,2000)
        self.assertEqual(closeout.validated_recovery_cents,500000)
        self.assertEqual(closeout.prospective_savings_cents,999999)
        self.assertFalse(closeout.invoice_created)
        self.assertFalse(closeout.payment_due_asserted)
        self.assertFalse(closeout.payment_received)
        self.assertFalse(closeout.continuation_authorized)
        self.assertEqual(
            closeout.as_dict()["state"],"PILOT_CLOSEOUT_REVIEW_READY")

    def test_zero_recovered_cash_means_zero_success_fee(self):
        charter,kickoff=charter_and_kickoff()
        closeout=build_pilot_closeout_snapshot(
            charter,kickoff,report(recovered=0,validated=100000,savings=1000000),
            buyer_review_evidence_hash="3"*64,
            reviewed_at="2026-09-24T16:00:00Z")
        self.assertEqual(closeout.recovered_cash_success_fee_cents_arithmetic,0)

    def test_outputs_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            charter,kickoff=charter_and_kickoff()
            closeout=build_pilot_closeout_snapshot(
                charter,kickoff,report(),
                buyer_review_evidence_hash="3"*64,
                reviewed_at="2026-09-24T16:00:00Z")
            jp=Path(d)/"private"/"closeout.json"
            mp=Path(d)/"private"/"closeout.md"
            write_pilot_closeout_snapshot(closeout,json_path=jp,markdown_path=mp)
            self.assertTrue(private_permissions_verified(jp))
            self.assertTrue(private_permissions_verified(mp))


if __name__=="__main__":
    unittest.main()
