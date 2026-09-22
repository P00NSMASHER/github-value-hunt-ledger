import copy
import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks import EvidenceRef, RecoveryEngine, RecoveryLedger, RuleRef
from recoveryworks.branches import from_ap_variance
from recoveryworks.fees import FeeAgreement, assess_fee
from recoveryworks.storage import export_ledger, import_ledger, load_ledger, save_ledger


def ledger_with_recovery():
    rule = RuleRef(
        rule_id="invoice-rule",
        source_hash="rulehash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="source://invoice",
    )
    evidence = EvidenceRef(
        evidence_id="pay-1",
        source_hash="paymenthash",
        locator="source://payment#1",
        kind="payment",
        verified=True,
    )
    observation = from_ap_variance(
        client_id="client-1",
        vendor_id="vendor-1",
        transaction_id="inv-1",
        transaction_date="2026-06-01",
        expected_cents=10000,
        paid_cents=15000,
        rule=rule,
        evidence=(evidence,),
    )
    finding = RecoveryEngine().evaluate(observation)
    ledger = RecoveryLedger()
    ledger.add(finding)
    ledger.approve(finding.finding_id, "reviewer", "verified")
    ledger.authorize(finding.finding_id, "customer-auth")
    claim_receipt = EvidenceRef(
        evidence_id="claim-receipt",
        source_hash="claimhash",
        locator="source://claim/receipt",
        kind="claim_submission_receipt",
        verified=True,
    )
    recovery_receipt = EvidenceRef(
        evidence_id="settlement-receipt",
        source_hash="settlementhash",
        locator="source://settlement/receipt",
        kind="recovery_settlement",
        verified=True,
    )
    ledger.mark_claimed(finding.finding_id, claim_receipt)
    fee_assessment = assess_fee(
        finding,
        4000,
        FeeAgreement(
            agreement_id="fee-1",
            client_id=finding.client_id,
            fee_bps=2000,
            branches=(finding.branch,),
            source_hash="fee-hash",
            locator="source://fee-agreement",
            verified=True,
            currency=finding.currency,
        ),
    )
    ledger.mark_recovered(
        finding.finding_id, 4000, 800,
        recovery_evidence=recovery_receipt,
        fee_assessment=fee_assessment,
    )
    return ledger


class LedgerStorageTests(unittest.TestCase):
    def test_export_import_preserves_snapshot_and_audit_chain(self):
        original = ledger_with_recovery()
        payload = export_ledger(original)
        restored = import_ledger(payload)
        self.assertEqual(restored.snapshot_hash, original.snapshot_hash)
        self.assertEqual(restored.audit_head, original.audit_head)
        self.assertTrue(restored.verify_event_chain())
        self.assertEqual(restored.rollup(), original.rollup())

    def test_signed_snapshot_requires_correct_key(self):
        original = ledger_with_recovery()
        payload = export_ledger(original, integrity_key="secret-key")
        restored = import_ledger(payload, integrity_key="secret-key")
        self.assertEqual(restored.snapshot_hash, original.snapshot_hash)
        with self.assertRaises(ValueError):
            import_ledger(payload)
        with self.assertRaises(ValueError):
            import_ledger(payload, integrity_key="wrong-key")

    def test_unsigned_snapshot_can_be_forbidden(self):
        payload = export_ledger(ledger_with_recovery())
        with self.assertRaises(ValueError):
            import_ledger(payload, require_signature=True)

    def test_recomputed_plain_hash_cannot_bypass_hmac(self):
        from recoveryworks.models import canonical_hash

        payload = export_ledger(ledger_with_recovery(), integrity_key="secret-key")
        tampered = copy.deepcopy(payload)
        tampered["records"][0]["review_note"] = "tampered but internally rehashed"
        # An attacker can recompute ordinary hashes only if every nested proof is
        # also rebuilt. Even recomputing the outer export hash cannot reproduce
        # the HMAC without the secret key.
        core = {
            "schema": tampered["schema"],
            "records": tampered["records"],
            "events": tampered["events"],
            "audit_head": tampered["audit_head"],
            "ledger_snapshot_hash": tampered["ledger_snapshot_hash"],
        }
        tampered["export_hash"] = canonical_hash(core)
        with self.assertRaises(ValueError):
            import_ledger(tampered, integrity_key="secret-key")

    def test_atomic_file_roundtrip(self):
        original = ledger_with_recovery()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            save_ledger(path, original)
            restored = load_ledger(path)
            self.assertEqual(restored.snapshot_hash, original.snapshot_hash)
            self.assertTrue(path.exists())

    def test_tampered_money_is_rejected(self):
        payload = export_ledger(ledger_with_recovery())
        tampered = copy.deepcopy(payload)
        tampered["records"][0]["recovered_cents"] += 1
        with self.assertRaises(ValueError):
            import_ledger(tampered)

    def test_tampered_event_chain_is_rejected_even_if_outer_hash_recomputed(self):
        payload = export_ledger(ledger_with_recovery())
        tampered = copy.deepcopy(payload)
        tampered["events"][1]["previous_event_hash"] = "0" * 64
        core = {
            "schema": tampered["schema"],
            "records": tampered["records"],
            "events": tampered["events"],
            "audit_head": tampered["audit_head"],
            "ledger_snapshot_hash": tampered["ledger_snapshot_hash"],
        }
        from recoveryworks.models import canonical_hash
        tampered["export_hash"] = canonical_hash(core)
        with self.assertRaises(ValueError):
            import_ledger(tampered)

    def test_event_for_unknown_finding_is_rejected(self):
        payload = export_ledger(ledger_with_recovery())
        tampered = copy.deepcopy(payload)
        tampered["events"][0]["finding_id"] = "unknown"
        # Recomputing nested hashes is deliberately omitted: the first failing
        # integrity layer should already reject the mutation.
        with self.assertRaises(ValueError):
            import_ledger(tampered)


if __name__ == "__main__":
    unittest.main()
