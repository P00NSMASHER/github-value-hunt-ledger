"""Offline adversarial contract tests for all four unified research lanes."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from freight.unified_research_lab import (
    ENGINES, SEARCHES, SEEDS, ResearchError, current_engine, ledger_from, merge_sources,
    read_ledger, run, safe_url, scan, source_record, validate_ledger,
    mirror_scout_all, get_json, metadata_in_scope, original_nyc_catalog_entry,
)

NOW = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)


class ProtectedMainOfficialSourceReconciliationTests(unittest.TestCase):
    """Hold six upstream source identities without admitting new provider hosts."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "protected_main_official_source_reconciliation_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def test_current_main_four_fmc_pointers_cannot_be_promoted(self):
        """Current upstream main-only sources stay held until independent review."""
        data = self._pack()["ownership"]["current_main_fmc_source_gap"]
        self.assertEqual(data["canonical_main_sha"],
                         "b1c49b7ad6431d648325ba31b804ecd0542857d6")
        self.assertEqual(data["canonical_main_catalog_git_blob_sha1"],
                         "fe6faa9d85d002fcabf3f38b8c2836f1fbdb86fc")
        self.assertEqual(data["candidate_before_sha"],
                         "6c9447d1336a43e2ba8a9e6c47abedea372252b9")
        self.assertEqual(data["candidate_before_catalog_git_blob_sha1"],
                         "a52e50df2e273465d14ebda947fb3b3027acd6d3")
        self.assertEqual(data["main_only_fmc_pointer_count"], 4)
        self.assertEqual(data["evaluation_family"],
                         "FREIGHT_PUBLIC_ADMINISTRATIVE_RECORD_SOURCE_IDENTITY_ONLY")
        for gate in ("raw_publisher_pdf_bytes_held", "production_seed_promotion_authorized",
                     "host_allowlist_change_authorized", "independent_qa_complete",
                     "engine_changes_made"):
            self.assertIs(data[gate], False)
        self.assertEqual(data["rights_state"], "UNVERIFIED_HOLD")
        self.assertEqual(data["independent_customer_ground_truth_cases"], 0)
        expected = (
            ("2015(I)", "SETTLEMENT_DISMISSAL_ORDER", "2024-11-08"),
            ("2015(I)", "SETTLEMENT_NONREVIEW_NOTICE", "2024-12-10"),
            ("2036(I)", "INITIAL_DECISION_WITH_APPENDICES", "2026-07-16"),
            ("2036(I)", "EXTENSION_DENIAL_NOT_PROOF_OF_FINALITY", "2026-07-23"),
        )
        rows = data["sources"]
        self.assertEqual(len(rows), 4)
        self.assertEqual([(x["docket"], x["document_kind"], x["served_on"])
                          for x in rows], list(expected))
        self.assertEqual(len({x["url"] for x in rows}), 4)
        for row in rows:
            self.assertTrue(row["url"].startswith(
                "https://www2.fmc.gov/readingroom/docs/"))
            self.assertNotIn(row["url"], SEEDS["freightrecovery"])
            self.assertIsNone(row["publisher_response_bytes_sha256"])
            self.assertIs(row["independently_heldout_real_customer_label"], False)
            self.assertIs(row["commercial_reuse_approved"], False)
            self.assertIs(row["actual_cash_settlement_replayed"], False)
            self.assertEqual(row["customer_invoice_ground_truth"], "UNKNOWN")
        controls = data["synthetic_negative_controls"]
        self.assertEqual(len(controls), 4)
        self.assertEqual(len({x["id"] for x in controls}), 4)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" for x in controls))
        self.assertEqual(data["acceptance_state"],
                         "HELD_REQUIRES_MAIN_TREE_RECONCILIATION_AND_INDEPENDENT_QA")

    def _assert_contract(self, pack):
        self.assertEqual(set(pack), {"schema_version", "evaluation_family",
                         "asof_date", "ownership", "rights", "cohort", "sources",
                         "synthetic_negative_controls", "acceptance"})
        self.assertEqual(pack["schema_version"], "0.1.0")
        self.assertEqual(pack["evaluation_family"],
                         "OFFICIAL_FREIGHT_SOURCE_RECONCILIATION_POINTER_HOLD_NOT_INVOICE_SCORING")
        self.assertEqual(pack["ownership"]["canonical_repository"],
                         "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(pack["ownership"]["candidate_before_commit"],
                         "c62f6a1ce9c4587c606b2b39c4570e5dc1eac57e")
        self.assertFalse(pack["ownership"]["official_host_allowlist_or_provider_rule_change_applied"])
        self.assertEqual(pack["ownership"]["original_main_seed_references_count"], 6)
        self.assertEqual(pack["rights"]["rights_status"], "HOLD")
        self.assertFalse(pack["rights"]["commercial_engine_admission_authorized"])
        self.assertEqual(pack["cohort"]["independent_held_out_invoice_labels"], 0)
        self.assertEqual(pack["cohort"]["shipment_level_reliable_error_truth_labels"], 0)
        self.assertEqual(pack["cohort"]["real_customer_invoice_or_receipt_documents_custodied"], 0)
        self.assertFalse(pack["cohort"]["freight_error_scoring_eligible"])
        for name in ("main_to_candidate_executable_seeds_reconciled",
                     "provider_host_policy_change_authorized",
                     "independent_qa_complete", "actual_current_main_integration_green",
                     "release_authorized"):
            self.assertFalse(pack["acceptance"][name])
        expected = (
          ("DOJ_2016_MENLO_ESTES", "2016-05-03", 1300000000,
           "PUBLISHER_REPORTS_PAID_AGGREGATE_SETTLEMENT"),
          ("DOJ_2022_YRC", "2022-03-14", 685000000,
           "PUBLISHER_REPORTS_APPROXIMATE_AGREED_SETTLEMENT_NOT_PAID_PROOF"),
          ("CBCA_6578_RATE_2020", "2020-08-06", 1554908,
           "CARRIER_PAID_GSA_SEVEN_NOTICES_CLAIM_GRANTED_REFUND_UNVERIFIED"),
          ("CBCA_8051_RATE_2024", "2024-08-08", 1459569,
           "UNPAID_CARRIER_INVOICE_CLAIM_TIME_BARRED_NOT_OVERCHARGE"),
          ("CBCA_1317_RATE_2009", "2009-10-29", 13735675,
           "TWELVE_RAIL_BOL_DEDUCTIONS_REVERSED_AS_UNTIMELY_NOT_VERIFIED_CARRIER_REFUND"),
          ("CBCA_3467_RATE_2014", "2014-05-14", 33989575,
           "GSA_70_PAID_DETENTION_INVOICE_RECOUPMENT_NOTICES_INVALID_NO_REFUND_PROOF"),
        )
        self.assertEqual(len(pack["sources"]), 6)
        self.assertEqual(len({x["url"] for x in pack["sources"]}), 6)
        rows_keys = {"id", "url", "publisher", "published_on", "reported_amount_cents",
                     "publisher_outcome_scope", "source_review_status",
                     "reported_amount_semantics", "original_publisher_response_bytes_acquired",
                     "original_publisher_response_sha256",
                     "original_invoice_tariff_bank_receipt_custody",
                     "source_specific_commercial_rights_verified",
                     "independent_held_out_customer_invoice_label",
                     "actual_customer_invoice_error_label",
                     "independent_actual_settlement_cash_receipt_verified",
                     "verified_retally_customer_recovery_cents", "historical_tariff_effective_date"}
        for row, should in zip(pack["sources"], expected):
            self.assertEqual(set(row), rows_keys | ({"decision_evidence"} if
                             row["id"] in ("CBCA_6578_RATE_2020", "CBCA_8051_RATE_2024",
                                           "CBCA_1317_RATE_2009",
                                           "CBCA_3467_RATE_2014") else set()))  # Explicit nested whitelist.
            self.assertEqual((row["id"], row["published_on"], row["reported_amount_cents"],
                              row["publisher_outcome_scope"]), should)
            self.assertTrue(row["url"].startswith("https://www.justice.gov/" if
                                                 row["publisher"] == "DOJ"
                                                 else "https://www.cbca.gov/"))
            self.assertFalse(row["original_publisher_response_bytes_acquired"])
            self.assertIsNone(row["original_publisher_response_sha256"])
            self.assertFalse(row["original_invoice_tariff_bank_receipt_custody"])
            self.assertFalse(row["source_specific_commercial_rights_verified"])
            self.assertFalse(row["independent_held_out_customer_invoice_label"])
            self.assertFalse(row["independent_actual_settlement_cash_receipt_verified"])
            self.assertEqual(row["actual_customer_invoice_error_label"], "UNKNOWN")
            self.assertEqual(row["verified_retally_customer_recovery_cents"], 0)
            self.assertIsNone(row["historical_tariff_effective_date"])
            self.assertNotIn(row["url"], SEEDS["freightrecovery"])
            with self.assertRaises(ResearchError):
                safe_url(row["url"])  # Existing candidate does NOT permit these hosts.
        self.assertEqual(pack["sources"][0]["reported_amount_semantics"],
                         "EXACT_REPORTED_AGGREGATE_NOT_INVOICE_LABEL")
        self.assertEqual(pack["sources"][1]["reported_amount_semantics"],
                         "APPROXIMATE_AGREED_AGGREGATE_NOT_RECEIPT")
        self.assertEqual(pack["sources"][3]["reported_amount_semantics"],
                         "CLAIM_FACE_VALUE_NOT_PAYMENT_OR_OVERCHARGE")
        # First-party CBCA 8051-RATE: original 2018 invoice was timely,
        # but the later denial challenge was not. DPS approval is not payment.
        j = pack["sources"][3]
        self.assertEqual(j["source_review_status"],
                         "ORIGINAL_CBCA_13_PAGE_PDF_TEXT_REVIEWED_PAGES_1_13_VISUALLY_CHECKED_2026_10_27")
        self.assertEqual(j["decision_evidence"], {"original_pdf_pages": 13, "original_pdf_pages_visually_verified": [1, 13], "service_start_date": "2018-05-31", "delivery_window": "JUNE_OR_JULY_2018", "invoice_form": "SF_1113", "original_invoice_submitted_on": "2018-09-26", "dps_internal_approval_on": "2018-09-28", "prepayment_audit_payment_denied_on": "2018-10-02", "prepayment_denial_reason": "MISSING_WEIGHT_TICKET", "initial_approval_equates_to_government_payment": False, "notice_contained_regulatorily_required_appeal_rights": False, "internal_weight_ticket_discussion_on": "2019-07-12", "documented_government_receipt_of_2019_resubmission": False, "first_documented_followup_on_denied_invoice": "2023-01-13", "gsa_claim_denied_on": "2024-01-22", "board_review_requested_on": "2024-03-19", "board_review_within_six_months": True, "separate_underlying_payment_denial_claim_timely": False, "missing_appeal_notice_actual_prejudice_proven": False, "accounting_record_issue": "UNPAID_INVOICE_LOST_IN_CARRIER_ACCOUNTING_SYSTEM", "reported_unpaid_invoice_amount_cents": 1459569, "board_decision": "CARRIER_UNPAID_CLAIM_DENIED_AS_UNTIMELY_NOT_RATE_ERROR_ADJUDICATION", "actual_government_payment_independently_verified": False, "original_invoice_ticket_bol_and_bank_bytes_acquired": False, "applicable_historical_tariff_effective_date": None, "current_customer_billing_error_ground_truth": "UNKNOWN"})
        je = j["decision_evidence"]
        self.assertLess(datetime.fromisoformat(je["original_invoice_submitted_on"]),
                        datetime.fromisoformat(je["prepayment_audit_payment_denied_on"]))
        self.assertLess(datetime.fromisoformat(je["prepayment_audit_payment_denied_on"]),
                        datetime.fromisoformat(je["first_documented_followup_on_denied_invoice"]))
        self.assertLess(datetime.fromisoformat(je["gsa_claim_denied_on"]),
                        datetime.fromisoformat(je["board_review_requested_on"]))
        self.assertEqual(pack["cohort"]["primary_original_text_or_first_page_checked_this_run"], 6)
        self.assertEqual(pack["sources"][2]["source_review_status"],
                         "ORIGINAL_CBCA_PDF_TEXT_REVIEWED_PAGES_1_3_6_VISUAL_2026_10_27")
        self.assertEqual(pack["sources"][2]["reported_amount_semantics"],
                         "CARRIER_PAID_GSA_DISPUTED_NOTICES_NOT_VERIFIED_REFUND_RECEIVED")
        self.assertEqual(pack["sources"][2]["decision_evidence"], {
            "original_pdf_pages": 6,
            "visually_reviewed_pages_one_based": [1, 3, 6],
            "shipment_year": 2014,
            "government_notices_total": 115,
            "appealed_notices": 7,
            "other_notices_disposition": "UNKNOWN",
            "carrier_paid_gsa_disputed_notices_cents": 1554908,
            "board_disposition": "AARE_CLAIM_GRANTED_GSA_OVERCHARGE_PREMISE_REJECTED",
            "carrier_refund_received_independently_verified": False,
            "underlying_original_tenders_gbls_or_bank_receipts_acquired": False,
        })
        # Official CBCA 1317-RATE decision table: 12 reported BOL references, not
        # original BOL custody or independently held-out customer truth.
        u = pack["sources"][4]
        self.assertEqual(u["source_review_status"],
                         "ORIGINAL_CBCA_PDF_TEXT_REVIEWED_PAGES_1_2_3_5_7_WEB_RENDER_VISUAL_PAGES_3_7_8_2026_10_27")
        self.assertEqual(u["reported_amount_semantics"],
                         "ACTUAL_TREASURY_DEDUCTIONS_REPORTED_IN_DECISION_NOT_VALIDATED_OVERCHARGE_OR_REFUND")
        e = u["decision_evidence"]
        self.assertEqual(set(e), {
            "original_pdf_pages", "board_reported_initial_overcharge_notices",
            "original_claims_reportedly_resolved", "added_claims_in_same_proceeding",
            "remaining_appealed_bols", "decision_bol_table_one_based_page",
            "sum_reported_overcharge_notices_cents", "sum_treasury_deductions_cents",
            "gap_notice_vs_deduction_cents", "board_disposition",
            "underlying_rate_overcharge_merits_adjudicated",
            "carrier_refund_received_independently_verified",
            "original_twelve_bols_tariffs_or_bank_receipts_acquired",
            "original_pdf_pages_visually_verified", "decision_reported_bol_rows",
        })
        self.assertEqual((e["original_pdf_pages"],
                          e["board_reported_initial_overcharge_notices"],
                          e["original_claims_reportedly_resolved"],
                          e["added_claims_in_same_proceeding"],
                          e["remaining_appealed_bols"],
                          e["decision_bol_table_one_based_page"]), (8, 74, 67, 5, 12, 3))
        self.assertEqual(74 - 67 + 5, e["remaining_appealed_bols"])
        self.assertEqual(e["board_disposition"],
                         "REVERSED_GOVERNMENT_OVERCHARGE_DEDUCTIONS_AS_UNTIMELY")
        self.assertIs(e["underlying_rate_overcharge_merits_adjudicated"], False)
        self.assertIs(e["carrier_refund_received_independently_verified"], False)
        self.assertIs(e["original_twelve_bols_tariffs_or_bank_receipts_acquired"], False)
        self.assertEqual(e["original_pdf_pages_visually_verified"], [3, 7, 8])
        expected_bols = [
            ("W45QQ90009822", 1793654, "2005-01-20", 1793654, "2008-06-16"),
            ("W45QQ90009825", 1314805, "2005-01-20", 1314805, "2008-06-16"),
            ("W45QQ90009832", 2194247, "2005-02-11", 2194247, "2008-10-15"),
            ("W45QQ90009833", 878744, "2005-02-02", 878744, "2008-04-15"),
            ("W45QQ90009838", 438849, "2005-02-11", 438849, "2008-04-15"),
            ("W45QQ90009856", 877698, "2005-02-11", 877698, "2008-04-15"),
            ("W45QQ90009858", 436990, "2005-02-11", 436990, "2008-04-15"),
            ("W67G230008416", 330460, "2004-01-27", 330460, "2008-10-10"),
            ("W67G230008417", 479879, "2004-02-05", 479879, "2008-10-10"),
            ("W5CQRF0017135", 466531, "2004-02-09", 466531, "2008-10-10"),
            ("W45QQ90006106", 1207383, "2004-03-01", 1197902, "2008-10-31"),
            ("W45QQ90006013", 3342164, "2004-02-06", 3325916, "2008-10-31"),
        ]
        rows = e["decision_reported_bol_rows"]
        self.assertEqual(len(rows), 12)
        for row in rows:
            self.assertEqual(set(row), {"bol_reference", "alleged_overcharge_cents",
                                        "bill_paid_on", "treasury_deduction_cents",
                                        "treasury_deducted_on"})
            paid, deducted = (datetime.fromisoformat(row["bill_paid_on"]),
                              datetime.fromisoformat(row["treasury_deducted_on"]))
            self.assertGreater(deducted, paid.replace(year=paid.year + 3))
        self.assertEqual([
            (r["bol_reference"], r["alleged_overcharge_cents"], r["bill_paid_on"],
             r["treasury_deduction_cents"], r["treasury_deducted_on"]) for r in rows
        ], expected_bols)
        self.assertEqual(len({r["bol_reference"] for r in rows}), 12)
        self.assertEqual(sum(r["alleged_overcharge_cents"] for r in rows), 13761404)
        self.assertEqual(sum(r["treasury_deduction_cents"] for r in rows), 13735675)
        self.assertEqual((e["sum_reported_overcharge_notices_cents"],
                          e["sum_treasury_deductions_cents"],
                          e["gap_notice_vs_deduction_cents"]), (13761404, 13735675, 25729))

        # CBCA 3467-RATE has conflicting amounts within its ORIGINAL decision:
        # p.5 demand $339,895.73; p.6 operative no-indebtedness $339,895.75.
        # Neither amount is a cash refund or verified current customer error.
        t = pack["sources"][5]
        self.assertEqual(t["source_review_status"],
                         "ORIGINAL_CBCA_PDF_TEXT_REVIEWED_PAGES_4_5_6_VISUAL_2026_10_27")
        self.assertEqual(t["reported_amount_semantics"],
                         "BOARD_NO_INDEBTEDNESS_AMOUNT_NOT_CASH_AWARD_BODY_AND_DECISION_DIFFER_BY_2_CENTS")
        x = t["decision_evidence"]
        self.assertEqual(set(x), {
            "original_pdf_pages", "visually_reviewed_pages_one_based",
            "gsa_paid_detention_shipments_2010", "gsa_paid_detention_shipments_2011",
            "gsa_paid_detention_shipments_total",
            "gsa_retroactively_allowed_first_shipment_invoices",
            "gsa_challenged_paid_invoice_count",
            "government_repayment_demand_body_cents",
            "board_no_indebtedness_decision_cents",
            "within_original_decision_amount_discrepancy_cents",
            "gsa_detention_rule", "gsa_detention_rule_historical_effective_date",
            "board_disposition", "actual_prior_gsa_detention_payments_reported",
            "government_collected_disputed_recoupment_verified",
            "new_carrier_refund_received_verified",
            "original_79_bols_invoices_tariff_and_payment_receipts_acquired",
            "independently_scored_customer_invoice_error_count",
        })
        self.assertEqual(x["original_pdf_pages"], 6)
        self.assertEqual(x["visually_reviewed_pages_one_based"], [4, 5, 6])
        self.assertEqual((x["gsa_paid_detention_shipments_2010"],
                          x["gsa_paid_detention_shipments_2011"],
                          x["gsa_paid_detention_shipments_total"],
                          x["gsa_retroactively_allowed_first_shipment_invoices"],
                          x["gsa_challenged_paid_invoice_count"]), (4, 75, 79, 9, 70))
        self.assertEqual(x["gsa_paid_detention_shipments_2010"] +
                         x["gsa_paid_detention_shipments_2011"],
                         x["gsa_paid_detention_shipments_total"])
        self.assertEqual(x["gsa_retroactively_allowed_first_shipment_invoices"] +
                         x["gsa_challenged_paid_invoice_count"],
                         x["gsa_paid_detention_shipments_total"])
        self.assertEqual((x["government_repayment_demand_body_cents"],
                          x["board_no_indebtedness_decision_cents"],
                          x["within_original_decision_amount_discrepancy_cents"]),
                         (33989573, 33989575, 2))
        self.assertEqual(x["board_no_indebtedness_decision_cents"] -
                         x["government_repayment_demand_body_cents"],
                         x["within_original_decision_amount_discrepancy_cents"])
        self.assertEqual(x["gsa_detention_rule"], "STOS_100_D_ITEM_325")
        self.assertIsNone(x["gsa_detention_rule_historical_effective_date"])
        self.assertEqual(x["board_disposition"],
                         "GSA_RECOUPMENT_NOTICES_INVALID_CARRIER_NOT_INDEBTED")
        self.assertIs(x["actual_prior_gsa_detention_payments_reported"], True)
        for field in ("government_collected_disputed_recoupment_verified",
                      "new_carrier_refund_received_verified",
                      "original_79_bols_invoices_tariff_and_payment_receipts_acquired"):
            self.assertIs(x[field], False)
        self.assertEqual(x["independently_scored_customer_invoice_error_count"], 0)

        controls = pack["synthetic_negative_controls"]
        self.assertEqual(len(controls), 17)
        self.assertEqual(len({x["id"] for x in controls}), 17)
        self.assertEqual(controls[-1]["id"], "SYNTH_CBCA_JFC_TIME_BARRED_UNPAID_INVOICE_PROMOTED_TO_RATE_OVERCHARGE")
        for control in controls:
            self.assertEqual(set(control), {"id", "kind", "actual_independent_customer_outcome",
                                            "expected"})
            self.assertTrue(control["id"].startswith("SYNTH_"))
            self.assertEqual(control["kind"], "SYNTHETIC")
            self.assertIsNone(control["actual_independent_customer_outcome"])
            self.assertEqual(control["expected"], "REJECT_UNSUPPORTED_SOURCE_PROMOTION")

    def test_source_hold_scope_and_original_upstream_identity(self):
        self._assert_contract(self._pack())

    def test_poisoned_agreement_cash_invoice_rights_and_nested_claims_rejected(self):
        pack = self._pack()
        for index, key, spoofed in (
            (0, "reported_amount_cents", 130000000000),
            (1, "publisher_outcome_scope", "PUBLISHER_REPORTS_PAID_AGGREGATE_SETTLEMENT"),
            (1, "independent_actual_settlement_cash_receipt_verified", True),
            (3, "publisher_outcome_scope", "ADJUDICATED_CUSTOMER_OVERCHARGE"),
            (3, "reported_amount_cents", 0),
            (2, "reported_amount_cents", 1554909),
            (2, "publisher_outcome_scope", "CARRIER_REFUND_RECEIVED"),
            (0, "original_publisher_response_sha256", "fake-original-bytes"),
            (0, "source_specific_commercial_rights_verified", True),
            (0, "actual_customer_invoice_error_label", "TRUE_POSITIVE"),
            (0, "verified_retally_customer_recovery_cents", 1300000000),
            (0, "bank_receipt_sha256", "unsupported-new-field"),
        ):
            bad = json.loads(json.dumps(pack))
            bad["sources"][index][key] = spoofed
            with self.subTest(spoofed=key), self.assertRaises(AssertionError):
                self._assert_contract(bad)

    def test_cbca_6578_decision_unpaid_refund_and_unevaluated_108_controls(self):
        baseline = self._pack()
        for key, forged in (
            ("government_notices_total", 7),
            ("appealed_notices", 115),
            ("other_notices_disposition", "ALL_108_REFUNDED"),
            ("carrier_paid_gsa_disputed_notices_cents", 1554909),
            ("carrier_refund_received_independently_verified", True),
            ("underlying_original_tenders_gbls_or_bank_receipts_acquired", True),
        ):
            poisoned = json.loads(json.dumps(baseline))
            poisoned["sources"][2]["decision_evidence"][key] = forged
            with self.subTest(forged=key), self.assertRaises(AssertionError):
                self._assert_contract(poisoned)

    def test_cbca_1317_rejects_bol_amount_count_merits_and_cash_spoofing(self):
        baseline = self._pack()
        changes = (
            ("board_reported_initial_overcharge_notices", 12),
            ("remaining_appealed_bols", 74),
            ("sum_treasury_deductions_cents", 13761404),
            ("gap_notice_vs_deduction_cents", 0),
            ("underlying_rate_overcharge_merits_adjudicated", True),
            ("carrier_refund_received_independently_verified", True),
            ("original_twelve_bols_tariffs_or_bank_receipts_acquired", True),
            ("original_pdf_pages_visually_verified", list(range(1, 9))),
        )
        for key, forged in changes:
            bad = json.loads(json.dumps(baseline))
            bad["sources"][4]["decision_evidence"][key] = forged
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self._assert_contract(bad)
        for key, forged in (("alleged_overcharge_cents", 0),
                            ("treasury_deduction_cents", 1207383),
                            ("treasury_deducted_on", "2006-10-31")):
            bad = json.loads(json.dumps(baseline))
            bad["sources"][4]["decision_evidence"]["decision_reported_bol_rows"][10][key] = forged
            with self.subTest(table_cell=key), self.assertRaises(AssertionError):
                self._assert_contract(bad)
        bad = json.loads(json.dumps(baseline))
        bad["sources"][4]["claim_paid_bank_receipt_sha256"] = "unsupported"
        with self.assertRaises(AssertionError):
            self._assert_contract(bad)


    def test_cbca_8051_denial_accounting_timeline_and_no_cash_promotion(self):
        original = self._pack()
        for key, forged in (
            ("initial_approval_equates_to_government_payment", True),
            ("documented_government_receipt_of_2019_resubmission", True),
            ("board_review_within_six_months", False),
            ("separate_underlying_payment_denial_claim_timely", True),
            ("missing_appeal_notice_actual_prejudice_proven", True),
            ("actual_government_payment_independently_verified", True),
            ("original_invoice_ticket_bol_and_bank_bytes_acquired", True),
            ("reported_unpaid_invoice_amount_cents", 0),
            ("original_pdf_pages", 6),
            ("original_pdf_pages_visually_verified", [1, 2, 13]),
            ("current_customer_billing_error_ground_truth", "VERIFIED_OVERCHARGE"),
            ("applicable_historical_tariff_effective_date", "2018-05-31"),
            ("prepayment_audit_payment_denied_on", "2023-10-02"),
            ("board_decision", "CARRIER_CASH_RECOVERED"),
            ("notice_contained_regulatorily_required_appeal_rights", True),
        ):
            bad = json.loads(json.dumps(original))
            bad["sources"][3]["decision_evidence"][key] = forged
            with self.subTest(field=key), self.assertRaises(AssertionError):
                self._assert_contract(bad)
        for key, forged in (("reported_amount_cents", 1459568),
                            ("publisher_outcome_scope", "VERIFIED_SHIPPER_OVERCHARGE"),
                            ("source_specific_commercial_rights_verified", True)):
            bad = json.loads(json.dumps(original))
            bad["sources"][3][key] = forged
            with self.subTest(outside_field=key), self.assertRaises(AssertionError):
                self._assert_contract(bad)
        bad = json.loads(json.dumps(original))
        bad["sources"][3]["decision_evidence"]["bank_receipt_sha256"] = "invented"
        with self.assertRaises(AssertionError):
            self._assert_contract(bad)

    def test_cbca_3467_conflicting_decision_amount_and_no_cash_promotion(self):
        original = self._pack()
        for key, replacement in (
            ("gsa_paid_detention_shipments_total", 70),
            ("gsa_challenged_paid_invoice_count", 79),
            ("government_repayment_demand_body_cents", 33989575),
            ("board_no_indebtedness_decision_cents", 33989573),
            ("within_original_decision_amount_discrepancy_cents", 0),
            ("new_carrier_refund_received_verified", True),
            ("government_collected_disputed_recoupment_verified", True),
            ("original_79_bols_invoices_tariff_and_payment_receipts_acquired", True),
            ("independently_scored_customer_invoice_error_count", 70),
            ("gsa_detention_rule_historical_effective_date", "2011-01-01"),
        ):
            poisoned = json.loads(json.dumps(original))
            poisoned["sources"][5]["decision_evidence"][key] = replacement
            with self.subTest(field=key), self.assertRaises(AssertionError):
                self._assert_contract(poisoned)
        for key, replacement in (("reported_amount_cents", 33989573),
                                 ("publisher_outcome_scope", "CARRIER_REFUND_RECEIVED"),
                                 ("verified_retally_customer_recovery_cents", 33989575)):
            poisoned = json.loads(json.dumps(original))
            poisoned["sources"][5][key] = replacement
            with self.subTest(field=key), self.assertRaises(AssertionError):
                self._assert_contract(poisoned)


class UnifiedResearchLabTests(unittest.TestCase):
    def test_main_gao_adjudication_source_reconciliation_hold(self):
        # Pinned 2026-10-27 protected-main locators: historic rulings, NOT invoice custody.
        sources = (
            "https://www.gao.gov/products/b-213717-0",
            "https://www.gao.gov/products/b-192856",
            "https://www.gao.gov/products/b-191258",
        )
        self.assertEqual(len(set(sources)), 3)
        for url in sources:
            self.assertIn(url, SEEDS["freightrecovery"])
            self.assertEqual(safe_url(url), url)
            ledger, added = merge_sources(
                ledger_from([]), "freightrecovery", [url, url], "2026-10-27"
            )
            self.assertEqual(added, 1)
            self.assertEqual(len(ledger["entries"]), 1)
            for key in ("commercial_reuse_authorized", "independent_ground_truth",
                        "independent_payment_verified", "recovered_cash_verified"):
                self.assertFalse(ledger["entries"][0][key])
        # Main's obsolete restaurant-inspection locator must not be reintroduced.
        self.assertNotIn("https://data.cityofnewyork.us/d/43nn-pn8j",
                         SEEDS["permitplate"])

    def test_gao_b215958_source_scope_dedup_and_unknowns(self):
        fixture = Path(__file__).with_name("fixtures") / "gao_b215958_source_v1.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertEqual(data["status"], "SOURCE_BOUND_DECISION_LEVEL_CANDIDATE_NOT_HELD_OUT")
        source = data["source"]
        url = "https://www.gao.gov/products/b-215958"
        self.assertEqual(source["original_record_url"], url)
        self.assertEqual(source["original_report_url"],
                         "https://www.gao.gov/assets/b-215958-125766.pdf")
        self.assertEqual(source["decision_date"], "1984-12-05")
        self.assertEqual(source["superseding_reconsideration_url"],
                         "https://www.gao.gov/products/b-215958-2")
        self.assertEqual(source["superseding_reconsideration_date"], "1986-02-18")
        self.assertEqual(source["decision_page_for_disposition"], 3)
        self.assertIsNone(source["source_bytes_sha256"])
        self.assertFalse(source["source_bytes_acquired"])
        self.assertFalse(source["commercial_use_of_engine_input_approved"])
        population = data["population"]
        self.assertEqual(population["challenged_government_bills_of_lading"], 55)
        self.assertEqual(population["decision_reversals_with_recorded_numbered_seals"], 53)
        self.assertEqual(population["remainder_cases_with_unresolved_disposition"], 2)
        self.assertEqual(population["decision_outcome"],
                         "GAO_1984_INITIAL_REVERSAL_SUBSEQUENTLY_OVERRULED_IN_1986")
        self.assertFalse(population["per_bill_of_lading_labels_available"])
        self.assertIsNone(population["independently_confirmed_refunds_received"])
        self.assertIsNone(population["independently_confirmed_carrier_overcharge_amount_cents"])
        self.assertFalse(data["limits"]["independent_accuracy_scoring_permitted"])
        self.assertEqual(data["limits"]["realized_retally_recovered_cash_cents"], 0)
        self.assertEqual(len(data["controls"]), 2)
        self.assertEqual(data["controls"][0]["expected"],
                         "1984_INITIAL_FAVORABLE_RULING_NOT_FINAL_1986_WRITTEN_REQUEST_REQUIRED")
        self.assertTrue(all(x["synthetic"] for x in data["controls"]))
        self.assertTrue(all(x["actual_refund_received_cents"] is None
                            and x["actual_customer_overcharge_cents"] is None
                            for x in data["controls"]))
        self.assertIn(url, SEEDS["freightrecovery"])
        self.assertEqual(safe_url(url), url)
        single, added = merge_sources(ledger_from([]), "freightrecovery",
                                      [url, url], "2026-10-23")
        self.assertEqual(added, 1)
        self.assertEqual(len(single["entries"]), 1)
        self.assertFalse(single["entries"][0]["independent_ground_truth"])
        self.assertFalse(single["entries"][0]["commercial_reuse_authorized"])
        self.assertFalse(single["entries"][0]["recovered_cash_verified"])

    def test_gao_b215958_research_manifest_hash_and_negative_control(self):
        fixture = Path(__file__).with_name("fixtures") / "gao_b215958_source_v1.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(
            data["manifest_hash_contract"],
            "RESEARCH_AUTHORED_MANIFEST_SHA256_CANONICAL_SORTED_JSON_EXCLUDING_SELF_NOT_ORIGINAL_PUBLISHER_BYTES",
        )
        self.assertEqual(data["data_quality"]["publisher_original_review_date"], "2026-10-23")
        self.assertIsNone(data["source"]["source_bytes_sha256"])
        self.assertFalse(data["source"]["source_bytes_acquired"])
        self.assertFalse(data["source"]["commercial_use_of_engine_input_approved"])

        def authored_digest(obj):
            canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        author_fields = {k: v for k, v in data.items() if k != "manifest_sha256"}
        self.assertEqual(data["manifest_sha256"], authored_digest(author_fields))
        mutated = json.loads(json.dumps(author_fields))
        mutated["population"]["decision_reversals_with_recorded_numbered_seals"] = 55
        self.assertNotEqual(data["manifest_sha256"], authored_digest(mutated))
        self.assertEqual(
            mutated["population"]["decision_reversals_with_recorded_numbered_seals"]
            + data["population"]["remainder_cases_with_unresolved_disposition"],
            57,
        )

    def test_gao_b165091_historical_tariff_contrast_is_labeled_not_laundered(self):
        """GAO gives a numeric adjudication, not a customer invoice truth set."""
        case = json.loads(
            (Path(__file__).with_name("fixtures") / "gao_b165091_source_v1.json")
            .read_text(encoding="utf-8")
        )
        original = {k: v for k, v in case.items() if k != "manifest_sha256"}
        digest = hashlib.sha256(json.dumps(
            original, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        self.assertEqual(case["manifest_sha256"], digest)
        self.assertEqual(case["source"]["decision_date"], "1969-01-03")
        self.assertEqual(case["source"]["historical_tariff"].split(",")[-1].strip(), "item 2400")
        self.assertFalse(case["source"]["source_bytes_acquired"])
        self.assertIsNone(case["source"]["source_bytes_sha256"])
        self.assertFalse(case["source"]["commercial_use_of_engine_input_approved"])
        self.assertFalse(case["cohort"]["independent_holdout_against_engine_training_verified"])
        self.assertFalse(case["limits"]["independent_invoice_error_accuracy_scoring_permitted"])
        adjudicated, conditional = case["adjudications"]
        self.assertTrue(adjudicated["decision_complete"])
        self.assertEqual(adjudicated["adjudicated_sustained_deduction_cents"], 17980)
        self.assertEqual(adjudicated["original_paid_exclusive_use_charge_cents"], 45050)
        self.assertFalse(adjudicated["contemporaneous_written_exclusive_use_order_verified"])
        self.assertIsNone(adjudicated["independently_verified_refund_received_cents"])
        self.assertFalse(conditional["decision_complete"])
        self.assertEqual(conditional["original_claimed_additional_charges_cents"], 39324)
        self.assertIsNone(conditional["finally_allowed_amount_cents"])
        self.assertTrue(all(c["synthetic"] and c["real_invoice_error_cents"] is None
                            for c in case["controls"]))
        self.assertNotEqual(case["source"]["historical_tariff"],
                            case["contrasting_source"]["historical_tariff"])
        mutated = json.loads(json.dumps(original))
        mutated["adjudications"][0]["adjudicated_sustained_deduction_cents"] = 0
        self.assertNotEqual(case["manifest_sha256"], hashlib.sha256(
            json.dumps(mutated, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
        ).hexdigest())
        url = case["source"]["original_record_url"]
        self.assertIn(url, SEEDS["freightrecovery"])
        doc, added = merge_sources(ledger_from([]), "freightrecovery",
                                   [url, url, case["contrasting_source"]["url"]],
                                   "2026-10-24")
        self.assertEqual(added, 2)
        self.assertEqual(len(doc["entries"]), 2)
        self.assertTrue(all(not x["commercial_reuse_authorized"]
                            and not x["independent_ground_truth"]
                            and not x["recovered_cash_verified"]
                            for x in doc["entries"]))

    def test_freight_is_primary_over_ten_five_minute_discovery_slots(self):
        selected = [current_engine(NOW + timedelta(minutes=5 * i)) for i in range(10)]
        self.assertEqual(selected.count("freightrecovery"), 7)
        self.assertEqual({name: selected.count(name) for name in ENGINES},
                         {"freightrecovery": 7, "permitplate": 1,
                          "capturebrief": 1, "recoveryos": 1})
        # Consecutive primary research cycles are never separated by more
        # than one secondary discovery cycle in the planned rotation.
        twenty = [current_engine(NOW + timedelta(minutes=5 * i)) for i in range(20)]
        self.assertTrue(all(a == "freightrecovery" or b == "freightrecovery"
                            for a, b in zip(twenty, twenty[1:])))
        with self.assertRaises(ResearchError):
            current_engine(NOW.replace(tzinfo=None))

    def test_offline_populates_only_rights_held_real_source_pointers(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            for engine in ENGINES:
                result = run(engine=engine, live=False, ledger=ledger, now=NOW)
                self.assertFalse(result["network_enabled"])
                self.assertEqual(result["customer_contact_actions"], 0)
            records = read_ledger(ledger)["entries"]
            self.assertGreaterEqual(len(records), 6)
            self.assertTrue(all(x["rights_state"].startswith("UNVERIFIED") for x in records))
            self.assertTrue(all(not x["commercial_reuse_authorized"] for x in records))
            self.assertTrue(all(not x["recovered_cash_verified"] for x in records))
            self.assertTrue(all(not x["independent_ground_truth"] for x in records))

    def test_repeat_preserves_first_seen_and_exact_file_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            a = run(engine="freightrecovery", live=False, ledger=ledger, now=NOW)
            self.assertGreater(a["new_leads"], 0)
            original_first_seen = {
                item["id"]: item["first_seen"]
                for item in read_ledger(ledger)["entries"]
            }
            # Seeds can exceed the configured 40-new-lead safety cap. An
            # immediate second offline run must not be mistaken for an
            # idempotence failure while the remaining seed batch is pending.
            # All calls here use live=False: zero external provider requests.
            from freight.unified_research_lab import MAX_NEW_PER_RUN
            max_cycles = (len(SEEDS["freightrecovery"]) // MAX_NEW_PER_RUN) + 2
            for cycle in range(1, max_cycles + 1):
                result = run(engine="freightrecovery", live=False, ledger=ledger,
                             now=NOW + timedelta(days=cycle))
                if result["new_leads"] == 0:
                    break
            else:
                self.fail("BOUNDED_OFFLINE_SEED_REPLAY_NEVER_SETTLED")
            contents = ledger.read_bytes()
            final_first_seen = {
                item["id"]: item["first_seen"]
                for item in read_ledger(ledger)["entries"]
            }
            for source_id, first_seen in original_first_seen.items():
                self.assertEqual(final_first_seen[source_id], first_seen)
            again = run(engine="freightrecovery", live=False, ledger=ledger,
                        now=NOW + timedelta(days=cycle + 1))
            self.assertEqual(again["new_leads"], 0)
            self.assertEqual(ledger.read_bytes(), contents)

    def test_one_canonical_source_can_feed_multiple_engines(self):
        link = "https://catalog.data.gov/dataset/real-example"
        doc, count = merge_sources(ledger_from([]), "freightrecovery",
                                   [link], "2026-10-22")
        self.assertEqual(count, 1)
        later, count2 = merge_sources(doc, "recoveryos", [link], "2026-10-23")
        self.assertEqual(count2, 0)
        self.assertEqual(len(later["entries"]), 1)
        self.assertEqual(later["entries"][0]["first_seen"], "2026-10-22")
        self.assertEqual(later["entries"][0]["engines"],
                         ["freightrecovery", "recoveryos"])

    def test_source_flags_cannot_be_forged_even_if_digest_recomputed(self):
        doc = ledger_from([source_record(
            "https://www.gao.gov/products/b-160344", "freightrecovery", "2026-10-22"
        )])
        doc["entries"][0]["independent_ground_truth"] = True
        from freight.unified_research_lab import digest
        doc["entries_sha256"] = digest(doc["entries"])
        with self.assertRaises(ResearchError):
            validate_ledger(doc)

    def test_rows_cannot_hide_document_bytes_or_unknown_fields(self):
        doc = ledger_from([source_record(
            "https://sam.gov/opportunities", "capturebrief", "2026-10-22"
        )])
        doc["entries"][0]["private_invoice_bytes"] = "secret"
        with self.assertRaises(ResearchError):
            validate_ledger(doc)

    def test_untrusted_external_links_blocked(self):
        for url in (
            "http://catalog.data.gov/dataset/x",
            "https://catalog.data.gov@127.0.0.1/dataset/x",
            "https://127.0.0.1/dataset/x",
            "https://catalog.data.gov/dataset/x?token=private",
            "https://catalog.data.gov/../private",
            "https://evil.invalid/records/3",
            "https://catalog.data.gov/%0Aevil",
            "https://github.com/owner/repo#fragment",
        ):
            with self.subTest(url=url), self.assertRaises(ResearchError):
                safe_url(url)

    def test_feed_parses_canonical_metadata_and_not_raw_rows(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.github.com" in url:
                return {"items": [{"html_url": "https://github.com/owner/public-data",
                                   "name": "freight-invoice-source",
                                   "description": "ignore copied PII"},
                                  {"html_url": "https://internal.example/repo"}]}
            return {"hits": {"hits": [{"id": 12345, "metadata": {"title": "LTL freight tariff dataset", "creators": ["X"]}}]}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("freightrecovery", fetch=fake)
        self.assertEqual(errors, [])
        self.assertIn("https://github.com/owner/public-data", urls)
        self.assertIn("https://zenodo.org/records/12345", urls)
        self.assertTrue(all("@" not in x and "private" not in x for x in urls))

    def test_nyc_official_catalog_uses_dataset_ids_only(self):
        def row(ident, title):
            return {"resource": {"id": ident, "name": title,
                                 "provenance": "official", "type": "dataset",
                                 "parent_fxf": []},
                    "metadata": {"domain": "data.cityofnewyork.us"}}

        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.us.socrata.com" in url:
                params = parse_qs(urlsplit(url).query)
                self.assertEqual(params.get("provenance"), ["official"])
                self.assertEqual(params.get("only"), ["dataset"])
                self.assertEqual(params.get("domains"), ["data.cityofnewyork.us"])
                community = row("qnmk-7xra", "DOB NOW: Build – Approved Permits")
                community["resource"]["provenance"] = "community"
                return {"results": [
                    row("abcd-1234", "DOHMH Restaurant Inspection"),
                    row("rbx6-tga4", "DOB NOW: Build – Approved Permits"),
                    row("../secret", "DOB NOW: Build – Approved Permits"),
                    community,
                ]}
            if "api.github.com" in url:
                return {"items": []}
            return {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://data.cityofnewyork.us/d/rbx6-tga4"])

    def test_socrata_original_publisher_identity_must_be_explicit(self):
        original = {
            "resource": {
                "id": "rbx6-tga4", "name": "DOB NOW: Build – Approved Permits",
                "provenance": "official", "type": "dataset", "parent_fxf": [],
            },
            "metadata": {"domain": "data.cityofnewyork.us"},
        }
        self.assertTrue(original_nyc_catalog_entry(original))
        variations = (
            {"resource": dict(original["resource"], provenance="community"),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], type="filter"),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], parent_fxf=["rbx6-tga4"]),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], provenance=None),
             "metadata": original["metadata"]},
            {"resource": original["resource"],
             "metadata": {"domain": "data.evil.invalid"}},
            {"resource": original["resource"], "metadata": {}},
            {"resource": dict(original["resource"], parent_fxf=None),
             "metadata": original["metadata"]},
            {"resource": dict(original["resource"], name="DOHMH Restaurant Inspection"),
             "metadata": original["metadata"]},
            {},
            None,
        )
        for row in variations:
            with self.subTest(source=row):
                self.assertFalse(original_nyc_catalog_entry(row))

    def test_data_gov_v4_is_not_used_without_a_production_api_key(self):
        seen = []
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            seen.append(url)
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            scan("capturebrief", fetch=fake)
        self.assertFalse(any("api.gsa.gov" in url for url in seen))
        self.assertFalse(any("catalog.data.gov/api/3/" in url for url in seen))

    def test_data_gov_v4_only_admits_public_dataset_metadata(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.gsa.gov" in url:
                return {"results": [
                    {"slug": "public-data-2026", "dcat": {"accessLevel": "public"},
                     "description": "contains arbitrary names and private details"},
                    {"slug": "restricted-data-2026", "dcat": {"accessLevel": "restricted public"}},
                    {"slug": "../unsafe", "dcat": {"accessLevel": "public"}},
                ]}
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": "fake-test-key"}):
            urls, errors = scan("recoveryos", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://catalog.data.gov/dataset/public-data-2026"])

    def test_partial_provider_failure_is_disclosed_but_all_fail_closed(self):
        def partial(url):
            if "retally-unified-research-scout" in url:
                engine = parse_qs(urlsplit(url).query)["engine"][0]
                return {"engine": engine,
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "zenodo.org" in url:
                raise ResearchError("HTTP_STATUS_503")
            if "api.us.socrata.com" in url:
                return {"results": []}
            return {"items": []}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=partial)
        self.assertEqual(urls, [])
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("HTTP_STATUS_503" in x for x in errors))
        def all_failed(_):
            raise ResearchError("OFFLINE")
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            with self.assertRaisesRegex(ResearchError, "ALL_PUBLIC_FEEDS_UNAVAILABLE"):
                scan("recoveryos", fetch=all_failed)

    def test_independent_scout_validated_metadata_is_prioritized(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                return {"engine": "recoveryos",
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": [
                            {"url": "https://zenodo.org/records/12345",
                             "private_account": "never copied"},
                            {"url": "https://github.com/public/recon-dataset"},
                        ]}
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("recoveryos", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(urls, ["https://zenodo.org/records/12345",
                                "https://github.com/public/recon-dataset"])
        self.assertNotIn("private_account", str(urls))

    def test_independent_scout_rejects_invalid_or_cross_engine_source(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                return {"engine": "freightrecovery",
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": [{"url": "https://evil.invalid/private"}]}
            return {"items": []} if "api.github.com" in url else {"hits": {"hits": []}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            urls, errors = scan("permitplate", fetch=fake)
        self.assertEqual(urls, [])
        self.assertTrue(any("UNTRUSTED_SCOUT_FEED" in e for e in errors))

    def test_corrupt_saved_ledger_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            path.write_text('{"entries":[]}', encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(ResearchError):
                run(engine="capturebrief", live=False, ledger=path, now=NOW)
            self.assertEqual(path.read_bytes(), before)


    def test_one_git_run_mirrors_all_four_lanes_and_preserves_scout_first_seen(self):
        observed = []
        urls = {
            "freightrecovery": "https://www.gao.gov/products/b-160344",
            "permitplate": "https://data.cityofnewyork.us/d/w9ak-ipjd",
            "capturebrief": "https://sam.gov/opportunities",
            "recoveryos": "https://www.penninecare.nhs.uk/download_file/5855/277",
        }
        def fake(url):
            self.assertTrue(url.startswith("https://retally-unified-research-scout."))
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            observed.append(engine)
            return {"engine": engine, "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": [{"url": urls[engine], "first_seen": "2026-10-22",
                                 "extra_personal_note": "never copied"}]}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            now = NOW + timedelta(days=1)
            out = mirror_scout_all(ledger=path, now=now, fetch=fake)
            self.assertEqual(observed, list(ENGINES))
            self.assertEqual(out["new_leads"], 4)
            self.assertEqual(out["feed_errors"], [])
            before = path.read_bytes()
            again = mirror_scout_all(ledger=path, now=now, fetch=fake)
            self.assertEqual(again["new_leads"], 0)
            self.assertEqual(before, path.read_bytes())
            records = read_ledger(path)["entries"]
            self.assertEqual(len(records), 4)
            self.assertTrue(all(row["first_seen"] == "2026-10-22" for row in records))
            self.assertTrue(all(row["commercial_reuse_authorized"] is False for row in records))
            self.assertTrue(all(row["independent_ground_truth"] is False for row in records))
            self.assertNotIn("extra_personal_note", path.read_text())

    def test_mirror_quarantines_failed_or_future_dated_lane_without_overwriting_ledger(self):
        def fake(url):
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            if engine == "permitplate":
                return {"engine": "recoveryos", "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if engine == "capturebrief":
                return {"engine": engine, "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": [{"url": "https://sam.gov/opportunities",
                                     "first_seen": "2099-12-01"}]}
            return {"engine": engine, "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "leads.json"
            run(engine="freightrecovery", live=False, ledger=path, now=NOW)
            before = path.read_bytes()
            report = mirror_scout_all(ledger=path, now=NOW, fetch=fake)
            self.assertEqual(report["new_leads"], 0)
            self.assertEqual(len(report["feed_errors"]), 2)
            self.assertTrue(any("UNTRUSTED_SCOUT_FEED" in e for e in report["feed_errors"]))
            self.assertTrue(any("SCOUT_OBSERVATION_DATE_INVALID" in e for e in report["feed_errors"]))
            self.assertEqual(before, path.read_bytes())


    def test_permitplate_searches_are_construction_not_restaurant(self):
        self.assertTrue(all("restaurant" not in q.lower() for q in SEARCHES["permitplate"]))
        self.assertTrue(any("permit" in q.lower() for q in SEARCHES["permitplate"]))

    def test_permitplate_official_dob_seed_replaces_restaurant_and_stays_rights_held(self):
        # Official NYC DOB original source, not the DOHMH restaurant-inspection seed.
        official = "https://data.cityofnewyork.us/d/rbx6-tga4"
        applications = "https://data.cityofnewyork.us/d/w9ak-ipjd"
        bis_issued = "https://data.cityofnewyork.us/d/ipu4-2q9a"
        self.assertEqual(set(SEEDS["permitplate"]), {official, applications, bis_issued, "https://data.cityofnewyork.us/d/dm9a-ab7w", "https://data.cityofnewyork.us/d/kfp4-dz4h", "https://data.cityofnewyork.us/d/xxbr-ypig"})
        self.assertNotIn("https://data.cityofnewyork.us/d/43nn-pn8j", SEEDS["permitplate"])
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "permit_sources.json"
            receipt = run(engine="permitplate", live=False, ledger=ledger, now=NOW)
            rows = read_ledger(ledger)["entries"]
            self.assertEqual(receipt["new_leads"], 6)
            repeat = run(engine="permitplate", live=False, ledger=ledger,
                         now=NOW + timedelta(hours=1))
            self.assertEqual(repeat["new_leads"], 0)
            self.assertEqual({r["url"] for r in rows}, set(SEEDS["permitplate"]))
            self.assertEqual(receipt["approved_real_truth_cases"], 0)
            self.assertTrue(all(not r["commercial_reuse_authorized"]
                                and not r["independent_ground_truth"]
                                and not r["document_bytes_stored"] for r in rows))
        pack = json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_source_scope_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(pack["evaluation_family"],
                         "GOVERNMENT_PERMIT_SCORING_SOURCE_COVERAGE_ONLY")
        self.assertEqual(pack["real_issuance_cases_ingested"], 0)
        self.assertEqual(pack["acceptance_boundaries"]["independent_labels_count"], 0)
        self.assertEqual(pack["accuracy_evaluation"],
                         "NOT_ESTIMABLE_WITHOUT_INDEPENDENT_LABELS")
        source = next(x for x in pack["official_sources"] if x["dataset_id"] == "rbx6-tga4")
        self.assertEqual(source["official_url"], official)
        self.assertFalse(source["commercial_reuse_authorized"])
        self.assertFalse(source["independent_outcome_adjudicated"])
        self.assertIsNone(source["original_source_bytes_sha256"])
        bis_source = next(x for x in pack["official_sources"]
                          if x["dataset_id"] == "ipu4-2q9a")
        self.assertEqual(bis_source["official_url"], bis_issued)
        self.assertEqual(bis_source["coverage"], "BIS_ONLY_NOT_DOB_NOW")
        self.assertFalse(bis_source["commercial_reuse_authorized"])
        self.assertFalse(bis_source["independent_outcome_adjudicated"])
        self.assertIsNone(bis_source["original_source_bytes_sha256"])
        self.assertIn("bis_coverage_is_not_all_dob",
                      {c["id"] for c in pack["synthetic_negative_controls"]})
        # Existing approved excluded-scope v1 pack remains the canonical
        # evaluation pointer; this seed linkage does not create a second pack.
        excluded = json.loads((Path(__file__).with_name("fixtures") /
                              "nyc_dob_excluded_scope_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(excluded["real_permit_records_ingested"], 0)
        self.assertEqual(excluded["independent_outcome_labels"], 0)
        self.assertEqual(excluded["cross_dataset_join"], "UNVERIFIED")
        self.assertEqual(excluded["commercial_use"], "UNVERIFIED_NOT_APPROVED")
        self.assertEqual({s["official_url"] for s in excluded["companion_source_candidates"]},
                         set(SEEDS["permitplate"]) - {official, applications, bis_issued})
        self.assertEqual(len(pack["synthetic_negative_controls"]), 4)
        self.assertTrue(all(c["provenance_class"].startswith("SYNTHETIC")
                            and c["real_world_accuracy_label"] is None
                            for c in pack["synthetic_negative_controls"]))

    def test_permitplate_obvious_wrong_topic_is_excluded_but_history_unchanged(self):
        prior = source_record("https://github.com/owner/nyc-restaurant-inspections",
                              "permitplate", "2026-10-22")
        ledger = ledger_from([prior])
        revised, added = merge_sources(
            ledger, "permitplate",
            ["https://github.com/owner/nyc-restaurant-inspections-2026",
             "https://github.com/owner/NYC-DOB-Building-Permits"],
            "2026-10-23")
        self.assertEqual(added, 1)
        self.assertEqual(len(revised["entries"]), 2)
        self.assertIn(prior, revised["entries"])
        self.assertTrue(any("NYC-DOB-Building-Permits" in row["url"]
                            for row in revised["entries"]))


    def test_mirror_survives_one_malformed_provider_without_losing_other_lanes(self):
        urls = {
            "freightrecovery": "https://www.gao.gov/products/b-160344",
            "permitplate": "https://data.cityofnewyork.us/d/rbx6-tga4",
            "recoveryos": "https://www.penninecare.nhs.uk/download_file/5855/277",
        }
        def fetch(url):
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            if engine == "capturebrief":
                raise ValueError("untrusted provider text must not leak")
            return {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": [{"url": urls[engine], "first_seen": "2026-10-22"}]}
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            result = mirror_scout_all(ledger=ledger, now=NOW, fetch=fetch)
            self.assertEqual(result["new_leads"], 3)
            self.assertEqual(len(result["feed_errors"]), 1)
            self.assertEqual(result["feed_errors"][0],
                             "capturebrief:UNTRUSTED_SCOUT_RESPONSE_ValueError")
            self.assertNotIn("untrusted provider text", str(result))
            self.assertEqual(len(read_ledger(ledger)["entries"]), 3)
            self.assertEqual(result["third_party_documents_saved"], 0)
            self.assertEqual(result["customer_contact_actions"], 0)

    def test_json_provider_invalid_response_is_bounded_error_not_raw_body(self):
        from contextlib import nullcontext
        url = "https://api.github.com/search/repositories?q=metadata"
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def geturl(self):
                return url
            def read(self, limit):
                return b'{"not-a-valid-object":'
        with patch("freight.unified_research_lab.global_dns"):
            with patch("freight.unified_research_lab.build_opener") as opener:
                opener.return_value.open.return_value = nullcontext(Response())
                with self.assertRaisesRegex(ResearchError, "SOURCE_JSON_INVALID"):
                    get_json(url)




    def test_pagination_mirrors_all_pages_and_respects_40_new_source_budget(self):
        called = []
        def fake(url):
            query = parse_qs(urlsplit(url).query)
            engine = query["engine"][0]
            before = query.get("before", [None])[0]
            called.append((engine, before))
            data = {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
            if engine == "capturebrief":
                if before is None:
                    data["sources"] = [
                        {"url": f"https://github.com/synthetic-fixture/capture-dataset-{i:03d}",
                         "first_seen": "2026-10-22"}
                        for i in range(100)]
                    data["next_cursor"] = "250"
                elif before == "250":
                    data["sources"] = [
                        {"url": f"https://github.com/synthetic-fixture/capture-dataset-{i:03d}",
                         "first_seen": "2026-10-21"}
                        for i in range(100, 102)]
                    data["next_cursor"] = None
                else:
                    raise AssertionError("unexpected cursor")
            return data
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "sources.json"
            now = NOW + timedelta(days=1)
            outputs = [mirror_scout_all(ledger=ledger, now=now, fetch=fake)
                       for _ in range(3)]
            self.assertEqual([x["new_leads"] for x in outputs], [40,40,22])
            self.assertEqual(len(read_ledger(ledger)["entries"]), 102)
            self.assertEqual(outputs[-1]["per_engine"]["capturebrief"]["available"], 102)
            self.assertEqual(outputs[-1]["per_engine"]["capturebrief"]["pages_read"], 2)
            self.assertEqual(outputs[-1]["feed_errors"], [])
            self.assertEqual(called.count(("capturebrief", "250")), 3)
            self.assertTrue(all(row["rights_state"].startswith("UNVERIFIED")
                                for row in read_ledger(ledger)["entries"]))
            self.assertEqual(
                sorted({row["first_seen"] for row in read_ledger(ledger)["entries"]}),
                ["2026-10-21", "2026-10-22"])

    def test_pagination_invalid_cursor_quarantines_only_affected_lane(self):
        def fake(url):
            engine = parse_qs(urlsplit(url).query)["engine"][0]
            data = {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
            if engine == "capturebrief":
                data["sources"] = [
                    {"url": f"https://github.com/synthetic-fixture/invalid-cursor-{i:03d}",
                     "first_seen": "2026-10-22"} for i in range(100)]
                data["next_cursor"] = "1234bad"
            return data
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sources.json"
            result = mirror_scout_all(ledger=path, now=NOW, fetch=fake)
            self.assertEqual(result["new_leads"], 0)
            self.assertEqual(result["feed_errors"], ["capturebrief:SCOUT_CURSOR_INVALID"])
            self.assertEqual(result["per_engine"]["capturebrief"]["pages_read"], 0)
            self.assertEqual(read_ledger(path)["entries"], [])

    def test_pagination_six_page_ceiling_is_disclosed_not_silently_ignored(self):
        def fake(url):
            args = parse_qs(urlsplit(url).query)
            engine = args["engine"][0]
            before = args.get("before", [None])[0]
            data = {"engine": engine,
                    "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                    "sources": []}
            if engine == "recoveryos":
                index = 0 if before is None else 601 - int(before)
                if index < 0 or index >= 6:
                    raise AssertionError("page beyond configured limit")
                data["sources"] = [
                    {"url": f"https://github.com/synthetic-fixture/recovery-source-{index:02d}-{i:03d}",
                     "first_seen": "2026-10-22"} for i in range(100)]
                data["next_cursor"] = str(600-index)
            return data
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sources.json"
            report = mirror_scout_all(ledger=path, now=NOW, fetch=fake)
            self.assertIn("recoveryos:SCOUT_PAGE_CAP_REACHED", report["feed_errors"])
            self.assertTrue(report["per_engine"]["recoveryos"]["page_cap_reached"])
            self.assertEqual(report["per_engine"]["recoveryos"]["pages_read"], 6)
            self.assertEqual(report["per_engine"]["recoveryos"]["available"], 600)
            self.assertEqual(report["per_engine"]["recoveryos"]["new"], 40)
            self.assertEqual(len(read_ledger(path)["entries"]), 40)




    def test_public_publisher_topic_filter_discards_off_topic_metadata_per_lane(self):
        cases = (
            ("freightrecovery", "Freight invoice tariff dataset", "Baking and dining recipes"),
            ("permitplate", "NYC DOB NOW approved building permits",
             "NYC restaurant inspection permits"),
            ("capturebrief", "Federal solicitation contract awards",
             "Professional basketball boxscores"),
            ("recoveryos", "Accounts payable supplier invoice reconciliation",
             "Wildlife photography archive"),
        )
        for engine, good, bad in cases:
            for provider in ("github", "zenodo"):
                with self.subTest(engine=engine, provider=provider):
                    good_row = ({"name": "generic", "description": good}
                                if provider == "github" else {"metadata": {"title": good}})
                    bad_row = ({"name": "generic", "description": bad}
                               if provider == "github" else {"metadata": {"title": bad}})
                    self.assertTrue(metadata_in_scope(engine, provider, good_row))
                    self.assertFalse(metadata_in_scope(engine, provider, bad_row))
                    self.assertFalse(metadata_in_scope(engine, provider,
                                                      {"metadata": {"creators": ["A"]}}))
        with self.assertRaises(ResearchError):
            metadata_in_scope("invalid", "github", {"name": "freight"})
        with self.assertRaises(ResearchError):
            metadata_in_scope("freightrecovery", "socrata", {})

    def test_live_scan_rejects_wrong_topic_github_and_zenodo_without_private_metadata(self):
        def fake(url):
            if "retally-unified-research-scout" in url:
                return {"engine": "recoveryos",
                        "scope": "PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA",
                        "sources": []}
            if "api.github.com" in url:
                return {"items": [
                    {"html_url": "https://github.com/synthetic-fixture/vendor-payment-dataset",
                     "name": "unrelated-title",
                     "description": "Accounts payable vendor payment dataset"},
                    {"html_url": "https://github.com/synthetic-fixture/wildlife-project",
                     "name": "not-relevant",
                     "description": "Biology research bird species"},
                ]}
            return {"hits": {"hits": [
                {"id": 345, "metadata": {"title": "Supplier invoice reconciliation research"}},
                {"id": 999, "metadata": {"title": "Bird migration routes"}},
                {"id": 2000, "metadata": {"creators": ["private author info"]}},
            ]}}
        with patch.dict(os.environ, {"RETALLY_DATAGOV_API_KEY": ""}):
            sources, errors = scan("recoveryos", fetch=fake)
        self.assertEqual(errors, [])
        self.assertEqual(sources, [
            "https://github.com/synthetic-fixture/vendor-payment-dataset",
            "https://zenodo.org/records/345",
        ])
        self.assertNotIn("private author", str(sources))
        self.assertNotIn("Bird", str(sources))




class FMCIndexOnlySourceCandidateTests(unittest.TestCase):
    """Original publisher indexed case is a held, not score-admitted source."""

    def test_current_main_fmc_shipper_lifecycle_seeds_keep_truth_boundary(self):
        # Existing protected-main original publisher locators, not new customer evidence.
        sources = (
            "https://www2.fmc.gov/readingroom/docs/2022%28I%29/%2801%29%202022%28I%29%20Initial%20Decision.pdf",
            "https://www2.fmc.gov/readingroom/docs/2022%28I%29/%2802%29%202022%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf",
            "https://www2.fmc.gov/readingroom/docs/2025%28I%29/%2801%29%202025%28I%29%20Initial%20Decision.pdf",
        )
        self.assertEqual(len(set(sources)), 3)
        for url in sources:
            self.assertIn(url, SEEDS["freightrecovery"])
            self.assertEqual(safe_url(url), url)
            ledger, added = merge_sources(
                ledger_from([]), "freightrecovery", [url, url], "2026-10-26"
            )
            self.assertEqual(added, 1)
            self.assertEqual(len(ledger["entries"]), 1)
            recorded = ledger["entries"][0]
            self.assertFalse(recorded["commercial_reuse_authorized"])
            self.assertFalse(recorded["independent_ground_truth"])
            self.assertFalse(recorded["independent_payment_verified"])
            self.assertFalse(recorded["recovered_cash_verified"])

    def test_final_commission_interest_supersedes_preliminary_denial(self):
        path = Path(__file__).with_name("fixtures") / "fmc_22fmc94_girton_index_candidate_v0.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["admission_state"], "DISCOVERED_SOURCE_ONLY_NOT_EVALUATION_ADMITTED")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_HISTORICAL_MARITIME_DECISION_ONLY")
        source = item["source"]
        self.assertIn(source["official_pdf_url"], SEEDS["freightrecovery"])
        self.assertEqual(source["citation"], "22 F.M.C. 94")
        self.assertEqual(source["docket"], "Informal Docket 594(I)")
        self.assertEqual(source["commission_decision_date"], "1979-09-05")
        self.assertFalse(source["original_publisher_pdf_bytes_held"])
        self.assertIsNone(source["original_publisher_pdf_sha256"])
        self.assertFalse(source["rights_or_customer_engine_commercial_reuse_verified"])
        facts = item["historical_decision_only"]
        self.assertEqual(facts["commission_reparation_award_cents"], 40930)
        self.assertTrue(facts["commission_interest_awarded"])
        self.assertEqual(facts["commission_interest_rate_basis_points_per_year"], 600)
        self.assertEqual(facts["interest_accrual_start"], "1978-04-03")
        self.assertTrue(facts["preliminary_settlement_officer_interest_denied"])
        self.assertTrue(facts["preliminary_officer_1979_claim_filing_date_corrected_by_commission"])
        self.assertIsNone(facts["commission_award_collected_cents"])
        self.assertIsNone(facts["interest_actually_paid_cents"])
        self.assertEqual(facts["later_disposition"], "UNKNOWN")
        limits = item["truth_boundaries"]
        self.assertFalse(limits["independently_replayable_original_invoice_truth"])
        self.assertFalse(limits["independently_held_out_from_training_verified"])
        self.assertFalse(limits["admitted_for_freight_error_accuracy"])
        self.assertFalse(limits["admitted_for_modern_rate_authority"])
        self.assertFalse(limits["customer_score_or_cash_promotion_allowed"])
        self.assertIsNone(limits["independent_private_customer_error_cents"])
        self.assertEqual(limits["verified_retally_recovered_cash_cents"], 0)

    def test_fmc_index_candidate_negative_controls_remain_synthetic(self):
        path = Path(__file__).with_name("fixtures") / "fmc_22fmc94_girton_index_candidate_v0.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({c["id"] for c in controls}), 6)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTHETIC_") for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_FINAL_COMMISSION_AWARDED_INTEREST",
            "REJECT_SETTLEMENT_PAYMENT_UNKNOWN",
            "REJECT_UNRELATED_HISTORICAL_AUTHORITY",
            "REJECT_ORIGINAL_BYTES_SHA256_UNKNOWN",
            "REJECT_INTEREST_SETTLEMENT_UNKNOWN",
            "REJECT_CROSS_DOCKET_CARRIER_AND_INTEREST_COLLISION",
        })
        self.assertFalse(item["quality"]["complete_publisher_pdf_byte_read_succeeded"])
        self.assertFalse(item["quality"]["source_original_sha256_known"])
        self.assertEqual(item["quality"]["independent_commercial_customer_labels"], 0)
        bad = json.loads(json.dumps(item))
        bad["historical_decision_only"]["commission_interest_awarded"] = False
        self.assertNotEqual(bad["historical_decision_only"],
                            item["historical_decision_only"])


    def test_fmc_same_claimant_distinct_docket_interest_and_identity_hold(self):
        path = Path(__file__).with_name("fixtures") / "fmc_22fmc94_girton_index_candidate_v0.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        first = item["source"]
        other = item["same_claimant_distinct_docket_counterexample"]
        self.assertEqual(other["source_class"],
                         "PUBLISHER_INDEX_EXCERPT_ONLY_SEPARATE_DECISION_NOT_PACK_ADMITTED")
        self.assertEqual(other["official_pdf_url"],
                         "https://www.fmc.gov/wp-content/uploads/2019/04/vol23.pdf")
        self.assertEqual(other["citation"], "23 F.M.C. 78")
        self.assertEqual(other["docket"], "Informal Docket 746(I)")
        self.assertEqual(other["respondent"], "Prudential Lines, Inc.")
        self.assertIn("Girton Manufacturing", first["decision_title"])
        self.assertEqual(other["claimant"], "Girton Manufacturing Company")
        self.assertEqual(other["commission_adoption_date"], "1980-07-30")
        self.assertEqual(other["shipment_bill_date"], "1977-10-30")
        self.assertEqual(other["reparation_claimed_cents"], 22476)
        self.assertIsNone(other["reparation_amount_awarded_cents"])
        self.assertTrue(other["adopted_officer_disposition_says_reparation_awarded"])
        self.assertTrue(other["offsetting_claim_denied"])
        self.assertFalse(other["final_interest_awarded"])
        self.assertTrue(item["historical_decision_only"]["commission_interest_awarded"])
        self.assertNotEqual((first["citation"], first["docket"]),
                            (other["citation"], other["docket"]))
        self.assertNotEqual(first["commission_decision_date"],
                            other["commission_adoption_date"])
        self.assertFalse(other["cross_case_join_allowed"])
        self.assertIsNone(other["commission_award_collected_cents"])
        self.assertIsNone(other["original_publisher_pdf_sha256"])
        self.assertFalse(other["original_publisher_pdf_bytes_held"])
        self.assertFalse(other["original_bill_of_lading_invoice_tariff_bytes_held"])
        self.assertFalse(other["rights_for_customer_engine_commercial_use_verified"])
        self.assertFalse(other["independently_adjudicated_invoice_ground_truth"])



class CaptureBriefSAMNoticeCandidateTests(unittest.TestCase):
    """Research-only original government notice chronology, not an award truth set."""

    def test_original_sam_notice_amendment_and_expired_deadline_are_not_award(self):
        url = "https://sam.gov/opp/e4a54b2056164c7da290f5a04e60e047/view"
        item = json.loads((Path(__file__).with_name("fixtures") /
                           "capturebrief_sam_barda_2026_amendment_candidate_v0.json").read_text(encoding="utf-8"))
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["evaluation_family"],
                         "GOVERNMENT_SOLICITATION_CHRONOLOGY_SOURCE_CANDIDATE_ONLY")
        self.assertEqual(item["source"]["official_notice_url"], url)
        self.assertEqual(item["source"]["notice_id"], "BARDA-27-100227")
        self.assertIn(url, SEEDS["capturebrief"])
        self.assertFalse(item["source"]["source_original_html_bytes_acquired"])
        self.assertIsNone(item["source"]["source_original_html_sha256"])
        self.assertFalse(item["source"]["commercial_engine_reuse_approved"])
        self.assertFalse(item["source"]["automated_scraping_permitted"])
        facts = item["published_notice_facts"]
        self.assertEqual(facts["original_offers_due_local"], "2026-10-09T13:00:00-04:00")
        self.assertEqual(facts["amended_offers_due_local"], "2026-10-21T13:00:00-04:00")
        self.assertLess(facts["original_offers_due_local"], facts["amended_offers_due_local"])
        self.assertEqual(facts["latest_visible_amendment_number"], "0002")
        self.assertEqual(facts["latest_published_ui_status"], "ACTIVE")
        self.assertEqual(facts["latest_published_inactive_date"], "2026-11-05")
        self.assertTrue(facts["official_notice_date_offer_due_is_not_inactive_date"])
        bound = item["asof_constraints"]
        self.assertEqual(bound["date"], "2026-10-25")
        self.assertTrue(bound["published_amended_due_date_precedes_asof"])
        self.assertTrue(bound["page_ui_active_status_does_not_prove_bid_window_open"])
        self.assertEqual(bound["independent_award_outcome"], "UNKNOWN")
        self.assertEqual(bound["independently_held_out_labeled_cases"], 0)
        self.assertFalse(bound["opportunity_to_award_identity_verified"])
        self.assertFalse(item["quality"]["production_input_approved"])

    def test_sam_notice_synthetic_controls_and_deduped_metadata_only(self):
        item = json.loads((Path(__file__).with_name("fixtures") /
                           "capturebrief_sam_barda_2026_amendment_candidate_v0.json").read_text(encoding="utf-8"))
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTHETIC_") for c in controls))
        self.assertIn("REJECT_DUE_DATE_PASSED_UI_STATUS_NOT_OFFER_ELIGIBILITY",
                      {c["expected"] for c in controls})
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "capturebrief.json"
            first = run(engine="capturebrief", live=False, ledger=ledger,
                        now=datetime(2026, 10, 25, tzinfo=timezone.utc))
            second = run(engine="capturebrief", live=False, ledger=ledger,
                         now=datetime(2026, 10, 25, 1, tzinfo=timezone.utc))
            urls = [r for r in read_ledger(ledger)["entries"]
                    if r["url"] == item["source"]["official_notice_url"]]
            self.assertEqual(len(urls), 1)
            self.assertEqual(second["new_leads"], 0)
            self.assertGreaterEqual(first["new_leads"], 1)
            self.assertFalse(urls[0]["commercial_reuse_authorized"])
            self.assertFalse(urls[0]["independent_ground_truth"])
            self.assertFalse(urls[0]["document_bytes_stored"])



class STBCrowleyTariffSourceTests(unittest.TestCase):
    """First-party 2026 tariff timing evidence, not an invoice-error outcome."""

    @staticmethod
    def _pack():
        path = Path(__file__).with_name("fixtures") / "stb_crowley_fuel_surcharge_timing_candidate_v0.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _assert_original_source_contract(self, pack):
        source = pack["source"]
        self.assertEqual(source["official_certification_registry_url"],
                         "https://www.stb.gov/reports-data/water-carrier-annual-certifications/")
        self.assertEqual(source["carrier_index_url"],
                         "https://www.crowley.com/logistics/resources/rates-tariffs/stb/")
        self.assertEqual(source["carrier_pdf_url"],
                         "https://www.crowley.com/wp-content/uploads/sites/7/2026/10/"
                         "STB-14.1-Intermodal-Fuel-Surcharge-AM-48.pdf")
        self.assertEqual((source["carrier_tariff_org_number"],
                          source["carrier_tariff_number"], source["rule"],
                          source["revision"]), ("023286", "002", "14.1", 48))
        self.assertEqual(source["filed_on"], "2026-10-08")
        self.assertEqual(source["effective_on"], "2026-11-01")
        self.assertEqual(source["publisher_stated_fuel_surcharge_percent"], 66)
        self.assertLess(datetime.fromisoformat(source["filed_on"]),
                        datetime.fromisoformat(source["effective_on"]))
        self.assertLess(datetime.fromisoformat(pack["as_of_utc_date"]),
                        datetime.fromisoformat(source["effective_on"]))
        self.assertTrue(source["carrier_pdf_visual_page_reviewed"])
        self.assertFalse(source["carrier_original_pdf_bytes_acquired"])
        self.assertIsNone(source["carrier_original_pdf_sha256"])
        self.assertFalse(pack["rights"]["carrier_tariff_commercial_machine_reuse_verified"])
        self.assertFalse(pack["rights"]["carrier_tariff_redistribution_permission_verified"])
        self.assertEqual(pack["rights"]["engine_production_admission"],
                         "HOLD_UNTIL_SOURCE_SPECIFIC_RIGHTS_AND_AUTHORITY")
        self.assertEqual(pack["cohort"]["independent_held_out_real_tariff_to_invoice_labels"], 0)
        self.assertEqual(pack["ground_truth_limits"]["freight_overcharge_and_recoverability"],
                         "UNKNOWN")
        self.assertEqual(pack["ground_truth_limits"]["retally_verified_customer_recovery_cents"], 0)
        self.assertFalse(pack["consumption"]["engine_code_modified"])
        self.assertFalse(pack["consumption"]["release_authorized"])
        self.assertIn(source["official_certification_registry_url"],
                      SEEDS["freightrecovery"])

    def test_original_2026_stb_crowley_rule_is_future_effective_not_customer_truth(self):
        pack = self._pack()
        self.assertEqual(pack["engine"], "freightrecovery")
        self.assertEqual(pack["evaluation_family"],
                         "PUBLIC_CARRIER_TARIFF_EFFECTIVE_DATE_PROVENANCE_NOT_INVOICE_ERROR_SCORING")
        self._assert_original_source_contract(pack)

    def test_synthetic_negative_controls_and_forged_source_mutations_rejected(self):
        pack = self._pack()
        self.assertEqual({x["id"] for x in pack["synthetic_negative_controls"]}, {
            "SYNTH_PRE_EFFECTIVE_SHIPMENT", "SYNTH_UNRELATED_MOTOR_LTL",
            "SYNTH_MISSING_INVOICE_BASE",
        })
        controls = {c["id"]: c for c in pack["synthetic_negative_controls"]}
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["independent_outcome"] is None for c in controls.values()))
        self.assertEqual(controls["SYNTH_PRE_EFFECTIVE_SHIPMENT"]["expected"],
                         "REJECT_PRE_EFFECTIVE_TARIFF_APPLICATION")
        self.assertLess(controls["SYNTH_PRE_EFFECTIVE_SHIPMENT"]["shipment_date"],
                        pack["source"]["effective_on"])
        self.assertEqual(controls["SYNTH_UNRELATED_MOTOR_LTL"]["expected"],
                         "REJECT_CROSS_MODE_SCOPE_PROMOTION")
        self.assertEqual(controls["SYNTH_MISSING_INVOICE_BASE"]["expected"],
                         "REJECT_UNGROUNDED_INVOICE_OVERCHARGE")
        self.assertIsNone(controls["SYNTH_MISSING_INVOICE_BASE"]["base_charge_cents"])
        for key, bad in (("effective_on", "2026-10-08"),
                         ("publisher_stated_fuel_surcharge_percent", 86),
                         ("revision", 47),
                         ("carrier_original_pdf_sha256", "unverified-rehash")):
            poisoned = json.loads(json.dumps(pack))
            poisoned["source"][key] = bad
            with self.subTest(forgery=key), self.assertRaises(AssertionError):
                self._assert_original_source_contract(poisoned)
        for key in ("carrier_tariff_commercial_machine_reuse_verified",
                    "carrier_tariff_redistribution_permission_verified"):
            poisoned = json.loads(json.dumps(pack))
            poisoned["rights"][key] = True
            with self.subTest(forgery=key), self.assertRaises(AssertionError):
                self._assert_original_source_contract(poisoned)



class FMC2015ISettlementBoundaryTests(unittest.TestCase):
    """Original FMC settlement/finality sources: cancellation is not cash recovery."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "fmc_2015i_settlement_boundary_candidate_v0.json").read_text(encoding="utf-8"))

    def _assert_contract(self, item):
        self.assertEqual(item["schema_version"], "0.1.0")
        self.assertEqual(item["evaluation_family"],
                         "FREIGHT_SETTLEMENT_AND_ACCOUNTING_OUTCOME_SEPARATION_NOT_CUSTOMER_ERROR_SCORING")
        self.assertEqual(item["status"], "HELD_SOURCE_BOUND_CANDIDATE_NOT_ENGINE_ADMITTED")
        self.assertEqual(item["ownership"]["canonical_repository"],
                         "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(item["ownership"]["existing_draft_pr"], 766)
        self.assertFalse(item["ownership"]["operational_lab_changed"])
        source = item["source"]
        self.assertEqual(source["docket"], "2015(I)")
        self.assertEqual(source["order_url"],
                         "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20-Order%20of%20Dismissal.pdf")
        self.assertEqual(source["nonreview_notice_url"],
                         "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20Not.%20Not%20Review.pdf")
        self.assertEqual(source["order_served_on"], "2024-11-08")
        self.assertEqual(source["nonreview_notice_served_on"], "2024-12-10")
        self.assertFalse(source["original_order_pdf_bytes_acquired"])
        self.assertIsNone(source["original_order_pdf_sha256"])
        self.assertFalse(source["original_notice_pdf_bytes_acquired"])
        self.assertIsNone(source["original_notice_pdf_sha256"])
        self.assertFalse(source["original_bill_of_lading_or_invoice_bytes_acquired"])
        self.assertFalse(source["original_settlement_and_bank_ledger_bytes_acquired"])
        self.assertIsNone(source["historical_tariff_effective_date"])
        self.assertFalse(item["rights"]["production_engine_commercial_ingest_approved"])
        self.assertFalse(item["rights"]["source_specific_commercial_reuse_permission_verified"])
        self.assertEqual(item["rights"]["rights_status"], "HOLD")
        facts = item["publisher_reported_facts"]
        self.assertEqual(facts["shipment_bill_of_lading_reference"], "MEDUUP205245")
        self.assertEqual(facts["complaint_filed_year"], 2024)
        self.assertEqual(facts["alleged_low_water_fee_usd_cents"], 300000)
        self.assertEqual(facts["alleged_extra_fee_usd_cents"], 14000)
        self.assertEqual(facts["approved_settlement_outstanding_demurrage_cancelled_usd_cents"], 465000)
        self.assertEqual(facts["settlement_right_to_claim_previous_freight_refund_usd_cents_waived"], 300000)
        self.assertEqual(facts["settlement_waived_late_fee_claim_brl_cents"], 70000)
        self.assertEqual(facts["settlement_submitted_on"], "2024-10-17")
        self.assertEqual(facts["settlement_fmc_approved_on"], "2024-11-08")
        self.assertEqual(facts["administratively_final_on"], "2024-12-10")
        self.assertTrue(facts["complaint_dismissed_with_prejudice"])
        self.assertFalse(facts["merits_freight_overcharge_adjudicated"])
        self.assertIsNone(facts["verified_actual_cash_refund_received_usd_cents"])
        self.assertIsNone(facts["independent_ledger_confirmation_of_demurrage_cancellation"])
        self.assertEqual(facts["verified_retally_recovered_cash_usd_cents"], 0)
        self.assertIsNone(facts["reported_cash_settlement_paid_usd_cents"])
        self.assertEqual(item["cohort"]["independently_held_out_original_invoice_labels"], 0)
        self.assertEqual(item["cohort"]["independently_adjudicated_freight_billing_error_cases"], 0)
        self.assertFalse(item["cohort"]["customer_precision_recall_estimation_permitted"])
        self.assertEqual(item["truth_limits"]["customer_error_accuracy"], "UNKNOWN")
        self.assertTrue(item["truth_limits"]["cancellation_of_outstanding_charge_is_not_a_cash_refund"])
        self.assertTrue(item["truth_limits"]["waived_refund_claim_is_not_a_cash_payment"])
        self.assertTrue(item["truth_limits"]["administrative_finality_is_not_merits_adjudication"])
        self.assertFalse(item["acceptance"]["original_publisher_response_byte_hash_verified"])
        self.assertFalse(item["acceptance"]["independent_qa_complete"])
        self.assertFalse(item["acceptance"]["full_main_and_draft_seed_integration_verified"])
        self.assertFalse(item["acceptance"]["guarded_release_eligible"])
        controls = item["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({c["id"] for c in controls}), 6)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and
                            c["id"].startswith("SYNTH_") for c in controls))
        self.assertEqual({c["expected"] for c in controls}, {
            "REJECT_CANCELLATION_IS_NOT_CASH",
            "REJECT_WAIVED_CLAIM_IS_NOT_PAYMENT",
            "REJECT_ALLEGATION_IS_NOT_ADJUDICATION",
            "REJECT_DOCKET_IDENTIFIER_NOT_YEAR",
            "REJECT_PREMATURE_FINALITY",
            "REJECT_URL_NOT_SOURCE_OR_CUSTOMER_CUSTODY",
        })

    def test_fmc_settlement_facts_finality_and_truth_boundary(self):
        item = self._pack()
        self._assert_contract(item)
        # These original main-only pointers remain held, never silently
        # activated by this research-lab fixture on a diverged draft branch.
        self.assertNotIn(item["source"]["order_url"], SEEDS["freightrecovery"])
        self.assertNotIn(item["source"]["nonreview_notice_url"], SEEDS["freightrecovery"])

    def test_fmc_settlement_forged_cancellation_cash_and_source_custody_are_red(self):
        original = self._pack()
        self._assert_contract(original)
        attacks = (
            ("publisher_reported_facts", "approved_settlement_outstanding_demurrage_cancelled_usd_cents", 765000),
            ("publisher_reported_facts", "verified_retally_recovered_cash_usd_cents", 465000),
            ("publisher_reported_facts", "merits_freight_overcharge_adjudicated", True),
            ("publisher_reported_facts", "administratively_final_on", "2024-11-08"),
            ("publisher_reported_facts", "settlement_right_to_claim_previous_freight_refund_usd_cents_waived", 0),
            ("source", "original_order_pdf_bytes_acquired", True),
            ("source", "original_notice_pdf_sha256", "unsupported-rehash"),
            ("source", "original_bill_of_lading_or_invoice_bytes_acquired", True),
            ("rights", "production_engine_commercial_ingest_approved", True),
            ("cohort", "independently_held_out_original_invoice_labels", 1),
        )
        for section, key, fake in attacks:
            with self.subTest(section=section, field=key):
                altered = json.loads(json.dumps(original))
                altered[section][key] = fake
                with self.assertRaises(AssertionError):
                    self._assert_contract(altered)



class NYCCatalogIdentityReconciliationTests(unittest.TestCase):
    """Original NYC catalog IDs: reject restaurant-topic and unearned permit truth."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                          "nyc_dob_catalog_identity_reconciliation_candidate_v0.json"
                          ).read_text(encoding="utf-8"))

    def _assert_contract(self, data):
        self.assertEqual(set(data), {
            "schema_version", "pack_id", "evaluation_family", "asof_date",
            "ownership", "publisher_sources", "source_identity_delta",
            "rights_and_provenance", "cohort", "synthetic_negative_controls",
            "acceptance",
        })
        self.assertEqual(data["schema_version"], "0.1.0")
        self.assertEqual(data["pack_id"],
                         "NYC_DOB_SOURCE_IDENTITY_MAIN_CANDIDATE_NEGATIVE_CONTROL_V0")
        self.assertEqual(data["evaluation_family"],
                         "GOVERNMENT_PERMIT_SOURCE_IDENTITY_NOT_PERMIT_SCORING")
        owner = data["ownership"]
        self.assertEqual(owner["canonical_repository"],
                         "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(owner["protected_main_catalog_git_blob_sha1"],
                         "3fd2c32284e27833ed90725c276af6d63a086190")
        self.assertEqual(owner["candidate_catalog_git_blob_sha1"],
                         "a52e50df2e273465d14ebda947fb3b3027acd6d3")
        self.assertEqual(owner["existing_operational_writer_branch"],
                         "research/retally-unified-data-lab")
        self.assertFalse(owner["operational_writer_modified"])
        self.assertFalse(owner["provider_or_host_rule_changed"])
        roles = {
            "43nn-pn8j": "RESTAURANT_INSPECTION_RESULTS_NOT_DOB",
            "w9ak-ipjd": "DOB_NOW_JOB_APPLICATION_FILINGS_NOT_ISSUED_PERMITS",
            "rbx6-tga4": "DOB_NOW_APPROVED_PERMITS_EXCLUDES_ELECTRICAL_ELEVATOR_LAA",
            "ipu4-2q9a": "DOB_BIS_PERMIT_ISSUANCE_NOT_DOB_NOW",
        }
        sources = data["publisher_sources"]
        self.assertEqual(len(sources), 4)
        self.assertEqual({row["id"] for row in sources}, set(roles))
        for row in sources:
            self.assertEqual(set(row), {
                "id", "publisher", "role", "url", "source_updated_on",
                "original_http_bytes_custodied", "original_http_sha256",
                "dataset_specific_commercial_reuse_verified",
            })
            self.assertEqual(row["url"],
                             "https://data.cityofnewyork.us/d/" + row["id"])
            self.assertEqual(row["role"], roles[row["id"]])
            self.assertFalse(row["original_http_bytes_custodied"])
            self.assertIsNone(row["original_http_sha256"])
            self.assertFalse(row["dataset_specific_commercial_reuse_verified"])
        delta = data["source_identity_delta"]
        self.assertEqual(delta["main_only_wrong_topic_dataset_id"], "43nn-pn8j")
        self.assertTrue(delta["candidate_excludes_wrong_topic"])
        self.assertEqual(delta["correct_dob_now_approved_permit_id"], "rbx6-tga4")
        self.assertEqual(delta["correct_historical_bis_issuance_id"], "ipu4-2q9a")
        self.assertEqual(delta["job_application_filing_id_not_issuance"], "w9ak-ipjd")
        self.assertTrue(delta["main_metadata_locator_is_not_live_customer_error_proof"])
        self.assertNotIn("https://data.cityofnewyork.us/d/43nn-pn8j",
                         SEEDS["permitplate"])
        self.assertIn("https://data.cityofnewyork.us/d/rbx6-tga4",
                      SEEDS["permitplate"])
        self.assertIn("https://data.cityofnewyork.us/d/ipu4-2q9a",
                      SEEDS["permitplate"])
        self.assertIn("https://data.cityofnewyork.us/d/w9ak-ipjd",
                      SEEDS["permitplate"])
        rights = data["rights_and_provenance"]
        self.assertTrue(rights["public_municipal_catalog_metadata_only"])
        self.assertFalse(rights["source_specific_commercial_reuse_authorized"])
        self.assertFalse(rights["original_publisher_http_bytes_acquired"])
        self.assertIsNone(rights["original_publisher_http_sha256"])
        self.assertEqual(rights["commercial_engine_admission"], "HOLD")
        self.assertEqual(rights["raw_customer_or_original_permit_rows_stored"], 0)
        self.assertTrue(rights["source_citations_not_original_response_byte_custody"])
        cohort = data["cohort"]
        for key in ("independently_held_out_issued_permit_labels",
                    "independent_current_validity_labels",
                    "independent_commercial_buyer_labels",
                    "source_row_count_acquired",
                    "verified_retally_customer_cash_cents"):
            self.assertEqual(cohort[key], 0)
        self.assertEqual(cohort["permit_scoring_precision_recall"], "UNKNOWN")
        self.assertEqual(cohort["buyer_demand"], "UNKNOWN")
        controls = data["synthetic_negative_controls"]
        self.assertEqual(len(controls), 3)
        self.assertEqual({row["id"] for row in controls}, {
            "SYNTH_RESTAURANT_INSPECTION_ID_PROMOTED_TO_DOB_PERMIT",
            "SYNTH_JOB_APPLICATION_FILINGS_PROMOTED_TO_ISSUED_PERMITS",
            "SYNTH_DOB_APPROVED_PERMITS_ROWS_PROMOTED_TO_ACTIVE_BUYER_LEADS",
        })
        self.assertEqual({row["expected"] for row in controls}, {
            "REJECT_WRONG_TOPIC", "REJECT_APPLICATION_NOT_PERMIT_ISSUANCE",
            "UNKNOWN_CURRENT_VALIDITY_AND_BUYER_DEMAND",
        })
        self.assertTrue(all(set(x) == {"id", "kind", "input_dataset_id", "expected"}
                            and x["kind"] == "SYNTHETIC" for x in controls))
        acceptance = data["acceptance"]
        self.assertTrue(acceptance["existing_unified_lab_fixture_only"])
        for key in ("original_source_byte_hash_verified", "independent_qa_complete",
                    "original_row_level_labels_collected",
                    "operational_main_source_catalog_corrected", "release_eligible"):
            self.assertFalse(acceptance[key])
        self.assertEqual(acceptance["owner_lane"], ":48")
        self.assertEqual(acceptance["independent_qa_lane"], ":44")

    def test_official_nyc_catalog_identities_held_not_scored(self):
        self._assert_contract(self._pack())

    def test_no_unverified_catalog_promotion_or_fake_provenance(self):
        original = self._pack()
        self._assert_contract(original)
        mutations = (
            ("publisher_sources", 0, "role", "DOB_ISSUED_PERMITS"),
            ("publisher_sources", 1, "role", "DOB_ISSUED_PERMITS"),
            ("publisher_sources", 2, "original_http_bytes_custodied", True),
            ("publisher_sources", 2, "original_http_sha256", "not-a-source-hash"),
            ("rights_and_provenance", None, "source_specific_commercial_reuse_authorized", True),
            ("cohort", None, "independently_held_out_issued_permit_labels", 1),
            ("cohort", None, "buyer_demand", "VERIFIED"),
            ("acceptance", None, "operational_main_source_catalog_corrected", True),
            ("acceptance", None, "independent_qa_complete", True),
            ("synthetic_negative_controls", 0, "kind", "ORIGINAL"),
        )
        for section, index, key, fake in mutations:
            with self.subTest(section=section, field=key):
                modified = json.loads(json.dumps(original))
                target = modified[section][index] if index is not None else modified[section]
                target[key] = fake
                with self.assertRaises(AssertionError):
                    self._assert_contract(modified)



class ProtectedMainSeedContinuityTests(unittest.TestCase):
    """Pinned main/draft source comparison: eight source locators held; one wrong topic rejected."""

    @staticmethod
    def _read(name):
        return json.loads((Path(__file__).with_name("fixtures") / name).read_text(encoding="utf-8"))

    def _check(self, official, fmc, nyc):
        state = official["acceptance"]["protected_main_source_set_continuity_20261027"]
        self.assertEqual(set(state), {
            "observed_main_head", "main_catalog_git_blob_sha1",
            "draft_head_before_snapshot", "draft_catalog_git_blob_sha1",
            "original_main_only_seed_url_count",
            "original_official_freight_pointers_retained_as_held_metadata",
            "retained_in_six_source_manifest",
            "retained_in_fmc_2015i_pair_manifest",
            "excluded_nyc_restaurant_wrong_topic_count", "excluded_nyc_dataset_id",
            "original_publisher_response_sha256", "original_source_bytes_acquired",
            "source_specific_commercial_use_admitted",
            "independently_held_out_customer_truth_labels",
            "provider_host_or_rule_modified",
            "executable_main_to_draft_source_merge_complete",
            "protected_main_integration_verified",
            "legacy_labs_consolidated", "classification", "cohort",
            "owner_lane", "independent_qa_lane",
        })
        self.assertEqual(state["observed_main_head"], "ff4edaa6540d02cdddb4c04ef6ce224a434a3f8b")
        self.assertEqual(state["main_catalog_git_blob_sha1"],
                         "3fd2c32284e27833ed90725c276af6d63a086190")
        self.assertEqual(state["draft_head_before_snapshot"],
                         "49609760a7e2dd83d7686e5ae7852597639472a1")
        self.assertEqual(state["draft_catalog_git_blob_sha1"],
                         "a52e50df2e273465d14ebda947fb3b3027acd6d3")
        self.assertEqual((state["original_main_only_seed_url_count"],
                          state["original_official_freight_pointers_retained_as_held_metadata"],
                          state["retained_in_six_source_manifest"],
                          state["retained_in_fmc_2015i_pair_manifest"],
                          state["excluded_nyc_restaurant_wrong_topic_count"]), (9, 8, 6, 2, 1))
        self.assertEqual(state["excluded_nyc_dataset_id"], "43nn-pn8j")
        self.assertEqual(state["classification"],
                         "STATIC_PINNED_SEED_DIFF_EIGHT_HELD_ONE_EXCLUDED_NOT_ORIGINAL_SOURCE_BYTE_CUSTODY")
        self.assertEqual(state["cohort"], "PROTECTED_MAIN_VS_DRAFT_SEED_IDENTITY_2026_10_27")
        self.assertEqual(state["owner_lane"], "UNIFIED_RESEARCH_LAB")
        self.assertEqual(state["independent_qa_lane"], ":44")
        self.assertIsNone(state["original_publisher_response_sha256"])
        self.assertEqual(state["independently_held_out_customer_truth_labels"], 0)
        for field in ("original_source_bytes_acquired",
                      "source_specific_commercial_use_admitted",
                      "provider_host_or_rule_modified",
                      "executable_main_to_draft_source_merge_complete",
                      "protected_main_integration_verified",
                      "legacy_labs_consolidated"):
            self.assertFalse(state[field], field)

        expected = {
            "https://www.justice.gov/usao-edca/pr/menlo-worldwide-services-inc-and-its-subcontractor-estes-pay-us-13-million-resolve",
            "https://www.justice.gov/archives/opa/pr/freight-carriers-agree-pay-685-million-resolve-allegations-knowingly-presenting-false-claims",
            "https://www.cbca.gov/files/decisions/2020/SULLIVAN_08-06-20_6578-RATE__AARE_LOGISTICS%2C_LLC%20%28Decision%29.pdf",
            "https://www.cbca.gov/files/decisions/2024/LESTER_08-08-24_8051-RATE__JAMES_FORWARDING_COMPANY_INC%20%28DECISION%29.pdf",
            "https://www.cbca.gov/files/decisions/2009/GILMORE_10-29-09_1317-RATE__UNION_PACIFIC_RAILROAD_508.pdf",
            "https://www.cbca.gov/files/decisions/2014/ZISCHKAU_05-14-14_CBCA%203467-RATE__IN_THE_MATTER_OF_TOTAL_QUALITY_LOGISTICS_LLC_.pdf",
            "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20-Order%20of%20Dismissal.pdf",
            "https://www2.fmc.gov/readingroom/docs/2015%28I%29/2015%28I%29%20Not.%20Not%20Review.pdf",
        }
        actual = {row["url"] for row in official["sources"]} | {
            fmc["source"]["order_url"], fmc["source"]["nonreview_notice_url"],
        }
        self.assertEqual(len(official["sources"]), 6)
        self.assertEqual(actual, expected)
        self.assertTrue(all(url not in SEEDS["freightrecovery"] for url in expected))
        self.assertTrue(all(not row["original_publisher_response_bytes_acquired"]
                            and row["original_publisher_response_sha256"] is None
                            and row["actual_customer_invoice_error_label"] == "UNKNOWN"
                            for row in official["sources"]))
        self.assertFalse(official["rights"]["commercial_engine_admission_authorized"])
        self.assertFalse(fmc["rights"]["production_engine_commercial_ingest_approved"])
        self.assertFalse(fmc["source"]["original_order_pdf_bytes_acquired"])
        self.assertFalse(fmc["source"]["original_notice_pdf_bytes_acquired"])
        self.assertIsNone(fmc["source"]["original_order_pdf_sha256"])
        self.assertIsNone(fmc["source"]["original_notice_pdf_sha256"])
        self.assertEqual(nyc["source_identity_delta"]["main_only_wrong_topic_dataset_id"],
                         "43nn-pn8j")
        self.assertNotIn("https://data.cityofnewyork.us/d/43nn-pn8j",
                         SEEDS["permitplate"])
        self.assertFalse(nyc["rights_and_provenance"]["source_specific_commercial_reuse_authorized"])
        self.assertEqual(nyc["cohort"]["independently_held_out_issued_permit_labels"], 0)

    def _assert_latest_main_source_continuity(self, official, fmc, nyc):
        """Compare pinned current-main source locators, not publisher bytes or invoice labels."""
        recent = official["acceptance"]["current_main_source_set_continuity_20261027"]
        self.assertEqual(recent["schema_version"], "1.0.0")
        self.assertEqual(recent["observed_main_head"],
                         official["ownership"]["current_main_fmc_source_gap"]["canonical_main_sha"])
        self.assertEqual(recent["main_catalog_git_blob_sha1"],
                         official["ownership"]["current_main_fmc_source_gap"]["canonical_main_catalog_git_blob_sha1"])
        self.assertEqual(recent["draft_catalog_git_blob_sha1"],
                         official["ownership"]["current_main_fmc_source_gap"]["candidate_before_catalog_git_blob_sha1"])
        base_six = {row["url"] for row in official["sources"]}
        fmc_pair = {fmc["source"]["order_url"], fmc["source"]["nonreview_notice_url"]}
        fmc_four = {row["url"] for row in official["ownership"]["current_main_fmc_source_gap"]["sources"]}
        retained = base_six | fmc_pair | fmc_four
        restaurant = "https://data.cityofnewyork.us/d/43nn-pn8j"
        self.assertEqual(len(base_six), 6)
        self.assertEqual(len(fmc_pair), 2)
        self.assertEqual(len(fmc_four), 4)
        self.assertEqual(len(fmc_pair & fmc_four), 2)
        self.assertEqual(len(retained), 10)
        self.assertNotIn(restaurant, retained)
        self.assertEqual((recent["main_only_source_url_count"],
                          recent["unique_held_freight_source_pointers"],
                          recent["held_legacy_six_source_manifest"],
                          recent["held_fmc_2015_pair_manifest"],
                          recent["held_current_main_fmc_gap_manifest"],
                          recent["overlap_of_two_fmc_2015_pointers"],
                          recent["excluded_wrong_topic_nyc_restaurant"]),
                         (11, 10, 6, 2, 4, 2, 1))
        self.assertEqual(recent["excluded_wrong_topic_dataset_id"], "43nn-pn8j")
        self.assertEqual(len(retained | {restaurant}), 11)
        self.assertTrue(all(url not in SEEDS["freightrecovery"] for url in retained))
        self.assertNotIn(restaurant, SEEDS["permitplate"])
        self.assertIsNone(recent["original_publisher_response_sha256"])
        self.assertEqual(recent["independently_held_out_customer_invoice_labels"], 0)
        self.assertEqual(recent["verified_retally_cash_recovery_cents"], 0)
        for held in ("original_source_bytes_held", "commercial_reuse_approved",
                     "independent_qa_green", "main_integration_complete"):
            self.assertIs(recent[held], False)
        self.assertEqual(recent["status"],
                         "MAIN_SOURCE_IDENTITY_RECONCILED_IN_HELD_METADATA_NOT_EXECUTABLE_OR_LICENSED")
        controls = recent["synthetic_negative_controls"]
        self.assertEqual(len(controls), 2)
        self.assertEqual(len({row["id"] for row in controls}), 2)
        self.assertTrue(all(row["kind"] == "SYNTHETIC" for row in controls))
        self.assertEqual(nyc["source_identity_delta"]["main_only_wrong_topic_dataset_id"],
                         "43nn-pn8j")

    def test_current_main_eleven_seed_identity_reconciliation(self):
        self._assert_latest_main_source_continuity(
            self._read("protected_main_official_source_reconciliation_candidate_v0.json"),
            self._read("fmc_2015i_settlement_boundary_candidate_v0.json"),
            self._read("nyc_dob_catalog_identity_reconciliation_candidate_v0.json"),
        )

    def test_current_main_rejects_nine_only_snapshot_and_forged_promotions(self):
        official = self._read("protected_main_official_source_reconciliation_candidate_v0.json")
        fmc = self._read("fmc_2015i_settlement_boundary_candidate_v0.json")
        nyc = self._read("nyc_dob_catalog_identity_reconciliation_candidate_v0.json")
        self._assert_latest_main_source_continuity(official, fmc, nyc)
        mutations = (
            ("main_only_source_url_count", 9),
            ("unique_held_freight_source_pointers", 8),
            ("held_current_main_fmc_gap_manifest", 2),
            ("overlap_of_two_fmc_2015_pointers", 0),
            ("original_publisher_response_sha256", "FAKE"),
            ("original_source_bytes_held", True),
            ("commercial_reuse_approved", True),
            ("independently_held_out_customer_invoice_labels", 1),
            ("verified_retally_cash_recovery_cents", 1),
            ("independent_qa_green", True),
            ("main_integration_complete", True),
        )
        for field, forged in mutations:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                mutated = json.loads(json.dumps(official))
                mutated["acceptance"]["current_main_source_set_continuity_20261027"][field] = forged
                self._assert_latest_main_source_continuity(mutated, fmc, nyc)

    def test_main_only_sources_preserved_as_held_or_explicitly_excluded(self):
        self._check(
            self._read("protected_main_official_source_reconciliation_candidate_v0.json"),
            self._read("fmc_2015i_settlement_boundary_candidate_v0.json"),
            self._read("nyc_dob_catalog_identity_reconciliation_candidate_v0.json"),
        )

    def test_reject_promoted_seed_parity_or_forged_source_truth(self):
        original = self._read("protected_main_official_source_reconciliation_candidate_v0.json")
        fmc = self._read("fmc_2015i_settlement_boundary_candidate_v0.json")
        nyc = self._read("nyc_dob_catalog_identity_reconciliation_candidate_v0.json")
        self._check(original, fmc, nyc)
        mutations = (
            ("original_main_only_seed_url_count", 8),
            ("original_official_freight_pointers_retained_as_held_metadata", 9),
            ("excluded_nyc_restaurant_wrong_topic_count", 0),
            ("original_publisher_response_sha256", "UNVERIFIED"),
            ("source_specific_commercial_use_admitted", True),
            ("protected_main_integration_verified", True),
            ("legacy_labs_consolidated", True),
        )
        for field, forged in mutations:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                changed = json.loads(json.dumps(original))
                changed["acceptance"]["protected_main_source_set_continuity_20261027"][field] = forged
                self._check(changed, fmc, nyc)




class FMCMaerskFederalPenaltyNotCustomerCashTests(unittest.TestCase):
    """Original FMC release: paid federal penalty != delivered shipper refunds."""

    @staticmethod
    def _pack():
        path = Path(__file__).with_name("fixtures") / (
            "fmc_maersk_penalty_vs_refund_2026_candidate_v0.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def _check(self, record):
        src = record["source"]
        facts = record["publisher_reported_facts"]
        truth = record["ground_truth_limits"]
        self.assertEqual(record["schema_version"], "0.1.0")
        self.assertEqual(src["publication_date"], "2026-05-26")
        self.assertEqual(src["original_official_url"],
                         "https://www.fmc.gov/articles/"
                         "fmc-collects-civil-penalty-payment-of-1900000-from-shipping-line/")
        self.assertEqual(facts["civil_penalty_payment_received_by_government_cents"],
                         190000000)
        self.assertEqual(facts["civil_penalty_cash_destination"],
                         "UNITED_STATES_GENERAL_FUND")
        self.assertEqual(facts["fmc_received_penalty_payment_cents"], 0)
        self.assertIs(facts["civil_penalty_violations_admitted"], False)
        self.assertIsNone(facts["published_total_customer_refunds_paid_cents"])
        self.assertEqual(truth["verified_retally_customer_recovery_cents"], 0)
        self.assertIs(truth["independent_freight_error_accuracy_scoring_permitted"],
                      False)
        self.assertIsNone(src["original_publisher_response_sha256"])
        self.assertIs(src["commercial_customer_engine_reuse_approved"], False)
        self.assertEqual(record["admission_state"],
                         "RESEARCH_ONLY_HELD_NOT_ENGINE_SCORING_OR_CUSTOMER_CASH")
        self.assertEqual(truth["independently_held_out_private_invoice_labels"], 0)
        self.assertEqual(truth["customer_refund_implementation"], "UNKNOWN")
        self.assertIs(src["original_publisher_response_bytes_custodied"], False)

    def test_original_regulator_release_keeps_distinct_cash_destinations(self):
        pack = self._pack()
        self._check(pack)
        self.assertNotIn(pack["source"]["original_official_url"],
                         SEEDS["freightrecovery"])
        self.assertIs(pack["publisher_reported_facts"]
                      ["carrier_agreed_to_refunds_and_waivers_for_affected_third_parties"],
                      True)
        self.assertIsNone(pack["publisher_reported_facts"]
                          ["adjudicated_individual_freight_invoice_error_cents"])
        self.assertIs(pack["ground_truth_limits"]
                      ["independent_government_treasury_receipt_replayed"], False)
        self.assertFalse(pack["quality"]["source_response_bytes_sha256_known"])

    def test_five_proposed_unsafe_inferences_are_explicitly_synthetic(self):
        cases = self._pack()["synthetic_negative_controls"]
        self.assertEqual(len(cases), 5)
        self.assertEqual(len({case["id"] for case in cases}), 5)
        self.assertTrue(all(case["kind"] == "SYNTHETIC" and
                            case["id"].startswith("SYNTHETIC_") for case in cases))

    def test_nine_forged_money_rights_and_provenance_promotions_are_rejected(self):
        original = self._pack()
        self._check(original)
        mutations = [
            ("amount", lambda x: x["publisher_reported_facts"].update(
                civil_penalty_payment_received_by_government_cents=190000)),
            ("beneficiary", lambda x: x["publisher_reported_facts"].update(
                civil_penalty_cash_destination="RETALLY")),
            ("agency_cash", lambda x: x["publisher_reported_facts"].update(
                fmc_received_penalty_payment_cents=190000000)),
            ("admission", lambda x: x["publisher_reported_facts"].update(
                civil_penalty_violations_admitted=True)),
            ("refund", lambda x: x["publisher_reported_facts"].update(
                published_total_customer_refunds_paid_cents=190000000)),
            ("retally_cash", lambda x: x["ground_truth_limits"].update(
                verified_retally_customer_recovery_cents=190000000)),
            ("scoring", lambda x: x["ground_truth_limits"].update(
                independent_freight_error_accuracy_scoring_permitted=True)),
            ("publisher_hash", lambda x: x["source"].update(
                original_publisher_response_sha256="0" * 64)),
            ("rights", lambda x: x["source"].update(
                commercial_customer_engine_reuse_approved=True)),
        ]
        for name, mutation in mutations:
            with self.subTest(forged=name), self.assertRaises(AssertionError):
                fake = json.loads(json.dumps(original))
                mutation(fake)
                self._check(fake)



class FMCMSC23_08CaseCohortAndCashBoundaryTests(unittest.TestCase):
    """2026 FMC first-party case: bounded NOR overbill percentage != buyer refund."""

    @staticmethod
    def _pack():
        return json.loads(
            (Path(__file__).with_name("fixtures") /
             "fmc_msc_23_08_nor_adjudication_candidate_v0.json").read_text(
                 encoding="utf-8"))

    def _check(self, record):
        src = record["source"]
        case = record["publisher_reported_case"]
        truth = record["ground_truth_limits"]
        self.assertEqual(record["schema_version"], "0.1.2")
        self.assertEqual(src["commission_docket"], "23-08")
        self.assertEqual(src["fmc_summary_temporal_boundaries_reviewed_on"],
                         "2026-10-27")
        self.assertEqual(src["temporal_scope_evidence_kind"],
                         "FMC_FIRST_PARTY_2026_01_28_HTML_SUMMARY_ONLY_NOT_ORIGINAL_ORDER_BYTES")
        self.assertEqual(src["final_order_index_document_id"], 131865)
        self.assertEqual(src["official_fmc_final_order_document_locator_url"],
                         "https://www2.fmc.gov/readingroom/documents/131865")
        self.assertEqual(src["official_fmc_final_order_indexed_pdf_url"],
                         "https://www2.fmc.gov/readingroom/docs/23-08/%2832%29%2023-08%20Order%20on%20Initial%20Decision%20%28public%29.pdf/")
        self.assertEqual(src["final_order_source_locator_crosschecked_on"],
                         "2026-10-27")
        self.assertIs(src["final_order_link_is_raw_document_custody"], False)
        self.assertIs(src["final_order_pdf_content_independently_examined"], False)
        self.assertEqual(src["original_fmc_release_published"], "2026-01-28")
        self.assertEqual(src["testimony_published"], "2026-06-03")
        self.assertEqual(record["cohort"],
                         "MSC_NON_OPERATING_REEFER_DEMURRAGE_DETENTION_2021_ONLY")
        self.assertEqual(case["approximate_nor_bill_overcharge_share_percent"], 23)
        self.assertEqual(case["notify_party_merchant_clause_billing_years"],
                         "2018_TO_2020")
        self.assertEqual(case["nor_tariff_publication_violation_period"],
                         "2021_TO_EARLY_2023")
        self.assertEqual(case["nor_tariff_knowing_willful_start_month"],
                         "2022-03")
        self.assertEqual(case["nor_overcharge_unreasonable_practice_year"], 2021)
        self.assertIs(case["cross_violation_invoice_error_inference_permitted"], False)
        self.assertIs(case["percentage_is_approximate"], True)
        self.assertIs(case["other_carriers_or_billing_years_extrapolation_permitted"],
                      False)
        self.assertEqual(case["civil_penalty_notify_party_cents"], 6500000)
        self.assertEqual(case["civil_penalty_tariff_publication_cents"], 946000000)
        self.assertEqual(case["civil_penalty_nor_overcharge_cents"], 1314500000)
        self.assertEqual(case["civil_penalty_total_assessed_cents"], 2267000000)
        self.assertEqual(
            sum(case[key] for key in (
                "civil_penalty_notify_party_cents",
                "civil_penalty_tariff_publication_cents",
                "civil_penalty_nor_overcharge_cents")),
            case["civil_penalty_total_assessed_cents"])
        self.assertEqual(case["reported_penalty_payment_recipient"],
                         "UNITED_STATES_TREASURY")
        self.assertIs(case["fmc_civil_penalty_is_customer_restitution"], False)
        self.assertIsNone(case["shipper_refunds_paid_total_cents"])
        self.assertEqual(case["payment_status_from_january_28_release"],
                         "ASSESSED_NOT_INDEPENDENTLY_CONFIRMED_PAID")
        self.assertIs(case["june_3_testimony_reports_penalty_paid_in_full_asof_may_2026"],
                      True)
        self.assertEqual(truth["independently_heldout_labeled_shipment_invoices"], 0)
        self.assertIs(truth["current_freight_error_precision_recall_scoring_permitted"],
                      False)
        self.assertEqual(truth["exact_nor_invoice_population_size"], "UNKNOWN")
        self.assertEqual(truth["exact_day_of_march_2022_tariff_statement"], "UNKNOWN")
        self.assertEqual(truth["exact_notify_party_billed_invoice_population"], "UNKNOWN")
        self.assertEqual(truth["exact_customer_refund_total"], "UNKNOWN")
        self.assertEqual(truth["verified_retally_customer_recovery_cents"], 0)
        self.assertIs(src["original_press_release_response_bytes_custodied"], False)
        self.assertIsNone(src["original_press_release_response_sha256"])
        self.assertIs(src["final_order_original_pdf_bytes_custodied"], False)
        self.assertIsNone(src["final_order_original_pdf_sha256"])
        self.assertIsNone(src["public_testimony_original_response_sha256"])
        self.assertIs(src["commercial_scoring_authorized"], False)
        self.assertEqual(record["admission_state"],
                         "RESEARCH_ONLY_SOURCE_POINTERS_NOT_CURRENT_CUSTOMER_TRUTH_OR_COMMERCIAL_SCORING")

    def test_fmc_reported_adjudication_not_all_freight_accuracy(self):
        data = self._pack()
        self._check(data)
        self.assertNotIn(data["source"]["official_fmc_release_url"],
                         SEEDS["freightrecovery"])
        self.assertIn("2021", data["publisher_reported_case"]["overcharge_cohort"])
        self.assertIs(data["quality"]["invoice_level_labeling_complete"], False)
        self.assertIs(data["quality"]["case_level_labeling_complete"], False)

    def test_fmc_original_order_locator_is_not_custodied_pdf(self):
        """Official 23-08 decision index and PDF link are not byte custody."""
        item = self._pack()
        self._check(item)
        self.assertEqual(item["source"]["final_order_index_served"], "2026-01-06")
        self.assertFalse(item["source"]["final_order_original_pdf_bytes_custodied"])
        self.assertIsNone(item["source"]["final_order_original_pdf_sha256"])
        # Each scenario is deliberately SYNTHETIC, not a source assertion.
        for key, replacement in (
            ("final_order_index_document_id", 131866),
            ("official_fmc_final_order_document_locator_url",
             "https://www2.fmc.gov/readingroom/documents/131866"),
            ("official_fmc_final_order_indexed_pdf_url",
             "https://www2.fmc.gov/readingroom/docs/23-01/WRONG.pdf"),
            ("final_order_link_is_raw_document_custody", True),
            ("final_order_pdf_content_independently_examined", True),
            ("final_order_original_pdf_bytes_custodied", True),
            ("final_order_original_pdf_sha256", "0" * 64),
        ):
            with self.subTest(synthetic_forgery=key), self.assertRaises(AssertionError):
                forged = json.loads(json.dumps(item))
                forged["source"][key] = replacement
                self._check(forged)

    def test_synthetic_controls_and_source_rights_stay_held(self):
        data = self._pack()
        controls = data["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(controls[-1]["id"],
                         "SYNTHETIC_MSC_THREE_VIOLATION_COHORT_CONFLATION")
        self.assertEqual(controls[-1]["expected"],
                         "REJECT_DISTINCT_COHORTS_AND_MARCH_2022_WILLFULNESS_BOUNDARY")
        self.assertEqual(data["quality"]["temporal_boundary_evidence_status"],
                         "FIRST_PARTY_FMC_PRESS_SUMMARY_REVIEWED_ORDER_PDF_BYTES_NOT_ACQUIRED")
        self.assertEqual(len({x["id"] for x in controls}), 5)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" and
                            x["id"].startswith("SYNTHETIC_") for x in controls))
        self.assertEqual(data["source"]["source_rights_status"],
                         "NOT_INDEPENDENTLY_ATTESTED_COMMERCIAL_ENGINE_REUSE_HOLD")
        self.assertFalse(data["quality"]["independent_original_order_and_invoice_custody"])

    def test_three_violation_periods_not_conflated_or_backdated(self):
        """FMC summary: 2018-20 notify, 2021 NOR; tariff willfulness only 2022-03."""
        original = self._pack()
        self._check(original)
        for key, forged_value in (
            ("notify_party_merchant_clause_billing_years", "2021_TO_2023"),
            ("nor_tariff_publication_violation_period", "2018_TO_2020"),
            ("nor_tariff_knowing_willful_start_month", "2021-01"),
            ("nor_overcharge_unreasonable_practice_year", 2023),
            ("cross_violation_invoice_error_inference_permitted", True),
        ):
            with self.subTest(synthetic_forgery=key):
                altered = json.loads(json.dumps(original))
                altered["publisher_reported_case"][key] = forged_value
                with self.assertRaises(AssertionError):
                    self._check(altered)

    def test_eleven_forged_promotion_attempts_rejected(self):
        original = self._pack()
        self._check(original)
        mutations = (
            ("cohort_share", lambda x: x["publisher_reported_case"].update(
                approximate_nor_bill_overcharge_share_percent=100)),
            ("generalization", lambda x: x["publisher_reported_case"].update(
                other_carriers_or_billing_years_extrapolation_permitted=True)),
            ("penalty_amount", lambda x: x["publisher_reported_case"].update(
                civil_penalty_total_assessed_cents=22670000)),
            ("treasury", lambda x: x["publisher_reported_case"].update(
                reported_penalty_payment_recipient="RETALLY")),
            ("paid_date", lambda x: x["publisher_reported_case"].update(
                payment_status_from_january_28_release="PAID_IN_JANUARY")),
            ("refund", lambda x: x["publisher_reported_case"].update(
                shipper_refunds_paid_total_cents=2267000000)),
            ("customer_labels", lambda x: x["ground_truth_limits"].update(
                independently_heldout_labeled_shipment_invoices=2629)),
            ("customer_recovery", lambda x: x["ground_truth_limits"].update(
                verified_retally_customer_recovery_cents=2267000000)),
            ("source_hash", lambda x: x["source"].update(
                final_order_original_pdf_sha256="0" * 64)),
            ("completeness", lambda x: x["quality"].update(
                case_level_labeling_complete=True)),
            ("commercial_rights", lambda x: x["source"].update(
                commercial_scoring_authorized=True)),
        )
        for name, mutation in mutations:
            with self.subTest(forgery=name), self.assertRaises(AssertionError):
                forged = json.loads(json.dumps(original))
                mutation(forged)
                self._check(forged)



def load_tests(loader, tests, pattern):
    """Route source-bound freight, accounting, and procurement safety tests to CI."""
    from freight import test_gao_b215958_supersession
    additional = loader.loadTestsFromModule(test_gao_b215958_supersession)
    if additional.countTestCases() < 3:
        raise AssertionError("GAO B-215958 temporal provenance test coverage missing")
    tests.addTests(additional)
    # Existing RecoveryOS GAO-02-635 publisher-level accounting controls
    # are held tests only, never customer accuracy or cash recovery labels.
    from freight import test_recoveryos_gao_ap_reconciliation_candidate
    accounting_controls = loader.loadTestsFromModule(
        test_recoveryos_gao_ap_reconciliation_candidate
    )
    if accounting_controls.countTestCases() != 4:
        raise AssertionError("GAO-02-635 accounting boundary tests missing")
    tests.addTests(accounting_controls)
    # Existing CaptureBrief FY2027 SAM.gov notice-identity controls remain
    # as-of metadata only: no solicitation/award or commercial-use proof.
    from freight import test_capturebrief_sam_fy2027_renumbering
    procurement_controls = loader.loadTestsFromModule(
        test_capturebrief_sam_fy2027_renumbering
    )
    if procurement_controls.countTestCases() != 3:
        raise AssertionError("SAM FY2027 notice-identity tests missing")
    tests.addTests(procurement_controls)
    # CBCA 3467-RATE is an adjudicated *negative* freight-overcharge case.
    # Preserve the published two-cent amount conflict and no-cash/no-rights hold.
    from freight import test_cbca_3467_detention_negative
    freight_negative_controls = loader.loadTestsFromModule(
        test_cbca_3467_detention_negative
    )
    if freight_negative_controls.countTestCases() != 4:
        raise AssertionError("CBCA 3467-RATE negative freight tests missing")
    tests.addTests(freight_negative_controls)
    # Historical GAO B-121220 limits documentary/payment evidence claims.
    # Register existing source-bound controls without admitting customer truth.
    from freight import test_gao_b121220_documentary_proof
    documentary_controls = loader.loadTestsFromModule(
        test_gao_b121220_documentary_proof
    )
    if documentary_controls.countTestCases() != 3:
        raise AssertionError("GAO B-121220 documentary-proof controls missing")
    tests.addTests(documentary_controls)
    return tests



class NYCDOBGeneralRightsBoundaryContract(unittest.TestCase):
    """First-party NYC use policy does not create permit/customer truth or bypass source terms."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_held(self, p):
        src = p["source"]
        policy = src["citywide_open_data_policy"]
        self.assertEqual(p["schema_version"], "0.1.3")
        self.assertEqual(p["engine"], "permitplate")
        self.assertEqual(src["reuse_rights"], "UNVERIFIED_HOLD")
        self.assertFalse(src["dataset_specific_commercial_reuse_authorized"])
        self.assertFalse(src["original_publisher_response_acquired"])
        self.assertIsNone(src["publisher_original_http_bytes_sha256"])
        self.assertEqual(policy["official_faq_url"],
                         "https://www.nyc.gov/opendata/get-started/FAQs")
        self.assertEqual(policy["official_technical_standards_url"],
                         "https://cityofnewyork.github.io/opendatatsm/publicpolicies.html")
        self.assertTrue(policy["citywide_general_open_data_use_unrestricted"])
        self.assertTrue(policy["source_and_version_disclosure_can_be_required_for_republication"])
        self.assertTrue(policy["additional_dataset_provider_terms_can_apply"])
        self.assertTrue(policy["publisher_does_not_warrant_completeness_or_accuracy"])
        self.assertTrue(policy["older_portal_dataset_versions_not_retained"])
        self.assertFalse(policy["dataset_specific_extra_terms_and_sensitive_field_review_completed"])
        self.assertFalse(policy["citywide_policy_is_customer_data_or_permit_validity_authorization"])
        self.assertFalse(policy["dataset_specific_commercial_scoring_approved"])
        self.assertIsNone(policy["source_original_response_sha256"])
        self.assertEqual(p["observed"]["held_out_labeled_permits"], 0)
        self.assertIsNone(p["observed"]["permitplate_scoring_precision_recall"])
        controls=p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 7)
        self.assertTrue(all(row["kind"] == "SYNTHETIC" for row in controls))
        self.assertEqual(controls[-1]["id"],
                         "SYNTH_CITYWIDE_OPEN_DATA_USE_EQUALS_AUTOMATIC_PERMIT_SCORING")

    def test_citywide_permission_but_dataset_specific_and_scoring_holds(self):
        self._assert_held(self._pack())

    def test_forged_rights_and_labels_are_rejected(self):
        pack = self._pack()
        mutants = [
            ("unrestricted", lambda q: q["source"]["citywide_open_data_policy"].update(
                citywide_general_open_data_use_unrestricted=False)),
            ("extra_terms", lambda q: q["source"]["citywide_open_data_policy"].update(
                additional_dataset_provider_terms_can_apply=False)),
            ("commercial", lambda q: q["source"].update(
                dataset_specific_commercial_reuse_authorized=True)),
            ("real_labels", lambda q: q["observed"].update(held_out_labeled_permits=1)),
            ("synthetic_tag", lambda q: q["synthetic_negative_controls"][-1].update(
                kind="REAL")),
        ]
        for name, mutate in mutants:
            with self.subTest(name=name):
                forged=json.loads(json.dumps(pack))
                mutate(forged)
                with self.assertRaises(AssertionError):
                    self._assert_held(forged)


class NYCDOBPublicAPIStatusExpiryBoundaryContract(unittest.TestCase):
    """Original public permit fields are not independent current-validity labels."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_boundary(self, p):
        self.assertEqual(p["schema_version"], "0.1.3")
        self.assertEqual(p["engine"], "permitplate")
        self.assertEqual(p["observed"]["held_out_labeled_permits"], 0)
        self.assertIsNone(p["observed"]["permitplate_scoring_precision_recall"])
        o = p["public_api_status_vs_expiration_observation"]
        self.assertEqual(o["source_url"],
                         "https://data.cityofnewyork.us/resource/rbx6-tga4.json")
        self.assertEqual(o["observed_date_et"], "2026-10-27")
        self.assertFalse(o["publisher_original_http_response_bytes_custodied"])
        self.assertIsNone(o["publisher_http_response_sha256"])
        self.assertFalse(o["upstream_snapshot_reproducible"])
        self.assertFalse(o["source_row_identity_stability_independently_verified"])
        self.assertTrue(o["source_excerpts_are_not_independent_permit_truth"])
        self.assertEqual(o["independently_held_out_labeled_permits_added"], 0)
        self.assertEqual(o["real_customer_outcome_labels_added"], 0)
        self.assertFalse(o["source_specific_commercial_scoring_authorized"])
        self.assertEqual(o["production_admission"],
                         "HOLD_SOURCE_METADATA_ONLY_NO_CUSTOMER_LEAD_OR_PERMIT_SCORING")
        rows = o["original_public_api_field_excerpts"]
        self.assertEqual(len(rows), 2)
        expired, unissued = rows
        self.assertEqual(expired["source_tracking_number"], "969875523")
        self.assertEqual(expired["source_reported_permit_status"], "Permit Issued")
        self.assertLess(expired["source_reported_expired_date"][:10],
                        o["observed_date_et"])
        self.assertIsNone(expired["independent_current_validity_label"])
        self.assertEqual(expired["expected_evaluation_boundary"],
                         "REJECT_PERMIT_ISSUED_STATUS_ALONE_AS_ACTIVE_ASOF_2026_10_27")
        self.assertEqual(unissued["source_tracking_number"], "593832799")
        self.assertEqual(unissued["source_reported_permit_status"], "Signed-off")
        self.assertEqual(unissued["source_reported_work_permit"],
                         "Permit is not yet issued")
        self.assertIsNone(unissued["source_reported_issued_date"])
        self.assertIsNone(unissued["independent_issued_permit_label"])
        self.assertEqual(unissued["expected_evaluation_boundary"],
                         "REJECT_SIGNED_OFF_STATUS_AS_PROOF_OF_AN_ISSUED_WORK_PERMIT")
        for row in rows:
            self.assertFalse(row["source_excerpt_is_independently_held_out_label"])
            for private in ("owner_name", "applicant_first_name",
                            "applicant_last_name", "house_no",
                            "street_name", "applicant_business_address"):
                self.assertNotIn(private, row)
        controls = o["retained_synthetic_negative_controls"]
        self.assertEqual(len(controls), 2)
        self.assertEqual(
            [c["id"] for c in controls],
            ["SYNTH_PUBLIC_STATUS_ISSUED_OVERRIDES_2025_EXPIRATION",
             "SYNTH_PUBLIC_SIGNED_OFF_BUT_NOT_ISSUED_IS_ISSUED"],
        )
        self.assertTrue(all(c["kind"] == "SYNTHETIC" for c in controls))

    def test_official_row_status_and_expiration_are_not_current_truth(self):
        self._assert_boundary(self._pack())

    def test_forged_issued_validity_rights_and_hash_promotions_rejected(self):
        initial = self._pack()
        okey = "public_api_status_vs_expiration_observation"
        changes = [
            ("raw_bytes", lambda q: q[okey].update(
                publisher_original_http_response_bytes_custodied=True)),
            ("fake_sha", lambda q: q[okey].update(
                publisher_http_response_sha256="unverified")),
            ("fake_labels", lambda q: q[okey].update(
                independently_held_out_labeled_permits_added=2)),
            ("fake_rights", lambda q: q[okey].update(
                source_specific_commercial_scoring_authorized=True)),
            ("future_expiration", lambda q: q[okey][
                "original_public_api_field_excerpts"][0].update(
                    source_reported_expired_date="2027-10-05T04:00:00.000")),
            ("fake_issuance", lambda q: q[okey][
                "original_public_api_field_excerpts"][1].update(
                    source_reported_issued_date="2026-10-27T00:00:00.000")),
            ("synthetic_as_real", lambda q: q[okey][
                "retained_synthetic_negative_controls"][0].update(kind="REAL")),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                forged = json.loads(json.dumps(initial))
                change(forged)
                with self.assertRaises(AssertionError):
                    self._assert_boundary(forged)



class NYCDOBFreshWriterReceiptBoundaryContract(unittest.TestCase):
    """Newest existing-writer readback is not original publisher custody or permit truth."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_boundary(self, p):
        self.assertEqual(p["schema_version"], "0.1.3")
        v = p["operational_writer_2026_10_28_readback_followup"]
        self.assertEqual(v["source_dataset_id"], "rbx6-tga4")
        self.assertEqual(v["observed_as_of_utc_date"], "2026-10-28")
        self.assertEqual(v["live_writer_head_commit"], "824d896a04f5fcccbddc6cce0691407377038220")
        self.assertEqual(v["live_writer_receipt_blob_git_sha1"], "f55dda41987641e74883964c544d0650ef256583")
        self.assertEqual(v["sample_count"], 20)
        self.assertEqual(v["projected_unique_source_identities"], 16)
        self.assertEqual(v["projected_repeated_source_rows"], 4)
        self.assertEqual(v["second_read_checked"], 3)
        self.assertEqual(v["second_read_exact_match"], 3)
        self.assertEqual(v["source_errors"], ["DUPLICATE_SOURCE_IDENTITIES"])
        self.assertEqual(v["receipt_status"], "PUBLISHER_REPLAY_DEGRADED")
        self.assertFalse(v["original_publisher_http_bytes_in_custody"])
        self.assertIsNone(v["original_publisher_http_bytes_sha256"])
        self.assertEqual(v["raw_permit_rows_copied"], 0)
        self.assertIsNone(v["independently_verified_distinct_permit_count"])
        self.assertEqual(v["independently_labeled_current_permit_validity"], 0)
        self.assertEqual(v["independently_labeled_issuance_outcomes"], 0)
        self.assertFalse(v["commercially_licensed_for_scoring"])
        self.assertFalse(v["repeated_counts_form_a_comparable_time_series"])
        self.assertEqual(v["production_admission"], "HOLD_REDACTED_WRITER_RECEIPT_ONLY")
        self.assertEqual(v["synthetic_negative_control"]["kind"], "SYNTHETIC")
        self.assertEqual(p["observed"]["held_out_labeled_permits"], 0)
        self.assertFalse(p["source"]["original_publisher_response_acquired"])

    def test_new_writer_readback_is_not_new_labeled_permit_truth(self):
        self._assert_boundary(self._pack())

    def test_forged_source_and_customer_promotions_rejected(self):
        original = self._pack()
        mutations = (
            ("custody", lambda v: v.update(original_publisher_http_bytes_in_custody=True)),
            ("raw_hash", lambda v: v.update(original_publisher_http_bytes_sha256="0" * 64)),
            ("labels", lambda v: v.update(independently_labeled_current_permit_validity=4)),
            ("duplicate_claim", lambda v: v.update(independently_verified_distinct_permit_count=20)),
            ("commercial", lambda v: v.update(commercially_licensed_for_scoring=True)),
            ("time_series", lambda v: v.update(repeated_counts_form_a_comparable_time_series=True)),
            ("synthetic_promotion", lambda v: v["synthetic_negative_control"].update(kind="ORIGINAL")),
            ("source_identity", lambda v: v.update(projected_unique_source_identities=20)),
            ("readback", lambda v: v.update(second_read_exact_match=4)),
        )
        for name, mutation in mutations:
            with self.subTest(synthetic_forgery=name):
                forged = json.loads(json.dumps(original))
                mutation(forged["operational_writer_2026_10_28_readback_followup"])
                with self.assertRaises(AssertionError):
                    self._assert_boundary(forged)


# Must follow every TestCase class; direct script execution otherwise skips late tests.
if __name__ == "__main__":
    unittest.main()
