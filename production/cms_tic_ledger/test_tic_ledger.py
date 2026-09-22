import gzip
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq

import inventory
import rate_ingest
from common import init_db
from source_registry import _parse_markdown_table


class TiCLedgerTests(unittest.TestCase):
    def test_master_registry_parser(self):
        text = """
| Payer | Type | Public MRF TOC / landing URL | Notes |
|---|---|---|---|
| Example Health | national | https://example.com/tic | curated source |
| Missing | regional | - | no URL |
"""
        rows = _parse_markdown_table(text, "a" * 64)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].payer_name, "Example Health")
        self.assertEqual(rows[0].root_url, "https://example.com/tic")

    def test_file_kind(self):
        self.assertEqual(
            inventory.file_kind("https://x.test/2026_payer_in-network-rates.json.gz"),
            "in_network",
        )
        self.assertEqual(
            inventory.file_kind("https://x.test/allowed-amounts.json"),
            "allowed_amounts",
        )
        self.assertEqual(
            inventory.file_kind("https://x.test/2026_payer_index.json"),
            "table_of_contents",
        )

    def test_toc_preserves_plan_to_file_relationship(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "catalog.sqlite"
            conn = init_db(db)
            conn.execute(
                """INSERT INTO source_roots
                   (payer_name,payer_type,root_url,notes,source_tier,active)
                   VALUES ('Example','national','https://example.test','','test',1)"""
            )
            source_id = conn.execute("SELECT id FROM source_roots").fetchone()[0]
            payload = {
                "reporting_entity_name": "Example Health",
                "reporting_entity_type": "health insurance issuer",
                "last_updated_on": "2026-09-01",
                "version": "2.0.0",
                "reporting_structure": [{
                    "reporting_plans": [{
                        "plan_name": "Gold",
                        "issuer_name": "Example Health",
                        "plan_id_type": "hios",
                        "plan_id": "12345",
                        "plan_market_type": "individual",
                    }],
                    "in_network_files": [{
                        "description": "medical",
                        "location": "https://example.test/medical_in-network-rates.json.gz",
                    }],
                }],
            }
            result = inventory.parse_toc(
                conn,
                source_id=source_id,
                index_url="https://example.test/index.json",
                index_sha="b" * 64,
                payload=payload,
            )
            self.assertTrue(result["is_toc"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM files").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM file_plans").fetchone()[0], 1)
            conn.close()

    def test_streaming_rate_normalization(self):
        fixture = {
            "reporting_entity_name": "Example",
            "last_updated_on": "2026-09-01",
            "version": "2.0.0",
            "provider_references": [{
                "provider_group_id": 7,
                "network_name": ["Example PPO"],
                "provider_groups": [{
                    "npi": [1902960099],
                    "tin": {
                        "type": "ein",
                        "value": "11-2700051",
                        "business_name": "Example Medical",
                    },
                }],
            }],
            "in_network": [{
                "negotiation_arrangement": "ffs",
                "name": "Office visit",
                "billing_code_type": "CPT",
                "billing_code_type_version": "2026",
                "billing_code": "99213",
                "description": "Office visit",
                "negotiated_rates": [{
                    "provider_references": [7],
                    "negotiated_prices": [{
                        "negotiated_type": "negotiated",
                        "negotiated_rate": 139.39,
                        "expiration_date": "2026-12-31",
                        "billing_class": "professional",
                        "setting": "outpatient",
                        "service_code": ["11"],
                        "billing_code_modifier": ["25"],
                    }],
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "fixture.json.gz"
            with gzip.open(src, "wt", encoding="utf-8") as fh:
                json.dump(fixture, fh)

            writers = {
                name: rate_ingest.RollingWriter(root / "normalized", name, rows_per_part=100, batch_size=2)
                for name in rate_ingest.SCHEMAS
            }
            matching, pstats = rate_ingest.parse_providers(
                src,
                source_file_id="file1",
                source_sha="c" * 64,
                writers=writers,
                npi_filter={"1902960099"},
                tin_filter=set(),
            )
            rstats = rate_ingest.parse_rates(
                src,
                source_file_id="file1",
                source_sha="c" * 64,
                writers=writers,
                billing_codes={"99213"},
                provider_filter_active=True,
                matching_groups=matching,
                max_items=0,
            )
            for writer in writers.values():
                writer.close()

            self.assertEqual(matching, {"7"})
            self.assertEqual(pstats["provider_groups"], 1)
            self.assertEqual(rstats["prices_written"], 1)
            prices = pq.read_table(root / "normalized" / "prices" / "part-00000.parquet")
            self.assertEqual(prices.num_rows, 1)
            self.assertEqual(prices.column("negotiated_rate")[0].as_py(), "139.39")

    def test_provider_filter_excludes_other_groups(self):
        fixture = {
            "provider_references": [
                {"provider_group_id": 1, "provider_groups": [{"npi": [1111111111], "tin": {"type": "ein", "value": "111111111"}}]},
                {"provider_group_id": 2, "provider_groups": [{"npi": [2222222222], "tin": {"type": "ein", "value": "222222222"}}]},
            ],
            "in_network": [{
                "billing_code": "A1",
                "billing_code_type": "HCPCS",
                "billing_code_type_version": "2026",
                "negotiation_arrangement": "ffs",
                "negotiated_rates": [
                    {"provider_references": [1], "negotiated_prices": [{"negotiated_type": "negotiated", "negotiated_rate": 10, "expiration_date": "9999-12-31", "billing_class": "professional", "setting": "outpatient"}]},
                    {"provider_references": [2], "negotiated_prices": [{"negotiated_type": "negotiated", "negotiated_rate": 20, "expiration_date": "9999-12-31", "billing_class": "professional", "setting": "outpatient"}]},
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"f.json"
            src.write_text(json.dumps(fixture))
            writers={name:rate_ingest.RollingWriter(root/"n",name,100,2) for name in rate_ingest.SCHEMAS}
            matching,_=rate_ingest.parse_providers(
                src,source_file_id="f",source_sha="d"*64,writers=writers,
                npi_filter={"2222222222"},tin_filter=set()
            )
            stats=rate_ingest.parse_rates(
                src,source_file_id="f",source_sha="d"*64,writers=writers,
                billing_codes={"A1"},provider_filter_active=True,matching_groups=matching,max_items=0
            )
            for w in writers.values(): w.close()
            self.assertEqual(stats["prices_written"],1)


if __name__ == "__main__":
    unittest.main()
