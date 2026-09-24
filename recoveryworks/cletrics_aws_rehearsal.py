"""Authorized AWS-shaped rehearsal for Cletrics -> CloudRecovery -> RecoveryOS.

This is synthetic data only. It deliberately exercises three independent
recovery theories (base contracted rate, contractual discount, commitment
benefit) plus non-money anomaly/reconciliation/savings signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from recoveryworks.integrations.cletrics_exporter import (
    CletricsSourceArtifact,
    export_cletrics_focus_snapshot,
)
from recoveryworks.runner import run_scan360_config


@dataclass(frozen=True)
class AwsCletricsRehearsalResult:
    base_rate_validated_cents: int
    discount_validated_cents: int
    commitment_validated_cents: int
    savings_opportunity_cents: int
    anomaly_exposure_cents: int
    reconciliation_drift_cents: int
    base_exception_codes: tuple[str, ...]
    accepted: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_rate_validated_cents": self.base_rate_validated_cents,
            "discount_validated_cents": self.discount_validated_cents,
            "commitment_validated_cents": self.commitment_validated_cents,
            "savings_opportunity_cents": self.savings_opportunity_cents,
            "anomaly_exposure_cents": self.anomaly_exposure_cents,
            "reconciliation_drift_cents": self.reconciliation_drift_cents,
            "base_exception_codes": list(self.base_exception_codes),
            "accepted": self.accepted,
        }


def _source(path: Path, kind: str) -> CletricsSourceArtifact:
    return CletricsSourceArtifact(
        path=path,
        kind=kind,
        locator=f"synthetic-aws://{path.name}",
        acquired_at="2026-09-01T12:00:00Z",
    )


def _write_focus(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    # resource, service, billed cost, sku
    body = [
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "ChargePeriodEnd,BilledCost,EffectiveCost,ListCost,ContractedCost,"
        "BillingCurrency,ResourceId,RegionId,SkuId,InvoiceId,ConsumedQuantity,"
        "ConsumedUnit"
    ]
    for index, (resource, service, billed, sku) in enumerate(rows, start=1):
        body.append(
            "AWS,payer-aws-123,"
            f"{service},2026-08-31T00:00:00Z,2026-09-01T00:00:00Z,"
            f"{billed},{billed},{billed},{billed},USD,{resource},us-east-1,"
            f"{sku},INV-AWS-2026-08-{index},10,hours"
        )
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _write_meter(path: Path, rows: list[tuple[str, str, str]]) -> None:
    # resource, service, units
    body = ["Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate"]
    for index, (resource, service, units) in enumerate(rows, start=1):
        body.append(f"M-{index},{units},{resource},{service},2026-08-31")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _export_bundle(
    root: Path,
    *,
    name: str,
    focus_rows: list[tuple[str, str, str, str]],
    meter_rows: list[tuple[str, str, str]],
    include_signals: bool = False,
) -> Path:
    focus = root / f"{name}-focus.csv"
    meter = root / f"{name}-meter.csv"
    _write_focus(focus, focus_rows)
    _write_meter(meter, meter_rows)

    kwargs: dict[str, Any] = {}
    if include_signals:
        anomaly = root / f"{name}-anomaly.csv"
        anomaly.write_text(
            "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,"
            "Region,Severity,Detection_Method,Metric_Name,Estimated_Cost_Impact,"
            "Confidence\n"
            "AWS-A-1,2026-09-01T01:00:00Z,aws,payer-aws-123,EC2,i-rate,"
            "us-east-1,HIGH,zscore,daily_cost,5000.00,0.95\n"
            "AWS-A-2,2026-09-01T01:05:00Z,aws,payer-aws-123,NATGateway,nat-1,"
            "us-east-1,MEDIUM,seasonal,daily_cost,1200.00,0.80\n",
            encoding="utf-8",
        )
        reconciliation = root / f"{name}-reconciliation.csv"
        reconciliation.write_text(
            "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Estimated_Cost,"
            "Actual_Cost,Error_Pct,Drift_Direction\n"
            "AWS-R-1,2026-09-01T02:00:00Z,aws,payer-aws-123,EC2,30.00,40.00,"
            "33.33,over\n",
            encoding="utf-8",
        )
        savings = root / f"{name}-savings.csv"
        savings.write_text(
            "Signal_ID,Detected_At,Provider,Account_ID,Service_ID,Resource_ID,"
            "Region,Savings_Category,Estimated_Savings,Confidence,Recommendation,"
            "Remediation_Action\n"
            "AWS-S-1,2026-09-01T03:00:00Z,aws,payer-aws-123,EC2,i-rate,"
            "us-east-1,rightsize,250.00,0.90,Downsize after utilization review,"
            "resize_instance\n"
            "AWS-S-2,2026-09-01T03:05:00Z,aws,payer-aws-123,NATGateway,nat-1,"
            "us-east-1,idle_resource,100.00,0.85,Remove only after dependency review,"
            "remove_idle_resource\n",
            encoding="utf-8",
        )
        kwargs = {
            "anomaly": _source(anomaly, "cletrics_anomaly_output"),
            "reconciliation": _source(
                reconciliation, "cletrics_reconciliation_output"
            ),
            "savings": _source(savings, "cletrics_savings_output"),
        }

    output = root / f"{name}.zip"
    export_cletrics_focus_snapshot(
        output_path=output,
        client_id="client-aws-rehearsal",
        focus=_source(focus, "cletrics_focus_export"),
        meter=_source(meter, "cletrics_independent_meter_export"),
        cletrics_release="aws-rehearsal",
        cletrics_commit="d" * 40,
        exported_at="2026-09-01T04:00:00Z",
        period_start="2026-08-01",
        period_end="2026-08-31",
        **kwargs,
    )
    return output


def _write_rates(path: Path) -> None:
    path.write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "AWS,EC2,2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )


def run_aws_cletrics_rehearsal(root: str | Path) -> AwsCletricsRehearsalResult:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rates = root / "rates.csv"
    _write_rates(rates)

    base_bundle = _export_bundle(
        root,
        name="base",
        focus_rows=[
            ("i-rate", "EC2", "40.00", "m7i.2xlarge"),
            ("nat-1", "NATGateway", "100.00", "nat-gateway"),
        ],
        meter_rows=[
            ("i-rate", "EC2", "10"),
            ("nat-1", "NATGateway", "10"),
        ],
        include_signals=True,
    )
    base = run_scan360_config(
        {
            "client_id": "client-aws-rehearsal",
            "currency": "USD",
            "cloud": {
                "cletrics_bundle": base_bundle.name,
                "rates_csv": rates.name,
                "charge_source_verified": True,
                "meter_source_verified": True,
                "rate_source_verified": True,
            },
        },
        state_path=root / "base-ledger.json",
        base_dir=root,
    )

    discount_bundle = _export_bundle(
        root,
        name="discount",
        focus_rows=[("i-discount", "EC2", "40.00", "m7i.2xlarge")],
        meter_rows=[("i-discount", "EC2", "10")],
    )
    discounts = root / "discounts.csv"
    discounts.write_text(
        "Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,"
        "Discount_BPS,Applies_To\n"
        "AWS,payer-aws-123,EC2,2026-01-01,,1000,VARIABLE\n",
        encoding="utf-8",
    )
    discount = run_scan360_config(
        {
            "client_id": "client-aws-rehearsal",
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
        state_path=root / "discount-ledger.json",
        base_dir=root,
    )

    commitment_bundle = _export_bundle(
        root,
        name="commitment",
        focus_rows=[("i-commit", "EC2", "40.00", "m7i.2xlarge")],
        meter_rows=[("i-commit", "EC2", "10")],
    )
    commitments = root / "commitments.csv"
    commitments.write_text(
        "Counterparty,Account_ID,Service_ID,Effective_From,Effective_To,"
        "Commitment_Type,Committed_Unit_Rate\n"
        "AWS,payer-aws-123,EC2,2026-01-01,,savings_plan,1.00\n",
        encoding="utf-8",
    )
    allocations = root / "allocations.csv"
    allocations.write_text(
        "Charge_ID,Allocation_ID,Entitled_Units\n",
        encoding="utf-8",
    )

    # The exporter deliberately derives content-addressed charge IDs when the
    # FOCUS source has no provider ChargeId. Read the normalized bundle once so
    # the independently reviewed allocation can bind the exact charge.
    from recoveryworks.integrations.cletrics import load_cletrics_bundle

    loaded_commitment = load_cletrics_bundle(commitment_bundle)
    commitment_charge_id = loaded_commitment.charges[0].charge_id
    allocations.write_text(
        "Charge_ID,Allocation_ID,Entitled_Units\n"
        f"{commitment_charge_id},ALLOC-AWS-1,6\n",
        encoding="utf-8",
    )
    commitment = run_scan360_config(
        {
            "client_id": "client-aws-rehearsal",
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
        state_path=root / "commitment-ledger.json",
        base_dir=root,
    )

    base_savings = base.cloud_savings
    if base_savings is None:
        raise AssertionError("AWS rehearsal expected a savings surface")

    exception_codes = tuple(sorted(issue["code"] for issue in base.exceptions))
    result = AwsCletricsRehearsalResult(
        base_rate_validated_cents=base.report.totals["validated_cents"],
        discount_validated_cents=discount.report.totals["validated_cents"],
        commitment_validated_cents=commitment.report.totals["validated_cents"],
        savings_opportunity_cents=base_savings.estimated_savings_opportunity_cents,
        anomaly_exposure_cents=base_savings.estimated_anomaly_exposure_cents,
        reconciliation_drift_cents=base_savings.reconciliation_drift_cents,
        base_exception_codes=exception_codes,
        accepted=(
            base.report.totals["validated_cents"] == 1000
            and discount.report.totals["validated_cents"] == 1200
            and commitment.report.totals["validated_cents"] == 1600
            and base_savings.estimated_savings_opportunity_cents == 35000
            and base_savings.estimated_anomaly_exposure_cents == 620000
            and base_savings.reconciliation_drift_cents == 1000
            and exception_codes == ("NO_CONTRACT_RATE",)
            and base.report.totals["cases"] == 1
        ),
    )
    if not result.accepted:
        raise AssertionError(f"AWS Cletrics rehearsal acceptance failed: {result.as_dict()}")
    return result
