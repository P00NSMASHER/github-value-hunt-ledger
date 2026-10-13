"""Mission 46: real SQLite DDL tamper denial and transaction/tenant proof.

The original M44/M45 money checks are NOT weakened. These tests exercise
a changed SQLite catalogue with completely consistent underlying financial
rows, including missing and no-op replacement triggers.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight.lab_assurance import digest
from freight import lab_schema_integrity_m46 as m46
from freight import lab_persistent_semantic_m44 as m44
from freight import settlement_schema_guard_m46 as sg
from freight.settlement_store import SettlementEventRecord, SettlementStore
from freight.test_lab_phase3_real_chain import funded_store


class M46SQLiteSchemaTests(unittest.TestCase):
    def test_exact_ten_ddl_scenarios_block_every_live_read_write_and_reopen(self):
        self.assertEqual(len(m46.DDL_ATTACKS),10)
        self.assertEqual(len(m46.READ_ACTIONS),7)
        for attack, (_ddl, expected) in m46.DDL_ATTACKS.items():
            with self.subTest(attack=attack):
                result=m46.replay_one(attack)
                self.assertEqual(result["schema_mutation"],attack)
                self.assertEqual(result["expected_denial"],expected)
                self.assertEqual(result["positive_original_money_reads"],5)
                self.assertEqual(result["read_surface_exact_denials"],7)
                self.assertTrue(result["write_attempt_denied"])
                self.assertTrue(result["reopen_denied_without_recreating_triggers"])
                self.assertTrue(result["denied_sources_did_not_change_mutated_schema"])
                self.assertEqual(result["denied_api_surface_ids"],
                                 [*m46.READ_ACTIONS,"new_provider_write"])
                self.assertNotEqual(result["original_schema_catalog_digest"],
                                    result["test_only_mutated_schema_catalog_digest"])
                self.assertFalse(result["original_historical_defect_closed"])
                self.assertFalse(result["real_customer_carrier_or_bank_credentials_used"])

    def test_complete_campaign_keeps_original_findings_and_human_approvals_open(self):
        report=m46.run_campaign(as_of=date(2026,10,13))
        self.assertEqual(report["scope"],m46.SCOPE)
        self.assertEqual(report["existing_research_lab_count"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["disposable_ddl_mutation_cases"],10)
        self.assertEqual(report["positive_synthetic_money_controls"],50)
        self.assertEqual(report["financial_read_denials"],70)
        self.assertEqual(report["attempted_write_denials"],10)
        self.assertEqual(report["preexisting_file_reopen_denials"],10)
        self.assertTrue(report["denied_mutations_preserved_test_source"])
        self.assertEqual(report["original_historical_findings_open"],26)
        self.assertEqual(report["original_historical_findings_closed"],0)
        self.assertEqual(report["human_first_customer_pilot_gates_unmet"],18)
        self.assertFalse(report["independent_real_bank_evidence_reproduced"])
        self.assertEqual(report["actual_customer_invoices_imported"],0)
        self.assertEqual(report["actual_company_revenue_cents"],0)
        self.assertEqual(report["public_empirical_claims_approved"],0)
        self.assertTrue(report["no_live_deployments_or_schedules_changed"])
        self.assertEqual(report["receipt_sha256"],digest({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_reviewed_schema_source_policy_is_exact_and_complete(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            with sqlite3.connect(store.path) as c:
                policy=sg.assert_sqlite_schema(c)
            self.assertTrue(policy["six_original_tables_intact"])
            self.assertTrue(policy["thirty_original_triggers_intact"])
            self.assertTrue(policy["four_original_explicit_indexes_intact"])
            self.assertTrue(policy["trigger_and_unique_constraint_policy_matches_source"])
            self.assertTrue(policy["not_external_bank_carrier_or_customer_evidence"])
            self.assertEqual(sg._git_blob_sha1(sg.SCHEMA_PATH.read_bytes()),
                             sg.SCHEMA_GIT_BLOB_SHA1)
            expected=sg._expected()
            self.assertEqual(len(expected),40)

    def test_source_schema_change_requires_reviewed_policy_update_not_self_healing(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"surreptitiously-edited-schema.sql"
            text=sg.SCHEMA_PATH.read_text()
            path.write_text(text.replace("immutable_claim_u","falsified_claim_u",1))
            with patch.object(sg,"SCHEMA_PATH",path):
                sg._expected.cache_clear()
                try:
                    with self.assertRaisesRegex(RuntimeError,
                                                "M46_SQLITE_APPROVED_SCHEMA_SOURCE_CHANGED"):
                        sg._expected()
                finally:
                    sg._expected.cache_clear()
            self.assertEqual(len(sg._expected()),40)

    def test_new_empty_database_is_initialized_but_existing_empty_db_is_not_silently_adopted(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"new.sqlite3"
            s=SettlementStore(db,buyer_id="TEST",business_unit="DIVISION")
            self.assertTrue(db.is_file())
            self.assertEqual(s.realized_cents(),0)
            db2=Path(td)/"preexisting-empty.sqlite3"
            sqlite3.connect(db2).close()
            with self.assertRaisesRegex(RuntimeError,"M46_SQLITE_EXISTING_SOURCE_UNREADABLE|legacy unscoped"):
                SettlementStore(db2,buyer_id="TEST",business_unit="DIVISION")
            with sqlite3.connect(db2) as c:
                self.assertEqual(c.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchone()[0],0)

    def test_post_write_drop_only_trigger_is_rolled_back_in_entire_sqlite_tx(self):
        with tempfile.TemporaryDirectory() as td:
            s=funded_store(td)
            db=Path(s.path)
            before=m46._catalog_receipt(db)
            def malicious(conn):
                conn.execute("DROP TRIGGER immutable_claim_u")
                conn.execute(
                    "INSERT INTO settlement_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    ("SIM-BUYER","SIM-DIVISION","m46-unauthorized-event",
                     "INV-100","SIM-CARRIER","SIM-BUYER","USD",1,
                     "2026-12-20T12:00:00.000000Z",
                     sha256(b"m46-unauthorized").hexdigest(),"EXTERNAL"),
                )
                return "MUST_ROLL_BACK"
            with self.assertRaisesRegex(RuntimeError,"M46_SQLITE_CATALOG_OBJECTS_CHANGED"):
                s._write(malicious)
            self.assertEqual(m46._catalog_receipt(db),before)
            self.assertEqual(s.count("settlement_events"),2)
            with sqlite3.connect(db) as c:
                self.assertEqual(c.execute(
                    "SELECT COUNT(*) FROM settlement_events "
                    "WHERE event_id='m46-unauthorized-event'"
                ).fetchone()[0],0)

    def test_schema_is_global_so_tenant_a_cannot_ignore_tenant_b_trigger_changes(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"multi-tenant.sqlite3"
            a=SettlementStore(db,buyer_id="TENANT-A",business_unit="OPS")
            b=SettlementStore(db,buyer_id="TENANT-B",business_unit="OPS")
            self.assertEqual(a.realized_cents(),0)
            self.assertEqual(b.realized_cents(),0)
            with sqlite3.connect(db) as con:
                con.execute("DROP TRIGGER allocation_event_capacity")
            for user in (a,b):
                with self.assertRaisesRegex(RuntimeError,"M46_SQLITE_CATALOG_OBJECTS_CHANGED"):
                    user.realized_cents()
            with self.assertRaisesRegex(RuntimeError,"M46_SQLITE_CATALOG_OBJECTS_CHANGED"):
                SettlementStore(db,buyer_id="TENANT-A",business_unit="OPS")

    def test_m44_corrupted_rows_still_get_precise_semantic_denial_before_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            m44._attack(Path(store.path),"FEE_ELIGIBILITY_DRIFT")
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                store.realized_cents()

    def test_invalid_scenario_cannot_execute_sql(self):
        for attack in ("",None,True,17,"DROP TABLE","immutable_claim_u",
                       "X'; DELETE FROM recovery_claims;--"):
            with self.subTest(attack=attack),tempfile.TemporaryDirectory() as td:
                store=funded_store(td)
                before=m46._catalog_receipt(Path(store.path))
                with self.assertRaisesRegex(ValueError,"M46_UNREGISTERED_SCHEMA_MUTATION"):
                    m46.mutate_disposable_sqlite(Path(store.path),attack)
                self.assertEqual(m46._catalog_receipt(Path(store.path)),before)
                with self.assertRaisesRegex(ValueError,"M46_UNKNOWN_SCHEMA_ATTACK"):
                    m46.replay_one(attack)

    def test_schema_catalog_escaped_and_not_represented_as_bank_security_certificate(self):
        result=m46.run_campaign(as_of=date(2026,10,13))
        forged=deepcopy(result)
        forged["cases"][0]["schema_mutation"]="<img src=x onerror=alert(1)>"
        rendered=m46.render_html(forged)
        self.assertIn("&lt;img",rendered)
        self.assertNotIn("<img",rendered)
        self.assertIn("26/26",rendered)
        self.assertIn("SYNTHETIC INTERNAL ONLY",rendered)

    def test_bad_date_fails_before_artifact_directory_is_created(self):
        for d in ("2026-10-13",None,True,date(2026,10,12)):
            with self.subTest(d=d),self.assertRaisesRegex(ValueError,"M46_INVALID_AS_OF_DATE"):
                m46.run_campaign(as_of=d)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"absent"
            with patch("sys.argv",[
                "m46","--as-of-date","2026-10-12","--out",str(out)
            ]):
                with self.assertRaisesRegex(ValueError,"M46_INVALID_AS_OF_DATE"):
                    m46.main()
            self.assertFalse(out.exists())

    def test_cli_produces_internal_aggregate_receipts_not_invoice_files(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"out"
            with patch("sys.argv",["m46","--as-of-date","2026-10-13","--out",str(target)]):
                m46.main()
            saved=json.loads((target/"sqlite_schema_integrity_m46.json").read_text())
            self.assertEqual(saved["financial_read_denials"],70)
            self.assertEqual(saved["attempted_write_denials"],10)
            self.assertEqual(saved["preexisting_file_reopen_denials"],10)
            self.assertFalse(saved["independent_real_bank_evidence_reproduced"])
            self.assertTrue((target/"sqlite_schema_integrity_m46.html").is_file())


if __name__=="__main__":
    unittest.main()
