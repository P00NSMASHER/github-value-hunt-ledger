"""Synthetic-only Brain-to-RETALLY reviewer integration; no customer outcomes."""
import unittest
from dataclasses import asdict, replace

from freight import reviewer_cockpit as cockpit
from freight.contracts import PopulationRow, canonical_hash, freeze_population
from freight.finding_factory import InvoiceCharge
from freight.duplicate_charge_review import review_duplicate_charges


def charge(**changes):
    values = dict(buyer_id="synthetic-buyer", business_unit="test-unit",
                  invoice_id="INV-1", shipment_id="LOAD-1", customer_id="fictional-customer",
                  carrier_id="fictional-carrier", currency="USD", charge_id="C1",
                  charge_code="LINEHAUL", service_date="2026-09-10", quantity_units=1,
                  billed_cents=100000, source_hash="synthetic-source-1")
    values.update(changes)
    return InvoiceCharge(**values)


def population(charges):
    rows = {}
    for item in charges:
        row = PopulationRow(item.invoice_id, item.shipment_id, item.customer_id,
                            item.carrier_id, item.currency, item.source_hash)
        rows.setdefault(row.row_key, row)
    return freeze_population("synthetic-buyer", "test-unit", "SYNTHETIC_ONLY", tuple(rows.values()))


class BrainReviewCockpitTests(unittest.TestCase):
    def queue(self, charges):
        fn = getattr(cockpit, "build_invoice_review_queue", None)
        self.assertTrue(callable(fn), "missing invoice-review integration in existing cockpit")
        return fn(population(charges), iter(charges))

    def test_cross_shipment_lead_reaches_existing_cockpit(self):
        rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2"))
        self.assertEqual(review_duplicate_charges(population(rows), rows).review_count, 0)
        result = self.queue(rows)
        self.assertEqual(len(result.items), 1)
        self.assertIsInstance(result, cockpit.ReviewQueue)
        self.assertTrue(result.items[0].case_id.startswith("invoice-ref:"))

    def test_original_line_level_review_is_preserved(self):
        rows = (charge(), charge(charge_id="C2"))
        old = review_duplicate_charges(population(rows), rows)
        result = self.queue(rows)
        self.assertEqual([x.case_id for x in result.items], [x.candidate_id for x in old.candidates])
        self.assertEqual(result.items[0].record_hash, old.candidates[0].proof_hash)

    def test_no_money_or_invented_confidence(self):
        rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2"))
        item = self.queue(rows).items[0]
        self.assertEqual((item.amount_cents, item.confidence_ppm, item.novelty_ppm,
                          item.downstream_risk_ppm), (0, 0, 0, 0))
        self.assertIn("UNSCORED_REVIEW_ONLY", item.blocker_codes)
        self.assertIn("NO_FINANCIAL_AUTHORITY", item.blocker_codes)
        self.assertIn("MULTI_LOAD_INVOICE_AUTHORIZATION", item.blocker_codes)

    def test_source_and_population_evidence_follow_the_case(self):
        rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2", source_hash="synthetic-source-2"))
        item = self.queue(rows).items[0]
        self.assertIn(population(rows).manifest_hash, item.evidence_hashes)
        self.assertIn("synthetic-source-1", item.evidence_hashes)
        self.assertIn("synthetic-source-2", item.evidence_hashes)
        for charge_row in rows:
            self.assertIn(
                canonical_hash({"schema": 1, **asdict(charge_row)}),
                item.evidence_hashes,
            )
        self.assertIn(item.record_hash, item.evidence_hashes)

    def test_same_charge_in_two_lead_classes_is_not_double_counted_as_money(self):
        rows = (charge(), charge(charge_id="C2"), charge(charge_id="C3", shipment_id="LOAD-2"))
        items = self.queue(rows).items
        self.assertEqual(len(items), 2)
        self.assertEqual(sum(x.amount_cents for x in items), 0)
        self.assertEqual(len({x.case_id for x in items}), 2)

    def test_scope_and_near_matches_do_not_mix(self):
        for field, value in (("invoice_id", "INV-2"), ("customer_id", "other-customer"),
                             ("carrier_id", "other-carrier"), ("currency", "EUR")):
            with self.subTest(field=field):
                rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2", **{field: value}))
                self.assertEqual(len(self.queue(rows).items), 0)

    def test_invalid_buyer_scope_and_duplicate_ids_fail_closed(self):
        for second in (charge(charge_id="C2", shipment_id="LOAD-2", buyer_id="other-buyer"),
                       charge(shipment_id="LOAD-2")):
            with self.assertRaises(ValueError):
                self.queue((charge(), second))

    def test_order_stability_and_changed_source_proof(self):
        rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2"))
        self.assertEqual(self.queue(rows), self.queue(tuple(reversed(rows))))
        changed = (rows[0], replace(rows[1], source_hash="changed-synthetic-source"))
        self.assertNotEqual(self.queue(rows).queue_hash, self.queue(changed).queue_hash)

    def test_existing_human_disposition_path_accepts_generated_case(self):
        item = self.queue((charge(), charge(charge_id="C2", shipment_id="LOAD-2"))).items[0]
        disposition = cockpit.record_disposition(item, reviewer_id="synthetic-reviewer",
            decision="NEED_EVIDENCE", reason="Training example only; request invoice lineage",
            decided_at="2026-10-13T00:00:00Z")
        self.assertEqual(disposition.case_hash, item.case_hash)
        self.assertEqual(cockpit.export_disposition(disposition)["decision"], "NEED_EVIDENCE")
        self.assertEqual(item.amount_cents, 0)

    def test_record_disposition_rejects_forged_case_provenance(self):
        original = cockpit.make_case(
            case_id="case-1",
            record_hash="record-hash",
            amount_cents=0,
            confidence_ppm=0,
            novelty_ppm=0,
            downstream_risk_ppm=0,
            blocker_codes=("UNSCORED_REVIEW_ONLY", "NO_FINANCIAL_AUTHORITY"),
            evidence_hashes=("evidence-hash",),
        )
        forged = replace(
            original,
            amount_cents=100_000,
            blocker_codes=(),
            evidence_hashes=("forged-evidence",),
        )
        with self.assertRaisesRegex(ValueError, "case proof"):
            cockpit.record_disposition(
                forged,
                reviewer_id="synthetic-reviewer",
                decision="NEED_EVIDENCE",
                reason="Training example only",
                decided_at="2026-10-13T00:00:00Z",
            )

    def test_legitimate_consolidation_is_not_silently_called_recovery(self):
        items = self.queue((charge(), charge(charge_id="C2", shipment_id="LOAD-2"))).items
        self.assertEqual(len(items), 1)  # Still a review burden, NOT a proven duplicate.
        self.assertEqual(items[0].amount_cents, 0)
        self.assertIn("MULTI_LOAD_INVOICE_AUTHORIZATION", items[0].blocker_codes)


    def test_case_identity_text_rejects_whitespace_and_invisible_controls(self):
        valid = {
            "case_id": "case-1",
            "record_hash": "record-hash",
            "amount_cents": 0,
            "confidence_ppm": 0,
            "novelty_ppm": 0,
            "downstream_risk_ppm": 0,
            "blocker_codes": ("REVIEW",),
            "evidence_hashes": ("evidence-hash",),
        }
        invalid_values = (
            ("case_id", " case-1"),
            ("record_hash", "record\u200b-hash"),
            ("blocker_codes", ("RE\u202eVIEW",)),
            ("evidence_hashes", ("evidence\u2066hash",)),
        )

        for field, value in invalid_values:
            with self.subTest(field=field), self.assertRaises(ValueError):
                cockpit.make_case(**{**valid, field: value})

    def test_disposition_reviewer_identity_rejects_ambiguous_text(self):
        item = self.queue((charge(), charge(charge_id="C2", shipment_id="LOAD-2"))).items[0]

        for reviewer_id in (
            " synthetic-reviewer",
            "synthetic\u200breviewer",
            "synthetic\u202ereviewer",
        ):
            with self.subTest(reviewer_id=repr(reviewer_id)), self.assertRaises(
                ValueError
            ):
                cockpit.record_disposition(
                    item,
                    reviewer_id=reviewer_id,
                    decision="NEED_EVIDENCE",
                    reason="Training example only",
                    decided_at="2026-10-13T00:00:00Z",
                )


    def test_build_queue_rejects_forged_case_provenance(self):
        original = cockpit.make_case(
            case_id="case-1",
            record_hash="record-hash",
            amount_cents=0,
            confidence_ppm=0,
            novelty_ppm=0,
            downstream_risk_ppm=0,
            blocker_codes=("UNSCORED_REVIEW_ONLY", "NO_FINANCIAL_AUTHORITY"),
            evidence_hashes=("evidence-hash",),
        )
        forged = replace(
            original,
            amount_cents=100_000,
            blocker_codes=(),
            evidence_hashes=("forged-evidence",),
        )
        with self.assertRaisesRegex(ValueError, "case proof"):
            cockpit.build_queue((forged,))



class BrainReviewManifestTests(unittest.TestCase):
    def test_forged_population_digest_is_rejected(self):
        rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2"))
        forged = replace(population(rows), manifest_hash="0" * 64)
        with self.assertRaisesRegex(ValueError, "population"):
            cockpit.build_invoice_review_queue(forged, rows)

    def test_mutated_population_rows_cannot_reuse_the_old_proof(self):
        rows = (charge(), charge(charge_id="C2", shipment_id="LOAD-2"))
        original = population(rows)
        forged = replace(original, rows=(replace(original.rows[0], source_hash="tampered"), *original.rows[1:]))
        with self.assertRaisesRegex(ValueError, "population"):
            cockpit.build_invoice_review_queue(forged, rows)


if __name__ == "__main__":
    unittest.main()
