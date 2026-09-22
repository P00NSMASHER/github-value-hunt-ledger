import unittest

from recoveryworks.reconciliation_kernel import (
    ManyToOneConfig,
    ReconConfig,
    ReconTxn,
    SOURCE_COMMIT,
    parse_amount_to_minor,
    reconcile,
)


def txn(identifier, amount, *, date="2026-03-10", currency="USD", reference=None):
    return ReconTxn(
        id=identifier,
        amount=amount,
        date=date,
        currency=currency,
        reference=reference,
    )


class ReconciliationKernelTests(unittest.TestCase):
    def test_source_is_pinned(self):
        self.assertEqual(SOURCE_COMMIT, "e6b787213bb023568c99c432ea4733e1f2456a5e")

    def test_exact_and_fuzzy_ladder_order(self):
        result = reconcile(
            [txn("a1", "100.00", reference="ORD-7")],
            [
                txn("b-drift", "99.80"),
                txn("b-exact", "100.00", reference="ORD-7"),
            ],
        )
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.matches[0].receipt.rule, "exact")
        self.assertEqual(result.matches[0].settlement_ids, ("b-exact",))

        fuzzy = reconcile(
            [txn("a1", "10.00", reference="00042")],
            [txn("b1", "10.00", date="2026-03-12", reference="REF 42")],
        )
        self.assertEqual(fuzzy.matches[0].receipt.rule, "reference-fuzzy")
        self.assertEqual(fuzzy.matches[0].receipt.normalization["normalized"], "42")

    def test_amount_date_and_tolerance(self):
        window = reconcile(
            [txn("a1", "25.00")],
            [txn("b1", "25.00", date="2026-03-12")],
        )
        self.assertEqual(window.matches[0].receipt.rule, "amount-date-window")
        self.assertEqual(window.matches[0].receipt.date_delta_days, -2)

        tolerance = reconcile(
            [txn("a1", "250.00", reference="INV-1")],
            [txn("b1", "249.10", reference="INV-1")],
        )
        receipt = tolerance.matches[0].receipt
        self.assertEqual(receipt.rule, "amount-tolerance")
        self.assertEqual(receipt.amount_delta_minor, 90)
        self.assertEqual(receipt.tolerance["allowed_delta_minor"], 125)
        self.assertEqual(receipt.tolerance["consumed_bps"], 36)

    def test_many_to_one_and_near_miss(self):
        result = reconcile(
            [
                txn("a1", "12.75", date="2026-03-08"),
                txn("a2", "9.50", date="2026-03-09"),
                txn("a3", "21.25", date="2026-03-09"),
            ],
            [txn("b1", "43.50", reference="PAYOUT-1")],
        )
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.matches[0].receipt.rule, "many-to-one")
        self.assertEqual(set(result.matches[0].internal_ids), {"a1", "a2", "a3"})

        miss = reconcile(
            [txn("a1", "12.75"), txn("a2", "9.50")],
            [txn("b1", "22.26")],
        )
        self.assertEqual(len(miss.matches), 0)

    def test_many_to_one_respects_group_bound(self):
        result = reconcile(
            [txn("a1", "10.00"), txn("a2", "11.00"), txn("a3", "12.00")],
            [txn("b1", "33.00")],
            ReconConfig(many_to_one=ManyToOneConfig(max_group_size=2)),
        )
        self.assertEqual(len(result.matches), 0)

    def test_currency_isolation_and_amount_mismatch_residual(self):
        isolated = reconcile(
            [txn("a1", "10.00", currency="EUR", reference="X-1")],
            [txn("b1", "10.00", currency="USD", reference="X-1")],
        )
        self.assertEqual(len(isolated.matches), 0)
        self.assertEqual(isolated.unmatched_internal[0].category, "missing-in-settlement")

        mismatch = reconcile(
            [txn("a1", "64.00", reference="ORD-18")],
            [txn("b1", "58.00", reference="ord 18")],
        )
        residual = mismatch.unmatched_internal[0]
        self.assertEqual(residual.category, "amount-mismatch")
        self.assertEqual(residual.candidate.id, "b1")
        self.assertEqual(residual.candidate.amount_delta_minor, 600)

    def test_strict_money_and_date_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unparseable amount"):
            parse_amount_to_minor("1,000.00")
        with self.assertRaisesRegex(ValueError, "fractional digits"):
            parse_amount_to_minor("1.005")
        with self.assertRaisesRegex(ValueError, "impossible calendar date"):
            reconcile([txn("a1", "1.00", date="2026-02-30")], [])

    def test_duplicate_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            reconcile([txn("a1", "1.00"), txn("a1", "2.00")], [])

    def test_shuffle_invariance(self):
        internal = [
            txn("a3", "30.00", date="2026-03-09", reference="ORD-3"),
            txn("a1", "10.00", reference="ORD-1"),
            txn("a2", "20.00", date="2026-03-11"),
        ]
        settlement = [
            txn("b2", "20.00", date="2026-03-12"),
            txn("b1", "10.00", reference="ORD-1"),
            txn("b3", "30.00", date="2026-03-09", reference="ord 3"),
        ]
        first = reconcile(internal, settlement).canonical_json()
        second = reconcile(list(reversed(internal)), list(reversed(settlement))).canonical_json()
        self.assertEqual(first, second)

    def test_residue_is_stable(self):
        result = reconcile(
            [txn("a1", "64.00", reference="ORD-18"), txn("a2", "5.00")],
            [txn("b1", "58.00", reference="ord 18")],
        )
        ids_a = {r.id for r in result.unmatched_internal}
        ids_b = {r.id for r in result.unmatched_settlement}
        again = reconcile(
            [t for t in [txn("a1", "64.00", reference="ORD-18"), txn("a2", "5.00")] if t.id in ids_a],
            [t for t in [txn("b1", "58.00", reference="ord 18")] if t.id in ids_b],
        )
        self.assertEqual(len(again.matches), 0)
        self.assertEqual(
            [(r.id, r.category) for r in again.unmatched_internal],
            [(r.id, r.category) for r in result.unmatched_internal],
        )


if __name__ == "__main__":
    unittest.main()
