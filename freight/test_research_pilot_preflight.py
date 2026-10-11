"""RETALLY Mission 11: adversarial zero-approval pilot handoff tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import unittest

from freight.research_evidence_gate import canon_hash
from freight.research_pilot_preflight import (
    CONTRACT, _reports_are_held, build_preflight, render_html,
    validate_preflight,
)
from freight.research_validation_protocols import build_protocol_report
from freight.research_data_readiness import build_readiness
from freight.research_rehearsal import run_rehearsal
from freight.research_ground_truth import run_ground_truth

DAY = date(2026, 10, 11)


def fixture():
    """Create the actual repository's held reports, never substitute a fake pass."""
    protocols = build_protocol_report(as_of=DAY)
    sources = build_readiness(as_of=DAY, protocols=protocols)
    rehearsal = run_rehearsal(as_of=DAY, protocol_report=protocols)
    ground = run_ground_truth(as_of=DAY, protocols=protocols)
    book = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return book, protocols, sources, rehearsal, ground


def validate(arguments, when=DAY):
    return validate_preflight(*arguments, as_of=when)


def patch_sha(report):
    report["receipt_sha256"] = canon_hash({
        k: v for k, v in report.items() if k != "receipt_sha256"
    })


class PilotPreflightTests(unittest.TestCase):
    def test_eighteen_gates_six_stages_and_no_outside_evidence(self):
        book, p, s, r, g = fixture()
        self.assertEqual(validate((book, p, s, r, g)), [])
        result = build_preflight(as_of=DAY, book=book, protocols=p,
                                 sources=s, rehearsal=r, ground=g)
        self.assertEqual(result["scope"],
                         "LAB14_PROSPECTIVE_PILOT_INTERNAL_READINESS_ONLY")
        self.assertEqual(result["readiness"],
                         "BLOCKED_NO_VERIFIED_BUYER_PERMISSION_OR_REAL_EVIDENCE")
        self.assertEqual(result["required_controls"], 18)
        self.assertEqual(result["unmet_requirements"], 18)
        self.assertEqual(result["controls_with_independently_verified_external_evidence"], 0)
        self.assertEqual(result["workflow_stage_count"], 6)
        self.assertTrue(all(x["required_evidence_records"] == 3 and
                            x["actual_verified_records"] == 0 for x in result["stages"]))
        self.assertEqual(result["target_studies"], ["M7-01", "M7-06"])
        self.assertEqual(result["existing_lab_number"], 14)
        self.assertFalse(result["new_lab_created"])
        self.assertEqual(result["receipt_sha256"], canon_hash({
            k: v for k, v in result.items() if k != "receipt_sha256"
        }))
        self.assertTrue(all(
            item["real_world_evidence_observed"] is False and
            item["approval_and_storage_authorized"] is False and
            item["external_actions_permitted"] is False
            for item in result["evidence_preparation_queue"]
        ))

    def test_independently_approved_data_and_customer_results_remain_zero(self):
        r = build_preflight(as_of=DAY)
        for key in (
            "studies_with_pilot_data", "datasets_imported",
            "real_invoices_received", "actual_human_independent_reviewers",
            "verified_invoice_overcharges", "real_net_recovery_cents",
        ):
            self.assertEqual(r[key], 0, key)
        for key in (
            "external_customer_contact", "live_customer_document_intake",
            "external_claim_or_fee_action", "product_security_or_legal_clearance",
            "real_world_study_authorized", "public_performance_claims_permitted",
        ):
            self.assertIs(r[key], False)

    def test_fake_blinded_reviewer_agreement_not_human_reliability(self):
        result = build_preflight(as_of=DAY)
        agreement = result["fictional_test_case_reviewer_concordance"]
        self.assertEqual(agreement["equal_votes"], 9)
        self.assertEqual(agreement["mock_pairs"], 10)
        self.assertEqual(agreement["agreement_fraction"], "9/10")
        self.assertFalse(agreement["actual_independent_reviewer_reliability_established"])
        self.assertIn("same synthetic fixture function", agreement["why_not_valid"])
        self.assertEqual(result["fictional_invoice_cases_used_as_design_tests"], 10)

    def test_real_approval_is_never_inferred_from_healthy_ci(self):
        book, p, s, r, g = fixture()
        self.assertEqual(r["rehearsed_protocols"], 6)
        self.assertEqual(g["case_count"], 10)
        self.assertEqual(s["source_leads"], 7)
        result = build_preflight(as_of=DAY, book=book, protocols=p,
                                 sources=s, rehearsal=r, ground=g)
        self.assertEqual(result["unmet_requirements"], 18)
        self.assertEqual(result["studies_with_pilot_data"], 0)

    def test_three_controls_per_stage_and_stable_human_role_sequence(self):
        result = build_preflight(as_of=DAY)
        ids = [x["id"] for x in result["evidence_preparation_queue"]]
        self.assertEqual(ids, [f"P11-{i:02d}" for i in range(1, 19)])
        self.assertEqual(result["evidence_preparation_queue"][12]["owner_role"],
                         "INDEPENDENT_ADJUDICATOR")
        self.assertEqual(result["evidence_preparation_queue"][15]["related_studies"],
                         ["M7-06"])
        self.assertEqual(result["evidence_preparation_queue"][16]["related_studies"],
                         ["M7-06"])

    def test_unsupported_external_approval_and_contact_flags_rejected(self):
        for key, value in (
            ("no_customer_contact_authorized", False),
            ("no_new_lab", False),
            ("data_collection_enabled", True),
            ("external_carrier_or_financial_actions_allowed", True),
            ("public_performance_claims_allowed", True),
            ("privacy_security_clearance_proven", True),
            ("status", "APPROVED"),
        ):
            args = list(fixture())
            args[0][key] = value
            self.assertTrue(validate(args), key)
            with self.assertRaisesRegex(ValueError, "INVALID_PILOT_PREFLIGHT"):
                build_preflight(as_of=DAY, book=args[0], protocols=args[1],
                                sources=args[2], rehearsal=args[3],
                                ground=args[4])

    def test_fake_positive_count_or_bool_zero_fields_rejected(self):
        for key in (
            "real_customer_records_received", "approved_data_transfers",
            "real_buyer_authorizations_verified", "real_blind_reviewers_appointed",
            "live_payment_events_examined", "approved_external_study_results",
        ):
            for value in (True, 1, -1, "0"):
                args = list(fixture())
                args[0][key] = value
                self.assertTrue(validate(args), (key, value))

    def test_no_contact_identity_or_signed_document_payload_can_be_added(self):
        for key, value in (
            ("customer_email", "buyer@example.com"),
            ("signed_dua_blob", "not-real-signature"),
            ("customer_invoice_file", "/mnt/private/invoice.pdf"),
        ):
            args = list(fixture())
            args[0][key] = value
            self.assertIn("unexpected pilot fields", "; ".join(validate(args)))
        args = list(fixture())
        args[0]["gates"][0]["customer_name"] = "private customer"
        self.assertIn("missing or unexpected key", "; ".join(validate(args)))

    def test_sensitive_identifiers_cannot_hide_in_freeform_planning_fields(self):
        examples = (
            "contact shipper.name@example.com",
            "SSN 123-45-6789",
            "call (570) 555-0123",
            "file /mnt/private/customer-invoice.pdf",
            "Bearer pretendedtoken",
            "ghp_ABCDEFGHIJKLMN123456",
        )
        for example in examples:
            args = list(fixture())
            args[0]["gates"][0]["required_evidence"] += " " + example
            self.assertIn("no personal identifiers, private paths or credentials",
                          "; ".join(validate(args)), example)
        args = list(fixture())
        args[0]["intended_scope"] += " contact jane@example.com"
        self.assertIn("planning scope may not contain personal identifiers",
                      "; ".join(validate(args)))

    def test_gates_must_have_original_unverified_permits(self):
        for key, value in (
            ("status", "INDEPENDENTLY_VERIFIED"),
            ("verified", True),
            ("external_signoff_observed", True),
            ("assigned_real_person", True),
            ("receipt_of_original_evidence", "a"*64),
        ):
            args = list(fixture())
            args[0]["gates"][0][key] = value
            self.assertIn("independent signoff/evidence not established",
                          "; ".join(validate(args)), key)

    def test_malformed_or_duplicate_gate_id_cannot_be_silent(self):
        for value in ("P11-02", "P11-CUSTOMER", None):
            args = list(fixture())
            args[0]["gates"][0]["id"] = value
            self.assertIn("gate id or order", "; ".join(validate(args)))
        args = list(fixture())
        args[0]["gates"].pop()
        self.assertIn("exactly 18", "; ".join(validate(args)))
        args = list(fixture())
        args[0]["gates"].append(deepcopy(args[0]["gates"][0]))
        self.assertIn("exactly 18", "; ".join(validate(args)))

    def test_role_swapping_cannot_elevate_company_self_review_to_independent(self):
        args = list(fixture())
        args[0]["gates"][12]["owner_role"] = "RESEARCH_LEAD"
        self.assertIn("independent owner roles were changed",
                      "; ".join(validate(args)))
        args = list(fixture())
        args[0]["gates"][15]["owner_role"] = "INDEPENDENT_ADJUDICATOR"
        self.assertTrue(validate(args))

    def test_stage_scope_and_related_study_join_are_fixed(self):
        args = list(fixture())
        args[0]["gates"][2]["stage"] = "ECONOMICS"
        self.assertIn("review stage swapped", "; ".join(validate(args)))
        args = list(fixture())
        args[0]["stages"][0]["id"] = "SKIP_SECURITY"
        self.assertIn("stage scope/order/purpose changed", "; ".join(validate(args)))
        args = list(fixture())
        args[0]["gates"][15]["related_studies"] = ["M7-01"]
        self.assertIn("study boundary mismatch", "; ".join(validate(args)))

    def test_missing_evidence_or_next_step_is_fail_closed(self):
        for field in ("name", "required_evidence", "why_missing_blocks",
                      "next_internal_step"):
            args = list(fixture())
            args[0]["gates"][3][field] = ""
            self.assertTrue(validate(args), field)

    def test_original_method_sources_are_attributed_but_not_approval(self):
        r = build_preflight(as_of=DAY)
        refs = r["linked_mission_receipts"]
        self.assertEqual(set(refs), {
            "M7_protocols", "M8_rehearsal", "M9_public_data_readiness",
            "M10_synthetic_invoice", "M11_gate_definitions",
        })
        self.assertTrue(all(type(x) is str and len(x) == 64
                            for x in refs.values()))
        self.assertFalse(r["product_security_or_legal_clearance"])

    def test_upstream_protocol_tamper_is_caught_even_with_rehashed_receipt(self):
        args = list(fixture())
        args[1]["approved_preregistrations"] = 2
        patch_sha(args[1])
        self.assertIn("Mission 7", "; ".join(validate(args)))
        args = list(fixture())
        args[1]["protocols"][0]["status"] = "COMPLETED"
        patch_sha(args[1])
        self.assertIn("Mission 7 protocol status", "; ".join(validate(args)))

    def test_upstream_fraudulent_public_data_import_rejected_after_rehash(self):
        args = list(fixture())
        args[2]["datasets_imported"] = 1
        patch_sha(args[2])
        self.assertIn("Mission 9 public source", "; ".join(validate(args)))
        args = list(fixture())
        args[2]["invoice_ground_truth_benchmarks"] = 1
        patch_sha(args[2])
        self.assertIn("Mission 9 public source", "; ".join(validate(args)))

    def test_upstream_synthetic_survey_as_real_customer_rejected(self):
        args = list(fixture())
        args[3]["independent_customer_observations"] = 35
        patch_sha(args[3])
        self.assertIn("Mission 8 synthetic results", "; ".join(validate(args)))

    def test_upstream_forged_original_invoice_result_rejected(self):
        for key, value in (
            ("verified_ground_truth_cases", 10),
            ("actual_cash_recovered_cents", 300000),
            ("real_customer_cases", 1),
            ("synthetic_only", False),
        ):
            args = list(fixture())
            args[4][key] = value
            patch_sha(args[4])
            self.assertIn("Mission 10 synthetic ground truth",
                          "; ".join(validate(args)), key)

    def test_upstream_source_linkage_must_resolve_to_same_study_protocol(self):
        for idx, key in (
            (2, "protocol_report_sha256"),
            (3, "protocol_report_sha256"),
            (4, "study_design_sha256"),
        ):
            args = list(fixture())
            args[idx][key] = "0"*64
            patch_sha(args[idx])
            self.assertIn("wrong study provenance link", "; ".join(validate(args)))

    def test_mutated_digest_is_not_a_signature(self):
        args = list(fixture())
        args[4]["receipt_sha256"] = "0"*64
        self.assertIn("Mission 10 synthetic ground truth",
                      "; ".join(validate(args)))
        self.assertIn("consistency only", build_preflight(as_of=DAY)["limits"])

    def test_future_dated_scope_or_bogus_research_reference_rejected(self):
        args = list(fixture())
        args[0]["created_on"] = "2026-12-31"
        self.assertIn("future-dated", "; ".join(validate(args)))
        args = list(fixture())
        args[0]["references"][0]["url"] = "https://random-vendor.example/endorsement"
        self.assertIn("reference meaning, origin or scope altered",
                      "; ".join(validate(args)))
        args = list(fixture())
        args[0]["references"].append(deepcopy(args[0]["references"][0]))
        self.assertIn("exactly two", "; ".join(validate(args)))

    def test_all_m11_artifacts_remain_blocked_after_90_day_source_expiry(self):
        r = build_preflight(as_of=date(2027, 2, 1))
        self.assertEqual(r["public_data_sources_due_for_review"], 7)
        self.assertEqual(r["real_invoices_received"], 0)
        self.assertEqual(r["unmet_requirements"], 18)
        self.assertFalse(r["public_performance_claims_permitted"])

    def test_render_escapes_injected_html_and_does_not_advertise_approval(self):
        r = build_preflight(as_of=DAY)
        bad = deepcopy(r)
        bad["evidence_preparation_queue"][0]["name"] = '<script>alert("x")</script>'
        bad["evidence_preparation_queue"][1]["risk_if_unproven"] = (
            '<img src=x onerror=alert(1)>')
        html = render_html(bad)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img ", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("No customer consent", html)
        self.assertIn("not independent human reliability", html.lower())

    def test_statistical_precision_not_inferred_from_mock_9_of_10(self):
        r = build_preflight(as_of=DAY)
        self.assertEqual(r["fictional_test_case_reviewer_concordance"]["agreement_fraction"], "9/10")
        self.assertEqual(r["actual_human_independent_reviewers"], 0)
        self.assertEqual(r["verified_invoice_overcharges"], 0)
        self.assertNotIn("accuracy_percentage", r)


if __name__ == "__main__":
    unittest.main()
