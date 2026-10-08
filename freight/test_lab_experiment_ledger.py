import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from freight.lab_experiment_ledger import Experiment,ExperimentLedger,verdict

H=lambda t:hashlib.sha256(t.encode()).hexdigest()

def sample(**changes):
    return Experiment(**(dict(experiment_id="LAB-P0-03-REPRO-01",finding_id="LAB-P0-03",
           source_head_sha=H("old-source"),candidate_head_sha=H("candidate-source"),
           frozen_input_sha256=H("frozen-fixture"),independent_test_sha256=H("independent-test"),
           original_counterexample_reproduced=True,repaired_counterexample_rejected=True,
           known_good_control_passed=True,measured_runtime_ms=6,
           execution_scope="SYNTHETIC_OFFLINE") | changes))

class ExperimentLedgerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.db=Path(tmp.name)/"evidence.sqlite3"
        self.ledger=ExperimentLedger(self.db)
    def test_immutable_receipt_and_replay(self):
        made,sha=self.ledger.append(sample())
        self.assertTrue(made)
        again,second=self.ledger.append(sample())
        self.assertFalse(again)
        self.assertEqual(sha,second)
        self.assertEqual(self.ledger.read_and_verify()[0]["verdict"],
                         "REPAIR_DEMONSTRATED_IN_STATED_TEST_SCOPE_ONLY")
    def test_conflicting_same_experiment_id(self):
        self.ledger.append(sample())
        with self.assertRaisesRegex(ValueError,"replay conflicts"):
            self.ledger.append(sample(measured_runtime_ms=900))
    def test_failed_candidate_remains_visible(self):
        run=sample(repaired_counterexample_rejected=False)
        self.assertEqual(verdict(run),"DEFECT_STILL_REPRODUCED")
        self.ledger.append(run)
        self.assertEqual(self.ledger.read_and_verify()[0]["verdict"],"DEFECT_STILL_REPRODUCED")
    def test_unreproduced_original_not_marked_repaired(self):
        self.assertEqual(verdict(sample(original_counterexample_reproduced=False)),"INCONCLUSIVE")
    def test_append_only_db_triggers(self):
        self.ledger.append(sample())
        con=sqlite3.connect(self.db)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM experiments")
        finally:
            con.rollback();con.close()
    def test_invalid_hash_rejected(self):
        with self.assertRaises(ValueError):
            self.ledger.append(sample(frozen_input_sha256="broken"))
    def test_successful_second_append_proves_chain(self):
        self.ledger.append(sample())
        self.ledger.append(sample(experiment_id="Y-02-REPRO-02",finding_id="Y-02"))
        self.assertEqual(len(self.ledger.read_and_verify()),2)

if __name__=="__main__":unittest.main()
