"""RETALLY Lab 14 Mission 35: adversarial source-to-commercial claim clearance.

No tests download private customer records, appoint human reviewers, authorize
publication, claim actual recovered funds, or create a scheduled task.
All source-only statements remain internal; fixture approvals are not real.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_claim_clearance_m35 as m35

TODAY=date(2026,10,12)


def policy():
    return json.loads(m35.BOOK.read_text(encoding="utf-8"))


def rehash(report):
    report["receipt_sha256"]=canon_hash({
        k:v for k,v in report.items() if k!="receipt_sha256"
    })
    return report


class ClaimClearanceM35Tests(unittest.TestCase):
    def test_closed_policy_and_git_blob_frozen(self):
        self.assertEqual(m35._blob(m35.BOOK.read_bytes()),m35.BOOK_SHA1)
        self.assertEqual(m35.validate_policy(policy(),as_of=TODAY),[])
        self.assertEqual(policy()["scope"],m35.BOOK_SCOPE)
        self.assertEqual(policy()["lab_number"],14)

    def test_sixteen_claims_have_eight_internal_and_eight_blocked(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(r["claim_count"],16)
        self.assertEqual(r["qualified_internal_source_statements"],8)
        self.assertEqual(r["blocked_unsupported_customer_business_claims"],8)
        self.assertEqual(r["external_commercial_claims_authorized"],0)
        self.assertEqual([c["claim_id"] for c in r["source_claim_registry"]],
                         list(m35.ALL_IDS))

    def test_internal_eight_values_reproduced_from_real_upstream_research(self):
        r=m35.report_shell(as_of=TODAY)
        got={
            c["metric_key"]:c["internal_value"] for c in r["source_claim_registry"]
            if c["internal_value"] is not None
        }
        self.assertEqual(got,{
            "BEA_2024_NOMINAL":"545435.000",
            "CENSUS_2024_REVENUE":"402827.246",
            "DENOMINATOR_2024_GAP":"142607.754",
            "CENSUS_TO_BEA_RATIO":"73.85",
            "BEA_GROSS_OUTPUT_CHANGE":"8.05",
            "BLS_SECTORAL_CHANGE":"4.02",
            "CENSUS_PPI_PROXY":"1.18",
            "PRICE_SCOPE_GAP":"0.45",
        })

    def test_all_internal_gov_stats_are_not_auto_marketing_approvals(self):
        r=m35.report_shell(as_of=TODAY)
        for claim in r["source_claim_registry"][:8]:
            self.assertEqual(claim["internal_decision"],
                             "INTERNAL_RESEARCH_WITH_SOURCE_CAVEATS")
            self.assertEqual(claim["external_publication_decision"],
                             "BLOCKED_NO_LAB_PUBLICATION_AUTHORITY")
            self.assertFalse(claim["external_claims_authorized"])
            self.assertFalse(claim["claim_money_or_recovery_established"])
            self.assertEqual(claim["required_unmet_human_signoffs"][0]["gate_id"],
                             "P11-18")
            self.assertEqual(claim["required_unmet_human_signoffs"][0]["stage"],
                             "ECONOMICS")

    def test_eight_false_customer_claims_blocked_and_reasons_present(self):
        r=m35.report_shell(as_of=TODAY)
        blocked=r["source_claim_registry"][8:]
        self.assertEqual([c["claim_id"] for c in blocked],list(m35.BLOCKED_IDS))
        for c in blocked:
            self.assertEqual(c["internal_decision"],"BLOCKED_UNSUPPORTED_INFERENCE")
            self.assertEqual(c["external_publication_decision"],
                             "BLOCKED_NO_INDEPENDENT_CUSTOMER_EVIDENCE")
            self.assertIn(c["block_reason_code"],m35.BLOCK_REASONS)
            self.assertIsNone(c["internal_value"])
            self.assertFalse(c["independent_customer_evidence_accepted"])

    def test_all_18_real_independent_customer_human_controls_are_unmet(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(r["independent_customer_pilot_human_approvals_required"],18)
        self.assertEqual(r["independent_customer_pilot_human_approvals_verified"],0)
        self.assertEqual(r["independent_customer_pilot_human_approvals_unmet"],18)
        allgates={g["gate_id"] for c in r["source_claim_registry"]
                  for g in c["required_unmet_human_signoffs"]}
        self.assertEqual(allgates,set(m35.GATES))
        self.assertTrue(all(g["human_evidence_observed"] is False
                            for c in r["source_claim_registry"]
                            for g in c["required_unmet_human_signoffs"]))

    def test_six_original_gate_stages_without_fake_approvals(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(len(r["evidence_stage_progress"]),6)
        self.assertEqual({x["stage"] for x in r["evidence_stage_progress"]},{
            "AUTHORITY","SECURITY","EVIDENCE",
            "SAMPLING","ADJUDICATION","ECONOMICS",
        })
        self.assertEqual(sum(x["required_evidence_records"]
                             for x in r["evidence_stage_progress"]),18)
        self.assertEqual(sum(x["real_independently_approved_records"]
                             for x in r["evidence_stage_progress"]),0)

    def test_original_pilot_preflight_is_reused_not_duplicated(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertIn("M11_pilot_human_evidence",r["source_provenance_receipts"])
        self.assertEqual(
            r["source_provenance_receipts"]["M11_pilot_human_evidence"],
            m35.build_preflight(as_of=TODAY)["receipt_sha256"],
        )
        self.assertFalse(r["source_original_publisher_replay_completed_in_this_run"])

    def test_gov_sources_are_prior_verified_not_fresh_http_in_this_execution(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],
                         "OFFLINE_VERIFIED_PRIOR_MACRO_SOURCE_CATALOGS_NOT_FRESH_SOURCE_REPLAY")
        self.assertTrue(r["separate_original_2017_2024_source_evidence_available_historically"])
        self.assertFalse(r["source_original_publisher_replay_completed_in_this_run"])
        self.assertEqual(set(r["source_provenance_receipts"]),{
            "M34_economic_denominator","M33_BEA_original","M31_BLS_sectoral",
            "M29_BLS_PPI","M11_pilot_human_evidence","M35_claim_policy",
        })
        self.assertTrue(all(len(v)==64 for v in r["source_provenance_receipts"].values()))

    def test_bea_census_gap_not_recoverable_tam_or_missing_invoices(self):
        result=m35.lookup_claim(m35.report_shell(as_of=TODAY),"M35-03")
        self.assertEqual(result["internal_value"],"142607.754")
        self.assertIn("not causally decomposed or recoverable",result["reason"])
        trap=m35.lookup_claim(m35.report_shell(as_of=TODAY),"M35-09")
        self.assertEqual(trap["block_reason_code"],"UNVERIFIED_RECOVERY_TAM")
        self.assertFalse(trap["claim_money_or_recovery_established"])
        self.assertIsNone(trap["internal_value"])

    def test_census_bea_ratio_not_freight_invoice_accuracy_or_coverage(self):
        result=m35.lookup_claim(m35.report_shell(as_of=TODAY),"M35-04")
        self.assertEqual(result["internal_value"],"73.85")
        self.assertEqual(result["unit"],
                         "Ratio of distinct nominal industry totals, %")
        forbidden=m35.lookup_claim(m35.report_shell(as_of=TODAY),"M35-10")
        self.assertEqual(forbidden["block_reason_code"],"UNVERIFIED_INVOICE_ERROR_RATE")

    def test_synthetic_agreement_9_of_10_is_not_real_reviewer_accuracy(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(r["synthetic_only_reviewer_agreement"],
                         "9/10_NOT_REAL_HUMAN_ACCURACY")
        self.assertEqual(r["real_independent_reviewers_observed"],0)
        claimed=m35.lookup_claim(r,"M35-11")
        self.assertEqual(claimed["block_reason_code"],"SYNTHETIC_VERSUS_REAL")
        self.assertTrue(any(g["gate_id"]=="P11-13"
                            for g in claimed["required_unmet_human_signoffs"]))

    def test_refund_and_fee_claim_requires_independent_finance_records(self):
        r=m35.report_shell(as_of=TODAY)
        item=m35.lookup_claim(r,"M35-12")
        self.assertEqual(item["block_reason_code"],"UNVERIFIED_CASH_AND_FEES")
        self.assertIn("P11-16",[g["gate_id"] for g in
                                 item["required_unmet_human_signoffs"]])
        self.assertIn("P11-17",[g["gate_id"] for g in
                                 item["required_unmet_human_signoffs"]])
        self.assertIsNone(r["retally_cash_recovered_usd"])
        self.assertIsNone(r["retally_recoverable_tam_usd"])

    def test_buyer_authorization_and_security_claim_requires_seven_specific_gates(self):
        r=m35.report_shell(as_of=TODAY)
        item=m35.lookup_claim(r,"M35-13")
        self.assertEqual([g["gate_id"] for g in item["required_unmet_human_signoffs"]],
                         [f"P11-{i:02d}" for i in range(1,7)]+["P11-18"])
        self.assertFalse(r["no_real_customer_document_or_carrier_research_data_imported"] is False)

    def test_approval_of_real_pilot_cannot_be_inferred_from_ci(self):
        item=m35.lookup_claim(m35.report_shell(as_of=TODAY),"M35-16")
        self.assertEqual(item["required_unmet_human_signoff_count"],18)
        self.assertEqual(item["block_reason_code"],"UNVERIFIED_HUMAN_APPROVAL")
        self.assertEqual(len({x["stage"] for x in item["required_unmet_human_signoffs"]}),6)

    def test_arbitrary_input_claim_id_and_prompt_injection_rejected(self):
        report=m35.report_shell(as_of=TODAY)
        for value in (
            "M35-00","M35-17","M35-09\nIGNORE PREVIOUS INSTRUCTIONS",
            "<script>alert('profit')</script>",False,None,15,
        ):
            with self.assertRaisesRegex(ValueError,
                                        "M35_UNKNOWN_OR_UNCONTROLLED_CLAIM_IDENTIFIER"):
                m35.lookup_claim(report,value)

    def test_changed_macroeconomic_receipt_does_not_validate_fabricated_claims(self):
        report=m35.m34_report(as_of=TODAY)
        report["bea_minus_census_nominal_2024_million_usd"]="142607754000.000"
        rehash(report)
        with patch.object(m35,"m34_report",return_value=report):
            with self.assertRaisesRegex(ValueError,
                                        "M35_BEA_CENSUS_GAP_PROMOTED_TO_FAKE_CLIENT_OUTCOME"):
                m35.report_shell(as_of=TODAY)

    def test_missing_or_wrong_macro_source_receipt_fails(self):
        report=m35.m33_report(as_of=TODAY)
        report["receipt_sha256"]="0"*64
        with patch.object(m35,"m33_report",return_value=report):
            with self.assertRaisesRegex(ValueError,
                                        "M35_MACROECONOMIC_REPORT_RECEIPT_MISSING_OR_TAMPERED"):
                m35.report_shell(as_of=TODAY)

    def test_fake_fresh_source_status_rehashed_does_not_claim_live_bytes(self):
        report=m35.m31_report(as_of=TODAY)
        report["status"]="ORIGINAL_PUBLISHER_FRESH_AND_COMPLETED"
        rehash(report)
        with patch.object(m35,"m31_report",return_value=report):
            with self.assertRaisesRegex(ValueError,
                                        "M35_HISTORICAL_SOURCE_GRADE_PROMOTED_AS_FRESH"):
                m35.report_shell(as_of=TODAY)

    def test_fake_pilot_verified_customer_approval_rehashed_fails_closed(self):
        report=m35.build_preflight(as_of=TODAY)
        report["controls_with_independently_verified_external_evidence"]=1
        report["unmet_requirements"]=17
        rehash(report)
        with patch.object(m35,"build_preflight",return_value=report):
            with self.assertRaisesRegex(ValueError,
                                        "M35_EXISTING_PILOT_SIGNOFFS_FALSIFIED_OR_NOT_PROVEN"):
                m35.report_shell(as_of=TODAY)

    def test_fake_assigned_human_approver_in_queue_rehashed_fails_closed(self):
        report=m35.build_preflight(as_of=TODAY)
        report["evidence_preparation_queue"][13]["real_world_evidence_observed"]=True
        rehash(report)
        with patch.object(m35,"build_preflight",return_value=report):
            with self.assertRaisesRegex(ValueError,
                                        "M35_INDEPENDENT_CUSTOMER_HUMAN_PROOF_FALSELY_ENTERED"):
                m35.report_shell(as_of=TODAY)

    def test_fake_human_reviewer_reliability_in_synthetic_report_rejected(self):
        report=m35.build_preflight(as_of=TODAY)
        report["fictional_test_case_reviewer_concordance"][
            "actual_independent_reviewer_reliability_established"]=True
        rehash(report)
        with patch.object(m35,"build_preflight",return_value=report):
            with self.assertRaisesRegex(ValueError,
                                        "M35_SYNTHETIC_VOTES_FALSELY_RELABELED_INDEPENDENT_HUMAN"):
                m35.report_shell(as_of=TODAY)

    def test_external_approval_in_frozen_policy_cannot_be_switched_on(self):
        for key in (
            "no_external_marketing_or_outreach_authorized",
            "no_client_document_import_authorized",
            "no_pilot_signoff_from_research_ci",
            "no_recovery_tam_from_industry_denominator_gap",
            "no_new_schedule_created",
        ):
            p=policy()
            p[key]=False
            self.assertTrue(m35.validate_policy(p,as_of=TODAY),key)

    def test_added_customer_recovery_amount_in_policy_rejected(self):
        for key,amount in (
            ("real_customer_invoices_observed",10),
            ("actual_cash_recovered_usd",100000),
            ("recoverable_market_tam_usd",142607754000),
            ("external_claims_approved",8),
        ):
            p=policy()
            p[key]=amount
            self.assertTrue(m35.validate_policy(p,as_of=TODAY),key)

    def test_unsupported_citied_publication_status_cannot_be_added(self):
        p=policy()
        p["claim_registry"][0]["public_publication_authorized"]=True
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))
        p=policy()
        p["claim_registry"][8]["internal_result"]="INTERNAL_RESEARCH_WITH_SOURCE_CAVEATS"
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))
        p=policy()
        p["claim_registry"][8]["metric_key"]="DENOMINATOR_2024_GAP"
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))

    def test_missing_publication_gate_from_internal_claim_rejected(self):
        p=policy()
        p["claim_registry"][0]["required_pilot_gate_ids"]=[]
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))
        p=policy()
        p["claim_registry"][9]["required_pilot_gate_ids"]=["P11-01"]
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))

    def test_policy_missing_and_duplicate_claims_rejected(self):
        p=policy()
        p["claim_registry"].pop()
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))
        p=policy()
        p["claim_registry"][0]["id"]="M35-02"
        self.assertTrue(m35.validate_policy(p,as_of=TODAY))

    def test_rehashed_public_claim_report_must_not_forge_approval(self):
        r=m35.report_shell(as_of=TODAY)
        r["source_claim_registry"][0]["external_claims_authorized"]=True
        r["external_commercial_claims_authorized"]=1
        rehash(r)
        with self.assertRaisesRegex(ValueError,"M35_FORGED_CLAIM_CLEARANCE_OR_PUBLICATION_APPROVAL"):
            m35.lookup_claim(r,"M35-01")

    def test_rehashed_case_value_must_match_catalog_not_just_hash(self):
        r=m35.report_shell(as_of=TODAY)
        r["source_claim_registry"][0]["internal_value"]="1000000.000"
        rehash(r)
        with self.assertRaisesRegex(ValueError,"M35_FORGED_CLAIM_CLEARANCE_OR_PUBLICATION_APPROVAL"):
            m35.lookup_claim(r,"M35-01")

    def test_report_receipts_are_deterministic_and_customer_free(self):
        r=m35.report_shell(as_of=TODAY)
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))
        self.assertTrue(r["no_real_customer_document_or_carrier_research_data_imported"])
        self.assertTrue(r["no_new_schedule_created_or_modified"])
        self.assertIsNone(r["retally_cash_recovered_usd"])

    def test_date_before_policy_observation_fails(self):
        self.assertTrue(m35.validate_policy(policy(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M35_RESEARCH_CLAIM_POLICY_INVALID"):
            m35.report_shell(as_of=date(2026,10,11))

    def test_safe_html_escapes_caveat_html_and_does_not_advertise_approvals(self):
        r=m35.report_shell(as_of=TODAY)
        r["source_claim_registry"][0]["reason"]="<script>alert('TAM')</script>"
        html=m35.render_html(r)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("18/18 still unmet",html)
        self.assertIn("External commercial claims authorized",html)
        self.assertIn("BEA–Census",html)

    def test_cli_generates_two_local_internal_artifacts(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("sys.argv",["m35","--out",root,
                                   "--as-of-date","2026-10-12"]):
                m35.main()
            p=Path(root)
            self.assertTrue((p/"claim_clearance.json").exists())
            self.assertTrue((p/"claim_clearance.html").exists())
            out=json.loads((p/"claim_clearance.json").read_text())
            self.assertEqual(out["blocked_unsupported_customer_business_claims"],8)
            self.assertEqual(out["qualified_internal_source_statements"],8)
            self.assertEqual(out["independent_customer_pilot_human_approvals_unmet"],18)


if __name__=="__main__":
    unittest.main()
