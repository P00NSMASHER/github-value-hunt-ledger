import unittest
from dataclasses import replace

from freight.contracts import PopulationRow, freeze_population
from freight.duplicate_charge_review import (
    POSSIBLE_DUPLICATE_LINE_ITEM,
    POSSIBLE_ECONOMIC_DUPLICATE,
    REVIEW,
    review_duplicate_charges,
)
from freight.finding_factory import InvoiceCharge


def charge(**overrides):
    values = dict(
        buyer_id="buyer", business_unit="unit", invoice_id="inv-1",
        shipment_id="shp-1", customer_id="customer", carrier_id="carrier",
        currency="USD", charge_id="charge-1", charge_code="DETENTION",
        service_date="2026-09-10", quantity_units=1, billed_cents=12500,
        source_hash="source-1",
    )
    values.update(overrides)
    return InvoiceCharge(**values)


def population(*rows):
    return freeze_population(
        "buyer", "unit", "synthetic",
        rows or (
            PopulationRow("inv-1", "shp-1", "customer", "carrier", "USD", "row-1"),
            PopulationRow("inv-2", "shp-1", "customer", "carrier", "USD", "row-2"),
        ),
    )


class DuplicateChargeReviewTests(unittest.TestCase):
    def test_cross_invoice_match_is_review_only_and_content_addressed(self):
        charges = (
            charge(),
            charge(invoice_id="inv-2", charge_id="charge-2", source_hash="source-2"),
        )
        out = review_duplicate_charges(population(), charges)
        candidate = out.candidates[0]

        self.assertEqual(candidate.decision, REVIEW)
        self.assertEqual(candidate.reason, POSSIBLE_ECONOMIC_DUPLICATE)
        self.assertEqual(candidate.candidate_excess_cents, 12500)
        self.assertEqual(candidate.validated_cents, 0)
        self.assertEqual(out.validated_cents, 0)
        self.assertFalse(candidate.may_assert_validated_dollars)
        self.assertTrue(candidate.requires_human_review)
        self.assertEqual(candidate.candidate_id, "dup:" + candidate.proof_hash)
        self.assertEqual(candidate.invoice_ids, ("inv-1", "inv-2"))
        self.assertIn("CREDIT_REBILL_STATUS", candidate.unresolved_evidence)

    def test_same_invoice_repeated_line_is_distinguished_but_still_review_only(self):
        out = review_duplicate_charges(
            population(PopulationRow("inv-1", "shp-1", "customer", "carrier", "USD", "row-1")),
            (charge(), charge(charge_id="charge-2", source_hash="source-2")),
        )
        self.assertEqual(out.candidates[0].reason, POSSIBLE_DUPLICATE_LINE_ITEM)
        self.assertEqual(out.candidates[0].validated_cents, 0)

    def test_three_matching_lines_rank_only_the_repeated_exposure(self):
        pop = population(
            PopulationRow("inv-1", "shp-1", "customer", "carrier", "USD", "row-1"),
            PopulationRow("inv-2", "shp-1", "customer", "carrier", "USD", "row-2"),
            PopulationRow("inv-3", "shp-1", "customer", "carrier", "USD", "row-3"),
        )
        charges = tuple(
            charge(invoice_id=f"inv-{index}", charge_id=f"charge-{index}", source_hash=f"source-{index}")
            for index in (1, 2, 3)
        )
        out = review_duplicate_charges(pop, charges)
        self.assertEqual(out.candidate_excess_cents, 25000)

    def test_near_matches_do_not_become_candidates(self):
        pop = population(
            PopulationRow("inv-1", "shp-1", "customer", "carrier", "USD", "row-1"),
            PopulationRow("inv-2", "shp-1", "customer", "carrier", "USD", "row-2"),
            PopulationRow("inv-3", "shp-1", "customer", "carrier", "USD", "row-3"),
            PopulationRow("inv-4", "shp-1", "customer", "carrier", "USD", "row-4"),
        )
        charges = (
            charge(),
            charge(invoice_id="inv-2", charge_id="charge-2", billed_cents=12501, source_hash="source-2"),
            charge(invoice_id="inv-3", charge_id="charge-3", quantity_units=2, source_hash="source-3"),
            charge(invoice_id="inv-4", charge_id="charge-4", charge_code="LAYOVER", source_hash="source-4"),
        )
        self.assertEqual(review_duplicate_charges(pop, charges).candidates, ())

    def test_input_order_is_deterministic_and_evidence_change_changes_proof(self):
        a = charge()
        b = charge(invoice_id="inv-2", charge_id="charge-2", source_hash="source-2")
        forward = review_duplicate_charges(population(), (a, b))
        reverse = review_duplicate_charges(population(), (b, a))
        changed = review_duplicate_charges(population(), (a, replace(b, source_hash="changed")))
        self.assertEqual(forward, reverse)
        self.assertNotEqual(forward.candidates[0].proof_hash, changed.candidates[0].proof_hash)
        self.assertNotEqual(forward.batch_hash, changed.batch_hash)

    def test_duplicate_ids_and_population_boundary_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate charge_id"):
            review_duplicate_charges(population(), (charge(), charge(invoice_id="inv-2")))
        with self.assertRaisesRegex(ValueError, "scope mismatch"):
            review_duplicate_charges(population(), (charge(buyer_id="other"),))
        with self.assertRaisesRegex(ValueError, "outside frozen population"):
            review_duplicate_charges(population(), (charge(invoice_id="unknown"),))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            review_duplicate_charges(population(), (charge(carrier_id="other"),))

    def test_invalid_numeric_and_date_types_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "billed_cents"):
            review_duplicate_charges(population(), (charge(billed_cents=True),))
        with self.assertRaisesRegex(ValueError, "quantity_units"):
            review_duplicate_charges(population(), (charge(quantity_units=0),))
        with self.assertRaisesRegex(ValueError, "service_date"):
            review_duplicate_charges(population(), (charge(service_date="09/10/2026"),))


if __name__ == "__main__":
    unittest.main()
