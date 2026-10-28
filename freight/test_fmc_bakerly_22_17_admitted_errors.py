"""FMC 22-17 decision-level source boundary, not independent invoice labels."""
import copy
import json
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "fixtures" / "fmc_bakerly_22_17_admitted_errors_non_systemic_v0.json"

class FMCBakerlyBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(SOURCE.read_text(encoding="utf-8"))

    @staticmethod
    def contract(row):
        assert row["schema_version"] == "0.1.0"
        assert row["source"]["docket"] == "22-17"
        assert row["source"]["commission_affirmance_date"] == "2024-10-30"
        assert row["source"]["original_document_pdf_sha256"] is None
        assert row["source"]["pdf_visual_review_completed"] is False
        assert row["source"]["commercial_engine_use_approved"] is False
        a = row["published_record"]
        assert a["commission_affirmed_initial_dismissal"] is True
        assert a["systemic_unreasonable_invoicing_practice_proven"] is False
        assert a["isolated_overcharge_admitted_by_carrier_cents"] == 887955
        assert a["isolated_double_billing_admitted_record_cents"] == 365950
        assert a["isolated_double_billing_quote_cents"] == 365000
        assert a["quoted_amount_conflict_cents"] == 950
        assert a["isolated_double_billing_admitted_record_cents"] - a["isolated_double_billing_quote_cents"] == 950
        assert a["confirmed_exact_overlap_between_two_admissions"] is None
        assert a["aggregate_nonoverlapping_invoice_errors_cents"] is None
        assert a["cash_refund_amount_proven_cents"] is None
        assert a["these_credits_prove_cash_refund"] is False
        assert a["multiple_invoices_for_one_container_alone_establish_duplicate_charge"] is False
        b = row["truth_boundaries"]
        assert b["independent_original_invoice_label_count"] == 0
        assert b["independent_current_customer_invoice_error_cents"] is None
        assert b["customer_actual_refund_received"] == "UNKNOWN"
        assert b["commercial_customer_scoring"] is False
        assert b["retally_verified_recovered_cash_cents"] == 0
        controls = row["synthetic_negative_controls"]
        assert len(controls) == len({x["id"] for x in controls}) == 6
        assert all(x["kind"] == "SYNTHETIC" and x["expected"].startswith("REJECT_") for x in controls)

    def test_source_bound_record_and_nonpromotion(self):
        self.contract(self.case)

    def test_mutated_truth_and_source_claims_rejected(self):
        edits = [
            ("source", "original_document_pdf_sha256", "0" * 64),
            ("source", "commercial_engine_use_approved", True),
            ("source", "pdf_visual_review_completed", True),
            ("published_record", "systemic_unreasonable_invoicing_practice_proven", True),
            ("published_record", "isolated_overcharge_admitted_by_carrier_cents", 887956),
            ("published_record", "isolated_double_billing_admitted_record_cents", 365000),
            ("published_record", "quoted_amount_conflict_cents", 0),
            ("published_record", "aggregate_nonoverlapping_invoice_errors_cents", 1253905),
            ("published_record", "these_credits_prove_cash_refund", True),
            ("truth_boundaries", "independent_original_invoice_label_count", 2),
            ("truth_boundaries", "customer_actual_refund_received", "YES"),
            ("truth_boundaries", "retally_verified_recovered_cash_cents", 1),
        ]
        for section, field, replacement in edits:
            with self.subTest(section=section, field=field):
                copy_case = copy.deepcopy(self.case)
                copy_case[section][field] = replacement
                with self.assertRaises(AssertionError):
                    self.contract(copy_case)

if __name__ == "__main__":
    unittest.main()
