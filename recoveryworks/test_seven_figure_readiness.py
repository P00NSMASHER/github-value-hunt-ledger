from dataclasses import replace
import hashlib
import unittest

from recoveryworks import (
    DurableRecoveryLedger,
    RecoveryLedger,
    REQUIRED_READINESS_CHECKS,
    authorize_case_action,
    bind_seven_figure_dossier_consent,
    build_seven_figure_authorization_dossier,
    build_seven_figure_authorization_seal,
    build_seven_figure_readiness,
    prepare_external_action,
    readiness_from_payload,
    readiness_to_payload,
    record_build_provider_verification,
    record_external_signature_verification,
    record_external_timestamp_verification,
    record_object_lock_verification,
    seven_figure_consent_payload_hash,
    verify_seven_figure_authorization_seal,
    verify_seven_figure_readiness,
)
from recoveryworks.test_custody_provenance import build_custody_chain


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_lock_receipts(retention):
    result = []
    for index, item in enumerate(retention.entries, start=1):
        result.append(record_object_lock_verification(
            source_id=item.source_id,
            role=item.role,
            source_hash=item.source_hash,
            provider="SIM-OBJECT-STORE",
            object_version_id=f"SIM-VERSION-{index}",
            retention_control_id=item.retention_control_id,
            retention_mode=item.retention_mode,
            retain_until=item.retain_until,
            legal_hold_status="OFF",
            checked_at="2026-09-22T16:46:00Z",
            provider_request_id=f"SIM-LOCK-VERIFY-{index}",
            provider_response_hash=item.provider_attestation_hash,
            verified_by_adapter="sim-object-lock-adapter",
            provider_verified=True,
        ))
    return tuple(result)


def signature_for(public_record, *, provider_verified=True, algorithm="RSA_PSS_SHA256"):
    return record_external_signature_verification(
        signature_id="SIM-EXT-SIGNATURE-1",
        payload_kind="recoveryworks_public_verification_record_v1",
        payload_hash=public_record.record_hash,
        provider="SIM-KMS",
        key_id="sim-kms-asymmetric-key-1",
        algorithm=algorithm,
        public_key_fingerprint=sha(b"SIMULATED PUBLIC KEY"),
        signature_hash=sha(b"SIMULATED RSA-PSS SIGNATURE BYTES"),
        provider_request_id="SIM-KMS-VERIFY-REQUEST-1",
        verification_receipt_hash=sha(b"SIMULATED KMS VERIFY RESPONSE"),
        signed_at="2026-09-22T16:46:00Z",
        verified_at="2026-09-22T16:47:00Z",
        verified_by_adapter="sim-kms-verify-adapter",
        provider_verified=provider_verified,
    )


def timestamp_for(signature, *, provider_verified=True, subject_hash=None):
    return record_external_timestamp_verification(
        timestamp_id="SIM-RFC3161-1",
        subject_hash=subject_hash or signature.signature_hash,
        authority="SIM-TRUSTED-TIMESTAMP-AUTHORITY",
        standard="RFC3161",
        token_hash=sha(b"SIMULATED RFC3161 TOKEN"),
        serial_number="SIM-TSA-SERIAL-1",
        provider_request_id="SIM-TSA-VERIFY-REQUEST-1",
        verification_receipt_hash=sha(b"SIMULATED TSA VERIFY RESPONSE"),
        timestamped_at="2026-09-22T16:47:30Z",
        verified_at="2026-09-22T16:48:00Z",
        verified_by_adapter="sim-rfc3161-verify-adapter",
        provider_verified=provider_verified,
    )


def build_readiness_chain():
    bundle, ledger, packet, retention, completeness, build, public = (
        build_custody_chain()
    )
    signature = signature_for(public)
    timestamp = timestamp_for(signature)
    receipts = object_lock_receipts(retention)
    readiness = build_seven_figure_readiness(
        bundle,
        packet,
        retention,
        completeness,
        build,
        public,
        signature,
        timestamp,
        receipts,
        journal_head_hash=ledger.journal.head_hash,
        evaluated_at="2026-09-22T16:49:00Z",
        evaluated_by="sim-seven-figure-readiness-controller",
    )
    return (
        bundle,
        ledger,
        packet,
        retention,
        completeness,
        build,
        public,
        signature,
        timestamp,
        receipts,
        readiness,
    )



def build_final_authorization_chain():
    (
        bundle,
        ledger,
        packet,
        retention,
        completeness,
        build,
        public,
        _signature,
        _timestamp,
        _receipts,
        readiness,
    ) = build_readiness_chain()
    authorization = authorize_case_action(
        bundle,
        authorization_id="SIM-CLIENT-AUTH-FINAL-GATE-1",
        client_actor_id="sim-client-cfo",
        approved_action_type="carrier_overcharge_demand",
        authorized_at="2026-09-22T16:50:00Z",
        maximum_amount_cents=100_000_000,
        note="SIMULATION ONLY. Preliminary authorization before final dossier consent.",
    )
    dossier = build_seven_figure_authorization_dossier(
        readiness,
        packet,
        retention,
        completeness,
        build,
        public,
        bundle,
        journal_head_hash=ledger.journal.head_hash,
        assembled_at="2026-09-22T16:49:30Z",
        assembled_by="sim-seven-figure-dossier-controller",
    )
    build_receipt = record_build_provider_verification(
        build,
        provider="SIM-GITHUB-ACTIONS",
        workflow_run_id=build.workflow_run_id,
        code_commit_sha=build.code_commit_sha,
        source_tree_hash=build.source_tree_hash,
        build_artifact_hash=build.build_artifact_hash,
        tests_passed=True,
        checked_at="2026-09-22T16:50:15Z",
        provider_request_id="SIM-CI-VERIFY-REQ-1",
        provider_response_hash=sha(b"SIMULATED CI PROVIDER VERIFIED RESPONSE"),
        verified_by_adapter="sim-ci-provider-adapter",
        provider_verified=True,
    )
    consented_at = "2026-09-22T16:50:20Z"
    consent_note = "SIMULATION ONLY. Client approves the exact final readiness dossier."
    consent_payload_hash = seven_figure_consent_payload_hash(
        authorization,
        bundle,
        dossier,
        consented_at=consented_at,
        note=consent_note,
    )
    client_signature = record_external_signature_verification(
        signature_id="SIM-CLIENT-DOSSIER-SIGNATURE-1",
        payload_kind="recoveryworks_seven_figure_dossier_consent_v1",
        payload_hash=consent_payload_hash,
        provider="SIM-CLIENT-ESIGN",
        key_id="sim-client-cfo-signing-key",
        algorithm="ECDSA_SHA256",
        public_key_fingerprint=sha(b"SIMULATED CLIENT PUBLIC KEY"),
        signature_hash=sha(b"SIMULATED CLIENT DOSSIER SIGNATURE"),
        provider_request_id="SIM-CLIENT-SIGN-VERIFY-REQ-1",
        verification_receipt_hash=sha(b"SIMULATED CLIENT ESIGN VERIFY RESPONSE"),
        signed_at="2026-09-22T16:50:30Z",
        verified_at="2026-09-22T16:50:40Z",
        verified_by_adapter="sim-client-esign-adapter",
        provider_verified=True,
    )
    consent = bind_seven_figure_dossier_consent(
        authorization,
        bundle,
        dossier,
        client_signature,
        consented_at=consented_at,
        note=consent_note,
    )
    seal = build_seven_figure_authorization_seal(
        authorization,
        bundle,
        dossier,
        build_receipt,
        consent,
        journal_head_hash=ledger.journal.head_hash,
        sealed_at="2026-09-22T16:50:45Z",
        sealed_by="sim-final-authorization-controller",
    )
    return (
        bundle,
        ledger,
        authorization,
        packet,
        retention,
        completeness,
        build,
        public,
        readiness,
        dossier,
        build_receipt,
        consent,
        seal,
    )


class SevenFigureReadinessTests(unittest.TestCase):
    def test_full_readiness_package_verifies(self):
        (
            bundle,
            ledger,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            _signature,
            _timestamp,
            _receipts,
            readiness,
        ) = build_readiness_chain()
        verify_seven_figure_readiness(
            readiness,
            bundle,
            expected_journal_head_hash=ledger.journal.head_hash,
        )
        self.assertEqual(
            tuple(sorted(readiness.checks)),
            tuple(sorted(REQUIRED_READINESS_CHECKS)),
        )

    def test_hmac_is_rejected_as_external_signature(self):
        (
            _bundle,
            _ledger,
            _packet,
            _retention,
            _completeness,
            _build,
            public,
            *_rest,
        ) = build_readiness_chain()
        with self.assertRaises(ValueError):
            signature_for(public, algorithm="HMAC-SHA256")

    def test_unverified_external_signature_blocks_readiness(self):
        (
            bundle,
            ledger,
            packet,
            retention,
            completeness,
            build,
            public,
            _signature,
            _timestamp,
            receipts,
            _readiness,
        ) = build_readiness_chain()
        signature = signature_for(public, provider_verified=False)
        timestamp = timestamp_for(signature)
        with self.assertRaises(ValueError):
            build_seven_figure_readiness(
                bundle,
                packet,
                retention,
                completeness,
                build,
                public,
                signature,
                timestamp,
                receipts,
                journal_head_hash=ledger.journal.head_hash,
                evaluated_at="2026-09-22T16:49:00Z",
                evaluated_by="controller",
            )

    def test_timestamp_must_bind_external_signature(self):
        (
            bundle,
            ledger,
            packet,
            retention,
            completeness,
            build,
            public,
            signature,
            _timestamp,
            receipts,
            _readiness,
        ) = build_readiness_chain()
        timestamp = timestamp_for(signature, subject_hash=sha(b"wrong-signature-hash"))
        with self.assertRaises(ValueError):
            build_seven_figure_readiness(
                bundle,
                packet,
                retention,
                completeness,
                build,
                public,
                signature,
                timestamp,
                receipts,
                journal_head_hash=ledger.journal.head_hash,
                evaluated_at="2026-09-22T16:49:00Z",
                evaluated_by="controller",
            )

    def test_object_lock_provider_response_must_match_retention_attestation(self):
        (
            bundle,
            ledger,
            packet,
            retention,
            completeness,
            build,
            public,
            signature,
            timestamp,
            receipts,
            _readiness,
        ) = build_readiness_chain()
        bad = list(receipts)
        bad[0] = replace(
            bad[0],
            provider_response_hash=sha(b"wrong-provider-response-hash"),
        )
        with self.assertRaises(ValueError):
            build_seven_figure_readiness(
                bundle,
                packet,
                retention,
                completeness,
                build,
                public,
                signature,
                timestamp,
                bad,
                journal_head_hash=ledger.journal.head_hash,
                evaluated_at="2026-09-22T16:49:00Z",
                evaluated_by="controller",
            )

    def test_high_value_authorization_refuses_missing_readiness(self):
        bundle, ledger, *_rest = build_readiness_chain()
        authorization = authorize_case_action(
            bundle,
            authorization_id="SIM-CLIENT-AUTH-READINESS-1",
            client_actor_id="sim-client-cfo",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:50:00Z",
            maximum_amount_cents=100_000_000,
            note="SIMULATION ONLY. Approve frozen seven-figure claim.",
        )
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(
                bundle.finding.finding_id,
                bundle,
                authorization,
            )

    def test_stale_readiness_journal_head_blocks_authorization(self):
        bundle, ledger, *rest = build_readiness_chain()
        readiness = rest[-1]
        authorization = authorize_case_action(
            bundle,
            authorization_id="SIM-CLIENT-AUTH-READINESS-2",
            client_actor_id="sim-client-cfo",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:50:00Z",
            maximum_amount_cents=100_000_000,
            note="SIMULATION ONLY. Approve frozen seven-figure claim.",
        )
        ledger.add(
            replace(
                bundle.finding,
                finding_id=f"{bundle.finding.finding_id}:later-case",
                reference=f"{bundle.finding.reference}:later-case",
            )
        )
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(
                bundle.finding.finding_id,
                bundle,
                authorization,
                readiness,
            )

    def test_authorized_claim_persists_readiness_through_durable_replay(self):
        (
            bundle,
            ledger,
            authorization,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            readiness,
            dossier,
            _build_receipt,
            _consent,
            seal,
        ) = build_final_authorization_chain()
        authorized = ledger.authorize_with_case(
            bundle.finding.finding_id,
            bundle,
            authorization,
            readiness,
            dossier,
            seal,
        )
        self.assertEqual(authorized.readiness_hash, readiness.package_hash)
        self.assertEqual(authorized.readiness_dossier_hash, dossier.dossier_hash)
        self.assertEqual(authorized.authorization_seal_hash, seal.seal_hash)

        artifact = b"SIMULATION ONLY. Readiness-gated external demand."
        envelope = prepare_external_action(
            bundle,
            authorization,
            artifact_kind="synthetic_demand",
            artifact_bytes=artifact,
            artifact_locator="sim://outbound/readiness-demand",
            action_amount_cents=100_000_000,
            prepared_by="sim-recovery-ops",
            prepared_at="2026-09-22T16:51:00Z",
        )
        ledger.mark_claimed(bundle.finding.finding_id, envelope)

        exported = ledger.export_bundle()
        restored = DurableRecoveryLedger.from_bundle(exported)
        restored_record = restored.get(bundle.finding.finding_id)
        self.assertEqual(restored.journal.head_hash, ledger.journal.head_hash)
        self.assertEqual(restored_record.readiness_hash, readiness.package_hash)
        self.assertEqual(restored_record.readiness_dossier_hash, dossier.dossier_hash)
        self.assertEqual(restored_record.authorization_seal_hash, seal.seal_hash)


    def test_final_gate_refuses_missing_authorization_seal(self):
        (
            bundle,
            ledger,
            authorization,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            readiness,
            dossier,
            *_rest,
        ) = build_final_authorization_chain()
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(
                bundle.finding.finding_id,
                bundle,
                authorization,
                readiness,
                dossier,
            )

    def test_client_consent_cannot_predate_final_dossier(self):
        (
            bundle,
            _ledger,
            authorization,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            _readiness,
            dossier,
            *_rest,
        ) = build_final_authorization_chain()
        with self.assertRaises(ValueError):
            seven_figure_consent_payload_hash(
                authorization,
                bundle,
                dossier,
                consented_at="2026-09-22T16:49:00Z",
                note="too early",
            )

    def test_unverified_build_provider_blocks_final_seal(self):
        (
            bundle,
            ledger,
            authorization,
            _packet,
            _retention,
            _completeness,
            build,
            _public,
            _readiness,
            dossier,
            _build_receipt,
            consent,
            _seal,
        ) = build_final_authorization_chain()
        bad_receipt = record_build_provider_verification(
            build,
            provider="SIM-GITHUB-ACTIONS",
            workflow_run_id=build.workflow_run_id,
            code_commit_sha=build.code_commit_sha,
            source_tree_hash=build.source_tree_hash,
            build_artifact_hash=build.build_artifact_hash,
            tests_passed=True,
            checked_at="2026-09-22T16:50:15Z",
            provider_request_id="SIM-CI-BAD-REQ",
            provider_response_hash=sha(b"SIMULATED UNVERIFIED RESPONSE"),
            verified_by_adapter="sim-ci-provider-adapter",
            provider_verified=False,
        )
        with self.assertRaises(ValueError):
            build_seven_figure_authorization_seal(
                authorization,
                bundle,
                dossier,
                bad_receipt,
                consent,
                journal_head_hash=ledger.journal.head_hash,
                sealed_at="2026-09-22T16:50:45Z",
                sealed_by="controller",
            )

    def test_final_seal_is_invalid_after_journal_changes(self):
        (
            bundle,
            ledger,
            authorization,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            _readiness,
            dossier,
            _build_receipt,
            _consent,
            seal,
        ) = build_final_authorization_chain()
        ledger.add(
            replace(
                bundle.finding,
                finding_id=f"{bundle.finding.finding_id}:later-seal-case",
                reference=f"{bundle.finding.reference}:later-seal-case",
            )
        )
        with self.assertRaises(ValueError):
            verify_seven_figure_authorization_seal(
                seal,
                authorization,
                bundle,
                dossier,
                expected_journal_head_hash=ledger.journal.head_hash,
            )

    def test_high_value_authorization_requires_durable_ledger_even_with_readiness(self):
        (
            bundle,
            _durable_ledger,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            _signature,
            _timestamp,
            _receipts,
            readiness,
        ) = build_readiness_chain()
        ledger = RecoveryLedger()
        ledger.add(bundle.finding)
        ledger.approve(
            bundle.finding.finding_id,
            "sim-reviewer-1",
            "Synthetic primary review.",
        )
        ledger.independent_approve(
            bundle.finding.finding_id,
            "sim-reviewer-2",
            "Synthetic independent review.",
        )
        authorization = authorize_case_action(
            bundle,
            authorization_id="SIM-CLIENT-AUTH-NONDURABLE",
            client_actor_id="sim-client-cfo",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:50:00Z",
            maximum_amount_cents=100_000_000,
            note="SIMULATION ONLY. Must still require durable journal.",
        )
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(
                bundle.finding.finding_id,
                bundle,
                authorization,
                readiness,
            )

    def test_unapproved_timestamp_standard_is_rejected(self):
        (
            _bundle,
            _ledger,
            _packet,
            _retention,
            _completeness,
            _build,
            _public,
            signature,
            *_rest,
        ) = build_readiness_chain()
        with self.assertRaises(ValueError):
            record_external_timestamp_verification(
                timestamp_id="SIM-BAD-TIMESTAMP",
                subject_hash=signature.signature_hash,
                authority="SIM-TSA",
                standard="UNVERIFIED-CLOCK",
                token_hash=sha(b"bad token"),
                serial_number="BAD-1",
                provider_request_id="BAD-REQ",
                verification_receipt_hash=sha(b"bad receipt"),
                timestamped_at="2026-09-22T16:47:30Z",
                verified_at="2026-09-22T16:48:00Z",
                verified_by_adapter="sim-adapter",
                provider_verified=True,
            )

    def test_unapproved_object_lock_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            record_object_lock_verification(
                source_id="SIM-EV",
                role="evidence",
                source_hash="hash",
                provider="SIM-STORE",
                object_version_id="v1",
                retention_control_id="control",
                retention_mode="CONFIGURED_BUT_MUTABLE",
                retain_until="2033-09-22T00:00:00Z",
                legal_hold_status="OFF",
                checked_at="2026-09-22T16:46:00Z",
                provider_request_id="req",
                provider_response_hash="response",
                verified_by_adapter="adapter",
                provider_verified=True,
            )

    def test_expired_object_lock_horizon_is_rejected(self):
        with self.assertRaises(ValueError):
            record_object_lock_verification(
                source_id="SIM-EV",
                role="evidence",
                source_hash="hash",
                provider="SIM-STORE",
                object_version_id="v1",
                retention_control_id="control",
                retention_mode="OBJECT_LOCK_COMPLIANCE",
                retain_until="2026-09-22T16:45:00Z",
                legal_hold_status="OFF",
                checked_at="2026-09-22T16:46:00Z",
                provider_request_id="req",
                provider_response_hash="response",
                verified_by_adapter="adapter",
                provider_verified=True,
            )

    def test_readiness_payload_round_trip_is_tamper_evident(self):
        bundle, ledger, *rest = build_readiness_chain()
        readiness = rest[-1]
        payload = readiness_to_payload(readiness)
        restored = readiness_from_payload(payload)
        verify_seven_figure_readiness(
            restored,
            bundle,
            expected_journal_head_hash=ledger.journal.head_hash,
        )
        tampered = replace(restored, evaluated_by="different-controller")
        with self.assertRaises(ValueError):
            verify_seven_figure_readiness(
                tampered,
                bundle,
                expected_journal_head_hash=ledger.journal.head_hash,
            )


if __name__ == "__main__":
    unittest.main()
