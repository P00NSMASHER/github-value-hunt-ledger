import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.engines.ap import APInvoice, APPayment, detect_ap_overpayments


def invoice(*, verified=True):
    return APInvoice(
        vendor_id="vendor-1",
        invoice_id="inv-1",
        invoice_date="2026-05-01",
        amount_cents=10000,
        currency="USD",
        source_hash="invoicehash",
        locator="file://invoices.csv#inv-1",
        verified=verified,
    )


def payment(payment_id, amount=10000, *, verified=True, posted=True, currency="USD"):
    return APPayment(
        vendor_id="vendor-1",
        invoice_id="inv-1",
        payment_id=payment_id,
        payment_date="2026-05-15",
        amount_cents=amount,
        currency=currency,
        source_hash=f"hash:{payment_id}",
        locator=f"file://payments.csv#{payment_id}",
        verified=verified,
        posted=posted,
    )


class APRecoveryEngineTests(unittest.TestCase):
    def test_duplicate_cash_against_invoice_becomes_validated_recovery(self):
        observations = detect_ap_overpayments(
            client_id="client-1",
            invoices=(invoice(),),
            payments=(payment("p1"), payment("p2")),
        )
        self.assertEqual(len(observations), 1)
        finding = RecoveryEngine().evaluate(observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 10000)
        self.assertEqual(finding.actual_cents, 20000)
        self.assertEqual(finding.potential_recovery_cents, 10000)

    def test_unverified_payment_keeps_case_in_review(self):
        observation = detect_ap_overpayments(
            client_id="client-1",
            invoices=(invoice(),),
            payments=(payment("p1"), payment("p2", verified=False)),
        )[0]
        finding = RecoveryEngine().evaluate(observation)
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_duplicate_export_row_with_same_payment_id_is_deduped(self):
        observations = detect_ap_overpayments(
            client_id="client-1",
            invoices=(invoice(),),
            payments=(payment("p1"), payment("p1")),
        )
        self.assertEqual(observations, ())

    def test_unposted_payment_does_not_create_overpayment(self):
        observations = detect_ap_overpayments(
            client_id="client-1",
            invoices=(invoice(),),
            payments=(payment("p1"), payment("p2", posted=False)),
        )
        self.assertEqual(observations, ())

    def test_currency_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            detect_ap_overpayments(
                client_id="client-1",
                invoices=(invoice(),),
                payments=(payment("p1"), payment("p2", currency="EUR")),
            )

    def test_conflicting_invoice_authority_fails_closed(self):
        other = APInvoice(
            vendor_id="vendor-1", invoice_id="inv-1", invoice_date="2026-05-01",
            amount_cents=11000, currency="USD", source_hash="other",
            locator="file://other#1", verified=True,
        )
        with self.assertRaises(ValueError):
            detect_ap_overpayments(
                client_id="client-1",
                invoices=(invoice(), other),
                payments=(payment("p1"), payment("p2")),
            )


if __name__ == "__main__":
    unittest.main()
