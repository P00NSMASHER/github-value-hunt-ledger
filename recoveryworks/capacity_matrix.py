"""Proof-bound capacity matrix and conservative internal operating envelope."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from recoveryworks.capacity_certification import CapacityMeasurement
from recoveryworks.models import canonical_hash, normalize_sha256


class CapacityDimension(str, Enum):
    BILLING_ROWS = "BILLING_ROWS"
    PROVIDERS = "PROVIDERS"
    TENANTS = "TENANTS"


@dataclass(frozen=True)
class CapacityMatrixCell:
    cell_id: str
    dimension: CapacityDimension
    billing_rows: int
    provider_count: int
    tenant_count: int
    bundle_bytes: int
    runtime_ms: int
    peak_memory_bytes: int
    rows_per_second_milli: int
    evidence_proof_hashes: tuple[str, ...]
    passed: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, CapacityDimension):
            raise ValueError("dimension must be CapacityDimension")
        for name in (
            "billing_rows","provider_count","tenant_count","bundle_bytes",
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
        "runtime_ms":measurement.runtime_ms,
        "peak_memory_bytes":measurement.peak_memory_bytes,
        "rows_per_second_milli":measurement.rows_per_second_milli,
        "evidence_proof_hashes":[measurement.proof_hash],"passed":True,
    }
    return CapacityMatrixCell(
        cell_id="recoveryworks-capacity-cell:"+canonical_hash(identity),
        dimension=CapacityDimension.BILLING_ROWS,billing_rows=measurement.row_count,
        provider_count=1,tenant_count=1,bundle_bytes=measurement.bundle_bytes,
        runtime_ms=measurement.runtime_ms,peak_memory_bytes=measurement.peak_memory_bytes,
        rows_per_second_milli=measurement.rows_per_second_milli,
        evidence_proof_hashes=(measurement.proof_hash,),passed=True,
    )


def measured_capacity_cell(
    *, dimension: CapacityDimension, billing_rows: int, provider_count: int,
    tenant_count: int, bundle_bytes: int, runtime_ms: int,
    peak_memory_bytes: int, rows_per_second_milli: int,
    evidence_proof_hashes: tuple[str,...],
) -> CapacityMatrixCell:
    identity={
        "schema":1,"dimension":dimension.value,"billing_rows":billing_rows,
        "provider_count":provider_count,"tenant_count":tenant_count,
        "bundle_bytes":bundle_bytes,"runtime_ms":runtime_ms,
        "peak_memory_bytes":peak_memory_bytes,
        "rows_per_second_milli":rows_per_second_milli,
        "evidence_proof_hashes":sorted(evidence_proof_hashes),"passed":True,
    }
    return CapacityMatrixCell(
        cell_id="recoveryworks-capacity-cell:"+canonical_hash(identity),
        dimension=dimension,billing_rows=billing_rows,provider_count=provider_count,
        tenant_count=tenant_count,bundle_bytes=bundle_bytes,runtime_ms=runtime_ms,
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
    required={CapacityDimension.BILLING_ROWS,CapacityDimension.PROVIDERS,CapacityDimension.TENANTS}
    if not required.issubset(dimensions):
        raise ValueError("capacity matrix requires measured rows/providers/tenants dimensions")
    identity={
        "schema":1,
        "max_measured_billing_rows":max(c.billing_rows for c in cells),
        "max_measured_provider_count":max(c.provider_count for c in cells),
        "max_measured_tenant_count":max(c.tenant_count for c in cells),
        "max_measured_bundle_bytes":max(c.bundle_bytes for c in cells),
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
        max_measured_runtime_ms=identity["max_measured_runtime_ms"],
        max_measured_peak_memory_bytes=identity["max_measured_peak_memory_bytes"],
        min_measured_rows_per_second_milli=identity["min_measured_rows_per_second_milli"],
        matrix_cell_hashes=tuple(identity["matrix_cell_hashes"]),
        internal_only=True,extrapolation_used=False,external_sla_claimed=False,
    )


def enforce_operating_envelope(
    envelope: ConservativeOperatingEnvelope, *,
    billing_rows: int, provider_count: int, tenant_count: int,
) -> dict[str,Any]:
    requested={"billing_rows":billing_rows,"provider_count":provider_count,"tenant_count":tenant_count}
    limits={
        "billing_rows":envelope.max_measured_billing_rows,
        "provider_count":envelope.max_measured_provider_count,
        "tenant_count":envelope.max_measured_tenant_count,
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
