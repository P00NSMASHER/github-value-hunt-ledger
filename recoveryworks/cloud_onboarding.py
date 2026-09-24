"""Customer onboarding checklist and diagnostic-intake builder.

Readiness means the required information is present and structurally usable.
It does not mean billing, meter, or commercial-authority evidence has been
verified. Verification flags are explicit and default false.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import canonical_hash, normalize_source_hash
from recoveryworks.private_io import atomic_private_write


class OnboardingItemState(str, Enum):
    READY = "READY"
    MISSING = "MISSING"
    INVALID = "INVALID"
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True)
class OnboardingChecklistItem:
    item_id: str
    label: str
    state: OnboardingItemState
    detail: str
    blocks_diagnostic: bool

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "item_id": self.item_id,
            "label": self.label,
            "state": self.state.value,
            "detail": self.detail,
            "blocks_diagnostic": self.blocks_diagnostic,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "state": self.state.value,
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class CloudOnboardingReadiness:
    onboarding_id: str
    client_id: str
    provider: str
    billing_account_id: str
    diagnostic_ready: bool
    checklist: tuple[OnboardingChecklistItem, ...]
    diagnostic_intake: Mapping[str, Any] | None

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "onboarding_id": self.onboarding_id,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "diagnostic_ready": self.diagnostic_ready,
            "checklist_hashes": [item.proof_hash for item in self.checklist],
            "diagnostic_intake": self.diagnostic_intake,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "onboarding_id": self.onboarding_id,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "diagnostic_ready": self.diagnostic_ready,
            "checklist": [item.as_dict() for item in self.checklist],
            "diagnostic_intake": self.diagnostic_intake,
            "proof_hash": self.proof_hash,
        }


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _resolve(base: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value.strip())
    return path if path.is_absolute() else base / path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _csv_has_columns(path: Path, required: set[str]) -> tuple[bool, str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
    except (OSError, UnicodeError) as exc:
        return False, f"cannot read CSV: {exc}"
    missing = sorted(required - fields)
    if missing:
        return False, "missing columns: " + ", ".join(missing)
    return True, "required columns present"


def _item(
    item_id: str,
    label: str,
    state: OnboardingItemState,
    detail: str,
    *,
    blocks: bool,
) -> OnboardingChecklistItem:
    return OnboardingChecklistItem(
        item_id=item_id,
        label=label,
        state=state,
        detail=detail,
        blocks_diagnostic=blocks,
    )


def validate_cloud_onboarding(
    spec: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> CloudOnboardingReadiness:
    if spec.get("schema") != 1:
        raise ValueError("unsupported onboarding schema")
    base = Path(base_dir).resolve()
    onboarding_id = _text("onboarding_id", spec.get("onboarding_id"))
    client_id = _text("client_id", spec.get("client_id"))
    provider = _text("provider", spec.get("provider")).lower()
    if provider != "aws":
        raise ValueError("initial onboarding currently supports AWS only")
    billing_account_id = _text(
        "billing_account_id", spec.get("billing_account_id")
    )
    currency = _text("currency", spec.get("currency", "USD")).upper()
    period = spec.get("period")
    authorization = spec.get("authorization")
    inputs = spec.get("inputs")
    cletrics = spec.get("cletrics")
    if not isinstance(period, Mapping):
        raise ValueError("period must be an object")
    if not isinstance(authorization, Mapping):
        raise ValueError("authorization must be an object")
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be an object")
    if not isinstance(cletrics, Mapping):
        raise ValueError("cletrics must be an object")

    items: list[OnboardingChecklistItem] = []

    required_auth = (
        "authorization_id",
        "customer_actor_id",
        "authorized_at",
        "expires_at",
        "source_hash",
        "source_locator",
    )
    missing_auth = [
        name for name in required_auth
        if not isinstance(authorization.get(name), str)
        or not str(authorization.get(name)).strip()
    ]
    purposes = set(authorization.get("allowed_purposes") or ())
    if missing_auth:
        items.append(_item(
            "AUTHORIZATION",
            "Customer diagnostic authorization",
            OnboardingItemState.MISSING,
            "missing fields: " + ", ".join(missing_auth),
            blocks=True,
        ))
    elif not {
        "BILLING_RECOVERY_DIAGNOSTIC", "SAVINGS_ANALYSIS"
    }.issubset(purposes):
        items.append(_item(
            "AUTHORIZATION",
            "Customer diagnostic authorization",
            OnboardingItemState.INVALID,
            "required diagnostic purposes are not authorized",
            blocks=True,
        ))
    else:
        try:
            normalize_source_hash(str(authorization["source_hash"]))
        except ValueError as exc:
            items.append(_item(
                "AUTHORIZATION",
                "Customer diagnostic authorization",
                OnboardingItemState.INVALID,
                str(exc),
                blocks=True,
            ))
        else:
            items.append(_item(
                "AUTHORIZATION",
                "Customer diagnostic authorization",
                OnboardingItemState.READY,
                "authorization fields and purposes present",
                blocks=True,
            ))

    file_rules = (
        (
            "FOCUS",
            "FOCUS billing export",
            "focus_csv",
            {
                "ProviderName",
                "BillingAccountId",
                "ServiceName",
                "ChargePeriodStart",
                "BilledCost",
                "BillingCurrency",
            },
            True,
        ),
        (
            "METER",
            "Independent meter export",
            "meter_csv",
            {"Meter_Record_ID", "Usage_Units"},
            True,
        ),
        (
            "RATES",
            "Reviewed commercial rate file",
            "rates_csv",
            {
                "Counterparty",
                "Service_ID",
                "Effective_From",
                "Fixed_Fee",
                "Included_Units",
                "Unit_Rate",
            },
            True,
        ),
    )
    resolved_inputs: dict[str, str] = {}
    input_hashes: dict[str, str] = {}
    for item_id, label, key, columns, blocks in file_rules:
        path = _resolve(base, inputs.get(key))
        if path is None or not path.is_file():
            items.append(_item(
                item_id,
                label,
                OnboardingItemState.MISSING,
                "file is required",
                blocks=blocks,
            ))
            continue
        valid, detail = _csv_has_columns(path, columns)
        items.append(_item(
            item_id,
            label,
            OnboardingItemState.READY if valid else OnboardingItemState.INVALID,
            detail,
            blocks=blocks,
        ))
        if valid:
            resolved_inputs[key] = str(path)
            input_hashes[key] = _hash(path)

    for key, label in (
        ("anomaly_csv", "Anomaly export"),
        ("reconciliation_csv", "Reconciliation export"),
        ("savings_csv", "Savings opportunity export"),
    ):
        path = _resolve(base, inputs.get(key))
        if path is None:
            items.append(_item(
                key.upper(),
                label,
                OnboardingItemState.OPTIONAL,
                "not supplied",
                blocks=False,
            ))
        elif not path.is_file():
            items.append(_item(
                key.upper(),
                label,
                OnboardingItemState.INVALID,
                "configured optional file does not exist",
                blocks=False,
            ))
        else:
            items.append(_item(
                key.upper(),
                label,
                OnboardingItemState.READY,
                "optional file supplied",
                blocks=False,
            ))
            resolved_inputs[key] = str(path)
            input_hashes[key] = _hash(path)

    period_start = period.get("start")
    period_end = period.get("end")
    if not isinstance(period_start, str) or not isinstance(period_end, str):
        items.append(_item(
            "PERIOD",
            "Diagnostic service period",
            OnboardingItemState.MISSING,
            "period.start and period.end are required",
            blocks=True,
        ))
    else:
        items.append(_item(
            "PERIOD",
            "Diagnostic service period",
            OnboardingItemState.READY,
            f"{period_start} through {period_end}",
            blocks=True,
        ))

    release = cletrics.get("release")
    identity_present = bool(cletrics.get("commit") or cletrics.get("image_digest"))
    if not isinstance(release, str) or not release.strip() or not identity_present:
        items.append(_item(
            "CLETRICS_IDENTITY",
            "Cletrics exporter identity",
            OnboardingItemState.MISSING,
            "release plus commit or image_digest required",
            blocks=True,
        ))
    else:
        items.append(_item(
            "CLETRICS_IDENTITY",
            "Cletrics exporter identity",
            OnboardingItemState.READY,
            "version identity supplied",
            blocks=True,
        ))

    blockers = [
        item for item in items
        if item.blocks_diagnostic
        and item.state is not OnboardingItemState.READY
    ]
    ready = not blockers

    verification_raw = spec.get("verification", {})
    if verification_raw is None:
        verification_raw = {}
    if not isinstance(verification_raw, Mapping):
        raise ValueError("verification must be an object")
    verification: dict[str, bool] = {}
    for key in (
        "charge_source_verified",
        "meter_source_verified",
        "rate_source_verified",
    ):
        value = verification_raw.get(key, False)
        if type(value) is not bool:
            raise ValueError(f"verification.{key} must be boolean")
        verification[key] = value

    diagnostic_intake = None
    if ready:
        auth = {
            key: authorization[key]
            for key in required_auth
        }
        auth.update({
            "allowed_purposes": sorted(purposes),
            "credentials_embedded": False,
            "external_actions_allowed": False,
            "remediation_allowed": False,
        })
        diagnostic_intake = {
            "schema": 1,
            "diagnostic_id": _text(
                "diagnostic_id",
                spec.get("diagnostic_id", f"diagnostic:{onboarding_id}"),
            ),
            "client_id": client_id,
            "provider": provider,
            "billing_account_id": billing_account_id,
            "currency": currency,
            "period": {
                "start": period_start,
                "end": period_end,
            },
            "authorization": auth,
            "inputs": resolved_inputs,
            "verification": verification,
            "cletrics": {
                "release": cletrics["release"],
                "commit": cletrics.get("commit"),
                "image_digest": cletrics.get("image_digest"),
                "exported_at": _text(
                    "cletrics.exported_at", cletrics.get("exported_at")
                ),
            },
            "outputs": {
                "private_root": _text(
                    "outputs.private_root",
                    (spec.get("outputs") or {}).get(
                        "private_root",
                        f"private/diagnostics/{onboarding_id}",
                    )
                    if isinstance(spec.get("outputs") or {}, Mapping)
                    else None,
                )
            },
            "onboarding": {
                "onboarding_id": onboarding_id,
                "input_hashes": dict(sorted(input_hashes.items())),
                "note": "READY means structurally complete, not evidence-verified.",
            },
        }

    return CloudOnboardingReadiness(
        onboarding_id=onboarding_id,
        client_id=client_id,
        provider=provider,
        billing_account_id=billing_account_id,
        diagnostic_ready=ready,
        checklist=tuple(items),
        diagnostic_intake=diagnostic_intake,
    )


def write_onboarding_outputs(
    readiness: CloudOnboardingReadiness,
    *,
    checklist_path: str | Path,
    diagnostic_intake_path: str | Path | None = None,
) -> None:
    atomic_private_write(
        Path(checklist_path),
        (
            json.dumps(
                readiness.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    if diagnostic_intake_path is not None:
        if readiness.diagnostic_intake is None:
            raise ValueError("cannot write diagnostic intake until onboarding is ready")
        atomic_private_write(
            Path(diagnostic_intake_path),
            (
                json.dumps(
                    readiness.diagnostic_intake,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
