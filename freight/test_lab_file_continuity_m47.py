"""M47: test actual replacement/deletion path protections on persistent SQLite.

All money, database files, alternate scopes and signers are synthetic.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight.lab_assurance import digest
from freight import lab_file_continuity_m47 as m47
from freight import settlement_file_identity_m47 as identity
from freight.settlement_store import SettlementStore, SettlementEventRecord
from freight.test_lab_phase3_real_chain import funded_store


class M47SQLiteFileContinuityTests(unittest.TestCase):
    def test_eight_replacements_fail_original_sessions_on_every_financial_operation(self):
        self.assertEqual(len(m47.ATTACKS),8)
        self.assertEqual(len(m47.READ_SURFACES),7)
        for name,reason in m47.ATTACKS.items():
            with self.subTest(case=name):
                result=m47.replay_one(name)
                self.assertEqual(result["source_path_attack"],name)
                self.assertEqual(result["exact_expected_denial"],reason)
                self.assertEqual(result["original_synthetic_money_controls_passed"],5)
                self.assertEqual(result["existing_session_read_denials"],7)
                self.assertEqual(result["existing_session_write_denials"],1)
                self.assertEqual(result["all_synthetic_operation_ids_denied"],
                                 [*m47.READ_SURFACES,"attempt_new_credit"])
                self.assertTrue(result["database_file_identity_changed"])
                self.assertTrue(result["rejected_actions_did_not_create_or_replace_file"])
                self.assertFalse(result["original_historical_finding_closed"])
                self.assertFalse(result["external_customer_bank_carrier_source_verified"])

    def test_end_to_end_report_rejects_every_fake_original_customer_or_cash_claim(self):
        out=m47.run_campaign(as_of=date(2026,10,13))
        self.assertEqual(out["scope"],m47.SCOPE)
        self.assertEqual(out["existing_research_lab"],14)
        self.assertFalse(out["new_lab_created"])
        self.assertEqual(out["disposed_current_sqlite_path_attack_cases"],8)
        self.assertEqual(out["positive_fictional_money_baseline_checks"],40)
        self.assertEqual(out["existing_session_money_and_report_read_denials"],56)
        self.assertEqual(out["existing_session_write_denials"],8)
        self.assertEqual(out["total_file_path_attacks_blocked_on_current_operations"],64)
        self.assertEqual(out["all_26_original_findings_still_open"],26)
        self.assertEqual(out["original_historical_findings_closed"],0)
        self.assertEqual(out["independent_first_customer_human_approval_gates_unmet"],18)
        self.assertEqual(out["real_customers_or_payment_accounts_contacted"],0)
        self.assertIsNone(out["real_recovered_company_cash_cents"])
        self.assertEqual(out["external_empirical_freight_recovery_claims_allowed"],0)
        self.assertTrue(out["no_registration_hosted_deployment_or_schedule_changes"])
        self.assertEqual(out["receipt_sha256"],digest({
            k:v for k,v in out.items() if k!="receipt_sha256"
        }))

    def test_main_file_removed_after_init_is_not_recreated_by_any_read_write(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            db=Path(store.path)
            db.unlink()
            self.assertFalse(db.exists())
            for operation in (
                store.realized_cents, store.fee_eligible_cents,
                lambda:store.count("allocations"),store.report_snapshot_json,
                store.assert_semantic_integrity,
            ):
                with self.assertRaisesRegex(RuntimeError,
                                             "M47_SQLITE_SOURCE_FILE_MISSING"):
                    operation()
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_FILE_MISSING"):
                store.ingest_event(SettlementEventRecord(
                    "m47-missing-credit","INV-100","SIM-CARRIER","SIM-BUYER",
                    "USD",1,"2026-12-20T12:00:00Z",
                    sha256(b"m47-missing-credit").hexdigest(),"EXTERNAL"
                ))
            self.assertFalse(db.exists(),
                             "no implicit sqlite3.connect CREATE is allowed")

    def test_atomic_valid_same_tenant_replacement_is_rejected_by_old_instance(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            path=Path(store.path)
            replacement=Path(td)/"reviewed-replacement.sqlite3"
            m47._copy_valid(path,replacement)
            os.replace(replacement,path)
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_FILE_REPLACED"):
                store.realized_cents()
            # Explicit new instance can adopt a *valid* reviewed restore.
            fresh=SettlementStore(path,buyer_id=store.buyer_id,
                                  business_unit=store.business_unit)
            self.assertEqual(fresh.realized_cents(),500)
            self.assertEqual(fresh.fee_eligible_cents(),500)
            self.assertEqual(fresh.count("allocations"),2)

    def test_new_valid_empty_database_at_old_path_cannot_silently_reset_balance(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            original=Path(store.path)
            replacement=Path(td)/"empty-valid.sqlite3"
            clean=SettlementStore(
                replacement,buyer_id=store.buyer_id,
                business_unit=store.business_unit
            )
            self.assertEqual(clean.realized_cents(),0)
            os.replace(replacement,original)
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_FILE_REPLACED"):
                store.realized_cents()
            # New instance deliberately opening a reviewed separate file is
            # permitted, but the original session cannot pretend it is the
            # previously audited $5 balance.
            reop=SettlementStore(original,buyer_id=store.buyer_id,
                                 business_unit=store.business_unit)
            self.assertEqual(reop.realized_cents(),0)

    def test_dangling_or_valid_symlink_initialization_does_not_follow_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            linked=root/"linked.sqlite3"
            good=SettlementStore(root/"actual.sqlite3",
                                 buyer_id="A",business_unit="B")
            self.assertEqual(good.count("allocations"),0)
            linked.symlink_to(good.path)
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_SYMLINK_REJECTED"):
                SettlementStore(linked,buyer_id="A",business_unit="B")
            linked.unlink()
            linked.symlink_to(root/"nonexistent.sqlite3")
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_SYMLINK_REJECTED"):
                SettlementStore(linked,buyer_id="A",business_unit="B")
            self.assertFalse((root/"nonexistent.sqlite3").exists())

    def test_exclusive_creation_rejects_race_without_truncating_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"attempt.sqlite3"
            original=identity.create_exclusive_empty
            def overlapping_new_writer(filepath):
                Path(filepath).write_bytes(b"OTHER_WRITER_SENTINEL")
                return original(filepath)
            with patch.object(identity,"create_exclusive_empty",
                              side_effect=overlapping_new_writer):
                with self.assertRaisesRegex(RuntimeError,
                                             "M47_SQLITE_CREATE_PATH_ALREADY_PRESENT"):
                    SettlementStore(path,buyer_id="A",business_unit="B")
            self.assertEqual(path.read_bytes(),b"OTHER_WRITER_SENTINEL")

    def test_orphaned_wal_file_is_not_treated_as_fresh_empty_database(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"settlements.sqlite3"
            Path(str(path)+"-wal").write_bytes(b"UNTRUSTED_PENDING_WAL")
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_ORPHANED_SQLITE_SIDECAR"):
                SettlementStore(path,buyer_id="A",business_unit="B")
            self.assertFalse(path.exists())
            self.assertEqual(Path(str(path)+"-wal").read_bytes(),
                             b"UNTRUSTED_PENDING_WAL")

    def test_initial_absolute_location_is_not_retargeted_by_working_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            first=root/"first";second=root/"second"
            first.mkdir();second.mkdir()
            cwd=os.getcwd()
            try:
                os.chdir(first)
                s=SettlementStore("relative.sqlite3",
                                  buyer_id="A",business_unit="B")
                self.assertTrue(Path(s.path).is_absolute())
                os.chdir(second)
                self.assertEqual(s.realized_cents(),0)
                self.assertFalse((second/"relative.sqlite3").exists())
            finally:
                os.chdir(cwd)

    def test_copy_valid_database_mid_read_must_abort_even_if_rows_are_consistent(self):
        with tempfile.TemporaryDirectory() as td:
            s=funded_store(td)
            original=Path(s.path)
            another=Path(td)/"replacement.sqlite3"
            m47._copy_valid(original,another)
            def swapped(conn):
                os.replace(another,original)
                return conn.execute(
                    "SELECT COUNT(*) FROM settlement_events"
                ).fetchone()[0]
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_FILE_REPLACED"):
                s._read(swapped)

    def test_copy_valid_database_mid_write_fails_before_commit(self):
        with tempfile.TemporaryDirectory() as td:
            s=funded_store(td)
            original=Path(s.path)
            other=Path(td)/"new-valid.sqlite3"
            m47._copy_valid(original,other)
            def swapped_during_tx(conn):
                os.replace(other,original)
                return "MUST_NOT_SUCCEED"
            with self.assertRaisesRegex(RuntimeError,
                                         "M47_SQLITE_SOURCE_FILE_REPLACED"):
                s._write(swapped_during_tx)
            # The replacement path has a valid database but is NOT the
            # original source identity; explicit fresh store can reopen it.
            r=SettlementStore(original,buyer_id=s.buyer_id,
                              business_unit=s.business_unit)
            self.assertEqual(r.realized_cents(),500)

    def test_new_file_permissions_are_private_on_posix(self):
        if os.name!="posix":
            self.skipTest("POSIX permission check")
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"new.sqlite3"
            s=SettlementStore(path,buyer_id="A",business_unit="B")
            self.assertEqual((path.stat().st_mode & 0o777),0o600)
            self.assertEqual(s.count("allocations"),0)

    def test_legitimate_same_file_concurrent_source_addition_is_still_visible(self):
        with tempfile.TemporaryDirectory() as td:
            first=funded_store(td)
            second=SettlementStore(first.path,
                                   buyer_id=first.buyer_id,
                                   business_unit=first.business_unit)
            new=SettlementEventRecord(
                "m47-legit-concurrent","INV-100","SIM-CARRIER","SIM-BUYER",
                "USD",1,"2026-12-20T12:00:00Z",
                sha256(b"m47-legit-concurrent").hexdigest(),"EXTERNAL",
            )
            self.assertTrue(second.ingest_event(new))
            self.assertEqual(first.count("settlement_events"),3)
            self.assertEqual(second.count("settlement_events"),3)
            self.assertEqual(first.realized_cents(),500)

    def test_unregistered_mutations_never_touch_user_supplied_database_paths(self):
        for bad in ("",None,True,"CREATE TABLE","../../another.db",42):
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as td:
                s=funded_store(td)
                existing=m47._state(Path(s.path))
                with self.assertRaisesRegex(ValueError,
                                             "M47_UNKNOWN_DISPOSABLE_SOURCE_REPLACEMENT"):
                    m47._mutate(Path(s.path),bad,(s.buyer_id,s.business_unit))
                with self.assertRaisesRegex(ValueError,
                                             "M47_UNKNOWN_PERSISTENT_FILE_CONTINUITY_CASE"):
                    m47.replay_one(bad)
                self.assertEqual(m47._state(Path(s.path)),existing)

    def test_invalid_date_blocks_before_creating_report_files(self):
        for bad in (date(2026,10,12),"2026-10-13",None,True):
            with self.subTest(bad=bad),self.assertRaisesRegex(
                ValueError,"M47_INVALID_RESEARCH_AS_OF"
            ):
                m47.run_campaign(as_of=bad)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"no-output"
            with patch("sys.argv",[
                "m47","--as-of-date","2026-10-12","--out",str(out)
            ]):
                with self.assertRaises(ValueError):
                    m47.main()
            self.assertFalse(out.exists())

    def test_html_escapes_malicious_display_and_discloses_no_real_authority(self):
        report=m47.run_campaign(as_of=date(2026,10,13))
        other=deepcopy(report)
        other["cases"][0]["source_path_attack"]="<script>alert(1)</script>"
        html=m47.render_html(other)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("26 historical defects still open",html)
        self.assertTrue(report["file_identity_is_local_device_inode_not_bank_proof"])

    def test_cli_outputs_only_bounded_derived_internal_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"receipt"
            with patch("sys.argv",[
                "m47","--as-of-date","2026-10-13","--out",str(out)
            ]):
                m47.main()
            r=json.loads((out/"sqlite_file_continuity_m47.json").read_text())
            self.assertEqual(r["existing_session_money_and_report_read_denials"],56)
            self.assertEqual(r["existing_session_write_denials"],8)
            self.assertEqual(r["original_historical_findings_closed"],0)
            self.assertTrue((out/"sqlite_file_continuity_m47.html").is_file())
            self.assertNotIn("external_customer_account_id",r)


if __name__ == "__main__":
    unittest.main()
