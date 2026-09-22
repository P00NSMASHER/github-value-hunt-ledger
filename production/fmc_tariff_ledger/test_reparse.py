import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler
import reparse


class OfflineReparseTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.db = self.root / "ledger.sqlite"
        self.conn = crawler.init_db(self.db)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.td.cleanup()

    def seed_snapshot(self, *, url, org, legal, text, existing_rule=None):
        self.conn.execute(
            """INSERT INTO entities(entity_class, organization_no, legal_name, trade_name, active)
               VALUES ('oti', ?, ?, '', 1)""",
            (org, legal),
        )
        eid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """INSERT INTO tariff_locations(
                 entity_id, canonical_url, directory_url, directory_snapshot_sha256,
                 first_seen_at, last_seen_at
               ) VALUES (?, ?, 'https://fmc.test', 'x', 'now', 'now')""",
            (eid, url),
        )
        loc = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        raw = text.encode()
        digest = crawler.sha256_bytes(raw)
        rel = crawler.write_blob(self.root / "blobs", digest, raw)
        self.conn.execute(
            """INSERT INTO snapshots(
                 tariff_location_id, requested_url, final_url, fetched_at,
                 http_status, content_type, byte_count, sha256, blob_relpath,
                 parser_status
               ) VALUES (?, ?, ?, 'now', 200, 'text/html', ?, ?, ?, 'parsed:html')""",
            (loc, url, url, len(raw), digest, rel),
        )
        snap = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if existing_rule:
            self.conn.execute(
                """INSERT INTO terms(
                     snapshot_id, entity_class, organization_no, legal_name,
                     rule_type, term_kind, evidence_excerpt, confidence,
                     parser_version, created_at
                   ) VALUES (?, 'oti', ?, ?, ?, 'rule_text', 'legacy', 0.8,
                             'legacy', 'now')""",
                (snap, org, legal, existing_rule),
            )
        self.conn.commit()
        return snap

    def test_reparse_adds_compact_date_version_and_new_rule_families(self):
        snap = self.seed_snapshot(
            url="https://carrier.example/tariff",
            org="123456",
            legal="ACME OCEAN LLC",
            text="""
            <html><body>
            Tariff No. 123456-001 Amendment No. 7
            Effective Date: 5MAY2022
            Rates, charges, and rules applicable are those in effect on the date
            cargo is received by the carrier.
            Terminal services charges may be passed through at cost without markup.
            </body></html>
            """,
        )
        stats = reparse.reparse(self.db, self.root)
        self.assertEqual(stats["snapshots_reparsed"], 1)
        row = self.conn.execute(
            "SELECT effective_from, source_version FROM snapshots WHERE id=?",
            (snap,),
        ).fetchone()
        self.assertEqual(row["effective_from"], "2022-05-05")
        self.assertEqual(row["source_version"], "123456-001|AMD:7")
        rules = {
            r[0]
            for r in self.conn.execute(
                "SELECT rule_type FROM terms WHERE snapshot_id=?", (snap,)
            )
        }
        self.assertIn("applicability_date", rules)
        self.assertIn("pass_through", rules)

    def test_reparse_replaces_legacy_terms(self):
        snap = self.seed_snapshot(
            url="https://carrier2.example/tariff",
            org="654321",
            legal="SECOND OCEAN LLC",
            text="<html><body>Effective 1SEP2021 DEMURRAGE USD 125 per day</body></html>",
            existing_rule="rule:no",
        )
        stats = reparse.reparse(self.db, self.root)
        self.assertGreaterEqual(stats["terms_deleted_for_reparse"], 1)
        rules = {
            r[0]
            for r in self.conn.execute(
                "SELECT rule_type FROM terms WHERE snapshot_id=?", (snap,)
            )
        }
        self.assertNotIn("rule:no", rules)
        self.assertIn("demurrage", rules)

    def test_shared_generic_snapshot_is_not_reintroduced(self):
        snap = self.seed_snapshot(
            url="https://pctb.com",
            org="222222",
            legal="THIRD OCEAN LLC",
            text="<html><body>Generic PCTB portal. Demurrage USD 100/day.</body></html>",
            existing_rule="demurrage",
        )
        stats = reparse.reparse(self.db, self.root)
        self.assertEqual(stats["snapshots_skipped_shared_generic"], 1)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM terms WHERE snapshot_id=?", (snap,)
        ).fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
