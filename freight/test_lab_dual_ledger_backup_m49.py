"""M49: two-file backup source stability, independent byte receipt and rollback.

These tests use fictional AuditStore and SettlementStore objects only. They
do NOT establish synchronized cross-file SQLite transactions, external bank
credentials, real invoices, or first-customer authorization.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
from pathlib import Path
from hashlib import sha256
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight import backup_restore as backup
from freight import lab_dual_ledger_backup_m49 as m49
from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight.lab_assurance import digest
from freight.settlement_store import SettlementEventRecord, SettlementStore
from freight.test_backup_restore import populated


DAY=date(2026,10,13)


class DualLedgerBackupM49Tests(unittest.TestCase):
    def test_every_failed_copy_or_concurrent_append_refuses_partial_success(self):
        self.assertEqual(len(m49.SCENARIOS),9)
        for case,expected in m49.SCENARIOS.items():
            with self.subTest(case=case):
                r=m49.replay_one(case)
                self.assertEqual(r["scenario"],case)
                self.assertEqual(r["expected_failure"],expected)
                self.assertTrue(r["one_known_good_synthetic_backup_and_restore_verified"])
                self.assertTrue(r["negative_current_code_fails_closed"])
                self.assertTrue(r["no_partial_new_sqlite_bundle_published"])
                self.assertTrue(r["no_false_completion_marker_published"])
                self.assertTrue(r["preexisting_user_artifacts_remain_untouched"])
                self.assertFalse(r["original_historical_finding_closed"])
                self.assertFalse(r["actual_customer_bank_carrier_authority_attested"])

    def test_positive_bundle_has_four_real_sqlite_files_and_final_commit_marker(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            audit,settlement=populated(base)
            target=base/"approved"
            result=backup.run_backup_restore_drill(
                audit,settlement,work_dir=target
            )
            backup.verify_backup_restore_result(result)
            manifest=backup.verify_backup_bundle(target,result)
            self.assertTrue((target/"capture.complete.json").is_file())
            self.assertEqual(manifest["scope"],
                             "M49_SCOPED_TWO_SQLITE_STABLE_WINDOW_NOT_ATOMIC_CROSS_FILE")
            self.assertFalse(manifest["separate_two_file_atomic_database_commit_established"])
            self.assertEqual(manifest["original_26_historical_findings_closed"],0)
            self.assertFalse(manifest["real_customer_bank_or_carrier_source_verified"])
            self.assertEqual(set(manifest["full_file_logical_source_hashes"]),
                             {"audit","settlement"})
            for file in backup._capture_files():
                self.assertTrue((target/file).is_file())
                self.assertTrue((target/file).read_bytes().startswith(b"SQLite format 3"))

    def test_manifest_file_corruption_fails_file_level_verification(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            audit,settlement=populated(base)
            path=base/"run"
            result=backup.run_backup_restore_drill(audit,settlement,work_dir=path)
            self.assertEqual(
                backup.verify_backup_bundle(path,result)["proof_hash"],
                result.proof_hash,
            )
            file=path/"settlement.backup.sqlite3"
            with file.open("ab") as handle:
                handle.write(b"M49_TEST_ONLY_POST_PUBLISH_TAMPERING")
            with self.assertRaisesRegex(ValueError,
                                         "M49_BUNDLE_SQLITE_FILE_MISSING_OR_CHANGED"):
                backup.verify_backup_bundle(path,result)

    def test_rehashed_or_forged_local_receipt_is_not_merely_length_checked(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            audit,settlement=populated(base)
            result=backup.run_backup_restore_drill(
                audit,settlement,work_dir=base/"approved"
            )
            fake=replace(result,audit_backup_sha256="e"*64)
            with self.assertRaisesRegex(ValueError,
                                         "M49_REHASHED_OR_MISMATCHED_LOCAL_BACKUP_RESULT"):
                backup.verify_backup_restore_result(fake)

    def test_corrupted_or_absent_completion_marker_does_not_approve_partial_files(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            audit,settlement=populated(base)
            location=base/"committed"
            result=backup.run_backup_restore_drill(
                audit,settlement,work_dir=location
            )
            marker=location/"capture.complete.json"
            valid=marker.read_bytes()
            marker.unlink()
            with self.assertRaisesRegex(ValueError,
                                         "M49_MISSING_OR_INVALID_CAPTURE_COMPLETION_MARKER"):
                backup.verify_backup_bundle(location,result)
            marker.write_bytes(valid)
            document=json.loads(marker.read_text())
            document["original_26_historical_findings_closed"]=26
            marker.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError,
                                         "M49_BUNDLE_COMPLETION_MANIFEST_NOT_TRUSTWORTHY"):
                backup.verify_backup_bundle(location,result)

    def test_other_tenant_audit_append_during_capture_is_not_ignored(self):
        result=m49.replay_one("OTHER_TENANT_AUDIT_APPEND")
        self.assertTrue(result["no_false_completion_marker_published"])
        self.assertEqual(result["expected_failure"],
                         "M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE")

    def test_other_tenant_settlement_source_append_during_capture_is_not_ignored(self):
        result=m49.replay_one("OTHER_TENANT_SETTLEMENT_APPEND")
        self.assertTrue(result["no_partial_new_sqlite_bundle_published"])
        self.assertEqual(result["expected_failure"],
                         "M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE")

    def test_any_preexisting_customer_backup_filename_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            output=root/"existing"
            output.mkdir()
            preserved=output/"settlement.restored.sqlite3"
            preserved.write_bytes(b"KEEP_PREVIOUS_CUSTOMER_RECOVERY")
            with self.assertRaisesRegex(RuntimeError,
                                         "M49_EXISTING_BACKUP_ARTIFACT_MUST_NOT_BE_OVERWRITTEN"):
                backup.run_backup_restore_drill(audit,settlement,work_dir=output)
            self.assertEqual(preserved.read_bytes(),
                             b"KEEP_PREVIOUS_CUSTOMER_RECOVERY")
            self.assertEqual(list(output.iterdir()),[preserved])

    def test_output_symlink_directory_is_rejected_even_if_valid(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            normal=root/"real"
            normal.mkdir()
            evil=root/"link"
            evil.symlink_to(normal,target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError,
                                         "M49_BACKUP_OUTPUT_DIRECTORY_NOT_TRUSTWORTHY"):
                backup.run_backup_restore_drill(audit,settlement,work_dir=evil)
            self.assertEqual(list(normal.iterdir()),[])

    def test_third_hardlink_publication_failure_cleans_up_all_our_files(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            audit,settlement=populated(base)
            target=base/"failed"
            link=backup.os.link
            counter=[0]
            def fail_third(src,dst,*args,**kwargs):
                counter[0]+=1
                if counter[0]==3:
                    raise OSError("M49_TEST_ONLY_EXCLUSIVE_PUBLICATION_ERROR")
                return link(src,dst,*args,**kwargs)
            with patch.object(backup.os,"link",side_effect=fail_third):
                with self.assertRaisesRegex(OSError,
                                             "M49_TEST_ONLY_EXCLUSIVE_PUBLICATION_ERROR"):
                    backup.run_backup_restore_drill(
                        audit,settlement,work_dir=target
                    )
            self.assertEqual(counter[0],3)
            self.assertFalse(target.exists(),
                             "No partial final directory should survive failure")

    def test_midway_restore_fault_leaves_no_final_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            original=backup._restore_copy
            def bad_restore(src,dst):
                if dst.name=="settlement.restored.sqlite3":
                    raise RuntimeError("M49_TEST_ONLY_RESTORE_ABORT")
                return original(src,dst)
            target=root/"should-not-exist"
            with patch.object(backup,"_restore_copy",side_effect=bad_restore):
                with self.assertRaisesRegex(RuntimeError,
                                             "M49_TEST_ONLY_RESTORE_ABORT"):
                    backup.run_backup_restore_drill(
                        audit,settlement,work_dir=target
                    )
            self.assertFalse(target.exists())

    def test_audit_summary_one_snapshot_not_three_avoidable_separate_reads(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            with patch.object(audit,"verify",side_effect=AssertionError(
                "M49 must not use separate audit verify"
            )),patch.object(audit,"count",side_effect=AssertionError(
                "M49 must not separately count audit events"
            )),patch.object(audit,"head",side_effect=AssertionError(
                "M49 must not separately fetch chain head"
            )):
                result=backup.workspace_summary(audit,settlement)
            self.assertEqual(result.audit_record_count,2)
            self.assertEqual(result.audit_chain_head,
                             audit.records()[-1].event_hash)

    def test_logical_hash_check_covers_complete_tenant_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            secondary=AuditStore(
                audit.path,buyer_id="OTHER-SIMULATED-TENANT",business_unit="OPS"
            )
            a=backup._logical_sqlite_hash(Path(audit.path),"audit")
            baseline=backup.workspace_summary(audit,settlement)
            secondary.append(
                event_type=AuditEventType.SOURCE_PRESENT,
                object_id="other-tenant-source",
                occurred_at="2026-09-26T11:00:00Z",
                evidence_hash=sha256(b"other-tenant").hexdigest(),
            )
            b=backup._logical_sqlite_hash(Path(audit.path),"audit")
            after=backup.workspace_summary(audit,settlement)
            self.assertNotEqual(a,b)
            self.assertEqual(baseline.semantic_hash,after.semantic_hash,
                             "Scope-A summary deliberately unchanged")

    def test_capture_refuses_new_original_source_deletion_without_recreating_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            actual=backup._sqlite_backup
            def delete_first(src,dst):
                if dst.name=="audit.backup.sqlite3":
                    Path(audit.path).unlink()
                return actual(src,dst)
            out=root/"should-not-exist"
            with patch.object(backup,"_sqlite_backup",side_effect=delete_first):
                with self.assertRaisesRegex(RuntimeError,
                                             "M47_SQLITE_SOURCE_FILE_MISSING"):
                    backup.run_backup_restore_drill(audit,settlement,work_dir=out)
            self.assertFalse(out.exists())
            self.assertFalse(Path(audit.path).exists())

    def test_invalid_source_scope_and_kind_do_not_create_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            other=SettlementStore(root/"different.sqlite3",
                                  buyer_id="OTHER",business_unit="OPS")
            with self.assertRaisesRegex(ValueError,"workspace scope mismatch"):
                backup.run_backup_restore_drill(
                    audit,other,work_dir=root/"bad"
                )
            self.assertFalse((root/"bad").exists())
            with self.assertRaisesRegex(ValueError,
                                         "M49_UNSUPPORTED_SQLITE_CAPTURE_FAMILY"):
                backup._logical_sqlite_hash(Path(audit.path),"personal_customer")

    def test_local_receipt_does_not_upgrade_into_verified_external_cash(self):
        report=m49.run_campaign(as_of=DAY)
        self.assertEqual(report["scope"],m49.SCOPE)
        self.assertFalse(report["two_sqlite_files_atomically_committed_together"])
        self.assertTrue(report["completed_bundles_use_commit_marker_last"])
        self.assertEqual(report["disposable_dual_source_attack_scenarios"],9)
        self.assertEqual(report["matching_positive_fictional_bundles"],9)
        self.assertEqual(report["current_code_exact_negative_denials"],9)
        self.assertEqual(report["original_historical_findings_open"],26)
        self.assertEqual(report["original_historical_findings_closed"],0)
        self.assertEqual(report["first_customer_independent_human_controls_unmet"],18)
        self.assertIsNone(report["reproducible_real_customer_cash_recovery"])
        self.assertFalse(report["externally_authenticated_invoice_or_bank_data"])
        self.assertEqual(report["externally_publishable_empirical_claims_approved"],0)
        self.assertTrue(report["no_live_deployments_customer_messages_or_schedules"])
        self.assertEqual(report["receipt_sha256"],digest({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_html_escapes_and_bad_date_fails_before_writing_files(self):
        report=m49.run_campaign(as_of=DAY)
        modified=deepcopy(report)
        modified["cases"][0]["scenario"]="<img src=x onerror=alert(1)>"
        html=m49.render_html(modified)
        self.assertIn("&lt;img",html)
        self.assertNotIn("<img",html)
        self.assertIn("NOT an atomic distributed snapshot",html)
        for date_candidate in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(date=date_candidate):
                with self.assertRaisesRegex(ValueError,"M49_INVALID_RESEARCH_AS_OF"):
                    m49.run_campaign(as_of=date_candidate)

    def test_cli_writes_metadata_only_reports_without_customer_sqlite_data(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=root/"derived"
            with patch("sys.argv",["m49","--as-of-date","2026-10-13","--out",str(out)]):
                m49.main()
            body=json.loads((out/"dual_ledger_backup_m49.json").read_text())
            self.assertEqual(body["current_code_exact_negative_denials"],9)
            self.assertEqual(body["original_historical_findings_closed"],0)
            self.assertTrue((out/"dual_ledger_backup_m49.html").exists())
            self.assertFalse(any(p.suffix in (".sqlite3",".db") for p in out.iterdir()))


if __name__=="__main__":
    unittest.main()
