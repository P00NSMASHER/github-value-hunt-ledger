import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cli import main
from recoveryworks import CaseState
from recoveryworks.io import run_scan_payload
from recoveryworks.storage import load_ledger


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
            ledger_path = Path(tmp) / "ledger.json"
            src.write_text(json.dumps(payload()), encoding="utf-8")
            self.assertEqual(main([
                "scan", str(src), "--output", str(dst),
                "--ledger-output", str(ledger_path),
            ]), 0)
            result = json.loads(dst.read_text(encoding="utf-8"))
            self.assertEqual(result["portfolio"]["totals"]["potential_cents"], 8000)
            ledger = load_ledger(ledger_path)
            self.assertEqual(ledger.rollup()["totals"]["cases"], 2)
            self.assertTrue(ledger.verify_event_chain())

    def test_cli_persists_review_authorization_and_recovery_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "scan.json"
            ledger_path = Path(tmp) / "ledger.json"
            result_path = Path(tmp) / "result.json"
            src.write_text(json.dumps(payload()), encoding="utf-8")
            main([
                "scan", str(src), "--output", str(result_path),
                "--ledger-output", str(ledger_path),
            ])
            finding_id = load_ledger(ledger_path).records()[0].finding.finding_id

            self.assertEqual(main([
                "approve", str(ledger_path), finding_id,
                "--reviewer", "reviewer-1", "--note", "verified source and arithmetic",
            ]), 0)
            self.assertEqual(main([
                "authorize", str(ledger_path), finding_id,
                "--authorization-id", "customer-auth-1",
            ]), 0)
            self.assertTrue(
                __import__("recoveryworks.packets", fromlist=["submission_ready"])
                .submission_ready(
                    __import__("recoveryworks.packets", fromlist=["build_recovery_packet"])
                    .build_recovery_packet(load_ledger(ledger_path).get(finding_id))
                )
            )
            self.assertEqual(main(["mark-claimed", str(ledger_path), finding_id]), 0)
            self.assertEqual(main([
                "recover", str(ledger_path), finding_id,
                "--recovered-cents", "1000", "--fee-cents", "200",
            ]), 0)

            ledger = load_ledger(ledger_path)
            record = ledger.get(finding_id)
            self.assertIs(record.case_state, CaseState.RECOVERED)
            self.assertEqual(record.recovered_cents, 1000)
            self.assertEqual(record.fee_cents, 200)
            self.assertTrue(ledger.verify_event_chain())


if __name__ == "__main__":
    unittest.main()
