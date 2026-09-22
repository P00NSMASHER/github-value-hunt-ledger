import sqlite3
import tempfile
import unittest
from pathlib import Path

import build_recovery_case as cases
import crawler
import shaq_route_crawl


class RecoveryCaseTests(unittest.TestCase):
    def test_candidate_consolidation_uses_max_per_line_not_sum(self):
        base = {
            "invoice_line_id": "BASE",
            "status": "POTENTIAL_BASE_RATE_VARIANCE_REVIEW",
            "potential_review_amount": "200.00",
        }
        pass_rows = [
            {
                "invoice_line_id": "DD-1",
                "status": "POTENTIAL_PASS_THROUGH_MARKUP_REVIEW",
                "potential_markup_delta": "125.00",
            }
        ]
        dd_rows = [
            {
                "invoice_id": "DD-1",
                "status": "POTENTIAL_NO_PAYMENT_OBLIGATION_REVIEW",
                "potential_charge_relief_amount": "1500.00",
            }
        ]
        result = cases.consolidate_candidates(base, pass_rows, dd_rows)
        self.assertEqual(
            result["potential_review_upper_bound_no_double_count"],
            "1700.00",
        )
        dd_line = next(
            row for row in result["lines"] if row["invoice_line_id"] == "DD-1"
        )
        self.assertEqual(dd_line["candidate_upper_bound_no_double_count"], "1500.00")
        self.assertEqual(result["asserted_recovery_total"], "0.00")

    def test_unresolved_base_authority_produces_no_candidate_amount(self):
        envelope = {
            "status": "NOT_READY_FOR_MONEY_ASSERTION",
            "base_rate_authority": {
                "status": "NO_AUTHORITY_READY_CONTRACT_RATE"
            },
        }
        result = cases.base_rate_review(
            envelope,
            {
                "invoice_line_id": "BASE",
                "billed_amount": "6000",
                "quantity": "1",
            },
        )
        self.assertEqual(result["status"], "BASE_RATE_AUTHORITY_UNRESOLVED")
        self.assertEqual(result["potential_review_amount"], "0.00")
        self.assertEqual(result["asserted_recovery"], "0.00")

    def test_resolved_base_variance_is_review_only(self):
        envelope = {
            "status": "AUTHORITY_ENVELOPE_READY",
            "base_rate_authority": {
                "status": "RESOLVED",
                "amount_value": "5000",
                "rate_basis": "per container",
                "contract_candidates": [{"source": "contract"}],
                "benchmark_context": {"status": "AVAILABLE"},
            },
        }
        result = cases.base_rate_review(
            envelope,
            {
                "invoice_line_id": "BASE",
                "billed_amount": "5600",
                "quantity": "1",
            },
        )
        self.assertEqual(result["status"], "POTENTIAL_BASE_RATE_VARIANCE_REVIEW")
        self.assertEqual(result["potential_review_amount"], "600.00")
        self.assertEqual(result["asserted_recovery"], "0.00")

    def test_case_without_contract_authority_keeps_asserted_total_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rates = shaq_route_crawl.init_db(root / "rates.sqlite")
            rates.row_factory = sqlite3.Row
            fmc = crawler.init_db(root / "fmc.sqlite")
            fmc.row_factory = sqlite3.Row

            fmc.execute(
                """INSERT INTO entities(
                     entity_class,organization_no,legal_name,trade_name,active
                   ) VALUES ('vocc','123456','TEST CARRIER','',1)"""
            )
            fmc.commit()

            case = {
                "case_id": "CASE-1",
                "shipment": {
                    "fmc_organization_no": "123456",
                    "shipment_date": "2026-06-01",
                    "origin": "Shanghai",
                    "destination": "Chancay",
                    "container_type": "40HQ",
                    "currency": "USD",
                    "rule_types": [],
                },
                "base_charge": {
                    "invoice_line_id": "BASE",
                    "billed_amount": "6000",
                    "quantity": "1",
                },
            }
            result = cases.assemble_case(rates, fmc, case)
            self.assertEqual(result["asserted_recovery_total"], "0.00")
            self.assertEqual(
                result["base_rate_review"]["status"],
                "BASE_RATE_AUTHORITY_UNRESOLVED",
            )
            rates.close()
            fmc.close()


if __name__ == "__main__":
    unittest.main()
