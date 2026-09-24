"""Provider-specific Azure/GCP rehearsals on the shared FOCUS proof contract."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from recoveryworks.integrations.cletrics_exporter import (
    CletricsSourceArtifact,
    export_cletrics_focus_snapshot,
)
from recoveryworks.runner import run_scan360_config


_PROVIDER_SPECS = {
    "azure": {
        "display": "Azure",
        "account": "azure-billing-123",
        "service": "VirtualMachines",
        "unsupported_service": "AzureFirewall",
        "region": "eastus",
        "resource": "azure-vm-1",
        "commitment_type": "reservation",
    },
    "gcp": {
        "display": "GCP",
        "account": "gcp-billing-123",
        "service": "ComputeEngine",
        "unsupported_service": "CloudNAT",
        "region": "us-central1",
        "resource": "gcp-vm-1",
        "commitment_type": "cud",
    },
}


@dataclass(frozen=True)
class ProviderRehearsalResult:
    provider: str
    base_rate_validated_cents: int
    discount_validated_cents: int
    commitment_validated_cents: int
    savings_opportunity_cents: int
    base_exception_codes: tuple[str, ...]
    accepted: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_rate_validated_cents": self.base_rate_validated_cents,
            "discount_validated_cents": self.discount_validated_cents,
            "commitment_validated_cents": self.commitment_validated_cents,
            "savings_opportunity_cents": self.savings_opportunity_cents,
            "base_exception_codes": list(self.base_exception_codes),
            "accepted": self.accepted,
        }


def _source(path: Path, provider: str, kind: str) -> CletricsSourceArtifact:
    return CletricsSourceArtifact(
        path=path,
        kind=kind,
        locator=f"synthetic-{provider}://{path.name}",
        acquired_at="2026-09-01T12:00:00Z",
    )


def _write_focus(
    path: Path,
    *,
    spec: dict[str, str],
    rows: list[tuple[str, str, str, str]],
) -> None:
    body = [
        "ChargeId,ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "ChargePeriodEnd,BilledCost,EffectiveCost,ListCost,ContractedCost,"
        "BillingCurrency,ResourceId,RegionId,SkuId,InvoiceId,ConsumedQuantity,"
        "ConsumedUnit"
    ]
    for index, (charge_id, service, billed, resource) in enumerate(rows, start=1):
        body.append(
            f"{charge_id},{spec['display']},{spec['account']},{service},"
            "2026-08-31T00:00:00Z,2026-09-01T00:00:00Z,"
            f"{billed},{billed},{billed},{billed},USD,{resource},"
            f"{spec['region']},sku-{index},INV-{spec['display']}-{index},10,hours"
        )
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _write_meter(
    path: Path,
    rows: list[tuple[str, str, str]],
) -> None:
    body = ["Charge_ID,Meter_Record_ID,Usage_Units"]
    for charge_id, meter_id, units in rows:
        body.append(f"{charge_id},{meter_id},{units}")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _bundle(
    root: Path,
    provider: str,
    name: str,
    *,
    focus_rows: list[tuple[str, str, str, str]],
    meter_rows: list[tuple[str, str, str]],
    include_savings: bool = False,
) -> Path:
    spec = _PROVIDER_SPECS[provider]
    focus = root / f"{provider}-{name}-focus.csv"
    meter = root / f"{provider}-{name}-meter.csv"
    _write_focus(focus, spec=spec, rows=focus_rows)
    _write_meter(meter, meter_rows)
    kwargs: dict[str, Any] = {}
    if include_savings:
        savings = root / f"{provider}-{name}-savings.csv"
        savings.write_text(
            "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,"
            "Region,Savings_Category,Estimated_Savings,Confidence,Recommendation,"
            "Remediation_Action\n"
            f"{provider.upper()}-S-1,2026-09-01T03:00:00Z,{provider},"
            f"{spec['account']},{spec['service']},{spec['resource']},{spec['region']},"
            "rightsize,50.00,0.90,Review utilization and resize,resize_instance\n",
            encoding="utf-8",
        )
        kwargs["savings"] = _source(savings, provider, "cletrics_savings_output")

    output = root / f"{provider}-{name}.zip"
    export_cletrics_focus_snapshot(
        output_path=output,
        client_id=f"client-{provider}-rehearsal",
        focus=_source(focus, provider, "cletrics_focus_export"),
        meter=_source(meter, provider, "cletrics_independent_meter_export"),
        cletrics_release=f"{provider}-rehearsal",
        cletrics_commit="e" * 40,
        exported_at="2026-09-01T04:00:00Z",
        period_start="2026-08-01",
        period_end="2026-08-31",
        **kwargs,
    )
    return output


def run_provider_rehearsal(
    root: str | Path,
    provider: str,
) -> ProviderRehearsalResult:
    provider = provider.lower()
    if provider not in _PROVIDER_SPECS:
        raise ValueError("provider rehearsal supports azure or gcp")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    spec = _PROVIDER_SPECS[provider]
    rates = root / f"{provider}-rates.csv"
    rates.write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        f"{spec['display']},{spec['service']},2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )

    base_id = f"{provider.upper()}-BASE-1"
    unsupported_id = f"{provider.upper()}-UNSUPPORTED-1"
    base_bundle = _bundle(
        root,
        provider,
        "base",
        focus_rows=[
            (base_id, spec["service"], "40.00", spec["resource"]),
            (
                unsupported_id,
                spec["unsupported_service"],
                "100.00",
                f"{provider}-unsupported-1",
            ),
        ],
        meter_rows=[
            (base_id, "M-BASE", "10"),
            (unsupported_id, "M-UNSUPPORTED", "10"),
        ],
        include_savings=True,
    )
    base = run_scan360_config(
        {
            "client_id": f"client-{provider}-rehearsal",
            "currency": "USD",
            "cloud": {
                "cletrics_bundle": base_bundle.name,
                "rates_csv": rates.name,
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
            },
        },
        state_path=root / f"{provider}-base-ledger.json",
        base_dir=root,
    )

    discount_id = f"{provider.upper()}-DISCOUNT-1"
    discount_bundle = _bundle(
        root,
        provider,
        "discount",
        focus_rows=[
            (discount_id, spec["service"], "40.00", f"{provider}-discount-1")
        ],
        meter_rows=[(discount_id, "M-DISCOUNT", "10")],
    )
    discounts = root / f"{provider}-discounts.csv"
    discounts.write_text(
        "Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,"
        "Discount_BPS,Applies_To\n"
        f"{spec['display']},{spec['account']},{spec['service']},"
        "2026-01-01,,1000,VARIABLE\n",
        encoding="utf-8",
    )
    discount = run_scan360_config(
        {
            "client_id": f"client-{provider}-rehearsal",
            "currency": "USD",
            "cloud_discount": {
                "cletrics_bundle": discount_bundle.name,
                "rates_csv": rates.name,
                "discounts_csv": discounts.name,
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
                "discount_source_verified": True,
            },
        },
        state_path=root / f"{provider}-discount-ledger.json",
        base_dir=root,
    )

    commitment_id = f"{provider.upper()}-COMMITMENT-1"
    commitment_bundle = _bundle(
        root,
        provider,
        "commitment",
        focus_rows=[
            (commitment_id, spec["service"], "40.00", f"{provider}-commitment-1")
        ],
        meter_rows=[(commitment_id, "M-COMMITMENT", "10")],
    )
    commitments = root / f"{provider}-commitments.csv"
    commitments.write_text(
        "Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,"
        "Commitment_Type,Committed_Unit_Rate\n"
        f"{spec['display']},{spec['account']},{spec['service']},2026-01-01,,"
        f"{spec['commitment_type']},1.00\n",
        encoding="utf-8",
    )
    allocations = root / f"{provider}-allocations.csv"
    allocations.write_text(
        "Charge_ID,Allocation_ID,Entitled_Units\n"
        f"{commitment_id},ALLOC-{provider.upper()}-1,6\n",
        encoding="utf-8",
    )
    commitment = run_scan360_config(
        {
            "client_id": f"client-{provider}-rehearsal",
            "currency": "USD",
            "cloud_commitment": {
                "cletrics_bundle": commitment_bundle.name,
                "rates_csv": rates.name,
                "commitments_csv": commitments.name,
                "allocations_csv": allocations.name,
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
                "commitment_source_verified": True,
                "allocation_source_verified": True,
            },
        },
        state_path=root / f"{provider}-commitment-ledger.json",
        base_dir=root,
    )

    savings = base.cloud_savings
    if savings is None:
        raise AssertionError("provider rehearsal expected savings surface")
    exception_codes = tuple(sorted(item["code"] for item in base.exceptions))
    result = ProviderRehearsalResult(
        provider=provider,
        base_rate_validated_cents=base.report.totals["validated_cents"],
        discount_validated_cents=discount.report.totals["validated_cents"],
        commitment_validated_cents=commitment.report.totals["validated_cents"],
        savings_opportunity_cents=savings.estimated_savings_opportunity_cents,
        base_exception_codes=exception_codes,
        accepted=(
            base.report.totals["validated_cents"] == 1000
            and discount.report.totals["validated_cents"] == 1200
            and commitment.report.totals["validated_cents"] == 1600
            and savings.estimated_savings_opportunity_cents == 5000
            and exception_codes == ("NO_CONTRACT_RATE",)
            and base.report.totals["cases"] == 1
        ),
    )
    if not result.accepted:
        raise AssertionError(
            f"{provider} rehearsal acceptance failed: {result.as_dict()}"
        )
    return result


def run_azure_cletrics_rehearsal(root: str | Path) -> ProviderRehearsalResult:
    return run_provider_rehearsal(root, "azure")


def run_gcp_cletrics_rehearsal(root: str | Path) -> ProviderRehearsalResult:
    return run_provider_rehearsal(root, "gcp")
