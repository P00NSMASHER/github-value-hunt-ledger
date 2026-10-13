import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from ledger_workload_parameters import LIMITS,MAX_RETENTION_DAYS,bounded_integer,reviewed_parameters

class BoundLedgerWorkflowTest(unittest.TestCase):
    def test_existing_exact_run_markers(self):
        for lane,filename,name,expected in [
            ("tic","tic_mrf_ledger","max_indexes",60),
            ("urdb","urdb_ledger","history_limit",100)]:
            r=reviewed_parameters(lane=lane,event="push",requested="1",retention="90",
                   run_now=ROOT/"production"/filename/"RUN_NOW")
            self.assertEqual(r,{name:expected,"retention_days":90})

    def test_manual_bounds_and_bad_values(self):
        for lane,(key,cap) in LIMITS.items():
            r=reviewed_parameters(lane=lane,event="workflow_dispatch",requested=str(cap),
                   retention="90",run_now=ROOT/"missing")
            self.assertEqual(r[key],cap)
        for key,cap in [*LIMITS.values(),("retention_days",MAX_RETENTION_DAYS)]:
            for bad in ["","0","01","-1","+1","1 "," 1","1.0","1e6","0xFF",
                        "1;echo hi","1\n2","$((999))",str(cap+1),"999999"]:
                with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):
                    bounded_integer(bad,label=key,maximum=cap)

    def test_unapproved_events_and_duplicate_markers_rejected(self):
        for event in ["schedule","pull_request","workflow_run","repository_dispatch"]:
            with self.subTest(event=event),self.assertRaises(ValueError):
                reviewed_parameters(lane="tic",event=event,requested="25",retention="90",
                                    run_now=ROOT/"production/tic_mrf_ledger/RUN_NOW")
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/"RUN_NOW"
            for body in ["","max_indexes=20\nmax_indexes=30\n","max_indexes=1e7\n"]:
                f.write_text(body,encoding="utf-8")
                with self.subTest(body=body),self.assertRaises(ValueError):
                    reviewed_parameters(lane="tic",event="push",requested="1",retention="90",run_now=f)

    def test_all_release_lanes_preserved(self):
        full=(ROOT/".github/workflows/repository-release-gate.yml").read_text()
        self.assertIn("name: Repository Release Gate",full)
        for lane in ["ai-business-os","freight","recoveryworks","technology-intelligence"]:
            self.assertIn("  "+lane+":",full)
        self.assertIn("release-gate:",full)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}",full)
        for filename in ["tic-mrf-ledger.yml","urdb-ledger.yml"]:
            source=(ROOT/".github/workflows"/filename).read_text()
            self.assertIn("needs: admission",source)
            self.assertIn("Refusing stale or branch-selected ledger source.",source)
            self.assertIn("ledger_workload_parameters.py",source)
            self.assertIn("steps.parameters.outputs.retention_days",source)

if __name__=="__main__": unittest.main()
