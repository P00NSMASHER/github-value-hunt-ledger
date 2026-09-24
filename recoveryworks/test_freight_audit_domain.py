from datetime import datetime
import unittest

from recoveryworks.branches.freight_audit import (
    CarrierInvoice,
    FindingType,
    FreightAuditDomainAdapter,
    LineItem,
    ProofOfDelivery,
    RateConfirmation,
    Severity,
    UPSTREAM_COMMIT,
    is_same_load,
    normalize_category,
)


def _finding(result, kind):
    return next((item for item in result.findings if item.type is kind), None)


class FreightAuditDomainAdapterTests(unittest.TestCase):
    def test_port_is_pinned_and_keeps_integer_cent_findings(self):
        self.assertEqual(
            UPSTREAM_COMMIT,
            "e7869162cf9cb23f6d520a0cd71f87cf973d8c28",
        )
        rate = RateConfirmation(
            "L1",
            "broker",
            "carrier",
            "A",
            "B",
            210_000,
            line_items=[
                LineItem("Linehaul", 180_000),
                LineItem("Fuel", 30_000),
            ],
        )
        invoice = CarrierInvoice(
            "INV1",
            "L1",
            "carrier",
            240_000,
            line_items=[
                LineItem("Linehaul", 180_000),
                LineItem("Fuel", 30_000),
                LineItem("Fuel Surcharge", 30_000),
            ],
        )

        result = FreightAuditDomainAdapter().audit(rate, invoice, None)

        self.assertEqual(
            _finding(result, FindingType.TOTAL_MISMATCH).money_impact_cents,
            30_000,
        )
        self.assertEqual(
            _finding(result, FindingType.LINE_OVERCHARGE).money_impact_cents,
            30_000,
        )
        self.assertEqual(
            _finding(result, FindingType.DUPLICATE_LINE).money_impact_cents,
            30_000,
        )

    def test_unauthorized_accessorial_is_preserved(self):
        rate = RateConfirmation(
            "L2",
            "broker",
            "carrier",
            "A",
            "B",
            100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        invoice = CarrierInvoice(
            "INV2",
            "L2",
            "carrier",
            112_500,
            line_items=[
                LineItem("Linehaul", 100_000),
                LineItem("Liftgate Service", 12_500),
            ],
        )

        result = FreightAuditDomainAdapter().audit(rate, invoice, None)

        self.assertEqual(
            _finding(result, FindingType.UNAUTHORIZED_ACCESSORIAL).money_impact_cents,
            12_500,
        )

    def test_underbilled_detention_keeps_negative_direction(self):
        rate = RateConfirmation(
            "L3",
            "broker",
            "carrier",
            "A",
            "B",
            100_000,
            line_items=[LineItem("Linehaul", 100_000)],
            approved_accessorials={"detention": 8_000},
            free_time_hours=2.0,
        )
        invoice = CarrierInvoice(
            "INV3",
            "L3",
            "carrier",
            100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        pod = ProofOfDelivery(
            "L3",
            True,
            arrival_time=datetime(2026, 6, 1, 8, 0),
            departure_time=datetime(2026, 6, 1, 12, 15),
        )

        result = FreightAuditDomainAdapter().audit(rate, invoice, pod)
        detention = _finding(result, FindingType.DETENTION_UNDERBILLED)

        self.assertEqual(detention.money_impact_cents, -18_000)
        self.assertIs(detention.severity, Severity.WARN)

    def test_date_only_pod_does_not_create_detention_math(self):
        rate = RateConfirmation(
            "L4",
            "broker",
            "carrier",
            "A",
            "B",
            100_000,
            line_items=[LineItem("Linehaul", 100_000)],
            free_time_hours=2.0,
        )
        invoice = CarrierInvoice(
            "INV4",
            "L4",
            "carrier",
            100_000,
            line_items=[LineItem("Linehaul", 100_000)],
        )
        pod = ProofOfDelivery(
            "L4",
            True,
            arrival_time=datetime(2026, 6, 1, 0, 0),
            departure_time=datetime(2026, 6, 1, 5, 0),
        )

        result = FreightAuditDomainAdapter().audit(rate, invoice, pod)

        self.assertIsNone(_finding(result, FindingType.DETENTION_UNDERBILLED))

    def test_mismatched_load_ids_block(self):
        rate = RateConfirmation("L-100", "broker", "carrier", "A", "B", 10_000)
        invoice = CarrierInvoice("INV5", "L-999", "carrier", 10_000)

        result = FreightAuditDomainAdapter().audit(rate, invoice, None)

        self.assertIs(
            _finding(result, FindingType.LOAD_ID_MISMATCH).severity,
            Severity.BLOCK,
        )

    def test_normalization_matches_upstream_edge_cases(self):
        self.assertEqual(normalize_category("Line Haul"), "linehaul")
        self.assertEqual(normalize_category("FSC"), "fuel")
        self.assertEqual(normalize_category("Detenton"), "detention")
        self.assertTrue(is_same_load("L-100482", "100482"))
        self.assertFalse(is_same_load("L-100481", "L-100999"))


if __name__ == "__main__":
    unittest.main()
