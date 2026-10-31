"""Official Treasury aggregate accounting identity, never customer cash or invoices."""
import json
from pathlib import Path
import unittest
from datetime import date

PATH = Path(__file__).parent / "fixtures" / "treasury_dts_tga_reconciliation_v1.json"
FIELDS = ("opening_today_musd", "deposits_today_musd", "withdrawals_today_musd", "closing_today_musd")

def residual(row):
    if any(row.get(k) is None for k in FIELDS):
        return None
    return (row["opening_today_musd"] + row["deposits_today_musd"]
            - row["withdrawals_today_musd"] - row["closing_today_musd"])

def gate(control, base):
    kind = control["kind"]
    row = dict(base)
    if kind == "alter_field":
        row[control["field"]] += control["delta"]
    elif kind == "double_count_deposits":
        row["deposits_today_musd"] *= 2
    elif kind == "reverse_withdrawals":
        row["withdrawals_today_musd"] *= -1
    elif kind == "missing_field":
        row[control["field"]] = None
    elif kind == "duplicate_publisher_as_independent":
        return "REJECT_NOT_INDEPENDENT"
    elif kind == "claim_customer_cash":
        return "UNKNOWN_NO_BANK_SETTLEMENT"
    elif kind == "rounding_nonzero_not_error":
        value = residual(row)
        return "UNKNOWN_ROUNDING_AMBIGUITY" if value is not None and 0 < abs(value) <= 2 else "MISMATCH"
    elif kind == "cross_month_opening_mismatch":
        return ("MISMATCH" if control["claimed_march_opening_musd"] != control["feb_closing_musd"] else "MATCH")
    elif kind == "lookahead":
        return ("REJECT_LOOKAHEAD" if date.fromisoformat(control["source_date"]) >
                date.fromisoformat(control["asof_date"]) else "UNKNOWN")
    else:
        raise AssertionError("unrecognized synthetic scenario")
    result = residual(row)
    if result is None:
        return "UNKNOWN_MISSING_FIELD"
    if abs(result) > 2:
        return "MISMATCH"
    return "UNKNOWN_ROUNDING_AMBIGUITY"

class TreasuryDTSReconciliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PATH.read_text(encoding="utf-8"))

    def test_real_source_dates_and_provenance_cannot_be_fake_independent_labels(self):
        d = self.pack
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["source"]["publisher"], "U.S. Treasury, Bureau of the Fiscal Service")
        self.assertEqual(len(d["real_reported_cases"]), 4)
        self.assertEqual({r["record_date"] for r in d["real_reported_cases"]},
                         {"2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30"})
        self.assertEqual({r["split"] for r in d["real_reported_cases"]},
                         {"calibration", "temporal_holdout_same_publisher"})
        self.assertEqual(d["source_identity"]["publisher_independent_count"], 1)
        self.assertEqual(d["source_identity"]["independently_adjudicated_outcome_labels"], 0)
        self.assertEqual(d["source_identity"]["independent_cross_publisher_cash_confirmation"], 0)
        self.assertIsNone(d["source"]["source_pdf_http_body_sha256"])
        self.assertFalse(d["source"]["source_pdf_bytes_custodied"])
        self.assertFalse(d["source"]["commercial_customer_scoring_authorized"])

    def test_official_reported_cash_identity_and_time_bucket_join(self):
        rows = self.pack["real_reported_cases"]
        self.assertEqual([residual(r) for r in rows], [0, 0, 0, -1])
        self.assertEqual(rows[0]["closing_today_musd"], rows[1]["opening_this_month_musd"])
        self.assertEqual(rows[1]["closing_today_musd"], rows[2]["opening_this_month_musd"])
        self.assertEqual(rows[2]["closing_today_musd"], rows[3]["opening_this_month_musd"])
        self.assertEqual(self.pack["tests_and_limitations"]["observed_residuals_musd"], [0, 0, 0, -1])
        self.assertEqual(self.pack["tests_and_limitations"]["cross_month_residual_musd"], 0)
        self.assertTrue(all(r["source_url"].startswith("https://fiscaldata.treasury.gov/")
                            and r["document_page"] == 1 for r in rows))

    def test_synthetic_mutations_reject_bad_arithmetic_and_unsupported_truth(self):
        d = self.pack
        controls = d["synthetic_controls"]
        self.assertEqual(len(controls), 11)
        self.assertEqual(len({x["id"] for x in controls}), 11)
        base = d["real_reported_cases"][1]
        for c in controls:
            with self.subTest(c=c["id"]):
                selected = next((r for r in d["real_reported_cases"] if r["id"] == c.get("base_case_id")), base)
                self.assertEqual(gate(c, selected), c["expected"])
                self.assertIsNone(c["independent_real_label"])
                self.assertEqual(c["provenance"], "RESEARCH_AUTHORED_SYNTHETIC_NOT_ORIGINAL_REPORT")
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in controls), 9)

    def test_mutation_detection_red_to_green_contract(self):
        base = dict(self.pack["real_reported_cases"][0])
        self.assertEqual(residual(base), 0)
        corrupted = dict(base, closing_today_musd=base["closing_today_musd"]+10)
        self.assertEqual(residual(corrupted), -10)
        self.assertGreater(abs(residual(corrupted)), 2)
        self.assertEqual(residual(base), 0)

    def test_march_heldout_and_adversarial_month_opening(self):
        cases = self.pack["real_reported_cases"]
        march = cases[2]
        self.assertEqual(march["record_date"], "2025-03-31")
        self.assertEqual(march["opening_today_musd"], 301789)
        self.assertEqual(march["deposits_today_musd"], 262527)
        self.assertEqual(march["withdrawals_today_musd"], 158530)
        self.assertEqual(march["closing_today_musd"], 405786)
        self.assertEqual(residual(march), 0)
        self.assertEqual(cases[1]["closing_today_musd"], march["opening_this_month_musd"])
        self.assertEqual(self.pack["tests_and_limitations"]["cross_month_residuals_musd"], [0, 0, 0])
        control = next(c for c in self.pack["synthetic_controls"] if c["id"] == "SYN_MARCH_CROSS_MONTH_OPEN_TAMPER")
        self.assertEqual(gate(control, march), "MISMATCH")
        self.assertEqual(control["independent_real_label"], None)
        self.assertEqual(self.pack["source_identity"]["publisher_independent_count"], 1)
        self.assertEqual(self.pack["tests_and_limitations"]["independent_real_world_heldout_cases"], 0)

    def test_april_reported_rounding_temporal_holdout_not_one_million_recovery(self):
        rows = self.pack["real_reported_cases"]
        april = rows[3]
        self.assertEqual(april["record_date"], "2025-04-30")
        self.assertEqual(april["source_url"], "https://fiscaldata.treasury.gov/static-data/published-reports/dts/DailyTreasuryStatement_20250430.pdf")
        self.assertEqual((april["opening_today_musd"], april["deposits_today_musd"],
                          april["withdrawals_today_musd"], april["closing_today_musd"]),
                         (616705, 307733, 246782, 677657))
        self.assertEqual(rows[2]["closing_today_musd"], april["opening_this_month_musd"])
        self.assertEqual(residual(april), -1)  # Real printed million-dollar rounded cells.
        self.assertNotEqual(residual(april), 0)  # Baseline exact-identity assumption is RED.
        self.assertLessEqual(abs(residual(april)), self.pack["tests_and_limitations"]["allowed_aggregate_rounding_tolerance_musd"])
        self.assertEqual(self.pack["source_identity"]["publisher_independent_count"], 1)
        self.assertEqual(self.pack["source_identity"]["independently_adjudicated_outcome_labels"], 0)
        self.assertIsNone(self.pack["source"]["source_pdf_http_body_sha256"])
        self.assertFalse(self.pack["source"]["source_pdf_bytes_custodied"])
        self.assertEqual(self.pack["tests_and_limitations"]["cross_month_residuals_musd"], [0, 0, 0])
        self.assertEqual(self.pack["tests_and_limitations"]["independent_real_world_heldout_cases"], 0)

    def test_april_synthetic_rounding_and_tamper_are_not_original_labels(self):
        rows = self.pack["real_reported_cases"]
        controls = [c for c in self.pack["synthetic_controls"] if c.get("base_case_id") == rows[3]["id"]]
        self.assertEqual(len(controls), 2)
        self.assertEqual({c["id"] for c in controls}, {"SYN_APR_NONZERO_ROUNDING_FALSE_ERROR", "SYN_APR_TAMPER_CLOSING_BY_10M"})
        for c in controls:
            self.assertEqual(c["split"], "synthetic_holdout")
            self.assertIsNone(c["independent_real_label"])
            self.assertEqual(gate(c, rows[3]), c["expected"])
        self.assertEqual(gate(controls[0], rows[3]), "UNKNOWN_ROUNDING_AMBIGUITY")
        self.assertEqual(gate(controls[1], rows[3]), "MISMATCH")
        self.assertIsNone(self.pack["tests_and_limitations"]["independent_recovery_accuracy"])

    def test_no_cash_recovery_claim_or_cross_engine_label_leak(self):
        d = self.pack
        e = d["tests_and_limitations"]
        self.assertEqual(e["independent_real_world_heldout_cases"], 0)
        self.assertEqual(e["real_reported_accounting_cases"], 4)
        self.assertIsNone(e["independent_recovery_accuracy"])
        self.assertIsNone(e["invoice_level_accuracy"])
        self.assertIsNone(e["commercial_scoring_precision"])
        self.assertFalse(d["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(d["restrictions"]["writer_branch_modified"])
        self.assertFalse(d["restrictions"]["release_authorized"])
        self.assertEqual(d["source_identity"]["raw_invoice_or_bank_documents"], 0)

if __name__ == "__main__":
    unittest.main()
