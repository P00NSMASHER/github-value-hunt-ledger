"""Isolated, synthetic-only tests for cross-shipment invoice-reference REVIEW.

A duplicate invoice reference is not proof of duplicate service or payment.
No real buyers, carrier records, amounts recovered, or external actions.
"""
import unittest
from dataclasses import replace

from freight.contracts import PopulationRow, freeze_population
from freight.duplicate_charge_review import (
    INVOICE_REFERENCE_EVIDENCE,
    POSSIBLE_CROSS_SHIPMENT_INVOICE_REFERENCE,
    REVIEW,
    review_duplicate_charges,
    review_reused_invoice_references,
)
from freight.finding_factory import InvoiceCharge


def make_charge(**changes):
    data = dict(
        buyer_id="synthetic-buyer", business_unit="test-unit",
        invoice_id="INV-5", shipment_id="LOAD-1",
        customer_id="fictional-customer", carrier_id="fictional-carrier",
        currency="USD", charge_id="CH-1", charge_code="LINEHAUL",
        service_date="2026-09-10", quantity_units=1,
        billed_cents=100_000, source_hash="synthetic-doc-hash-1",
    )
    data.update(changes)
    return InvoiceCharge(**data)


def make_population(*rows):
    rows = rows or (
        PopulationRow("INV-5", "LOAD-1", "fictional-customer", "fictional-carrier", "USD", "source-1"),
        PopulationRow("INV-5", "LOAD-2", "fictional-customer", "fictional-carrier", "USD", "source-2"),
    )
    return freeze_population("synthetic-buyer", "test-unit", "SYNTHETIC", rows)


def second(**changes):
    overrides = dict(
        shipment_id="LOAD-2",
        charge_id="CH-2",
        source_hash="synthetic-doc-hash-2",
    )
    overrides.update(changes)
    return make_charge(**overrides)


class InvoiceReferenceReviewTests(unittest.TestCase):
    def test_cross_shipment_same_carrier_invoice_is_review_only_and_zero_dollars(self):
        out = review_reused_invoice_references(make_population(), (make_charge(), second()))
        self.assertEqual(out.review_count, 1)
        [item] = out.candidates
        self.assertEqual(item.decision, REVIEW)
        self.assertEqual(item.reason, POSSIBLE_CROSS_SHIPMENT_INVOICE_REFERENCE)
        self.assertEqual(item.shipment_ids, ("LOAD-1", "LOAD-2"))
        self.assertEqual(item.invoice_id, "INV-5")
        self.assertEqual(item.charge_ids, ("CH-1", "CH-2"))
        self.assertEqual(item.source_hashes, ("synthetic-doc-hash-1", "synthetic-doc-hash-2"))
        self.assertEqual(item.validated_cents, 0)
        self.assertEqual(out.validated_cents, 0)
        self.assertTrue(item.requires_human_review)
        self.assertFalse(item.may_assert_validated_dollars)
        self.assertEqual(item.unresolved_evidence, INVOICE_REFERENCE_EVIDENCE)
        self.assertIn("MULTI_LOAD_INVOICE_AUTHORIZATION", item.unresolved_evidence)
        self.assertEqual(item.candidate_id, "invoice-ref:" + item.proof_hash)

    def test_same_reference_two_lines_same_shipment_is_not_cross_shipment(self):
        pop = make_population(PopulationRow(
            "INV-5", "LOAD-1", "fictional-customer", "fictional-carrier", "USD", "source-1"
        ))
        more = make_charge(charge_id="CH-2", source_hash="synthetic-doc-hash-2")
        self.assertEqual(
            review_reused_invoice_references(pop, (make_charge(), more)).review_count,
            0,
        )

    def test_distinct_reference_numbers_are_not_flagged(self):
        pop = make_population(
            PopulationRow("INV-5", "LOAD-1", "fictional-customer", "fictional-carrier", "USD", "source-1"),
            PopulationRow("INV-6", "LOAD-2", "fictional-customer", "fictional-carrier", "USD", "source-2"),
        )
        self.assertEqual(
            review_reused_invoice_references(
                pop, (make_charge(), second(invoice_id="INV-6"))
            ).review_count, 0,
        )

    def test_independent_customer_and_carrier_scope_is_never_mixed(self):
        pop = make_population(
            PopulationRow("INV-5", "LOAD-1", "fictional-customer", "fictional-carrier", "USD", "source-1"),
            PopulationRow("INV-5", "LOAD-2", "different-customer", "fictional-carrier", "USD", "source-2"),
            PopulationRow("INV-5", "LOAD-3", "fictional-customer", "different-carrier", "USD", "source-3"),
        )
        rows = (
            make_charge(),
            second(customer_id="different-customer"),
            make_charge(
                shipment_id="LOAD-3", carrier_id="different-carrier",
                charge_id="CH-3", source_hash="synthetic-doc-hash-3",
            ),
        )
        self.assertEqual(review_reused_invoice_references(pop, rows).candidates, ())

    def test_currency_difference_is_not_evidence_of_duplicate_identity(self):
        pop = make_population(
            PopulationRow("INV-5", "LOAD-1", "fictional-customer", "fictional-carrier", "USD", "source-1"),
            PopulationRow("INV-5", "LOAD-2", "fictional-customer", "fictional-carrier", "EUR", "source-2"),
        )
        self.assertEqual(
            review_reused_invoice_references(
                pop, (make_charge(), second(currency="EUR"))
            ).review_count, 0,
        )

    def test_grouping_preserves_three_shipments_without_monetary_aggregation(self):
        pop = make_population(*(
            PopulationRow("INV-5", f"LOAD-{i}", "fictional-customer", "fictional-carrier", "USD", f"source-{i}")
            for i in (1, 2, 3)
        ))
        rows = tuple(
            make_charge(
                shipment_id=f"LOAD-{i}", charge_id=f"CH-{i}",
                source_hash=f"synthetic-doc-hash-{i}", billed_cents=100_000 * i,
            ) for i in (1, 2, 3)
        )
        out = review_reused_invoice_references(pop, rows)
        self.assertEqual(out.review_count, 1)
        self.assertEqual(out.candidates[0].shipment_ids, ("LOAD-1", "LOAD-2", "LOAD-3"))
        self.assertEqual(out.validated_cents, 0)
        self.assertFalse(hasattr(out.candidates[0], "candidate_excess_cents"))
        self.assertFalse(hasattr(out.candidates[0], "payment_hold_authorized"))

    def test_input_order_is_idempotent_and_source_changes_change_proof(self):
        a, b = make_charge(), second()
        pop = make_population()
        forward = review_reused_invoice_references(pop, (a, b))
        reverse = review_reused_invoice_references(pop, (b, a))
        changed = review_reused_invoice_references(
            pop, (a, replace(b, source_hash="tampered-blob-source"))
        )
        self.assertEqual(forward, reverse)
        self.assertNotEqual(forward.batch_hash, changed.batch_hash)
        self.assertNotEqual(forward.candidates[0].proof_hash, changed.candidates[0].proof_hash)

    def test_invalid_source_identity_and_scope_fail_closed(self):
        pop = make_population()
        for bad, diagnostic in [
            (second(charge_id="CH-1"), "duplicate charge_id"),
            (second(buyer_id="other"), "scope mismatch"),
            (second(invoice_id="INV-OTHER"), "outside frozen population"),
            (second(carrier_id="wrong"), "identity mismatch"),
        ]:
            with self.subTest(bad=diagnostic), self.assertRaisesRegex(ValueError, diagnostic):
                review_reused_invoice_references(pop, (make_charge(), bad))

    def test_bad_numeric_and_service_date_types_fail_closed(self):
        pop = make_population()
        for bad, diagnostic in [
            (second(billed_cents=True), "billed_cents"),
            (second(quantity_units=0), "quantity_units"),
            (second(service_date="09/10/2026"), "service_date"),
        ]:
            with self.subTest(bad=diagnostic), self.assertRaisesRegex(ValueError, diagnostic):
                review_reused_invoice_references(pop, (make_charge(), bad))

    def test_human_multi_load_invoices_must_not_be_called_recoveries(self):
        out = review_reused_invoice_references(make_population(), (make_charge(), second()))
        case = out.candidates[0]
        self.assertEqual(case.decision, "REVIEW")
        self.assertIn("CREDIT_REBILL_STATUS", case.unresolved_evidence)
        self.assertIn("INVOICE_LINEAGE", case.unresolved_evidence)
        self.assertIn("PAYMENT_STATUS", case.unresolved_evidence)
        self.assertFalse(case.may_assert_validated_dollars)
        self.assertEqual(case.validated_cents, 0)
        self.assertNotIn("recovered_cents", case.__dict__)
        self.assertNotIn("fee_eligible_cents", case.__dict__)

    def test_existing_line_level_duplicate_review_remains_independent(self):
        pop = make_population()
        rows = (make_charge(), second())
        old = review_duplicate_charges(pop, rows)
        new = review_reused_invoice_references(pop, rows)
        self.assertEqual(old.review_count, 0)
        self.assertEqual(new.review_count, 1)
        self.assertEqual(old.validated_cents, 0)
        self.assertEqual(new.validated_cents, 0)


if __name__ == "__main__":
    unittest.main()
