"""Authorized multi-provider real-account diagnostic intake and local execution.

Exact customer-authorized input bytes are hash-checked, preflighted for scope,
and snapshotted into private storage before RecoveryOS runs. Permission to
process is independent from financial evidence verification.
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

from recoveryworks.cloud_provider import canonical_cloud_provider
from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_source_hash,
    normalize_utc_timestamp,
)
from recoveryworks.pilot_runner import PilotRunResult, run_local_pilot
from recoveryworks.private_io import (
    atomic_private_write,
    private_permissions_verified,
)


_REQUIRED_INPUTS = ("focus_csv", "meter_csv", "rates_csv")
_OPTIONAL_INPUTS = ("anomaly_csv", "reconciliation_csv", "savings_csv")
_SUPPORTED_PROVIDERS = {"aws", "azure", "gcp"}


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _iso_date(name: str, value: Any) -> str:
    raw = _text(name, value)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(
        normalize_utc_timestamp("timestamp", value).replace("Z", "+00:00")
    )


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
    authorized_input_hashes: Mapping[str, str]
    source_hash: str
    source_locator: str
    verified: bool
    credentials_embedded: bool = False
    external_actions_allowed: bool = False
    remediation_allowed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "client_id",
            "provider",
            "billing_account_id",
            "customer_actor_id",
            "source_locator",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self, "provider", canonical_cloud_provider(self.provider)
        )
        if self.provider not in _SUPPORTED_PROVIDERS:
            raise ValueError(
                "diagnostic provider must be one of: "
                + ", ".join(sorted(_SUPPORTED_PROVIDERS))
            )
        start = _iso_date("period_start", self.period_start)
        end = _iso_date("period_end", self.period_end)
        if end < start:
            raise ValueError("authorization period_end cannot predate period_start")
        object.__setattr__(self, "period_start", start)
        object.__setattr__(self, "period_end", end)
        authorized = normalize_utc_timestamp("authorized_at", self.authorized_at)
        expires = normalize_utc_timestamp("expires_at", self.expires_at)
        if _instant(expires) <= _instant(authorized):
            raise ValueError("authorization expiry must follow authorization")
        object.__setattr__(self, "authorized_at", authorized)
        object.__setattr__(self, "expires_at", expires)

        hashes = {
            str(key): normalize_sha256(f"authorized_input_hashes.{key}", value)
            for key, value in self.authorized_input_hashes.items()
        }
        if not set(_REQUIRED_INPUTS).issubset(hashes):
            raise ValueError("authorization must bind focus, meter, and rates inputs")
        unknown = set(hashes) - set(_REQUIRED_INPUTS) - set(_OPTIONAL_INPUTS)
        if unknown:
            raise ValueError(
                "authorization contains unsupported input roles: "
                + ", ".join(sorted(unknown))
            )
        object.__setattr__(
            self,
            "authorized_input_hashes",
            freeze_json(hashes, name="authorized_input_hashes"),
        )
        object.__setattr__(self, "source_hash", normalize_source_hash(self.source_hash))
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.credentials_embedded:
            raise ValueError("diagnostic authorization must not embed credentials")
        if self.external_actions_allowed:
            raise ValueError("diagnostic authorization cannot allow external actions")
        if self.remediation_allowed:
            raise ValueError("diagnostic authorization cannot allow remediation")
        expected = "cloud-diagnostic-authorization:" + canonical_hash(
            self._identity()
        )
        if self.authorization_id != expected:
            raise ValueError("authorization_id does not bind authorization payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "customer_actor_id": self.customer_actor_id,
            "authorized_at": self.authorized_at,
            "expires_at": self.expires_at,
            "authorized_input_hashes": dict(self.authorized_input_hashes),
            "source_hash": self.source_hash,
            "source_locator": self.source_locator,
            "verified": self.verified,
            "credentials_embedded": False,
            "external_actions_allowed": False,
            "remediation_allowed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_customer_diagnostic_authorization(
    *,
    client_id: str,
    provider: str = "aws",
    billing_account_id: str,
    customer_actor_id: str,
    period_start: str,
    period_end: str,
    authorized_at: str,
    expires_at: str,
    authorized_input_hashes: Mapping[str, str],
    source_hash: str,
    source_locator: str,
    verified: bool,
) -> CustomerDiagnosticAuthorization:
    identity = {
        "schema": 1,
        "client_id": _text("client_id", client_id),
        "provider": canonical_cloud_provider(provider),
        "billing_account_id": _text("billing_account_id", billing_account_id),
        "period_start": _iso_date("period_start", period_start),
        "period_end": _iso_date("period_end", period_end),
        "customer_actor_id": _text("customer_actor_id", customer_actor_id),
        "authorized_at": normalize_utc_timestamp("authorized_at", authorized_at),
        "expires_at": normalize_utc_timestamp("expires_at", expires_at),
        "authorized_input_hashes": {
            str(key): normalize_sha256(f"authorized_input_hashes.{key}", value)
            for key, value in authorized_input_hashes.items()
        },
        "source_hash": normalize_source_hash(source_hash),
        "source_locator": _text("source_locator", source_locator),
        "verified": verified,
        "credentials_embedded": False,
        "external_actions_allowed": False,
        "remediation_allowed": False,
    }
    return CustomerDiagnosticAuthorization(
        authorization_id="cloud-diagnostic-authorization:"
        + canonical_hash(identity),
        client_id=client_id,
        provider=provider,
        billing_account_id=billing_account_id,
        period_start=period_start,
        period_end=period_end,
        customer_actor_id=customer_actor_id,
        authorized_at=authorized_at,
        expires_at=expires_at,
        authorized_input_hashes=authorized_input_hashes,
        source_hash=source_hash,
        source_locator=source_locator,
        verified=verified,
    )


@dataclass(frozen=True)
class DiagnosticEvidenceReview:
    review_id: str
    reviewer_id: str
    reviewed_at: str
    money_source_hashes: Mapping[str, str]
    charge_source_verified: bool
    meter_source_verified: bool
    rate_source_verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "reviewer_id", _text("reviewer_id", self.reviewer_id))
        object.__setattr__(
            self,
            "reviewed_at",
            normalize_utc_timestamp("reviewed_at", self.reviewed_at),
        )
        hashes = {
            str(key): normalize_sha256(f"money_source_hashes.{key}", value)
            for key, value in self.money_source_hashes.items()
        }
        if set(hashes) != set(_REQUIRED_INPUTS):
            raise ValueError(
                "evidence review must bind exactly focus, meter, and rates"
            )
        object.__setattr__(
            self,
            "money_source_hashes",
            freeze_json(hashes, name="money_source_hashes"),
        )
        for name in (
            "charge_source_verified",
            "meter_source_verified",
            "rate_source_verified",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        expected = "cloud-diagnostic-evidence-review:" + canonical_hash(
            self._identity()
        )
        if self.review_id != expected:
            raise ValueError("review_id does not bind evidence review payload")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "money_source_hashes": dict(self.money_source_hashes),
            "charge_source_verified": self.charge_source_verified,
            "meter_source_verified": self.meter_source_verified,
            "rate_source_verified": self.rate_source_verified,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_diagnostic_evidence_review(
    *,
    reviewer_id: str,
    reviewed_at: str,
    money_source_hashes: Mapping[str, str],
    charge_source_verified: bool,
    meter_source_verified: bool,
    rate_source_verified: bool,
) -> DiagnosticEvidenceReview:
    identity = {
        "schema": 1,
        "reviewer_id": _text("reviewer_id", reviewer_id),
        "reviewed_at": normalize_utc_timestamp("reviewed_at", reviewed_at),
        "money_source_hashes": {
            str(key): normalize_sha256(f"money_source_hashes.{key}", value)
            for key, value in money_source_hashes.items()
        },
        "charge_source_verified": charge_source_verified,
        "meter_source_verified": meter_source_verified,
        "rate_source_verified": rate_source_verified,
    }
    return DiagnosticEvidenceReview(
        review_id="cloud-diagnostic-evidence-review:" + canonical_hash(identity),
        reviewer_id=reviewer_id,
        reviewed_at=reviewed_at,
        money_source_hashes=money_source_hashes,
        charge_source_verified=charge_source_verified,
        meter_source_verified=meter_source_verified,
        rate_source_verified=rate_source_verified,
    )


@dataclass(frozen=True)
class CloudDiagnosticIntakeReceipt:
    diagnostic_id: str
    authorization_proof_hash: str
    evidence_review_proof_hash: str
    client_id: str
    billing_account_id: str
    period_start: str
    period_end: str
    input_hashes: Mapping[str, str]
    private_snapshot_paths: Mapping[str, str]
    pilot_deployment_plan_hash: str
    pilot_report_path: str

    def __post_init__(self) -> None:
        for name in (
            "authorization_proof_hash",
            "evidence_review_proof_hash",
            "pilot_deployment_plan_hash",
        ):
            object.__setattr__(self, name, normalize_sha256(name, getattr(self, name)))
        for name in (
            "diagnostic_id",
            "client_id",
            "billing_account_id",
            "pilot_report_path",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        object.__setattr__(
            self,
            "input_hashes",
            freeze_json(
                {
                    str(key): normalize_sha256(f"input_hashes.{key}", value)
                    for key, value in self.input_hashes.items()
                },
                name="input_hashes",
            ),
        )
        object.__setattr__(
            self,
            "private_snapshot_paths",
            freeze_json(
                {
                    str(key): _text(f"private_snapshot_paths.{key}", value)
                    for key, value in self.private_snapshot_paths.items()
                },
                name="private_snapshot_paths",
            ),
        )

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "diagnostic_id": self.diagnostic_id,
            "authorization_proof_hash": self.authorization_proof_hash,
            "evidence_review_proof_hash": self.evidence_review_proof_hash,
            "client_id": self.client_id,
            "billing_account_id": self.billing_account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "input_hashes": dict(self.input_hashes),
            "private_snapshot_paths": dict(self.private_snapshot_paths),
            "pilot_deployment_plan_hash": self.pilot_deployment_plan_hash,
            "pilot_report_path": self.pilot_report_path,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "authorization_proof_hash": self.authorization_proof_hash,
            "evidence_review_proof_hash": self.evidence_review_proof_hash,
            "client_id": self.client_id,
            "billing_account_id": self.billing_account_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "input_hashes": dict(self.input_hashes),
            "private_snapshot_paths": dict(self.private_snapshot_paths),
            "pilot_deployment_plan_hash": self.pilot_deployment_plan_hash,
            "pilot_report_path": self.pilot_report_path,
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class AuthorizedCloudDiagnosticResult:
    intake_receipt: CloudDiagnosticIntakeReceipt
    pilot: PilotRunResult
    intake_receipt_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "intake_receipt": self.intake_receipt.as_dict(),
            "pilot": self.pilot.as_dict(),
            "intake_receipt_path": self.intake_receipt_path,
        }


def _resolve(base: Path, value: Any, *, name: str) -> Path:
    raw = Path(_text(name, value))
    path = raw if raw.is_absolute() else base / raw
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{name} must be a regular file: {path}")
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
        provider = canonical_cloud_provider(
            str(row.get("ProviderName") or "")
        )
        account = str(row.get("BillingAccountId") or "").strip()
        row_currency = str(row.get("BillingCurrency") or "").strip().upper()
        service_date = _iso_date(
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


def run_authorized_cloud_diagnostic(
    *,
    diagnostic_id: str,
    authorization: CustomerDiagnosticAuthorization,
    evidence_review: DiagnosticEvidenceReview,
    input_paths: Mapping[str, str],
    cletrics_release: str,
    cletrics_commit: str,
    exported_at: str,
    currency: str = "USD",
    private_root: str | Path,
    base_dir: str | Path = ".",
    run_at: str,
) -> AuthorizedCloudDiagnosticResult:
    base = Path(base_dir).resolve()
    checked = normalize_utc_timestamp("run_at", run_at)
    if not authorization.verified:
        raise ValueError("customer diagnostic authorization must be verified")
    if _instant(checked) < _instant(authorization.authorized_at):
        raise ValueError("diagnostic run cannot predate customer authorization")
    if _instant(checked) > _instant(authorization.expires_at):
        raise ValueError("customer diagnostic authorization has expired")

    paths: dict[str, Path] = {}
    for role in _REQUIRED_INPUTS:
        if role not in input_paths:
            raise ValueError(f"diagnostic input missing {role}")
    for role, value in input_paths.items():
        if role not in set(_REQUIRED_INPUTS) | set(_OPTIONAL_INPUTS):
            raise ValueError(f"unsupported diagnostic input role: {role}")
        paths[role] = _resolve(base, value, name=f"inputs.{role}")

    current_hashes = {role: _file_hash(path) for role, path in paths.items()}
    if current_hashes != dict(authorization.authorized_input_hashes):
        raise ValueError("diagnostic source bytes do not match customer authorization")
    money_hashes = {role: current_hashes[role] for role in _REQUIRED_INPUTS}
    if money_hashes != dict(evidence_review.money_source_hashes):
        raise ValueError("evidence review does not bind current money-bearing inputs")

    currency = _text("currency", currency).upper()
    _preflight_focus(
        paths["focus_csv"],
        authorization=authorization,
        currency=currency,
    )

    private_root = Path(private_root)
    if not private_root.is_absolute():
        private_root = base / private_root
    snapshot_root = private_root / "intake"
    snapped: dict[str, str] = {}
    for role in sorted(paths):
        source = paths[role]
        target = snapshot_root / f"{role}-{current_hashes[role]}{source.suffix}"
        atomic_private_write(target, source.read_bytes())
        if not private_permissions_verified(target):
            raise PermissionError(f"private input snapshot failed: {role}")
        snapped[role] = str(target)

    pilot_spec: dict[str, Any] = {
        "schema": 1,
        "deployment_id": f"diagnostic:{_text('diagnostic_id', diagnostic_id)}",
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
            "exported_at": normalize_utc_timestamp("exported_at", exported_at),
        },
        "cletrics": {
            "focus_csv": snapped["focus_csv"],
            "meter_csv": snapped["meter_csv"],
            "release": _text("cletrics_release", cletrics_release),
            "commit": _text("cletrics_commit", cletrics_commit),
        },
        "recoveryos": {
            "rates_csv": snapped["rates_csv"],
            "verification": {
                "charge_source_verified":
                    evidence_review.charge_source_verified,
                "meter_source_verified":
                    evidence_review.meter_source_verified,
                "rate_source_verified":
                    evidence_review.rate_source_verified,
            },
            "bundle_path": str(private_root / "cletrics-bundle.zip"),
            "ledger_path": str(private_root / "ledger.json"),
            "receipt_registry_path": str(private_root / "receipts.json"),
            "report_path": str(private_root / "cloud-assurance.json"),
        },
    }
    for role, spec_key in (
        ("anomaly_csv", "anomaly_csv"),
        ("reconciliation_csv", "reconciliation_csv"),
        ("savings_csv", "savings_csv"),
    ):
        if role in snapped:
            pilot_spec["cletrics"][spec_key] = snapped[role]

    pilot = run_local_pilot(pilot_spec, base_dir=base)
    receipt = CloudDiagnosticIntakeReceipt(
        diagnostic_id=diagnostic_id,
        authorization_proof_hash=authorization.proof_hash,
        evidence_review_proof_hash=evidence_review.proof_hash,
        client_id=authorization.client_id,
        billing_account_id=authorization.billing_account_id,
        period_start=authorization.period_start,
        period_end=authorization.period_end,
        input_hashes=current_hashes,
        private_snapshot_paths=snapped,
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
        intake_receipt=receipt,
        pilot=pilot,
        intake_receipt_path=str(receipt_path),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="This API is intended to be invoked by an authorized wrapper."
    )
    parser.error(
        "construct CustomerDiagnosticAuthorization and DiagnosticEvidenceReview "
        "in an authorized integration; raw CLI authorization is intentionally unsupported"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
