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

# Reuse the existing unified CI lane for source-bound historical GAO deduction tests.
# A standalone test file is not selected by the workflow's fixed unittest list.
# The imported TestCase is discovered by unittest without any new provider call.
from freight.test_gao_b143950_collected_deduction import GAOB143950CollectedDeductionEvidenceTests as GAOB143950CollectedDeductionEvidenceTests
from freight.test_gao_b143491_adjusted_deduction import GAOB143491TariffCorrectionTests as GAOB143491TariffCorrectionTests

# Keep independently authored offline evidence tests discoverable by the existing
# unified PR verify command. These imports do not fetch providers or admit labels.
# Do not infer full Python CI success until the exact head is actually executed.
from freight.test_capturebrief_sam_fy2027_renumbering import SAMFY2027RenumberingEvidenceTests
from freight.test_cbca_3467_detention_negative import CBCADetentionNegativeControlTest
from freight.test_fmc_bakerly_22_17_admitted_errors import FMCBakerlyBoundaryTests as FMCBakerlyBoundaryTests
from freight.test_gao_b121220_documentary_proof import GAOB121220DocumentaryProofTests
from freight.test_gao_b215958_supersession import GAOB215958SupersessionTests
from freight.test_recoveryos_gao_ap_reconciliation_candidate import GAOAccountingReconCandidateTest
from freight.test_nara_2022_foia_bol_extraction import NARAOriginalBOLExtractionTests as NARAOriginalBOLExtractionTests

class GAOB166882DamagedFreightExclusionTests(unittest.TestCase):
    """Historical unearned-freight category must never be sold as tariff accuracy."""

    @staticmethod
    def pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "gao_b166882_damaged_delivery_unearned_freight_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    @staticmethod
    def held(d):
        try:
            s, p, h, t, q = (d["source"], d["published_decision"],
                             d["historical_shipments"], d["truth_boundaries"],
                             d["quality"])
            return (
                d["schema_version"] == "0.1.0"
                and d["pack_id"] == "GAO_B166882_DAMAGED_DELIVERY_UNEARNED_FREIGHT_CANDIDATE_V0"
                and d["evaluation_family"] == "FREIGHT_CHARGE_CATEGORY_EXCLUSION_NOT_TARIFF_RATE_ACCURACY"
                and d["admission_state"] == "PUBLIC_GAO_HISTORICAL_DECISION_FIXTURE_ONLY_NOT_CUSTOMER_EVALUATION"
                and s["official_url"] == "https://www.gao.gov/products/b-166882"
                and s["decision_id"] == "B-166882"
                and s["decision_date"] == "1969-11-18"
                and s["rights_url"] == "https://www.gao.gov/copyright"
                and "NO_IMPLIED_ENDORSEMENT" in s["rights_scope"]
                and s["original_publisher_http_sha256"] is None
                and s["original_publisher_http_bytes_held"] is False
                and s["original_signed_gbl_freight_bill_or_bank_bytes_held"] is False
                and s["controlling_historical_gbl_contract_pages_independently_acquired"] is False
                and s["historical_gbl_terms_effective_date_independently_verified"] is False
                and s["customer_commercial_evaluation_authorized"] is False
                and s["modern_contract_application"] == "UNKNOWN"
                and p["freight_charges_demanded_back_cents"] == 247468
                and p["separately_reported_shipments"] == 2
                and p["paid_to_carrier_reported_for_both_shipments"] is True
                and p["decision_freight_refund_demanded"] is True
                and p["refund_instruction_days"] == 60
                and p["refund_collected_cents"] is None
                and p["rate_overcharge_cents"] is None
                and p["independent_bank_refund_receipt_held"] is False
                and p["later_court_or_payment_outcome"] == "UNKNOWN"
                and p["physical_property_value_compensation_not_freight_refund"] is True
                and len(h) == 2
                and [x["source_published_gbl"] for x in h] == ["A-6242431", "B-7961821"]
                and [x["source_gbl_signed_date"] for x in h] == ["1967-05-09", "1966-09-19"]
                and [x["collected_freight_cents"] for x in h] == [207241, 40227]
                and sum(x["collected_freight_cents"] for x in h) == p["freight_charges_demanded_back_cents"]
                and len({x["case_key"] for x in h}) == 2
                and all(x["consignee_signed_delivery_certificate"] is True
                        and x["original_signed_paperwork_acquired"] is False
                        and x["refund_settlement_confirmed"] == "UNKNOWN" for x in h)
                and [x["damage_exception"] for x in h] == [
                    "DESTROYED_ON_GBL_REVERSE", "TOTAL_LOSS_ON_CARRIER_COMBINATION_BILL"]
                and h[0]["trailer_value_reportedly_paid_by_carrier_cents"] == 345000
                and h[0]["carrier_reported_salvage_proceeds_cents"] == 79200
                and h[1]["trailer_value_reportedly_paid_by_carrier_cents"] is None
                and h[1]["carrier_reported_salvage_proceeds_cents"] is None
                and t["historical_charge_category"] == "UNEARNED_FREIGHT_DAMAGED_DELIVERY_NOT_RERATING"
                and t["is_independently_verified_modern_tariff_rate_error"] is False
                and t["independently_heldout_modern_invoice_labels"] == 0
                and t["independently_complete_original_invoice_rate_shipment_payment_adjudication_cases"] == 0
                and t["independent_actual_freight_refund_receipts"] == 0
                and t["verified_retally_cash_cents"] == 0
                and t["customer_precision_recall"] == "UNKNOWN"
                and t["current_freight_case_truth"] == "UNKNOWN"
                and t["customer_admission_approved"] is False
                and t["supersession_exhaustively_checked"] is False
                and q["original_publisher_html_sha256_available"] is False
                and q["independent_original_customer_invoice_level_holdout_complete"] is False
                and q["cash_recovery_or_commercial_accuracy_certified"] is False
                and len(d["synthetic_negative_controls"]) == 7
                and len({x["id"] for x in d["synthetic_negative_controls"]}) == 7
                and all(x["kind"] == "SYNTHETIC"
                        and x["expected"].startswith("REJECT_")
                        for x in d["synthetic_negative_controls"])
                and d["handoff"]["engine_code_changed"] is False
                and d["handoff"]["release_approved"] is False
                and d["handoff"]["provider_requests_added"] == 0
            )
        except (KeyError, TypeError, ValueError):
            return False

    def test_original_gao_two_shipment_negative_category_is_held(self):
        self.assertTrue(self.held(self.pack()))

    def test_historical_freight_refund_demand_not_rate_or_recovered_cash(self):
        d = self.pack()
        self.assertEqual(d["published_decision"]["freight_charges_demanded_back_cents"],
                         207241 + 40227)
        self.assertIsNone(d["published_decision"]["refund_collected_cents"])
        self.assertIsNone(d["published_decision"]["rate_overcharge_cents"])
        self.assertEqual(d["truth_boundaries"]["verified_retally_cash_cents"], 0)

    def test_synthetic_forged_proof_or_rate_reclassification_fails_closed(self):
        original = self.pack()
        attacks = [
            (("source", "original_publisher_http_sha256"), "0" * 64),
            (("source", "original_signed_gbl_freight_bill_or_bank_bytes_held"), True),
            (("source", "customer_commercial_evaluation_authorized"), True),
            (("published_decision", "refund_collected_cents"), 247468),
            (("published_decision", "rate_overcharge_cents"), 247468),
            (("historical_shipments", 1, "collected_freight_cents"), 207241),
            (("historical_shipments", 0, "damage_exception"), "NO_DAMAGE_NOTED"),
            (("truth_boundaries", "independently_heldout_modern_invoice_labels"), 2),
            (("truth_boundaries", "verified_retally_cash_cents"), 247468),
            (("truth_boundaries", "historical_charge_category"), "TARIFF_RATE_OVERCHARGE"),
            (("quality", "cash_recovery_or_commercial_accuracy_certified"), True),
        ]
        for path, forged in attacks:
            with self.subTest(synthetic_forgery=str(path)):
                d = json.loads(json.dumps(original))
                target = d
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = forged
                self.assertFalse(self.held(d))
        self.assertTrue(self.held(original))


NOW = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)

# Pin the evolving NYC source-evidence pack once; historical receipt fields stay frozen.
NYC_DOB_REPLAY_PACK_SCHEMA_VERSION = "0.1.10"


class ProtectedMainOfficialSourceReconciliationTests(unittest.TestCase):
    """Hold six upstream source identities without admitting new provider hosts."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "protected_main_official_source_reconciliation_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_original_invoice_census_bridge(self, pack):
        """Aggregate public source receipt only, never independent error truth."""
        b = pack["ownership"]["private_original_invoice_blind_census_bridge"]
        self.assertEqual(b["evaluation_family"],
                         "ORIGINAL_INVOICE_CENSUS_ONLY_NOT_FREIGHT_ERROR_ACCURACY")
        self.assertEqual(b["authoritative_repository"],
                         "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(b["authoritative_main_commit"],
                         "02752be8074d3f08e9b2b2b8b5da9495da0381c7")
        self.assertEqual(b["merged_pr_url"],
                         "https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/872")
        self.assertEqual(b["public_documentation_git_blob_sha1"],
                         "51b49867abd34233888cb9410f5b4e33595c9e1a")
        self.assertEqual((b["original_invoice_faces_total"],
                          b["globaltranz_faces"], b["arcbest_faces"]), (110, 100, 10))
        self.assertEqual(b["globaltranz_faces"] + b["arcbest_faces"],
                         b["original_invoice_faces_total"])
        self.assertEqual(b["source_pdf_hashes_controlled_by"],
                         "EXISTING_ORIGINAL_DOCUMENT_LAB_NOT_THIS_PUBLIC_EVIDENCE_PACK")
        for key in ("source_documents_newly_harvested_by_unified_lab",
                    "independent_buyer_rate_bol_payment_adjudication_complete_cases",
                    "independently_adjudicated_positive_negative_truth_labels",
                    "verified_retally_recovery_cents",
                    "new_research_writer_or_provider_runs"):
            self.assertEqual(b[key], 0, key)
        for key in ("private_original_pdf_bytes_in_unified_lab_custody",
                    "buyer_specific_commercial_use_rights_cleared_by_unified_lab",
                    "commercial_or_production_scoring_authorized"):
            self.assertIs(b[key], False, key)
        self.assertEqual(b["accuracy_precision_recall"], "UNKNOWN_NOT_ESTIMABLE")
        self.assertEqual(b["required_independent_artifact_types"],
                         ["rate", "shipment", "payment", "adjudication"])
        self.assertEqual(b["handoff_freightrecovery_recoveryos_12"],
                         "USE_EXISTING_SOURCE_CENSUS_BRIDGE_NO_DUPLICATE_PDF_COLLECTION")
        controls = b["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and c["expected"] == "REJECT"
                            for c in controls))

    def test_main_110_original_invoice_faces_are_source_census_only(self):
        self._assert_original_invoice_census_bridge(self._pack())

    def test_main_110_original_invoice_false_promotions_rejected(self):
        changes = (
            ("original_invoice_faces_total", 109),
            ("arcbest_faces", 11),
            ("authoritative_main_commit", "0" * 40),
            ("public_documentation_git_blob_sha1", "0" * 40),
            ("source_documents_newly_harvested_by_unified_lab", 110),
            ("private_original_pdf_bytes_in_unified_lab_custody", True),
            ("independently_adjudicated_positive_negative_truth_labels", 110),
            ("independent_buyer_rate_bol_payment_adjudication_complete_cases", 110),
            ("commercial_or_production_scoring_authorized", True),
            ("buyer_specific_commercial_use_rights_cleared_by_unified_lab", True),
            ("verified_retally_recovery_cents", 1),
            ("accuracy_precision_recall", "1.00"),
            ("source_pdf_hashes_controlled_by", "UNIFIED_LAB"),
        )
        for key, bad in changes:
            with self.subTest(synthetic_forgery=key):
                p = json.loads(json.dumps(self._pack()))
                p["ownership"]["private_original_invoice_blind_census_bridge"][key] = bad
                with self.assertRaises(AssertionError):
                    self._assert_original_invoice_census_bridge(p)
        p = json.loads(json.dumps(self._pack()))
        p["ownership"]["private_original_invoice_blind_census_bridge"][
            "synthetic_negative_controls"][0]["kind"] = "ORIGINAL"
        with self.assertRaises(AssertionError):
            self._assert_original_invoice_census_bridge(p)

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
            self.assertIn(row["url"], SEEDS["freightrecovery"])
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
        self.assertEqual(pack["schema_version"], "0.1.1")
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
            self.assertIn(row["url"], SEEDS["freightrecovery"])
            self.assertEqual(safe_url(row["url"]), row["url"])  # Safe URL != source rights.
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
        self.assertIn(item["source"]["order_url"], SEEDS["freightrecovery"])
        self.assertIn(item["source"]["nonreview_notice_url"], SEEDS["freightrecovery"])

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
        self.assertTrue(all(url in SEEDS["freightrecovery"] for url in expected))
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
        self.assertTrue(all(url in SEEDS["freightrecovery"] for url in retained))
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
        self.assertIs(record["quality"]["case_level_labeling_complete"], False)
        self.assertIs(record["quality"]["invoice_level_labeling_complete"], False)
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
        self.assertEqual(len({x["id"] for x in controls}), 6)
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
    """Require all five existing evidence cohorts without running them twice.

    unittest already discovers the imported TestCase classes above. Appending
    the same modules here executed 17 offline controls twice; retain exact
    cohort counts while letting the standard loader execute each test once.
    """
    required = (
        (GAOB215958SupersessionTests, 3),
        (GAOAccountingReconCandidateTest, 4),
        (SAMFY2027RenumberingEvidenceTests, 3),
        (CBCADetentionNegativeControlTest, 4),
        (GAOB121220DocumentaryProofTests, 3),
    )
    for case, expected in required:
        if loader.loadTestsFromTestCase(case).countTestCases() != expected:
            raise AssertionError(f"Evidence coverage drift: {case.__name__}")
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
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
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
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
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
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
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


class NYCDOBPublisherCatalogMetadataQualityBoundary(unittest.TestCase):
    """First-party cached counts must not become real permit IDs, labels or current leads."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_metadata_held(self, p):
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
        q = p["official_socrata_catalog_metadata_quality_2026_10_28"]
        self.assertEqual(q["dataset_id"], "rbx6-tga4")
        self.assertEqual(q["official_metadata_url"],
                         "https://data.cityofnewyork.us/api/views/rbx6-tga4")
        self.assertEqual(q["publisher_rows_updated_at_utc"], "2026-10-27T18:42:06Z")
        self.assertEqual(q["cached_total_row_count"], 1020884)
        self.assertEqual(q["cached_permit_status_signed_off_count"], 652613)
        self.assertEqual(q["cached_permit_status_permit_issued_count"], 368271)
        self.assertEqual(
            q["cached_permit_status_signed_off_count"] +
            q["cached_permit_status_permit_issued_count"],
            q["cached_total_row_count"])
        self.assertEqual(q["cached_filing_reason_no_work_permit_count"], 6765)
        self.assertEqual(q["cached_work_permit_not_yet_issued_count"], 344)
        self.assertEqual(q["cached_issued_date_null_count"], 343)
        self.assertEqual(q["cached_sequence_number_null_count"], 351)
        self.assertEqual(q["cached_tracking_number_null_count"], 1)
        self.assertEqual(q["cached_top_tracking_number_frequency"], 8)
        self.assertEqual(q["cached_job_filing_number_placeholder"], "Permit is no")
        self.assertEqual(q["cached_job_filing_number_placeholder_frequency"], 344)
        self.assertEqual(q["cached_job_filing_number_null_count"], 212)
        self.assertEqual(q["cached_job_filing_number_placeholder_frequency"],
                         q["cached_work_permit_not_yet_issued_count"])
        self.assertEqual(q["source_scope_excludes"],
                         ["ELECTRICAL", "ELEVATOR", "LIMITED_ALTERATION_APPLICATION_LAA"])
        self.assertTrue(q["cached_statistics_snapshot_not_independent_row_labels"])
        for key in (
            "original_catalog_http_response_bytes_custodied",
            "publisher_cached_counts_verified_as_live_row_level_query",
            "source_tracking_number_globally_unique_verified",
            "cached_column_cardinality_is_distinct_filing_identity_count",
            "placeholder_frequency_and_work_permit_sentinel_same_rows_verified",
            "placeholder_value_proves_distinct_issued_permits",
            "source_cached_status_proves_current_permit_validity",
            "source_covers_all_nyc_building_permits",
            "source_specific_commercial_scoring_authorized",
        ):
            self.assertFalse(q[key], key)
        self.assertIsNone(q["original_catalog_http_response_sha256"])
        for key in (
            "independently_held_out_labeled_current_permits",
            "independently_held_out_labeled_customer_outcomes",
            "customer_proven_lead_count", "original_raw_permit_or_personal_records_stored",
        ):
            self.assertEqual(q[key], 0, key)
        controls = q["synthetic_negative_controls"]
        self.assertEqual(len(controls), 6)
        self.assertEqual(len({c["id"] for c in controls}), 6)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" for c in controls))
        self.assertEqual(q["production_admission"],
                         "HOLD_PUBLISHER_CACHED_CATALOG_METADATA_ONLY")

    def test_cached_publisher_status_counts_are_not_independent_permit_truth(self):
        self._assert_metadata_held(self._pack())

    def test_forged_counts_identity_custody_rights_and_labels_rejected(self):
        original = self._pack()
        key = "official_socrata_catalog_metadata_quality_2026_10_28"
        mutations = (
            ("active_status", lambda q: q.update(source_cached_status_proves_current_permit_validity=True)),
            ("tracking_unique", lambda q: q.update(source_tracking_number_globally_unique_verified=True)),
            ("all_categories", lambda q: q.update(source_covers_all_nyc_building_permits=True)),
            ("live_counts", lambda q: q.update(publisher_cached_counts_verified_as_live_row_level_query=True)),
            ("cached_frequency", lambda q: q.update(cached_top_tracking_number_frequency=1)),
            ("truncated_placeholder", lambda q: q.update(cached_job_filing_number_placeholder="B01234567-I1")),
            ("placeholder_frequency", lambda q: q.update(cached_job_filing_number_placeholder_frequency=0)),
            ("placeholder_null", lambda q: q.update(cached_job_filing_number_null_count=0)),
            ("placeholder_promoted", lambda q: q.update(placeholder_value_proves_distinct_issued_permits=True)),
            ("false_row_join", lambda q: q.update(placeholder_frequency_and_work_permit_sentinel_same_rows_verified=True)),
            ("false_cardinality", lambda q: q.update(cached_column_cardinality_is_distinct_filing_identity_count=True)),
            ("no_work_rows", lambda q: q.update(cached_filing_reason_no_work_permit_count=0)),
            ("fake_labels", lambda q: q.update(independently_held_out_labeled_current_permits=1)),
            ("fake_rights", lambda q: q.update(source_specific_commercial_scoring_authorized=True)),
            ("fake_bytes", lambda q: q.update(original_catalog_http_response_bytes_custodied=True)),
            ("fake_sha", lambda q: q.update(original_catalog_http_response_sha256="0"*64)),
            ("synthetic_to_real", lambda q: q["synthetic_negative_controls"][0].update(kind="ORIGINAL")),
        )
        for label, mutate in mutations:
            with self.subTest(forgery=label):
                poisoned = json.loads(json.dumps(original))
                mutate(poisoned[key])
                with self.assertRaises(AssertionError):
                    self._assert_metadata_held(poisoned)


    def _assert_current_catalog_update_boundary(self, p):
        q = p["official_socrata_catalog_refresh_2026_10_28"]
        prior = p["official_socrata_catalog_metadata_quality_2026_10_28"]
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
        self.assertEqual(q["schema_version"], "0.1.0")
        self.assertEqual(q["dataset_id"], "rbx6-tga4")
        self.assertEqual(q["original_catalog_metadata_url"],
                         "https://data.cityofnewyork.us/api/views/rbx6-tga4")
        self.assertEqual(q["previous_catalog_rows_updated_at_utc"],
                         prior["publisher_rows_updated_at_utc"])
        self.assertEqual(q["publisher_rows_updated_at_epoch_seconds"], 1793213280)
        self.assertEqual(q["publisher_rows_updated_at_utc"],
                         "2026-10-28T18:48:00Z")
        self.assertEqual(q["publisher_view_last_modified_epoch_seconds"], 1793212310)
        self.assertEqual(q["publisher_view_last_modified_utc"],
                         "2026-10-28T18:31:50Z")
        self.assertTrue(q["new_catalog_timestamp_after_previous"])
        self.assertTrue(q["source_reported_cached_counts_stable_across_two_metadata_views"])
        self.assertEqual(q["compared_cached_fields"], {
            "cached_total_row_count": 1020884,
            "cached_permit_status_signed_off_count": 652613,
            "cached_permit_status_permit_issued_count": 368271,
            "cached_job_filing_number_placeholder_frequency": 344,
        })
        for k, v in q["compared_cached_fields"].items():
            self.assertEqual(v, prior[k], k)
        for field in ("original_publisher_http_response_bytes_custodied",
                      "independently_replayed_row_level_api_in_this_run",
                      "timestamp_change_proves_new_unique_permits",
                      "same_cached_counts_prove_no_rows_changed",
                      "timestamp_change_proves_current_permit_validity",
                      "dataset_specific_extra_terms_and_customer_scoring_review_complete"):
            self.assertIs(q[field], False, field)
        self.assertIsNone(q["original_publisher_http_response_sha256"])
        self.assertTrue(q["semantic_observation_not_raw_source_hash"])
        self.assertTrue(q["citywide_general_open_data_reuse_allowed"])
        self.assertEqual(q["commercial_scoring_authorization"], "HOLD")
        self.assertEqual(q["production_admission"], "HOLD")
        self.assertEqual(q["independent_held_out_current_validity_labels"], 0)
        self.assertEqual(q["raw_personal_or_permit_rows_stored"], 0)
        controls = q["synthetic_negative_controls"]
        self.assertEqual(len(controls), 2)
        self.assertEqual(len({c["id"] for c in controls}), 2)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" for c in controls))

    def test_catalog_clock_advanced_but_cached_counts_are_not_live_truth(self):
        self._assert_current_catalog_update_boundary(self._pack())

    def test_forged_catalog_refresh_claims_rejected(self):
        original = self._pack()
        attacks = (
            ("false_timestamp", "publisher_rows_updated_at_utc", "2026-10-27T18:42:06Z"),
            ("false_count", "compared_cached_fields", {"cached_total_row_count": 1}),
            ("new_permits", "timestamp_change_proves_new_unique_permits", True),
            ("no_row_changes", "same_cached_counts_prove_no_rows_changed", True),
            ("permit_validity", "timestamp_change_proves_current_permit_validity", True),
            ("fake_source_bytes", "original_publisher_http_response_bytes_custodied", True),
            ("fake_source_hash", "original_publisher_http_response_sha256", "0"*64),
            ("fake_labels", "independent_held_out_current_validity_labels", 1),
            ("fake_commercial", "commercial_scoring_authorization", "APPROVED"),
        )
        for name, field, fake in attacks:
            with self.subTest(forgery=name):
                tampered = json.loads(json.dumps(original))
                tampered["official_socrata_catalog_refresh_2026_10_28"][field] = fake
                with self.assertRaises(AssertionError):
                    self._assert_current_catalog_update_boundary(tampered)



class FMCTCWEvergreenDocketCollisionBoundary(unittest.TestCase):
    """Publisher typo must not split one adjudicated case into two labels."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "fmc_tcw_1966i_docket_collision_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_boundary(self, p):
        self.assertEqual(p["schema_version"], "0.1.0")
        self.assertEqual(p["fixture_id"],
                         "FMC_TCW_EVERGREEN_1966I_APPELLATE_DOCKET_IDENTITY_COLLISION_HELD_V0")
        s = p["source"]
        f = p["published_case_facts"]
        q = p["truth_and_quality"]
        self.assertEqual(s["court_docket"], "25-1104")
        self.assertEqual(s["fmc_correct_proceeding_docket"], "1966(I)")
        self.assertEqual(s["fmc_2023_press_body_docket"], "1996(I)")
        self.assertEqual(s["fmc_2023_press_link_target_docket"], "1966(I)")
        self.assertEqual(s["fmc_2026_press_docket"], "1966(I)")
        self.assertEqual(s["docket_resolution"],
                         "1966(I)_PER_FIRST_PARTY_INDEX_AND_2023_LINK_TARGET_NOT_PRESS_BODY_1996(I)")
        self.assertEqual(s["proceeding_index_http_access"],
                         "INDEXED_PUBLIC_TEXT_DIRECT_OPEN_403")
        self.assertEqual(s["court_decision_pdf_pages_checked"], [3, 5])
        self.assertTrue(s["court_pdf_visually_checked_via_public_view"])
        self.assertFalse(s["original_court_pdf_http_bytes_in_custody"])
        self.assertIsNone(s["original_court_pdf_http_sha256"])
        self.assertFalse(s["raw_publisher_response_integrity_verified"])
        self.assertFalse(s["commercial_invoice_scoring_rights_verified"])
        self.assertEqual(f["port_closed_dates"],
                         ["2020-05-23", "2020-05-24", "2020-05-25"])
        self.assertEqual(f["port_closed_days"] *
                         (f["container_daily_rate_cents"] +
                          f["chassis_daily_rate_cents"]), 51000)
        self.assertEqual(f["court_reported_total_detention_invoice_cents"], 149000)
        self.assertEqual(f["court_reported_disputed_detention_cents"], 51000)
        self.assertTrue(f["court_reports_invoice_paid_before_complaint"])
        self.assertFalse(f["original_invoice_or_bank_payment_bytes_held"])
        self.assertFalse(f["all_original_invoice_charges_held_invalid"])
        self.assertFalse(f["final_customer_refund_bank_verified"])
        self.assertIsNone(f["actual_customer_refund_amount_cents"])
        self.assertEqual(f["automatic_modern_claim_eligibility"], "UNKNOWN")
        self.assertEqual(q["published_adjudicated_historical_case_count"], 1)
        self.assertEqual(q["independent_heldout_invoice_labels"], 0)
        self.assertFalse(q["sample_is_independent_from_existing_real_world_eval_v1"])
        self.assertFalse(q["additional_unique_invoice_case_created"])
        self.assertEqual(q["existing_casebook_reference"], "EVERGREEN_TCW_2026_COURT")
        self.assertEqual(q["verified_retally_customer_cash_recovery_cents"], 0)
        self.assertEqual(q["commercial_admission"], "HOLD")
        self.assertEqual(len(p["synthetic_negative_controls"]), 5)
        self.assertEqual(len({x["id"] for x in p["synthetic_negative_controls"]}), 5)
        self.assertTrue(all(x["kind"] == "SYNTHETIC"
                            for x in p["synthetic_negative_controls"]))

    def test_docket_identity_and_historical_invoice_boundary(self):
        self._assert_boundary(self._pack())

    def test_forged_identity_custody_rights_and_cash_are_rejected(self):
        source = self._pack()
        mutations = (
            ("press_typo_promoted", lambda d: d["source"].update(
                fmc_correct_proceeding_docket="1996(I)")),
            ("collision_hidden", lambda d: d["source"].update(
                fmc_2023_press_body_docket="1966(I)")),
            ("court_docket_forged", lambda d: d["source"].update(
                court_docket="1996(I)")),
            ("pdf_custody_forged", lambda d: d["source"].update(
                original_court_pdf_http_bytes_in_custody=True)),
            ("publisher_hash_forged", lambda d: d["source"].update(
                original_court_pdf_http_sha256="0" * 64)),
            ("commercial_rights_forged", lambda d: d["source"].update(
                commercial_invoice_scoring_rights_verified=True)),
            ("whole_invoice_false_positive", lambda d: d["published_case_facts"].update(
                court_reported_disputed_detention_cents=149000)),
            ("bank_receipt_forged", lambda d: d["published_case_facts"].update(
                original_invoice_or_bank_payment_bytes_held=True)),
            ("customer_cash_forged", lambda d: d["truth_and_quality"].update(
                verified_retally_customer_cash_recovery_cents=51000)),
            ("duplicate_case_mislabelled_holdout", lambda d: d["truth_and_quality"].update(
                independent_heldout_invoice_labels=1)),
            ("synthetic_mislabelled_real", lambda d: d["synthetic_negative_controls"][0].update(
                kind="ORIGINAL")),
        )
        for name, mutation in mutations:
            with self.subTest(forgery=name):
                forged = json.loads(json.dumps(source))
                mutation(forged)
                with self.assertRaises(AssertionError):
                    self._assert_boundary(forged)



class GAOB221594AgencyTenderScopeHeldTests(unittest.TestCase):
    """A rejected DOD tender cannot be assumed invalid for unrelated agencies."""

    @staticmethod
    def _pack():
        return json.loads(
            (Path(__file__).with_name("fixtures") /
             "gao_b221594_dod_tender_scope_candidate_v0.json").read_text(
                 encoding="utf-8")
        )

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], "0.1.0")
        self.assertEqual(p["fixture_id"],
                         "GAO_B221594_MTMC_REJECTED_TENDER_DOD_SCOPE_NEGATIVE_HELD_V0")
        self.assertEqual(p["engine"], "freightrecovery")
        self.assertEqual(p["evaluation_family"],
                         "HISTORICAL_GAO_FREIGHT_ERROR_FALSE_POSITIVE_SCOPE_ONLY")
        s = p["source"]
        h = p["historical_facts"]
        q = p["ground_truth"]
        self.assertEqual(set(p), {
            "schema_version", "fixture_id", "engine", "evaluation_family",
            "cohort", "source", "historical_facts", "ground_truth",
            "synthetic_negative_controls"})
        self.assertEqual(set(s), {
            "official_url", "rights_reference", "publisher", "decision_date",
            "verified_public_text_date", "source_format", "rights_scope",
            "commercial_customer_scoring_admission",
            "original_publisher_response_bytes_acquired",
            "original_publisher_response_sha256",
            "original_invoice_gbl_tender_bank_bytes_acquired"})
        self.assertEqual(set(h), {
            "carrier", "tender_id", "tender_stated_effective_date",
            "mtmc_return_date", "tender_refiled_and_approved_before_dod_shipment",
            "illustrative_dod_shipper", "illustrative_service_date",
            "reported_shipment_weight_lb", "reported_paid_cents",
            "gsa_setoff_collected_cents", "gao_source_ocr_lower_charge",
            "gsa_implied_lower_charge_cents", "lower_charge_provenance",
            "gao_dod_audit_disposition", "dod_similar_claims_scope",
            "gaos_footnote_non_dod_boundary", "non_dod_tender_validity",
            "actual_carrier_refund_or_repayment_confirmed"})
        self.assertEqual(set(q), {
            "original_publisher_adjudicated_historical_case_count",
            "independently_heldout_original_invoice_labels",
            "original_buyer_specific_rate_chain_complete",
            "modern_customer_contract_applicability",
            "automatic_current_customer_error_scoring_allowed",
            "commercial_reuse_authorized",
            "verified_retally_customer_recovery_cents"})
        self.assertEqual(p["cohort"],
                         "US_GSA_DOD_MOTOR_FREIGHT_SEPTEMBER_1983_ADJUDICATED_1986")
        self.assertEqual(s["publisher"], "U.S. Government Accountability Office")
        self.assertEqual(s["verified_public_text_date"], "2026-10-28")
        self.assertEqual(s["source_format"], "OFFICIAL_PUBLISHED_DECISION_HTML")
        self.assertEqual(s["rights_scope"],
                         "GAO_TEXT_US_PUBLIC_DOMAIN_WITH_ACKNOWLEDGMENT_NO_ENDORSEMENT_THIRD_PARTY_RIGHTS_SEPARATE")
        self.assertEqual(h["carrier"], "RISS_INTERNATIONAL")
        self.assertEqual(s["official_url"],
                         "https://www.gao.gov/products/b-221594-0")
        self.assertEqual(s["rights_reference"], "https://www.gao.gov/copyright")
        self.assertEqual(s["decision_date"], "1986-09-29")
        self.assertEqual(s["commercial_customer_scoring_admission"], "HOLD")
        self.assertFalse(s["original_publisher_response_bytes_acquired"])
        self.assertIsNone(s["original_publisher_response_sha256"])
        self.assertFalse(s["original_invoice_gbl_tender_bank_bytes_acquired"])
        self.assertEqual(h["tender_id"], "ICC_TENDER_1544")
        self.assertEqual(h["tender_stated_effective_date"], "1983-01-15")
        self.assertEqual(h["mtmc_return_date"], "1983-02-17")
        self.assertFalse(h["tender_refiled_and_approved_before_dod_shipment"])
        self.assertEqual(h["illustrative_dod_shipper"], "US_ARMY")
        self.assertEqual(h["illustrative_service_date"], "1983-09-07")
        self.assertEqual(h["reported_shipment_weight_lb"], 27792)
        self.assertEqual(h["reported_paid_cents"], 94200)
        self.assertEqual(h["gsa_setoff_collected_cents"], 22075)
        self.assertEqual(h["gao_source_ocr_lower_charge"], "$72L.25")
        self.assertEqual(h["gsa_implied_lower_charge_cents"], 72125)
        self.assertEqual(h["reported_paid_cents"] - h["gsa_setoff_collected_cents"],
                         h["gsa_implied_lower_charge_cents"])
        self.assertEqual(h["lower_charge_provenance"],
                         "ARITHMETIC_94200_MINUS_22075_NOT_EXACT_OCR_EXTRACTION")
        self.assertEqual(h["gao_dod_audit_disposition"],
                         "SET_OFF_INVALID_TENDER_REJECTED_BEFORE_DOD_SHIPMENT")
        self.assertEqual(h["dod_similar_claims_scope"],
                         "SETTLE_CONSISTENTLY_ABSENT_PROOF_REFILED_AND_MTMC_APPROVED")
        self.assertEqual(h["gaos_footnote_non_dod_boundary"],
                         "MTMC_REJECTION_ALONE_DOES_NOT_BLOCK_AGENCIES_OUTSIDE_MTMC_JURISDICTION_UNLESS_THEY_ALSO_REJECTED")
        self.assertEqual(h["non_dod_tender_validity"],
                         "UNKNOWN_AGENCY_SPECIFIC_REJECTION_AND_ACCEPTANCE_REQUIRED")
        self.assertIsNone(h["actual_carrier_refund_or_repayment_confirmed"])
        self.assertEqual(q["original_publisher_adjudicated_historical_case_count"], 1)
        self.assertEqual(q["independently_heldout_original_invoice_labels"], 0)
        self.assertFalse(q["original_buyer_specific_rate_chain_complete"])
        self.assertEqual(q["modern_customer_contract_applicability"], "UNKNOWN")
        self.assertFalse(q["automatic_current_customer_error_scoring_allowed"])
        self.assertFalse(q["commercial_reuse_authorized"])
        self.assertEqual(q["verified_retally_customer_recovery_cents"], 0)
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({x["id"] for x in controls}), 5)
        self.assertTrue(all(set(x) == {"id", "kind", "inference", "expected"}
                            for x in controls))
        self.assertTrue(all(x["kind"] == "SYNTHETIC" for x in controls))
        self.assertEqual([x["id"] for x in controls], [
            "SYNTHETIC_MTMc_REJECTION_INVALID_FOR_ALL_AGENCIES",
            "SYNTHETIC_NON_DOD_TENDER_ALWAYS_VALID",
            "SYNTHETIC_GSA_DEDUCTION_COUNTS_AS_CUSTOMER_CASH",
            "SYNTHETIC_OCR_72125_PUBLISHER_EXPLICIT",
            "SYNTHETIC_GAO_PAGE_IS_ORIGINAL_INVOICE"])
        self.assertEqual(
            [x["expected"] for x in controls],
            ["REJECT_NON_DOD_SCOPE_MUST_BE_EVALUATED_SEPARATELY",
             "UNKNOWN_OTHER_AGENCY_REJECTION_OR_ACCEPTANCE_NOT_ESTABLISHED",
             "REJECT_GSA_HISTORY_NOT_CUSTOMER_BANK_CREDIT",
             "REJECT_72125_DERIVED_FROM_DIFFERENCE_ONLY",
             "REJECT_NO_ORIGINAL_DOCUMENT_CUSTODY"]
        )

    def test_dod_rejection_is_not_blanket_non_dod_invalidity(self):
        self._assert_scope(self._pack())

    def test_forged_cross_agency_custody_cash_and_labels_rejected(self):
        p = self._pack()
        mutations = (
            lambda x: x["historical_facts"].update(
                non_dod_tender_validity="INVALID_FOR_ALL_AGENCIES"),
            lambda x: x["historical_facts"].update(
                gaos_footnote_non_dod_boundary="MTMC_REJECTION_APPLIES_EVERYWHERE"),
            lambda x: x["historical_facts"].update(mtmc_return_date="1983-09-08"),
            lambda x: x["historical_facts"].update(
                tender_refiled_and_approved_before_dod_shipment=True),
            lambda x: x["historical_facts"].update(
                lower_charge_provenance="PUBLISHER_EXPLICIT"),
            lambda x: x["historical_facts"].update(gsa_implied_lower_charge_cents=72124),
            lambda x: x["source"].update(
                original_publisher_response_sha256="0" * 64),
            lambda x: x["source"].update(
                original_invoice_gbl_tender_bank_bytes_acquired=True),
            lambda x: x["source"].update(
                commercial_customer_scoring_admission="APPROVED"),
            lambda x: x["ground_truth"].update(
                independently_heldout_original_invoice_labels=1),
            lambda x: x["ground_truth"].update(
                verified_retally_customer_recovery_cents=22075),
            lambda x: x["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
            lambda x: x["source"].update(unverified_customer_refund=True),
            lambda x: x["ground_truth"].update(independent_bank_receipt=True),
            lambda x: x["synthetic_negative_controls"][0].update(
                {"independent_original_invoice": True}),
            lambda x: x["source"].update(
                rights_scope="AUTOMATED_CUSTOMER_SCORING_APPROVED"),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(forgery=index):
                forged = json.loads(json.dumps(p))
                mutation(forged)
                with self.assertRaises(AssertionError):
                    self._assert_scope(forged)



class NYCDOBMetadataDriftClockInvariantTests(unittest.TestCase):
    """Publisher cached totals changed while two catalog update clocks did not."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json").read_text(
                               encoding="utf-8"))

    @staticmethod
    def _assert_quality(p):
        assert p["schema_version"] == NYC_DOB_REPLAY_PACK_SCHEMA_VERSION
        q = p["official_socrata_catalog_cached_count_drift_same_clock_2026_10_28"]
        assert q["publisher_rows_updated_at_epoch_seconds_in_both_views"] == 1793213280
        assert q["publisher_view_last_modified_epoch_seconds_in_both_views"] == 1793212310
        previous = {"total": 1020884, "signed": 652613, "issued": 368271, "no_work": 6765}
        current = {"total": 1021662, "signed": 653292, "issued": 368370, "no_work": 6766}
        assert q["earlier_cached_counts"] == previous
        assert q["later_cached_counts"] == current
        assert q["source_reported_cached_count_deltas"] == {
            k: current[k] - previous[k] for k in previous}
        assert q["source_reported_cached_count_deltas"]["total"] == (
            q["source_reported_cached_count_deltas"]["signed"] +
            q["source_reported_cached_count_deltas"]["issued"])
        for field in ("clock_fields_unchanged_across_views",
                      "cached_counts_changed_across_views",
                      "status_count_deltas_balance_total"):
            assert q[field] is True, field
        for field in ("clock_fields_sufficient_cache_fingerprint",
                      "original_publisher_http_bytes_acquired",
                      "raw_live_row_replay_executed"):
            assert q[field] is False, field
        assert q["original_publisher_http_sha256"] is None
        assert q["independent_held_out_permit_labels"] == 0
        assert q["commercial_use_approval"] == "HOLD"
        assert q["production_admission"] == "HOLD"
        assert len(q["synthetic_negative_controls"]) == 4
        assert all(v["kind"] == "SYNTHETIC" for v in q["synthetic_negative_controls"])

    def test_first_party_catalog_metadata_count_drift_boundary(self):
        self._assert_quality(self._pack())

    def test_forged_active_validity_hash_and_commercial_rights_rejected(self):
        import copy
        for field, value in (
            ("clock_fields_sufficient_cache_fingerprint", True),
            ("original_publisher_http_sha256", "0" * 64),
            ("independent_held_out_permit_labels", 1),
            ("commercial_use_approval", "APPROVED"),
            ("publisher_rows_updated_at_epoch_seconds_in_both_views", 1),
        ):
            with self.subTest(field=field):
                forged = copy.deepcopy(self._pack())
                forged["official_socrata_catalog_cached_count_drift_same_clock_2026_10_28"][field] = value
                with self.assertRaises(AssertionError):
                    self._assert_quality(forged)
        for field, value in (("total", 1), ("issued", 778)):
            with self.subTest(field=field):
                forged = copy.deepcopy(self._pack())
                row = "later_cached_counts" if field == "total" else "source_reported_cached_count_deltas"
                forged["official_socrata_catalog_cached_count_drift_same_clock_2026_10_28"][row][field] = value
                with self.assertRaises(AssertionError):
                    self._assert_quality(forged)
        forged = copy.deepcopy(self._pack())
        forged["official_socrata_catalog_cached_count_drift_same_clock_2026_10_28"]["synthetic_negative_controls"][0]["kind"] = "ORIGINAL"
        with self.assertRaises(AssertionError):
            self._assert_quality(forged)


class NYCDOBUnsortedReadbackChurnBoundaryTests(unittest.TestCase):
    """Two changing unsorted writer receipts are not independent permit identities."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json").read_text(
                               encoding="utf-8"))

    @staticmethod
    def _assert_scope(p):
        assert p["schema_version"] == NYC_DOB_REPLAY_PACK_SCHEMA_VERSION
        q = p["operational_writer_unsorted_identity_churn_2026_10_29"]
        assert q["source_dataset_id"] == "rbx6-tga4"
        a = q["previous_writer_snapshot"]
        b = q["current_writer_snapshot"]
        assert (a["sample_rows"], a["projected_unique_identities"],
                a["projected_repeated_rows"]) == (20, 16, 4)
        assert (b["sample_rows"], b["projected_unique_identities"],
                b["projected_repeated_rows"]) == (20, 18, 2)
        assert a["projected_unique_identities"] + a["projected_repeated_rows"] == 20
        assert b["projected_unique_identities"] + b["projected_repeated_rows"] == 20
        assert a["receipt_sha256"] == "f164464fea21a9caf2c877069bcea373c6d0e753b75666ae52089baa0f959d13"
        assert b["receipt_sha256"] == "906d194881c63532fedc8259db825f839a622529a978ad61442946d116f69c7e"
        assert b["canonical_sample_sha256"] == "7b01fb5ae962e8808bb9f66e5cf47ed95a488c8494915bee880df7f39b39ae6b"
        assert b["receipt_git_blob_sha1"] == "89b59eb304f0f17a506c47a2cf0d63beca84f8ec"
        assert b["writer_commit"] == "4543f5f35ab30baffe9be32bbc2e82d00405e1fd"
        for field in ("sample_sequence_stably_sorted",
                      "sampled_identities_change_is_independent_real_permit_count",
                      "projected_repeat_count_change_proves_dedupe_repair",
                      "original_publisher_http_bytes_acquired",
                      "socrata_system_id_probe_executed"):
            assert q[field] is False, field
        assert q["original_publisher_http_sha256"] is None
        assert q["distinct_source_api_rows_independently_verified"] == 0
        assert q["independent_current_issuance_or_validity_labels"] == 0
        assert q["verified_buyer_outcomes"] == 0
        assert q["commercial_scoring_rights"] == "UNVERIFIED_HOLD"
        assert q["production_admission"] == "HOLD"
        assert len(q["synthetic_negative_controls"]) == 3
        assert all(x["kind"] == "SYNTHETIC" for x in q["synthetic_negative_controls"])

    def test_two_writer_receipts_do_not_establish_permit_identity(self):
        self._assert_scope(self._pack())

    def test_forged_identity_hash_labels_and_rights_are_rejected(self):
        import copy
        attacks = (
            lambda q: q["current_writer_snapshot"].update(projected_repeated_rows=0),
            lambda q: q["current_writer_snapshot"].update(projected_unique_identities=20),
            lambda q: q["previous_writer_snapshot"].update(projected_unique_identities=20),
            lambda q: q["current_writer_snapshot"].update(receipt_git_blob_sha1="0" * 40),
            lambda q: q["current_writer_snapshot"].update(receipt_sha256="0" * 64),
            lambda q: q["current_writer_snapshot"].update(canonical_sample_sha256="0" * 64),
            lambda q: q.update(original_publisher_http_bytes_acquired=True),
            lambda q: q.update(original_publisher_http_sha256="0" * 64),
            lambda q: q.update(sample_sequence_stably_sorted=True),
            lambda q: q.update(projected_repeat_count_change_proves_dedupe_repair=True),
            lambda q: q.update(independent_current_issuance_or_validity_labels=18),
            lambda q: q.update(commercial_scoring_rights="APPROVED"),
            lambda q: q["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        )
        for index, attack in enumerate(attacks):
            with self.subTest(forged=index):
                forged = copy.deepcopy(self._pack())
                attack(forged["operational_writer_unsorted_identity_churn_2026_10_29"])
                with self.assertRaises(AssertionError):
                    self._assert_scope(forged)


class NYCDOBCachedCardinalityCounterexampleTests(unittest.TestCase):
    """Cached cardinality is not a distinct permit or even distinct status count."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_live_replay_quality_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
        q = p["official_socrata_cached_cardinality_counterexample_2026_10_29"]
        total = p["official_socrata_catalog_cached_count_drift_same_clock_2026_10_28"]["later_cached_counts"]
        self.assertEqual(q["schema_version"], "0.1.0")
        self.assertEqual(q["dataset_id"], "rbx6-tga4")
        self.assertEqual(q["source_url"], "https://data.cityofnewyork.us/api/views/rbx6-tga4")
        self.assertEqual(q["source_rows_updated_at_epoch_seconds"], 1793213280)
        status = q["permit_status_column"]
        self.assertEqual(status["non_null"], total["total"])
        self.assertEqual(status["null"], 0)
        self.assertEqual(status["cached_cardinality"], 1021662)
        self.assertEqual(status["cached_top_values"], {
            "Signed-off": total["signed"], "Permit Issued": total["issued"],
        })
        self.assertEqual(sum(status["cached_top_values"].values()), status["non_null"])
        self.assertTrue(status["top_values_exhaust_reported_non_null"])
        self.assertEqual(status["distinct_status_categories_supported_by_cached_top"], 2)
        self.assertNotEqual(status["cached_cardinality"],
                            status["distinct_status_categories_supported_by_cached_top"])
        city = q["owner_city_column"]
        self.assertEqual(city, {
            "non_null": 0, "null": total["total"], "cached_cardinality": total["total"],
        })
        for field in ("publisher_response_bytes_custodied",
                      "cached_cardinality_is_distinct_permit_identity_count",
                      "cached_cardinality_proves_source_row_uniqueness"):
            self.assertIs(q[field], False, field)
        self.assertIsNone(q["publisher_response_sha256"])
        self.assertEqual(q["real_permit_identity_and_actual_distinct_count"], "UNKNOWN")
        self.assertEqual(q["source_specific_customer_scoring_approval"], "UNVERIFIED_HOLD")
        self.assertEqual(q["production_admission"], "HOLD")
        for field in ("current_validity_labels_from_this_probe",
                      "independently_held_out_permit_labels_from_this_probe",
                      "buyer_outcome_labels_from_this_probe"):
            self.assertEqual(q[field], 0, field)
        controls = q["synthetic_negative_controls"]
        self.assertEqual(len(controls), 2)
        self.assertEqual(len({x["id"] for x in controls}), 2)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" for x in controls))

    def test_official_cached_column_cardinality_not_unique_row_truth(self):
        self._assert_scope(self._pack())

    def test_forged_cached_identity_rights_hash_and_labels_rejected(self):
        import copy
        edits = [
            lambda q: q["permit_status_column"].update(cached_cardinality=2),
            lambda q: q["permit_status_column"]["cached_top_values"].update(
                {"Permit Issued": 368371}),
            lambda q: q["owner_city_column"].update(non_null=1),
            lambda q: q.update(cached_cardinality_is_distinct_permit_identity_count=True),
            lambda q: q.update(cached_cardinality_proves_source_row_uniqueness=True),
            lambda q: q.update(real_permit_identity_and_actual_distinct_count="1021662"),
            lambda q: q.update(source_specific_customer_scoring_approval="APPROVED"),
            lambda q: q.update(publisher_response_bytes_custodied=True),
            lambda q: q.update(publisher_response_sha256="0" * 64),
            lambda q: q.update(independently_held_out_permit_labels_from_this_probe=1),
            lambda q: q["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        ]
        for index, edit in enumerate(edits):
            with self.subTest(forged=index):
                bad = copy.deepcopy(self._pack())
                edit(bad["official_socrata_cached_cardinality_counterexample_2026_10_29"])
                with self.assertRaises(AssertionError):
                    self._assert_scope(bad)

class NYCElectricalCatalogMarginalReconciliationTests(unittest.TestCase):
    """One official cached-field count gap is not one adjudicated permit error."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_excluded_scope_v1.json").read_text(encoding="utf-8"))

    def _assert_scope(self, data):
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["real_permit_records_ingested"], 0)
        q = data["electrical_application_catalog_cached_marginal_reconciliation_2026_10_29"]
        self.assertEqual(q["observation_version"], "0.1.0")
        self.assertEqual(q["source_dataset_id"], "dm9a-ab7w")
        self.assertEqual(q["official_metadata_url"],
                         "https://data.cityofnewyork.us/api/views/dm9a-ab7w")
        self.assertEqual(q["publisher_rows_updated_at_utc"], "2026-10-28T21:43:32Z")
        self.assertEqual(q["cached_filing_rows"], 596371)
        self.assertEqual(q["cached_filing_type_counts"], {
            "New Job Filing": 485310, "PAA": 96230, "Subsequent Filing": 14831,
        })
        self.assertEqual(sum(q["cached_filing_type_counts"].values()),
                         q["cached_filing_rows"])
        self.assertEqual(q["cached_filing_number_i1_count"], 485311)
        self.assertEqual(q["cross_field_marginal_delta"], 1)
        self.assertEqual(
            q["cached_filing_number_i1_count"] -
            q["cached_filing_type_counts"]["New Job Filing"],
            q["cross_field_marginal_delta"])
        self.assertTrue(q["source_marginals_do_not_independently_prove_row_level_error"])
        for field in ("row_level_causal_record_identified", "original_http_bytes_custodied",
                      "source_specific_commercial_scoring_approved",
                      "production_collector_modified"):
            self.assertIs(q[field], False, field)
        self.assertIsNone(q["original_publisher_http_response_sha256"])
        self.assertEqual(q["raw_permit_person_or_applicant_rows_stored"], 0)
        self.assertEqual(q["independently_held_out_issued_permit_labels"], 0)
        self.assertEqual(q["independent_validity_labels"], 0)
        self.assertEqual(q["buyer_outcome_labels"], 0)
        self.assertEqual(q["commercial_scoring_gate"], "HOLD")
        self.assertEqual(q["consumer_owner"], ":48 PermitPlate")
        self.assertEqual(q["independent_qa_owner"], ":44 QA")
        negatives = q["synthetic_negative_controls"]
        self.assertEqual(len(negatives), 3)
        self.assertEqual(len({x["id"] for x in negatives}), 3)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" for x in negatives))

    def test_official_electrical_catalog_marginals_are_not_permit_truth(self):
        self._assert_scope(self._pack())

    def test_forged_electrical_marginal_rights_custody_and_labels_rejected(self):
        import copy
        attacks = (
            lambda q: q.update(cached_filing_number_i1_count=485310),
            lambda q: q["cached_filing_type_counts"].update({"New Job Filing": 485311}),
            lambda q: q.update(cross_field_marginal_delta=0),
            lambda q: q.update(row_level_causal_record_identified=True),
            lambda q: q.update(original_http_bytes_custodied=True),
            lambda q: q.update(original_publisher_http_response_sha256="0" * 64),
            lambda q: q.update(source_specific_commercial_scoring_approved=True),
            lambda q: q.update(independently_held_out_issued_permit_labels=1),
            lambda q: q["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        )
        key = "electrical_application_catalog_cached_marginal_reconciliation_2026_10_29"
        for index, attack in enumerate(attacks):
            with self.subTest(forged=index):
                changed = copy.deepcopy(self._pack())
                attack(changed[key])
                with self.assertRaises(AssertionError):
                    self._assert_scope(changed)


# Must follow every TestCase class; direct script execution otherwise skips late tests.

class CaptureBriefFY27VAFlooringLifecycleEvidenceTests(unittest.TestCase):
    """Officially indexed FY27 notices: market research is not a live solicitation."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "capturebrief_sam_fy2027_va_flooring_lifecycle_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], "0.1.1")
        self.assertEqual(p["evaluation_family"],
                         "GOVERNMENT_NOTICE_ASOF_LIFECYCLE_AND_ELIGIBILITY_NOT_AWARD_SCORING")
        s, n, g, q = (p["source"], p["notice_chronology"],
                       p["ground_truth_boundaries"], p["quality"])
        self.assertEqual(s["published_notice_number"], "36C26127Q0047")
        # Each historical SAM version has a distinct indexed publisher identity.
        expected_versions = (
            ("market_research_original", "ce12814b985b4908ae57248813c085b3",
             "https://sam.gov/opp/ce12814b985b4908ae57248813c085b3/view",
             "original_sources_sought_url"),
            ("market_research_amended", "16e70df741c94882979fd9e6824ef1ff",
             "https://sam.gov/opp/16e70df741c94882979fd9e6824ef1ff/view",
             "updated_sources_sought_url"),
            ("subsequent_solicitation", "b8205e6e69db41bc85611de60bbe9566",
             "https://sam.gov/opp/b8205e6e69db41bc85611de60bbe9566/view",
             "later_solicitation_url"),
        )
        for stage, uuid, url, source_key in expected_versions:
            self.assertEqual(n[stage]["notice_record_uuid"], uuid)
            self.assertEqual(s[source_key], url)
        # Secondary indexes indicate a later Oct 23 amendment. Do not mark the
        # Oct 19 record as the latest or claim unheld SAM bytes/roster custody.
        amendment = s["secondary_oct23_amendment_index"]
        self.assertEqual(amendment["candidate_notice_record_uuid"],
                         "bfc14294001d4d5dbb20fe49a288b687")
        self.assertEqual(amendment["candidate_official_url"],
                         "https://sam.gov/opp/bfc14294001d4d5dbb20fe49a288b687/view")
        self.assertEqual(amendment["secondary_indexes_report_posted_on"], "2026-10-23")
        self.assertEqual(amendment["reported_version"],
                         "SOLICITATION_UPDATED_AMENDMENT_P0001")
        self.assertEqual(amendment["evidence_class"],
                         "SECONDARY_PUBLIC_INDEX_ONLY_NOT_ORIGINAL_SAM_BYTES")
        self.assertEqual(len(amendment["independent_secondary_indexes"]), 2)
        for key in ("original_sam_record_http_bytes_verified",
                    "amendment_pdf_or_roster_attachment_read",
                    "commercial_reuse_approved"):
            self.assertFalse(amendment[key])
        self.assertIsNone(amendment["original_sam_record_http_sha256"])
        self.assertTrue(amendment["primary_source_reverification_required"])
        self.assertEqual(s["later_solicitation_url"],
                         "https://sam.gov/opp/b8205e6e69db41bc85611de60bbe9566/view")
        self.assertEqual(s["site_terms_url"], "https://sam.gov/about/terms-of-use")
        self.assertFalse(s["original_publisher_http_response_bytes_custodied"])
        self.assertIsNone(s["original_publisher_http_sha256"])
        self.assertFalse(s["publisher_attachment_bytes_custodied"])
        self.assertFalse(s["source_specific_commercial_scoring_rights_verified"])
        self.assertFalse(s["automated_sam_web_scraping_authorized"])
        self.assertEqual(s["permission_state"],
                         "HOLD_SOURCE_SPECIFIC_API_PERMISSION_AND_ATTACHMENT_RIGHTS_NOT_PROVEN")
        self.assertEqual(n["market_research_original"]["original_response_due_local"],
                         "2026-10-30T16:00:00-07:00")
        self.assertEqual(n["market_research_amended"]["updated_response_due_local"],
                         "2026-09-22T16:00:00-07:00")
        self.assertEqual(n["subsequent_solicitation"]["publication_date"], "2026-10-19")
        self.assertEqual(n["subsequent_solicitation"]["date_offers_due_local"],
                         "2026-11-17T15:00:00-08:00")
        self.assertEqual(n["subsequent_solicitation"]["set_aside"],
                         "SERVICE_DISABLED_VETERAN_OWNED_SMALL_BUSINESS")
        self.assertEqual(len({x["notice_record_uuid"] for x in n.values()}), 3)
        for label in ("same_notice_number_is_not_same_notice_record_uuid",
                      "three_notice_record_uuids_do_not_prove_three_contract_awards",
                      "original_sources_sought_deadline_is_not_current_solicitation_offer_deadline",
                      "amended_sources_sought_deadline_is_not_current_solicitation_offer_deadline"):
            self.assertTrue(g[label], label)
        self.assertEqual(g["last_indexed_publisher_stage_asof_2026_10_29"],
                         "UNKNOWN_SECONDARY_INDEX_REPORTS_OCT23_AMENDMENT_ORIGINAL_NOT_VERIFIED")
        self.assertTrue(g["oct19_original_not_safe_as_latest_without_oct23_review"])
        self.assertFalse(g["oct23_amendment_source_verified_from_original_publisher"])
        self.assertEqual(g["oct23_amendment_changed_deadline_or_set_aside"],
                         "UNKNOWN_NO_ORIGINAL_AMENDMENT_PDF_REPLAY")
        for key in ("bidder_sdvobs_eligibility",
                    "current_bid_acceptance_from_live_publisher_response",
                    "subsequent_changes_after_latest_indexed_source",
                    "solicitation_award_outcome"):
            self.assertIn("UNKNOWN", g[key], key)
        for key in ("independent_heldout_lifecycle_labels", "independent_award_labels",
                    "verified_customer_eligible_bids", "customer_contact_actions"):
            self.assertEqual(g[key], 0, key)
        self.assertFalse(g["commercial_capturebrief_scoring_admitted"])
        self.assertEqual(g["production_input_state"], "HOLD")
        self.assertEqual(q["source_content_sha256"],
                         "UNKNOWN_NO_ORIGINAL_PUBLISHER_HTTP_BYTES")
        self.assertEqual(q["original_attachment_files_acquired"], 0)
        self.assertEqual(q["secondary_indexed_later_amendment_candidates"], 1)
        self.assertEqual(q["primary_verified_later_amendment_documents"], 0)
        self.assertIsNone(q["later_amendment_original_http_sha256"])
        self.assertFalse(q["amendment_may_be_used_for_customer_scoring"])
        self.assertTrue(q["no_private_customer_student_or_medical_records_used"])
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 10)
        self.assertEqual(len({c["id"] for c in controls}), 10)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" and c["id"].startswith("SYNTHETIC_")
                            for c in controls))

    def test_september_market_research_is_not_october_live_solicitation(self):
        self._assert_scope(self._pack())

    def test_synthetic_stale_date_identity_rights_and_award_promotions_rejected(self):
        import copy
        edits = (
            lambda p: p["notice_chronology"]["market_research_amended"].update(
                updated_response_due_local="2026-11-17T15:00:00-08:00"),
            lambda p: p["notice_chronology"]["subsequent_solicitation"].update(
                date_offers_due_local="2026-10-30T16:00:00-07:00"),
            lambda p: p["notice_chronology"]["subsequent_solicitation"].update(
                set_aside="UNRESTRICTED"),
            lambda p: p["source"].update(original_publisher_http_sha256="f" * 64),
            lambda p: p["source"].update(automated_sam_web_scraping_authorized=True),
            lambda p: p["ground_truth_boundaries"].update(independent_award_labels=1),
            lambda p: p["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
            lambda p: p["source"].update(original_sources_sought_url="https://sam.gov/opp/FAKE/view"),
            lambda p: p["source"].update(updated_sources_sought_url="https://sam.gov/opp/FAKE/view"),
            lambda p: p["notice_chronology"]["market_research_original"].update(
                notice_record_uuid="SYNTHETIC_WRONG_RECORD"),
            lambda p: p["notice_chronology"]["market_research_amended"].update(
                notice_record_uuid="SYNTHETIC_WRONG_RECORD"),
            lambda p: p["notice_chronology"]["subsequent_solicitation"].update(
                notice_record_uuid="SYNTHETIC_WRONG_RECORD"),
            lambda p: p["source"]["secondary_oct23_amendment_index"].update(
                original_sam_record_http_bytes_verified=True),
            lambda p: p["source"]["secondary_oct23_amendment_index"].update(
                amendment_pdf_or_roster_attachment_read=True),
            lambda p: p["source"]["secondary_oct23_amendment_index"].update(
                candidate_notice_record_uuid="SYNTHETIC_WRONG_AMENDMENT"),
            lambda p: p["ground_truth_boundaries"].update(
                last_indexed_publisher_stage_asof_2026_10_29="SOLICITATION_ORIGINAL"),
            lambda p: p["quality"].update(
                amendment_may_be_used_for_customer_scoring=True),
        )
        for i, edit in enumerate(edits):
            with self.subTest(synthetic_mutation=i):
                bad = copy.deepcopy(self._pack())
                edit(bad)
                with self.assertRaises(AssertionError):
                    self._assert_scope(bad)


class GAOB221609SixGBLCorrelatedEvidenceTests(unittest.TestCase):
    """A GAO opinion citing six GBLs is not six held-out labeled invoices."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "gao_b221609_six_gbl_cluster_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], "0.1.0")
        self.assertEqual(p["evaluation_family"],
                         "FREIGHT_ERROR_ADJUDICATION_CORRELATED_CASE_CLUSTER_NOT_EXTRACTION_OR_AP_RECONCILIATION")
        s, d, g = p["source"], p["reported_decision"], p["ground_truth"]
        self.assertEqual(s["official_url"], "https://www.gao.gov/products/b-221609-0")
        self.assertEqual(s["decision_date"], "1986-02-28")
        self.assertEqual(s["commercial_scoring_permission"],
                         "HOLD_NO_ORIGINAL_INVOICE_OR_CUSTOMER_RIGHTS")
        self.assertFalse(s["raw_publisher_http_bytes_acquired"])
        self.assertIsNone(s["original_publisher_response_sha256"])
        for key in ("original_gbl_bytes_custodied", "original_carrier_invoices_custodied",
                    "underlying_tender_pages_custodied", "original_payment_deduction_receipts_custodied"):
            self.assertFalse(s[key])
        self.assertEqual(d["reviewed_gsa_deduction_actions"], 6)
        self.assertTrue(d["gao_sustained_all_reviewed_actions"])
        self.assertTrue(d["carrier_higher_joint_line_position_rejected"])
        self.assertIsNone(d["source_aggregate_recovery_amount_cents"])
        self.assertIsNone(d["source_per_gbl_overcharge_amounts_cents"])
        expected = ("APO743634", "S4283162", "M6361307", "M6361264",
                    "M6357146", "BPO392232")
        self.assertEqual(tuple(p["reported_gbl_numbers"]), expected)
        self.assertEqual(len(set(expected)), 6)
        self.assertEqual(g["published_adjudication_decision_labels"], 1)
        self.assertEqual(g["reported_referenced_gbls"], 6)
        for key in ("independent_invoice_face_labels",
                    "independently_held_out_labeled_invoice_cases",
                    "independent_shipment_deduction_receipt_labels",
                    "independent_modern_customer_cases", "verified_retally_customer_recovered_cents"):
            self.assertEqual(g[key], 0)
        self.assertTrue(g["publisher_decision_count_is_not_independent_invoice_count"])
        self.assertTrue(g["shared_opinion_and_referenced_precedent_create_correlated_examples"])
        self.assertFalse(g["production_accuracy_admitted"])
        self.assertFalse(g["customer_inference_permitted"])
        self.assertEqual(g["per_shipment_amount"], "UNKNOWN_NOT_REPORTED_IN_DECISION")
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({c["id"] for c in controls}), 5)
        self.assertTrue(all(c["kind"] == "SYNTHETIC" for c in controls))

    def test_one_adjudication_not_six_independently_scored_invoices(self):
        self._assert_scope(self._pack())

    def test_synthetic_label_money_custody_and_rights_promotions_rejected(self):
        import copy
        edits = (
            lambda p: p["ground_truth"].update(independently_held_out_labeled_invoice_cases=6),
            lambda p: p["ground_truth"].update(published_adjudication_decision_labels=6),
            lambda p: p["reported_decision"].update(gao_sustained_all_reviewed_actions=False),
            lambda p: p["reported_decision"].update(carrier_higher_joint_line_position_rejected=False),
            lambda p: p["source"].update(raw_publisher_http_bytes_acquired=True),
            lambda p: p["source"].update(original_publisher_response_sha256="a" * 64),
            lambda p: p["source"].update(commercial_scoring_permission="APPROVED"),
            lambda p: p["reported_decision"].update(source_aggregate_recovery_amount_cents=100),
            lambda p: p["ground_truth"].update(verified_retally_customer_recovered_cents=15604),
            lambda p: p["reported_gbl_numbers"].__setitem__(0, "SYNTHETIC"),
            lambda p: p["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        )
        for i, edit in enumerate(edits):
            with self.subTest(synthetic_mutation=i):
                bad = copy.deepcopy(self._pack())
                edit(bad)
                with self.assertRaises(AssertionError):
                    self._assert_scope(bad)


class NYCDOBCommunityViewAuthorityTests(unittest.TestCase):
    """Official BIS and DOB NOW cohorts are not an unendorsed community view."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "nyc_dob_community_view_authority_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], "0.1.0")
        self.assertEqual(p["evaluation_family"],
                         "GOVERNMENT_PERMIT_SOURCE_AUTHORITY_AND_COHORT_DISAMBIGUATION_NOT_SCORING")
        self.assertEqual(p["status"], "DRAFT_HELD_UNRELEASED")
        sources = {x["dataset_id"]: x for x in p["sources"]}
        self.assertEqual(len(p["sources"]), 3)
        self.assertEqual(set(sources), {"ipu4-2q9a", "rbx6-tga4", "cwwt-dc2f"})
        bis, now, view = sources["ipu4-2q9a"], sources["rbx6-tga4"], sources["cwwt-dc2f"]
        self.assertEqual(bis["cohort"], "BIS_PER_WORK_TYPE_PERMIT_LIFECYCLE_NOT_DOB_NOW")
        self.assertEqual(now["cohort"], "DOB_NOW_APPROVED_EXCLUDES_ELECTRICAL_ELEVATOR_LAA")
        self.assertEqual(view["cohort"], "COMMUNITY_VIEW_OF_BIS_UNVERIFIED_FILTERS")
        self.assertTrue(bis["agency_original"])
        self.assertTrue(now["agency_original"])
        self.assertFalse(view["agency_original"])
        self.assertTrue(view["community_created_view"])
        self.assertEqual(view["upstream_dataset_id"], "ipu4-2q9a")
        self.assertEqual(view["official_catalog_url"],
                         "https://data.cityofnewyork.us/d/cwwt-dc2f")
        for row in sources.values():
            self.assertFalse(row["raw_publisher_http_bytes_acquired"])
            self.assertIsNone(row["original_publisher_response_sha256"])
            self.assertEqual(row["personal_permit_applicant_rows_saved"], 0)
        a, r, q, g = p["source_authority"], p["rights"], p["source_quality"], p["ground_truth"]
        self.assertFalse(a["community_view_city_endorsed"])
        self.assertFalse(a["community_view_predicate_and_row_lineage_replayed"])
        self.assertEqual(a["dob_now_excluded_application_families"],
                         ["ELECTRICAL", "ELEVATOR", "LIMITED_ALTERATION_APPLICATION"])
        self.assertFalse(a["bis_issuance_is_current_dob_now_issuance"])
        self.assertFalse(a["community_view_title_proves_permit_issuance_or_validity"])
        self.assertTrue(r["general_nyc_open_data_reuse_without_use_restrictions"])
        self.assertFalse(r["additional_dataset_specific_terms_review_complete"])
        self.assertFalse(r["commercial_scoring_or_customer_contact_approved"])
        self.assertFalse(r["pii_customer_or_private_record_entitlement"])
        self.assertFalse(q["original_api_export_or_row_replay_performed"])
        self.assertTrue(q["city_catalog_last_updated_is_not_live_active_permit_truth"])
        self.assertTrue(q["no_applicant_contact_or_address_rows_saved"])
        for key in ("independently_held_out_labeled_issued_permit_cases",
                    "independently_held_out_current_validity_labels",
                    "independently_held_out_customer_outcome_labels"):
            self.assertEqual(g[key], 0)
        for key in ("cross_system_unique_real_permit_count", "community_filtered_row_count",
                    "production_permit_precision_recall"):
            self.assertEqual(g[key], "UNKNOWN")
        self.assertFalse(g["real_permit_or_customer_truth_admitted"])
        controls = p["synthetic_negative_controls"]
        self.assertEqual(len(controls), 8)
        self.assertEqual(len(set(x["id"] for x in controls)), 8)
        self.assertTrue(all(x["kind"] == "SYNTHETIC" for x in controls))

    def test_original_agency_and_community_view_cohorts_are_distinct(self):
        self._assert_scope(self._pack())

    def test_synthetic_authority_rights_and_truth_promotions_are_rejected(self):
        import copy
        edits = (
            lambda p: p["source_authority"].update(community_view_city_endorsed=True),
            lambda p: p["sources"][2].update(agency_original=True),
            lambda p: p["sources"][2].update(upstream_dataset_id="rbx6-tga4"),
            lambda p: p["sources"][0].update(cohort="CURRENT_DOB_NOW"),
            lambda p: p["source_authority"].update(dob_now_excluded_application_families=[]),
            lambda p: p["source_authority"].update(bis_issuance_is_current_dob_now_issuance=True),
            lambda p: p["rights"].update(additional_dataset_specific_terms_review_complete=True),
            lambda p: p["rights"].update(commercial_scoring_or_customer_contact_approved=True),
            lambda p: p["source_quality"].update(original_api_export_or_row_replay_performed=True),
            lambda p: p["sources"][1].update(original_publisher_response_sha256="e" * 64),
            lambda p: p["ground_truth"].update(independently_held_out_current_validity_labels=1),
            lambda p: p["ground_truth"].update(cross_system_unique_real_permit_count="3990000"),
            lambda p: p["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        )
        for i, edit in enumerate(edits):
            with self.subTest(synthetic_mutation=i):
                mutated = copy.deepcopy(self._pack())
                edit(mutated)
                with self.assertRaises(AssertionError):
                    self._assert_scope(mutated)



class GAOB253541ConflictingOriginalGBLTests(unittest.TestCase):
    """Original GAO decision's conflicting document values are not modern invoice truth."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "gao_b253541_conflicting_gbl_original_candidate_v0.json"
                           ).read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        self.assertEqual(p["schema_version"], "0.1.0")
        self.assertEqual(p["evaluation_family"],
                         "FREIGHT_DOCUMENT_EXTRACTION_ORIGINAL_VS_SHIPPING_ORDER_CONFLICT_NOT_MODERN_RATE_SCORING")
        self.assertEqual(p["status"], "DRAFT_SOURCE_BOUND_HOLD")
        s = p["source"]
        self.assertEqual((s["decision_id"], s["decision_date"], s["publisher"]),
                         ("GAO_B_253541", "1993-10-18", "US_GAO"))
        self.assertEqual(s["official_url"], "https://www.gao.gov/products/b-253541")
        self.assertEqual(s["rights_url"], "https://www.gao.gov/copyright")
        self.assertTrue(s["published_agency_decision_text_reviewed"])
        for key in ("third_party_attached_material_rights_checked",
                    "publisher_http_response_bytes_acquired",
                    "original_sf1103_microfiche_bytes_acquired",
                    "original_sf1104_shipping_order_bytes_acquired",
                    "signed_original_gbl_independently_in_lab_custody"):
            self.assertFalse(s[key])
        self.assertIsNone(s["publisher_http_body_sha256"])
        d = p["historical_discrepancy"]
        self.assertEqual(d["gbl_identifier"], "D-0,521,277")
        self.assertEqual((d["shipping_order_form"], d["shipping_order_valuation_string"]),
                         ("SF_1104", "$2150"))
        self.assertEqual((d["signed_original_gbl_form"], d["signed_original_gbl_valuation_string"]),
                         ("SF_1103", "$2.50"))
        self.assertEqual(d["valuation_basis"], "USD_PER_POUND_PER_ARTICLE")
        self.assertTrue(d["gao_reports_original_carrier_representative_signature"])
        self.assertEqual(d["gao_resolution"],
                         "GSA_AUDIT_SETTLEMENT_AFFIRMED_USING_ORIGINAL_GBL_VALUATION")
        self.assertFalse(d["same_released_value_on_both_forms"])
        self.assertTrue(d["original_vs_shipping_order_inference_is_case_specific"])
        self.assertFalse(d["released_value_is_freight_transportation_charge"])
        self.assertEqual(d["actual_original_tariff_rate"], "UNKNOWN")
        self.assertEqual(d["actual_claim_dollar_amount"], "UNKNOWN")
        self.assertFalse(d["original_microfiche_independently_replayed"])
        r, g, h = p["rights"], p["ground_truth"], p["handoff"]
        self.assertTrue(r["gao_text_reuse_with_credit_and_no_implied_endorsement"])
        for key in ("separate_third_party_invoice_and_image_rights_verified",
                    "commercial_customer_scoring_authorized", "private_data_acquired"):
            self.assertFalse(r[key])
        self.assertEqual(g["published_adjudication_decision_labels"], 1)
        for key in ("independently_heldout_original_gbl_document_pairs",
                    "independently_heldout_customer_invoice_rate_labels",
                    "independent_current_customer_cash_receipts",
                    "verified_retally_customer_recovery_cents"):
            self.assertEqual(g[key], 0)
        self.assertEqual(g["freight_error_precision_recall"], "UNKNOWN")
        self.assertEqual(g["customer_rate_error_label"], "UNKNOWN")
        self.assertEqual(g["document_conflict_source_scope"],
                         "ONE_AGENCY_DECISION_NOT_TWO_INDEPENDENT_DOCUMENT_EXAMPLES")
        self.assertEqual(len(p["synthetic_negative_controls"]), 5)
        self.assertEqual(len({x["id"] for x in p["synthetic_negative_controls"]}), 5)
        self.assertTrue(all(x["kind"] == "SYNTHETIC"
                            for x in p["synthetic_negative_controls"]))
        self.assertEqual(h["intended_lane"],
                         "FREIGHTRECOVERY_DOCUMENT_EXTRACTION_CONFLICT_REGRESSION_CANDIDATE")
        for key in ("engine_implementation_changes_made", "operational_writer_changed",
                    "independent_qa_completed", "production_release_authorized"):
            self.assertFalse(h[key])

    def test_historical_signed_original_not_shipping_order_is_decision_scope_only(self):
        self._assert_scope(self._pack())

    def test_synthetic_document_custody_rights_and_money_claims_rejected(self):
        import copy
        edits = (
            lambda p: p["historical_discrepancy"].update(shipping_order_valuation_string="$2.50"),
            lambda p: p["historical_discrepancy"].update(signed_original_gbl_valuation_string="$2150"),
            lambda p: p["historical_discrepancy"].update(signed_original_gbl_form="SF_1104"),
            lambda p: p["historical_discrepancy"].update(original_vs_shipping_order_inference_is_case_specific=False),
            lambda p: p["historical_discrepancy"].update(released_value_is_freight_transportation_charge=True),
            lambda p: p["historical_discrepancy"].update(actual_claim_dollar_amount="$2150"),
            lambda p: p["source"].update(original_sf1103_microfiche_bytes_acquired=True),
            lambda p: p["source"].update(publisher_http_body_sha256="a" * 64),
            lambda p: p["rights"].update(commercial_customer_scoring_authorized=True),
            lambda p: p["ground_truth"].update(independently_heldout_original_gbl_document_pairs=1),
            lambda p: p["ground_truth"].update(verified_retally_customer_recovery_cents=215000),
            lambda p: p["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
            lambda p: p["handoff"].update(production_release_authorized=True),
        )
        for i, edit in enumerate(edits):
            with self.subTest(synthetic_mutation=i):
                forged = copy.deepcopy(self._pack())
                edit(forged)
                with self.assertRaises(AssertionError):
                    self._assert_scope(forged)



class UnifiedResearchConsolidationSnapshotTests(unittest.TestCase):
    """Freeze actual single-writer and cross-engine metadata census, without truth promotion."""

    @staticmethod
    def _snapshot():
        return json.loads((Path(__file__).with_name("fixtures") /
            "unified_legacy_lab_consolidation_snapshot_20261030.json").read_text(encoding="utf-8"))

    def _assert_held(self, x):
        self.assertEqual(x["fixture_id"], "RETALLY_UNIFIED_LEGACY_RESEARCH_SNAPSHOT_2026_10_30")
        self.assertEqual(x["canonical_repository"], "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(x["single_writer_branch"], "research/retally-unified-data-lab")
        self.assertEqual(x["active_operational_controller"], ".github/workflows/retally-unified-research-lab.yml")
        self.assertTrue(x["operational_one_writer_consolidated_in_existing_flow"])
        self.assertEqual(x["unique_source_urls"], 801)
        self.assertEqual(sum(x["engine_reference_counts"].values())-x["cross_engine_shared_pointers"], x["unique_source_urls"])
        self.assertEqual(x["ledger_entries_sha256"], x["bounded_evaluation_feed"]["lab15_candidate_metadata_sha256"] if False else "651b27d26d60e7012c7cadfd13fcab31d6fd9094f7bd48ec09534d11abb09a95")
        self.assertEqual(x["bounded_evaluation_feed"]["selected_source_pointers"], 260)
        self.assertLess(x["bounded_evaluation_feed"]["selected_source_pointers"], x["unique_source_urls"])
        self.assertEqual(len(x["legacy_source_ledgers_considered"]), 3)
        self.assertEqual(len(x["historical_lab15_workflows_with_no_active_cron_observed"]), 2)
        self.assertFalse(x["all_historical_legacy_branches_physically_retired"])
        self.assertFalse(x["all_historical_legacy_labs_exhaustively_audited"])
        self.assertFalse(x["new_cron_or_provider_calls_added"])
        self.assertEqual(x["original_external_document_bytes_saved"], 0)
        self.assertEqual(x["publisher_response_full_bounded_sha256_count"], 3)
        self.assertIsNone(x["original_nyc_electrical_metadata_response_sha256"])
        self.assertEqual(x["independent_new_freight_error_labels"], 0)
        self.assertEqual(x["independent_permit_outcome_labels"], 0)
        self.assertEqual(x["verified_customer_recoveries_cents"], 0)
        self.assertFalse(x["commercial_reuse_approved"])
        self.assertFalse(x["fully_approved_customer_release"])
        self.assertFalse(x["simulated_independent_qa_passed"])
        self.assertFalse(x["real_independent_qa_completed"])
        self.assertEqual(x["source_accuracy"], "UNKNOWN")
        self.assertEqual(x["commercial_accuracy"], "UNKNOWN")
        self.assertEqual(len(set(x["evaluation_lanes"])), 5)

    def test_current_single_writer_snapshot_preserves_provenance_and_unknowns(self):
        self._assert_held(self._snapshot())

    def test_synthetic_forged_consolidation_and_revenue_claims_rejected(self):
        original=self._snapshot()
        attacks=(
            ("all_historical_legacy_branches_physically_retired", True),
            ("all_historical_legacy_labs_exhaustively_audited", True),
            ("new_cron_or_provider_calls_added", True),
            ("original_nyc_electrical_metadata_response_sha256", "0"*64),
            ("independent_new_freight_error_labels", 1),
            ("independent_permit_outcome_labels", 1),
            ("verified_customer_recoveries_cents", 100),
            ("commercial_reuse_approved", True),
            ("fully_approved_customer_release", True),
            ("real_independent_qa_completed", True),
        )
        for key, forged in attacks:
            with self.subTest(synthetic_attack=key), self.assertRaises(AssertionError):
                altered=json.loads(json.dumps(original))
                altered[key]=forged
                self._assert_held(altered)



class NYCDOB20261030CachedRefreshTests(unittest.TestCase):
    """Original publisher cached aggregates are not independent current permit labels."""

    @staticmethod
    def _pack():
        return json.loads((Path(__file__).with_name("fixtures") /
            "nyc_dob_live_replay_quality_candidate_v0.json").read_text(encoding="utf-8"))

    def _assert_scope(self, p):
        import hashlib
        self.assertEqual(p["schema_version"], NYC_DOB_REPLAY_PACK_SCHEMA_VERSION)
        q = p["official_socrata_catalog_cached_refresh_2026_10_30"]
        self.assertEqual(q["schema_version"], "0.1.0")
        self.assertEqual(q["evaluation_family"],
                         "GOVERNMENT_PERMIT_SOURCE_METADATA_QUALITY_NOT_PERMIT_SCORING")
        self.assertEqual(q["source_url"], "https://data.cityofnewyork.us/api/views/rbx6-tga4")
        self.assertEqual(q["publisher_rows_updated_at_utc"], "2026-10-29T18:46:11Z")
        self.assertEqual(q["publisher_view_last_modified_at_utc"], "2026-10-29T18:32:11Z")
        prior, current, delta = (q["previous_cached_counts"],
                                 q["current_cached_counts"], q["cached_deltas"])
        self.assertEqual(prior, {"total":1021662, "signed_off":653292, "permit_issued":368370})
        self.assertEqual(current, {"total":1022310, "signed_off":653898, "permit_issued":368412})
        self.assertEqual(delta, {"total":648, "signed_off":606, "permit_issued":42})
        self.assertEqual(current["total"], current["signed_off"]+current["permit_issued"])
        for key in delta:
            self.assertEqual(current[key]-prior[key], delta[key])
        s = q["source_semantic_input"]
        self.assertEqual(s["dataset_id"], "rbx6-tga4")
        self.assertEqual(s["cached_total_count"], current["total"])
        self.assertEqual(s["cached_signed_off_count"], current["signed_off"])
        self.assertEqual(s["cached_permit_issued_count"], current["permit_issued"])
        self.assertEqual(s["cached_status_column_cardinality"], current["total"])
        self.assertEqual(s["cached_work_permit_not_yet_issued"], 346)
        self.assertEqual((s["owner_city_cached_non_null"], s["owner_city_cached_null"],
                          s["owner_city_cached_cardinality"]), (0, current["total"], current["total"]))
        self.assertEqual(s["rows_updated_at_epoch_seconds"], 1793299571)
        self.assertEqual(s["view_last_modified_epoch_seconds"], 1793298731)
        digest = hashlib.sha256(json.dumps(
            s, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        self.assertEqual(digest, "4e4cc38a25e6ee2578ac9591c4100239890882f3695f263421fc055bafcb8513")
        self.assertEqual(q["normalized_semantic_snapshot_sha256_not_original_http_bytes"], digest)
        self.assertFalse(q["original_publisher_response_bytes_custodied"])
        self.assertIsNone(q["publisher_http_bytes_sha256"])
        self.assertFalse(q["system_field_identity_probe_executed"])
        self.assertFalse(q["cached_field_cardinality_is_distinct_identity_count"])
        self.assertFalse(q["cached_row_changes_establish_new_active_permits"])
        self.assertEqual(q["source_distinct_permit_count"], "UNKNOWN")
        self.assertEqual(q["source_specific_commercial_scoring_rights"], "UNVERIFIED_HOLD")
        self.assertEqual(q["dataset_specific_extra_terms_review"], "UNKNOWN")
        self.assertEqual(q["independently_heldout_permit_validity_labels"], 0)
        self.assertEqual(q["independent_buyer_outcomes"], 0)
        self.assertEqual(q["private_rows_stored"], 0)
        self.assertEqual(q["production_admission"], "HOLD_NO_INDEPENDENT_LABELS")
        w = q["operational_writer_receipt"]
        self.assertEqual(w["git_blob_sha1"], "cd8c4e1bdbb8e5a478c5a670f6c9b02988bd89a1")
        self.assertEqual(w["as_of_utc_date"], "2026-10-30")
        self.assertEqual((w["bounded_unsorted_sample_count"],
                          w["projected_unique_identities"], w["projected_repeated_rows"]), (20,19,1))
        self.assertEqual(w["status"], "PUBLISHER_REPLAY_DEGRADED")
        self.assertFalse(w["identity_repair_proven"])
        controls = q["synthetic_negative_controls"]
        self.assertEqual(len(controls), 5)
        self.assertEqual(len({a["id"] for a in controls}), 5)
        self.assertTrue(all(a["kind"] == "SYNTHETIC" for a in controls))

    def test_publisher_cached_refresh_preserves_ground_truth_boundaries(self):
        self._assert_scope(self._pack())

    def test_synthetic_false_promotions_rejected(self):
        import copy
        changes = (
            lambda q: q["cached_deltas"].update(total=649),
            lambda q: q["current_cached_counts"].update(permit_issued=368413),
            lambda q: q["source_semantic_input"].update(cached_status_column_cardinality=2),
            lambda q: q["source_semantic_input"].update(owner_city_cached_non_null=1),
            lambda q: q["source_semantic_input"].update(cached_work_permit_not_yet_issued=345),
            lambda q: q.update(original_publisher_response_bytes_custodied=True),
            lambda q: q.update(publisher_http_bytes_sha256="0"*64),
            lambda q: q.update(independently_heldout_permit_validity_labels=1),
            lambda q: q.update(source_specific_commercial_scoring_rights="APPROVED"),
            lambda q: q["operational_writer_receipt"].update(projected_unique_identities=20),
            lambda q: q["synthetic_negative_controls"][0].update(kind="ORIGINAL"),
        )
        for n, change in enumerate(changes):
            with self.subTest(synthetic_mutation=n), self.assertRaises(AssertionError):
                altered = copy.deepcopy(self._pack())
                change(altered["official_socrata_catalog_cached_refresh_2026_10_30"])
                self._assert_scope(altered)



class HistoricalArchiveLineageIntegrityTests(unittest.TestCase):
    """Independently falsifiable Git-tree inventory; NOT publisher-byte/rights approval."""

    ROOT = Path(__file__).with_name("fixtures") / "legacy_branch_archive"

    @classmethod
    def index(cls):
        return json.loads((cls.ROOT / "index_v1.json").read_text(encoding="utf-8"))

    @staticmethod
    def git_sha1(raw):
        import hashlib
        return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

    def validate(self, doc):
        self.assertEqual(doc["index_id"], "RETALLY_HISTORICAL_LAB_LINEAGE_20261030")
        self.assertEqual(doc["canonical_repo"], "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(doc["single_operational_writer"], "research/retally-unified-data-lab")
        self.assertEqual(doc["historical_refs_inventoried"], 40)
        self.assertEqual(doc["refs_with_material_content_deltas"], 33)
        self.assertEqual(doc["refs_already_ancestor_of_main"], 7)
        self.assertEqual(doc["complete_tree_snapshots"], 15)
        self.assertEqual(doc["complete_tree_file_references"], 554)
        self.assertEqual(doc["distinct_legacy_paths"], 113)
        self.assertEqual(doc["distinct_legacy_git_blob_sha1"], 118)
        self.assertEqual(len(doc["branch_groups"]), 10)
        self.assertEqual(len(doc["full_tree_groups"]), 5)
        self.assertEqual(sum(x["expected_refs"] for x in doc["branch_groups"]), 40)
        self.assertEqual(sum(x["expected_refs"] for x in doc["full_tree_groups"]), 15)
        self.assertEqual(doc["primary_unified_ledger_references"], 801)
        self.assertEqual(doc["bounded_evaluation_feed_source_candidates"], 260)
        self.assertEqual(doc["unified_metadata_ledger_entries_sha256"],
                         "651b27d26d60e7012c7cadfd13fcab31d6fd9094f7bd48ec09534d11abb09a95")
        for key in ("new_scheduled_workflows", "provider_queries_from_archive",
                    "privacy_sensitive_source_bytes_copied", "private_invoice_bol_bank_documents_copied",
                    "independently_labeled_new_freight_invoices", "verified_retally_cash_cents",
                    "legacy_branches_deleted"):
            self.assertEqual(doc[key], 0, key)
        for key in ("commercial_reuse_approved", "original_gao_html_or_pdf_bytes_cryptographically_rechecked_this_run",
                    "nyc_live_response_bytes_cryptographically_rechecked_this_run",
                    "real_independent_qa_approved", "full_legacy_source_material_migration_approved"):
            self.assertIs(doc[key], False, key)
        self.assertEqual(doc["migration_state"], "ALL_40_BRANCH_REFS_INDEXED_LEGACY_SOURCE_GIT_BLOBS_PINNED_TWO_INSPECTED_PUBLIC_META_FILES_IMPORTED_UNREVIEWED_SOURCE_BYTES_HELD")

    def test_complete_40_branch_git_provenance_and_dedup(self):
        x=self.index(); self.validate(x)
        refs=[];paths=set();blobs=set();entries=0;full=set()
        for group in x["branch_groups"]:
            p=self.ROOT / Path(group["path"]).name; raw=p.read_bytes()
            self.assertEqual(self.git_sha1(raw),group["git_blob_sha1"])
            obj=json.loads(raw)
            self.assertEqual(len(obj["records"]), group["expected_refs"])
            for b in obj["records"]:
                self.assertNotIn("error",b)
                self.assertEqual(len(b["head_sha"]),40)
                self.assertEqual(b["rights"],"UNKNOWN_HOLD")
                self.assertTrue(b["git_only"])
                refs.append(b["ref"])
        self.assertEqual(len(refs),40)
        self.assertEqual(len(set(refs)),40)
        for group in x["full_tree_groups"]:
            p=self.ROOT / Path(group["path"]).name; raw=p.read_bytes()
            self.assertEqual(self.git_sha1(raw),group["git_blob_sha1"])
            obj=json.loads(raw)
            self.assertEqual(len(obj["records"]),group["expected_refs"])
            for b in obj["records"]:
                self.assertNotIn("error",b)
                self.assertIn(b["ref"],refs)
                self.assertEqual(b["rights"],"UNKNOWN_HOLD")
                self.assertTrue(b["original_bytes_not_copied"])
                full.add(b["ref"])
                for folder in b["folders"]:
                    if folder.get("missing"):
                        self.assertEqual(folder["files"], [])
                        continue
                    self.assertIs(folder["truncated"],False)
                    for f in folder["files"]:
                        self.assertTrue(f["p"].startswith("freight/"))
                        self.assertEqual(len(f["sha1"]),40)
                        self.assertGreater(f["bytes"],0)
                        paths.add(f["p"]);blobs.add(f["sha1"]);entries+=1
        self.assertEqual(len(full),15)
        self.assertEqual((entries,len(paths),len(blobs)),(554,113,118))

    def test_inspected_public_source_metadata_not_invoice_truth(self):
        x=self.index()
        self.assertEqual(len(x["directly_archived_inspected_source_metadata"]),2)
        for item in x["directly_archived_inspected_source_metadata"]:
            raw=(self.ROOT / Path(item["path"]).name).read_bytes()
            self.assertEqual(self.git_sha1(raw),item["git_blob_sha1"])
            self.assertFalse(item["publisher_body_reverified_this_run"])
            obj=json.loads(raw)
            if "faf6" in item["path"]:
                self.assertIn("actual_customer_invoice",obj["prohibited_conclusions"])
                self.assertIn("recoverable_cents",obj["prohibited_conclusions"])
            else:
                self.assertEqual(obj["actual_retally_client_invoices"],0)
                self.assertEqual(obj["actual_retally_customer_recoveries_cents"],0)
                self.assertEqual(obj["independent_Treasury_or_carrier_bank_transaction_statements_examined"],0)

    def test_simulated_adversarial_qa_rejects_false_releases(self):
        import copy
        obj=self.index()
        for key,value in (("new_scheduled_workflows",1),
                          ("privacy_sensitive_source_bytes_copied",1),
                          ("independently_labeled_new_freight_invoices",1),
                          ("verified_retally_cash_cents",1),
                          ("commercial_reuse_approved",True),
                          ("real_independent_qa_approved",True),
                          ("legacy_branches_deleted",40),
                          ("original_gao_html_or_pdf_bytes_cryptographically_rechecked_this_run",True)):
            with self.subTest(synthetic_forgery=key),self.assertRaises(AssertionError):
                y=copy.deepcopy(obj);y[key]=value;self.validate(y)


class RetallyLegacyArchiveInventoryTests(unittest.TestCase):
    """Independent-contract-style offline QA for held historical source metadata."""

    _archive = Path(__file__).with_name("research_lab") / "legacy_archive"

    @staticmethod
    def _git_blob_sha(raw):
        return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()

    def _check_inventory(self, index, groups, held_bytes):
        self.assertEqual(index["inventory_id"], "RETALLY_HISTORICAL_RESEARCH_BRANCH_INVENTORY_2026_10_30")
        self.assertEqual(index["canonical_repo"], "P00NSMASHER/github-value-hunt-ledger")
        self.assertEqual(index["historical_refs_indexed"], 40)
        self.assertEqual(index["single_live_metadata_writer"], "research/retally-unified-data-lab")
        self.assertEqual(len(index["compare_groups"]), 10)
        self.assertEqual(index["historical_compare_results_with_possible_path_truncation"], 8)
        self.assertIs(index["full_historical_file_content_migration_completed"], False)
        self.assertIs(index["original_customer_invoice_or_contract_bytes_migrated"], False)
        self.assertEqual(index["historical_source_reports_migrated"], 3)
        all_refs = []
        partial_count = 0
        for i, meta in enumerate(index["compare_groups"]):
            self.assertEqual(meta["ordinal"], i)
            self.assertEqual(meta["refs"], 4)
            self.assertEqual(meta["path"], f"groups/{i:02d}.json")
            self.assertEqual(self._git_blob_sha(groups[i]), meta["git_blob_sha1"])
            g = json.loads(groups[i])
            self.assertEqual(g["group"], i)
            self.assertEqual(g["schema_version"], 1)
            self.assertEqual(len(g["records"]), 4)
            for row in g["records"]:
                self.assertTrue(row["ref"])
                self.assertRegex(row["head_sha"], r"^[0-9a-f]{40}$")
                self.assertGreaterEqual(row["ahead"], 0)
                self.assertGreaterEqual(row["behind"], 0)
                self.assertTrue(row["git_only"])
                self.assertEqual(row["rights"], "UNKNOWN_HOLD")
                self.assertFalse(row.get("error"))
                for path in row["evidence_paths"]:
                    self.assertTrue(path.startswith("freight/"))
                    self.assertNotIn("..", path)
                if row.get("possible_truncated"):
                    partial_count += 1
                all_refs.append(row["ref"])
        self.assertEqual(len(all_refs), 40)
        self.assertEqual(len(set(all_refs)), 40)
        self.assertEqual(partial_count, 8)
        for required in ("research/retally-unified-data-lab", "research/retally-lab15-source-ledger", "research/retally-lab15-candidate-ledger", "lab/retally-real-document-engines-20261019"):
            self.assertIn(required, all_refs)
        self.assertEqual(len(index["held_reports"]), 3)
        self.assertEqual(len(held_bytes), 3)
        self.assertEqual(set(held_bytes), {m["archive_path"] for m in index["held_reports"]})
        lanes = []
        for m in index["held_reports"]:
            self.assertIn(m["source_branch"], all_refs)
            self.assertIn(m["archive_path"], held_bytes)
            self.assertEqual(self._git_blob_sha(held_bytes[m["archive_path"]]), m["git_blob_sha1"])
            self.assertIsNone(m["original_publisher_http_body_sha256"])
            self.assertFalse(m["commercial_customer_benchmark_rights_verified"])
            lanes.append(m["evaluation_lane"])
        self.assertEqual(len(set(lanes)), 3)
        claims = index["ref_claims"]
        self.assertFalse(claims["real_independent_qa_completed"])
        self.assertEqual(claims["independent_customer_freight_error_labels"], 0)
        self.assertEqual(claims["independent_permit_buyer_outcome_labels"], 0)
        self.assertEqual(claims["verified_retally_cash_recovery_cents"], 0)
        self.assertIsNone(claims["original_external_publisher_byte_sha256_for_new_manifests"])
        for key in ("commercial_customer_use_authorized", "new_workflows_or_paid_providers_added", "all_legacy_workflows_decommissioned"):
            self.assertFalse(claims[key], key)

    def _load_all(self):
        root = self._archive
        index = json.loads((root / "inventory_v1.json").read_text(encoding="utf-8"))
        groups = [(root / meta["path"]).read_bytes() for meta in index["compare_groups"]]
        held = {m["archive_path"]: (root / m["archive_path"]).read_bytes() for m in index["held_reports"]}
        return index, groups, held

    def test_branch_and_source_bytes_preserve_rights_and_qa_holds(self):
        self._check_inventory(*self._load_all())

    def test_synthetic_reviewer_forged_migrations_and_cash_are_rejected(self):
        index, groups, held = self._load_all()
        self._check_inventory(index, groups, held)
        cases = (
            ("invented_complete_migration", "full_historical_file_content_migration_completed", True),
            ("invented_user_contract", "original_customer_invoice_or_contract_bytes_migrated", True),
            ("inflated_branch_census", "historical_refs_indexed", 41),
        )
        for label, key, value in cases:
            with self.subTest(synthetic_mutation=label), self.assertRaises(AssertionError):
                changed = json.loads(json.dumps(index))
                changed[key] = value
                self._check_inventory(changed, groups, held)
        for key, value in (
            ("real_independent_qa_completed", True),
            ("independent_customer_freight_error_labels", 1),
            ("independent_permit_buyer_outcome_labels", 1),
            ("verified_retally_cash_recovery_cents", 100),
            ("original_external_publisher_byte_sha256_for_new_manifests", "0"*64),
            ("commercial_customer_use_authorized", True),
            ("all_legacy_workflows_decommissioned", True),
        ):
            with self.subTest(synthetic_forgery=key), self.assertRaises(AssertionError):
                changed = json.loads(json.dumps(index))
                changed["ref_claims"][key] = value
                self._check_inventory(changed, groups, held)
        with self.assertRaises(AssertionError):
            forged = list(groups)
            forged[0] = forged[0] + b" "
            self._check_inventory(index, forged, held)
        with self.assertRaises(AssertionError):
            forged = dict(held)
            name = next(iter(forged))
            forged[name] += b" "
            self._check_inventory(index, groups, forged)
        with self.assertRaises(AssertionError):
            changed = json.loads(json.dumps(index))
            changed["held_reports"][0]["commercial_customer_benchmark_rights_verified"] = True
            self._check_inventory(changed, groups, held)




class SourceByteReplayIntegrityReceiptTests(unittest.TestCase):
    """Pin historical runner checks without making a fresh live publisher claim."""

    @staticmethod
    def receipt():
        return json.loads((Path(__file__).with_name("fixtures") / "legacy_branch_archive" /
            "source_byte_replay_v1.json").read_text(encoding="utf-8"))

    def check(self, r):
        from freight.real_document_lab import FROZEN_DOCUMENT_SHA256, FROZEN_PENNINE_SHA256
        self.assertEqual(r["receipt_id"],"RETALLY_PINNED_ORIGINAL_PUBLISHER_BYTE_REPLAY_2026_10_30")
        self.assertEqual(r["existing_read_only_workflow_run_id"],40990993765)
        self.assertEqual(r["existing_workflow_job_id"],123853092328)
        self.assertEqual(r["source_code_commit"],"1ddef8e0955e20bda658a1f73b810f2ae5c13812")
        self.assertTrue(r["source_hosted_file_sha256_verified_in_ci"])
        self.assertEqual((r["verified_original_hosted_files_count"],
                          r["freight_invoice_pdf_count"],r["public_accounting_csv_count"]),(7,2,5))
        rows=r["verified_sources"]
        self.assertEqual(len(rows),7)
        self.assertEqual(len(set(x["id"] for x in rows)),7)
        for x in rows:
            want=(FROZEN_DOCUMENT_SHA256 if x["kind"]=="ORIGINAL_PUBLIC_INVOICE_PDF"
                  else FROZEN_PENNINE_SHA256)
            self.assertEqual(x["sha256"],want[x["id"]])
            self.assertEqual(len(x["sha256"]),64)
            self.assertTrue(x["url"].startswith("https://"))
        self.assertEqual(len(r["source_authority_gaps"]),3)
        for gap in r["source_authority_gaps"]:
            self.assertIsNone(gap["original_publisher_response_sha256"])
            self.assertFalse(gap["source_bytes_reacquired_this_turn"])
            self.assertTrue(gap["metric"].startswith("UNKNOWN"))
        self.assertFalse(r["original_transaction_issuer_authenticity_independently_attested"])
        self.assertFalse(r["commercial_customer_use_rights_approved"])
        self.assertFalse(r["independent_human_qa_completed"])
        self.assertTrue(r["qa_simulation_not_human_signoff"])
        self.assertEqual(r["real_customer_freight_error_labels"],0)
        self.assertEqual(r["verified_retally_cash_cents"],0)
        self.assertEqual(r["hold_state"],"PARTIAL_PUBLISHER_BYTE_VERIFICATION_NOT_FULL_CUSTOMER_BENCHMARK")

    def test_accepted_source_hashes_are_exact_existing_run_receipts(self):
        self.check(self.receipt())

    def test_synthetic_publisher_authority_and_cash_forgery_is_rejected(self):
        import copy
        original=self.receipt()
        attacks=[
            lambda x:x["verified_sources"][0].update(sha256="a"*64),
            lambda x:x["source_authority_gaps"][0].update(original_publisher_response_sha256="b"*64),
            lambda x:x.update(verified_original_hosted_files_count=8),
            lambda x:x.update(real_customer_freight_error_labels=1),
            lambda x:x.update(verified_retally_cash_cents=1),
            lambda x:x.update(independent_human_qa_completed=True),
            lambda x:x.update(commercial_customer_use_rights_approved=True),
            lambda x:x.update(hold_state="FULL_CUSTOMER_ACCURACY_VERIFIED"),
        ]
        for n,attack in enumerate(attacks):
            with self.subTest(synthetic_attack=n),self.assertRaises(AssertionError):
                x=copy.deepcopy(original);attack(x);self.check(x)


class RetallyLegacySourceTreeCompletenessTests(unittest.TestCase):
    """Second-pass read-only Git-tree inventory for branches exceeding compare limits."""

    _root = Path(__file__).with_name("research_lab") / "legacy_archive"

    @staticmethod
    def _git_blob_sha(raw):
        return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()

    def _load(self):
        root = self._root
        receipt = json.loads((root / "subtree_inventory_v1.json").read_text(encoding="utf-8"))
        anchors = []
        for meta in receipt["anchored_groups"]:
            raw = (root / meta["path"]).read_bytes()
            self.assertEqual(self._git_blob_sha(raw), meta["git_blob_sha1"])
            anchors.extend(json.loads(raw)["records"])
        subtrees = []
        for meta in receipt["complete_tree_groups"]:
            raw = (root / meta["path"]).read_bytes()
            self.assertEqual(self._git_blob_sha(raw), meta["git_blob_sha1"])
            subtrees.extend(json.loads(raw)["records"])
        return receipt, anchors, subtrees

    def _check(self, receipt, anchors, subtrees):
        self.assertEqual(receipt["inventory_id"], "RETALLY_LEGACY_COMPLETE_SOURCE_SUBTREE_CENSUS_2026_10_30")
        self.assertEqual(receipt["branches_with_capped_compare_fallback"], 8)
        self.assertEqual(receipt["unique_source_directory_trees"], 10)
        self.assertEqual(receipt["total_entries_across_unique_trees"], 209)
        self.assertTrue(receipt["all_selected_source_directory_tree_reads_complete"])
        self.assertTrue(receipt["branches_no_code_or_schedule_migration"])
        self.assertFalse(receipt["original_publisher_sha256_available_for_these_git_trees"])
        self.assertEqual(receipt["newly_cleared_commercial_customer_source_rights"], 0)
        self.assertFalse(receipt["fully_migrated_historical_contents"])
        self.assertEqual(len(anchors), 8)
        self.assertEqual(len({a["ref"] for a in anchors}), 8)
        self.assertTrue(all(a["status"] == "NESTED_TREE_ONLY_PENDING_READ" for a in anchors))
        self.assertEqual(len(subtrees), 10)
        sha_map = {x["tree_sha"]: x for x in subtrees}
        self.assertEqual(len(sha_map), 10)
        self.assertEqual(sum(x["file_count"] for x in subtrees), 209)
        selected_dirs = set(receipt["selected_directory_names"])
        self.assertEqual(selected_dirs, {"freight/research", "freight/fixtures", "freight/evidence", "freight/lab_archive_repairs"})
        for tree in subtrees:
            self.assertTrue(tree["complete"])
            self.assertIn(tree["prefix"], selected_dirs)
            self.assertRegex(tree["tree_sha"], r"^[a-f0-9]{40}$")
            self.assertEqual(tree["file_count"], len(tree["paths"]))
            self.assertEqual(len({x["path"] for x in tree["paths"]}), tree["file_count"])
            for x in tree["paths"]:
                self.assertTrue(x["path"].startswith(tree["prefix"] + "/"))
                self.assertRegex(x["sha"], r"^[a-f0-9]{40}$")
        for a in anchors:
            self.assertEqual(a["entries"] > 0, True)
            self.assertEqual({x["path"] for x in a["dirs"]}, selected_dirs)
            for d in a["dirs"]:
                self.assertIn(d["sha"], sha_map)
                self.assertEqual(sha_map[d["sha"]]["prefix"], d["path"])
        self.assertTrue(receipt["caveats"])
        self.assertIn("GIT_TREE_METADATA_ONLY", receipt["scope"])

    def test_capped_compare_cases_are_recovered_from_complete_subtree_trees(self):
        self._check(*self._load())

    def test_synthetic_false_complete_migration_and_source_claims_fail_closed(self):
        receipt, anchors, subtrees = self._load()
        self._check(receipt, anchors, subtrees)
        for key, forged in (
            ("fully_migrated_historical_contents", True),
            ("newly_cleared_commercial_customer_source_rights", 1),
            ("original_publisher_sha256_available_for_these_git_trees", True),
            ("unique_source_directory_trees", 9),
            ("total_entries_across_unique_trees", 210),
        ):
            with self.subTest(synthetic_forgery=key), self.assertRaises(AssertionError):
                x = json.loads(json.dumps(receipt))
                x[key] = forged
                self._check(x, anchors, subtrees)
        with self.assertRaises(AssertionError):
            mutated = json.loads(json.dumps(subtrees))
            mutated[0]["paths"].pop()
            self._check(receipt, anchors, mutated)
        with self.assertRaises(AssertionError):
            mutated = json.loads(json.dumps(anchors))
            mutated[0]["dirs"][0]["sha"] = "0" * 40
            self._check(receipt, mutated, subtrees)



if __name__ == "__main__":
    unittest.main()
