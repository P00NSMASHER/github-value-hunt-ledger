import unittest

from recoveryworks import EvidenceRef, RecoveryEngine, RecoveryLedger, RuleRef
from recoveryworks.branches import from_ap_variance
from recoveryworks.packets import (
    build_client_portfolio_packet,
    build_recovery_packet,
    submission_ready,
)


def ev():
    return EvidenceRef(
        evidence_id="payment-1",
        source_hash="paymenthash",
        locator="source://payment#1",
        kind="payment",
        verified=True,
    )


def rule():
    return RuleRef(
        rule_id="ap-control",
        source_hash="rulehash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="source://policy#1",
    )


def finding(client_id="client-a", reference="pay-1"):
    observation = from_ap_variance(
        client_id=client_id,
        vendor_id="vendor",
        transaction_id=reference,
        transaction_date="2026-06-01",
        expected_cents=10000,
        paid_cents=15000,
        rule=rule(),
        evidence=(ev(),),
    )
    return RecoveryEngine().evaluate(observation)


class PacketTests(unittest.TestCase):
    def test_packet_is_not_submission_ready_before_human_and_customer_gates(self):
        ledger = RecoveryLedger()
        record = ledger.add(finding())
        packet = build_recovery_packet(record)
        self.assertFalse(submission_ready(packet))
        self.assertTrue(packet.gates["finding_validated"])
        self.assertFalse(packet.gates["reviewer_approved"])
        self.assertFalse(packet.gates["customer_authorized"])

    def test_packet_becomes_ready_only_at_authorized_state(self):
        ledger = RecoveryLedger()
        f = finding()
        ledger.add(f)
        ledger.approve(f.finding_id, "reviewer", "checked")
        ledger.authorize(f.finding_id, "customer-auth")
        packet = build_recovery_packet(ledger.get(f.finding_id))
        self.assertTrue(submission_ready(packet))
        self.assertEqual(len(packet.packet_hash), 64)

        claim_receipt = EvidenceRef(
            evidence_id="claim-receipt",
            source_hash="claimhash",
            locator="source://claim/receipt",
            kind="claim_submission_receipt",
            verified=True,
        )
        ledger.mark_claimed(f.finding_id, claim_receipt)
        claimed_packet = build_recovery_packet(ledger.get(f.finding_id))
        self.assertFalse(submission_ready(claimed_packet))
        self.assertEqual(claimed_packet.case_state, "CLAIMED")
        self.assertEqual(
            claimed_packet.claim_evidence["proof_hash"],
            claim_receipt.proof_hash,
        )

    def test_client_portfolio_packet_never_rolls_up_other_clients(self):
        ledger = RecoveryLedger()
        a = finding("client-a", "pay-a")
        b = finding("client-b", "pay-b")
        ledger.add(a)
        ledger.add(b)
        report = build_client_portfolio_packet(ledger, "client-a")
        self.assertEqual(report["totals"]["cases"], 1)
        self.assertEqual(report["totals"]["potential_cents"], 5000)
        self.assertEqual(len(report["portfolio_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
