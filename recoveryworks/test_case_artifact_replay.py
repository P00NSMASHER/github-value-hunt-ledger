from dataclasses import replace
import hashlib
import unittest

from recoveryworks import (
    AuthoritySnapshot,
    Branch,
    CalculationManifest,
    ChallengeReview,
    DeadlineAssessment,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    ReviewAttestation,
    RuleRef,
    SourceAttestation,
    freeze_case_proof,
    replay_case_source_artifacts,
    verify_case_artifact_replay,
)


CREATED = "2026-09-22T16:00:00Z"
AUTHORITY_BYTES = (
    b"SIMULATION ONLY. Executed freight agreement v3. "
    b"Reviewed maximum payable amount for the frozen shipment population."
)
INVOICE_BYTES = (
    b'{"invoice_id":"SIM-MASTER-INVOICE-2026-08",'
    b'"amount_usd":5250000.00,"carrier":"SIM-CARRIER-A"}'
)
TMS_BYTES = (
    b'{"period":"2026-08","shipment_count":1842,'
    b'"frozen_population_total_contract_usd":4250000.00}'
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frozen_bundle():
    rule = RuleRef(
        rule_id="rule:sim-seven-figure",
        source_hash=sha(AUTHORITY_BYTES),
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="sim://authority/carrier-master-agreement-v3#section=7.4",
        jurisdiction="US",
    )
    evidence = (
        EvidenceRef(
            evidence_id="SIM-EV-INVOICE",
            source_hash=sha(INVOICE_BYTES),
            locator="sim://evidence/carrier-portal/invoice-2026-08.json",
            kind="carrier_portal_invoice",
            verified=True,
        ),
        EvidenceRef(
            evidence_id="SIM-EV-TMS",
            source_hash=sha(TMS_BYTES),
            locator="sim://evidence/tms/august-2026-population.json",
            kind="tms_shipment_population",
            verified=True,
        ),
    )
    finding = RecoveryEngine().evaluate(RecoveryObservation(
        branch=Branch.FREIGHT,
        client_id="SIMCO-INDUSTRIAL",
        counterparty_id="SIM-CARRIER-A",
        reference="SIM-MASTER-INVOICE-2026-08",
        currency="USD",
        expected_cents=425_000_000,
        actual_cents=525_000_000,
        rule=rule,
        evidence=evidence,
        reason="SIMULATED_CONTRACT_RATE_OVERCHARGE",
        confidence_basis="synthetic contract + portal invoice + TMS population",
    ))
    authority = AuthoritySnapshot(
        authority_id="SIM-AUTH-CONTRACT-V3",
        authority_kind="executed_contract",
        source_hash=sha(AUTHORITY_BYTES),
        source_locator=rule.source_locator,
        effective_from="2026-01-01",
        effective_to=None,
        acquired_at="2026-09-22T16:00:00Z",
        verified_by="sim-authority-reviewer",
        verification_note="Synthetic executed agreement independently authenticated.",
        jurisdiction="US",
    )
    attestations = (
        SourceAttestation(
            evidence_id="SIM-EV-INVOICE",
            source_hash=sha(INVOICE_BYTES),
            locator=evidence[0].locator,
            acquisition_method="counterparty_portal_export",
            acquired_at="2026-09-22T16:01:00Z",
            authenticated_by="sim-evidence-reviewer-1",
            authentication_note="Synthetic portal export preserved before normalization.",
            verified_source=True,
        ),
        SourceAttestation(
            evidence_id="SIM-EV-TMS",
            source_hash=sha(TMS_BYTES),
            locator=evidence[1].locator,
            acquisition_method="client_read_only_tms_export",
            acquired_at="2026-09-22T16:02:00Z",
            authenticated_by="sim-evidence-reviewer-2",
            authentication_note="Synthetic TMS export preserved before normalization.",
            verified_source=True,
        ),
    )
    calculation = CalculationManifest(
        calculator_id="recoveryworks.freight.synthetic_hostile_exam",
        calculator_version="1",
        code_commit_sha="SIMULATED-COMMIT-SHA",
        input_manifest_hash="SIM-SCAN-BATCH-HASH",
        finding_proof_hash=finding.proof_hash,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        potential_recovery_cents=finding.potential_recovery_cents,
        trace_hash=sha(
            b"expected=425000000;actual=525000000;variance=100000000"
        ),
        created_at="2026-09-22T16:05:00Z",
    )
    reviews = (
        ReviewAttestation(
            review_id="SIM-REVIEW-1",
            finding_proof_hash=finding.proof_hash,
            reviewer_id="sim-reviewer-1",
            reviewer_role="freight_reviewer",
            decision="APPROVE",
            reviewed_at="2026-09-22T16:10:00Z",
            note="Synthetic primary reperformance complete.",
        ),
        ReviewAttestation(
            review_id="SIM-REVIEW-2",
            finding_proof_hash=finding.proof_hash,
            reviewer_id="sim-reviewer-2",
            reviewer_role="independent_reviewer",
            decision="APPROVE",
            reviewed_at="2026-09-22T16:12:00Z",
            note="Synthetic independent reperformance complete.",
        ),
    )
    challenge = ChallengeReview(
        challenge_id="SIM-CHALLENGE-1",
        finding_proof_hash=finding.proof_hash,
        reviewer_id="sim-red-team-reviewer",
        reviewed_at="2026-09-22T16:14:00Z",
        challenge="Search for amendments, credits, rebills, or contrary shipment facts.",
        conclusion="Synthetic negative-evidence search found none.",
        resolved=True,
        contrary_evidence_hashes=(sha(b"SIMULATED NEGATIVE SEARCH MANIFEST"),),
    )
    deadline = DeadlineAssessment(
        assessment_id="SIM-DEADLINE-1",
        finding_proof_hash=finding.proof_hash,
        governing_source_hash=authority.source_hash,
        source_locator="sim://authority/carrier-master-agreement-v3#claims-window",
        trigger="receipt of disputed invoice",
        assessed_at="2026-09-22T16:15:00Z",
        assessed_by="sim-deadline-reviewer",
        deadline_at="2026-12-31T23:59:59Z",
        conclusion="Synthetic claim must be asserted before reviewed deadline.",
    )
    return freeze_case_proof(
        finding=finding,
        authority=authority,
        source_attestations=attestations,
        calculation=calculation,
        reviews=reviews,
        challenges=(challenge,),
        deadlines=(deadline,),
        created_at="2026-09-22T16:20:00Z",
        created_by="sim-case-freezer",
        scan_batch_hash="SIM-SCAN-BATCH-HASH",
    )


class CaseArtifactReplayTests(unittest.TestCase):
    def test_exact_raw_bytes_replay_to_deterministic_receipt(self):
        bundle = frozen_bundle()
        evidence = {
            "SIM-EV-INVOICE": INVOICE_BYTES,
            "SIM-EV-TMS": TMS_BYTES,
        }
        first = replay_case_source_artifacts(
            bundle,
            authority_bytes=AUTHORITY_BYTES,
            evidence_bytes=evidence,
            replayed_at="2026-09-22T16:30:00Z",
            replayed_by="independent-examiner-1",
        )
        second = replay_case_source_artifacts(
            bundle,
            authority_bytes=AUTHORITY_BYTES,
            evidence_bytes=evidence,
            replayed_at="2026-09-22T16:30:00Z",
            replayed_by="independent-examiner-1",
        )
        verify_case_artifact_replay(first, bundle)
        self.assertEqual(first.receipt_hash, second.receipt_hash)
        self.assertEqual(len(first.entries), 3)
        self.assertEqual(first.case_bundle_hash, bundle.bundle_hash)

    def test_tampered_authority_bytes_are_rejected(self):
        bundle = frozen_bundle()
        with self.assertRaises(ValueError):
            replay_case_source_artifacts(
                bundle,
                authority_bytes=AUTHORITY_BYTES + b" altered",
                evidence_bytes={
                    "SIM-EV-INVOICE": INVOICE_BYTES,
                    "SIM-EV-TMS": TMS_BYTES,
                },
                replayed_at="2026-09-22T16:30:00Z",
                replayed_by="examiner",
            )

    def test_tampered_evidence_bytes_are_rejected(self):
        bundle = frozen_bundle()
        with self.assertRaises(ValueError):
            replay_case_source_artifacts(
                bundle,
                authority_bytes=AUTHORITY_BYTES,
                evidence_bytes={
                    "SIM-EV-INVOICE": INVOICE_BYTES + b" altered",
                    "SIM-EV-TMS": TMS_BYTES,
                },
                replayed_at="2026-09-22T16:30:00Z",
                replayed_by="examiner",
            )

    def test_missing_or_extra_artifacts_fail_closed(self):
        bundle = frozen_bundle()
        with self.assertRaises(ValueError):
            replay_case_source_artifacts(
                bundle,
                authority_bytes=AUTHORITY_BYTES,
                evidence_bytes={"SIM-EV-INVOICE": INVOICE_BYTES},
                replayed_at="2026-09-22T16:30:00Z",
                replayed_by="examiner",
            )
        with self.assertRaises(ValueError):
            replay_case_source_artifacts(
                bundle,
                authority_bytes=AUTHORITY_BYTES,
                evidence_bytes={
                    "SIM-EV-INVOICE": INVOICE_BYTES,
                    "SIM-EV-TMS": TMS_BYTES,
                    "UNDECLARED": b"extra",
                },
                replayed_at="2026-09-22T16:30:00Z",
                replayed_by="examiner",
            )

    def test_receipt_tampering_is_detected(self):
        bundle = frozen_bundle()
        receipt = replay_case_source_artifacts(
            bundle,
            authority_bytes=AUTHORITY_BYTES,
            evidence_bytes={
                "SIM-EV-INVOICE": INVOICE_BYTES,
                "SIM-EV-TMS": TMS_BYTES,
            },
            replayed_at="2026-09-22T16:30:00Z",
            replayed_by="independent-examiner-1",
        )
        tampered = replace(receipt, replayed_by="different-examiner")
        with self.assertRaises(ValueError):
            verify_case_artifact_replay(tampered, bundle)


if __name__ == "__main__":
    unittest.main()
