from dataclasses import asdict, replace
import hashlib
import unittest

from recoveryworks import (
    BuildProvenanceAttestation,
    NegativeEvidenceSearch,
    PopulationSegment,
    RetainedSourceObject,
    create_build_provenance_attestation,
    create_public_verification_record,
    freeze_case_completeness,
    freeze_source_retention,
    verify_build_provenance,
    verify_case_completeness,
    verify_public_verification_record,
    verify_source_retention,
)
from recoveryworks.test_case_artifact_replay import (
    AUTHORITY_BYTES,
    INVOICE_BYTES,
    TMS_BYTES,
)
from recoveryworks.test_hostile_examination_packet import build_exam
from recoveryworks.models import canonical_hash


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def retained_entries(bundle):
    return (
        RetainedSourceObject(
            source_id=bundle.authority.authority_id,
            role="authority",
            source_hash=sha(AUTHORITY_BYTES),
            size_bytes=len(AUTHORITY_BYTES),
            storage_uri="sim-private://object-lock/authority-contract-v3",
            retained_at="2026-09-22T16:01:00Z",
            retention_mode="OBJECT_LOCK_COMPLIANCE",
            retention_control_id="SIM-LOCK-AUTH-1",
            provider_attestation_hash=sha(b"sim-provider-attestation-authority"),
            immutable_storage_verified=True,
            retain_until="2033-09-22T00:00:00Z",
        ),
        RetainedSourceObject(
            source_id="SIM-EV-INVOICE",
            role="evidence",
            source_hash=sha(INVOICE_BYTES),
            size_bytes=len(INVOICE_BYTES),
            storage_uri="sim-private://object-lock/invoice-2026-08",
            retained_at="2026-09-22T16:02:00Z",
            retention_mode="OBJECT_LOCK_COMPLIANCE",
            retention_control_id="SIM-LOCK-INVOICE-1",
            provider_attestation_hash=sha(b"sim-provider-attestation-invoice"),
            immutable_storage_verified=True,
            retain_until="2033-09-22T00:00:00Z",
        ),
        RetainedSourceObject(
            source_id="SIM-EV-TMS",
            role="evidence",
            source_hash=sha(TMS_BYTES),
            size_bytes=len(TMS_BYTES),
            storage_uri="sim-private://object-lock/tms-2026-08",
            retained_at="2026-09-22T16:03:00Z",
            retention_mode="OBJECT_LOCK_COMPLIANCE",
            retention_control_id="SIM-LOCK-TMS-1",
            provider_attestation_hash=sha(b"sim-provider-attestation-tms"),
            immutable_storage_verified=True,
            retain_until="2033-09-22T00:00:00Z",
        ),
    )


def population_segment():
    return PopulationSegment(
        segment_id="SIM-AUG-2026-SHIPMENTS",
        source_export_hash=sha(TMS_BYTES),
        selection_rule="All invoiced August 2026 shipments for SIM-CARRIER-A",
        record_count=1842,
        included_record_count=1842,
        excluded_record_count=0,
        control_total_hash=sha(b"shipment_count=1842;contract_total=4250000.00"),
        included_ids_hash=sha(b"SIMULATED SORTED 1842 SHIPMENT IDS"),
        excluded_ids_hash=sha(b"EMPTY"),
    )


def negative_search(bundle, *, resolved=True):
    return NegativeEvidenceSearch(
        search_id="SIM-NEGATIVE-SEARCH-1",
        scope=(
            "Executed amendments, credit memos, rebills, ERP reversals, "
            "waivers, and excluded-shipment schedules"
        ),
        method="Full synthetic repository/export scan using frozen selection rules",
        searched_source_hashes=(
            bundle.authority.source_hash,
            sha(INVOICE_BYTES),
            sha(TMS_BYTES),
            sha(b"SIMULATED AMENDMENT/CREDIT/REVERSAL EXPORT"),
        ),
        contrary_evidence_hashes=(),
        searched_at="2026-09-22T16:35:00Z",
        searched_by="sim-independent-red-team",
        conclusion="No synthetic contrary evidence found.",
        resolved=resolved,
    )


def build_custody_chain():
    (
        bundle,
        _artifact_receipt,
        _calculation_receipt,
        ledger,
        _proof_seal,
        packet,
    ) = build_exam()

    retention = freeze_source_retention(
        bundle,
        entries=retained_entries(bundle),
        created_at="2026-09-22T16:40:00Z",
        created_by="sim-custody-controller",
    )
    completeness = freeze_case_completeness(
        bundle,
        populations=(population_segment(),),
        negative_searches=(negative_search(bundle),),
        created_at="2026-09-22T16:41:00Z",
        created_by="sim-completeness-reviewer",
    )
    build = create_build_provenance_attestation(
        bundle,
        repository="P00NSMASHER/github-value-hunt-ledger",
        build_system="github-actions",
        workflow_identity="RecoveryWorks/recoveryworks",
        workflow_run_id="SIM-RUN-654",
        dependency_lock_hash=sha(b"SIMULATED STDLIB-ONLY DEPENDENCY LOCK"),
        source_tree_hash=sha(b"SIMULATED SOURCE TREE AT COMMIT"),
        build_artifact_hash=sha(b"SIMULATED RECOVERYWORKS BUILD ARTIFACT"),
        tests_passed=True,
        built_at="2026-09-22T16:36:00Z",
        attested_at="2026-09-22T16:42:00Z",
        attested_by="sim-ci-attestor",
    )
    public = create_public_verification_record(
        bundle,
        packet,
        retention,
        completeness,
        build,
        journal_head_hash=ledger.journal.head_hash,
        record_id="SIM-PUBLIC-VERIFY-1",
        published_at="2026-09-22T16:45:00Z",
        publisher_id="sim-recoveryworks-transparency-log",
    )
    return bundle, ledger, packet, retention, completeness, build, public


class CustodyProvenanceTests(unittest.TestCase):
    def test_full_simulated_seven_figure_custody_chain_verifies(self):
        bundle, ledger, packet, retention, completeness, build, public = (
            build_custody_chain()
        )
        verify_source_retention(retention, bundle)
        verify_case_completeness(completeness, bundle)
        verify_build_provenance(build, bundle)
        verify_public_verification_record(
            public,
            bundle,
            packet,
            retention,
            completeness,
            build,
            journal_head_hash=ledger.journal.head_hash,
        )
        self.assertEqual(bundle.finding.potential_recovery_cents, 100_000_000)
        self.assertEqual(len(retention.entries), 3)
        self.assertEqual(completeness.populations[0].record_count, 1842)

    def test_immutable_claim_requires_provider_attestation(self):
        with self.assertRaises(ValueError):
            RetainedSourceObject(
                source_id="x",
                role="evidence",
                source_hash="hash",
                size_bytes=1,
                storage_uri="s3://bucket/key",
                retained_at="2026-09-22T16:00:00Z",
                retention_mode="OBJECT_LOCK_COMPLIANCE",
                retention_control_id=None,
                provider_attestation_hash=None,
                immutable_storage_verified=True,
            )

    def test_missing_retained_source_fails_closed(self):
        bundle, *_ = build_exam()
        with self.assertRaises(ValueError):
            freeze_source_retention(
                bundle,
                entries=retained_entries(bundle)[:-1],
                created_at="2026-09-22T16:40:00Z",
                created_by="sim-custody-controller",
            )

    def test_retention_cannot_predate_source_acquisition(self):
        bundle, *_ = build_exam()
        entries = list(retained_entries(bundle))
        entries[2] = replace(entries[2], retained_at="2026-09-22T16:01:59Z")
        with self.assertRaises(ValueError):
            freeze_source_retention(
                bundle,
                entries=entries,
                created_at="2026-09-22T16:40:00Z",
                created_by="sim-custody-controller",
            )

    def test_population_counts_must_reconcile(self):
        with self.assertRaises(ValueError):
            PopulationSegment(
                segment_id="bad",
                source_export_hash="hash",
                selection_rule="all",
                record_count=100,
                included_record_count=90,
                excluded_record_count=9,
                control_total_hash="total",
                included_ids_hash="included",
                excluded_ids_hash="excluded",
            )

    def test_unresolved_negative_evidence_search_blocks_completeness(self):
        bundle, *_ = build_exam()
        with self.assertRaises(ValueError):
            freeze_case_completeness(
                bundle,
                populations=(population_segment(),),
                negative_searches=(negative_search(bundle, resolved=False),),
                created_at="2026-09-22T16:41:00Z",
                created_by="sim-completeness-reviewer",
            )

    def test_build_provenance_requires_passing_tests(self):
        bundle, *_ = build_exam()
        with self.assertRaises(ValueError):
            create_build_provenance_attestation(
                bundle,
                repository="P00NSMASHER/github-value-hunt-ledger",
                build_system="github-actions",
                workflow_identity="RecoveryWorks/recoveryworks",
                workflow_run_id="SIM-RUN-FAILED",
                dependency_lock_hash="lock",
                source_tree_hash="tree",
                build_artifact_hash="artifact",
                tests_passed=False,
                built_at="2026-09-22T16:36:00Z",
                attested_at="2026-09-22T16:42:00Z",
                attested_by="sim-ci-attestor",
            )

    def test_public_record_is_hash_only_and_contains_no_private_locators(self):
        _bundle, _ledger, _packet, _retention, _completeness, _build, public = (
            build_custody_chain()
        )
        rendered = repr(asdict(public))
        self.assertNotIn("sim://", rendered)
        self.assertNotIn("sim-private://", rendered)
        self.assertIn("merkle_root_hash", rendered)

    def test_public_record_cannot_predate_committed_components(self):
        bundle, ledger, packet, retention, completeness, build, public = (
            build_custody_chain()
        )

        with self.assertRaises(ValueError):
            create_public_verification_record(
                bundle,
                packet,
                retention,
                completeness,
                build,
                journal_head_hash=ledger.journal.head_hash,
                record_id="SIM-PUBLIC-VERIFY-EARLY",
                published_at="2026-09-22T16:41:30Z",
                publisher_id="sim-recoveryworks-transparency-log",
            )

        internally_consistent_but_early = replace(
            public,
            published_at="2026-09-22T16:41:30Z",
            record_hash="placeholder",
        )
        internally_consistent_but_early = replace(
            internally_consistent_but_early,
            record_hash=canonical_hash(
                internally_consistent_but_early.integrity_body()
            ),
        )
        with self.assertRaises(ValueError):
            verify_public_verification_record(
                internally_consistent_but_early,
                bundle,
                packet,
                retention,
                completeness,
                build,
                journal_head_hash=ledger.journal.head_hash,
            )

    def test_public_record_tampering_is_detected(self):
        bundle, ledger, packet, retention, completeness, build, public = (
            build_custody_chain()
        )
        tampered = replace(public, journal_head_hash="tampered-head")
        with self.assertRaises(ValueError):
            verify_public_verification_record(
                tampered,
                bundle,
                packet,
                retention,
                completeness,
                build,
                journal_head_hash=ledger.journal.head_hash,
            )

    def test_build_attestation_tampering_is_detected(self):
        bundle, _ledger, _packet, _retention, _completeness, build, _public = (
            build_custody_chain()
        )
        tampered = replace(build, code_commit_sha="f" * 40)
        with self.assertRaises(ValueError):
            verify_build_provenance(tampered, bundle)

    def test_build_attestation_rejects_non_digest_build_hash(self):
        _bundle, _ledger, _packet, _retention, _completeness, build, _public = (
            build_custody_chain()
        )
        with self.assertRaisesRegex(ValueError, "source_tree_hash must be a 64-character"):
            replace(build, source_tree_hash="tree")


if __name__ == "__main__":
    unittest.main()
