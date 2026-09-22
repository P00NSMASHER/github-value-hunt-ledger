from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.ap import (
    APObligation,
    APPayment,
    APVendorStatementLine,
    audit_ap_recovery,
)
from recoveryworks.branches.ap_csv import (
    load_vendor_statements_csv,
    signed_money_to_cents,
)


def payment(pid, amount=10000, *, invoice="INV-1", verified=True):
    return APPayment(
        payment_id=pid,
        vendor_id="Vendor A",
        invoice_number=invoice,
        amount_cents=amount,
        source_hash=f"pay-{pid}",
        source_locator=f"file://payments.csv#{pid}",
        verified=verified,
        payment_date="2026-08-01",
    )


def obligation(amount=10000, *, verified=True):
    return APObligation(
        vendor_id="Vendor A",
        invoice_number="INV-1",
        expected_cents=amount,
        source_hash="invoice-hash",
        source_locator="file://invoices.csv#INV-1",
        effective_from="2026-07-01",
        verified=verified,
    )


def statement(balance, *, verified=True, date="2026-08-31"):
    return APVendorStatementLine(
        vendor_id="Vendor A",
        invoice_number="INV-1",
        balance_cents=balance,
        statement_date=date,
        source_hash="statement-hash",
        source_locator="file://statement.csv#INV-1",
        verified=verified,
    )


class APRealIngestionTests(unittest.TestCase):
    def test_statement_money_parser_supports_credits(self):
        self.assertEqual(signed_money_to_cents("-123.45"), -12345)
        self.assertEqual(signed_money_to_cents("(123.45)"), -12345)
        self.assertEqual(signed_money_to_cents("0"), 0)

    def test_statement_only_credit_is_validated_when_source_verified(self):
        batch = audit_ap_recovery(
            client_id="client",
            payments=(),
            statements=(statement(-25000),),
        )
        self.assertEqual(batch.exceptions, ())
        self.assertEqual(len(batch.observations), 1)
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.potential_recovery_cents, 25000)
        self.assertEqual(finding.reason, "VENDOR_STATEMENT_CREDIT")

    def test_statement_credit_can_confirm_duplicate_without_obligation(self):
        batch = audit_ap_recovery(
            client_id="client",
            payments=(payment("P-1"), payment("P-2", invoice="INV-1-DUP")),
            statements=(statement(-10000),),
        )
        self.assertEqual(len(batch.observations), 1)
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.reason, "VENDOR_STATEMENT_CONFIRMED_DUPLICATE_PAYMENT")
        self.assertEqual(len(finding.evidence), 3)

    def test_contradictory_positive_statement_forces_review(self):
        batch = audit_ap_recovery(
            client_id="client",
            payments=(payment("P-1"), payment("P-2", invoice="INV-1-DUP")),
            obligations=(obligation(),),
            statements=(statement(5000),),
        )
        self.assertEqual(batch.exceptions[0].code, "STATEMENT_CONTRADICTS_OVERPAYMENT")
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)


    def test_mismatched_statement_credit_does_not_double_count_or_validate(self):
        batch = audit_ap_recovery(
            client_id="client",
            payments=(payment("P-1"), payment("P-2", invoice="INV-1-DUP")),
            statements=(statement(-5000),),
        )
        self.assertEqual(len(batch.observations), 1)
        self.assertEqual(batch.exceptions[0].code, "STATEMENT_CREDIT_MISMATCH")
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)
        self.assertEqual(finding.potential_recovery_cents, 10000)

    def test_duplicate_payment_ids_are_excluded_from_recovery_math(self):
        batch = audit_ap_recovery(
            client_id="client",
            payments=(payment("P-1"), payment("P-1")),
            obligations=(obligation(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "DUPLICATE_PAYMENT_ID")

    def test_vendor_statement_csv_preserves_hash_and_row_locator(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Vendor_Statement.csv"
            path.write_text(
                "Vendor,Invoice_Number,Balance,Statement_Date\n"
                "Vendor A,INV-1,(100.00),2026-08-31\n",
                encoding="utf-8",
            )
            rows = load_vendor_statements_csv(path, verified=True)
            self.assertEqual(rows[0].balance_cents, -10000)
            self.assertTrue(rows[0].source_hash)
            self.assertIn("#row=2", rows[0].source_locator)
            self.assertTrue(rows[0].verified)


if __name__ == "__main__":
    unittest.main()
