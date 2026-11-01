"""FMC verified adjudication and reported payment is not RETALLY cash."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from freight.fmc_real_shipper_billing_lifecycle import (
    ROOT, AWARD_GROUPS, RECEIPT_KEYS, LEADER, JIMEX, JIMEX_ROWS,
    load_fixture, make_receipt, validate_fixture, verify_receipt
)
from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.priority2_evidence import review_freight_rate
from freight.unified_research_lab import ResearchError, SEEDS, digest


class FMCPublicRealShipperBillingTests(unittest.TestCase):
    def test_official_case_identity_and_explicit_source_custody_limits(self):
        d=load_fixture()
        self.assertEqual(set(d),set(ROOT)|{
            "bridgewell_cosco","hp_logistics_quote_dispute",
            "leader_commerce_msc_signed_settlement",
            "jimex_unitrans_initial_paid_detention"})
        for section in ("bridgewell_cosco","hp_logistics_quote_dispute"):
            self.assertIn(d[section]["official_initial_decision_url"],
                          SEEDS["freightrecovery"])
        self.assertIn(d["bridgewell_cosco"]["official_final_notice_url"],
                      SEEDS["freightrecovery"])
        self.assertFalse(d["official_pdf_bytes_acquired"])
        self.assertIsNone(d["official_pdf_source_sha256"])
        self.assertFalse(d["original_customer_invoice_and_bank_bytes_acquired"])
        self.assertFalse(d["source_specific_commercial_reuse_verified"])
        self.assertEqual(d["retally_independent_customer_invoice_truth_cases"],0)
        self.assertEqual(d["retally_cash_recovered_cents"],0)


    def test_fmc_2015i_original_real_shipper_settlement_and_finality(self):
        from freight.unified_research_lab import SEEDS
        c=load_fixture()["leader_commerce_msc_signed_settlement"]
        self.assertEqual(set(c),set(LEADER))
        self.assertEqual(c["shipment_public_bill_of_lading"],"MEDUUP205245")
        self.assertEqual(c["original_shipment_origin"],"BALTIMORE_USA")
        self.assertEqual(c["original_shipment_destination"],"MANAUS_BRAZIL")
        self.assertEqual(c["respondent_submitted_signed_settlement_date"],"2024-10-17")
        self.assertEqual(c["original_order_served"],"2024-11-08")
        self.assertEqual(c["final_notice_served"],"2024-12-10")
        self.assertTrue(c["fmc_describes_both_parties_signed_settlement"])
        self.assertFalse(c["signed_settlement_original_bytes_independently_held"])
        self.assertFalse(c["original_invoice_bol_bank_and_tariff_bytes_in_retally_custody"])
        self.assertIn("DISMISSED_WITH_PREJUDICE",c["settled_final_state"])
        self.assertIn(c["official_order_url"],SEEDS["freightrecovery"])
        self.assertIn(c["official_final_notice_url"],SEEDS["freightrecovery"])

    def test_signed_ocean_settlement_non_cash_cancellation_and_waiver_in_two_currencies(self):
        c=load_fixture()["leader_commerce_msc_signed_settlement"]
        self.assertEqual(c["msc_settlement_promise_cancel_OUTSTANDING_UNPAID_demurrage_usd_cents"],465000)
        self.assertTrue(c["msc_settlement_promise_end_collection"])
        self.assertFalse(c["independent_msc_receivable_writeoff_ledger_confirmation"])
        self.assertEqual(c["claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_freight_usd_cents"],300000)
        self.assertEqual(c["claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_late_fee_brl_centavos"],70000)
        self.assertFalse(c["cross_currency_addition_or_implicit_conversion_permitted"])
        self.assertFalse(c["original_bank_evidence_of_previous_claimant_payments_in_retally_custody"])
        self.assertIsNone(c["settlement_result_verified_cash_refund_usd_cents"])
        self.assertFalse(c["independent_refund_or_tender_bank_receipt_verified"])
        self.assertFalse(c["liability_finding_original_fees_unlawful"])
        self.assertEqual(c["complaint_alleged_low_water_fee_usd_cents"],300000)
        self.assertEqual(c["complaint_alleged_other_extra_fee_usd_cents"],14000)
        r=make_receipt()
        self.assertEqual(r["leader_demurrage_UNPAID_cancelled_under_settlement_usd_cents"],465000)
        self.assertEqual(r["leader_previously_paid_freight_refund_rights_waived_usd_cents"],300000)
        self.assertEqual(r["leader_previously_paid_late_fee_refund_rights_waived_brl_centavos"],70000)
        self.assertFalse(r["leader_actual_carrier_ledger_cancellation_verified"])
        self.assertFalse(r["leader_usd_brl_conversion_or_sum_allowed"])
        self.assertIsNone(r["leader_refund_received_bank_verified_usd_cents"])
        self.assertTrue(r["leader_refund_rights_released_not_new_cash_awarded"])
        self.assertIsNone(r["leader_fmc_order_adjudicated_illegal_billing_amount_cents"])
        self.assertEqual(r["retally_recovered_cash_cents"],0)
        self.assertEqual(r["modern_retally_invoice_accuracy_labels"],0)

    def test_waived_refund_and_cancellation_cannot_be_promoted_to_customer_cash(self):
        d=load_fixture()
        changes=(
            ("msc_settlement_promise_cancel_OUTSTANDING_UNPAID_demurrage_usd_cents",465001),
            ("claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_freight_usd_cents",300001),
            ("claimant_settlement_waives_refund_rights_on_PREVIOUSLY_PAID_late_fee_brl_centavos",70001),
            ("independent_msc_receivable_writeoff_ledger_confirmation",True),
            ("original_bank_evidence_of_previous_claimant_payments_in_retally_custody",True),
            ("settlement_result_verified_cash_refund_usd_cents",465000),
            ("liability_finding_original_fees_unlawful",True),
            ("signed_settlement_original_bytes_independently_held",True),
            ("cross_currency_addition_or_implicit_conversion_permitted",True),
            ("claimant_original_economic_loss_independently_verified",True),
            ("final_notice_served","2024-11-08"),
            ("third_party_contract_rights_for_retally_use",True),
        )
        for name,value in changes:
            with self.subTest(field=name):
                tampered=deepcopy(d)
                tampered["leader_commerce_msc_signed_settlement"][name]=value
                with self.assertRaises(ResearchError):
                    validate_fixture(tampered)
        bad=deepcopy(d)
        bad["leader_commerce_msc_signed_settlement"]["new_paid_refund"]=465000
        with self.assertRaises(ResearchError):
            validate_fixture(bad)

    def test_even_rehashed_false_wrote_off_debt_or_refund_receipt_rejected(self):
        original=make_receipt()
        from freight.unified_research_lab import digest
        changes=(
            ("leader_actual_carrier_ledger_cancellation_verified",True),
            ("leader_refund_received_bank_verified_usd_cents",465000),
            ("leader_previously_paid_freight_refund_rights_waived_usd_cents",0),
            ("leader_demurrage_UNPAID_cancelled_under_settlement_usd_cents",0),
            ("leader_usd_brl_conversion_or_sum_allowed",True),
            ("leader_fmc_order_adjudicated_illegal_billing_amount_cents",465000),
            ("retally_recovered_cash_cents",465000),
        )
        for name,value in changes:
            with self.subTest(name=name):
                tampered=deepcopy(original)
                tampered[name]=value
                tampered["receipt_sha256"]=digest({
                    k:v for k,v in tampered.items() if k!="receipt_sha256"})
                with self.assertRaises(ResearchError):
                    verify_receipt(tampered)

    def test_january_2026_official_notice_principal_interest_and_due_date(self):
        case=load_fixture()["bridgewell_cosco"]
        self.assertEqual(case["initial_decision_served"],"2025-09-29")
        self.assertEqual(case["official_final_notice_served"],"2026-01-05")
        self.assertEqual(case["payment_due_date"],"2026-01-20")
        self.assertEqual(case["original_reparation_claim_cents"],4378000)
        self.assertEqual(case["administratively_final_amount_due_cents"],2828931)
        self.assertEqual(case["reparations_principal_cents"],2432880)
        self.assertEqual(case["interest_through_january_5_2026_cents"],396051)
        self.assertEqual(case["reparations_principal_cents"] +
                         case["interest_through_january_5_2026_cents"],2828931)
        self.assertEqual(case["adjudication"],
                         "INVALID_DEMURRAGE_DETENTION_INVOICE_CONTENT_REPARATIONS_GRANTED")
        self.assertEqual(
            [(r["multiplicity"],r["principal_cents_each"],r["interest_cents_each"])
             for r in case["reparation_award_groups"]],list(AWARD_GROUPS))
        self.assertEqual(sum(r[0]*r[1] for r in AWARD_GROUPS),2432880)
        self.assertEqual(sum(r[0]*r[2] for r in AWARD_GROUPS),396051)
        # A Notice's award groups are NOT synonymous with invoices or containers.
        self.assertEqual(sum(r[0] for r in AWARD_GROUPS),10)

    def test_received_date_is_reported_but_not_independently_bank_verified(self):
        case=load_fixture()["bridgewell_cosco"]
        self.assertEqual(case["later_enforcement_docket"],"FMC_26-13")
        self.assertEqual(case["later_order_to_show_cause_date"],"2026-10-02")
        self.assertEqual(case["fmc_original_enforcement_order_document_id"],145944)
        self.assertEqual(case["reported_actual_customer_payment_received_date"],"2026-08-31")
        self.assertEqual(case["official_order_payment_made_date_index_excerpt"],"2026-08-31")
        self.assertEqual(case["official_order_late_payment_days_index_excerpt"],223)
        self.assertFalse(case["official_order_pdf_bytes_acquired"])
        self.assertTrue(case["official_enforcement_order_url"].startswith("https://www2.fmc.gov/readingroom/docs/26-13/"))
        self.assertIn("OFFICIAL_FMC_ORDER_SEARCH_INDEX_EXCERPT",case["reported_payment_lifecycle_source"])
        self.assertTrue(case["government_reported_late_reparation_payment"])
        self.assertIn("MEDIA_REPORTS",case["reported_payment_lifecycle_source"])
        self.assertIsNone(case["exact_customer_received_amount_cents_independently_bank_verified"])
        self.assertIsNone(case["interest_actually_received_cents_independently_verified"])
        self.assertIsNone(case["civil_penalty_assessed_cents_at_review_date"])
        self.assertFalse(case["penalty_order_finalized_at_review_date"])
        self.assertFalse(case["applicable_to_private_domestic_motor_freight_tariffs"])
        self.assertFalse(load_fixture()["original_customer_invoice_and_bank_bytes_acquired"])

    def test_hpl_invoice_is_higher_but_fmc_awarded_zero_in_initial_decision(self):
        hp=load_fixture()["hp_logistics_quote_dispute"]
        self.assertEqual(hp["initial_decision_served"],"2025-08-07")
        self.assertEqual(hp["initial_quote_cents"],4320000)
        self.assertEqual(hp["additional_parts_discussed_cents"],1100000)
        self.assertEqual(hp["claimed_revised_quote_cents"],5420000)
        self.assertEqual(hp["final_invoiced_amount_cents"],7780000)
        self.assertEqual(hp["quote_vs_invoice_difference_cents"],2360000)
        self.assertEqual(hp["additional_demurrage_detention_claim_cents"],229500)
        self.assertEqual(hp["total_reparations_sought_cents"],2589500)
        self.assertFalse(hp["initial_decision_section_41102_c_violated"])
        self.assertTrue(hp["initial_decision_BIC_40501_a_1_tariff_publication_violation"])
        self.assertFalse(hp["initial_decision_CFL_violation_found"])
        self.assertEqual(hp["initial_decision_reparations_awarded_cents"],0)
        self.assertFalse(hp["administrative_finality_separately_verified"])
        self.assertIsNone(hp["later_customer_refund_verified_cents"])
        self.assertFalse(hp[
            "independent_full_original_quote_invoice_BOL_payment_chain_in_retally_custody"])


    def test_jimex_modern_real_shipper_initial_reparations_vs_claim_amount(self):
        from freight.unified_research_lab import SEEDS
        case=load_fixture()["jimex_unitrans_initial_paid_detention"]
        self.assertEqual(set(case),set(JIMEX)|{"appendix_b_paid_invoice_rows"})
        self.assertEqual(case["initial_decision_served"],"2026-07-16")
        self.assertEqual(case["official_extension_denial_served"],"2026-07-23")
        self.assertIn(case["official_initial_decision_url"],SEEDS["freightrecovery"])
        self.assertIn(case["official_extension_denial_url"],SEEDS["freightrecovery"])
        self.assertEqual(case["initial_claim_reparations_requested_cents"],4460669)
        self.assertEqual(case["respondent_contested_unpaid_balance_claim_cents"],1113600)
        self.assertFalse(case["respondent_claimed_unpaid_balance_independently_adjudicated_due"])
        self.assertTrue(case["initial_decision_41102_c_excess_late_fee_violation"])
        self.assertTrue(case["initial_decision_41104_a15_missing_detention_invoice_information_violation"])
        self.assertTrue(case["initial_decision_541_6_minimum_contents_violation"])
        self.assertEqual(case["initial_late_fee_reparations_ordered_cents"],999707)
        self.assertEqual(case["initial_detention_refund_ordered_cents"],197500)
        self.assertEqual(case["initial_ordered_principal_cents_EXCLUDES_interest"],1197207)
        self.assertEqual(999707+197500,1197207)
        self.assertTrue(case["interest_awarded_but_exact_amount_unverified"])
        self.assertTrue(case["initial_decision_granted_in_part_and_denied_in_part"])
        self.assertFalse(case["actual_finality_notice_independently_verified"])
        self.assertIsNone(case["refund_received_by_claimant_independently_bank_verified_cents"])
        self.assertFalse(case["underlying_paid_invoice_and_bank_bytes_held_by_RETALLY"])
        self.assertFalse(case["current_customer_scoring_authorized"])

    def test_jimex_appendix_b_five_paid_invoices_have_exact_fmc_source_grain(self):
        case=load_fixture()["jimex_unitrans_initial_paid_detention"]
        values=[
            (r["invoice_number_FMC_reported"],
             r["detention_charged_paid_cents_FMC_reported"],
             r["claimant_payment_date_FMC_reported"])
            for r in case["appendix_b_paid_invoice_rows"]
        ]
        self.assertEqual(tuple(values),JIMEX_ROWS)
        self.assertEqual([x[1] for x in values],[65000,12500,37500,57500,25000])
        self.assertEqual(sum(x[1] for x in values),197500)
        self.assertEqual(case["appendix_b_claimant_paid_detention_invoice_count"],5)
        self.assertEqual(case["appendix_b_total_paid_detention_cents"],197500)
        self.assertTrue(case["unrelated_carrier_invoice_exhibits_not_linkable_to_these_five_shipments"])
        self.assertTrue(case["third_party_pass_through_original_invoices_introduced_during_proceeding"])
        receipt=make_receipt()
        self.assertEqual(receipt["jimex_initial_late_fee_reparations_cents"],999707)
        self.assertEqual(receipt["jimex_initial_detention_refund_cents"],197500)
        self.assertEqual(receipt["jimex_initial_principal_NOT_actual_cash_received_cents"],1197207)
        self.assertEqual(receipt["jimex_appendix_b_paid_invoice_count"],5)
        self.assertEqual(receipt["jimex_appendix_b_paid_detention_cents"],197500)
        self.assertTrue(receipt["jimex_unrelated_carrier_exhibits_must_not_join"])
        self.assertFalse(receipt["jimex_initial_decision_finality_verified"])
        self.assertIsNone(receipt["jimex_later_bank_cleared_refund_cents"])
        self.assertIsNone(receipt["jimex_exact_interest_cents"])
        self.assertEqual(receipt["retally_recovered_cash_cents"],0)
        self.assertFalse(receipt["jimex_current_customer_scoring_authorized"])

    def test_jimex_appendix_b_case_custody_and_payment_forgery_fails_closed(self):
        for scope,key,value in (
            ("root","official_pdf_bytes_acquired",True),
            ("jimex","initial_late_fee_reparations_ordered_cents",999708),
            ("jimex","initial_detention_refund_ordered_cents",197499),
            ("jimex","initial_claim_reparations_requested_cents",1197207),
            ("jimex","respondent_contested_unpaid_balance_claim_cents",0),
            ("jimex","respondent_claimed_unpaid_balance_independently_adjudicated_due",True),
            ("jimex","actual_finality_notice_independently_verified",True),
            ("jimex","refund_received_by_claimant_independently_bank_verified_cents",1197207),
            ("jimex","underlying_paid_invoice_and_bank_bytes_held_by_RETALLY",True),
            ("jimex","current_customer_scoring_authorized",True),
        ):
            d=deepcopy(load_fixture())
            row=d if scope=="root" else d["jimex_unitrans_initial_paid_detention"]
            row[key]=value
            with self.subTest(field=key),self.assertRaises(ResearchError):
                validate_fixture(d)
        for i,key,value in (
            (0,"detention_charged_paid_cents_FMC_reported",65001),
            (1,"invoice_number_FMC_reported","90855"),
            (3,"claimant_payment_date_FMC_reported","2025-05-15"),
            (4,"source_claims_bank_recovery",25000),
        ):
            d=deepcopy(load_fixture())
            d["jimex_unitrans_initial_paid_detention"]["appendix_b_paid_invoice_rows"][i][key]=value
            with self.subTest(i=i,key=key),self.assertRaises(ResearchError):
                validate_fixture(d)

    def test_jimex_receipt_rehash_cannot_promote_initial_order_or_customer_cash(self):
        from freight.unified_research_lab import digest
        original=make_receipt()
        changes=(
            ("jimex_initial_claim_requested_cents",1197207),
            ("jimex_initial_late_fee_reparations_cents",1197207),
            ("jimex_initial_detention_refund_cents",0),
            ("jimex_initial_principal_NOT_actual_cash_received_cents",4460669),
            ("jimex_appendix_b_paid_invoice_count",11),
            ("jimex_appendix_b_paid_detention_cents",1113600),
            ("jimex_unrelated_carrier_exhibits_must_not_join",False),
            ("jimex_initial_decision_finality_verified",True),
            ("jimex_later_bank_cleared_refund_cents",1197207),
            ("jimex_exact_interest_cents",10000),
            ("jimex_current_customer_scoring_authorized",True),
            ("retally_recovered_cash_cents",1197207),
        )
        for key,value in changes:
            d=deepcopy(original)
            d[key]=value
            d["receipt_sha256"]=digest({k:v for k,v in d.items()
                                        if k!="receipt_sha256"})
            with self.subTest(key=key),self.assertRaises(ResearchError):
                verify_receipt(d)
        serialized=json.dumps(original)
        for invoice_id in ("90855","91146","91156","91692","91289-1"):
            self.assertNotIn('"'+invoice_id+'"',serialized)

    def test_separate_outcome_states_and_current_customer_nonpromotion(self):
        receipt=make_receipt()
        self.assertEqual(len(receipt["fmc_cases"]),4)
        self.assertEqual(receipt["bridgewell_final_ordered_total_cents"],2828931)
        self.assertEqual(receipt["bridgewell_final_principal_cents"],2432880)
        self.assertEqual(receipt["bridgewell_final_interest_as_of_notice_cents"],396051)
        self.assertEqual(receipt["bridgewell_award_components_not_invoice_count"],10)
        self.assertEqual(receipt["bridgewell_reported_late_customer_payment_date"],
                         "2026-08-31")
        self.assertEqual(receipt["bridgewell_official_order_payment_made_index_excerpt_date"],"2026-08-31")
        self.assertEqual(receipt["bridgewell_official_order_late_days"],223)
        self.assertFalse(receipt["bridgewell_original_enforcement_order_pdf_in_custody"])
        self.assertFalse(receipt["bridgewell_bank_receipt_confirmed"])
        self.assertIsNone(receipt["bridgewell_actual_bank_receipt_cents"])
        self.assertEqual(receipt["bridgewell_payment_evidence_tier"],
            "OFFICIAL_FMC_ORDER_INDEX_EXCERPT_CARRIER_PAID_SECONDARY_CUSTOMER_RECEIPT_BANK_UNVERIFIED")
        self.assertTrue(receipt[
            "bridgewell_later_payment_reported_NOT_verified_bank_receipt"])
        self.assertTrue(receipt[
            "bridgewell_exact_received_cash_and_interest_unverified"])
        self.assertIsNone(receipt["bridgewell_civil_penalties_imposed_cents"])
        self.assertEqual(receipt["hpl_initial_decision_reparations_awarded_cents"],0)
        self.assertTrue(receipt["hpl_initial_decision_tariff_publication_violation"])
        self.assertFalse(receipt["hpl_initial_decision_section_41102_c_violation"])
        self.assertFalse(receipt["hpl_final_status_independently_verified"])
        self.assertFalse(receipt["original_fmc_pdf_bytes_and_private_invoices_held"])
        self.assertEqual(receipt["modern_retally_invoice_accuracy_labels"],0)
        self.assertFalse(receipt["commercial_customer_reuse_approved"])
        self.assertEqual(receipt["retally_recovered_cash_cents"],0)
        self.assertIsNone(receipt["original_official_pdf_sha256"])
        self.assertEqual(set(receipt),RECEIPT_KEYS)
        self.assertEqual(verify_receipt(receipt),receipt)

    def test_forged_government_interest_or_award_group_cannot_pass(self):
        base=load_fixture()
        for i,key,value in (
            (0,"principal_cents_each",54451),
            (0,"interest_cents_each",9116),
            (0,"multiplicity",16),
            (4,"interest_cents_each",38561),
        ):
            altered=deepcopy(base)
            altered["bridgewell_cosco"]["reparation_award_groups"][i][key]=value
            with self.subTest(group=i,field=key),self.assertRaises(ResearchError):
                validate_fixture(altered)
        extra=deepcopy(base)
        extra["bridgewell_cosco"]["reparation_award_groups"][0][
            "original_bank_transfer_verified"]=True
        with self.assertRaises(ResearchError):
            validate_fixture(extra)

    def test_self_rehashed_false_payment_or_penalty_fails_closed(self):
        original=make_receipt()
        for key,val in (
            ("bridgewell_final_principal_cents",2828931),
            ("bridgewell_final_interest_as_of_notice_cents",0),
            ("bridgewell_final_ordered_total_cents",2432880),
            ("bridgewell_reported_late_customer_payment_date","2026-01-20"),
            ("bridgewell_official_order_payment_made_index_excerpt_date","2026-01-20"),
            ("bridgewell_official_order_late_days",0),
            ("bridgewell_original_enforcement_order_pdf_in_custody",True),
            ("bridgewell_bank_receipt_confirmed",True),
            ("bridgewell_actual_bank_receipt_cents",2828931),
            ("bridgewell_payment_evidence_tier","ORIGINAL_BANK_STATEMENT_VERIFIED"),
            ("bridgewell_exact_received_cash_and_interest_unverified",False),
            ("bridgewell_civil_penalties_imposed_cents",1670000000),
            ("hpl_initial_decision_reparations_awarded_cents",2360000),
            ("hpl_initial_decision_section_41102_c_violation",True),
            ("hpl_final_status_independently_verified",True),
            ("commercial_customer_reuse_approved",True),
            ("modern_retally_invoice_accuracy_labels",13),
            ("retally_recovered_cash_cents",2828931),
            ("original_official_pdf_sha256","a"*64),
        ):
            changed=deepcopy(original)
            changed[key]=val
            changed["receipt_sha256"]=digest({k:v for k,v in changed.items()
                                              if k!="receipt_sha256"})
            with self.subTest(key=key),self.assertRaises(ResearchError):
                verify_receipt(changed)

    def test_forged_original_payment_and_tariff_scope_rejected(self):
        base=load_fixture()
        for key,value in (
            ("official_pdf_bytes_acquired",True),
            ("official_pdf_source_sha256","b"*64),
            ("original_customer_invoice_and_bank_bytes_acquired",True),
            ("source_specific_commercial_reuse_verified",True),
            ("retally_independent_customer_invoice_truth_cases",1),
            ("retally_cash_recovered_cents",2432880),
        ):
            b=deepcopy(base)
            b[key]=value
            with self.subTest(key=key),self.assertRaises(ResearchError):
                validate_fixture(b)
        for target,key,value in (
            ("bridgewell_cosco","exact_customer_received_amount_cents_independently_bank_verified",2828931),
            ("bridgewell_cosco","interest_actually_received_cents_independently_verified",396051),
            ("bridgewell_cosco","civil_penalty_assessed_cents_at_review_date",1670000000),
            ("bridgewell_cosco","government_reported_late_reparation_payment",False),
            ("bridgewell_cosco","official_order_pdf_bytes_acquired",True),
            ("bridgewell_cosco","official_order_payment_made_date_index_excerpt","2026-01-20"),
            ("bridgewell_cosco","official_order_late_payment_days_index_excerpt",0),
            ("bridgewell_cosco","reported_payment_lifecycle_source","BANK_SETTLEMENT_VERIFIED"),
            ("bridgewell_cosco","applicable_to_private_domestic_motor_freight_tariffs",True),
            ("hp_logistics_quote_dispute","administrative_finality_separately_verified",True),
            ("hp_logistics_quote_dispute","later_customer_refund_verified_cents",2589500),
        ):
            changed=deepcopy(base)
            changed[target][key]=value
            with self.subTest(target=target,key=key),self.assertRaises(ResearchError):
                validate_fixture(changed)

    def test_receipt_roundtrip_does_not_include_external_customer_bank_data(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"source_bound_FMC_receipt.json"
            doc=make_receipt()
            p.write_text(json.dumps(doc,sort_keys=True),encoding="utf-8")
            content=p.read_text()
            for forbidden in ("ORIGINAL_BANK_TRANSFER_ID","CUSTOMER_BANK_ACCOUNT",
                              "BEAU6225110","CSNU8330251","HLBU8181527"):
                self.assertNotIn(forbidden,content)
            self.assertEqual(verify_receipt(json.loads(content)),doc)

    def test_native_rating_engine_still_refuses_third_party_fmc_claim(self):
        case=load_fixture()["bridgewell_cosco"]
        sha=sha256(b"SYNTHETIC_NO_ORIGINAL_FMC_EVIDENCE").hexdigest()
        record=build_record(
            buyer_id="SYNTHETIC_TEST",business_unit="SYNTHETIC_BUSINESS",
            invoice_id="SYNTHETIC_NOT_FMC_CUSTOMER",invoice_date="2026-10-26",
            customer_id="SYNTHETIC_TEST",currency="USD",
            shipment=ShipmentFacts(
                shipment_id="SYNTHETIC_SHIPMENT",
                carrier_id="SYNTHETIC_CARRIER",mode="LTL",service_date="2026-10-26",
                origin_postal="SYN_ORIGIN",destination_postal="SYN_DEST",
                actual_weight_grams=1000,package_count=1),
            charges=(ChargeLine("SYNTHETIC_DEMURRAGE","ACCESSORIAL",
                                case["reparations_principal_cents"]),),
            sources=(SourceArtifact("SYNTHETIC_ONLY",
                "NOT_A_REAL_SHIPPER_INVOICE",sha,
                "2026-10-26T00:00:00.000000Z","BATCH"),),
        )
        book=AuthorityBook(())
        r=rate_record(record,book)
        ev=review_freight_rate(record,book)
        self.assertEqual(r.status,REVIEW_REQUIRED)
        self.assertIsNone(r.expected_total_cents)
        self.assertIsNone(r.variance_cents)
        self.assertFalse(r.authority_verified)
        self.assertEqual(ev.status,"REVIEW_REQUIRED")
        self.assertFalse(ev.independent_accuracy_scored)
        self.assertIsNone(ev.externally_verified_freight_error_cents)
        self.assertEqual(ev.externally_verified_cash_recovered_cents,0)


if __name__=="__main__":
    unittest.main()
