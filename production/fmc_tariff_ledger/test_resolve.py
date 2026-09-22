import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler
import resolve


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "ledger.sqlite"
        self.conn = crawler.init_db(self.db)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """INSERT INTO entities(entity_class, organization_no, legal_name, trade_name, active)
               VALUES ('vocc', '999999', 'EXAMPLE OCEAN LINE', '', 1)"""
        )
        self.entity_id = self.conn.execute("SELECT id FROM entities").fetchone()[0]
        self.conn.execute(
            """INSERT INTO tariff_locations(
                 entity_id, canonical_url, directory_url, directory_snapshot_sha256,
                 first_seen_at, last_seen_at
               ) VALUES (?, 'https://carrier.test/tariff', 'https://fmc.test', 'x', 'now', 'now')""",
            (self.entity_id,),
        )
        self.loc_id = self.conn.execute("SELECT id FROM tariff_locations").fetchone()[0]
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.td.cleanup()

    def add_term(
        self,
        *,
        effective_from=None,
        effective_to=None,
        source_version=None,
        sha="a" * 64,
        rule_type="demurrage",
        amount="100",
        currency="USD",
    ):
        self.conn.execute(
            """INSERT INTO snapshots(
                 tariff_location_id, requested_url, final_url, fetched_at, http_status,
                 content_type, byte_count, sha256, blob_relpath, parser_status,
                 source_version, effective_from, effective_to
               ) VALUES (?, ?, ?, '2026-09-22T00:00:00Z', 200, 'text/html', 10,
                         ?, 'blobs/x', 'parsed:html:entity_scoped', ?, ?, ?)""",
            (
                self.loc_id,
                f"https://carrier.test/{sha[:8]}-{source_version or 'none'}",
                f"https://carrier.test/{sha[:8]}-{source_version or 'none'}",
                sha,
                source_version,
                effective_from,
                effective_to,
            ),
        )
        snap = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """INSERT INTO terms(
                 snapshot_id, entity_class, organization_no, legal_name, rule_type,
                 term_kind, amount_value, currency, unit, effective_from, effective_to,
                 source_version, evidence_locator, evidence_excerpt, confidence,
                 parser_version, created_at
               ) VALUES (?, 'vocc', '999999', 'EXAMPLE OCEAN LINE', ?, 'money',
                         ?, ?, 'per day', ?, ?, ?, 'rule:21', 'Demurrage charge', 0.95,
                         'test', 'now')""",
            (
                snap,
                rule_type,
                amount,
                currency,
                effective_from,
                effective_to,
                source_version,
            ),
        )
        self.conn.commit()

    def test_missing_entity(self):
        result = resolve.resolve_rule(
            self.conn, "000000", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "NO_ENTITY")

    def test_undated_only_does_not_resolve(self):
        self.add_term()
        result = resolve.resolve_rule(
            self.conn, "999999", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "UNDATED_ONLY")
        self.assertEqual(len(result["candidates"]), 1)

    def test_latest_effective_start_wins(self):
        self.add_term(
            effective_from="2025-01-01",
            source_version="2025-A",
            amount="100",
            sha="a" * 64,
        )
        self.add_term(
            effective_from="2026-04-01",
            source_version="2026-B",
            amount="175",
            sha="b" * 64,
        )
        result = resolve.resolve_rule(
            self.conn, "999999", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["selected_effective_from"], "2026-04-01")
        self.assertEqual({c["amount_value"] for c in result["candidates"]}, {"175"})

    def test_same_version_mirror_hashes_with_same_semantics_resolve(self):
        self.add_term(
            effective_from="2026-04-01",
            source_version="REV-A",
            amount="125",
            sha="a" * 64,
        )
        self.add_term(
            effective_from="2026-04-01",
            source_version="REV-A",
            amount="125",
            sha="b" * 64,
        )
        result = resolve.resolve_rule(
            self.conn, "999999", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "RESOLVED")
        self.assertTrue(result["mirror_hashes_semantically_identical"])
        self.assertIsNone(result["authority_conflict_reason"])
        self.assertEqual(len(result["source_hashes"]), 2)

    def test_same_version_divergent_hash_content_abstains(self):
        self.add_term(
            effective_from="2026-04-01",
            source_version="REV-A",
            amount="100",
            sha="a" * 64,
        )
        self.add_term(
            effective_from="2026-04-01",
            source_version="REV-A",
            amount="175",
            sha="b" * 64,
        )
        result = resolve.resolve_rule(
            self.conn, "999999", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "AMBIGUOUS_AUTHORITY")
        self.assertFalse(result["mirror_hashes_semantically_identical"])
        self.assertEqual(
            result["authority_conflict_reason"],
            "SAME_VERSION_DIVERGENT_CONTENT",
        )

    def test_competing_same_date_versions_abstain(self):
        self.add_term(
            effective_from="2026-04-01",
            source_version="REV-A",
            amount="100",
            sha="a" * 64,
        )
        self.add_term(
            effective_from="2026-04-01",
            source_version="REV-B",
            amount="175",
            sha="b" * 64,
        )
        result = resolve.resolve_rule(
            self.conn, "999999", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "AMBIGUOUS_AUTHORITY")
        self.assertEqual(set(result["authority_versions"]), {"REV-A", "REV-B"})

    def test_expired_rule_is_not_selected(self):
        self.add_term(
            effective_from="2025-01-01",
            effective_to="2025-12-31",
            source_version="OLD",
        )
        result = resolve.resolve_rule(
            self.conn, "999999", "2026-06-01", "demurrage"
        )
        self.assertEqual(result["status"], "NO_EFFECTIVE_RULE")


if __name__ == "__main__":
    unittest.main()
