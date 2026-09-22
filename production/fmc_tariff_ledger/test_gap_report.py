import tempfile
import unittest
from pathlib import Path

import crawler
import gap_report


class GapReportTests(unittest.TestCase):
    def test_unresolved_shared_publisher_ranks_ahead_of_clean_domain(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "ledger.sqlite"
            conn = crawler.init_db(db)

            def seed(org, legal, url, unresolved=False):
                conn.execute(
                    """INSERT INTO entities(
                         entity_class, organization_no, legal_name, trade_name, active
                       ) VALUES ('oti', ?, ?, '', 1)""",
                    (org, legal),
                )
                entity_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute(
                    """INSERT INTO tariff_locations(
                         entity_id, canonical_url, directory_url,
                         directory_snapshot_sha256, first_seen_at, last_seen_at
                       ) VALUES (?, ?, 'https://fmc.test', 'x', 'now', 'now')""",
                    (entity_id, url),
                )
                loc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                if unresolved:
                    conn.execute(
                        """INSERT INTO crawl_errors(
                             tariff_location_id, url, occurred_at, stage, error_type, detail
                           ) VALUES (?, ?, 'now', 'publisher_adapter',
                                     'EntityTariffNotResolved', 'unresolved')""",
                        (loc_id, url),
                    )

            seed("111111", "UNRESOLVED OCEAN LLC", "https://pctb.com", True)
            seed("222222", "CLEAN OCEAN LLC", "https://carrier.example/tariff", False)
            conn.commit()
            conn.close()

            report = gap_report.build_report(db)
            self.assertEqual(report["publisher_priority_queue"][0]["host"], "pctb.com")
            self.assertEqual(
                report["publisher_priority_queue"][0]["unresolved_entities"],
                1,
            )


if __name__ == "__main__":
    unittest.main()
