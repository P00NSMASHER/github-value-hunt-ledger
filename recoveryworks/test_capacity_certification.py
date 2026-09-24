from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.capacity_certification import (
    CapacityEnvelope,
    generate_deterministic_cloud_workload,
    measure_pilot_capacity,
)


class CapacityCertificationTests(unittest.TestCase):
    def test_workload_bytes_are_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            wa = generate_deterministic_cloud_workload(Path(a), row_count=50)
            wb = generate_deterministic_cloud_workload(Path(b), row_count=50)
            self.assertEqual(wa.focus_sha256, wb.focus_sha256)
            self.assertEqual(wa.meter_sha256, wb.meter_sha256)
            self.assertEqual(wa.rates_sha256, wb.rates_sha256)
            self.assertEqual(wa.expected_validated_cents, 50000)

    def test_real_pilot_passes_internal_capacity_envelope(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            workload = generate_deterministic_cloud_workload(
                root / "inputs",
                row_count=200,
            )
            envelope = CapacityEnvelope(
                max_billing_rows=1000,
                max_bundle_bytes=8 * 1024 * 1024,
                max_peak_memory_bytes=256 * 1024 * 1024,
                max_runtime_ms=30_000,
                min_rows_per_second_milli=1_000,
            )
            measurement, pilot = measure_pilot_capacity(
                root,
                workload,
                envelope,
            )
            self.assertEqual(
                measurement.as_dict()["state"],
                "INTERNAL_CAPACITY_ENVELOPE_PASSED",
            )
            self.assertEqual(measurement.row_count, 200)
            self.assertEqual(measurement.validated_cents, 200000)
            self.assertGreater(measurement.rows_per_second_milli, 0)
            self.assertGreater(measurement.peak_memory_bytes, 0)
            self.assertGreater(measurement.bundle_bytes, 0)
            self.assertFalse(measurement.external_sla_claimed)
            self.assertEqual(
                pilot.export_receipt.charge_count,
                200,
            )

    def test_oversized_requested_workload_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            workload = generate_deterministic_cloud_workload(
                root / "inputs",
                row_count=20,
            )
            envelope = CapacityEnvelope(
                max_billing_rows=10,
                max_bundle_bytes=1024,
                max_peak_memory_bytes=1024,
                max_runtime_ms=1000,
                min_rows_per_second_milli=1,
            )
            with self.assertRaisesRegex(ValueError, "row count exceeds"):
                measure_pilot_capacity(root, workload, envelope)


if __name__ == "__main__":
    unittest.main()
