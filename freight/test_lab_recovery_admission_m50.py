"""M50: adversarial published-backup restore admission and unkeyed SHA repair.

No actual customer, provider, bank, original invoice or real payment.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace,asdict
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight import backup_restore as backup
from freight import lab_recovery_admission_m50 as lab
from freight import restore_admission_m50 as guard
from freight.audit_store import AuditStore
from freight.audit_ledger import AuditEventType
from freight.test_backup_restore import populated
from freight.lab_assurance import digest
from freight.contracts import canonical_hash


DAY=date(2026,10,13)


class M50PublishedRecoveryAdmissionTests(unittest.TestCase):
    def test_thirteen_local_sha_repaired_invalid_bundles_all_fail_exactly(self):
        self.assertEqual(len(lab.CASES),13)
        self.assertEqual(set(lab.FILES),set(backup._capture_files()))
        for case,code in lab.CASES.items():
            with self.subTest(case=case):
                result=lab.replay_one(case)
                self.assertEqual(result["case"],case)
                self.assertEqual(result["expected_current_exact_denial"],code)
                self.assertTrue(result["original_good_bundle_accepted"])
                self.assertTrue(result["mutated_local_receipts_rehashed_to_look_complete"])
                self.assertTrue(result["predecessor_length_and_sha_only_gate_would_accept"])
                self.assertTrue(result["current_read_only_restoration_admission_denied"])
                self.assertTrue(result["all_four_sqlite_file_bytes_preserved_during_rejection"])
                self.assertFalse(result["original_historical_defect_closed"])
                self.assertFalse(result["real_customer_or_bank_signature_reproduced"])

    def test_campaign_never_promotes_synthetic_to_real_banking_or_historical_closure(self):
        result=lab.run_campaign(as_of=DAY)
        self.assertEqual(result["scope"],lab.SCOPE)
        self.assertEqual(result["existing_original_labs"],14)
        self.assertFalse(result["new_lab_created"])
        self.assertEqual(result["valid_original_fictional_recovery_bundles"],13)
        self.assertEqual(result["rehash_repaired_negative_bundle_attacks"],13)
        self.assertEqual(result["current_exact_fail_closed_recovery_denials"],13)
        self.assertTrue(result["full_tenant_audit_and_settlement_semantics_checked"])
        self.assertTrue(result["published_backup_and_restore_generations_reconciled"])
        self.assertTrue(result["hash_and_schema_checks_executed_read_only"])
        self.assertFalse(result["original_two_file_shared_atomic_commit_proven"])
        self.assertFalse(result["external_immutable_or_crypto_signed_backup_proven"])
        self.assertEqual(result["historical_original_recoveryos_findings_open"],26)
        self.assertEqual(result["historical_original_recoveryos_findings_closed"],0)
        self.assertEqual(result["first_customer_independent_human_approval_gates_unmet"],18)
        self.assertIsNone(result["real_customer_cash_recovered"])
        self.assertEqual(result["externally_publishable_empirical_claims_approved"],0)
        self.assertTrue(result["no_production_merge_deploy_or_new_schedules"])
        self.assertEqual(result["receipt_sha256"],digest({
            k:v for k,v in result.items() if k!="receipt_sha256"
        }))

    def test_good_bundle_is_valid_read_only_across_all_four_images(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)
            audit,settlement=populated(home)
            folder=home/"candidate"
            proof=backup.run_backup_restore_drill(
                audit,settlement,work_dir=folder
            )
            manifest=backup.verify_backup_bundle(folder,proof)
            outcome=guard.verify_published_candidate(folder,proof,manifest)
            self.assertEqual(outcome["scope"],guard.SCOPE)
            self.assertEqual(outcome["published_sqlite_images_inspected"],4)
            self.assertEqual(outcome["whole_file_audit_and_financial_semantics_validated"],4)
            self.assertEqual(outcome["all_tenant_logical_content_matches_frozen_manifest"],4)
            self.assertTrue(outcome["scoped_source_and_restored_financial_receipts_matched"])
            self.assertTrue(outcome["read_only_sqlite_query_mode_used"])
            self.assertFalse(outcome["external_buyer_bank_carrier_authentication_established"])
            self.assertTrue(outcome["m49_two_file_atomic_commit_not_established"])

    def test_rebinding_all_four_local_hashes_does_not_hide_missing_audit_trigger(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)
            audit,settlement=populated(home)
            folder=home/"bundle"
            proof=backup.run_backup_restore_drill(audit,settlement,work_dir=folder)
            altered=lab._mutate(folder,"AUDIT_BACKUP_MISSING_IMMUTABLE_TRIGGER",proof)
            altered=lab._rebind_local_unkeyed_receipts(folder,altered)
            self.assertTrue(lab._predecessor_receipt_would_pass(folder,altered))
            with self.assertRaisesRegex(ValueError,
                    "M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID"):
                backup.verify_backup_bundle(folder,altered)

    def test_extra_valid_other_tenant_audit_event_changes_all_tenant_generation(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)
            audit,settlement=populated(home)
            folder=home/"bundle"
            proof=backup.run_backup_restore_drill(audit,settlement,work_dir=folder)
            foreign=AuditStore(
                folder/"audit.backup.sqlite3",
                buyer_id="M50-UNRELATED-OTHER-TENANT",business_unit="OPS",
            )
            foreign.append(
                event_type=AuditEventType.SOURCE_PRESENT,
                object_id="other-tenant-new-local-only",
                occurred_at="2026-09-27T12:00:00Z",
                evidence_hash="d"*64,
            )
            altered=lab._rebind_local_unkeyed_receipts(folder,proof)
            self.assertTrue(lab._predecessor_receipt_would_pass(folder,altered))
            with self.assertRaisesRegex(ValueError,
                   "M50_RECOVERY_BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH"):
                backup.verify_backup_bundle(folder,altered)

    def test_scoped_semantic_sha_is_independently_recomputed_from_actual_backup_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            path=root/"valid"
            result=backup.run_backup_restore_drill(audit,settlement,work_dir=path)
            a=guard._read_candidate(path/"audit.backup.sqlite3","audit")
            s=guard._read_candidate(path/"settlement.backup.sqlite3","settlement")
            self.assertEqual(
                guard._scoped_summary(a,s,result.buyer_id,result.business_unit),
                result.source_semantic_hash,
            )
            with self.assertRaisesRegex(ValueError,"M50_RECOVERY_INVALID_SOURCE_SCOPE"):
                guard._scoped_summary(a,s,"",result.business_unit)
            self.assertNotEqual(
                guard._scoped_summary(a,s,"M50-UNMATCHED-OWNER",result.business_unit),
                result.source_semantic_hash
            )

    def test_wrong_scope_even_with_forged_locally_rehashed_report_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            path=root/"bundle"
            result=backup.run_backup_restore_drill(audit,settlement,work_dir=path)
            result=lab._mutate(path,"LOCAL_REPORT_WRONG_TENANT_SCOPE",result)
            result=lab._rebind_local_unkeyed_receipts(path,result)
            self.assertTrue(lab._predecessor_receipt_would_pass(path,result))
            with self.assertRaisesRegex(ValueError,
                    "M50_RECOVERY_SCOPED_AUDIT_OR_SETTLEMENT_RECEIPT_MISMATCH"):
                backup.verify_backup_bundle(path,result)

    def test_rehashed_false_claim_of_human_pilot_approval_is_blocked(self):
        self.assertEqual(
            lab.replay_one("MANIFEST_FAKE_HUMAN_APPROVAL")["expected_current_exact_denial"],
            "M50_RECOVERY_FALSE_RESTORE_PROVENANCE_OR_HUMAN_APPROVAL"
        )

    def test_recovery_manifest_symlink_is_blocked_before_sqlite_files_are_processed(self):
        self.assertEqual(
            lab.replay_one("COMPLETION_MARKER_REPLACED_WITH_SYMLINK")[
                "expected_current_exact_denial"
            ],
            "M50_RECOVERY_UNTRUSTED_BUNDLE_OR_COMPLETION_MARKER_SYMLINK",
        )

    def test_recovery_manifest_requires_exact_receipt_fields_not_just_proof_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            path=root/"bundle"
            result=backup.run_backup_restore_drill(audit,settlement,work_dir=path)
            marker=path/"capture.complete.json"
            record=json.loads(marker.read_text())
            record["source_semantic_hash"]="a"*64
            record["manifest_sha256"]=canonical_hash({
                k:v for k,v in record.items() if k!="manifest_sha256"
            })
            marker.write_text(json.dumps(record))
            self.assertEqual(record["proof_hash"],result.proof_hash)
            with self.assertRaisesRegex(ValueError,
                    "M50_RECOVERY_MANIFEST_SOURCE_RECEIPT_FIELDS_NOT_BOUND"):
                backup.verify_backup_bundle(path,result)

    def test_all_tenant_settlement_semantic_audit_refuses_same_cents_wrong_payer(self):
        self.assertEqual(lab.replay_one(
            "SETTLEMENT_BACKUP_WRONG_PAYER_WITH_ORIGINAL_DDL"
        )["expected_current_exact_denial"],
        "M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID")

    def test_readonly_candidate_checks_refuse_unknown_tables_or_types(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"no-unknown-family.sqlite3"
            with self.assertRaisesRegex(ValueError,"M50_UNKNOWN_SQLITE_FAMILY"):
                guard._read_candidate(db,"tampered")
            with self.assertRaisesRegex(ValueError,"M50_UNKNOWN_SQLITE_FAMILY"):
                guard._read_candidate(db,None)

    def test_wrong_signed_receipt_reason_or_false_acceptance_never_counts_as_proof(self):
        with patch.object(
            lab.backup,"verify_backup_bundle",
            return_value={"source_semantic_hash":"x"*64},
        ):
            with self.assertRaisesRegex(ValueError,"M50_KNOWN_GOOD_BUNDLE_BROKEN"):
                lab.replay_one("AUDIT_BACKUP_MISSING_IMMUTABLE_TRIGGER")

    def test_unregistered_scenario_does_not_mutate_any_existing_sqlite_source(self):
        for case in ("",None,True,42,"../someone-else.db","DROP TRIGGER"):
            with self.subTest(case=case):
                with self.assertRaisesRegex(ValueError,
                      "M50_UNKNOWN_RECOVERY_ADMISSION_CASE"):
                    lab.replay_one(case)
                with tempfile.TemporaryDirectory() as td:
                    db=Path(td)/"unused"
                    with self.assertRaisesRegex(ValueError,
                          "M50_UNREGISTERED_REHASHED_BUNDLE_ATTACK"):
                        lab._mutate(db,case,None)
                    self.assertFalse(db.exists())

    def test_invalid_date_and_escaped_html_do_not_approve_external_cash(self):
        for bad in (None,True,"2026-10-13",date(2026,10,12)):
            with self.subTest(date=bad),self.assertRaisesRegex(
                ValueError,"M50_INVALID_RESEARCH_AS_OF"
            ):
                lab.run_campaign(as_of=bad)
        result=lab.run_campaign(as_of=DAY)
        edited=deepcopy(result)
        edited["cases"][0]["case"]="<script>alert(1)</script>"
        html=lab.render_html(edited)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("26 historical findings",result["caveat"])
        self.assertFalse(result["external_immutable_or_crypto_signed_backup_proven"])

    def test_cli_writes_metadata_only_and_no_real_databases(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)
            out=home/"result"
            with patch("sys.argv",[
                "m50","--as-of-date","2026-10-13","--out",str(out)
            ]):
                lab.main()
            report=json.loads((out/"recovery_admission_m50.json").read_text())
            self.assertEqual(report["current_exact_fail_closed_recovery_denials"],13)
            self.assertEqual(report["historical_original_recoveryos_findings_closed"],0)
            self.assertTrue((out/"recovery_admission_m50.html").is_file())
            self.assertFalse(any(p.suffix in (".db",".sqlite3") for p in out.iterdir()))
            invalid=home/"blocked"
            with patch("sys.argv",[
                "m50","--as-of-date","2026-10-12","--out",str(invalid)
            ]):
                with self.assertRaisesRegex(ValueError,"M50_INVALID_RESEARCH_AS_OF"):
                    lab.main()
            self.assertFalse(invalid.exists())


if __name__=="__main__":
    unittest.main()
