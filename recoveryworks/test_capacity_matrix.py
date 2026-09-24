from __future__ import annotations
import unittest
from recoveryworks.capacity_matrix import (
    CapacityDimension, build_conservative_operating_envelope,
    enforce_operating_envelope, measured_capacity_cell,
)

class CapacityMatrixTests(unittest.TestCase):
    def test_measured_matrix_derives_no_extrapolation_envelope(self):
        cells=(
            measured_capacity_cell(
                dimension=CapacityDimension.BILLING_ROWS,billing_rows=1000,
                provider_count=1,tenant_count=1,bundle_bytes=500000,
                runtime_ms=2000,peak_memory_bytes=50000000,
                rows_per_second_milli=500000,evidence_proof_hashes=("1"*64,)),
            measured_capacity_cell(
                dimension=CapacityDimension.PROVIDERS,billing_rows=200,
                provider_count=3,tenant_count=1,bundle_bytes=600000,
                runtime_ms=3000,peak_memory_bytes=70000000,
                rows_per_second_milli=200000,evidence_proof_hashes=("2"*64,)),
            measured_capacity_cell(
                dimension=CapacityDimension.TENANTS,billing_rows=100,
                provider_count=1,tenant_count=8,bundle_bytes=400000,
                runtime_ms=4000,peak_memory_bytes=90000000,
                rows_per_second_milli=100000,evidence_proof_hashes=("3"*64,)),
            measured_capacity_cell(
                dimension=CapacityDimension.EVIDENCE_BYTES,billing_rows=100,
                provider_count=1,tenant_count=1,bundle_bytes=900000,
                evidence_bytes=750000,runtime_ms=2500,
                peak_memory_bytes=60000000,rows_per_second_milli=150000,
                evidence_proof_hashes=("4"*64,)),
        )
        envelope=build_conservative_operating_envelope(cells)
        self.assertEqual(envelope.max_measured_billing_rows,1000)
        self.assertEqual(envelope.max_measured_provider_count,3)
        self.assertEqual(envelope.max_measured_tenant_count,8)
        self.assertEqual(envelope.max_measured_evidence_bytes,750000)
        self.assertFalse(envelope.extrapolation_used)
        self.assertFalse(envelope.external_sla_claimed)
        self.assertTrue(enforce_operating_envelope(
            envelope,billing_rows=1000,provider_count=3,tenant_count=8,
            evidence_bytes=750000)["admitted"])

    def test_overload_fails_closed_before_execution(self):
        cells=(
            measured_capacity_cell(dimension=CapacityDimension.BILLING_ROWS,billing_rows=100,
                provider_count=1,tenant_count=1,bundle_bytes=1000,runtime_ms=100,
                peak_memory_bytes=10000,rows_per_second_milli=1000,evidence_proof_hashes=("1"*64,)),
            measured_capacity_cell(dimension=CapacityDimension.PROVIDERS,billing_rows=10,
                provider_count=2,tenant_count=1,bundle_bytes=1000,runtime_ms=100,
                peak_memory_bytes=10000,rows_per_second_milli=1000,evidence_proof_hashes=("2"*64,)),
            measured_capacity_cell(dimension=CapacityDimension.TENANTS,billing_rows=10,
                provider_count=1,tenant_count=2,bundle_bytes=1000,runtime_ms=100,
                peak_memory_bytes=10000,rows_per_second_milli=1000,evidence_proof_hashes=("3"*64,)),
            measured_capacity_cell(dimension=CapacityDimension.EVIDENCE_BYTES,billing_rows=10,
                provider_count=1,tenant_count=1,bundle_bytes=2000,evidence_bytes=1500,
                runtime_ms=100,peak_memory_bytes=10000,rows_per_second_milli=1000,
                evidence_proof_hashes=("4"*64,)),
        )
        envelope=build_conservative_operating_envelope(cells)
        decision=enforce_operating_envelope(
            envelope,billing_rows=101,provider_count=2,tenant_count=2,
            evidence_bytes=1500)
        self.assertFalse(decision["admitted"])
        self.assertEqual(decision["state"],"ADMISSION_REJECTED_CAPACITY")
        self.assertEqual(decision["exceeded_dimensions"],["billing_rows"])

    def test_matrix_requires_every_measured_dimension(self):
        cell=measured_capacity_cell(
            dimension=CapacityDimension.BILLING_ROWS,billing_rows=10,
            provider_count=1,tenant_count=1,bundle_bytes=1000,runtime_ms=100,
            peak_memory_bytes=10000,rows_per_second_milli=1000,
            evidence_proof_hashes=("1"*64,))
        with self.assertRaisesRegex(ValueError,"rows/providers/tenants/evidence"):
            build_conservative_operating_envelope((cell,))

if __name__=="__main__":
    unittest.main()
