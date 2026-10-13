"""M40 regression: rehashed ledger forgeries and historical repair promotion."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from freight.lab_assurance import digest
from freight.lab_experiment_ledger import Experiment, ExperimentLedger
from freight import lab_historical_disposition_m40 as m40


def sample(*, finding="LAB-P0-03", name="case-01", repair=False) -> Experiment:
    return Experiment(
        experiment_id="m40:" + name,
        finding_id=finding,
        baseline_artifact_sha256=digest({"synthetic_baseline": name}),
        candidate_artifact_sha256=digest({"synthetic_candidate": name}),
        frozen_input_sha256=digest({"synthetic_input": name}),
        independent_test_sha256=digest({"mocked_run": name}),
        original_counterexample_reproduced=repair,
        repaired_counterexample_rejected=repair,
        known_good_control_passed=True,
        measured_runtime_ms=12,
        execution_scope="REAL_CODE_MOCKED_PROVIDERS",
    )


def alter_local_db(path: Path, *, record=None, table_change=None):
    """Explicitly bypass local append-only triggers ONLY in isolated test DB."""
    con=sqlite3.connect(path)
    try:
        con.execute("DROP TRIGGER IF EXISTS no_experiment_update")
        con.execute("DROP TRIGGER IF EXISTS no_experiment_delete")
        if record is not None:
            row=con.execute("SELECT sequence,receipt_json FROM experiments ORDER BY sequence LIMIT 1").fetchone()
            content=json.loads(row[1])
            record(content)
            local_sha=digest({"previous":None,"receipt":content})
            con.execute("UPDATE experiments SET receipt_json=?,receipt_sha256=? WHERE sequence=?",
                        (json.dumps(content,sort_keys=True),local_sha,row[0]))
        if table_change is not None:
            table_change(con)
        con.commit()
    finally:
        con.close()


class M40LedgerIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.path=self.root/"ledger.sqlite3"
        self.ledger=ExperimentLedger(self.path)

    def test_frozen_catalogue_and_original_26_are_not_repaired(self):
        book=m40._book()
        self.assertEqual(m40._git_blob(m40.BOOK.read_bytes()),m40.BOOK_GIT_BLOB_SHA1)
        self.assertEqual(len(book["entries"]),28)
        self.assertEqual(book["historical_open_findings"],26)
        report=m40.audit(ledger_path=self.path)
        self.assertEqual(report["original_historical_findings"],26)
        self.assertEqual(report["original_historical_findings_open"],26)
        self.assertEqual(report["original_historical_findings_closed_by_local_reports"],0)
        self.assertEqual(report["additional_research_gate_only_fixed_items"],2)
        self.assertEqual(report["all_registered_items_including_gate_corrections"],28)
        self.assertEqual(report["local_experiments_recorded"],0)
        self.assertEqual(report["independent_regression_or_repair_signoffs"],0)
        self.assertEqual(report["independent_customer_human_pilot_gates_unmet"],18)
        self.assertFalse(report["external_publication_authority"])

    def test_research_ledger_remains_useful_for_inconclusive_experiments(self):
        self.ledger.append(sample(name="a"))
        self.ledger.append(sample(finding="D-01",name="b"))
        self.assertEqual(len(self.ledger.read_and_verify()),2)
        report=m40.audit(ledger_path=self.path)
        self.assertEqual(report["local_experiments_recorded"],2)
        self.assertEqual(report["distinct_original_findings_with_experiments"],2)
        self.assertEqual(report["original_historical_findings_open"],26)
        self.assertTrue(all(not x["historical_defect_closed"] for x in report["historical_findings"]))

    def test_self_asserted_local_repair_not_promoted_to_original_defect_closure(self):
        self.ledger.append(sample(repair=True))
        declared=self.ledger.read_and_verify()[0]["verdict"]
        self.assertEqual(declared,"REPAIR_DEMONSTRATED_IN_STATED_TEST_SCOPE_ONLY")
        report=m40.audit(ledger_path=self.path)
        self.assertEqual(report["local_repair_assertions_not_attested"],1)
        self.assertEqual(report["original_historical_findings_closed_by_local_reports"],0)
        self.assertEqual(report["independent_regression_or_repair_signoffs"],0)
        item=next(x for x in report["historical_findings"]
                  if x["finding_id"]=="LAB-P0-03")
        self.assertTrue(item["local_repair_asserted_but_not_approved"])
        self.assertFalse(item["original_counterexample_replayed_in_this_audit"])

    def test_old_gate_only_corrections_do_not_close_recoveryos_findings(self):
        self.ledger.append(sample(finding="GATE-001",name="gate1",repair=True))
        self.ledger.append(sample(finding="GATE-002",name="gate2",repair=True))
        report=m40.audit(ledger_path=self.path)
        self.assertEqual(report["local_experiments_recorded"],2)
        self.assertEqual(report["distinct_original_findings_with_experiments"],0)
        self.assertEqual(report["original_historical_findings_open"],26)
        self.assertTrue(all(x["represents_historical_RecoveryOS_repair"] is False
                            for x in report["separate_research_gate_corrections"]))

    def test_rehashed_json_forged_verdict_rejected(self):
        self.ledger.append(sample())
        alter_local_db(self.path,record=lambda x:x.update(verdict=
            "REPAIR_DEMONSTRATED_IN_STATED_TEST_SCOPE_ONLY"))
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_VERDICT_NOT_DERIVED"):
            self.ledger.read_and_verify()
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_VERDICT_NOT_DERIVED"):
            m40.audit(ledger_path=self.path)

    def test_rehashed_extra_evidence_or_unknown_fields_rejected(self):
        self.ledger.append(sample())
        alter_local_db(self.path,record=lambda x:x.update(approved_original_bug_closure=True))
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_RECEIPT_SCHEMA_CHANGED"):
            self.ledger.read_and_verify()

    def test_rehashed_local_row_identity_mismatch_rejected(self):
        self.ledger.append(sample())
        alter_local_db(self.path,table_change=lambda con:
            con.execute("UPDATE experiments SET finding_id='Y-02' WHERE sequence=1"))
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_ROW_IDENTITY_MISMATCH"):
            self.ledger.read_and_verify()

    def test_rehashed_missing_record_field_rejected(self):
        self.ledger.append(sample())
        alter_local_db(self.path,record=lambda x:x.pop("frozen_input_sha256"))
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_RECEIPT_SCHEMA_CHANGED"):
            self.ledger.read_and_verify()

    def test_rehashed_semantically_invalid_bools_rejected(self):
        self.ledger.append(sample())
        alter_local_db(self.path,record=lambda x:x.update(
            repaired_counterexample_rejected="yes"))
        with self.assertRaisesRegex(ValueError,"invalid repaired_counterexample_rejected"):
            self.ledger.read_and_verify()

    def test_append_fails_before_writing_into_corrupted_chain(self):
        self.ledger.append(sample())
        alter_local_db(self.path,record=lambda x:x.update(verdict="DEFECT_STILL_REPRODUCED"))
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_VERDICT_NOT_DERIVED"):
            self.ledger.append(sample(finding="Y-02",name="new"))
        con=sqlite3.connect(self.path)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM experiments").fetchone()[0],1)
        finally:
            con.close()

    def test_sequence_gap_after_bypassed_delete_rejected(self):
        self.ledger.append(sample())
        self.ledger.append(sample(finding="Y-02",name="next"))
        alter_local_db(self.path,table_change=lambda con:
            con.execute("DELETE FROM experiments WHERE sequence=1"))
        with self.assertRaisesRegex(ValueError,"M40_EXPERIMENT_SEQUENCE_GAP_OR_DELETION"):
            self.ledger.read_and_verify()

    def test_missing_source_ledger_refuses_to_create_database(self):
        missing=self.root/"never-created.sqlite3"
        with self.assertRaisesRegex(ValueError,"M40_LOCAL_EXPERIMENT_LEDGER_MISSING"):
            m40.audit(ledger_path=missing)
        self.assertFalse(missing.exists())

    def test_arbitrary_unknown_finding_id_not_promoted(self):
        self.ledger.append(sample(finding="INVENTED",name="extra"))
        with self.assertRaisesRegex(ValueError,"M40_UNREGISTERED_FINDING_ADDED_TO_LEDGER"):
            m40.audit(ledger_path=self.path)

    def test_register_mutation_fails_closed_even_when_counts_still_match(self):
        original=json.loads(m40.BOOK.read_text())
        original["entries"][0]["remediation"]="VERIFIED_FIXED"
        forged=self.root/"register.json"
        forged.write_text(json.dumps(original),encoding="utf-8")
        with patch.object(m40,"BOOK",forged):
            with self.assertRaisesRegex(ValueError,"M40_FROZEN_HISTORICAL_FINDING_REGISTER_CHANGED"):
                m40.audit(ledger_path=self.path)

    def test_invalid_document_cannot_claim_real_external_authority(self):
        report=m40.audit(ledger_path=self.path)
        self.assertEqual(report["real_customer_pilot_invoices_seen"],0)
        self.assertEqual(report["original_counterexamples_independently_reproduced_in_this_audit"],0)
        self.assertFalse(report["real_customer_recovery_or_fee_established"])
        self.assertEqual(report["release_status"],
                         "BLOCKED_PENDING_INDEPENDENT_ORIGINAL_DEFECT_REPRODUCTION")

    def test_html_is_escaped_and_discloses_unverified_26(self):
        report=m40.audit(ledger_path=self.path)
        bad=deepcopy(report)
        bad["historical_findings"][0]["root_cause_cluster"]="<script>alert(1)</script>"
        html=m40.render_html(bad)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("26 open / 0 closed",html)
        self.assertIn("repair claims",html.lower())

    def test_cli_validates_before_writing(self):
        self.ledger.append(sample())
        output=self.root/"out"
        with patch("sys.argv",["m40","--ledger",str(self.path),"--out",str(output)]):
            m40.main()
        saved=json.loads((output/"historical_finding_disposition.json").read_text())
        self.assertEqual(saved["original_historical_findings_open"],26)
        self.assertTrue((output/"historical_finding_disposition.html").is_file())
        missing=self.root/"missing.sqlite3"
        another=self.root/"no-output"
        with patch("sys.argv",["m40","--ledger",str(missing),"--out",str(another)]):
            with self.assertRaisesRegex(ValueError,"M40_LOCAL_EXPERIMENT_LEDGER_MISSING"):
                m40.main()
        self.assertFalse(another.exists())


if __name__=="__main__":
    unittest.main()
