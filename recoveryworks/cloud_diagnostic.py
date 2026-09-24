"""Authorized real-account cloud diagnostic intake and local execution path.

This module is designed for customer-provided or otherwise explicitly
authorized exports. It preflights authorization and FOCUS scope before creating
any RecoveryOS state, then invokes the existing local read-only pilot pipeline.
It does not connect to AWS, obtain credentials, or perform external actions.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import (
    canonical_hash,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_runner import PilotRunResult, run_local_pilot
from recoveryworks.private_io import atomic_private_write


_REQUIRED_PURPOSES = {
    "BILLING_RECOVERY_DIAGNOSTIC",
    "SAVINGS_ANALYSIS",
}


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _date(name: str, value: Any) -> str:
    raw = _text(name, value)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class CustomerDiagnosticAuthorization:
    authorization_id: str
    client_id: str
    provider: str
    billing_account_id: str
    period_start: str
    period_end: str
    customer_actor_id: str
    authorized_at: str
    expires_at: str
    allowed_purposes: tuple[str, ...]
    source_hash: str
    source_locator: str
    credentials_embedded: bool = False
    external_actions_allowed: bool = False
    remediation_allowed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "authorization_id",
            "client_id",
            "provider",
            "billing_account_id",
            "customer_actor_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(self, "provider", self.provider.lower())
        start = _date("period_start", self.period_start)
        end = _date("period_end", self.period_end)
        if end < start:
            raise ValueError("authorization period_end cannot predate period_start")
        object.__setattr__(self, "period_start", start)
        object.__setattr__(self, "period_end", end)
        object.__setattr__(
            self,
            "authorized_at",
            normalize_utc_timestamp("authorized_at", self.authorized_at),
        )
        object.__setattr__(
            self,
            "expires_at",
            normalize_utc_timestamp("expires_at", self.expires_at),
        )
        if _instant(self.expires_at) <= _instant(self.authorized_at):
            raise ValueError("diagnostic authorization expiry must follow authorization")
        purposes = tuple(sorted({_text("allowed_purpose", value) for value in self.allowed_purposes}))
        if not _REQUIRED_PURPOSES.issubset(purposes):
            raise ValueError(
                "diagnostic authorization must include billing recovery and savings analysis"
            )
        object.__setattr__(self, "allowed_purposes", purposes)
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if self.credentials_embedded:
            raise ValueError("diagnostic authorization must not embed credentials")
        if self.external_actions_allowed:
            raise ValueError("diagnostic authorization must not allow external actions")
        if self.remediation_allowed:
            raise ValueError("diagnostic authorization must not allow remediation")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            **asdict(self),
            "allowed_purposes": list(self.allowed_purposes),
        })


@dataclass(frozen=True)
class CloudDiagnosticIntakeReceipt:
    diagnostic_id: str
    authorization_proof_hash: str
    client_id: str
    provider: str
    billing_account_id: str
    period_start: str
    period_end: str
    input_hashes: Mapping[str, str]
    pilot_deployment_plan_hash: str
    pilot_report_path: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "authorization_proof_hash",
            normalize_sha256(
                "authorization_proof_hash", self.authorization_proof_hash
            ),
        )
        object.__setattr__(
            self,
            "pilot_deployment_plan_hash",
            normalize_sha256(
                "pilot_deployment_plan_hash", self.pilot_deployment_plan_hash
            ),
        )
        for name in (
            "diagnostic_id",
            "client_id",
            "provider",
            "billing_account_id",
            "pilot_report_path",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        normalized_hashes: dict[str, str] = {}
        for key, value in self.input_hashes.items():
            normalized_hashes[str(key)] = normalize_sha256(
                f"input_hashes.{key}", value
            )
        object.__setattr__(self, "input_hashes", normalized_hashes)

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "diagnostic_id": self.diagnostic_id,
            "authorization_proof_hash": self.authorization_proof_hash,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "input_hashes": dict(sorted(self.input_hashes.items())),
            "pilot_deployment_plan_hash": self.pilot_deployment_plan_hash,
            "pilot_report_path": self.pilot_report_path,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "authorization_proof_hash": self.authorization_proof_hash,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "input_hashes": dict(sorted(self.input_hashes.items())),
            "pilot_deployment_plan_hash": self.pilot_deployment_plan_hash,
            "pilot_report_path": self.pilot_report_path,
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class AuthorizedCloudDiagnosticResult:
    authorization: CustomerDiagnosticAuthorization
    intake_receipt: CloudDiagnosticIntakeReceipt
    pilot: PilotRunResult
    intake_receipt_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "authorization_proof_hash": self.authorization.proof_hash,
            "intake_receipt": self.intake_receipt.as_dict(),
            "pilot": self.pilot.as_dict(),
            "intake_receipt_path": self.intake_receipt_path,
        }


def _resolve(base: Path, value: Any, *, name: str) -> Path:
    raw = Path(_text(name, value))
    path = raw if raw.is_absolute() else base / raw
    if not path.is_file():
        raise ValueError(f"{name} does not exist as a file: {path}")
    return path


def _preflight_focus(
    path: Path,
    *,
    authorization: CustomerDiagnosticAuthorization,
    currency: str,
) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "ProviderName",
            "BillingAccountId",
            "ChargePeriodStart",
            "BillingCurrency",
        }
        fields = set(reader.fieldnames or ())
        missing = sorted(required - fields)
        if missing:
            raise ValueError(
                "FOCUS preflight missing required columns: " + ", ".join(missing)
            )
        rows = list(reader)
    if not rows:
        raise ValueError("FOCUS preflight requires at least one billing row")
    for row_number, row in enumerate(rows, start=2):
        provider = str(row.get("ProviderName") or "").strip().lower()
        account = str(row.get("BillingAccountId") or "").strip()
        row_currency = str(row.get("BillingCurrency") or "").strip().upper()
        service_date = _date(
            f"FOCUS row {row_number} ChargePeriodStart",
            str(row.get("ChargePeriodStart") or "")[:10],
        )
        if provider != authorization.provider:
            raise ValueError(f"FOCUS row {row_number} provider is outside authorization")
        if account != authorization.billing_account_id:
            raise ValueError(
                f"FOCUS row {row_number} billing account is outside authorization"
            )
        if row_currency != currency:
            raise ValueError(f"FOCUS row {row_number} currency does not match diagnostic")
        if not authorization.period_start <= service_date <= authorization.period_end:
            raise ValueError(
                f"FOCUS row {row_number} service date is outside authorized period"
            )


def authorization_from_intake(raw: Mapping[str, Any]) -> CustomerDiagnosticAuthorization:
    authorization = raw.get("authorization")
    if not isinstance(authorization, Mapping):
        raise ValueError("authorization must be an object")
    return CustomerDiagnosticAuthorization(
        authorization_id=_text(
            "authorization.authorization_id", authorization.get("authorization_id")
        ),
        client_id=_text("client_id", raw.get("client_id")),
        provider=_text("provider", raw.get("provider")),
        billing_account_id=_text(
            "billing_account_id", raw.get("billing_account_id")
        ),
        period_start=_date(
            "period.start", (raw.get("period") or {}).get("start")
            if isinstance(raw.get("period"), Mapping)
            else None,
        ),
        period_end=_date(
            "period.end", (raw.get("period") or {}).get("end")
            if isinstance(raw.get("period"), Mapping)
            else None,
        ),
        customer_actor_id=_text(
            "authorization.customer_actor_id", authorization.get("customer_actor_id")
        ),
        authorized_at=_text(
            "authorization.authorized_at", authorization.get("authorized_at")
        ),
        expires_at=_text(
            "authorization.expires_at", authorization.get("expires_at")
        ),
        allowed_purposes=tuple(authorization.get("allowed_purposes") or ()),
        source_hash=_text(
            "authorization.source_hash", authorization.get("source_hash")
        ),
        source_locator=_text(
            "authorization.source_locator", authorization.get("source_locator")
        ),
        credentials_embedded=bool(authorization.get("credentials_embedded", False)),
        external_actions_allowed=bool(
            authorization.get("external_actions_allowed", False)
        ),
        remediation_allowed=bool(authorization.get("remediation_allowed", False)),
    )


def run_authorized_cloud_diagnostic(
    intake: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
    run_at: str,
) -> AuthorizedCloudDiagnosticResult:
    if intake.get("schema") != 1:
        raise ValueError("unsupported diagnostic intake schema")
    base = Path(base_dir).resolve()
    authorization = authorization_from_intake(intake)
    checked = normalize_utc_timestamp("run_at", run_at)
    if _instant(checked) < _instant(authorization.authorized_at):
        raise ValueError("diagnostic run cannot predate customer authorization")
    if _instant(checked) > _instant(authorization.expires_at):
        raise ValueError("customer diagnostic authorization has expired")

    currency = _text("currency", intake.get("currency", "USD")).upper()
    inputs = intake.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be an object")
    focus = _resolve(base, inputs.get("focus_csv"), name="inputs.focus_csv")
    meter = _resolve(base, inputs.get("meter_csv"), name="inputs.meter_csv")
    rates = _resolve(base, inputs.get("rates_csv"), name="inputs.rates_csv")
    _preflight_focus(
        focus,
        authorization=authorization,
        currency=currency,
    )

    optional_paths: dict[str, Path] = {}
    for key in ("anomaly_csv", "reconciliation_csv", "savings_csv"):
        value = inputs.get(key)
        if value:
            optional_paths[key] = _resolve(
                base, value, name=f"inputs.{key}"
            )

    verification = intake.get("verification", {})
    if not isinstance(verification, Mapping):
        raise ValueError("verification must be an object")
    for key in (
        "charge_source_verified",
        "meter_source_verified",
        "rate_source_verified",
    ):
        if type(verification.get(key, False)) is not bool:
            raise ValueError(f"verification.{key} must be boolean")

    diagnostic_id = _text("diagnostic_id", intake.get("diagnostic_id"))
    outputs = intake.get("outputs", {})
    if not isinstance(outputs, Mapping):
        raise ValueError("outputs must be an object")
    private_root_value = outputs.get(
        "private_root", f"private/diagnostics/{diagnostic_id}"
    )
    private_root = Path(_text("outputs.private_root", private_root_value))
    if not private_root.is_absolute():
        private_root = base / private_root

    cletrics = intake.get("cletrics")
    if not isinstance(cletrics, Mapping):
        raise ValueError("cletrics must be an object")
    pilot_spec: dict[str, Any] = {
        "schema": 1,
        "deployment_id": f"diagnostic:{diagnostic_id}",
        "client_id": authorization.client_id,
        "currency": currency,
        "provider": authorization.provider,
        "security": {
            "cloud_access_mode": "READ_ONLY",
            "recoveryos_provider_write_credentials": False,
            "remediation_execution_enabled": False,
            "external_actions_enabled": False,
            "private_state_required": True,
        },
        "period": {
            "start": authorization.period_start,
            "end": authorization.period_end,
            "exported_at": _text(
                "cletrics.exported_at", cletrics.get("exported_at")
            ),
        },
        "cletrics": {
            "focus_csv": str(focus),
            "meter_csv": str(meter),
            "release": _text("cletrics.release", cletrics.get("release")),
            "commit": cletrics.get("commit"),
            "image_digest": cletrics.get("image_digest"),
        },
        "recoveryos": {
            "rates_csv": str(rates),
            "verification": {
                "charge_source_verified": verification.get(
                    "charge_source_verified", False
                ),
                "meter_source_verified": verification.get(
                    "meter_source_verified", False
                ),
                "rate_source_verified": verification.get(
                    "rate_source_verified", False
                ),
            },
            "bundle_path": str(private_root / "cletrics-bundle.zip"),
            "ledger_path": str(private_root / "ledger.json"),
            "receipt_registry_path": str(private_root / "receipts.json"),
            "report_path": str(private_root / "cloud-assurance.json"),
        },
    }
    for key, path in optional_paths.items():
        pilot_spec["cletrics"][key] = str(path)

    pilot = run_local_pilot(pilot_spec, base_dir=base)
    input_hashes = {
        "focus_csv": _file_hash(focus),
        "meter_csv": _file_hash(meter),
        "rates_csv": _file_hash(rates),
    }
    input_hashes.update(
        {key: _file_hash(path) for key, path in optional_paths.items()}
    )
    receipt = CloudDiagnosticIntakeReceipt(
        diagnostic_id=diagnostic_id,
        authorization_proof_hash=authorization.proof_hash,
        client_id=authorization.client_id,
        provider=authorization.provider,
        billing_account_id=authorization.billing_account_id,
        period_start=authorization.period_start,
        period_end=authorization.period_end,
        input_hashes=input_hashes,
        pilot_deployment_plan_hash=pilot.deployment_plan_hash,
        pilot_report_path=pilot.report_path,
    )
    receipt_path = private_root / "intake-receipt.json"
    atomic_private_write(
        receipt_path,
        (
            json.dumps(
                receipt.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    return AuthorizedCloudDiagnosticResult(
        authorization=authorization,
        intake_receipt=receipt,
        pilot=pilot,
        intake_receipt_path=str(receipt_path),
    )


def load_diagnostic_intake(path: str | Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("diagnostic intake must be readable JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError("diagnostic intake must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run an authorized local cloud recovery diagnostic."
    )
    parser.add_argument("--intake", required=True)
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--run-at", required=True)
    args = parser.parse_args(argv)
    result = run_authorized_cloud_diagnostic(
        load_diagnostic_intake(args.intake),
        base_dir=args.base_dir,
        run_at=args.run_at,
    )
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
