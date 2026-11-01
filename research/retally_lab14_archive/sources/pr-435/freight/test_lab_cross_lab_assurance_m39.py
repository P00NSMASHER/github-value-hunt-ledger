"""Mission 39: adversarial 14-lab execution/receipt assurance (local only)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.lab_assurance import digest
from freight import lab_cross_lab_assurance_m39 as m39
from freight.lab_phase4_director import execute_all_labs
from freight.test_lab_phase3_real_chain import rating_fixture, funded_store, scenario
from freight.test_lab_assurance import assertions_and_fees, verifier


def rehash(original):
    """Demonstrate local hashes do not authenticate a forged lab claim."""
    copy = deepcopy(original)
    stable = {**copy, "lab_runs": [
        {k: v for k, v in row.items() if k != "elapsed_ms"}
        for row in copy["lab_runs"]
    ]}
    stable.pop("receipt_sha256", None)
    copy["receipt_sha256"] = digest(stable)
    return copy


def fresh_execution(maximum=14):
    with tempfile.TemporaryDirectory(prefix="retally-m39-fixture-") as root:
        record, book = rating_fixture()
        store = funded_store(root)
        assertions, fees = assertions_and_fees()
        return execute_all_labs(
            record=record, authority_book=book, store=store,
            assertions=assertions, fee_events=fees, verifier=verifier(),
            contingency=scenario(), max_labs=maximum,
        )


class CrossLabM39Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = fresh_execution()

    def test_original_fourteen_labs_have_independent_structural_acceptance(self):
        r = m39.assess(self.original, require_complete=True)
        self.assertEqual(r["scope"], m39.SCOPE)
        self.assertEqual(r["local_review_decision"], m39.FULL)
        self.assertTrue(r["all_fourteen_locally_executed"])
        self.assertEqual(r["locally_executed_count"], 14)
        self.assertEqual(r["blocked_or_unexecuted_count"], 0)
        self.assertEqual(r["negative_probes_exactly_bound"], 14)
        self.assertEqual(r["existing_lab_count"], 14)
        self.assertEqual([x["lab"] for x in r["laboratory_results"]],
                         list(range(1, 15)))
        self.assertFalse(r["independently_authenticated_bank_or_carrier_money"])
        self.assertFalse(r["external_marketing_or_publication_authorized"])
        self.assertFalse(r["actual_hosted_staging_isolation_verified"])
        self.assertEqual(r["real_customer_revenue_cents"], 0)
        self.assertEqual(r["frozen_historical_findings_not_auto_closed"], 26)

    def test_exact_inherited_domain_proof_status_and_negative_probes(self):
        r = self.original
        self.assertEqual([r["lab_runs"][k-1]["proof"]["phase3_step"]
                          for k in (1, 4, 5, 8, 11)],
                         [m39.DOMAIN_STEP[k] for k in (1, 4, 5, 8, 11)])
        self.assertEqual([r["lab_runs"][k-1]["negative_probe"]
                          for k in range(1, 15)],
                         [m39.NEGATIVE_PROBE[k] for k in range(1, 15)])

    def test_rehashed_negative_probe_forgery_rejected_all_fourteen_labs(self):
        for lab in range(1, 15):
            r = deepcopy(self.original)
            r["lab_runs"][lab-1]["negative_probe"] = "PASS_WITHOUT_NEGATIVE_TEST"
            r = rehash(r)
            with self.subTest(lab=lab), self.assertRaisesRegex(
                ValueError, "M39_NEGATIVE_PROBE_REHASHED_OR_MISSING"
            ):
                m39.assess(r, require_complete=True)

    def test_rehashed_removed_proof_rejected_for_every_lab(self):
        for lab in range(1, 15):
            r = deepcopy(self.original)
            r["lab_runs"][lab-1]["proof"] = {}
            r = rehash(r)
            with self.subTest(lab=lab), self.assertRaisesRegex(
                ValueError, "M39_EXECUTED_LAB_WITHOUT_STRUCTURED_PROOF"
            ):
                m39.assess(r)

    def test_rehashed_replaced_status_cannot_promote_fabricated_execution(self):
        for lab in range(1, 15):
            r = deepcopy(self.original)
            r["lab_runs"][lab-1]["status"] = "EXECUTED_VENDOR_APPROVED"
            r = rehash(r)
            with self.subTest(lab=lab), self.assertRaisesRegex(
                ValueError, "M39_UNREGISTERED_LAB_STATUS_OR_FAKE_EXECUTION"
            ):
                m39.assess(r, require_complete=True)

    def test_rehashed_duplicate_or_swapped_lab_ids_rejected(self):
        for bad in (0, 2, True, 999):
            r = deepcopy(self.original)
            r["lab_runs"][0]["lab"] = bad
            r = rehash(r)
            with self.subTest(bad=bad), self.assertRaisesRegex(
                ValueError, "M39_LAB_ID_DUPLICATE_REORDER_OR_TITLE_CHANGED"
            ):
                m39.assess(r)
        r = deepcopy(self.original)
        r["lab_runs"][0], r["lab_runs"][1] = r["lab_runs"][1], r["lab_runs"][0]
        with self.assertRaisesRegex(ValueError, "M39_LAB_ID_DUPLICATE"):
            m39.assess(rehash(r))

    def test_rehashed_summary_falsification_fails_even_with_valid_local_sha(self):
        for field, value in (
            ("executed_labs", list(range(2, 15))),
            ("failed_or_blocked_labs", [14]),
        ):
            r = deepcopy(self.original)
            r[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "M39_EXECUTED_OR_FAILED_LAB_SUMMARY_TAMPERED"
            ):
                m39.assess(rehash(r))

    def test_all_external_authorities_and_cash_remain_unproven_when_rehashed(self):
        for field, value in (
            ("production_api_executed", True),
            ("hosted_staging_certified", True),
            ("customer_bank_carrier_authority_proven", True),
            ("actual_revenue_cents", 500),
            ("historical_findings_open", 0),
            ("laboratory_executions_not_equivalent_to_customer_accuracy", False),
            ("source_first_party", "AUTHENTICATED_REAL_CUSTOMER_AND_BANK_PROVIDER"),
        ):
            r = deepcopy(self.original)
            r[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                m39.assess(rehash(r), require_complete=True)

    def test_rehashed_lab14_pilot_approvals_or_source_claims_rejected(self):
        flags = [
            ("research_claim_clearance_external_approvals", 1),
            ("research_claim_clearance_pilot_gates_unmet", 0),
            ("research_m37_external_publication_authority", True),
            ("research_m38_external_claims_authorized", 16),
            ("research_m38_human_gates_unmet", 0),
            ("research_m38_hypothetical_census_values_quarantined", 0),
            ("rights_cleared_freight_data_imports", 7),
            ("real_invoice_adjudications_completed", 22),
            ("independent_customer_studies_completed", 1),
            ("source_refresh_automated", True),
            ("critical_current_path_negative_replays_m41", 0),
            ("critical_current_path_denials_m41", 3),
            ("critical_original_findings_closed_m41", 4),
            ("critical_original_vulnerable_revision_replays_m41", 4),
        ]
        for field, value in flags:
            r = deepcopy(self.original)
            r["lab_runs"][13]["proof"][field] = value
            r = rehash(r)
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "M39_LAB14_CUSTOMER_SOURCE_PERMISSION_OR_CLAIM_FABRICATED"
            ):
                m39.assess(r)

    def test_rehashed_lab6_security_and_lab9_procurement_and_lab10_tariff_flags(self):
        cases = [
            (6, "external_security_assurance", "CERTIFIED"),
            (9, "external_procurement_certification", "YES"),
            (10, "source_authenticity", "INDEPENDENT_CARRIER_SIGNED"),
            (12, "source", "REAL_BANK_TRANSACTIONS"),
            (13, "actual_customer_margin_cents", 5000),
        ]
        for lab, field, value in cases:
            r = deepcopy(self.original)
            r["lab_runs"][lab-1]["proof"][field] = value
            with self.subTest(lab=lab), self.assertRaises(ValueError):
                m39.assess(rehash(r))

    def test_forged_three_customer_pilot_rejected_even_with_both_hashes_updated(self):
        for field, value in (
            ("actual_company_revenue_cents", 500),
            ("actual_customer_recovery_cents", 50000),
            ("real_customer_permission_obtained", True),
            ("accepted_real_customer_count", 1),
        ):
            r = deepcopy(self.original)
            r["three_customer_pilot"][field] = value
            p = r["three_customer_pilot"]
            p["receipt_sha256"] = digest({
                k: v for k, v in p.items() if k != "receipt_sha256"
            })
            r = rehash(r)
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "M39_REAL_CUSTOMER_OUTCOME_OR_AUTHORITY_FABRICATED"
            ):
                m39.assess(r)

    def test_synthetic_savings_overstatement_rejected_against_independent_replay(self):
        r = deepcopy(self.original)
        r["three_customer_pilot"]["cohort"][0][
            "simulated_accounting"]["simulated_net_recovered_cents"] = 25000000
        p = r["three_customer_pilot"]
        p["receipt_sha256"] = digest({
            k: v for k, v in p.items() if k != "receipt_sha256"
        })
        r = rehash(r)
        with self.assertRaisesRegex(
            ValueError, "M39_REHASHED_FICTIONAL_PILOT_OUTCOME_CHANGED"
        ):
            m39.assess(r)

    def test_timing_is_excluded_from_receipts_but_wrong_types_fail(self):
        r = deepcopy(self.original)
        r["lab_runs"][0]["elapsed_ms"] += 1300
        accepted = m39.assess(r)
        self.assertEqual(accepted["source_execution_receipt_sha256"],
                         self.original["receipt_sha256"])
        r["lab_runs"][0]["elapsed_ms"] = True
        with self.assertRaisesRegex(ValueError, "M39_INVALID_EXECUTION_TIME"):
            m39.assess(r)

    def test_budget_cannot_be_accepted_as_all_labs_passed(self):
        r = fresh_execution(maximum=5)
        result = m39.assess(r, require_complete=False)
        self.assertEqual(result["locally_executed_count"], 5)
        self.assertEqual(result["blocked_or_unexecuted_count"], 9)
        self.assertEqual(result["local_review_decision"], m39.INCOMPLETE)
        self.assertFalse(result["all_fourteen_locally_executed"])
        with self.assertRaisesRegex(
            ValueError, "M39_INCOMPLETE_OR_FAILED_RESEARCH_LABS_CANNOT_PASS"
        ):
            m39.assess(r, require_complete=True)

    def test_structure_missing_or_unexpected_fields_fails_closed(self):
        for field in ("lab_runs", "scope", "receipt_sha256",
                      "three_customer_pilot", "executed_labs"):
            r = deepcopy(self.original)
            del r[field]
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "M39_EXECUTION_RECEIPT_UNEXPECTED_FIELDS"
            ):
                m39.assess(r)
        r = deepcopy(self.original)
        r["externally_signed_recovery"] = True
        with self.assertRaisesRegex(ValueError, "M39_EXECUTION_RECEIPT_UNEXPECTED_FIELDS"):
            m39.assess(r)

    def test_forged_receipt_with_original_shape_still_fails_local_hash(self):
        r = deepcopy(self.original)
        r["lab_runs"][1]["proof"]["synthetic_customer_reactions"] += 1
        with self.assertRaisesRegex(ValueError, "M39_REHASHED_OR_TAMPERED_EXECUTION_RECEIPT"):
            m39.assess(r)

    def test_local_receipts_are_not_third_party_certs_or_external_publication(self):
        report = m39.assess(self.original)
        self.assertEqual(report["receipt_sha256"], digest({
            k: v for k, v in report.items() if k != "receipt_sha256"
        }))
        self.assertTrue(report["receipt_not_third_party_attestation"])
        self.assertFalse(report["external_marketing_or_publication_authorized"])
        self.assertEqual(report["real_customers_observed"], 0)
        self.assertEqual(report["simulated_pilot_customer_count"], 3)

    def test_render_html_discloses_local_scope_and_escapes_text(self):
        report = m39.assess(self.original)
        injected = deepcopy(report)
        injected["laboratory_results"][0]["title"] = "<img src=x onerror=alert(1)>"
        html = m39.render_html(injected)
        self.assertIn("&lt;img", html)
        self.assertNotIn("<img", html)
        self.assertIn("26 historical findings", html)
        self.assertIn("14 / 14", html)

    def test_cli_runs_only_after_rejecting_invalid_input(self):
        with tempfile.TemporaryDirectory() as home:
            root = Path(home)
            input_path = root / "input.json"
            output = root / "assessed"
            input_path.write_text(json.dumps(self.original), encoding="utf-8")
            with patch("sys.argv", ["m39", "--receipt", str(input_path),
                                    "--out", str(output)]):
                m39.main()
            report = json.loads((output / "lab_cross_check_m39.json").read_text())
            self.assertEqual(report["locally_executed_count"], 14)
            self.assertIn("Cross-lab integrity", (
                output / "lab_cross_check_m39.html").read_text())
            bad = root / "bad.json"
            tampered = deepcopy(self.original)
            tampered["production_api_executed"] = True
            bad.write_text(json.dumps(rehash(tampered)), encoding="utf-8")
            second = root / "must_not_create"
            with patch("sys.argv", ["m39", "--receipt", str(bad),
                                    "--out", str(second)]):
                with self.assertRaisesRegex(ValueError, "M39_EXTERNAL_PRODUCTION"):
                    m39.main()
            self.assertFalse(second.exists())


if __name__ == "__main__":
    unittest.main()
