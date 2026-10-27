"""Adversarial tests of third-party historical freight-billing adjudications."""
from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path

from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.priority2_evidence import review_freight_rate
from freight.gao_adjudicated_billing_cases import (
    EvidenceError, LABEL_NEG, LABEL_POS, PINNED,
    canonical_digest, load_fixture, make_receipt, validate_fixture,
    verify_receipt,
)


class IndependentlyAdjudicatedHistoricalBillingTests(unittest.TestCase):
    def test_official_gao_decision_population_and_money(self):
        fixture = load_fixture()
        self.assertEqual(len(fixture["cases"]), 7)
        self.assertEqual([r["id"] for r in fixture["cases"]], list(PINNED))
        receipt = make_receipt()
        self.assertEqual(receipt["external_gao_adjudicated_historical_cases"], 7)
        self.assertEqual(receipt["sustained_overcharges_historical_cents"], 426699)
        self.assertEqual(receipt["invalid_government_deductions_historical_cents"], 25405)
        self.assertEqual(receipt["historical_agency_deductions_total_cents_not_retally_cash"], 452104)
        self.assertEqual([r["historical_label"] for r in receipt["case_outcomes"]],
                         [LABEL_POS, LABEL_POS, LABEL_POS, LABEL_POS, LABEL_POS, LABEL_NEG, LABEL_NEG])
        self.assertEqual(receipt["retally_recovered_cash_cents"], 0)
        self.assertEqual(receipt["private_customer_benchmark_truth_cases"], 0)
        self.assertEqual(receipt["source_original_invoice_rate_bank_chain_verified_cases"], 0)
        self.assertFalse(receipt["production_rating_or_dispute_allowed"])
        self.assertFalse(receipt["commercial_reuse_approved"])
        self.assertIsNone(receipt["source_original_gao_response_sha256"])
        verify_receipt(receipt)

    def test_two_additional_official_decisions_preserve_source_and_unknown_custody(self):
        from freight.test_gao_b189100_classification import (
            fixture as b189100, verify as verify_b189100,
        )
        from freight.unified_research_lab import SEEDS
        rows={row["id"]: row for row in load_fixture()["cases"]}
        classified=verify_b189100(b189100())["facts"]
        a=rows["B-189100"]
        self.assertEqual(a["reported_billed_and_paid_cents"],
                         classified["billed_charges_cents"])
        self.assertEqual(a["reported_gsa_deducted_cents"],
                         classified["gao_overcharge_deduction_cents"])
        self.assertEqual(a["reported_gsa_audited_cents"], 93280)
        self.assertEqual(a["money_calculation"], "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION")
        self.assertIsNone(a["reported_gbl_date"])
        b=rows["B-213717"]
        self.assertEqual((b["reported_billed_and_paid_cents"],
                          b["reported_gsa_audited_cents"],
                          b["reported_gsa_deducted_cents"]),
                         (121209,68678,52531))
        self.assertIsNone(b["reported_gbl"])
        self.assertIsNone(b["reported_gbl_date"])
        self.assertIsNone(b["reported_weight_lb"])
        self.assertIn(b["source_url"], SEEDS["freightrecovery"])
        self.assertEqual(b["ga_review_outcome"],
                         "GSA_CLASSIFICATION_DEDUCTION_SUSTAINED")
        receipt=make_receipt()
        labels={x["id"]:x for x in receipt["case_outcomes"]}
        self.assertTrue(labels["B-189100"]["amount_derived_from_gao_arithmetic"])
        self.assertFalse(labels["B-213717"]["amount_derived_from_gao_arithmetic"])
        self.assertEqual(receipt["private_customer_benchmark_truth_cases"],0)
        self.assertEqual(receipt["retally_recovered_cash_cents"],0)

    def test_original_gao_b192856_physical_sample_confirms_cargo_not_bol_assumption(self):
        """External adjudicator examined cargo, not an original invoice in our custody."""
        from freight.unified_research_lab import SEEDS
        rows={r["id"]:r for r in load_fixture()["cases"]}
        row=rows["B-192856"]
        self.assertEqual(row["decision_date"], "1979-03-15")
        self.assertEqual(row["reported_gbl"], "P-7343114")
        self.assertEqual(row["reported_weight_lb"], 2040)
        self.assertIsNone(row["reported_gbl_date"])
        self.assertEqual(Decimal("13.6")*60/16,Decimal("51"))
        self.assertEqual(40*51,row["reported_weight_lb"])
        audited=(Decimal("7.77")*Decimal("20.4")).quantize(
            Decimal("0.01"),rounding=ROUND_HALF_UP)
        self.assertEqual(audited,Decimal("158.51"))
        self.assertEqual(109793-93942,15851)
        self.assertEqual(row["reported_gsa_deducted_cents"],93942)
        self.assertEqual(row["reported_gsa_audited_cents"],15851)
        self.assertEqual(row["ga_review_outcome"],
                         "GSA_PHYSICAL_SAMPLE_CLASSIFICATION_DEDUCTION_SUSTAINED")
        self.assertEqual(row["money_calculation"],
                         "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION")
        self.assertIn("13.6-ounce",row["source_money_note"])
        self.assertIn(row["source_url"],SEEDS["freightrecovery"])
        self.assertFalse(load_fixture()["independent_original_invoice_and_bank_custody"])
        self.assertEqual(make_receipt()["private_customer_benchmark_truth_cases"],0)

    def test_original_gao_b191258_capacity_rule_reverses_false_setoff_not_cash_refund(self):
        """A full trailer's tariff minimum is NOT an actual-weight arbitrary rate."""
        from freight.unified_research_lab import SEEDS
        rows={r["id"]:r for r in load_fixture()["cases"]}
        row=rows["B-191258"]
        self.assertEqual(row["decision_date"],"1978-07-07")
        self.assertIsNone(row["reported_gbl"])  # Source OCR is ambiguous.
        self.assertEqual(row["reported_weight_lb"],6910)
        arbitrated=(Decimal("0.30")*(Decimal(24000)/100)).quantize(
            Decimal("0.01"),rounding=ROUND_HALF_UP)
        gsa=(Decimal("0.56")*(Decimal(6910)/100)).quantize(
            Decimal("0.01"),rounding=ROUND_HALF_UP)
        self.assertEqual(arbitrated,Decimal("72.00"))
        self.assertEqual(gsa,Decimal("38.70"))
        self.assertEqual(arbitrated-gsa,Decimal("33.30"))
        self.assertEqual((row["reported_billed_and_paid_cents"],
                          row["reported_gsa_audited_cents"],
                          row["reported_gsa_deducted_cents"]),(149760,146430,3330))
        self.assertEqual(row["adjudicated_historical_label"],LABEL_NEG)
        self.assertEqual(row["ga_review_outcome"],
                         "GSA_DEDUCTION_INVALID_TRUCKLOAD_MINIMUM_WEIGHT_RULE")
        self.assertIn("not proof of a paid refund",row["source_money_note"])
        self.assertIn(row["source_url"],SEEDS["freightrecovery"])
        self.assertEqual(load_fixture()["verified_retally_cash_cents"],0)
        labels={v["id"]:v for v in make_receipt()["case_outcomes"]}
        self.assertEqual(labels["B-191258"]["historical_label"],LABEL_NEG)
        self.assertTrue(labels["B-191258"]["amount_derived_from_gao_arithmetic"])
        self.assertEqual(make_receipt()["retally_recovered_cash_cents"],0)

    def test_unverified_source_notes_cannot_gain_authority_through_rehash(self):
        for index in range(len(load_fixture()["cases"])):
            altered=copy.deepcopy(load_fixture())
            altered["cases"][index]["source_money_note"]+=(
                " Independent customer bank refund and current tariff verified.")
            with self.subTest(index=index), self.assertRaises(EvidenceError):
                validate_fixture(altered)

    def test_negative_rejected_tender_never_becomes_positive_from_arithmetic(self):
        data = load_fixture()
        bad = next(row for row in data["cases"] if row["id"] == "B-221594")
        self.assertEqual(bad["reported_billed_and_paid_cents"], 94200)
        self.assertEqual(bad["reported_gsa_audited_cents"], 72125)
        self.assertEqual(bad["reported_gsa_deducted_cents"], 22075)
        self.assertEqual(bad["adjudicated_historical_label"], LABEL_NEG)
        self.assertEqual(bad["money_calculation"], "DERIVED_FROM_GAO_PAID_MINUS_DEDUCTION")
        self.assertIn("OCR", bad["source_money_note"])
        self.assertIsNone(bad["reported_gbl"])

    def test_positive_agency_collections_are_not_retally_revenue(self):
        for row in load_fixture()["cases"][:5]:
            with self.subTest(case=row["id"]):
                self.assertEqual(row["reported_billed_and_paid_cents"]
                                 - row["reported_gsa_audited_cents"],
                                 row["reported_gsa_deducted_cents"])
                self.assertEqual(row["adjudicated_historical_label"], LABEL_POS)
        self.assertFalse(load_fixture()["historical_government_deductions_are_retally_cash"])

    def test_rehashed_changed_money_disposition_source_and_claims_fail_closed(self):
        base = load_fixture()
        replacements = [
            ("cases", 0, "reported_billed_and_paid_cents", 82801),
            ("cases", 1, "reported_gsa_audited_cents", 13928),
            ("cases", 5, "reported_gsa_deducted_cents", 22074),
            ("cases", 5, "adjudicated_historical_label", LABEL_POS),
            ("cases", 5, "ga_review_outcome", "GSA_OVERCHARGE_DEDUCTION_SUSTAINED"),
            ("cases", 5, "money_calculation", "PUBLISHER_EXPLICIT"),
            ("cases", 0, "source_url", "https://www.gao.gov/products/b-999999"),
        ]
        for _, index, key, new in replacements:
            with self.subTest(index=index, key=key):
                forged = copy.deepcopy(base)
                forged["cases"][index][key] = new
                self.assertNotEqual(canonical_digest(forged),canonical_digest(base))
                with self.assertRaises(EvidenceError):
                    validate_fixture(forged)
        for key, value in (
            ("historical_government_deductions_are_retally_cash", True),
            ("independent_original_invoice_and_bank_custody", True),
            ("independent_current_customer_invoice_accuracy_cases", 1),
            ("verified_retally_cash_cents", 3200),
            ("production_rate_or_dispute_actions_allowed", True),
            ("rights_clearance_for_current_customer_engine", True),
        ):
            with self.subTest(key=key):
                forged = copy.deepcopy(base)
                forged[key] = value
                with self.assertRaises(EvidenceError):
                    validate_fixture(forged)

    def test_original_source_sha_and_custody_cannot_be_fabricated(self):
        base=load_fixture()
        for field, value in (
            ("original_gao_response_bytes_sha256","0"*64),
            ("original_invoice_gbl_tariff_bytes_in_custody",True),
            ("source_link_is_original_transaction_document",True),
            ("commercial_customer_use_rights_verified",True),
        ):
            with self.subTest(field=field):
                altered=copy.deepcopy(base)
                altered["source_common"][field]=value
                with self.assertRaises(EvidenceError):
                    validate_fixture(altered)

    def test_extra_nested_fabricated_claims_and_amount_types_rejected(self):
        for mutation in (
            lambda d: d["cases"][0].update({"real_customer_recovered_cents":3200}),
            lambda d: d["cases"][1].update({"reported_gsa_deducted_cents":13588.0}),
            lambda d: d["cases"][1].update({"reported_gsa_deducted_cents":True}),
            lambda d: d["cases"].append(copy.deepcopy(d["cases"][0])),
            lambda d: d["cases"].reverse(),
            lambda d: d["source_common"].update({"provider_payment_confirmed":True}),
        ):
            altered=copy.deepcopy(load_fixture())
            mutation(altered)
            with self.assertRaises(EvidenceError):
                validate_fixture(altered)

    def test_both_provenance_and_receipt_cannot_be_rehashed_into_authority(self):
        original=make_receipt()
        for key,val in (
            ("private_customer_benchmark_truth_cases",1),
            ("retally_recovered_cash_cents",3200),
            ("commercial_reuse_approved",True),
            ("external_gao_adjudicated_historical_cases",6),
            ("sustained_overcharges_historical_cents",452104),
        ):
            with self.subTest(key=key):
                forged=copy.deepcopy(original)
                forged[key]=val
                forged["receipt_sha256"]=canonical_digest({
                    k:v for k,v in forged.items() if k!="receipt_sha256"})
                with self.assertRaises(EvidenceError):
                    verify_receipt(forged)

    def test_no_unexpected_fixture_fields_or_missing_source_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            altered=copy.deepcopy(load_fixture())
            altered["cases"][0].pop("rate_authority")
            path=Path(folder)/"altered.json"
            path.write_text(json.dumps(altered))
            with self.assertRaises(EvidenceError):
                load_fixture(path)
            with self.assertRaises(EvidenceError):
                load_fixture(Path(folder)/"missing.json")

    def test_actual_rating_and_evidence_engines_refuse_historical_price_promotion(self):
        # All transaction identifiers, shipments, and byte hashes below are
        # fabricated for the test. GAO money facts are NEVER a customer invoice.
        for i, row in enumerate(load_fixture()["cases"]):
            with self.subTest(case=row["id"]):
                fake_sha=sha256(("FABRICATED-GAO-REVIEW-"+row["id"]).encode()).hexdigest()
                record=build_record(
                    buyer_id="SYNTHETIC-BUYER",
                    business_unit="SYNTHETIC-GAO-TEST-ONLY",
                    invoice_id="SYNTHETIC-CASE-"+str(i),
                    invoice_date="2026-10-26",
                    customer_id="SYNTHETIC-BUYER",
                    currency="USD",
                    shipment=ShipmentFacts(
                        shipment_id="SYNTHETIC-GAO-SHIPMENT-"+str(i),
                        carrier_id="SYNTHETIC-CARRIER",
                        mode="LTL", service_date="2026-10-26",
                        origin_postal="SYN-ORIGIN", destination_postal="SYN-DESTINATION",
                        actual_weight_grams=1000, package_count=1,
                    ),
                    charges=(ChargeLine("SYN-LINEHAUL","TRANSPORTATION",
                                        row["reported_billed_and_paid_cents"]),),
                    sources=(SourceArtifact(
                        "SYNTHETIC-NOT-ORIGINAL", "NOT_AN_ORIGINAL_INVOICE",
                        fake_sha, "2026-10-26T00:00:00.000000Z", "BATCH"),),
                )
                no_current_contract=AuthorityBook(())
                rated=rate_record(record,no_current_contract)
                strict=review_freight_rate(record,no_current_contract)
                self.assertEqual(rated.status,REVIEW_REQUIRED)
                self.assertIsNone(rated.expected_total_cents)
                self.assertIsNone(rated.variance_cents)
                self.assertFalse(rated.authority_verified)
                self.assertEqual(strict.status,"REVIEW_REQUIRED")
                self.assertFalse(strict.independent_accuracy_scored)
                self.assertIsNone(strict.externally_verified_freight_error_cents)
                self.assertEqual(strict.externally_verified_cash_recovered_cents,0)
                self.assertIn("BANK_CLEARED_PAYMENT_NOT_INDEPENDENTLY_VERIFIED",strict.blockers)

    def test_receipt_is_deterministic_and_authored_hash_is_not_source_hash(self):
        a=make_receipt()
        self.assertEqual(a,make_receipt())
        self.assertEqual(a["fixture_authored_sha256"],canonical_digest(load_fixture()))
        self.assertEqual(a["receipt_sha256"],canonical_digest({
            k:v for k,v in a.items() if k!="receipt_sha256"}))
        self.assertFalse(load_fixture()["rights_clearance_for_current_customer_engine"])


if __name__=="__main__":
    unittest.main()
