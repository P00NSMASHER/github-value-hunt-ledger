"""M44 — eight privileged-edit semantic-drift probes on REAL persistent store.

All tests operate on fresh disposable SQLite, with zero external provider,
customer, carrier, authenticated bank keys, or production configuration.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from freight.lab_assurance import digest
from freight import lab_persistent_semantic_m44 as m44
from freight.settlement_store import SettlementStore
from freight.test_lab_phase3_real_chain import funded_store
from freight.backup_restore import workspace_summary,run_backup_restore_drill
from freight.test_backup_restore import populated

TODAY=date(2026,10,13)


class PersistentSemanticM44Tests(unittest.TestCase):
    def test_eight_source_drifts_fail_current_report_audit_and_reopen(self):
        self.assertEqual(len(m44.ATTACKS),8)
        for name, reason in m44.ATTACKS.items():
            with self.subTest(scenario=name):
                x=m44.replay_one(name)
                self.assertEqual(x["scenario"],name)
                self.assertEqual(x["expected_exact_rejection"],reason)
                self.assertTrue(x["positive_scoped_persistent_store_verified"])
                self.assertTrue(x["actual_sqlite_source_rows_changed"])
                self.assertTrue(x["current_store_report_rejected"])
                self.assertTrue(x["current_store_audit_rejected"])
                self.assertTrue(x["reopen_existing_store_rejected"])
                self.assertNotEqual(x["before_fictional_sqlite_receipt_sha256"],
                                    x["after_fictional_sqlite_receipt_sha256"])
                self.assertFalse(x["original_historical_recoveryos_defect_closed"])
                self.assertFalse(x["live_customer_or_bank_data_read"])

    def test_original_fourteen_labs_will_only_see_typed_no_customer_attestation(self):
        r=m44.run_campaign(as_of=TODAY)
        self.assertEqual(r["scope"],m44.SCOPE)
        self.assertEqual(r["existing_research_lab"],14)
        self.assertFalse(r["new_lab_created"])
        for field in (
            "current_persistent_store_cases","positive_current_store_controls",
            "reported_financial_drift_denials","explicit_audit_denials","reopen_denials",
        ):
            self.assertEqual(r[field],8)
        self.assertEqual(r["original_historical_findings_open"],26)
        self.assertEqual(r["original_historical_findings_closed"],0)
        self.assertEqual(r["original_vulnerable_git_baselines_replayed"],0)
        self.assertEqual(r["separate_independent_human_customer_pilot_controls_unmet"],18)
        self.assertEqual(r["actual_customer_data_imports"],0)
        self.assertFalse(r["actual_bank_or_carrier_evidence_verified"])
        self.assertEqual(r["external_empirical_recovery_claims_approved"],0)
        self.assertEqual(r["receipt_sha256"],
                         digest({k:v for k,v in r.items() if k!="receipt_sha256"}))

    def test_valid_persistent_source_audit_has_no_real_world_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=funded_store(tmp)
            r=s.assert_semantic_integrity()
            self.assertEqual(r["validated_claims"],1)
            self.assertEqual(r["validated_allocations"],2)
            self.assertEqual(r["validated_returns"],1)
            self.assertEqual(r["validated_reversals"],1)
            self.assertTrue(r["input_is_current_sqlite_only_not_signed_original_evidence"])
            self.assertTrue(r["no_external_original_source_attestation"])
            self.assertTrue(r["no_real_bank_or_customer_countersigned_authority"])
            self.assertFalse("claim_id" in r)
            self.assertEqual(s.realized_cents(),500)

    def test_corruption_after_store_constructed_refuses_report_without_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=funded_store(tmp)
            m44._attack(Path(s.path),"RECEIPT_OVER_ALLOCATED")
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_CAPACITY_EXCEEDS_CREDIT"):
                s.report_snapshot_json()
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_CAPACITY_EXCEEDS_CREDIT"):
                s.assert_semantic_integrity()

    def test_corrupt_backup_is_rejected_before_semantically_validating_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,s=populated(root)
            before=workspace_summary(audit,s)
            self.assertEqual(before.recovery_claim_count,1)
            self.assertEqual(before.settlement_event_count,1)
            self.assertEqual(before.allocation_count,1)
            self.assertEqual(before.realized_cents,50000)
            m44_dir=root/"fake-restore"
            with sqlite3.connect(s.path) as c:
                c.execute("DROP TRIGGER immutable_alloc_u")
                c.execute(
                    "UPDATE allocations SET fee_eligible_cents=0 "
                    "WHERE allocation_id='auto:e1:c1'"
                )
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                workspace_summary(audit,s)
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                run_backup_restore_drill(audit,s,work_dir=m44_dir)
            self.assertFalse((m44_dir/"settlement.backup.sqlite3").exists())
            self.assertFalse((m44_dir/"audit.backup.sqlite3").exists())

    def test_snapshot_derived_metrics_do_not_mix_independent_settlement_revisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit,s=populated(Path(tmp))
            # Regression: older workspace_summary separately queried count,
            # realized and eligible through separate SQLite connections.
            # Source is now one immutable report_snapshot_json() receipt.
            with patch.object(s,"realized_cents",side_effect=AssertionError(
                "M44 must not use non-atomic balance read"
            )),patch.object(s,"fee_eligible_cents",side_effect=AssertionError(
                "M44 must not use non-atomic fee read"
            )),patch.object(s,"count",side_effect=AssertionError(
                "M44 must not use non-atomic count read"
            )):
                report=workspace_summary(audit,s)
            self.assertEqual(report.realized_cents,50000)
            self.assertEqual(report.fee_eligible_cents,50000)
            self.assertEqual(report.allocation_count,1)
            self.assertEqual(report.counter_event_count,0)
            self.assertEqual(report.reversal_edge_count,0)

    def test_multi_tenant_report_scopes_drift_without_cross_customer_leak(self):
        from freight.test_settlement_store import C,E,ALLOCATED_AT
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            db=root/"shared.sqlite3"
            a=SettlementStore(db,buyer_id="TENANT-A",business_unit="OPS")
            b=SettlementStore(db,buyer_id="TENANT-B",business_unit="OPS")
            b.create_claim(C())
            b.ingest_event(E())
            self.assertEqual(b.auto_allocate("e1",created_at=ALLOCATED_AT).status,
                             "ALLOCATED")
            self.assertEqual(a.assert_semantic_integrity()["validated_claims"],0)
            # A clean tenant's report remains scoped before the malicious
            # modification; no Tenant B customer rows may leak to Tenant A.
            good=json.loads(a.report_snapshot_json())
            self.assertEqual(good["buyer_id"],"TENANT-A")
            self.assertEqual(len(good["tables"]["allocations"]),0)
            with sqlite3.connect(db) as con:
                con.execute("DROP TRIGGER immutable_alloc_u")
                con.execute(
                    "UPDATE allocations SET fee_eligible_cents=0 "
                    "WHERE buyer_id='TENANT-B' AND allocation_id='auto:e1:c1'"
                )
            # M46's schema defense is GLOBAL, even though M44's money
            # audit is scoped. A cannot safely use a shared database with
            # missing protection triggers, regardless of whose rows changed.
            with self.assertRaisesRegex(RuntimeError,
                                         "M46_SQLITE_CATALOG_OBJECTS_CHANGED"):
                a.report_snapshot_json()
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                b.report_snapshot_json()
            # Reopen audits the WHOLE file and may refuse it even if the
            # requesting workspace itself had no tampered rows.
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                SettlementStore(db,buyer_id="TENANT-A",business_unit="OPS")

    def test_tampered_raw_event_denials_do_not_claim_a_signed_provider_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=funded_store(tmp)
            m44._attack(Path(s.path),"COUNTERPARTY_DRIFT")
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_CURRENCY_OR_COUNTERPARTY_DRIFT"):
                s.report_snapshot_json()
            # No independent original bank signature checked by semantic guard.
            self.assertFalse(
                "BANK_SIGNED" in m44.SCOPE
            )

    def test_invalid_attack_identifiers_cannot_execute_sql(self):
        for name in ("",None,True,5,"recovery_claims",
                     "x'; DROP TABLE settlement_events;--"):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                s=funded_store(tmp)
                before=m44._raw_digest(Path(s.path))
                with self.assertRaisesRegex(ValueError,
                                             "M44_UNKNOWN_SYNTHETIC_STORE_MUTATION"):
                    m44._attack(Path(s.path),name)
                self.assertEqual(before,m44._raw_digest(Path(s.path)))
                with self.assertRaisesRegex(ValueError,
                                             "M44_UNKNOWN_PERSISTENT_SETTLEMENT_CASE"):
                    m44.replay_one(name)

    def test_unexpected_audit_failure_does_not_count_as_verified_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=funded_store(tmp)
            good=s.assert_semantic_integrity()
            self.assertEqual(good["validated_claims"],1)
        with patch.object(m44,"_raw_digest",return_value="0"*64):
            with self.assertRaisesRegex(ValueError,"M44_PRIVILEGED_TEST_MUTATION_WAS_NOT_APPLIED"):
                m44.replay_one("RETURN_OVER_CREDIT")

    def test_html_escapes_untrusted_display_and_no_external_claims(self):
        r=m44.run_campaign(as_of=TODAY)
        poisoned=deepcopy(r)
        poisoned["cases"][0]["scenario"]="<script>alert(1)</script>"
        html=m44.render_html(poisoned)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("26 historical findings remain open",html)
        self.assertEqual(r["external_empirical_recovery_claims_approved"],0)

    def test_invalid_date_fails_before_output_directory_exists(self):
        for d in (date(2026,10,12),None,True,"2026-10-13"):
            with self.subTest(d=d),self.assertRaisesRegex(ValueError,"M44_INVALID_AS_OF_DATE"):
                m44.run_campaign(as_of=d)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"new"
            with patch("sys.argv",[
                "m44","--as-of-date","2026-10-12","--out",str(out)
            ]):
                with self.assertRaisesRegex(ValueError,"M44_INVALID_AS_OF_DATE"):
                    m44.main()
            self.assertFalse(out.exists())

    def test_cli_generates_internal_json_and_html_without_private_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"read-only"
            with patch("sys.argv",[
                "m44","--as-of-date","2026-10-13","--out",str(out)
            ]):
                m44.main()
            data=json.loads((out/"persistent_semantic_m44.json").read_text())
            self.assertEqual(data["reported_financial_drift_denials"],8)
            self.assertEqual(data["original_historical_findings_closed"],0)
            self.assertEqual(data["separate_independent_human_customer_pilot_controls_unmet"],18)
            self.assertTrue((out/"persistent_semantic_m44.html").is_file())
            self.assertNotIn("customer_invoice_source_blob",data)


if __name__=="__main__":
    unittest.main()
