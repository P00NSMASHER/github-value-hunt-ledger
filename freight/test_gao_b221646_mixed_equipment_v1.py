"""Source-bound GAO B-221646 mixed-validity equipment holdout, no engine calls."""
import json
import unittest
from pathlib import Path

PACK = Path(__file__).parent / "fixtures" / "gao_b221646_mixed_equipment_holdout_v1.json"


def adjudicated_scope_for_reported_equipment(equipment_code, portable_heater, division_called):
    """Only this historical decision's observed AV/AR equipment cohorts are labeled."""
    if equipment_code == "AV":
        return False
    if equipment_code == "AR":
        return True
    return None


class GAOB221646MixedEquipment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_official_provenance_rights_and_uncustodied_source(self):
        p, s = self.pack, self.pack["source"]
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(s["decision_id"], "B-221646")
        self.assertEqual(s["decision_date"], "1987-09-18")
        self.assertEqual(s["original_public_decision_url"], "https://www.gao.gov/assets/b-221646.pdf")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertIn("NO_ENDORSEMENT", s["rights"])
        self.assertEqual(s["original_decision_pages"], 6)
        self.assertIsNone(s["original_pdf_response_sha256"])
        self.assertIsNone(s["original_pdf_response_byte_length"])
        self.assertFalse(s["original_pdf_bytes_independently_custodied"])
        self.assertFalse(s["original_GBL_invoice_and_tender_bytes_custodied"])
        self.assertEqual(s["third_party_carrier_tender_rights"], "UNKNOWN_NOT_CLEARED")

    def test_decision_contains_both_real_aggregate_cohort_outcomes(self):
        a = self.pack["adjudication"]
        cohorts = {c["equipment_code"]: c for c in a["adjudicated_cohorts"]}
        self.assertEqual(set(cohorts), {"AV", "AR"})
        self.assertEqual(a["total_reported_shipments"], 38)
        self.assertEqual(cohorts["AV"]["shipment_count"], 13)
        self.assertEqual(cohorts["AR"]["shipment_count"], 25)
        self.assertEqual(sum(c["shipment_count"] for c in cohorts.values()), 38)
        self.assertFalse(cohorts["AV"]["rate_tenders_applicable"])
        self.assertTrue(cohorts["AR"]["rate_tenders_applicable"])
        self.assertEqual(cohorts["AV"]["GAO_result"], "GSA_OVERCHARGE_DEDUCTIONS_INCORRECT")
        self.assertEqual(cohorts["AR"]["GAO_result"], "GSA_OVERCHARGE_DEDUCTIONS_SUSTAINED")
        self.assertEqual(a["tariff_basis_for_original_carrier_charges"], "UNKNOWN_SOURCE_EXPLICITLY_NOT_DISCLOSED")
        self.assertFalse(a["independent_bank_clearing_proof"])

    def test_red_baselines_are_not_real_engine_accuracy(self):
        p = self.pack
        baselines = {x["id"]: x for x in p["heldout"]["rule_baseline_experiments_NOT_engine_scores"]}
        self.assertEqual(baselines["NAIVE_PROTECT_FROM_FREEZING_IMPLIES_TENDER"]["GAO_reported_aggregate_mismatches"], 13)
        self.assertEqual(baselines["NAIVE_NO_SCAT_CALL_IMPLIES_NO_TENDER"]["GAO_reported_aggregate_mismatches"], 25)
        self.assertEqual(p["heldout"]["independent_decision_labels"], 1)
        self.assertEqual(p["heldout"]["aggregate_equipment_strata_labels"], 2)
        self.assertEqual(p["heldout"]["independent_per_shipment_original_GBL_labels"], 0)
        self.assertEqual(p["heldout"]["product_engine_predictions_on_this_decision"], 0)
        self.assertEqual(p["heldout"]["external_real_customer_cases"], 0)
        self.assertIsNone(p["heldout"]["real_customer_error_precision"])
        self.assertIsNone(p["heldout"]["real_customer_error_recall"])

    def test_synthetic_counterexamples_and_mutations(self):
        controls = self.pack["synthetic_negative_controls"]
        self.assertEqual(len(controls), 9)
        self.assertEqual(len({x["id"] for x in controls}), 9)
        self.assertTrue(all(x["id"].startswith("SYNTH_")
                            and x["kind"] == "SYNTHETIC_NOT_ORIGINAL_SHIPMENT"
                            and x["independent_real_customer_label"] is None for x in controls))
        for control in controls[:6]:
            fields = control["input"]
            self.assertIs(
                adjudicated_scope_for_reported_equipment(
                    fields["equipment_code"], fields["portable_heater"], fields["division_called"]),
                control["expected_tender_applies"],
            )
        # Metamorphic negatives: portable heater and operating division do not turn AV into AR.
        self.assertFalse(adjudicated_scope_for_reported_equipment("AV", True, "SCAT"))
        self.assertTrue(adjudicated_scope_for_reported_equipment("AR", False, "general"))
        self.assertIsNone(adjudicated_scope_for_reported_equipment(None, True, "general"))
        self.assertEqual(controls[6]["expected_guard"], "UNKNOWN_NOT_ZERO")
        self.assertEqual(controls[7]["expected_guard"], "REJECT_ONE_DECISION_TWO_AGGREGATE_COHORT_LABELS")
        self.assertEqual(controls[8]["expected_guard"], "REJECT_GSA_DEDUCTION_NOT_RETALLY_CUSTOMER_CASH")

    def test_money_and_holdout_dedup_are_fail_closed(self):
        p = self.pack
        a, h, d = p["adjudication"], p["heldout"], p["dedup"]
        self.assertIsNone(a["footnote_deduction_range_dollars"]["aggregate_total_cents"])
        self.assertIsNone(a["footnote_deduction_range_dollars"]["individual_amounts"])
        self.assertEqual(a["footnote_deduction_range_dollars"]["per_cohort_assignment"], "UNKNOWN")
        self.assertEqual(h["money_amount_by_stratum"], "UNKNOWN_NOT_IN_SOURCE")
        self.assertEqual(h["actual_customer_cash_cents"], 0)
        self.assertEqual(a["observed_RETALLY_customer_recovery_cents"], 0)
        self.assertEqual(d["primary_decision_key"], "GAO/B-221646")
        self.assertEqual(len(set(d["labeled_cohort_keys"])), 2)
        self.assertTrue(d["must_not_multiply_independent_decision_count_by_shipments"])
        self.assertFalse(p["restrictions"]["legacy_15_lab_consolidation_certified"])
        self.assertFalse(p["restrictions"]["release_authorized"])


if __name__ == "__main__":
    unittest.main()
