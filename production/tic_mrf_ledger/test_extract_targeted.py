import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import catalog
import extract_targeted


SAMPLE = {
    "reporting_entity_name": "Example Health",
    "reporting_entity_type": "health insurance issuer",
    "last_updated_on": "2026-09-01",
    "version": "2.0.0",
    "provider_references": [
        {
            "provider_group_id": 1,
            "network_name": ["Network A"],
            "provider_groups": [
                {
                    "npi": [1111111111, 2222222222],
                    "tin": {
                        "type": "ein",
                        "value": "11-1111111",
                        "business_name": "Target Medical Group",
                    },
                }
            ],
        },
        {
            "provider_group_id": 2,
            "network_name": ["Network B"],
            "provider_groups": [
                {
                    "npi": [9999999999],
                    "tin": {
                        "type": "ein",
                        "value": "99-9999999",
                        "business_name": "Other Group",
                    },
                }
            ],
        },
    ],
    "in_network": [
        {
            "negotiation_arrangement": "ffs",
            "name": "Office visit",
            "billing_code_type": "CPT",
            "billing_code_type_version": "2026",
            "billing_code": "99214",
            "description": "Office visit",
            "negotiated_rates": [
                {
                    "provider_references": [1, 2],
                    "negotiated_prices": [
                        {
                            "setting": "outpatient",
                            "negotiated_type": "negotiated",
                            "negotiated_rate": 210.25,
                            "expiration_date": "2027-01-01",
                            "service_code": ["11"],
                            "billing_class": "professional",
                            "billing_code_modifier": ["25"],
                        }
                    ],
                }
            ],
        },
        {
            "negotiation_arrangement": "ffs",
            "name": "Unrelated",
            "billing_code_type": "CPT",
            "billing_code_type_version": "2026",
            "billing_code": "99999",
            "description": "Should be skipped",
            "negotiated_rates": [
                {
                    "provider_references": [1],
                    "negotiated_prices": [
                        {
                            "setting": "outpatient",
                            "negotiated_type": "negotiated",
                            "negotiated_rate": 99999.0,
                            "expiration_date": "2027-01-01",
                            "billing_class": "professional",
                            "service_code": ["11"],
                        }
                    ],
                }
            ],
        },
    ],
}


class TargetedExtractorTests(unittest.TestCase):
    def test_targeted_code_and_npi_keep_only_matching_provider_group(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "ledger.sqlite"
            conn = catalog.init_db(db)
            rate_file = root / "rates.json"
            rate_file.write_text(json.dumps(SAMPLE), encoding="utf-8")
            raw = rate_file.read_bytes()
            meta = {
                "final_url": "https://payer.test/rates.json",
                "http_status": 200,
                "content_type": "application/json",
                "content_length": len(raw),
                "etag": '"fixture"',
                "last_modified": "Tue, 01 Sep 2026 00:00:00 GMT",
                "sha256": catalog.sha256_bytes(raw),
            }
            with patch.object(
                extract_targeted,
                "download_rate_file",
                return_value=(rate_file, meta),
            ):
                stats = extract_targeted.extract_one(
                    conn,
                    rate_url="https://payer.test/rates.json",
                    billing_codes={"99214"},
                    target_npis={"1111111111"},
                    timeout=1,
                    max_bytes=1_000_000,
                )

            self.assertEqual(stats["target_items"], 1)
            self.assertEqual(stats["candidate_rate_rows"], 2)
            self.assertEqual(stats["matched_provider_group_ids"], 1)
            self.assertEqual(stats["kept_rate_rows"], 1)
            row = conn.execute(
                """SELECT billing_code,provider_group_id,negotiated_rate,setting,
                          expiration_date,billing_class
                   FROM rate_rows"""
            ).fetchone()
            self.assertEqual(
                tuple(row),
                ("99214", 1, "210.25", "outpatient", "2027-01-01", "professional"),
            )
            provider = conn.execute(
                """SELECT npi,tin_type,tin_value,business_name
                   FROM provider_groups"""
            ).fetchone()
            self.assertEqual(
                tuple(provider),
                ("1111111111", "ein", "11-1111111", "Target Medical Group"),
            )
            conn.close()

    def test_no_matching_npi_keeps_no_rates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            conn = catalog.init_db(root / "ledger.sqlite")
            rate_file = root / "rates.json"
            rate_file.write_text(json.dumps(SAMPLE), encoding="utf-8")
            raw = rate_file.read_bytes()
            meta = {
                "final_url": "https://payer.test/rates.json",
                "http_status": 200,
                "content_type": "application/json",
                "content_length": len(raw),
                "etag": None,
                "last_modified": None,
                "sha256": catalog.sha256_bytes(raw),
            }
            with patch.object(
                extract_targeted,
                "download_rate_file",
                return_value=(rate_file, meta),
            ):
                stats = extract_targeted.extract_one(
                    conn,
                    rate_url="https://payer.test/rates.json",
                    billing_codes={"99214"},
                    target_npis={"3333333333"},
                    timeout=1,
                    max_bytes=1_000_000,
                )
            self.assertEqual(stats["kept_rate_rows"], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM rate_rows").fetchone()[0], 0)
            conn.close()


if __name__ == "__main__":
    unittest.main()
