import sqlite3
import tempfile
import unittest
from pathlib import Path

import catalog
import coverage_debt


class CoverageDebtTests(unittest.TestCase):
    def test_report_distinguishes_sources_with_and_without_files(self):
        with tempfile.TemporaryDirectory() as td:
            conn = catalog.init_db(Path(td) / "ledger.sqlite")
            s1 = catalog.Source("s1", "Payer One", "direct", "https://one.test")
            s2 = catalog.Source("s2", "Payer Two", "master_list_candidate", "https://two.test")
            catalog.persist_source(conn, s1)
            catalog.persist_source(conn, s2)
            catalog.insert_mrf_file(
                conn, s1, "https://one.test/rates_in-network-rates.json.gz",
                "in_network", snapshot_id=None, manifest_sha="abc"
            )
            catalog.record_error(
                conn, "s2", "https://two.test", "source_discovery",
                "no resolver", error_type="Unresolved"
            )
            conn.commit()

            report = coverage_debt.build_report(conn)
            self.assertEqual(report["sources"]["total"], 2)
            self.assertEqual(report["sources"]["with_files"], 1)
            self.assertEqual(report["sources"]["without_files"], 1)
            self.assertEqual(report["files"]["in_network_unique_urls"], 1)
            self.assertEqual(
                report["unresolved_host_priority"][0]["host"],
                "two.test",
            )
            self.assertFalse(
                report["authority_boundary"]["public_tic_is_controlling_provider_contract"]
            )
            conn.close()


if __name__ == "__main__":
    unittest.main()
