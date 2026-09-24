from recoveryworks.test_support import source_hash as H
import copy
from dataclasses import replace
import hashlib
import unittest

from recoveryworks import (
    Branch,
    DurableRecoveryLedger,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    RuleRef,
    SettlementEvidence,
)


def verified_finding():
    rule = RuleRef(
        rule_id="rule:durable",
        source_hash=H("rulehash"),
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="source://contract#1",
    )
    evidence = EvidenceRef(
        evidence_id="ev:durable",
        source_hash=H("evhash"),
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


def settlement(ledger, finding_id, recovered_cents):
    return SettlementEvidence(
        settlement_id="settlement-1",
        finding_id=finding_id,
        source_hash=hashlib.sha256(b"settlement-1").hexdigest(),
        source_locator="bank://remittance/settlement-1",
        observed_at=ledger.get(finding_id).updated_at,
        recovered_cents=recovered_cents,
        currency="USD",
        verified=True,
    )


class DurableLedgerTests(unittest.TestCase):
    def test_round_trip_replays_full_lifecycle_and_economics(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        ledger.approve(finding.finding_id, "reviewer-1", "verified")
        ledger.authorize(finding.finding_id, "customer-auth-1")
        ledger.mark_claimed(finding.finding_id)
        ledger.mark_recovered(
            finding.finding_id,
            settlement(ledger, finding.finding_id, 4000),
            800,
        )

        bundle = ledger.export_bundle()
        restored = DurableRecoveryLedger.from_bundle(bundle)

        self.assertEqual(restored.rollup(), ledger.rollup())
        self.assertEqual(restored.journal.head_hash, ledger.journal.head_hash)
        self.assertEqual(len(restored.journal.events()), 5)
        self.assertEqual(restored.get(finding.finding_id).recovered_cents, 4000)
        self.assertEqual(restored.get(finding.finding_id).fee_cents, 800)
        self.assertEqual(
            restored.get(finding.finding_id).updated_at,
            ledger.get(finding.finding_id).updated_at,
        )
        self.assertEqual(
            restored.get(finding.finding_id).settlement_evidence_hash,
            ledger.get(finding.finding_id).settlement_evidence_hash,
        )

    def test_post_authorization_review_mutation_is_blocked(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        ledger.approve(finding.finding_id, "reviewer-1", "verified")
        ledger.authorize(finding.finding_id, "customer-auth-1")

        with self.assertRaisesRegex(ValueError, "case state VALIDATED"):
            ledger.approve(finding.finding_id, "reviewer-2", "late mutation")
        with self.assertRaisesRegex(ValueError, "case state VALIDATED"):
            ledger.authorize(finding.finding_id, "replacement-auth")

    def test_unverified_or_preclaim_settlement_cannot_create_recovered_dollars(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding, occurred_at="2026-09-23T12:00:00Z")
        ledger.approve(
            finding.finding_id,
            "reviewer-1",
            "verified",
            occurred_at="2026-09-23T12:01:00Z",
        )
        ledger.authorize(
            finding.finding_id,
            "customer-auth-1",
            occurred_at="2026-09-23T12:02:00Z",
        )
        ledger.mark_claimed(
            finding.finding_id,
            occurred_at="2026-09-23T12:03:00Z",
        )

        unverified = SettlementEvidence(
            settlement_id="settlement-unverified",
            finding_id=finding.finding_id,
            source_hash=hashlib.sha256(b"unverified").hexdigest(),
            source_locator="bank://remittance/unverified",
            observed_at="2026-09-23T12:04:00Z",
            recovered_cents=4000,
            currency="USD",
            verified=False,
        )
        with self.assertRaisesRegex(ValueError, "externally verified"):
            ledger.mark_recovered(
                finding.finding_id,
                unverified,
                occurred_at="2026-09-23T12:05:00Z",
            )

        predating = SettlementEvidence(
            settlement_id="settlement-too-early",
            finding_id=finding.finding_id,
            source_hash=hashlib.sha256(b"too-early").hexdigest(),
            source_locator="bank://remittance/too-early",
            observed_at="2026-09-23T12:02:59Z",
            recovered_cents=4000,
            currency="USD",
            verified=True,
        )
        with self.assertRaisesRegex(ValueError, "cannot predate the claim"):
            ledger.mark_recovered(
                finding.finding_id,
                predating,
                occurred_at="2026-09-23T12:05:00Z",
            )

    def test_journal_rejects_backdated_transition(self):
        finding = verified_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding, occurred_at="2026-09-23T12:00:00Z")
        with self.assertRaisesRegex(ValueError, "cannot predate|nondecreasing"):
            ledger.approve(
                finding.finding_id,
                "reviewer-1",
                "verified",
                occurred_at="2026-09-23T11:59:59Z",
            )

    def test_global_journal_time_failure_does_not_mutate_an_older_case(self):
        first = verified_finding()
        second = replace(first, finding_id=f"{first.finding_id}:second")
        ledger = DurableRecoveryLedger()
        ledger.add(first, occurred_at="2026-09-23T12:00:00Z")
        ledger.add(second, occurred_at="2026-09-23T13:00:00Z")
        before = ledger.get(first.finding_id)
        event_count = len(ledger.journal.events())

        with self.assertRaisesRegex(ValueError, "nondecreasing"):
            ledger.approve(
                first.finding_id,
                "reviewer-1",
                "verified",
                occurred_at="2026-09-23T12:30:00Z",
            )

        self.assertEqual(ledger.get(first.finding_id), before)
        self.assertEqual(len(ledger.journal.events()), event_count)

    def test_legacy_bundle_without_authenticated_times_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, "no authenticated event timestamps"):
            DurableRecoveryLedger.from_bundle({"schema": 1})

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
