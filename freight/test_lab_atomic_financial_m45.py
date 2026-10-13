"""M45 real SettlementStore read/write transactional source gates (synthetic)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight.lab_assurance import digest
from freight import lab_atomic_financial_m45 as m45
from freight import lab_persistent_semantic_m44 as m44
from freight import settlement_semantic_guard_m44 as safety
from freight.settlement_store import (
    RecoveryClaim, SettlementEventRecord, SettlementStore,
)
from freight.test_lab_phase3_real_chain import funded_store


class M45TransactionalPersistentFinancialTests(unittest.TestCase):
    def test_eight_damaged_sources_fail_all_six_live_operation_surfaces(self):
        self.assertEqual(len(m44.ATTACKS),8)
        self.assertEqual(len(m45.READ_SURFACES),5)
        for scenario, expected in m44.ATTACKS.items():
            with self.subTest(scenario=scenario):
                report=m45.replay_one(scenario)
                self.assertEqual(report["source_attack"],scenario)
                self.assertEqual(report["exact_source_error_code"],expected)
                self.assertEqual(report["positive_read_surfaces_passed"],5)
                self.assertEqual(report["read_operation_denials"],5)
                self.assertEqual(report["write_operation_denials"],1)
                self.assertEqual(report["verified_denied_operation_ids"],
                                 [*m45.READ_SURFACES,m45.WRITE_SURFACE])
                self.assertTrue(report["rejected_actions_left_source_unchanged"])
                self.assertNotEqual(
                    report["pre_corruption_synthetic_source_digest"],
                    report["post_corruption_synthetic_source_digest"],
                )
                self.assertFalse(report["independently_verified_bank_or_buyer_authority"])
                self.assertFalse(report["original_historical_finding_closed"])

    def test_aggregate_frozen_historical_and_external_approval_boundaries(self):
        report=m45.run_campaign(as_of=date(2026,10,13))
        self.assertEqual(report["original_research_lab_count"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertTrue(report["original_corpus_is_unmodified"])
        self.assertEqual(report["corrupted_persistent_source_scenarios"],8)
        self.assertEqual(report["current_financial_read_denials"],40)
        self.assertEqual(report["current_financial_write_denials"],8)
        self.assertEqual(report["total_fail_closed_financial_operations"],48)
        self.assertTrue(report["pre_and_post_commit_semantic_validation_enabled"])
        self.assertTrue(report["financial_reconciliation_observes_one_pinned_sqlite_revision"])
        self.assertEqual(report["current_original_historical_findings_open"],26)
        self.assertEqual(report["current_original_historical_findings_closed"],0)
        self.assertEqual(report["independent_human_first_customer_pilot_controls_unmet"],18)
        self.assertEqual(report["actual_customer_transactions_imported"],0)
        self.assertIsNone(report["actual_customer_cash_recovered_usd"])
        self.assertFalse(report["external_commercial_approval_granted"])
        self.assertFalse(report["production_deployment_or_schedule_changed"])
        self.assertEqual(report["receipt_sha256"],digest({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_prewrite_guard_does_not_allow_even_valid_new_event_after_source_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            db=Path(store.path)
            m44._attack(db,"FEE_ELIGIBILITY_DRIFT")
            mutated=m44._raw_digest(db)
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                store.ingest_event(
                    SettlementEventRecord(
                        "unrelated-valid-attempt","INV-100",
                        "SIM-CARRIER","SIM-BUYER","USD",1,
                        "2026-12-20T12:00:00Z",
                        sha256(b"unrelated-valid-attempt").hexdigest(),
                        "EXTERNAL",
                    )
                )
            self.assertEqual(m44._raw_digest(db),mutated)
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM settlement_events "
                    "WHERE event_id='unrelated-valid-attempt'"
                ).fetchone()[0],0)

    def test_postwrite_semantic_check_rolls_back_both_illegal_data_and_trigger_change(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            db=Path(store.path)
            original=m44._raw_digest(db)
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                def bad_write(conn):
                    conn.execute("DROP TRIGGER immutable_alloc_u")
                    conn.execute(
                        "UPDATE allocations SET fee_eligible_cents=1 "
                        "WHERE allocation_id='allocation-400'"
                    )
                    return "SHOULD_NOT_COMMIT"
                store._write(bad_write)
            self.assertEqual(m44._raw_digest(db),original)
            with sqlite3.connect(db) as conn:
                triggers={r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger'"
                )}
                self.assertIn("immutable_alloc_u",triggers,
                              "rollback must restore trigger DDL as well as source rows")
            self.assertEqual(store.realized_cents(),500)
            self.assertEqual(store.fee_eligible_cents(),500)

    def test_write_checked_within_same_transaction_even_when_source_changes_during_op(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            baseline=m44._raw_digest(Path(store.path))
            # A test-only callable stages a bad edit AFTER the pre-check.
            # Post-check must catch it while still holding the write lock.
            def stage_corruption(conn):
                conn.execute("DROP TRIGGER immutable_counter_u")
                conn.execute(
                    "UPDATE counter_events SET amount_cents=601 "
                    "WHERE counter_id='return-500'"
                )
                return "INVALID"
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_RETURN_CAPACITY_EXCEEDS_CREDIT"):
                store._write(stage_corruption)
            self.assertEqual(m44._raw_digest(Path(store.path)),baseline)
            self.assertEqual(store.count("counter_events"),1)

    def test_read_revision_is_pinned_before_a_concurrent_valid_writer_commits(self):
        # Before M45, an already-open count() could be read independently of
        # the initial semantic scan; M45 pins read snapshot via BEGIN and
        # verifies that the same revision is used for subsequent SELECT.
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            inserted=[]
            original=safety.audit_connection

            def injected_check(conn,*,scope=None):
                proof=original(conn,scope=scope)
                if not inserted and scope == ("SIM-BUYER","SIM-DIVISION"):
                    inserted.append(True)
                    store.ingest_event(
                        SettlementEventRecord(
                            "m45-outside-concurrent-write","INV-100",
                            "SIM-CARRIER","SIM-BUYER","USD",1,
                            "2026-12-20T12:00:00Z",
                            sha256(b"m45-outside-concurrent-write").hexdigest(),
                            "EXTERNAL",
                        )
                    )
                return proof

            with patch.object(safety,"audit_connection",side_effect=injected_check):
                count=store.count("settlement_events")
            self.assertEqual(count,2,
                             "Read must stay pinned despite newer committed writer")
            self.assertEqual(store.count("settlement_events"),3)
            self.assertEqual(len(inserted),1)

    def test_current_sqlite_foreign_tenant_corruption_cannot_leak_into_valid_scoped_reads(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"shared.sqlite3"
            safe=SettlementStore(path,buyer_id="TENANT-A",business_unit="OPS")
            corrupt=SettlementStore(path,buyer_id="TENANT-B",business_unit="OPS")
            corrupt.create_claim(
                RecoveryClaim(
                    "b-only","I-B","carrier","buyer","USD",1000,
                    "2026-09-01T10:00:00Z",
                    sha256(b"m45-tenant-b-only").hexdigest(),False,
                )
            )
            corrupt.ingest_event(
                SettlementEventRecord(
                    "event-b","I-B","carrier","buyer","USD",1000,
                    "2026-09-02T10:00:00Z",
                    sha256(b"m45-tenant-b-credit").hexdigest(),"EXTERNAL",
                )
            )
            corrupt.auto_allocate("event-b",created_at="2026-09-02T11:00:00Z")
            # Scoped valid reads do not leak another tenant's rows.
            self.assertEqual(safe.realized_cents(),0)
            self.assertEqual(safe.fee_eligible_cents(),0)
            self.assertEqual(safe.count("allocations"),0)
            with sqlite3.connect(path) as con:
                con.execute("DROP TRIGGER immutable_alloc_u")
                con.execute(
                    "UPDATE allocations SET fee_eligible_cents=0 "
                    "WHERE buyer_id='TENANT-B'"
                )
            # M46 must reject globally missing protection triggers even
            # when TENANT-A's money itself remains semantically valid.
            with self.assertRaisesRegex(RuntimeError,
                                         "M46_SQLITE_CATALOG_OBJECTS_CHANGED"):
                safe.realized_cents()
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                corrupt.realized_cents()
            # A new instance validates the WHOLE database on reopen.
            with self.assertRaisesRegex(RuntimeError,
                                         "M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT"):
                SettlementStore(path,buyer_id="TENANT-A",business_unit="OPS")

    def test_unrelated_valid_write_does_not_break_idempotent_retries(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            new=SettlementEventRecord(
                "m45-true-valid","INV-100","SIM-CARRIER","SIM-BUYER","USD",1,
                "2026-12-20T12:00:00Z",
                sha256(b"m45-true-valid").hexdigest(),"EXTERNAL",
            )
            self.assertTrue(store.ingest_event(new))
            self.assertFalse(store.ingest_event(new))
            self.assertEqual(store.count("settlement_events"),3)
            self.assertEqual(store.realized_cents(),500)

    def test_rejected_operations_do_not_mutate_corrupt_source_even_after_failed_reads(self):
        with tempfile.TemporaryDirectory() as td:
            store=funded_store(td)
            db=Path(store.path)
            m44._attack(db,"COUNTERPARTY_DRIFT")
            before=m44._raw_digest(db)
            for read in (
                store.realized_cents,store.fee_eligible_cents,
                lambda:store.claim_residual("case-1"),
                lambda:store.event_residual("credit-400"),
                lambda:store.count("allocations"),
            ):
                with self.assertRaisesRegex(RuntimeError,
                                             "M44_ALLOCATION_CURRENCY_OR_COUNTERPARTY_DRIFT"):
                    read()
            self.assertEqual(m44._raw_digest(db),before)

    def test_bad_scenario_input_has_no_filed_or_network_effect(self):
        for k in ("",None,False,1,"DROP TABLE","GATE-001"):
            with self.subTest(k=k),self.assertRaisesRegex(
                ValueError,"M45_UNREGISTERED_PERSISTENT_SOURCE_ATTACK"
            ):
                m45.replay_one(k)

    def test_bad_date_rejected_without_writing_artifacts(self):
        for d in ("2026-10-13",None,True,date(2026,10,12)):
            with self.subTest(d=d),self.assertRaisesRegex(
                ValueError,"M45_INVALID_RESEARCH_AS_OF"
            ):
                m45.run_campaign(as_of=d)

    def test_html_escapes_and_discloses_synthetic_limited_scope(self):
        result=m45.run_campaign(as_of=date(2026,10,13))
        tampered=deepcopy(result)
        tampered["cases"][0]["source_attack"]="<img src=x onerror=alert(1)>"
        html=m45.render_html(tampered)
        self.assertIn("&lt;img",html)
        self.assertNotIn("<img",html)
        self.assertIn("26 open / 0 closed",html)
        self.assertIn("OFFLINE SYNTHETIC ONLY",html)

    def test_cli_returns_derived_internal_only_report_and_no_invalid_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            ok=root/"ok"
            with patch("sys.argv",[
                "m45","--as-of-date","2026-10-13","--out",str(ok)
            ]):
                m45.main()
            data=json.loads((ok/"atomic_financial_operations_m45.json").read_text())
            self.assertEqual(data["total_fail_closed_financial_operations"],48)
            self.assertFalse(data["source_authenticity_or_bank_signature_established"])
            self.assertTrue((ok/"atomic_financial_operations_m45.html").exists())
            bad=root/"not-created"
            with patch("sys.argv",[
                "m45","--as-of-date","2026-10-12","--out",str(bad)
            ]):
                with self.assertRaises(ValueError):
                    m45.main()
            self.assertFalse(bad.exists())


if __name__ == "__main__":
    unittest.main()
