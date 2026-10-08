"""Real-code local experiment campaign; proof receipts do not claim old findings fixed."""
from __future__ import annotations
import copy
import tempfile
import unittest
from pathlib import Path

from freight.lab_phase4_experiments import (
    conduct_experiments, load_findings, select_experiments, verify_experiment_outcome,
)
from freight.lab_phase4_director import execute_all_labs
from freight.test_lab_phase3_real_chain import funded_store,rating_fixture,scenario
from freight.test_lab_assurance import assertions_and_fees,verifier


class ExperimentDirectorTests(unittest.TestCase):
    def test_priority_budget_and_duplicate_cluster_suppression(self):
        found=load_findings()
        original=copy.deepcopy(found)
        selected=select_experiments(found,max_experiments=5)
        self.assertEqual(len(selected),5)
        self.assertEqual(len({r.cluster for r in selected}),5)
        self.assertEqual(found,original)
        self.assertTrue(all(x.score>0 for x in selected))
        excluded=select_experiments(found,max_experiments=3,excluded_ids=frozenset({selected[0].finding_id}))
        self.assertNotEqual(selected[0].finding_id,excluded[0].finding_id)

    def test_invalid_budgets_fail(self):
        for n in [0,27,True,-1]:
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    select_experiments(load_findings(),max_experiments=n)

    def test_actual_experiment_execution_writes_inconclusive_chain(self):
        with tempfile.TemporaryDirectory() as d:
            record,book=rating_fixture()
            store=funded_store(d)
            assertions,fees=assertions_and_fees()
            outcome=conduct_experiments(register=load_findings(),
                ledger_path=Path(d)/"experiment_ledger.sqlite3",max_experiments=3,
                record=record,authority_book=book,store=store,
                assertions=assertions,fee_events=fees,verifier=verifier(),contingency=scenario())
            self.assertEqual(len(outcome["recorded_experiments"]),3)
            self.assertEqual(outcome["ledger_entry_count"],3)
            self.assertEqual(outcome["executed_labs"],list(range(1,15)))
            self.assertEqual(outcome["historical_findings_closed"],0)
            self.assertEqual(outcome["real_customer_recovery_cents"],0)
            self.assertTrue(all(r["verdict"]=="INCONCLUSIVE" for r in outcome["recorded_experiments"]))

    def test_report_mutations_never_become_verified(self):
        with tempfile.TemporaryDirectory() as d:
            record,book=rating_fixture()
            store=funded_store(d)
            a,fees=assertions_and_fees()
            receipt=execute_all_labs(record=record,authority_book=book,store=store,
                assertions=a,fee_events=fees,verifier=verifier(),contingency=scenario())
            verify_experiment_outcome(receipt)
            forged=copy.deepcopy(receipt);forged["actual_revenue_cents"]=1
            with self.assertRaises(ValueError):
                verify_experiment_outcome(forged)
            forged=copy.deepcopy(receipt);forged["lab_runs"][0]["status"]="EXECUTED_WITHOUT_PROOF"
            forged["lab_runs"][0]["proof"]={}
            with self.assertRaises(ValueError):
                verify_experiment_outcome(forged)
            forged=copy.deepcopy(receipt);forged["lab_runs"][4]["negative_probe"]="NOT_RUN"
            with self.assertRaises(ValueError):
                verify_experiment_outcome(forged)

if __name__=="__main__":
    unittest.main()
