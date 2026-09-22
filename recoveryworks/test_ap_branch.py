import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.ap import (
    APObligation,
    APPayment,
    build_ap_observations,
    canonical_invoice_number,
    normalize_invoice_number,
)


def payment(pid, vendor, invoice, cents, *, verified=True):
    return APPayment(
        payment_id=pid,
        vendor_id=vendor,
        invoice_number=invoice,
        amount_cents=cents,
        source_hash=f"hash-{pid}",
        source_locator=f"file://payments.csv#{pid}",
        verified=verified,
        payment_date="2026-08-01",
    )


def obligation(vendor, invoice, cents, *, verified=True):
    return APObligation(
        vendor_id=vendor,
        invoice_number=invoice,
        expected_cents=cents,
        source_hash=f"obligation-{vendor}-{invoice}",
        source_locator=f"file://invoices.csv#{invoice}",
        effective_from="2026-01-01",
        verified=verified,
    )


class APBranchTests(unittest.TestCase):
    def test_canonical_invoice_number_never_strips_semantic_suffix(self):
        self.assertEqual(canonical_invoice_number(" inv-2001-R "), "INV-2001-R")
        self.assertNotEqual(
            canonical_invoice_number("INV-2001"),
            canonical_invoice_number("INV-2001-R"),
        )

    def test_invoice_normalization_only_strips_known_suffix(self):
        self.assertEqual(normalize_invoice_number("inv-2001-R"), "INV-2001")
        self.assertEqual(normalize_invoice_number("inv-2001-DUP"), "INV-2001")
        self.assertNotEqual(
            normalize_invoice_number("INV-100"),
            normalize_invoice_number("INV-1000"),
        )

    def test_orphan_exact_duplicate_stays_review(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor", "INV-2001", 432100),
                payment("p2", "vendor", "INV-2001-R", 432100),
            ),
        )
        self.assertEqual(len(observations), 1)
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)
        self.assertEqual(finding.potential_recovery_cents, 432100)
        self.assertEqual(finding.reason, "SUSPECTED_DUPLICATE_PAYMENT")

    def test_suffix_alias_cannot_borrow_verified_obligation_authority(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor", "INV-2001", 432100),
                payment("p2", "vendor", "INV-2001-R", 432100),
            ),
            obligations=(obligation("vendor", "INV-2001", 432100),),
        )
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)
        self.assertEqual(finding.potential_recovery_cents, 432100)
        self.assertIsNone(finding.rule)

    def test_exact_invoice_duplicate_can_use_verified_obligation(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor", "INV-2001", 432100),
                payment("p2", "vendor", "INV-2001", 432100),
            ),
            obligations=(obligation("vendor", "INV-2001", 432100),),
        )
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 432100)

    def test_three_payments_recover_two_extras(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor", "INV-7", 10000),
                payment("p2", "vendor", "INV-7-DUP", 10000),
                payment("p3", "vendor", "INV-7-COPY", 10000),
            ),
            obligations=(obligation("vendor", "INV-7", 10000),),
        )
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertEqual(finding.potential_recovery_cents, 20000)
        self.assertEqual(finding.metadata["payment_count"], 3)

    def test_single_payment_above_verified_obligation_is_detected(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(payment("p1", "vendor", "INV-9", 15000),),
            obligations=(obligation("vendor", "INV-9", 10000),),
        )
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 5000)
        self.assertEqual(finding.reason, "AP_OBLIGATION_OVERPAYMENT")

    def test_unverified_obligation_or_payment_stays_review(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor", "INV-1", 10000, verified=True),
                payment("p2", "vendor", "INV-1-R", 10000, verified=False),
            ),
            obligations=(obligation("vendor", "INV-1", 10000, verified=True),),
        )
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_same_amount_different_invoices_do_not_false_match(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor", "INV-100", 10000),
                payment("p2", "vendor", "INV-1000", 10000),
            ),
        )
        self.assertEqual(observations, ())

    def test_same_invoice_different_vendors_do_not_false_match(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                payment("p1", "vendor-a", "INV-1", 10000),
                payment("p2", "vendor-b", "INV-1", 10000),
            ),
        )
        self.assertEqual(observations, ())

    def test_conflicting_obligations_are_rejected(self):
        with self.assertRaises(ValueError):
            build_ap_observations(
                client_id="client",
                payments=(payment("p1", "vendor", "INV-1", 12000),),
                obligations=(
                    obligation("vendor", "INV-1", 10000),
                    obligation("vendor", "INV-1", 11000),
                ),
            )


if __name__ == "__main__":
    unittest.main()
