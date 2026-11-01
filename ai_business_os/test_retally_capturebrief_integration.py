"""Command Center wiring for the private CaptureBrief immutable snapshot reader."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from ai_business_os.ceo_command_center import CommandCenterError, CommandCenterOperator
from ai_business_os.production_bridge import ProductionReadBridge
from ai_business_os.retally_capturebrief import CaptureBriefOutcomeReader
from ai_business_os.test_retally_capturebrief import event, producer_ledger, snapshot
from ai_business_os.test_retally_group_private import FakeGroupProduction, FINGERPRINT


class CaptureBriefCommandCenterTests(unittest.TestCase):
    def setUp(self):
        self.prod = FakeGroupProduction()
        self.calls = []
        self.raw = producer_ledger(event("PAYMENT"))
        def read():
            self.calls.append("read immutable CaptureBrief source")
            return snapshot(self.raw, observed=datetime.now(timezone.utc).isoformat())
        self.reader = CaptureBriefOutcomeReader(read)
        self.operator = CommandCenterOperator(
            ProductionReadBridge(self.prod.read),
            expected_schema_fingerprint=FINGERPRINT,
            capturebrief_outcome_reader=self.reader,
        )

    def test_default_dashboard_does_not_consume_capturebrief_source(self):
        dashboard = self.operator.dashboard()
        self.assertIsNone(dashboard["retally_group"]["private_observation"])
        self.assertEqual([], self.calls)
        self.assertEqual([], self.prod.writes)

    def test_group_reader_keeps_source_separate_from_business_and_finance(self):
        report = self.operator.group_observation()
        self.assertEqual(["read immutable CaptureBrief source"], self.calls)
        source = report["service_registers"]["capturebrief"]
        self.assertEqual(1, source["outcome_event_count"])
        self.assertEqual(1, source["distinct_case_count_not_customer_count"])
        self.assertEqual("NOT_CONNECTED", source["account_identity_binding"])
        self.assertIsNone(source["verified_metrics"]["cash_collected"])
        self.assertEqual(2, report["matched_catalog_entries"])
        self.assertEqual(9, report["unmatched_catalog_entries"])
        self.assertFalse(next(row for row in report["entries"] if row["catalog_id"] == "capturebrief")["binding_approved"])
        self.assertEqual([], self.prod.writes)

    def test_unconfigured_reader_is_not_connected_not_empty_success(self):
        unconfigured = CommandCenterOperator(
            ProductionReadBridge(self.prod.read), expected_schema_fingerprint=FINGERPRINT)
        report = unconfigured.group_observation()
        self.assertEqual({"mode": "NOT_CONNECTED"}, report["service_registers"]["capturebrief"])

    def test_invalid_reader_type_blocks_before_database_read(self):
        with self.assertRaises(CommandCenterError):
            CommandCenterOperator(ProductionReadBridge(self.prod.read),
                                  expected_schema_fingerprint=FINGERPRINT,
                                  capturebrief_outcome_reader=lambda: {})
        self.assertEqual([], self.prod.calls)

    def test_missing_or_faulted_source_is_redacted_and_never_success(self):
        for outcome in (None, RuntimeError("secret-contact@example.com")):
            with self.subTest(outcome=outcome):
                def invalid():
                    if isinstance(outcome, Exception):
                        raise outcome
                    return outcome
                self.operator.capturebrief_outcome_reader = CaptureBriefOutcomeReader(invalid)
                with self.assertRaises(CommandCenterError) as caught:
                    self.operator.group_observation()
                self.assertEqual("private CaptureBrief outcome source could not be validated", str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)
                self.assertNotIn("secret-contact", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
