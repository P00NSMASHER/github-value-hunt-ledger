from recoveryworks.test_support import source_hash as H
from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.procurement import (
    ProcurementAuthority,
    ProcurementInvoiceLine,
    ProcurementQuantityApproval,
    audit_procurement_lines,
)
from recoveryworks.branches.procurement_csv import (
    load_procurement_authorities_csv,
    load_procurement_invoice_lines_csv,
    load_procurement_quantities_csv,
)


def line(*, verified=True, actual=10000):
    return ProcurementInvoiceLine(
        invoice_line_id="L-1",
        invoice_id="INV-1",
        purchaser_id="client-1",
        supplier_id="Supplier A",
        po_line_id="PO-1-L1",
        sku="SKU-1",
        invoice_date="2026-08-15",
        invoiced_quantity="10",
        actual_line_cents=actual,
        source_hash=H("line-hash"),
        source_locator="file://invoice.csv#row=2",
        verified=verified,
    )


def authority(*, verified=True, price=1000):
    return ProcurementAuthority(
        authority_id="AUTH-1",
        supplier_id="Supplier A",
        po_line_id="PO-1-L1",
        sku="SKU-1",
        effective_from="2026-01-01",
        effective_to=None,
        contracted_unit_price_cents=price,
        price_basis="Approved PO line price",
        source_hash=H("authority-hash"),
        source_locator="file://po.csv#row=2",
        verified=verified,
    )


def quantity(*, verified=True, qty="8"):
    return ProcurementQuantityApproval(
        invoice_line_id="L-1",
        approved_billable_quantity=qty,
        quantity_basis="Receiving/3-way-match approved quantity",
        source_hash=H("quantity-hash"),
        source_locator="file://quantity.csv#row=2",
        verified=verified,
    )


class ProcurementRecoveryTests(unittest.TestCase):
    def test_price_and_quantity_variance_is_validated(self):
        batch = audit_procurement_lines(
            client_id="client-1",
            invoice_lines=(line(),),
            authorities=(authority(),),
            quantity_approvals=(quantity(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 8000)
        self.assertEqual(finding.actual_cents, 10000)
        self.assertEqual(finding.potential_recovery_cents, 2000)

    def test_missing_quantity_fails_closed(self):
        batch = audit_procurement_lines(
            client_id="client-1",
            invoice_lines=(line(),),
            authorities=(authority(),),
            quantity_approvals=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "NO_APPROVED_BILLABLE_QUANTITY",
        )

    def test_unverified_quantity_keeps_candidate_review(self):
        batch = audit_procurement_lines(
            client_id="client-1",
            invoice_lines=(line(),),
            authorities=(authority(),),
            quantity_approvals=(quantity(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_real_csvs_flow_to_procurement_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "invoice.csv").write_text(
                "Invoice_Line_ID,Invoice_ID,Purchaser_ID,Supplier_ID,PO_Line_ID,SKU,"
                "Invoice_Date,Invoiced_Quantity,Actual_Line_Amount\n"
                "L-1,INV-1,client-1,Supplier A,PO-1-L1,SKU-1,2026-08-15,10,100.00\n",
                encoding="utf-8",
            )
            (root / "authority.csv").write_text(
                "Authority_ID,Supplier_ID,PO_Line_ID,SKU,Effective_From,Effective_To,"
                "Contracted_Unit_Price,Price_Basis\n"
                "AUTH-1,Supplier A,PO-1-L1,SKU-1,2026-01-01,,10.00,Approved PO\n",
                encoding="utf-8",
            )
            (root / "quantity.csv").write_text(
                "Invoice_Line_ID,Approved_Billable_Quantity,Quantity_Basis\n"
                "L-1,8,Receiving approved\n",
                encoding="utf-8",
            )
            batch = audit_procurement_lines(
                client_id="client-1",
                invoice_lines=load_procurement_invoice_lines_csv(
                    root / "invoice.csv", verified=True
                ),
                authorities=load_procurement_authorities_csv(
                    root / "authority.csv", verified=True
                ),
                quantity_approvals=load_procurement_quantities_csv(
                    root / "quantity.csv", verified=True
                ),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertEqual(finding.potential_recovery_cents, 2000)
            self.assertIn("#row=2", finding.evidence[0].locator)


if __name__ == "__main__":
    unittest.main()
