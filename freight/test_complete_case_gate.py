"""Synthetic-only independent freight-case chain controls. NO real third-party rows."""
from __future__ import annotations

from dataclasses import replace
import unittest

from freight.research.complete_case_gate import (
    EvidencePointer, RecoveryCaseCandidate, assess_candidate, REQUIRED_KINDS,
    ORIGIN_REQUIRED,
)


def example_case(**changes):
    docs = tuple(EvidencePointer(
        kind=kind,
        url=f"https://example.test/evidence/{i}",
        source_sha256=f"{i+1:064x}",
        invoice_ref="SYN-INVOICE-9",
        shipment_ref="SYN-BOL-9",
        issuer_role=ORIGIN_REQUIRED[kind],
        rights_authority_url="https://example.test/licenses/explicit-case-test-rights",
        explicit_commercial_testing_grant=True,
        source_bytes_independently_verified=True,
        independently_reviewed=True,
        effective_from="2025-01-01" if kind == "EFFECTIVE_RATE_AUTHORITY" else None,
        effective_until="2025-12-31" if kind == "EFFECTIVE_RATE_AUTHORITY" else None,
        payment_payer_ref=("SYN-DEBTOR" if kind == "ORIGINAL_PAYMENT_CLEARING"
                           else "SYN-CARRIER" if kind == "EXECUTED_RECOVERY_CLEARING"
                           else None),
        payment_payee_ref=("SYN-CARRIER" if kind == "ORIGINAL_PAYMENT_CLEARING"
                           else "SYN-DEBTOR" if kind == "EXECUTED_RECOVERY_CLEARING"
                           else None),
        charge_type="LINEHAUL" if kind in ("ORIGINAL_CARRIER_INVOICE",
                                           "EFFECTIVE_RATE_AUTHORITY") else None,
    ) for i,kind in enumerate(sorted(REQUIRED_KINDS)))
    vals = dict(
        legal_debtor_ref="SYN-DEBTOR", creditor_ref="SYN-CREDITOR",
        carrier_ref="SYN-CARRIER", invoice_ref="SYN-INVOICE-9",
        shipment_ref="SYN-BOL-9", shipment_date="2025-07-15",
        currency="USD", billed_cents=100000, original_paid_cents=100000,
        controlling_charge_cents=75000, adjudicated_error_cents=25000,
        executed_recovery_cents=25000, original_payment_reference="SYN-PAID-1",
        recovery_clearing_reference="SYN-REFUND-1",
        outcome_independent_of_retally=True,
        original_payment_payer_ref="SYN-DEBTOR",
        recovery_beneficiary_ref="SYN-DEBTOR",
        charge_type="LINEHAUL",
        blind_label_frozen_sha256="a"*64, evidence=docs,
    )
    vals.update(changes)
    return RecoveryCaseCandidate(**vals)


def modify_doc(case, kind, **changes):
    return replace(case, evidence=tuple(
        replace(doc, **changes) if doc.kind == kind else doc
        for doc in case.evidence
    ))


class TestCompleteFreightChain(unittest.TestCase):
    def test_all_synthetic_metadata_never_means_software_validated(self):
        result = assess_candidate(example_case())
        self.assertEqual(result.state, "READY_FOR_INDEPENDENT_BLIND_REPLAY")
        self.assertEqual(result.flags, ())
        self.assertFalse(result.production_admission_authorized)
        self.assertFalse(result.freight_accuracy_independently_validated)
        self.assertEqual(result.verified_retally_recovered_cents, 0)

    def test_no_evidence_is_not_a_benchmark(self):
        result = assess_candidate(example_case(evidence=()))
        self.assertEqual(result.state, "RESEARCH_HOLD")
        self.assertIn("MISSING_ORIGINAL_CARRIER_INVOICE", result.flags)
        self.assertIn("MISSING_EXECUTED_RECOVERY_CLEARING", result.flags)

    def test_missing_one_bank_event_blocks(self):
        case = example_case()
        case = replace(case, evidence=tuple(x for x in case.evidence
                                               if x.kind != "ORIGINAL_PAYMENT_CLEARING"))
        self.assertIn("MISSING_ORIGINAL_PAYMENT_CLEARING", assess_candidate(case).flags)

    def test_unexecuted_award_not_paid_refund(self):
        r = assess_candidate(example_case(executed_recovery_cents=0))
        self.assertIn("RECOVERY_NOT_EXECUTED_OR_EXCEEDS_ERROR", r.flags)
        self.assertEqual(r.verified_retally_recovered_cents, 0)

    def test_liability_transfer_never_promotes(self):
        result = assess_candidate(example_case(liability_transfer_only=True))
        self.assertIn("NONCASH_LIABILITY_TRANSFER_NOT_A_RECOVERY", result.flags)

    def test_just_linking_filing_does_not_grant_commercial_reuse(self):
        c = modify_doc(example_case(), "ORIGINAL_CARRIER_INVOICE",
                       explicit_commercial_testing_grant=False)
        self.assertIn("COMMERCIAL_TEST_RIGHTS_NOT_CLEARED",
                      assess_candidate(c).flags)

    def test_public_paper_without_original_carrier_invoice_fails(self):
        c = modify_doc(example_case(), "ORIGINAL_CARRIER_INVOICE",
                       issuer_role="PUBLIC_GOVERNMENT_CASE_SUMMARY")
        self.assertIn("NOT_ORIGINAL_OR_INDEPENDENT_SOURCE_ORIGINAL_CARRIER_INVOICE",
                      assess_candidate(c).flags)

    def test_authorized_disbursement_not_bank_clearing(self):
        c = modify_doc(example_case(), "ORIGINAL_PAYMENT_CLEARING",
                       issuer_role="ACCOUNTING_LEDGER_MARKED_FULLY_PAID")
        self.assertIn("NOT_ORIGINAL_OR_INDEPENDENT_SOURCE_ORIGINAL_PAYMENT_CLEARING",
                      assess_candidate(c).flags)

    def test_rate_wrong_effective_date(self):
        c = modify_doc(example_case(), "EFFECTIVE_RATE_AUTHORITY",
                       effective_from="2026-01-01")
        self.assertIn("RATE_NOT_CONFIRMED_EFFECTIVE_AT_SHIPMENT",
                      assess_candidate(c).flags)

    def test_expired_rate(self):
        c = modify_doc(example_case(), "EFFECTIVE_RATE_AUTHORITY",
                       effective_until="2025-07-14")
        self.assertIn("RATE_NOT_CONFIRMED_EFFECTIVE_AT_SHIPMENT",
                      assess_candidate(c).flags)

    def test_filer_credibility_not_equivalent_to_undisputed_truth(self):
        r = assess_candidate(example_case(outcome_independent_of_retally=False))
        self.assertIn("NOT_INDEPENDENTLY_ADJUDICATED", r.flags)

    def test_no_blind_label_freeze(self):
        r = assess_candidate(example_case(blind_label_frozen_sha256=None))
        self.assertIn("BLIND_FROZEN_LABEL_MISSING", r.flags)

    def test_missing_source_bytes_independently_checked(self):
        c = modify_doc(example_case(), "EXECUTED_RECOVERY_CLEARING",
                       source_bytes_independently_verified=False)
        self.assertIn("SOURCE_NOT_INDEPENDENTLY_VERIFIED",
                      assess_candidate(c).flags)

    def test_provenance_missing_or_untrusted(self):
        c = modify_doc(example_case(), "ORIGINAL_CARRIER_INVOICE",
                       url="https://example.test.evil.invalid/claim",
                       source_sha256="not-sha256")
        self.assertIn("SOURCE_PROVENANCE_UNVERIFIED",
                      assess_candidate(c).flags)

    def test_bad_shipment_cross_join_is_blocked(self):
        c = modify_doc(example_case(), "SHIPMENT_BOL_POD", shipment_ref="OTHER-BOL")
        self.assertIn("SHIPMENT_IDENTITY_MISMATCH", assess_candidate(c).flags)

    def test_cross_invoice_recovery_is_not_a_match(self):
        c = modify_doc(example_case(), "EXECUTED_RECOVERY_CLEARING",
                       invoice_ref="OTHER-INVOICE")
        self.assertIn("INVOICE_IDENTITY_MISMATCH", assess_candidate(c).flags)

    def test_invoice_face_vs_correct_rate_must_equal_independent_label(self):
        r = assess_candidate(example_case(adjudicated_error_cents=24999))
        self.assertIn("ADJUDICATED_ERROR_ARITHMETIC_UNSUPPORTED", r.flags)

    def test_duplicate_source_pdf_cannot_fill_separate_roles(self):
        c = example_case()
        reused = c.evidence[0].source_sha256
        c = modify_doc(c, "EXECUTED_RECOVERY_CLEARING", source_sha256=reused)
        self.assertIn("INDEPENDENT_DOCUMENT_PROVENANCE_NOT_DISTINCT",
                      assess_candidate(c).flags)

    def test_wrong_currency_and_bool_money_block(self):
        r = assess_candidate(example_case(currency="GBP", original_paid_cents=True))
        self.assertIn("CURRENCY_SCOPE_UNSUPPORTED", r.flags)
        self.assertIn("INVALID_CENTS", r.flags)

    def test_unhashable_digest_is_review_hold_not_exception(self):
        c = modify_doc(example_case(), "ORIGINAL_CARRIER_INVOICE",
                       source_sha256=["invalid", "digest"])
        result = assess_candidate(c)
        self.assertIn("SOURCE_PROVENANCE_UNVERIFIED", result.flags)
        self.assertEqual(result.state, "RESEARCH_HOLD")

    def test_unhashable_evidence_kind_is_review_hold_not_exception(self):
        c = replace(example_case(),
                    evidence=(replace(example_case().evidence[0], kind=["bad"]),))
        result = assess_candidate(c)
        self.assertIn("UNKNOWN_EVIDENCE_ROLE", result.flags)
        self.assertEqual(result.state, "RESEARCH_HOLD")


    def test_original_payment_payer_is_required(self):
        result = assess_candidate(example_case(original_payment_payer_ref=None))
        self.assertIn("ORIGINAL_PAYMENT_PAYER_UNVERIFIED", result.flags)
        self.assertEqual(result.state, "RESEARCH_HOLD")

    def test_customer_recovery_beneficiary_is_required(self):
        result = assess_candidate(example_case(recovery_beneficiary_ref=None))
        self.assertIn("CUSTOMER_RECOVERY_BENEFICIARY_UNVERIFIED", result.flags)

    def test_direct_recovery_cannot_substitute_different_original_payer(self):
        result = assess_candidate(example_case(recovery_beneficiary_ref="SYN-OTHER"))
        self.assertIn("DIRECT_CUSTOMER_RECOVERY_IDENTITY_MISMATCH", result.flags)

    def test_court_confirmed_credit_to_forwarder_is_not_customer_cash(self):
        case = modify_doc(example_case(), "EXECUTED_RECOVERY_CLEARING",
                          payment_payee_ref="SYN-FORWARDER")
        result = assess_candidate(case)
        self.assertIn("REFUND_TO_INTERMEDIARY_NOT_CUSTOMER_RECOVERY", result.flags)
        self.assertEqual(result.state, "RESEARCH_HOLD")
        self.assertEqual(result.verified_retally_recovered_cents, 0)

    def test_bank_credit_reference_without_payee_identity_is_not_recovery(self):
        case = modify_doc(example_case(), "EXECUTED_RECOVERY_CLEARING",
                          payment_payee_ref=None)
        self.assertIn("EXECUTED_REFUND_BANK_PARTIES_MISSING",
                      assess_candidate(case).flags)

    def test_original_bank_payment_requires_payer_and_payee(self):
        case = modify_doc(example_case(), "ORIGINAL_PAYMENT_CLEARING",
                          payment_payer_ref=None)
        self.assertIn("ORIGINAL_BANK_PAYMENT_PARTIES_MISSING",
                      assess_candidate(case).flags)

    def test_original_payer_bank_record_must_match_case(self):
        case = modify_doc(example_case(), "ORIGINAL_PAYMENT_CLEARING",
                          payment_payer_ref="SYN-DIFFERENT-PAYER")
        self.assertIn("ORIGINAL_BANK_PAYMENT_PAYER_MISMATCH",
                      assess_candidate(case).flags)

    def test_same_customer_across_both_bank_events_still_not_software_proof(self):
        result = assess_candidate(example_case())
        self.assertEqual(result.state, "READY_FOR_INDEPENDENT_BLIND_REPLAY")
        self.assertFalse(result.freight_accuracy_independently_validated)
        self.assertEqual(result.verified_retally_recovered_cents, 0)

    def test_carrier_detention_invoice_cannot_use_demurrage_tariff(self):
        c = example_case(charge_type="DETENTION")
        c = modify_doc(c, "ORIGINAL_CARRIER_INVOICE", charge_type="DETENTION")
        c = modify_doc(c, "EFFECTIVE_RATE_AUTHORITY", charge_type="DEMURRAGE")
        result = assess_candidate(c)
        self.assertIn("INVOICE_RATE_SERVICE_CLASS_MISMATCH", result.flags)
        self.assertEqual(result.state, "RESEARCH_HOLD")
        self.assertEqual(result.verified_retally_recovered_cents, 0)

    def test_detention_invoice_with_source_verified_detention_rate_is_only_ready(self):
        c = example_case(charge_type="DETENTION")
        c = modify_doc(c, "ORIGINAL_CARRIER_INVOICE", charge_type="DETENTION")
        c = modify_doc(c, "EFFECTIVE_RATE_AUTHORITY", charge_type="DETENTION")
        result = assess_candidate(c)
        self.assertEqual(result.state, "READY_FOR_INDEPENDENT_BLIND_REPLAY")
        self.assertFalse(result.freight_accuracy_independently_validated)

    def test_unknown_rate_service_class_fails_closed(self):
        c = modify_doc(example_case(), "EFFECTIVE_RATE_AUTHORITY", charge_type=None)
        self.assertIn("INVOICE_OR_RATE_SERVICE_CLASS_NOT_SOURCE_VERIFIED",
                      assess_candidate(c).flags)

    def test_unknown_invoice_service_class_fails_closed(self):
        c = modify_doc(example_case(), "ORIGINAL_CARRIER_INVOICE", charge_type=None)
        self.assertIn("INVOICE_OR_RATE_SERVICE_CLASS_NOT_SOURCE_VERIFIED",
                      assess_candidate(c).flags)

    def test_case_without_known_charge_type_never_passes(self):
        self.assertIn("CASE_CHARGE_TYPE_UNVERIFIED",
                      assess_candidate(example_case(charge_type=None)).flags)

    def test_merged_detention_and_demurrage_require_explicit_source_agreement(self):
        c = example_case(charge_type="MERGED_DETENTION_DEMURRAGE")
        c = modify_doc(c, "ORIGINAL_CARRIER_INVOICE",
                       charge_type="MERGED_DETENTION_DEMURRAGE")
        c = modify_doc(c, "EFFECTIVE_RATE_AUTHORITY",
                       charge_type="MERGED_DETENTION_DEMURRAGE")
        self.assertEqual(assess_candidate(c).state,
                         "READY_FOR_INDEPENDENT_BLIND_REPLAY")

    def test_bogus_rate_service_class_must_not_pass(self):
        c = modify_doc(example_case(), "EFFECTIVE_RATE_AUTHORITY",
                       charge_type="CARRIER_PRICING")
        self.assertIn("INVOICE_OR_RATE_SERVICE_CLASS_NOT_SOURCE_VERIFIED",
                      assess_candidate(c).flags)

    def test_aggregate_statement_not_initial_paid_voucher(self):
        c = modify_doc(example_case(), "ORIGINAL_PAYMENT_CLEARING",
                       issuer_role="COURT_CLAIM_REGISTER")
        self.assertEqual(assess_candidate(c).state, "RESEARCH_HOLD")


if __name__ == "__main__":
    unittest.main()
