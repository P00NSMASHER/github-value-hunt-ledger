"""One-command local pilot launcher for Cletrics -> RecoveryOS.

This launcher executes only local file transformations and RecoveryOS
calculation/reporting. It does not provision infrastructure, call provider APIs,
start cloud remediation, contact counterparties, or perform external actions.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.cloud_provider import canonical_cloud_provider
from recoveryworks.integrations.cletrics_continuous import (
    ContinuousCletricsResult,
    run_continuous_cletrics_scan,
)
from recoveryworks.integrations.cletrics_exporter import (
    CletricsExportReceipt,
    CletricsSourceArtifact,
    export_cletrics_focus_snapshot,
)
from recoveryworks.cloud_assurance_report import (
    build_cloud_assurance_report,
    write_cloud_assurance_report,
)
from recoveryworks.pilot_deployment import (
    PilotDeploymentPlan,
    build_pilot_deployment_plan,
    load_pilot_spec,
)
from recoveryworks.store import LocalBundleStore
from recoveryworks.private_io import (
    atomic_private_write,
    private_permissions_verified,
)


@dataclass(frozen=True)
class PilotRunResult:
    deployment_plan_hash: str
    export_receipt: CletricsExportReceipt
    continuous_result: ContinuousCletricsResult
    report_path: str
    private_paths: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "deployment_plan_hash": self.deployment_plan_hash,
            "export_receipt": self.export_receipt.as_dict(),
            "continuous_result": self.continuous_result.as_dict(),
            "report_path": self.report_path,
            "private_paths": list(self.private_paths),
        }


def _mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _bool_setting(mapping: Mapping[str, Any], key: str) -> bool:
    value = mapping.get(key, False)
    if type(value) is not bool:
        raise ValueError(f"{key} must be boolean")
    return value


def _source(
    base: Path,
    value: str,
    *,
    kind: str,
    acquired_at: str,
) -> CletricsSourceArtifact:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return CletricsSourceArtifact(
        path=path,
        kind=kind,
        locator=f"file://{path.name}",
        acquired_at=acquired_at,
    )


def _optional_source(
    base: Path,
    value: Any,
    *,
    kind: str,
    acquired_at: str,
) -> CletricsSourceArtifact | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{kind} path must be a string")
    return _source(base, value, kind=kind, acquired_at=acquired_at)


def run_local_pilot(
    spec: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> PilotRunResult:
    """Run the authorized local pilot pipeline from a validated spec."""
    base = Path(base_dir).resolve()
    plan: PilotDeploymentPlan = build_pilot_deployment_plan(spec, base_dir=base)

    period = _mapping("period", spec.get("period"))
    cletrics = _mapping("cletrics", spec.get("cletrics"))
    recoveryos = _mapping("recoveryos", spec.get("recoveryos"))
    verification = recoveryos.get("verification", {})
    if verification is None:
        verification = {}
    verification = _mapping("recoveryos.verification", verification)

    exported_at = str(period["exported_at"])
    export_receipt = export_cletrics_focus_snapshot(
        output_path=plan.bundle_path,
        client_id=plan.client_id,
        focus=_source(
            base,
            str(cletrics["focus_csv"]),
            kind="cletrics_focus_export",
            acquired_at=exported_at,
        ),
        meter=_source(
            base,
            str(cletrics["meter_csv"]),
            kind="cletrics_independent_meter_export",
            acquired_at=exported_at,
        ),
        anomaly=_optional_source(
            base,
            cletrics.get("anomaly_csv"),
            kind="cletrics_anomaly_output",
            acquired_at=exported_at,
        ),
        reconciliation=_optional_source(
            base,
            cletrics.get("reconciliation_csv"),
            kind="cletrics_reconciliation_output",
            acquired_at=exported_at,
        ),
        savings=_optional_source(
            base,
            cletrics.get("savings_csv"),
            kind="cletrics_savings_output",
            acquired_at=exported_at,
        ),
        cletrics_release=str(cletrics["release"]),
        cletrics_commit=cletrics.get("commit"),
        cletrics_image_digest=cletrics.get("image_digest"),
        exported_at=exported_at,
        period_start=str(period["start"]),
        period_end=str(period["end"]),
    )

    if canonical_cloud_provider(export_receipt.provider) != plan.provider:
        raise ValueError(
            "FOCUS provider does not match declared pilot provider: "
            f"{export_receipt.provider!r} != {plan.provider!r}"
        )

    bundle_path = Path(plan.bundle_path)
    bundle_raw = bundle_path.read_bytes()
    atomic_private_write(bundle_path, bundle_raw)
    if not private_permissions_verified(bundle_path):
        raise PermissionError("pilot evidence bundle is not private")

    rates_path = Path(str(recoveryos["rates_csv"]))
    if not rates_path.is_absolute():
        rates_path = base / rates_path

    currency = str(spec.get("currency") or "USD").strip().upper()
    scan_config = {
        "client_id": plan.client_id,
        "currency": currency,
        "cloud": {
            "cletrics_bundle": plan.bundle_path,
            "rates_csv": str(rates_path),
            "charge_source_verified": _bool_setting(
                verification, "charge_source_verified"
            ),
            "meter_source_verified": _bool_setting(
                verification, "meter_source_verified"
            ),
            "rate_source_verified": _bool_setting(
                verification, "rate_source_verified"
            ),
        },
        "cloud_remediation": {
            "enabled": False,
            "execute": False,
        },
    }
    result = run_continuous_cletrics_scan(
        scan_config,
        state_path=plan.ledger_path,
        registry_path=plan.receipt_registry_path,
        base_dir=base,
    )

    ledger = LocalBundleStore(plan.ledger_path).load()
    if ledger is None:
        raise AssertionError("pilot run did not persist a RecoveryOS ledger")
    assurance = build_cloud_assurance_report(
        result=result,
        ledger=ledger,
    )
    report_path = Path(plan.report_path)
    markdown_path = report_path.with_suffix(".md")
    write_cloud_assurance_report(
        assurance,
        json_path=report_path,
        markdown_path=markdown_path,
    )

    private_paths = tuple(
        str(path)
        for path in (
            Path(plan.bundle_path),
            Path(plan.ledger_path),
            Path(plan.receipt_registry_path),
            report_path,
            markdown_path,
        )
    )
    for value in private_paths:
        if not private_permissions_verified(Path(value)):
            raise PermissionError(f"pilot private permissions missing: {value}")

    return PilotRunResult(
        deployment_plan_hash=plan.proof_hash,
        export_receipt=export_receipt,
        continuous_result=result,
        report_path=plan.report_path,
        private_paths=private_paths,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the local read-only Cletrics + RecoveryOS pilot pipeline."
    )
    parser.add_argument("--spec", required=True)
    parser.add_argument("--base-dir", default=".")
    args = parser.parse_args(argv)
    spec = load_pilot_spec(args.spec)
    result = run_local_pilot(spec, base_dir=args.base_dir)
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
