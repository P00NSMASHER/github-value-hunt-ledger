import sqlite3
import tempfile
import unittest
from pathlib import Path

import ingest
import resolve


class URDBResolveTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "ledger.sqlite"
        self.conn = ingest.init_db(self.db)
        rid = ingest.insert_release(
            self.conn,
            release_key="fixture",
            commit_sha=None,
            commit_date=None,
            message="fixture",
            metadata={"tariff_count": 3},
            metadata_sha="x",
        )
        rows = [
            ("A1","Utility A","101","GS","Commercial","Bundled","2025-01-01","2025-12-31",None,"A2","Ended"),
            ("A2","Utility A","101","GS","Commercial","Bundled","2026-01-01",None,"A1",None,"Active"),
            ("B1","Utility A","101","GS","Commercial","Bundled","2026-01-01",None,None,None,"Active"),
        ]
        for label, utility, eiaid, name, sector, svc, start, end, prev, nxt, status in rows:
            self.conn.execute(
                """INSERT INTO current_tariffs(
                     label,utility,eiaid,name,sector,servicetype,startdate,enddate,
                     supersedes,superseded_by,status,release_id,source_file_sha256,row_fingerprint
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (label,utility,eiaid,name,sector,svc,start,end,prev,nxt,status,rid,"sha",label),
            )
            root = "A1" if label.startswith("A") else label
            depth = {"A1":0,"A2":1,"B1":0}[label]
            self.conn.execute(
                """INSERT INTO tariff_history_edges(
                     label,supersedes,superseded_by,chain_root,chain_depth,cycle_detected
                   ) VALUES(?,?,?,?,?,0)""",
                (label,prev,nxt,root,depth),
            )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.td.cleanup()

    def test_exact_label_resolves_by_date(self):
        result = resolve.resolve(
            self.conn, service_date="2025-06-01", label="A1"
        )
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["selected"]["label"], "A1")

    def test_exact_label_outside_date_fails_closed(self):
        result = resolve.resolve(
            self.conn, service_date="2026-06-01", label="A1"
        )
        self.assertEqual(result["status"], "OUTSIDE_EFFECTIVE_INTERVAL")

    def test_overlapping_utility_name_is_ambiguous(self):
        result = resolve.resolve(
            self.conn,
            service_date="2026-06-01",
            utility="Utility A",
            name="GS",
        )
        self.assertEqual(result["status"], "AMBIGUOUS_TARIFF")
        self.assertEqual(result["candidate_count"], 2)


if __name__ == "__main__":
    unittest.main()
