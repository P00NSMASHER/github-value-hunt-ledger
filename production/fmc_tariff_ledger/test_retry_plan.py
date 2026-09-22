import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler
import retry_plan


class RetryPlanTests(unittest.TestCase):
    def test_failure_classification_is_bounded(self):
        self.assertEqual(
            retry_plan.classify(
                "fetch",
                "HTTPError",
                "503 Server Error: Service Unavailable",
            )[0],
            "SAFE_NETWORK_RETRY",
        )
        self.assertEqual(
            retry_plan.classify(
                "fetch",
                "HTTPError",
                "403 Client Error: Forbidden",
            )[0],
            "ACCESS_REVIEW",
        )
        self.assertEqual(
            retry_plan.classify(
                "fetch",
                "HTTPError",
                "404 Client Error: Not Found",
            )[0],
            "STALE_LINK",
        )
        self.assertEqual(
            retry_plan.classify("fetch", "ConnectTimeout", "timeout")[0],
            "SAFE_NETWORK_RETRY",
        )
        self.assertEqual(
            retry_plan.classify("parse", "DependencyError", "pdf")[0],
            "OFFLINE_REPARSE",
        )
        self.assertEqual(
            retry_plan.classify(
                "publisher_access",
                "AuthenticationRequired",
                "login",
            )[0],
            "MANUAL_PUBLISHER_RESOLUTION",
        )

    def test_plan_deduplicates_retry_urls_and_preserves_entities(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "ledger.sqlite"
            conn = crawler.init_db(db)

            for org, name in (("111111", "ONE LLC"), ("222222", "TWO LLC")):
                conn.execute(
                    """INSERT INTO entities(
                         entity_class, organization_no, legal_name, trade_name, active
                       ) VALUES ('oti', ?, ?, '', 1)""",
                    (org, name),
                )
                entity_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute(
                    """INSERT INTO tariff_locations(
                         entity_id, canonical_url, directory_url,
                         directory_snapshot_sha256, first_seen_at, last_seen_at
                       ) VALUES (?, ?, 'https://fmc.test', 'x', 'now', 'now')""",
                    (entity_id, f"https://publisher.test/{org}"),
                )
                loc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute(
                    """INSERT INTO crawl_errors(
                         tariff_location_id, url, occurred_at, stage, error_type, detail
                       ) VALUES (?, 'https://publisher.test/shared', 'now',
                                 'fetch', 'HTTPError',
                                 '503 Server Error: Service Unavailable')""",
                    (loc_id,),
                )
            conn.commit()

            plan = retry_plan.build_plan(conn)
            conn.close()

            self.assertEqual(plan["safe_network_retry_unique_urls"], 1)
            item = plan["safe_network_retry"][0]
            self.assertEqual(item["affected_entity_count"], 2)
            self.assertEqual(item["error_rows"], 2)
            self.assertEqual(
                item["reasons"],
                {"http:503": 2},
            )


if __name__ == "__main__":
    unittest.main()
