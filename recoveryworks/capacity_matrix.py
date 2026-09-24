"""Proof-bound capacity matrix and conservative internal operating envelope."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
import time
import tracemalloc
from typing import Any, Iterable

from recoveryworks.capacity_certification import CapacityMeasurement
from recoveryworks.pilot_runner import run_local_pilot
from recoveryworks.models import canonical_hash, normalize_sha256


class CapacityDimension(str, Enum):
    BILLING_ROWS = "BILLING_ROWS"
    PROVIDERS = "PROVIDERS"
    TENANTS = "TENANTS"
    EVIDENCE_BYTES = "EVIDENCE_BYTES"


@dataclass(frozen=True)
class CapacityMatrixCell:
    cell_id: str
    dimension: CapacityDimension
    billing_rows: int
    provider_count: int
    tenant_count: int
    bundle_bytes: int
    evidence_bytes: int
    runtime_ms: int
    peak_memory_bytes: int
    rows_per_second_milli: int
    evidence_proof_hashes: tuple[str, ...]
    passed: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, CapacityDimension):
            raise ValueError("dimension must be CapacityDimension")
        for name in (
            "billing_rows","provider_count","tenant_count","bundle_bytes","evidence_bytes",
            "runtime_ms","peak_memory_bytes","rows_per_second_milli",
        ):
            value=getattr(self,name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be positive")
        hashes=tuple(sorted(normalize_sha256("evidence_proof_hash",h) for h in self.evidence_proof_hashes))
        if not hashes:
            raise ValueError("capacity cell requires measured evidence")
        object.__setattr__(self,"evidence_proof_hashes",hashes)
        if self.passed is not True:
            raise ValueError("capacity matrix only accepts passing measured cells")
        expected="recoveryworks-capacity-cell:"+canonical_hash(self._identity())
        if self.cell_id!=expected:
            raise ValueError("cell_id does not bind capacity cell")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,"dimension":self.dimension.value,
            "billing_rows":self.billing_rows,"provider_count":self.provider_count,
            "tenant_count":self.tenant_count,"bundle_bytes":self.bundle_bytes,
            "evidence_bytes":self.evidence_bytes,
            "runtime_ms":self.runtime_ms,"peak_memory_bytes":self.peak_memory_bytes,
            "rows_per_second_milli":self.rows_per_second_milli,
            "evidence_proof_hashes":list(self.evidence_proof_hashes),"passed":True,
        }
    @property
    def proof_hash(self)->str: return canonical_hash(self._identity())


def row_capacity_cell(measurement: CapacityMeasurement) -> CapacityMatrixCell:
    identity={
        "schema":1,"dimension":"BILLING_ROWS","billing_rows":measurement.row_count,
        "provider_count":1,"tenant_count":1,"bundle_bytes":measurement.bundle_bytes,
        "evidence_bytes":measurement.bundle_bytes,
        "runtime_ms":measurement.runtime_ms,
        "peak_memory_bytes":measurement.peak_memory_bytes,
        "rows_per_second_milli":measurement.rows_per_second_milli,
        "evidence_proof_hashes":[measurement.proof_hash],"passed":True,
    }
    return CapacityMatrixCell(
        cell_id="recoveryworks-capacity-cell:"+canonical_hash(identity),
        dimension=CapacityDimension.BILLING_ROWS,billing_rows=measurement.row_count,
        provider_count=1,tenant_count=1,bundle_bytes=measurement.bundle_bytes,
        evidence_bytes=measurement.bundle_bytes,
        runtime_ms=measurement.runtime_ms,peak_memory_bytes=measurement.peak_memory_bytes,
        rows_per_second_milli=measurement.rows_per_second_milli,
        evidence_proof_hashes=(measurement.proof_hash,),passed=True,
    )


def measured_capacity_cell(
    *, dimension: CapacityDimension, billing_rows: int, provider_count: int,
    tenant_count: int, bundle_bytes: int, runtime_ms: int,
    peak_memory_bytes: int, rows_per_second_milli: int,
    evidence_proof_hashes: tuple[str,...],
    evidence_bytes: int | None = None,
) -> CapacityMatrixCell:
    evidence_size = bundle_bytes if evidence_bytes is None else evidence_bytes
    identity={
        "schema":1,"dimension":dimension.value,"billing_rows":billing_rows,
        "provider_count":provider_count,"tenant_count":tenant_count,
        "bundle_bytes":bundle_bytes,"evidence_bytes":evidence_size,
        "runtime_ms":runtime_ms,
        "peak_memory_bytes":peak_memory_bytes,
        "rows_per_second_milli":rows_per_second_milli,
        "evidence_proof_hashes":sorted(evidence_proof_hashes),"passed":True,
    }
    return CapacityMatrixCell(
        cell_id="recoveryworks-capacity-cell:"+canonical_hash(identity),
        dimension=dimension,billing_rows=billing_rows,provider_count=provider_count,
        tenant_count=tenant_count,bundle_bytes=bundle_bytes,
        evidence_bytes=evidence_size,runtime_ms=runtime_ms,
        peak_memory_bytes=peak_memory_bytes,
        rows_per_second_milli=rows_per_second_milli,
        evidence_proof_hashes=evidence_proof_hashes,passed=True,
    )


@dataclass(frozen=True)
class ConservativeOperatingEnvelope:
    envelope_id: str
    max_measured_billing_rows: int
    max_measured_provider_count: int
    max_measured_tenant_count: int
    max_measured_bundle_bytes: int
    max_measured_evidence_bytes: int
    max_measured_runtime_ms: int
    max_measured_peak_memory_bytes: int
    min_measured_rows_per_second_milli: int
    matrix_cell_hashes: tuple[str,...]
    internal_only: bool = True
    extrapolation_used: bool = False
    external_sla_claimed: bool = False

    def __post_init__(self)->None:
        for name in (
            "max_measured_billing_rows","max_measured_provider_count",
            "max_measured_tenant_count","max_measured_bundle_bytes",
            "max_measured_evidence_bytes",
            "max_measured_runtime_ms","max_measured_peak_memory_bytes",
            "min_measured_rows_per_second_milli",
        ):
            if type(getattr(self,name)) is not int or getattr(self,name)<=0:
                raise ValueError(f"{name} must be positive")
        hashes=tuple(sorted(normalize_sha256("matrix_cell_hash",h) for h in self.matrix_cell_hashes))
        if not hashes: raise ValueError("operating envelope requires matrix cells")
        object.__setattr__(self,"matrix_cell_hashes",hashes)
        if not self.internal_only or self.extrapolation_used or self.external_sla_claimed:
            raise ValueError("operating envelope must remain internal and measured-only")
        expected="recoveryworks-operating-envelope:"+canonical_hash(self._identity())
        if self.envelope_id!=expected: raise ValueError("envelope_id does not bind operating envelope")

    def _identity(self)->dict[str,Any]:
        return {
            "schema":1,
            "max_measured_billing_rows":self.max_measured_billing_rows,
            "max_measured_provider_count":self.max_measured_provider_count,
            "max_measured_tenant_count":self.max_measured_tenant_count,
            "max_measured_bundle_bytes":self.max_measured_bundle_bytes,
            "max_measured_evidence_bytes":self.max_measured_evidence_bytes,
            "max_measured_runtime_ms":self.max_measured_runtime_ms,
            "max_measured_peak_memory_bytes":self.max_measured_peak_memory_bytes,
            "min_measured_rows_per_second_milli":self.min_measured_rows_per_second_milli,
            "matrix_cell_hashes":list(self.matrix_cell_hashes),
            "internal_only":True,"extrapolation_used":False,"external_sla_claimed":False,
        }
    @property
    def proof_hash(self)->str: return canonical_hash(self._identity())
    def as_dict(self)->dict[str,Any]:
        return {**self._identity(),"envelope_id":self.envelope_id,
                "proof_hash":self.proof_hash,"state":"MEASURED_INTERNAL_OPERATING_ENVELOPE"}


def build_conservative_operating_envelope(
    cells: Iterable[CapacityMatrixCell],
) -> ConservativeOperatingEnvelope:
    cells=tuple(cells)
    if not cells: raise ValueError("capacity matrix cannot be empty")
    dimensions={cell.dimension for cell in cells}
    required={
        CapacityDimension.BILLING_ROWS,
        CapacityDimension.PROVIDERS,
        CapacityDimension.TENANTS,
        CapacityDimension.EVIDENCE_BYTES,
    }
    if not required.issubset(dimensions):
        raise ValueError("capacity matrix requires measured rows/providers/tenants/evidence dimensions")
    identity={
        "schema":1,
        "max_measured_billing_rows":max(c.billing_rows for c in cells),
        "max_measured_provider_count":max(c.provider_count for c in cells),
        "max_measured_tenant_count":max(c.tenant_count for c in cells),
        "max_measured_bundle_bytes":max(c.bundle_bytes for c in cells),
        "max_measured_evidence_bytes":max(c.evidence_bytes for c in cells),
        "max_measured_runtime_ms":max(c.runtime_ms for c in cells),
        "max_measured_peak_memory_bytes":max(c.peak_memory_bytes for c in cells),
        "min_measured_rows_per_second_milli":min(c.rows_per_second_milli for c in cells),
        "matrix_cell_hashes":sorted(c.proof_hash for c in cells),
        "internal_only":True,"extrapolation_used":False,"external_sla_claimed":False,
    }
    return ConservativeOperatingEnvelope(
        envelope_id="recoveryworks-operating-envelope:"+canonical_hash(identity),
        max_measured_billing_rows=identity["max_measured_billing_rows"],
        max_measured_provider_count=identity["max_measured_provider_count"],
        max_measured_tenant_count=identity["max_measured_tenant_count"],
        max_measured_bundle_bytes=identity["max_measured_bundle_bytes"],
        max_measured_evidence_bytes=identity["max_measured_evidence_bytes"],
        max_measured_runtime_ms=identity["max_measured_runtime_ms"],
        max_measured_peak_memory_bytes=identity["max_measured_peak_memory_bytes"],
        min_measured_rows_per_second_milli=identity["min_measured_rows_per_second_milli"],
        matrix_cell_hashes=tuple(identity["matrix_cell_hashes"]),
        internal_only=True,extrapolation_used=False,external_sla_claimed=False,
    )


def enforce_operating_envelope(
    envelope: ConservativeOperatingEnvelope, *,
    billing_rows: int, provider_count: int, tenant_count: int,
    evidence_bytes: int = 1,
) -> dict[str,Any]:
    requested={
        "billing_rows":billing_rows,
        "provider_count":provider_count,
        "tenant_count":tenant_count,
        "evidence_bytes":evidence_bytes,
    }
    limits={
        "billing_rows":envelope.max_measured_billing_rows,
        "provider_count":envelope.max_measured_provider_count,
        "tenant_count":envelope.max_measured_tenant_count,
        "evidence_bytes":envelope.max_measured_evidence_bytes,
    }
    exceeded=tuple(sorted(k for k,v in requested.items() if v>limits[k]))
    return {
        "admitted":not exceeded,
        "state":"WITHIN_MEASURED_ENVELOPE" if not exceeded else "ADMISSION_REJECTED_CAPACITY",
        "exceeded_dimensions":list(exceeded),
        "requested":requested,"measured_limits":limits,
        "envelope_proof_hash":envelope.proof_hash,
        "automatic_scaling_performed":False,
    }


_PROVIDER_FIXTURES = {
    "aws": ("Amazon Web Services", "EC2"),
    "azure": ("Microsoft Azure", "VirtualMachines"),
    "gcp": ("Google Cloud Platform", "ComputeEngine"),
}


def _write_provider_workload(
    root: Path,
    *,
    provider: str,
    client_id: str,
    account_id: str,
    row_count: int,
) -> tuple[dict[str, Any], int]:
    if provider not in _PROVIDER_FIXTURES:
        raise ValueError("unsupported capacity provider")
    if type(row_count) is not int or row_count <= 0:
        raise ValueError("capacity row_count must be positive")
    display, service = _PROVIDER_FIXTURES[provider]
    inputs = root / "inputs"
    private = root / "private"
    inputs.mkdir(parents=True, exist_ok=True)
    focus = inputs / "focus.csv"
    meter = inputs / "meter.csv"
    rates = inputs / "rates.csv"

    focus_lines = [
        "ChargeId,ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "ChargePeriodEnd,BilledCost,EffectiveCost,ListCost,ContractedCost,"
        "BillingCurrency,ResourceId,RegionId,SkuId,InvoiceId,ConsumedQuantity,"
        "ConsumedUnit"
    ]
    meter_lines = ["Charge_ID,Meter_Record_ID,Usage_Units"]
    for index in range(row_count):
        charge = f"{provider.upper()}-CAP-{index:08d}"
        resource = f"{provider}-r-{index:08d}"
        focus_lines.append(
            f"{charge},{display},{account_id},{service},"
            "2026-08-31T00:00:00Z,2026-09-01T00:00:00Z,"
            f"40.00,40.00,40.00,40.00,USD,{resource},region-1,"
            f"sku-{index:08d},INV-CAP,10,hours"
        )
        meter_lines.append(f"{charge},M-{index:08d},10")
    focus.write_text("\n".join(focus_lines) + "\n", encoding="utf-8")
    meter.write_text("\n".join(meter_lines) + "\n", encoding="utf-8")
    rates.write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        f"{display},{service},2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )
    evidence_bytes = sum(path.stat().st_size for path in (focus, meter, rates))
    spec = {
        "schema": 1,
        "deployment_id": f"capacity-{client_id}-{provider}",
        "tenant_id": client_id,
        "client_id": client_id,
        "currency": "USD",
        "provider": provider,
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
            "focus_csv": str(focus),
            "meter_csv": str(meter),
            "release": "capacity-matrix-fixture",
            "commit": "a" * 40,
        },
        "recoveryos": {
            "rates_csv": str(rates),
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
    return spec, evidence_bytes


def _measure_pilot_group(
    root: Path,
    *,
    dimension: CapacityDimension,
    specs: tuple[tuple[dict[str, Any], int, int], ...],
    provider_count: int,
    tenant_count: int,
) -> CapacityMatrixCell:
    if not specs:
        raise ValueError("capacity group cannot be empty")
    total_rows = sum(item[1] for item in specs)
    total_evidence_bytes = sum(item[2] for item in specs)
    proof_hashes: list[str] = []
    bundle_bytes = 0
    validated_cents = 0

    tracemalloc.start()
    started = time.perf_counter_ns()
    try:
        for index, (spec, row_count, _evidence_bytes) in enumerate(specs):
            run_root = root / f"run-{index:02d}"
            run_root.mkdir(parents=True, exist_ok=True)
            # Specs carry absolute source/output paths, while the base dir still
            # gives the tenant identity a deterministic namespace per run.
            pilot = run_local_pilot(spec, base_dir=run_root)
            proof_hashes.append(pilot.deployment_plan_hash)
            bundle_bytes += Path(pilot.export_receipt.output_path).stat().st_size
            validated_cents += pilot.continuous_result.scan.report.totals[
                "validated_cents"
            ]
        runtime_ns = time.perf_counter_ns() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    expected_validated = total_rows * 1000
    if validated_cents != expected_validated:
        raise ValueError("capacity group validated cents mismatch")
    runtime_ms = max(1, (runtime_ns + 999_999) // 1_000_000)
    throughput = total_rows * 1_000_000 // runtime_ms
    return measured_capacity_cell(
        dimension=dimension,
        billing_rows=total_rows,
        provider_count=provider_count,
        tenant_count=tenant_count,
        bundle_bytes=max(1, bundle_bytes),
        evidence_bytes=max(1, total_evidence_bytes),
        runtime_ms=runtime_ms,
        peak_memory_bytes=max(1, peak),
        rows_per_second_milli=max(1, throughput),
        evidence_proof_hashes=tuple(proof_hashes),
    )


@dataclass(frozen=True)
class MeasuredCapacityMatrix:
    matrix_id: str
    cells: tuple[CapacityMatrixCell, ...]
    operating_envelope: ConservativeOperatingEnvelope
    measured_only: bool = True
    extrapolation_used: bool = False
    external_sla_claimed: bool = False

    def __post_init__(self) -> None:
        cells = tuple(sorted(self.cells, key=lambda c: (c.dimension.value, c.proof_hash)))
        if not cells:
            raise ValueError("measured capacity matrix cannot be empty")
        object.__setattr__(self, "cells", cells)
        if not self.measured_only or self.extrapolation_used or self.external_sla_claimed:
            raise ValueError("capacity matrix must remain measured-only internal evidence")
        if self.operating_envelope.matrix_cell_hashes != tuple(
            sorted(cell.proof_hash for cell in cells)
        ):
            raise ValueError("operating envelope does not bind exact matrix cells")
        expected = "recoveryworks-measured-capacity-matrix:" + canonical_hash(
            self._identity()
        )
        if self.matrix_id != expected:
            raise ValueError("matrix_id does not bind measured capacity matrix")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "cell_hashes": [cell.proof_hash for cell in self.cells],
            "operating_envelope_proof_hash": self.operating_envelope.proof_hash,
            "measured_only": True,
            "extrapolation_used": False,
            "external_sla_claimed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "matrix_id": self.matrix_id,
            "proof_hash": self.proof_hash,
            "cells": [
                {
                    **cell._identity(),
                    "cell_id": cell.cell_id,
                    "proof_hash": cell.proof_hash,
                }
                for cell in self.cells
            ],
            "operating_envelope": self.operating_envelope.as_dict(),
            "state": "MEASURED_MULTI_AXIS_CAPACITY_MATRIX",
        }


def measure_capacity_matrix(
    root: str | Path,
    *,
    row_counts: tuple[int, ...] = (10, 25),
    provider_counts: tuple[int, ...] = (1, 2, 3),
    tenant_counts: tuple[int, ...] = (1, 2),
    evidence_row_counts: tuple[int, ...] = (10, 40),
    rows_per_provider: int = 5,
    rows_per_tenant: int = 5,
) -> MeasuredCapacityMatrix:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    providers = ("aws", "azure", "gcp")
    if not row_counts or not provider_counts or not tenant_counts or not evidence_row_counts:
        raise ValueError("capacity matrix axes cannot be empty")
    if max(provider_counts) > len(providers):
        raise ValueError("provider capacity count exceeds implemented providers")
    for values in (row_counts, provider_counts, tenant_counts, evidence_row_counts):
        if any(type(value) is not int or value <= 0 for value in values):
            raise ValueError("capacity matrix axis values must be positive integers")

    cells: list[CapacityMatrixCell] = []

    for row_count in row_counts:
        case_root = root / "rows" / str(row_count)
        spec, evidence_bytes = _write_provider_workload(
            case_root,
            provider="aws",
            client_id=f"capacity-row-{row_count}",
            account_id=f"row-{row_count}",
            row_count=row_count,
        )
        cells.append(_measure_pilot_group(
            case_root,
            dimension=CapacityDimension.BILLING_ROWS,
            specs=((spec, row_count, evidence_bytes),),
            provider_count=1,
            tenant_count=1,
        ))

    for provider_count in provider_counts:
        case_root = root / "providers" / str(provider_count)
        group = []
        shared_client = f"capacity-provider-{provider_count}"
        for provider in providers[:provider_count]:
            spec_root = case_root / provider
            spec, evidence_bytes = _write_provider_workload(
                spec_root,
                provider=provider,
                client_id=shared_client,
                account_id=f"{provider}-capacity",
                row_count=rows_per_provider,
            )
            group.append((spec, rows_per_provider, evidence_bytes))
        cells.append(_measure_pilot_group(
            case_root,
            dimension=CapacityDimension.PROVIDERS,
            specs=tuple(group),
            provider_count=provider_count,
            tenant_count=1,
        ))

    for tenant_count in tenant_counts:
        case_root = root / "tenants" / str(tenant_count)
        group = []
        for index in range(tenant_count):
            tenant_root = case_root / f"tenant-{index:02d}"
            spec, evidence_bytes = _write_provider_workload(
                tenant_root,
                provider="aws",
                client_id=f"capacity-tenant-{tenant_count}-{index}",
                account_id=f"tenant-{index}",
                row_count=rows_per_tenant,
            )
            group.append((spec, rows_per_tenant, evidence_bytes))
        cells.append(_measure_pilot_group(
            case_root,
            dimension=CapacityDimension.TENANTS,
            specs=tuple(group),
            provider_count=1,
            tenant_count=tenant_count,
        ))

    for evidence_rows in evidence_row_counts:
        case_root = root / "evidence" / str(evidence_rows)
        spec, evidence_bytes = _write_provider_workload(
            case_root,
            provider="aws",
            client_id=f"capacity-evidence-{evidence_rows}",
            account_id=f"evidence-{evidence_rows}",
            row_count=evidence_rows,
        )
        cells.append(_measure_pilot_group(
            case_root,
            dimension=CapacityDimension.EVIDENCE_BYTES,
            specs=((spec, evidence_rows, evidence_bytes),),
            provider_count=1,
            tenant_count=1,
        ))

    envelope = build_conservative_operating_envelope(cells)
    ordered = tuple(sorted(cells, key=lambda c: (c.dimension.value, c.proof_hash)))
    identity = {
        "schema": 1,
        "cell_hashes": [cell.proof_hash for cell in ordered],
        "operating_envelope_proof_hash": envelope.proof_hash,
        "measured_only": True,
        "extrapolation_used": False,
        "external_sla_claimed": False,
    }
    return MeasuredCapacityMatrix(
        matrix_id="recoveryworks-measured-capacity-matrix:"
        + canonical_hash(identity),
        cells=ordered,
        operating_envelope=envelope,
        measured_only=True,
        extrapolation_used=False,
        external_sla_claimed=False,
    )
