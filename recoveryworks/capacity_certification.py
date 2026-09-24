"""Deterministic RecoveryWorks pilot workload generation and capacity measurement.

This is an internal engineering envelope, not a customer SLA or external
certification. Measurements execute the real local Cletrics -> RecoveryOS pilot.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import time
import tracemalloc
from typing import Any

from recoveryworks.models import canonical_hash
from recoveryworks.pilot_runner import PilotRunResult, run_local_pilot


@dataclass(frozen=True)
class CapacityEnvelope:
    max_billing_rows: int
    max_bundle_bytes: int
    max_peak_memory_bytes: int
    max_runtime_ms: int
    min_rows_per_second_milli: int

    def __post_init__(self) -> None:
        for name in (
            "max_billing_rows",
            "max_bundle_bytes",
            "max_peak_memory_bytes",
            "max_runtime_ms",
            "min_rows_per_second_milli",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class DeterministicCloudWorkload:
    row_count: int
    focus_path: str
    meter_path: str
    rates_path: str
    focus_sha256: str
    meter_sha256: str
    rates_sha256: str
    expected_validated_cents: int

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_deterministic_cloud_workload(
    root: str | Path,
    *,
    row_count: int,
) -> DeterministicCloudWorkload:
    if type(row_count) is not int or row_count <= 0:
        raise ValueError("row_count must be positive")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    focus = root / "focus.csv"
    meter = root / "meter.csv"
    rates = root / "rates.csv"

    focus_lines = [
        "ChargeId,ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "ChargePeriodEnd,BilledCost,EffectiveCost,ListCost,ContractedCost,"
        "BillingCurrency,ResourceId,RegionId,SkuId,InvoiceId,ConsumedQuantity,"
        "ConsumedUnit"
    ]
    meter_lines = ["Charge_ID,Meter_Record_ID,Usage_Units"]
    for index in range(row_count):
        charge = f"CAP-{index:08d}"
        resource = f"i-cap-{index:08d}"
        focus_lines.append(
            f"{charge},Amazon Web Services,capacity-acct,EC2,"
            "2026-08-31T00:00:00Z,2026-09-01T00:00:00Z,"
            f"40.00,40.00,40.00,40.00,USD,{resource},us-east-1,"
            f"sku-{index:08d},INV-CAP,10,hours"
        )
        meter_lines.append(f"{charge},M-{index:08d},10")

    focus.write_text("\n".join(focus_lines) + "\n", encoding="utf-8")
    meter.write_text("\n".join(meter_lines) + "\n", encoding="utf-8")
    rates.write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "Amazon Web Services,EC2,2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )
    return DeterministicCloudWorkload(
        row_count=row_count,
        focus_path=str(focus),
        meter_path=str(meter),
        rates_path=str(rates),
        focus_sha256=_sha(focus),
        meter_sha256=_sha(meter),
        rates_sha256=_sha(rates),
        expected_validated_cents=row_count * 1000,
    )


@dataclass(frozen=True)
class CapacityMeasurement:
    measurement_id: str
    workload_proof_hash: str
    row_count: int
    runtime_ms: int
    rows_per_second_milli: int
    peak_memory_bytes: int
    bundle_bytes: int
    validated_cents: int
    state_head_present: bool
    envelope: CapacityEnvelope
    passed: bool
    internal_only: bool = True
    external_sla_claimed: bool = False

    def __post_init__(self) -> None:
        if self.passed is not True:
            raise ValueError("capacity measurement artifact only represents a passing envelope")
        if self.internal_only is not True or self.external_sla_claimed:
            raise ValueError("capacity envelope is internal engineering evidence only")
        expected = "recoveryworks-capacity-measurement:" + canonical_hash(
            self._identity()
        )
        if self.measurement_id != expected:
            raise ValueError("measurement_id does not bind capacity measurement")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "workload_proof_hash": self.workload_proof_hash,
            "row_count": self.row_count,
            "runtime_ms": self.runtime_ms,
            "rows_per_second_milli": self.rows_per_second_milli,
            "peak_memory_bytes": self.peak_memory_bytes,
            "bundle_bytes": self.bundle_bytes,
            "validated_cents": self.validated_cents,
            "state_head_present": self.state_head_present,
            "envelope": asdict(self.envelope),
            "passed": True,
            "internal_only": True,
            "external_sla_claimed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "measurement_id": self.measurement_id,
            "proof_hash": self.proof_hash,
            "state": "INTERNAL_CAPACITY_ENVELOPE_PASSED",
        }


def capacity_pilot_spec(
    root: str | Path,
    workload: DeterministicCloudWorkload,
) -> dict[str, Any]:
    root = Path(root)
    private = root / "private"
    return {
        "schema": 1,
        "deployment_id": f"capacity-{workload.row_count}",
        "tenant_id": f"capacity-tenant-{workload.row_count}",
        "client_id": f"capacity-client-{workload.row_count}",
        "currency": "USD",
        "provider": "aws",
        "security": {
            "cloud_access_mode": "READ_ONLY",
            "recoveryos_provider_write_credentials": False,
            "remediation_execution_enabled": False,
            "external_actions_enabled": False,
            "private_state_required": True,
        },
        "period": {
            "start": "2026-08-01",
            "end": "2026-08-31",
            "exported_at": "2026-09-01T12:00:00Z",
        },
        "cletrics": {
            "focus_csv": workload.focus_path,
            "meter_csv": workload.meter_path,
            "release": "capacity-fixture",
            "commit": "a" * 40,
        },
        "recoveryos": {
            "rates_csv": workload.rates_path,
            "verification": {
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
            },
            "bundle_path": str(private / "bundle.zip"),
            "ledger_path": str(private / "ledger.json"),
            "receipt_registry_path": str(private / "receipts.json"),
            "report_path": str(private / "assurance.json"),
        },
    }


def measure_pilot_capacity(
    root: str | Path,
    workload: DeterministicCloudWorkload,
    envelope: CapacityEnvelope,
) -> tuple[CapacityMeasurement, PilotRunResult]:
    if workload.row_count > envelope.max_billing_rows:
        raise ValueError("workload row count exceeds capacity envelope")
    spec = capacity_pilot_spec(root, workload)

    tracemalloc.start()
    started = time.perf_counter_ns()
    try:
        pilot = run_local_pilot(spec, base_dir=root)
        runtime_ns = time.perf_counter_ns() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    runtime_ms = max(1, (runtime_ns + 999_999) // 1_000_000)
    rows_per_second_milli = (
        workload.row_count * 1_000_000
    ) // runtime_ms
    bundle_bytes = Path(pilot.export_receipt.output_path).stat().st_size
    validated = pilot.continuous_result.scan.report.totals["validated_cents"]
    state_head_present = pilot.continuous_result.scan.state_head_hash is not None

    failures = []
    if runtime_ms > envelope.max_runtime_ms:
        failures.append("runtime")
    if peak > envelope.max_peak_memory_bytes:
        failures.append("peak_memory")
    if bundle_bytes > envelope.max_bundle_bytes:
        failures.append("bundle_size")
    if rows_per_second_milli < envelope.min_rows_per_second_milli:
        failures.append("throughput")
    if validated != workload.expected_validated_cents:
        failures.append("validated_cents")
    if not state_head_present:
        failures.append("state_head")
    if failures:
        raise ValueError(
            "capacity envelope failed: " + ", ".join(failures)
        )

    identity = {
        "schema": 1,
        "workload_proof_hash": workload.proof_hash,
        "row_count": workload.row_count,
        "runtime_ms": runtime_ms,
        "rows_per_second_milli": rows_per_second_milli,
        "peak_memory_bytes": peak,
        "bundle_bytes": bundle_bytes,
        "validated_cents": validated,
        "state_head_present": state_head_present,
        "envelope": asdict(envelope),
        "passed": True,
        "internal_only": True,
        "external_sla_claimed": False,
    }
    measurement = CapacityMeasurement(
        measurement_id="recoveryworks-capacity-measurement:"
        + canonical_hash(identity),
        workload_proof_hash=workload.proof_hash,
        row_count=workload.row_count,
        runtime_ms=runtime_ms,
        rows_per_second_milli=rows_per_second_milli,
        peak_memory_bytes=peak,
        bundle_bytes=bundle_bytes,
        validated_cents=validated,
        state_head_present=state_head_present,
        envelope=envelope,
        passed=True,
        internal_only=True,
        external_sla_claimed=False,
    )
    return measurement, pilot
