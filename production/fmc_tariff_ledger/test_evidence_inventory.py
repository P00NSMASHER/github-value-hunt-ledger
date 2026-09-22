import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler
import evidence_inventory


class EvidenceInventoryTests(unittest.TestCase):
    def _seed(self, db_path: Path, *, digest: str, size: int, url: str):
        conn = crawler.init_db(db_path)
        conn.execute(
            """INSERT INTO entities(
                 entity_class, organization_no, legal_name, trade_name, active
               ) VALUES ('vocc', ?, 'TEST CARRIER', '', 1)""",
            (db_path.parent.name[-1] * 6,),
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
        conn.execute(
            """INSERT INTO snapshots(
                 tariff_location_id, requested_url, final_url, fetched_at,
                 http_status, content_type, byte_count, sha256, blob_relpath,
                 parser_status
               ) VALUES (?, ?, ?, '2026-09-22T00:00:00+00:00',
                         200, 'application/pdf', ?, ?, ?, 'parsed:pdf')""",
            (
                loc_id,
                url,
                url,
                size,
                digest,
                f"blobs/sha256/{digest[:2]}/{digest}",
            ),
        )
        conn.commit()
        conn.close()

    def test_cross_shard_duplicate_hash_is_one_inventory_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shard0 = root / "fmc-metadata-shard-0"
            shard1 = root / "fmc-metadata-shard-1"
            shard0.mkdir()
            shard1.mkdir()
            digest = "a" * 64
            self._seed(
                shard0 / "ledger.sqlite",
                digest=digest,
                size=1000,
                url="https://carrier0.test/tariff.pdf",
            )
            self._seed(
                shard1 / "ledger.sqlite",
                digest=digest,
                size=1000,
                url="https://carrier1.test/tariff.pdf",
            )

            result = evidence_inventory.build_inventory(
                root,
                source_run_id="123",
            )
            self.assertEqual(result["metadata_shards_found"], 2)
            self.assertEqual(result["unique_blob_count"], 1)
            self.assertEqual(result["unique_blob_bytes"], 1000)
            self.assertEqual(result["shard_unique_blob_bytes_sum"], 2000)
            self.assertEqual(result["cross_shard_duplicate_bytes"], 1000)
            self.assertEqual(result["cross_shard_duplicate_pct"], 50.0)
            blob = result["blobs"][0]
            self.assertEqual(blob["source_shards"], [0, 1])
            self.assertEqual(
                blob["source_artifacts"],
                ["fmc-shard-0", "fmc-shard-1"],
            )
            self.assertEqual(blob["reference_count"], 2)
            self.assertEqual(result["source_workflow_run_id"], "123")


if __name__ == "__main__":
    unittest.main()
