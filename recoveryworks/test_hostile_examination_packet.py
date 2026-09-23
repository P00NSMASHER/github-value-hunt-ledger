from dataclasses import replace
import unittest

from recoveryworks import (
    DurableRecoveryLedger,
    build_hostile_examination_packet,
    create_proof_seal,
    replay_case_calculation,
    replay_case_source_artifacts,
    verify_hostile_examination_packet,
)
from recoveryworks.test_case_artifact_replay import (
    AUTHORITY_BYTES,
    INVOICE_BYTES,
    TMS_BYTES,
    frozen_bundle,
)


SECRET_KEY = b"simulation-only-hostile-exam-key-material-0001"
TRACE_BYTES = b"expected=425000000;actual=525000000;variance=100000000"


def build_exam():
    bundle = frozen_bundle()
    artifact_receipt = replay_case_source_artifacts(
        bundle,
        authority_bytes=AUTHORITY_BYTES,
        evidence_bytes={
            "SIM-EV-INVOICE": INVOICE_BYTES,
            "SIM-EV-TMS": TMS_BYTES,
        },
        replayed_at="2026-09-22T16:30:00Z",
        replayed_by="sim-independent-examiner",
    )
    calculation_receipt = replay_case_calculation(
        bundle,
        artifact_receipt,
        calculator_id=bundle.calculation.calculator_id,
        calculator_version=bundle.calculation.calculator_version,
        code_commit_sha=bundle.calculation.code_commit_sha,
        input_manifest_hash=bundle.calculation.input_manifest_hash,
        expected_cents=425_000_000,
        actual_cents=525_000_000,
        trace_bytes=TRACE_BYTES,
        reproduced_at="2026-09-22T16:31:00Z",
        reproduced_by="sim-independent-calculation-examiner",
    )

    ledger = DurableRecoveryLedger()
    finding = bundle.finding
    ledger.add(finding)
    ledger.approve(
        finding.finding_id,
        "sim-reviewer-1",
        "Synthetic primary review matches frozen case.",
    )
    ledger.independent_approve(
        finding.finding_id,
        "sim-reviewer-2",
        "Synthetic independent review matches frozen case.",
    )
    journal_head = ledger.journal.head_hash
    proof_seal = create_proof_seal(
        bundle,
        seal_id="SIM-SEAL-HOSTILE-EXAM-1",
        key_id="sim-kms-key-1",
        secret_key=SECRET_KEY,
        journal_head_hash=journal_head,
        sealed_at="2026-09-22T16:32:00Z",
    )
    packet = build_hostile_examination_packet(
        bundle,
        artifact_receipt,
        calculation_receipt,
        proof_seal,
        journal_head_hash=journal_head,
        secret_key=SECRET_KEY,
        key_id="sim-kms-key-1",
        assembled_at="2026-09-22T16:33:00Z",
        assembled_by="sim-hostile-exam-assembler",
    )
    return (
        bundle,
        artifact_receipt,
        calculation_receipt,
        ledger,
        proof_seal,
        packet,
    )


class HostileExaminationPacketTests(unittest.TestCase):
    def test_simulated_million_dollar_case_is_fully_reproducible(self):
        (
            bundle,
            artifact_receipt,
            calculation_receipt,
            ledger,
            proof_seal,
            packet,
        ) = build_exam()

        exported = ledger.export_bundle()
        restored = DurableRecoveryLedger.from_bundle(exported)
        self.assertEqual(restored.journal.head_hash, ledger.journal.head_hash)

        verify_hostile_examination_packet(
            packet,
            bundle,
            artifact_receipt,
            calculation_receipt,
            proof_seal,
            journal_head_hash=restored.journal.head_hash,
            secret_key=SECRET_KEY,
        )
        self.assertEqual(bundle.finding.potential_recovery_cents, 100_000_000)
        self.assertEqual(
            packet.artifact_replay_receipt_hash,
            artifact_receipt.receipt_hash,
        )
        self.assertEqual(
            packet.calculation_replay_receipt_hash,
            calculation_receipt.receipt_hash,
        )

    def test_recalculation_wrong_expected_amount_fails(self):
        bundle = frozen_bundle()
        artifacts = replay_case_source_artifacts(
            bundle,
            authority_bytes=AUTHORITY_BYTES,
            evidence_bytes={
                "SIM-EV-INVOICE": INVOICE_BYTES,
                "SIM-EV-TMS": TMS_BYTES,
            },
            replayed_at="2026-09-22T16:30:00Z",
            replayed_by="examiner",
        )
        with self.assertRaises(ValueError):
            replay_case_calculation(
                bundle,
                artifacts,
                calculator_id=bundle.calculation.calculator_id,
                calculator_version=bundle.calculation.calculator_version,
                code_commit_sha=bundle.calculation.code_commit_sha,
                input_manifest_hash=bundle.calculation.input_manifest_hash,
                expected_cents=424_999_999,
                actual_cents=525_000_000,
                trace_bytes=TRACE_BYTES,
                reproduced_at="2026-09-22T16:31:00Z",
                reproduced_by="examiner",
            )

    def test_recalculation_wrong_trace_fails(self):
        bundle = frozen_bundle()
        artifacts = replay_case_source_artifacts(
            bundle,
            authority_bytes=AUTHORITY_BYTES,
            evidence_bytes={
                "SIM-EV-INVOICE": INVOICE_BYTES,
                "SIM-EV-TMS": TMS_BYTES,
            },
            replayed_at="2026-09-22T16:30:00Z",
            replayed_by="examiner",
        )
        with self.assertRaises(ValueError):
            replay_case_calculation(
                bundle,
                artifacts,
                calculator_id=bundle.calculation.calculator_id,
                calculator_version=bundle.calculation.calculator_version,
                code_commit_sha=bundle.calculation.code_commit_sha,
                input_manifest_hash=bundle.calculation.input_manifest_hash,
                expected_cents=425_000_000,
                actual_cents=525_000_000,
                trace_bytes=TRACE_BYTES + b";hidden-adjustment=1",
                reproduced_at="2026-09-22T16:31:00Z",
                reproduced_by="examiner",
            )

    def test_recalculation_wrong_code_commit_fails(self):
        bundle = frozen_bundle()
        artifacts = replay_case_source_artifacts(
            bundle,
            authority_bytes=AUTHORITY_BYTES,
            evidence_bytes={
                "SIM-EV-INVOICE": INVOICE_BYTES,
                "SIM-EV-TMS": TMS_BYTES,
            },
            replayed_at="2026-09-22T16:30:00Z",
            replayed_by="examiner",
        )
        with self.assertRaises(ValueError):
            replay_case_calculation(
                bundle,
                artifacts,
                calculator_id=bundle.calculation.calculator_id,
                calculator_version=bundle.calculation.calculator_version,
                code_commit_sha="f" * 40,
                input_manifest_hash=bundle.calculation.input_manifest_hash,
                expected_cents=425_000_000,
                actual_cents=525_000_000,
                trace_bytes=TRACE_BYTES,
                reproduced_at="2026-09-22T16:31:00Z",
                reproduced_by="examiner",
            )

    def test_wrong_journal_head_breaks_packet_verification(self):
        (
            bundle,
            artifacts,
            calculation,
            _ledger,
            proof_seal,
            packet,
        ) = build_exam()
        with self.assertRaises(ValueError):
            verify_hostile_examination_packet(
                packet,
                bundle,
                artifacts,
                calculation,
                proof_seal,
                journal_head_hash="tampered-journal-head",
                secret_key=SECRET_KEY,
            )

    def test_packet_tampering_breaks_signature(self):
        (
            bundle,
            artifacts,
            calculation,
            ledger,
            proof_seal,
            packet,
        ) = build_exam()
        tampered = replace(packet, assembled_by="different-assembler")
        with self.assertRaises(ValueError):
            verify_hostile_examination_packet(
                tampered,
                bundle,
                artifacts,
                calculation,
                proof_seal,
                journal_head_hash=ledger.journal.head_hash,
                secret_key=SECRET_KEY,
            )

    def test_wrong_secret_key_breaks_packet_verification(self):
        (
            bundle,
            artifacts,
            calculation,
            ledger,
            proof_seal,
            packet,
        ) = build_exam()
        with self.assertRaises(ValueError):
            verify_hostile_examination_packet(
                packet,
                bundle,
                artifacts,
                calculation,
                proof_seal,
                journal_head_hash=ledger.journal.head_hash,
                secret_key=b"different-simulation-key-material-0000000001",
            )

    def test_replay_chronology_fails_closed(self):
        bundle = frozen_bundle()
        with self.assertRaises(ValueError):
            replay_case_source_artifacts(
                bundle,
                authority_bytes=AUTHORITY_BYTES,
                evidence_bytes={
                    "SIM-EV-INVOICE": INVOICE_BYTES,
                    "SIM-EV-TMS": TMS_BYTES,
                },
                replayed_at="2026-09-22T16:19:59Z",
                replayed_by="examiner",
            )


if __name__ == "__main__":
    unittest.main()
