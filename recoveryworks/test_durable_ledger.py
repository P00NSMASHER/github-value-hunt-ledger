import copy
import unittest

from recoveryworks import (
    Branch,
    DurableRecoveryLedger,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    RuleRef,
)


def verified_finding():
    rule = RuleRef(
        rule_id="rule:durable",
        source_hash="rulehash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="source://contract#1",
    )
    evidence = EvidenceRef(
        evidence_id="ev:durable",
        source_hash="evhash",
        locator="source://invoice#1",
        kind="invoice",
        verified=True,
    )
    return RecoveryEngine().evaluate(RecoveryObservation(
        branch=Branch.FREIGHT,
        client_id="client-1",
        counterparty_id="carrier-1",
        reference="invoice-1",
        currency="USD",
        expected_cents=10000,
        actual_cents=15000,
        rule=rule,
        evidence=(evidence,),
        reason="OVERCHARGE",
        confidence_basis="verified contract + invoice",
    ))


class DurableLedgerTests(unittest.TestCase):
    def test_round_trip_replays_full_lifecycle_and_economics(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        ledger.approve(finding.finding_id, "reviewer-1", "verified")
        ledger.authorize(finding.finding_id, "customer-auth-1")
        ledger.mark_claimed(finding.finding_id)
        ledger.mark_recovered(finding.finding_id, 4000, 800)

        bundle = ledger.export_bundle()
        restored = DurableRecoveryLedger.from_bundle(bundle)

        self.assertEqual(restored.rollup(), ledger.rollup())
        self.assertEqual(restored.journal.head_hash, ledger.journal.head_hash)
        self.assertEqual(len(restored.journal.events()), 5)
        self.assertEqual(restored.get(finding.finding_id).recovered_cents, 4000)
        self.assertEqual(restored.get(finding.finding_id).fee_cents, 800)

    def test_identical_add_dedupes_without_duplicate_journal_event(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        ledger.add(finding)
        self.assertEqual(len(ledger.journal.events()), 1)
        self.assertEqual(ledger.rollup()["totals"]["cases"], 1)

    def test_event_payload_tampering_is_detected(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        bundle = copy.deepcopy(ledger.export_bundle())
        bundle["journal"]["events"][0]["payload"]["finding"]["actual_cents"] = 999999
        with self.assertRaises(ValueError):
            DurableRecoveryLedger.from_bundle(bundle)

    def test_event_hash_tampering_is_detected(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        bundle = copy.deepcopy(ledger.export_bundle())
        bundle["journal"]["events"][0]["event_hash"] = "bad"
        with self.assertRaises(ValueError):
            DurableRecoveryLedger.from_bundle(bundle)

    def test_head_hash_tampering_is_detected(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        bundle = copy.deepcopy(ledger.export_bundle())
        bundle["journal"]["head_hash"] = "bad"
        with self.assertRaises(ValueError):
            DurableRecoveryLedger.from_bundle(bundle)

    def test_rollup_tampering_is_detected_after_valid_journal_replay(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        bundle = copy.deepcopy(ledger.export_bundle())
        bundle["rollup"]["totals"]["potential_cents"] = 1
        with self.assertRaises(ValueError):
            DurableRecoveryLedger.from_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
