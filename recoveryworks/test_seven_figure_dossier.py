from dataclasses import replace
import unittest

from recoveryworks import (
    DurableRecoveryLedger,
    authorize_case_action,
    authorization_dossier_from_payload,
    authorization_dossier_to_payload,
    build_seven_figure_authorization_dossier,
    verify_seven_figure_authorization_dossier,
)
from recoveryworks.test_seven_figure_readiness import (
    build_final_authorization_chain,
    build_readiness_chain,
)


def build_dossier_chain():
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
        readiness,
    ) = build_readiness_chain()
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
        dossier,
    )


class SevenFigureAuthorizationDossierTests(unittest.TestCase):
    def test_full_dossier_reverifies_all_underlying_components(self):
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
            _readiness,
            dossier,
        ) = build_dossier_chain()
        verify_seven_figure_authorization_dossier(
            dossier,
            bundle,
            expected_journal_head_hash=ledger.journal.head_hash,
        )

    def test_readiness_only_no_longer_authorizes_seven_figure_case(self):
        bundle, ledger, *_middle, readiness, _dossier = build_dossier_chain()
        authorization = authorize_case_action(
            bundle,
            authorization_id="SIM-CLIENT-AUTH-DOSSIER-1",
            client_actor_id="sim-client-cfo",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:50:00Z",
            maximum_amount_cents=100_000_000,
            note="SIMULATION ONLY. Dossier is mandatory.",
        )
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(
                bundle.finding.finding_id,
                bundle,
                authorization,
                readiness,
            )

    def test_full_dossier_authorizes_and_persists_both_hashes(self):
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
        record = ledger.authorize_with_case(
            bundle.finding.finding_id,
            bundle,
            authorization,
            readiness,
            dossier,
            seal,
        )
        self.assertEqual(record.readiness_hash, readiness.package_hash)
        self.assertEqual(record.readiness_dossier_hash, dossier.dossier_hash)
        self.assertEqual(record.authorization_seal_hash, seal.seal_hash)

        restored = DurableRecoveryLedger.from_bundle(ledger.export_bundle())
        restored_record = restored.get(bundle.finding.finding_id)
        self.assertEqual(
            restored_record.readiness_dossier_hash,
            dossier.dossier_hash,
        )
        self.assertEqual(restored_record.authorization_seal_hash, seal.seal_hash)

    def test_tampered_underlying_retention_fails_even_with_valid_readiness(self):
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
            _dossier,
        ) = build_dossier_chain()
        tampered_retention = replace(
            retention,
            created_by="different-custody-controller",
        )
        with self.assertRaises(ValueError):
            build_seven_figure_authorization_dossier(
                readiness,
                packet,
                tampered_retention,
                completeness,
                build,
                public,
                bundle,
                journal_head_hash=ledger.journal.head_hash,
                assembled_at="2026-09-22T16:49:30Z",
                assembled_by="sim-seven-figure-dossier-controller",
            )

    def test_compact_readiness_must_match_dossier_readiness(self):
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
            dossier,
        ) = build_dossier_chain()
        authorization = authorize_case_action(
            bundle,
            authorization_id="SIM-CLIENT-AUTH-DOSSIER-3",
            client_actor_id="sim-client-cfo",
            approved_action_type="carrier_overcharge_demand",
            authorized_at="2026-09-22T16:50:00Z",
            maximum_amount_cents=100_000_000,
            note="SIMULATION ONLY. Mismatched compact package must fail.",
        )
        mismatched = replace(
            readiness,
            package_hash="different-readiness-package-hash",
        )
        with self.assertRaises(ValueError):
            ledger.authorize_with_case(
                bundle.finding.finding_id,
                bundle,
                authorization,
                mismatched,
                dossier,
            )

    def test_dossier_payload_round_trip_is_tamper_evident(self):
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
            _readiness,
            dossier,
        ) = build_dossier_chain()
        payload = authorization_dossier_to_payload(dossier)
        restored = authorization_dossier_from_payload(payload)
        verify_seven_figure_authorization_dossier(
            restored,
            bundle,
            expected_journal_head_hash=ledger.journal.head_hash,
        )
        tampered = replace(restored, assembled_by="different-controller")
        with self.assertRaises(ValueError):
            verify_seven_figure_authorization_dossier(
                tampered,
                bundle,
                expected_journal_head_hash=ledger.journal.head_hash,
            )


if __name__ == "__main__":
    unittest.main()
