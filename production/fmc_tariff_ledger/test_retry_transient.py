import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import crawler
import retry_transient


class FakeResponse:
    def __init__(self, url, status_code=200, content_type="text/html"):
        self.url = url
        self.status_code = status_code
        self.headers = {"content-type": content_type}


class RetryTransientTests(unittest.TestCase):
    def _seed_location(self, conn, *, org="123456", url="https://carrier.example/tariff"):
        conn.execute(
            """INSERT INTO entities(
                 entity_class, organization_no, legal_name, trade_name, active
               ) VALUES ('vocc', ?, 'ACME CARRIER LLC', '', 1)""",
            (org,),
        )
        entity_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO tariff_locations(
                 entity_id, canonical_url, directory_url,
                 directory_snapshot_sha256, first_seen_at, last_seen_at
               ) VALUES (?, ?, 'https://fmc.test', 'd', 'now', 'now')""",
            (entity_id, url),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def test_collect_targets_excludes_auth_404_and_shared_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "ledger.sqlite"
            conn = crawler.init_db(db)
            loc_id = self._seed_location(conn)

            errors = [
                ("https://carrier.example/retry-503", "fetch", "HTTPError",
                 "503 Server Error: Service Unavailable"),
                ("https://carrier.example/auth", "fetch", "HTTPError",
                 "403 Client Error: Forbidden"),
                ("https://carrier.example/missing", "fetch", "HTTPError",
                 "404 Client Error: Not Found"),
                ("https://carrier.example/login", "publisher_access",
                 "AuthenticationRequired", "login required"),
                ("https://carrier.example/publisher", "publisher_adapter",
                 "EntityTariffNotResolved", "unresolved publisher"),
            ]
            for url, stage, error_type, detail in errors:
                conn.execute(
                    """INSERT INTO crawl_errors(
                         tariff_location_id, url, occurred_at, stage, error_type, detail
                       ) VALUES (?, ?, 'now', ?, ?, ?)""",
                    (loc_id, url, stage, error_type, detail),
                )
            conn.commit()

            targets = retry_transient.collect_targets(conn)
            conn.close()

            self.assertEqual(len(targets), 1)
            self.assertEqual(
                targets[0]["url"],
                "https://carrier.example/retry-503",
            )
            self.assertEqual(targets[0]["reasons"], {"http:503"})

    def test_collect_targets_skips_historic_failure_when_success_exists(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "ledger.sqlite"
            conn = crawler.init_db(db)
            loc_id = self._seed_location(conn)
            url = "https://carrier.example/recovered"
            conn.execute(
                """INSERT INTO crawl_errors(
                     tariff_location_id, url, occurred_at, stage, error_type, detail
                   ) VALUES (?, ?, 'now', 'fetch', 'ConnectTimeout', 'timeout')""",
                (loc_id, url),
            )
            conn.execute(
                """INSERT INTO snapshots(
                     tariff_location_id, requested_url, final_url, fetched_at,
                     http_status, content_type, byte_count, sha256, blob_relpath,
                     parser_status
                   ) VALUES (?, ?, ?, 'now', 200, 'text/html', 10, ?, 'blobs/x',
                             'parsed:html')""",
                (loc_id, url, url, "a" * 64),
            )
            conn.commit()

            self.assertEqual(retry_transient.collect_targets(conn), [])
            conn.close()

    def test_retry_one_direct_source_preserves_hash_and_generates_terms(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = crawler.EntitySource(
                entity_class="vocc",
                organization_no="123456",
                legal_name="ACME CARRIER LLC",
                trade_name="",
                active=True,
                tariff_url="https://carrier.example/tariff",
                directory_url="https://fmc.test",
                directory_sha256="d" * 64,
            )
            target = {
                "source": src,
                "url": "https://carrier.example/tariff",
                "reasons": {"http:503"},
                "error_ids": [1],
            }
            raw = b"""
            <html><body>
            Tariff No. ACME-1 Effective June 1, 2026.
            RULE 21 DEMURRAGE
            Demurrage is USD 125 per day.
            </body></html>
            """
            response = FakeResponse("https://carrier.example/tariff")

            with mock.patch.object(
                retry_transient.v2,
                "fetch_bytes_cached",
                return_value=(raw, response),
            ):
                result = retry_transient.retry_one(
                    target,
                    root,
                    timeout=5,
                    max_bytes=100000,
                )

            self.assertEqual(result["retry_status"], "RECOVERED")
            self.assertEqual(
                result["parser_version"],
                retry_transient.PARSER_VERSION,
            )
            self.assertEqual(len(result["snapshots"]), 1)
            self.assertEqual(
                result["snapshots"][0]["sha256"],
                crawler.sha256_bytes(raw),
            )
            self.assertTrue(
                any(
                    term.rule_type == "demurrage"
                    and term.term_kind == "money"
                    and term.amount_value == "125"
                    for _, term in result["terms"]
                )
            )
            blob = root / result["snapshots"][0]["blob_relpath"]
            self.assertEqual(blob.read_bytes(), raw)

    def test_retry_one_shared_generic_source_never_generates_terms(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = crawler.EntitySource(
                entity_class="oti",
                organization_no="222222",
                legal_name="DISTINCTIVE CARRIER LLC",
                trade_name="",
                active=True,
                tariff_url="https://pctb.com",
                directory_url="https://fmc.test",
                directory_sha256="d" * 64,
            )
            target = {
                "source": src,
                "url": "https://pctb.com",
                "reasons": {"http:503"},
                "error_ids": [1],
            }
            raw = b"""
            <html><body>
            Generic shared tariff publishing portal.
            Demurrage is USD 125 per day.
            </body></html>
            """
            response = FakeResponse("https://pctb.com")

            with mock.patch.object(
                retry_transient.v2,
                "fetch_bytes_cached",
                return_value=(raw, response),
            ):
                result = retry_transient.retry_one(
                    target,
                    root,
                    timeout=5,
                    max_bytes=100000,
                )

            self.assertEqual(result["retry_status"], "RECOVERED")
            self.assertEqual(result["terms"], [])
            self.assertIn(
                "publisher_retry_unresolved",
                result["snapshots"][0]["parser_status"],
            )


if __name__ == "__main__":
    unittest.main()
