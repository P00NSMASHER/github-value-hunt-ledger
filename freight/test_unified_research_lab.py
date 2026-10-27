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


def load_tests(loader, tests, pattern):
    """Include held GAO supersession regressions in the existing unified CI suite."""
    from freight import test_gao_b215958_supersession
    additional = loader.loadTestsFromModule(test_gao_b215958_supersession)
    if additional.countTestCases() < 3:
        raise AssertionError("GAO B-215958 temporal provenance test coverage missing")
    tests.addTests(additional)
    return tests


if __name__ == "__main__":
    unittest.main()
