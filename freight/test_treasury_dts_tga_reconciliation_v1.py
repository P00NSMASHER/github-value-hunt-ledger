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
        self.assertEqual(len(d["real_reported_cases"]), 2)
        self.assertEqual({r["record_date"] for r in d["real_reported_cases"]},
                         {"2025-01-31", "2025-02-28"})
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
        self.assertEqual([residual(r) for r in rows], [0, 0])
        self.assertEqual(rows[0]["closing_today_musd"], rows[1]["opening_this_month_musd"])
        self.assertEqual(self.pack["tests_and_limitations"]["observed_residuals_musd"], [0, 0])
        self.assertEqual(self.pack["tests_and_limitations"]["cross_month_residual_musd"], 0)
        self.assertTrue(all(r["source_url"].startswith("https://fiscaldata.treasury.gov/")
                            and r["document_page"] == 1 for r in rows))

    def test_synthetic_mutations_reject_bad_arithmetic_and_unsupported_truth(self):
        d = self.pack
        controls = d["synthetic_controls"]
        self.assertEqual(len(controls), 8)
        self.assertEqual(len({x["id"] for x in controls}), 8)
        base = d["real_reported_cases"][1]
        for c in controls:
            with self.subTest(c=c["id"]):
                self.assertEqual(gate(c, base), c["expected"])
                self.assertIsNone(c["independent_real_label"])
                self.assertEqual(c["provenance"], "RESEARCH_AUTHORED_SYNTHETIC_NOT_ORIGINAL_REPORT")
        self.assertEqual(sum(c["split"] == "synthetic_holdout" for c in controls), 6)

    def test_mutation_detection_red_to_green_contract(self):
        base = dict(self.pack["real_reported_cases"][0])
        self.assertEqual(residual(base), 0)
        corrupted = dict(base, closing_today_musd=base["closing_today_musd"]+10)
        self.assertEqual(residual(corrupted), -10)
        self.assertGreater(abs(residual(corrupted)), 2)
        self.assertEqual(residual(base), 0)

    def test_no_cash_recovery_claim_or_cross_engine_label_leak(self):
        d = self.pack
        e = d["tests_and_limitations"]
        self.assertEqual(e["independent_real_world_heldout_cases"], 0)
        self.assertEqual(e["real_reported_accounting_cases"], 2)
        self.assertIsNone(e["independent_recovery_accuracy"])
        self.assertIsNone(e["invoice_level_accuracy"])
        self.assertIsNone(e["commercial_scoring_precision"])
        self.assertFalse(d["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(d["restrictions"]["writer_branch_modified"])
        self.assertFalse(d["restrictions"]["release_authorized"])
        self.assertEqual(d["source_identity"]["raw_invoice_or_bank_documents"], 0)

if __name__ == "__main__":
    unittest.main()
