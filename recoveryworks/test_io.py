import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cli import main
from recoveryworks.io import run_scan_payload


def payload():
    rule = {
        "rule_id": "rule-1",
        "source_hash": "rulehash",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "verified_controlling": True,
        "source_locator": "source://rule#1",
    }
    return {
        "schema": 1,
        "scan_id": "scan-360-1",
        "client_id": "client-1",
        "branches": ["ap", "utility"],
        "selection_rule": "all supplied records for June 2026",
        "sources": [
            {
                "source_id": "ap-export",
                "branch": "ap",
                "source_hash": "aphash",
                "locator": "file://ap.csv",
                "kind": "payment_export",
            },
            {
                "source_id": "utility-export",
                "branch": "utility",
                "source_hash": "uthash",
                "locator": "file://utility.csv",
                "kind": "bill_export",
            },
        ],
        "observations": [
            {
                "branch": "ap",
                "client_id": "client-1",
                "counterparty_id": "vendor",
                "reference": "pay-1",
                "currency": "USD",
                "occurred_on": "2026-06-01",
                "expected_cents": 10000,
                "actual_cents": 15000,
                "rule": rule,
                "evidence": [{
                    "evidence_id": "pay-1",
                    "source_hash": "aphash",
                    "locator": "file://ap.csv#pay-1",
                    "kind": "payment",
                    "verified": True,
                }],
                "reason": "DUPLICATE_PAYMENT",
                "confidence_basis": "deterministic payment reconciliation",
            },
            {
                "branch": "utility",
                "client_id": "client-1",
                "counterparty_id": "utility",
                "reference": "bill-1",
                "currency": "USD",
                "occurred_on": "2026-06-15",
                "expected_cents": 20000,
                "actual_cents": 23000,
                "rule": rule,
                "evidence": [{
                    "evidence_id": "bill-1",
                    "source_hash": "uthash",
                    "locator": "file://utility.csv#bill-1",
                    "kind": "bill",
                    "verified": True,
                }],
                "reason": "TARIFF_VARIANCE",
                "confidence_basis": "deterministic tariff calculation",
            },
        ],
    }


class RecoveryIOTests(unittest.TestCase):
    def test_run_scan_payload_builds_cross_branch_portfolio(self):
        result = run_scan_payload(payload())
        self.assertEqual(result["portfolio"]["totals"]["cases"], 2)
        self.assertEqual(result["portfolio"]["totals"]["potential_cents"], 8000)
        self.assertEqual({item["branch"] for item in result["findings"]}, {"ap", "utility"})
        self.assertTrue(all(not item["submission_ready"] for item in result["findings"]))
        self.assertEqual(len(result["manifest_hash"]), 64)
        self.assertEqual(len(result["batch_hash"]), 64)

    def test_scan_payload_rejects_cross_client_observation(self):
        bad = payload()
        bad["observations"][0]["client_id"] = "other-client"
        with self.assertRaises(ValueError):
            run_scan_payload(bad)

    def test_cli_writes_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "scan.json"
            dst = Path(tmp) / "result.json"
            src.write_text(json.dumps(payload()), encoding="utf-8")
            self.assertEqual(main(["scan", str(src), "--output", str(dst)]), 0)
            result = json.loads(dst.read_text(encoding="utf-8"))
            self.assertEqual(result["portfolio"]["totals"]["potential_cents"], 8000)


if __name__ == "__main__":
    unittest.main()
