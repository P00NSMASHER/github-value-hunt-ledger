"""M48 current persistent audit trail protection, no real customer content.

Exercises thirteen disposable attacks against source DDL, scoped audit
hash-chain integrity and original database path continuity. Inherited
SettlementStore tests remain independent.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight import audit_store_integrity_m48 as policy
from freight import lab_audit_trust_boundary_m48 as m48
from freight.backup_restore import run_backup_restore_drill
from freight.test_backup_restore import populated


TODAY=date(2026,10,13)


class M48PersistentAuditTests(unittest.TestCase):
    def test_thirteen_real_current_file_or_hash_attacks_are_denied(self):
        self.assertEqual(len(m48.ATTACKS),13)
        for scenario, code in m48.ATTACKS.items():
            with self.subTest(scenario=scenario):
                result=m48.replay_one(scenario)
                self.assertEqual(result["scenario"],scenario)
                self.assertEqual(result["exact_expected_denial"],code)
                self.assertEqual(result["positive_original_test_events"],2)
                self.assertEqual(result["existing_session_read_denials"],5)
                self.assertEqual(result["existing_session_append_denials"],1)
                self.assertEqual(result["denied_source_action_ids"],
                                 [*m48.READS,"append_new"])
                self.assertTrue(result["original_source_modified_only_in_disposable_sqlite"])
                self.assertFalse(result["original_historical_defect_closed"])
                self.assertFalse(result["actual_customer_account_or_carrier_records_used"])

    def test_campaign_preserves_all_twenty_six_unverified_and_pilot_permissions(self):
        result=m48.run_campaign(as_of=TODAY)
        self.assertEqual(result["scope"],m48.SCOPE)
        self.assertEqual(result["original_research_labs"],14)
        self.assertFalse(result["new_lab_created"])
        self.assertEqual(result["current_real_audit_file_attack_classes"],13)
        self.assertEqual(result["verified_fictional_positive_source_records_per_attack"],2)
        self.assertEqual(result["current_audit_read_denials"],65)
        self.assertEqual(result["current_audit_append_denials"],13)
        self.assertEqual(result["original_historical_findings_open"],26)
        self.assertEqual(result["original_historical_findings_closed"],0)
        self.assertEqual(result["independent_first_customer_approval_gates_unmet"],18)
        self.assertFalse(result["independently_attested_audit_log_or_original_customer_data"])
        self.assertEqual(result["actual_customer_or_bank_transactions_imported"],0)
        self.assertEqual(result["externally_publishable_empirical_claims"],0)
        self.assertFalse(result["production_deployed_or_schedules_modified"])

    def test_original_audit_catalog_is_byte_pinned_and_reproduces_old_shape(self):
        with tempfile.TemporaryDirectory() as td:
            store=m48._start(Path(td))
            with sqlite3.connect(store.path) as con:
                scope=policy.verify_audit_connection(con)
            self.assertEqual(scope["validated_scoped_audit_events"],2)
            self.assertEqual(scope["validated_nonempty_tenant_chains"],1)
            self.assertTrue(scope["all_tenant_chains_included"])
            self.assertTrue(scope["original_one_table_and_three_triggers_intact"])
            self.assertTrue(scope["no_independent_original_customer_or_bank_proof"])
            self.assertEqual(len(policy._expected_catalog()),4)
            self.assertEqual(policy._git_blob_sha1(policy.SCHEMA_PATH.read_bytes()),
                             policy.APPROVED_SCHEMA_GIT_BLOB_SHA1)

    def test_source_sql_modification_is_not_self_approved(self):
        with tempfile.TemporaryDirectory() as td:
            alternate=Path(td)/"altered.sql"
            original=policy.SCHEMA_PATH.read_text()
            alternate.write_text(original.replace(
                "audit_events_immutable_update",
                "audit_events_weak_update",1
            ))
            with patch.object(policy,"SCHEMA_PATH",alternate):
                policy._expected_catalog.cache_clear()
                try:
                    with self.assertRaisesRegex(
                        RuntimeError,"M48_AUDIT_APPROVED_SCHEMA_SOURCE_CHANGED"
                    ):
                        policy._expected_catalog()
                finally:
                    policy._expected_catalog.cache_clear()
            self.assertEqual(len(policy._expected_catalog()),4)

    def test_dropped_triggers_are_not_silently_repaired_during_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            s=m48._start(Path(td))
            with sqlite3.connect(s.path) as con:
                con.execute("DROP TRIGGER audit_events_immutable_update")
            with self.assertRaisesRegex(RuntimeError,
                                         "M48_AUDIT_SCHEMA_CATALOG_DRIFT"):
                AuditStore(s.path,buyer_id=s.buyer_id,business_unit=s.business_unit)
            with sqlite3.connect(s.path) as con:
                self.assertIsNone(con.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                    " AND name='audit_events_immutable_update'"
                ).fetchone())
            with self.assertRaisesRegex(RuntimeError,
                                         "M48_AUDIT_SCHEMA_CATALOG_DRIFT"):
                s.count()

    def test_hash_chain_tamper_fails_reads_and_append_even_with_original_ddl(self):
        with tempfile.TemporaryDirectory() as td:
            s=m48._start(Path(td))
            m48.mutate_fixture(Path(s.path),
                               "TAMPER_ORIGINAL_EVENT_RESTORE_TRIGGER")
            with sqlite3.connect(s.path) as con:
                self.assertEqual(
                    policy._catalog(con),policy._expected_catalog(),
                    "Schema restored exactly: the HASH CHAIN must fail independently."
                )
            for fn in (s.records,s.count,s.head,s.verify,s.semantic_summary):
                with self.assertRaisesRegex(RuntimeError,"M48_AUDIT_CHAIN_INVALID"):
                    fn()
            with self.assertRaisesRegex(RuntimeError,"M48_AUDIT_CHAIN_INVALID"):
                s.append(event_type=AuditEventType.SOURCE_PRESENT,
                         object_id="no-append",occurred_at="2026-10-01T12:00:00Z")
            with sqlite3.connect(s.path) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],2)

    def test_staged_trigger_removal_and_new_append_both_rollback_on_postcheck(self):
        with tempfile.TemporaryDirectory() as td:
            s=m48._start(Path(td))
            before=m48._catalog_fingerprint(Path(s.path))
            def bad_op(conn):
                conn.execute("DROP TRIGGER audit_events_immutable_delete")
                return "NEVER_COMMIT"
            with self.assertRaisesRegex(RuntimeError,"M48_AUDIT_SCHEMA_CATALOG_DRIFT"):
                s._write(bad_op)
            self.assertEqual(m48._catalog_fingerprint(Path(s.path)),before)
            self.assertEqual(s.count(),2)

    def test_valid_two_tenant_chains_reopen_and_corrupt_other_scope_fail_global(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"shared-audit.sqlite3"
            a=AuditStore(path,buyer_id="TENANT-A",business_unit="OPS")
            b=AuditStore(path,buyer_id="TENANT-B",business_unit="OPS")
            for store in (a,b):
                store.append(event_type=AuditEventType.SOURCE_PRESENT,
                             object_id="fictional",occurred_at="2026-10-01T10:00:00Z")
            self.assertEqual(a.count(),1)
            self.assertEqual(b.count(),1)
            with sqlite3.connect(path) as con:
                raw=con.execute(
                    "SELECT sql FROM sqlite_master WHERE type='trigger'"
                    " AND name='audit_events_immutable_update'"
                ).fetchone()[0]
                con.execute("DROP TRIGGER audit_events_immutable_update")
                con.execute(
                    "UPDATE audit_events SET object_id='tampered' WHERE buyer_id='TENANT-B'"
                )
                con.execute(raw)
            # Existing scope-bound reads do not leak B's rows to A,
            # but reopen checks EVERY tenant chain and rejects B's corruption.
            self.assertEqual(a.count(),1)
            with self.assertRaisesRegex(RuntimeError,"M48_AUDIT_CHAIN_INVALID"):
                b.records()
            with self.assertRaisesRegex(RuntimeError,"M48_AUDIT_CHAIN_INVALID"):
                AuditStore(path,buyer_id="TENANT-A",business_unit="OPS")

    def test_deleted_file_never_recreated_by_old_audit_session_or_backup(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            audit,settlement=populated(root)
            old=Path(audit.path)
            old.unlink()
            for op in (audit.count,audit.records,audit.head,audit.verify):
                with self.assertRaisesRegex(RuntimeError,
                                             "M47_SQLITE_SOURCE_FILE_MISSING"):
                    op()
            with self.assertRaisesRegex(RuntimeError,"M47_SQLITE_SOURCE_FILE_MISSING"):
                run_backup_restore_drill(
                    audit,settlement,work_dir=root/"drill"
                )
            self.assertFalse(old.exists())
            self.assertFalse((root/"drill"/"audit.backup.sqlite3").exists())

    def test_atomic_valid_audit_swap_needs_new_explicit_session(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=m48._start(root)
            replacement=root/"other.sqlite3"
            m48._copy_valid(Path(source.path),replacement)
            os.replace(replacement,source.path)
            with self.assertRaisesRegex(RuntimeError,"M47_SQLITE_SOURCE_FILE_REPLACED"):
                source.count()
            reopened=AuditStore(source.path,buyer_id=source.buyer_id,
                                business_unit=source.business_unit)
            self.assertEqual(reopened.count(),2)
            self.assertEqual(reopened.head(),
                             reopened.records()[-1].event_hash)

    def test_initial_audit_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            s=m48._start(root)
            name=root/"symlink.sqlite3"
            name.symlink_to(s.path)
            with self.assertRaisesRegex(RuntimeError,"M47_SQLITE_SOURCE_SYMLINK_REJECTED"):
                AuditStore(name,buyer_id="SIM-OWNER",business_unit="SIM-BU")

    def test_empty_existing_db_does_not_migrate_or_autocreate_protective_schema(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"preexisting-empty.sqlite3"
            sqlite3.connect(db).close()
            with self.assertRaises(RuntimeError):
                AuditStore(db,buyer_id="SIM-OWNER",business_unit="SIM-BU")
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM sqlite_master"
                ).fetchone()[0],0)

    def test_two_live_concurrent_audit_writers_keep_one_valid_history(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"audit.sqlite3"
            def append(i):
                a=AuditStore(db,buyer_id="A",business_unit="B")
                return a.append(event_type=AuditEventType.SOURCE_PRESENT,
                                object_id=f"synthetic-{i}",
                                occurred_at="2026-10-01T10:00:00Z").sequence
            with ThreadPoolExecutor(max_workers=6) as pool:
                indexes=list(pool.map(append,range(16)))
            self.assertEqual(sorted(indexes),list(range(1,17)))
            reopened=AuditStore(db,buyer_id="A",business_unit="B")
            self.assertEqual(reopened.count(),16)
            reopened.verify()

    def test_source_replacement_mid_read_or_write_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            s=m48._start(root)
            db=Path(s.path)
            alternate=root/"alt.sqlite3"
            m48._copy_valid(db,alternate)
            def swap_mid_read(con):
                os.replace(alternate,db)
                return 0
            with self.assertRaisesRegex(RuntimeError,"M47_SQLITE_SOURCE_FILE_REPLACED"):
                s._read(swap_mid_read)
            fresh=AuditStore(db,buyer_id=s.buyer_id,business_unit=s.business_unit)
            new_alt=root/"alt-again.sqlite3"
            m48._copy_valid(db,new_alt)
            def swap_mid_write(con):
                os.replace(new_alt,db)
                return 42
            with self.assertRaisesRegex(RuntimeError,"M47_SQLITE_SOURCE_FILE_REPLACED"):
                fresh._write(swap_mid_write)

    def test_invalid_attack_names_never_interact_with_user_paths(self):
        for bad in ("",None,0,True,"DROP TABLE","../../../private-audit.sqlite3"):
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as td:
                s=m48._start(Path(td))
                original=m48._catalog_fingerprint(Path(s.path))
                with self.assertRaisesRegex(ValueError,
                                             "M48_UNREGISTERED_DISPOSABLE_AUDIT_MUTATION"):
                    m48.mutate_fixture(Path(s.path),bad)
                with self.assertRaisesRegex(ValueError,
                                             "M48_UNKNOWN_AUDIT_TRUST_BOUNDARY_ATTACK"):
                    m48.replay_one(bad)
                self.assertEqual(m48._catalog_fingerprint(Path(s.path)),original)

    def test_invalid_date_and_html_claim_safety(self):
        for d in (None,True,date(2026,10,12),"2026-10-13"):
            with self.assertRaisesRegex(ValueError,"M48_INVALID_RESEARCH_DATE"):
                m48.run_campaign(as_of=d)
        report=m48.run_campaign(as_of=TODAY)
        bad=deepcopy(report)
        bad["cases"][0]["scenario"]="<script>alert(1)</script>"
        html=m48.render_html(bad)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("26 historical findings open",html)

    def test_cli_generates_derived_source_summary_without_customer_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"reports"
            with patch("sys.argv",["m48","--as-of-date","2026-10-13","--out",str(out)]):
                m48.main()
            data=json.loads((out/"audit_trust_boundary_m48.json").read_text())
            self.assertEqual(data["current_real_audit_file_attack_classes"],13)
            self.assertEqual(data["current_audit_read_denials"],65)
            self.assertEqual(data["current_audit_append_denials"],13)
            self.assertEqual(data["original_historical_findings_closed"],0)
            self.assertFalse(data["independently_attested_audit_log_or_original_customer_data"])
            self.assertTrue((out/"audit_trust_boundary_m48.html").is_file())


if __name__=="__main__":
    unittest.main()
