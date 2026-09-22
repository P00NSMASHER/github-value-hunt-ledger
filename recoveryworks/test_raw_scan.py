import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cli import main
from recoveryworks.raw_scan import run_raw_scan_payload
from recoveryworks.storage import load_ledger


def all_six_payload():
    verified_rule = {
        "rule_id": "construction-rule-1",
        "source_hash": "construction-rule-hash",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "verified_controlling": True,
        "source_locator": "source://construction-contract#7.4",
    }
    return {
        "schema": 1,
        "scan_id": "raw-360-all-six",
        "client_id": "client-1",
        "selection_rule": "all supplied synthetic records",
        "ap": {
            "invoices": [{
                "vendor_id": "vendor-1", "invoice_id": "inv-1",
                "invoice_date": "2026-05-01", "amount_cents": 10000,
                "source_hash": "ap-invoice-hash", "locator": "source://ap/inv-1",
                "verified": True,
            }],
            "payments": [
                {
                    "vendor_id": "vendor-1", "invoice_id": "inv-1",
                    "payment_id": "p1", "payment_date": "2026-05-10",
                    "amount_cents": 7500, "source_hash": "ap-p1-hash",
                    "locator": "source://ap/p1", "verified": True,
                },
                {
                    "vendor_id": "vendor-1", "invoice_id": "inv-1",
                    "payment_id": "p2", "payment_date": "2026-05-15",
                    "amount_cents": 7500, "source_hash": "ap-p2-hash",
                    "locator": "source://ap/p2", "verified": True,
                },
            ],
        },
        "utility": [{
            "utility_id": "utility-1",
            "tariff": {
                "tariff_id": "t1", "effective_from": "2026-01-01",
                "effective_to": None, "fixed_charge_cents": 1000,
                "energy_tiers": [{"up_to_kwh": None, "rate_cents_per_kwh": "10"}],
                "demand_rate_cents_per_kw": "0",
                "source_hash": "utility-tariff-hash",
                "locator": "source://utility/tariff", "verified": True,
            },
            "bills": [{
                "bill_id": "bill-1", "bill_date": "2026-06-01",
                "usage_kwh": "100", "demand_kw": "0", "billed_cents": 2500,
                "source_hash": "utility-bill-hash", "locator": "source://utility/bill",
                "verified": True,
            }],
        }],
        "payer": [{
            "payer_id": "payer-1",
            "rates": [{
                "rate_id": "rate-1", "procedure_code": "99214",
                "effective_from": "2026-01-01", "effective_to": None,
                "allowed_cents_per_unit": 10000,
                "source_hash": "payer-rate-hash", "locator": "source://payer/rate",
                "verified": True,
            }],
            "service_lines": [{
                "claim_id": "claim-1", "service_line_id": "1",
                "service_date": "2026-06-01", "procedure_code": "99214",
                "units": 1, "paid_cents": 7500,
                "source_hash": "payer-line-hash", "locator": "source://payer/835",
                "verified": True,
            }],
        }],
        "duty": {
            "customs_counterparty_id": "CBP",
            "rates": [{
                "rate_id": "hts-1", "hts_code": "1234.56.7890",
                "effective_from": "2026-01-01", "effective_to": None,
                "ad_valorem_bps": 500, "specific_cents_per_unit": "0",
                "source_hash": "hts-hash", "locator": "source://hts/1",
                "verified": True,
            }],
            "lines": [{
                "entry_id": "entry-1", "line_id": "1",
                "entry_date": "2026-06-01", "hts_code": "1234.56.7890",
                "customs_value_cents": 100000, "quantity": "0",
                "paid_duty_cents": 6000,
                "source_hash": "entry-hash", "locator": "source://entry/1",
                "verified": True,
            }],
        },
        "construction": [{
            "counterparty_id": "gc-1",
            "require_schedule_impact": True,
            "entitlement": {
                "event_id": "co-7", "event_date": "2026-06-01",
                "entitled_cents": 500000, "paid_cents": 200000,
                "entitlement_type": "delay",
                "rule": verified_rule,
                "evidence": [{
                    "evidence_id": "co-7", "source_hash": "co-hash",
                    "locator": "source://co/7", "kind": "change_order",
                    "verified": True,
                }],
            },
            "schedule_impact": {
                "analysis_id": "cpm-1", "method": "AACE-window-analysis",
                "impact_days": 12, "analysis_hash": "cpm-hash",
                "locator": "source://cpm/1", "baseline_hash": "base-hash",
                "comparison_hash": "update-hash", "verified": True,
            },
        }],
        "freight": {
            "rules": [{
                "business_unit": "bu-1", "customer_id": "cust-1",
                "carrier_id": "carrier-1", "authority_document_id": "contract-1",
                "charge_code": "LIFTGATE", "pricing_model": "FIXED",
                "effective_from": "2026-01-01", "effective_to": "2026-12-31",
                "document_source_hash": "freight-rule-source",
                "verified_controlling_authority": True, "fixed_cents": 10000,
            }],
            "charges": [{
                "business_unit": "bu-1", "invoice_id": "freight-inv-1",
                "shipment_id": "ship-1", "customer_id": "cust-1",
                "carrier_id": "carrier-1", "charge_id": "charge-1",
                "charge_code": "LIFTGATE", "service_date": "2026-06-01",
                "quantity_units": 1, "billed_cents": 15000,
                "source_hash": "freight-charge-source",
            }],
        },
    }


class RawRecoveryScanTests(unittest.TestCase):
    def test_one_raw_scan_runs_all_six_recovery_branches(self):
        result = run_raw_scan_payload(all_six_payload())
        self.assertEqual(
            set(result["branches"]),
            {"ap", "utility", "payer", "duty", "construction", "freight"},
        )
        self.assertEqual(result["portfolio"]["totals"]["cases"], 6)
        self.assertEqual(result["portfolio"]["totals"]["potential_cents"], 314000)
        self.assertEqual(
            {item["branch"] for item in result["findings"]},
            {"ap", "utility", "payer", "duty", "construction", "freight"},
        )
        self.assertTrue(all(not item["submission_ready"] for item in result["findings"]))
        self.assertEqual(len(result["manifest_hash"]), 64)
        self.assertEqual(len(result["batch_hash"]), 64)
        self.assertGreaterEqual(result["source_count"], 13)

    def test_raw_scan_cli_persists_all_six_branch_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "raw.json"
            out = Path(tmp) / "result.json"
            ledger_path = Path(tmp) / "ledger.json"
            src.write_text(json.dumps(all_six_payload()), encoding="utf-8")
            self.assertEqual(main([
                "raw-scan", str(src),
                "--output", str(out),
                "--ledger-output", str(ledger_path),
            ]), 0)
            result = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(result["portfolio"]["totals"]["cases"], 6)
            ledger = load_ledger(ledger_path)
            self.assertEqual(ledger.rollup()["totals"]["cases"], 6)
            self.assertTrue(ledger.verify_event_chain())

    def test_missing_required_construction_schedule_impact_stays_review(self):
        payload = all_six_payload()
        payload["ap"] = None
        payload["utility"] = []
        payload["payer"] = []
        payload["duty"] = None
        payload["freight"] = None
        payload["construction"][0]["schedule_impact"] = None
        result = run_raw_scan_payload(payload)
        self.assertEqual(result["portfolio"]["totals"]["cases"], 1)
        self.assertEqual(result["portfolio"]["totals"]["validated_cents"], 0)
        self.assertEqual(result["findings"][0]["case_state"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
