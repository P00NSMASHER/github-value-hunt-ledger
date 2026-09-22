import copy
import unittest

from recoveryworks import (
    AuthorityRegistry,
    AuthoritySnapshot,
    Branch,
    CalculationManifest,
    ChallengeReview,
    DeadlineAssessment,
    DurableRecoveryLedger,
    EvidenceRef,
    RecoveryEngine,
    RecoveryObservation,
    ReviewAttestation,
    RuleRef,
    SourceAttestation,
    authorize_case_action,
    freeze_case_proof,
    prepare_external_action,
    verify_external_action,
)


CREATED = "2026-09-22T16:00:00Z"


def million_finding():
    rule = RuleRef(
        rule_id="rule:seven-figure",
        source_hash="authority-source-hash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="vault://authority/contract-v3#section=7.4",
        jurisdiction="US",
    )
    evidence = EvidenceRef(
        evidence_id="ev:invoice:1",
        source_hash="invoice-source-hash",
        locator="vault://evidence/invoice-1#page=2",
        kind="invoice",
        verified=True,
    )
    return RecoveryEngine().evaluate(RecoveryObservation(
        branch=Branch.FREIGHT,
        client_id="client-1",
        counterparty_id="carrier-1",
        reference="invoice-1",
        currency="USD",
        expected_cents=10_000_000,
        actual_cents=110_000_000,
        rule=rule,
        evidence=(evidence,),
        reason="CONTRACT_RATE_OVERCHARGE",
        confidence_basis="verified contract and invoice",
    ))


def authority():
    return AuthoritySnapshot(
        authority_id="auth:contract-v3",
        authority_kind="executed_contract",
        source_hash="authority-source-hash",
        source_locator="vault://authority/contract-v3#section=7.4",
        effective_from="2026-01-01",
        effective_to=None,
        acquired_at=CREATED,
        verified_by="authority-reviewer",
        verification_note="Executed amendment chain verified against client repository",
        jurisdiction="US",
    )


def source_attestation():
    return SourceAttestation(
        evidence_id="ev:invoice:1",
        source_hash="invoice-source-hash",
        locator="vault://evidence/invoice-1#page=2",
        acquisition_method="counterparty_portal_export",
        acquired_at=CREATED,
        authenticated_by="evidence-reviewer",
        authentication_note="Portal export preserved before normalization",
        verified_source=True,
    )


def calculation(finding):
    return CalculationManifest(
        calculator_id="recoveryworks.freight",
        calculator_version="3",
        code_commit_sha="abc123def456",
        input_manifest_hash="scan-batch-hash",
        finding_proof_hash=finding.proof_hash,
        expected_cents=finding.expected_cents,
        actual_cents=finding.actual_cents,
        potential_recovery_cents=finding.potential_recovery_cents,
        trace_hash="calculation-trace-hash",
        created_at=CREATED,
    )


def review(finding, rid, reviewer, role):
    return ReviewAttestation(
        review_id=rid,
        finding_proof_hash=finding.proof_hash,
        reviewer_id=reviewer,
        reviewer_role=role,
        decision="APPROVE",
        reviewed_at=CREATED,
        note="Reperformed calculation and checked controlling evidence.",
    )


def challenge(finding, reviewer="red-team-reviewer", resolved=True):
    return ChallengeReview(
        challenge_id="challenge:1",
        finding_proof_hash=finding.proof_hash,
        reviewer_id=reviewer,
        reviewed_at=CREATED,
        challenge="Identify evidence or amendments that would defeat the finding.",
        conclusion="No superseding amendment, credit, rebill, or contrary shipment fact found.",
        resolved=resolved,
        contrary_evidence_hashes=("negative-search-manifest-hash",),
    )


def deadline(finding):
    return DeadlineAssessment(
        assessment_id="deadline:1",
        finding_proof_hash=finding.proof_hash,
        governing_source_hash="authority-source-hash",
        source_locator="vault://authority/contract-v3#claims-window",
        trigger="receipt of disputed invoice",
        assessed_at=CREATED,
        assessed_by="deadline-reviewer",
        deadline_at="2026-12-31T23:59:59Z",
        conclusion="External action must occur by assessed deadline.",
    )


def frozen_bundle():
    finding = million_finding()
    return freeze_case_proof(
        finding=finding,
        authority=authority(),
        source_attestations=(source_attestation(),),
        calculation=calculation(finding),
        reviews=(
            review(finding, "review:1", "reviewer-1", "freight_reviewer"),
            review(finding, "review:2", "reviewer-2", "independent_reviewer"),
        ),
        challenges=(challenge(finding),),
        deadlines=(deadline(finding),),
        created_at=CREATED,
        created_by="case-freezer",
        scan_batch_hash="scan-batch-hash",
    )


class SevenFigureAssuranceTests(unittest.TestCase):
    def test_authority_registry_is_content_addressed_and_tamper_evident(self):
        registry = AuthorityRegistry()
        registry.register(authority())
        exported = registry.export()
        restored = AuthorityRegistry.from_export(exported)
        self.assertEqual(restored.registry_hash, registry.registry_hash)
        restored.resolve_rule(million_finding().rule)

        tampered = copy.deepcopy(exported)
        tampered["authorities"][0]["verification_note"] = "changed"
        with self.assertRaises(ValueError):
            AuthorityRegistry.from_export(tampered)

    def test_seven_figure_bundle_requires_two_approving_reviewers(self):
        finding = million_finding()
        with self.assertRaises(ValueError):
            freeze_case_proof(
                finding=finding,
                authority=authority(),
                source_attestations=(source_attestation(),),
                calculation=calculation(finding),
                reviews=(review(finding, "review:1", "reviewer-1", "freight_reviewer"),),
                challenges=(challenge(finding),),
                deadlines=(deadline(finding),),
                created_at=CREATED,
                created_by="case-freezer",
            )

    def test_seven_figure_bundle_requires_resolved_independent_challenge(self):
        finding = million_finding()
        with self.assertRaises(ValueError):
            freeze_case_proof(
                finding=finding,
                authority=authority(),
                source_attestations=(source_attestation(),),
                calculation=calculation(finding),
                reviews=(
                    review(finding, "review:1", "reviewer-1", "freight_reviewer"),
                    review(finding, "review:2", "reviewer-2", "independent_reviewer"),
                ),
                challenges=(challenge(finding, resolved=False),),
                deadlines=(deadline(finding),),
                created_at=CREATED,
                created_by="case-freezer",
            )
        with self.assertRaises(ValueError):
            freeze_case_proof(
                finding=finding,
                authority=authority(),
                source_attestations=(source_attestation(),),
                calculation=calculation(finding),
                reviews=(
                    review(finding, "review:1", "reviewer-1", "freight_reviewer"),
                    review(finding, "review:2", "reviewer-2", "independent_reviewer"),
                ),
                challenges=(challenge(finding, reviewer="reviewer-1"),),
                deadlines=(deadline(finding),),
                created_at=CREATED,
                created_by="case-freezer",
            )

    def test_case_bundle_binds_authority_source_and_calculation(self):
        finding = million_finding()
        bad_authority = AuthoritySnapshot(
            authority_id="bad",
            authority_kind="executed_contract",
            source_hash="wrong",
            source_locator="vault://authority/contract-v3#section=7.4",
            effective_from="2026-01-01",
            effective_to=None,
            acquired_at=CREATED,
            verified_by="reviewer",
            verification_note="bad source for test",
            jurisdiction="US",
        )
        with self.assertRaises(ValueError):
            freeze_case_proof(
                finding=finding,
                authority=bad_authority,
                source_attestations=(source_attestation(),),
                calculation=calculation(finding),
                reviews=(
                    review(finding, "review:1", "reviewer-1", "freight_reviewer"),
                    review(finding, "review:2", "reviewer-2", "independent_reviewer"),
                ),
                challenges=(challenge(finding),),
                deadlines=(deadline(finding),),
                created_at=CREATED,
                created_by="case-freezer",
            )

    def test_external_action_is_bound_to_exact_artifact(self):
        bundle = frozen_bundle()
        authorization = authorize_case_action(
            bundle,
            authorization_id="client-auth-1",
            client_actor_id="client-cfo-1",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:10:00Z",
            maximum_amount_cents=100_000_000,
            note="Approved to pursue the frozen validated amount.",
            expires_at="2026-12-01T00:00:00Z",
        )
        artifact = b"Demand amount: $1,000,000.00\nEvidence bundle: " + bundle.bundle_hash.encode()
        envelope = prepare_external_action(
            bundle,
            authorization,
            artifact_kind="demand_letter_pdf_bytes",
            artifact_bytes=artifact,
            artifact_locator="vault://outbound/demand-1.pdf",
            action_amount_cents=100_000_000,
            prepared_by="recovery-ops-1",
            prepared_at="2026-09-22T16:20:00Z",
        )
        verify_external_action(envelope, bundle, authorization, artifact_bytes=artifact)
        with self.assertRaises(ValueError):
            verify_external_action(
                envelope,
                bundle,
                authorization,
                artifact_bytes=artifact + b"tampered",
            )

    def test_high_value_ledger_cannot_use_legacy_authorization_path(self):
        finding = million_finding()
        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        ledger.approve(finding.finding_id, "reviewer-1", "primary review")
        with self.assertRaises(ValueError):
            ledger.authorize(finding.finding_id, "legacy-auth")

    def test_high_value_lifecycle_requires_dual_control_and_action_envelope(self):
        bundle = frozen_bundle()
        finding = bundle.finding
        authorization = authorize_case_action(
            bundle,
            authorization_id="client-auth-1",
            client_actor_id="client-cfo-1",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:10:00Z",
            maximum_amount_cents=100_000_000,
            note="Approved frozen finding.",
        )
        artifact = b"exact outbound demand"
        envelope = prepare_external_action(
            bundle,
            authorization,
            artifact_kind="demand_letter",
            artifact_bytes=artifact,
            artifact_locator="vault://outbound/exact-demand",
            action_amount_cents=100_000_000,
            prepared_by="recovery-ops-1",
            prepared_at="2026-09-22T16:20:00Z",
        )

        ledger = DurableRecoveryLedger()
        ledger.add(finding)
        ledger.approve(finding.finding_id, "reviewer-1", "primary review")
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(finding.finding_id, bundle, authorization)

        ledger.independent_approve(
            finding.finding_id,
            "reviewer-2",
            "independent reperformance",
        )
        ledger.authorize_with_case(finding.finding_id, bundle, authorization)
        with self.assertRaises(ValueError):
            ledger.mark_claimed(finding.finding_id)

        claimed = ledger.mark_claimed(finding.finding_id, envelope)
        self.assertEqual(
            claimed.external_action_envelope_hash,
            envelope.envelope_hash,
        )

        exported = ledger.export_bundle()
        restored = DurableRecoveryLedger.from_bundle(exported)
        restored_record = restored.get(finding.finding_id)
        self.assertEqual(restored.journal.head_hash, ledger.journal.head_hash)
        self.assertEqual(restored_record.case_bundle_hash, bundle.bundle_hash)
        self.assertEqual(
            restored_record.authorization_hash,
            authorization.proof_hash,
        )
        self.assertEqual(
            restored_record.external_action_envelope_hash,
            envelope.envelope_hash,
        )


if __name__ == "__main__":
    unittest.main()
