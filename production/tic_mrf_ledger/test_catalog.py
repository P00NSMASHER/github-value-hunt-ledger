import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import catalog


def fake_response(url: str, content_type: str = "application/json"):
    return SimpleNamespace(
        url=url,
        status_code=200,
        headers={
            "content-type": content_type,
            "etag": '"fixture"',
            "last-modified": "Mon, 01 Jan 2024 00:00:00 GMT",
        },
    )


class TiCCatalogTests(unittest.TestCase):
    def test_classify_file(self):
        self.assertEqual(catalog.classify_file("https://x/a_in-network-rates.json.gz"), "in_network")
        self.assertEqual(catalog.classify_file("https://x/a_allowed-amounts.json"), "allowed_amounts")
        self.assertEqual(catalog.classify_file("https://x/2026-09-01_payer_index.json"), "index")

    def test_historical_sqlite_catalog_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_db = root / "seed.db"
            c = sqlite3.connect(source_db)
            c.execute("CREATE TABLE in_network_files(url PRIMARY KEY, size)")
            c.execute("CREATE TABLE index_files(url PRIMARY KEY, size)")
            c.execute("INSERT INTO in_network_files VALUES (?,?)", ("https://payer.test/rates.json.gz", 1234))
            c.execute("INSERT INTO index_files VALUES (?,?)", ("https://payer.test/index.json", 456))
            c.commit()
            c.close()
            raw = source_db.read_bytes()

            conn = catalog.init_db(root / "ledger.sqlite")
            source = catalog.Source(
                "hist", "Historical Payer", "github_sqlite",
                "https://github.test/catalog.db", True
            )
            with patch.object(catalog, "fetch_bytes", return_value=(
                raw, fake_response(source.source_url, "application/octet-stream")
            )):
                stats = catalog.import_historical_sqlite(
                    conn, root, source, timeout=1, max_bytes=10_000_000
                )
            self.assertEqual(stats["files"], 2)
            rows = conn.execute(
                "SELECT file_type,file_url,content_length,historical FROM mrf_files ORDER BY file_type"
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(r[3] == 1 for r in rows))
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM source_snapshots").fetchone()[0], 1
            )
            conn.close()

    def test_index_maps_plans_to_in_network_and_allowed_amount_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            conn = catalog.init_db(root / "ledger.sqlite")
            conn.row_factory = sqlite3.Row
            source = catalog.Source(
                "live", "Example Payer", "html_index_links",
                "https://payer.test/"
            )
            source_id = catalog.persist_source(conn, source)
            index_id = catalog.insert_mrf_file(
                conn, source, "https://payer.test/index.json", "index",
                snapshot_id=None, manifest_sha="landing-hash"
            )
            index_row = conn.execute(
                "SELECT * FROM mrf_files WHERE id=?", (index_id,)
            ).fetchone()
            payload = {
                "reporting_entity_name": "Example Health",
                "reporting_entity_type": "health insurance issuer",
                "last_updated_on": "2026-09-01",
                "version": "2.0.0",
                "reporting_structure": [{
                    "reporting_plans": [
                        {
                            "plan_name": "Plan A",
                            "plan_id_type": "hios",
                            "plan_id": "11111",
                            "plan_market_type": "individual",
                            "issuer_name": "Example Health",
                        },
                        {
                            "plan_name": "Plan B",
                            "plan_id_type": "ein",
                            "plan_id": "12-3456789",
                            "plan_market_type": "group",
                            "issuer_name": "Example Health",
                            "plan_sponsor_name": "Employer B",
                        },
                    ],
                    "in_network_files": [{
                        "description": "rates",
                        "location": "https://payer.test/rates.json.gz",
                    }],
                    "allowed_amount_file": {
                        "description": "allowed",
                        "location": "https://payer.test/allowed.json.gz",
                    },
                }],
            }
            tmp = root / "index.json"
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            meta = {
                "final_url": "https://payer.test/index.json",
                "http_status": 200,
                "content_type": "application/json",
                "etag": '"idx"',
                "last_modified": "Mon, 01 Sep 2026 00:00:00 GMT",
                "content_length": tmp.stat().st_size,
                "sha256": catalog.sha256_bytes(tmp.read_bytes()),
            }
            with patch.object(catalog, "fetch_to_temp", return_value=(tmp, meta)):
                stats = catalog.parse_index_file(
                    conn, root, source, source_id, index_row,
                    timeout=1, max_index_bytes=1_000_000,
                    snapshot_max_bytes=1_000_000,
                )

            self.assertEqual(stats["files"], 2)
            self.assertEqual(stats["plans"], 2)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM file_plan_links").fetchone()[0], 4
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM mrf_files WHERE file_type='allowed_amounts'"
                ).fetchone()[0],
                1,
            )
            child = conn.execute(
                """SELECT reporting_entity_name,schema_version,last_updated_on
                   FROM mrf_files WHERE file_type='in_network'"""
            ).fetchone()
            self.assertEqual(tuple(child), ("Example Health", "2.0.0", "2026-09-01"))
            index_meta = conn.execute(
                """SELECT reporting_entity_name,reporting_entity_type,schema_version,last_updated_on
                   FROM mrf_files WHERE id=?""", (index_id,)
            ).fetchone()
            self.assertEqual(
                tuple(index_meta),
                ("Example Health", "health insurance issuer", "2.0.0", "2026-09-01"),
            )
            plans = conn.execute(
                "SELECT plan_name,issuer_name,plan_sponsor_name FROM plans ORDER BY plan_name"
            ).fetchall()
            self.assertEqual(plans[0][0], "Plan A")
            self.assertEqual(plans[1][2], "Employer B")
            conn.close()

    def test_aetna_unresolved_file_path_is_explicit_not_invented(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            conn = catalog.init_db(root / "ledger.sqlite")
            source = catalog.Source(
                "aetna-test", "Aetna/CVS", "aetna_metadata",
                "https://aetna.test/latest_metadata.json",
                brand_code="AETNACVS",
            )
            raw = json.dumps({
                "files": [{
                    "fileSchema": "IN_NETWORK_RATES",
                    "fileName": "rates-001.json.gz",
                    "size": 999,
                }]
            }).encode()
            with patch.object(catalog, "fetch_bytes", return_value=(
                raw, fake_response(source.source_url)
            )):
                catalog.discover_aetna_metadata(
                    conn, root, source, timeout=1, max_bytes=1_000_000
                )
            row = conn.execute(
                "SELECT file_url,parse_status FROM mrf_files"
            ).fetchone()
            self.assertTrue(row[0].startswith("mrf+unresolved://aetna/"))
            self.assertEqual(row[1], "unresolved_path_from_metadata")
            conn.close()

    def test_github_master_list_adds_source_candidates_and_direct_indexes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            conn = catalog.init_db(root / "ledger.sqlite")
            source = catalog.Source(
                "master", "Registry", "github_master_list",
                "https://github.test/master.md"
            )
            raw = (
                "| Payer | Type | Public MRF TOC / landing URL | Notes |\n"
                "|---|---|---|---|\n"
                "| Example Health | commercial | https://payer.test/2026-09-01_example_index.json | current |\n"
                "| Landing Only | tpa | https://payer.test/transparency | landing |\n"
            ).encode()
            with patch.object(catalog, "fetch_bytes", return_value=(
                raw, fake_response(source.source_url, "text/markdown")
            )):
                stats = catalog.discover_github_master_list(
                    conn, root, source, timeout=1, max_bytes=1_000_000
                )
            self.assertEqual(stats["source_candidates"], 2)
            self.assertEqual(stats["files"], 1)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0], 3
            )
            row = conn.execute(
                "SELECT file_type,file_url FROM mrf_files"
            ).fetchone()
            self.assertEqual(row[0], "index")
            self.assertIn("example_index.json", row[1])
            conn.close()

    def test_html_index_landing_is_not_misclassified_as_toc(self):
        self.assertEqual(
            catalog.classify_file("https://payer.test/index.html"),
            "unknown",
        )
        self.assertEqual(
            catalog.classify_file("https://payer.test/File/Visit/Index"),
            "unknown",
        )
        self.assertEqual(
            catalog.classify_file("https://payer.test/2026-09-01_payer_index.json"),
            "index",
        )

    def test_monthly_template_generates_current_and_previous_tocs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            conn = catalog.init_db(root / "ledger.sqlite")
            source = catalog.Source(
                "monthly",
                "Regional Payer",
                "monthly_toc_templates",
                "https://payer.test/mrf/",
                notes=json.dumps({
                    "base_url": "https://payer.test/mrf/",
                    "file_templates": ["{year}/{month_start}_payer_index.json"],
                    "month_offsets": [0, -1],
                }),
            )
            with patch.object(catalog, "month_start") as ms:
                ms.side_effect = [
                    (2026, 9, "2026-09-01", "20260901"),
                    (2026, 8, "2026-08-01", "20260801"),
                ]
                stats = catalog.discover_monthly_toc_templates(
                    conn, root, source, timeout=1, max_bytes=1000
                )
            self.assertEqual(stats["files"], 2)
            rows = [
                r[0] for r in conn.execute(
                    "SELECT file_url FROM mrf_files ORDER BY file_url"
                ).fetchall()
            ]
            self.assertEqual(rows, [
                "https://payer.test/mrf/2026/2026-08-01_payer_index.json",
                "https://payer.test/mrf/2026/2026-09-01_payer_index.json",
            ])
            conn.close()


if __name__ == "__main__":
    unittest.main()
