import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import ingest


class TicIngestTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.db = self.root / "ledger.sqlite"
        self.conn = ingest.init_db(self.db)

    def tearDown(self):
        self.conn.close()
        self.td.cleanup()

    def _blob(self, payload: dict, name: str = "fixture.json.gz"):
        raw_json = json.dumps(payload, separators=(",", ":")).encode()
        raw = gzip.compress(raw_json)
        sha = hashlib.sha256(raw).hexdigest()
        dest, rel = ingest.blob_path(self.root, sha)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        return ingest.BlobResult(
            requested_url=f"https://example.test/{name}",
            final_url=f"https://example.test/{name}",
            fetched_at=ingest.utcnow(),
            status=200,
            content_type="application/gzip",
            byte_count=len(raw),
            sha256=sha,
            blob_relpath=rel,
            etag=None,
            last_modified=None,
        )

    def test_schema_initializes(self):
        tables = {
            r[0]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        self.assertTrue(
            {
                "sources",
                "source_observations",
                "catalog_files",
                "plans",
                "mrf_snapshots",
                "provider_groups",
                "provider_entities",
                "negotiated_rates",
                "rate_provider_groups",
                "allowed_amounts",
                "errors",
            }
            <= tables
        )

    def test_kind_inference(self):
        self.assertEqual(
            ingest.infer_kind("https://x/2026-09_in-network-rates.json.gz"),
            "in-network-rates",
        )
        self.assertEqual(
            ingest.infer_kind("https://x/foo_allowed-amounts.json.gz"),
            "allowed-amounts",
        )
        self.assertEqual(
            ingest.infer_kind("https://x/2026-09_payer_index.json.gz"),
            "index",
        )

    def test_toc_expands_plans_and_files(self):
        cfg = {
            "source_id": "fixture",
            "payer_family": "Fixture Payer",
            "resolver": "direct_index",
            "url": "https://example.test/index.json.gz",
        }
        source_id = ingest.upsert_source(self.conn, cfg)
        payload = {
            "reporting_entity_name": "Fixture Payer LLC",
            "reporting_entity_type": "Health Insurance Issuer",
            "last_updated_on": "2026-09-01",
            "version": "2.0.0",
            "reporting_structure": [
                {
                    "reporting_plans": [
                        {
                            "plan_name": "PPO A",
                            "issuer_name": "Fixture Payer LLC",
                            "plan_id_type": "hios",
                            "plan_id": "12345AA001",
                            "plan_market_type": "individual",
                        }
                    ],
                    "in_network_files": [
                        {
                            "description": "rates",
                            "location": "https://example.test/in-network-rates.json.gz",
                        }
                    ],
                    "allowed_amount_file": {
                        "description": "oon",
                        "location": "https://example.test/allowed-amounts.json.gz",
                    },
                }
            ],
        }
        result = self._blob(payload, "index.json.gz")
        obs = ingest.persist_observation(
            self.conn, source_id, result, parser_status="fetched:test"
        )
        meta = ingest.parse_toc_catalog(
            self.conn,
            root=self.root,
            observation_id=obs,
            result=result,
            payer_family="Fixture Payer",
        )
        self.assertEqual(meta["files"], 2)
        self.assertEqual(meta["plans"], 1)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM catalog_files").fetchone()[0], 2
        )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM file_plan_links").fetchone()[0], 2
        )

    def test_in_network_rate_is_not_duplicated_per_provider_group(self):
        payload = {
            "reporting_entity_name": "Fixture Payer",
            "reporting_entity_type": "issuer",
            "last_updated_on": "2026-09-01",
            "version": "2.0.0",
            "provider_references": [
                {
                    "provider_group_id": 10,
                    "provider_groups": [
                        {
                            "npi": [1111111111, 2222222222],
                            "tin": {
                                "type": "ein",
                                "value": "12-3456789",
                                "business_name": "Example Practice",
                            },
                        }
                    ],
                    "network_name": ["PPO"],
                },
                {
                    "provider_group_id": 11,
                    "provider_groups": [
                        {
                            "npi": [3333333333],
                            "tin": {"type": "npi", "value": "3333333333"},
                        }
                    ],
                    "network_name": ["PPO"],
                },
            ],
            "in_network": [
                {
                    "negotiation_arrangement": "ffs",
                    "name": "Office visit",
                    "billing_code_type": "CPT",
                    "billing_code_type_version": "2026",
                    "billing_code": "99213",
                    "description": "Office visit",
                    "negotiated_rates": [
                        {
                            "provider_references": [10, 11],
                            "negotiated_prices": [
                                {
                                    "negotiated_type": "negotiated",
                                    "negotiated_rate": 101.25,
                                    "expiration_date": "2027-01-01",
                                    "billing_class": "professional",
                                    "setting": "outpatient",
                                    "service_code": ["11"],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = self._blob(payload)
        meta = ingest._read_head_metadata(
            self.root, result.blob_relpath, result.final_url
        )
        snap = ingest.create_snapshot(
            self.conn,
            result=result,
            source_url=None,
            kind="in-network-rates",
            meta=meta,
        )
        pstats = ingest.parse_provider_groups(
            self.conn,
            root=self.root,
            snapshot_id=snap,
            relpath=result.blob_relpath,
            source_url=result.final_url,
        )
        rstats = ingest.normalize_in_network(
            self.conn,
            root=self.root,
            snapshot_id=snap,
            relpath=result.blob_relpath,
            source_url=result.final_url,
            code_filter=None,
        )
        self.assertEqual(pstats["provider_groups"], 2)
        self.assertEqual(rstats["rate_rows"], 1)
        self.assertEqual(rstats["rate_provider_links"], 2)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM negotiated_rates").fetchone()[0], 1
        )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM rate_provider_groups").fetchone()[0], 2
        )

    def test_allowed_amount_retains_tin_and_npi(self):
        payload = {
            "reporting_entity_name": "Fixture Payer",
            "reporting_entity_type": "issuer",
            "last_updated_on": "2026-09-01",
            "version": "2.0.0",
            "out_of_network": [
                {
                    "name": "Office visit",
                    "billing_code_type": "CPT",
                    "billing_code_type_version": "2026",
                    "billing_code": "99213",
                    "description": "Office visit",
                    "allowed_amounts": [
                        {
                            "tin": {"type": "ein", "value": "98-7654321"},
                            "billing_class": "professional",
                            "service_code": ["11"],
                            "payments": [
                                {
                                    "allowed_amount": 88.50,
                                    "providers": [
                                        {
                                            "billed_charge": 150.00,
                                            "npi": [4444444444, 5555555555],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = self._blob(payload, "allowed-amounts.json.gz")
        snap = ingest.create_snapshot(
            self.conn,
            result=result,
            source_url=None,
            kind="allowed-amounts",
            meta=ingest._read_head_metadata(
                self.root, result.blob_relpath, result.final_url
            ),
        )
        stats = ingest.normalize_allowed(
            self.conn,
            root=self.root,
            snapshot_id=snap,
            relpath=result.blob_relpath,
            source_url=result.final_url,
            code_filter=None,
        )
        self.assertEqual(stats["allowed_rows"], 2)
        rows = self.conn.execute(
            "SELECT tin_value,npi,allowed_amount FROM allowed_amounts ORDER BY npi"
        ).fetchall()
        self.assertEqual(rows[0], ("98-7654321", "4444444444", "88.5"))
        self.assertEqual(rows[1], ("98-7654321", "5555555555", "88.5"))

    def test_code_filter_is_fail_closed(self):
        payload = {
            "in_network": [
                {
                    "negotiation_arrangement": "ffs",
                    "name": "A",
                    "billing_code_type": "CPT",
                    "billing_code_type_version": "2026",
                    "billing_code": "99213",
                    "description": "A",
                    "negotiated_rates": [
                        {
                            "provider_references": [1],
                            "negotiated_prices": [
                                {
                                    "negotiated_type": "negotiated",
                                    "negotiated_rate": 50,
                                    "expiration_date": "2027-01-01",
                                    "billing_class": "professional",
                                    "setting": "outpatient",
                                    "service_code": ["11"],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        result = self._blob(payload)
        snap = ingest.create_snapshot(
            self.conn,
            result=result,
            source_url=None,
            kind="in-network-rates",
            meta={},
        )
        stats = ingest.normalize_in_network(
            self.conn,
            root=self.root,
            snapshot_id=snap,
            relpath=result.blob_relpath,
            source_url=result.final_url,
            code_filter={"27447"},
        )
        self.assertEqual(stats["rate_rows"], 0)


if __name__ == "__main__":
    unittest.main()
