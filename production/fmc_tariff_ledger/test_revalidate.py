import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler
import revalidate


class RevalidateTests(unittest.TestCase):
    def _seed(self, root: Path, text: str, url: str, org: str, legal: str):
        db = root / "ledger.sqlite"
        conn = crawler.init_db(db)
        conn.execute(
            """INSERT INTO entities(entity_class, organization_no, legal_name, trade_name, active)
               VALUES ('oti', ?, ?, '', 1)""",
            (org, legal),
        )
        entity_id = conn.execute("SELECT id FROM entities").fetchone()[0]
        conn.execute(
            """INSERT INTO tariff_locations(
                 entity_id, canonical_url, directory_url,
                 directory_snapshot_sha256, first_seen_at, last_seen_at
               ) VALUES (?, ?, 'https://fmc.test', 'x', 'now', 'now')""",
            (entity_id, url),
        )
        loc_id = conn.execute("SELECT id FROM tariff_locations").fetchone()[0]
        raw = text.encode()
        digest = crawler.sha256_bytes(raw)
        rel = crawler.write_blob(root / "blobs", digest, raw)
        conn.execute(
            """INSERT INTO snapshots(
                 tariff_location_id, requested_url, final_url, fetched_at,
                 http_status, content_type, byte_count, sha256, blob_relpath,
                 parser_status
               ) VALUES (?, ?, ?, 'now', 200, 'text/html', ?, ?, ?, 'parsed:html:entity_scoped')""",
            (loc_id, url, url, len(raw), digest, rel),
        )
        snap_id = conn.execute("SELECT id FROM snapshots").fetchone()[0]
        conn.execute(
            """INSERT INTO terms(
                 snapshot_id, entity_class, organization_no, legal_name,
                 rule_type, term_kind, evidence_excerpt, confidence, created_at
               ) VALUES (?, 'oti', ?, ?, 'demurrage', 'money', 'USD 100/day', 0.9, 'now')""",
            (snap_id, org, legal),
        )
        conn.commit()
        conn.close()
        return db

    def test_generic_shared_publisher_terms_are_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = self._seed(
                root,
                "<html><body>Generic PCTB tariff publishing portal. Demurrage USD 100/day.</body></html>",
                "https://pctb.com",
                "123456",
                "ACME OCEAN LLC",
            )
            stats = revalidate.revalidate(db, root)
            self.assertEqual(stats["terms_quarantined_shared_generic"], 1)
            self.assertEqual(stats["remaining_terms"], 0)

    def test_entity_scoped_shared_publisher_terms_survive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = self._seed(
                root,
                "<html><body>FMC Organization 123456 ACME OCEAN tariff. Demurrage USD 100/day.</body></html>",
                "https://pctb.com",
                "123456",
                "ACME OCEAN LLC",
            )
            stats = revalidate.revalidate(db, root)
            self.assertEqual(stats["terms_quarantined_shared_generic"], 0)
            self.assertEqual(stats["remaining_terms"], 1)

    def test_rule_page_pseudo_identifier_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = self._seed(
                root,
                "<html><body>RULE PAGE 4</body></html>",
                "https://direct.example/tariff",
                "333333",
                "DIRECT CARRIER",
            )
            conn = sqlite3.connect(db)
            snap = conn.execute(
                "SELECT id FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO terms(
                     snapshot_id, entity_class, organization_no, legal_name,
                     rule_type, term_kind, evidence_excerpt, confidence,
                     parser_version, created_at
                   ) VALUES (?, 'vocc', '333333', 'DIRECT CARRIER',
                             'rule:PAGE', 'rule_text', 'RULE PAGE 4',
                             0.9, 'legacy', 'now')""",
                (snap,),
            )
            conn.commit()
            conn.close()

            report = revalidate.revalidate(db, root)
            self.assertGreaterEqual(report["bogus_rule_terms_removed"], 1)

            conn = sqlite3.connect(db)
            remaining = conn.execute(
                "SELECT COUNT(*) FROM terms WHERE lower(rule_type)='rule:page'"
            ).fetchone()[0]
            conn.close()
            self.assertEqual(remaining, 0)

    def test_shared_duplicate_blob_text_is_parsed_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            html = (
                "<html><body>Generic shared tariff portal. "
                "Demurrage USD 100/day.</body></html>"
            )
            db = self._seed(
                root,
                html,
                "https://pctb.com",
                "111111",
                "FIRST OCEAN LLC",
            )
            conn = sqlite3.connect(db)
            first = conn.execute(
                """SELECT sha256, blob_relpath, content_type
                   FROM snapshots LIMIT 1"""
            ).fetchone()
            conn.execute(
                """INSERT INTO entities(
                     entity_class, organization_no, legal_name, trade_name, active
                   ) VALUES ('oti', '222222', 'SECOND OCEAN LLC', '', 1)"""
            )
            entity_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """INSERT INTO tariff_locations(
                     entity_id, canonical_url, directory_url,
                     directory_snapshot_sha256, first_seen_at, last_seen_at
                   ) VALUES (?, 'https://pctb.com', 'https://fmc.test',
                             'x', 'now', 'now')""",
                (entity_id,),
            )
            loc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """INSERT INTO snapshots(
                     tariff_location_id, requested_url, final_url, fetched_at,
                     http_status, content_type, byte_count, sha256, blob_relpath,
                     parser_status
                   ) VALUES (?, 'https://pctb.com', 'https://pctb.com', 'now',
                             200, ?, 1, ?, ?, 'parsed:html:entity_scoped')""",
                (loc_id, first[2], first[0], first[1]),
            )
            snap_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """INSERT INTO terms(
                     snapshot_id, entity_class, organization_no, legal_name,
                     rule_type, term_kind, evidence_excerpt, confidence, created_at
                   ) VALUES (?, 'oti', '222222', 'SECOND OCEAN LLC',
                             'demurrage', 'money', 'USD 100/day', 0.9, 'now')""",
                (snap_id,),
            )
            conn.commit()
            conn.close()

            stats = revalidate.revalidate(db, root)
            self.assertEqual(stats["unique_blob_text_parses"], 1)
            self.assertGreaterEqual(stats["text_cache_hits"], 1)
            self.assertEqual(stats["terms_quarantined_shared_generic"], 2)
            self.assertEqual(stats["remaining_terms"], 0)


if __name__ == "__main__":
    unittest.main()
