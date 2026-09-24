"""Customer onboarding checklist mapped to the current diagnostic API.

Readiness means required artifacts exist and the authorization/review surfaces
are structurally complete. It never implies financial evidence verification.
Customer processing authorization and financial evidence review remain separate.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.cloud_diagnostic import (
    CustomerDiagnosticAuthorization,
    DiagnosticEvidenceReview,
    build_customer_diagnostic_authorization,
    build_diagnostic_evidence_review,
)
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
    diagnostic_request: Mapping[str, Any] | None

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 2,
            "onboarding_id": self.onboarding_id,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "diagnostic_ready": self.diagnostic_ready,
            "checklist_hashes": [item.proof_hash for item in self.checklist],
            "diagnostic_request": self.diagnostic_request,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": 2,
            "onboarding_id": self.onboarding_id,
            "client_id": self.client_id,
            "provider": self.provider,
            "billing_account_id": self.billing_account_id,
            "diagnostic_ready": self.diagnostic_ready,
            "checklist": [item.as_dict() for item in self.checklist],
            "diagnostic_request": self.diagnostic_request,
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
    if spec.get("schema") != 2:
        raise ValueError("unsupported onboarding schema")
    base = Path(base_dir).resolve()
    onboarding_id = _text("onboarding_id", spec.get("onboarding_id"))
    diagnostic_id = _text("diagnostic_id", spec.get("diagnostic_id"))
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
    review = spec.get("evidence_review")
    inputs = spec.get("inputs")
    cletrics = spec.get("cletrics")
    if not isinstance(period, Mapping):
        raise ValueError("period must be an object")
    if not isinstance(authorization, Mapping):
        raise ValueError("authorization must be an object")
    if not isinstance(review, Mapping):
        raise ValueError("evidence_review must be an object")
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be an object")
    if not isinstance(cletrics, Mapping):
        raise ValueError("cletrics must be an object")

    items: list[OnboardingChecklistItem] = []
    resolved_inputs: dict[str, str] = {}
    input_hashes: dict[str, str] = {}

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
    for item_id, label, key, columns, blocks in file_rules:
        path = _resolve(base, inputs.get(key))
        if path is None or not path.is_file():
            items.append(_item(
                item_id, label, OnboardingItemState.MISSING,
                "file is required", blocks=blocks,
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
                key.upper(), label, OnboardingItemState.OPTIONAL,
                "not supplied", blocks=False,
            ))
        elif not path.is_file():
            items.append(_item(
                key.upper(), label, OnboardingItemState.INVALID,
                "configured optional file does not exist", blocks=False,
            ))
        else:
            items.append(_item(
                key.upper(), label, OnboardingItemState.READY,
                "optional file supplied", blocks=False,
            ))
            resolved_inputs[key] = str(path)
            input_hashes[key] = _hash(path)

    period_start = period.get("start")
    period_end = period.get("end")
    if not isinstance(period_start, str) or not isinstance(period_end, str):
        items.append(_item(
            "PERIOD", "Diagnostic service period", OnboardingItemState.MISSING,
            "period.start and period.end are required", blocks=True,
        ))
    else:
        items.append(_item(
            "PERIOD", "Diagnostic service period", OnboardingItemState.READY,
            f"{period_start} through {period_end}", blocks=True,
        ))

    required_auth = (
        "customer_actor_id",
        "authorized_at",
        "expires_at",
        "source_hash",
        "source_locator",
        "verified",
    )
    missing_auth = [key for key in required_auth if key not in authorization]
    auth_valid = not missing_auth
    if auth_valid:
        try:
            normalize_source_hash(str(authorization["source_hash"]))
        except ValueError:
            auth_valid = False
        if type(authorization.get("verified")) is not bool:
            auth_valid = False
        elif authorization.get("verified") is not True:
            auth_valid = False
    items.append(_item(
        "AUTHORIZATION",
        "Customer processing authorization",
        OnboardingItemState.READY if auth_valid else (
            OnboardingItemState.MISSING if missing_auth else OnboardingItemState.INVALID
        ),
        (
            "authorization is verified and ready to bind exact input hashes"
            if auth_valid
            else (
                "missing fields: " + ", ".join(missing_auth)
                if missing_auth
                else "authorization must contain valid source hash and verified=true"
            )
        ),
        blocks=True,
    ))

    required_review = (
        "reviewer_id",
        "reviewed_at",
        "charge_source_verified",
        "meter_source_verified",
        "rate_source_verified",
    )
    missing_review = [key for key in required_review if key not in review]
    review_valid = not missing_review and all(
        type(review.get(key)) is bool
        for key in (
            "charge_source_verified",
            "meter_source_verified",
            "rate_source_verified",
        )
    )
    items.append(_item(
        "EVIDENCE_REVIEW",
        "Money-bearing evidence review",
        OnboardingItemState.READY if review_valid else (
            OnboardingItemState.MISSING if missing_review else OnboardingItemState.INVALID
        ),
        (
            "reviewer identity and explicit verification decisions present"
            if review_valid
            else (
                "missing fields: " + ", ".join(missing_review)
                if missing_review
                else "verification decisions must be boolean"
            )
        ),
        blocks=True,
    ))

    release = cletrics.get("release")
    commit = cletrics.get("commit")
    exported_at = cletrics.get("exported_at")
    cletrics_valid = all(
        isinstance(value, str) and value.strip()
        for value in (release, commit, exported_at)
    )
    items.append(_item(
        "CLETRICS_IDENTITY",
        "Cletrics exporter identity",
        OnboardingItemState.READY if cletrics_valid else OnboardingItemState.MISSING,
        (
            "release, full commit, and export timestamp supplied"
            if cletrics_valid
            else "release, commit, and exported_at are required"
        ),
        blocks=True,
    ))

    blockers = [
        item for item in items
        if item.blocks_diagnostic
        and item.state is not OnboardingItemState.READY
    ]
    ready = not blockers

    diagnostic_request = None
    if ready:
        money_hashes = {
            role: input_hashes[role]
            for role in ("focus_csv", "meter_csv", "rates_csv")
        }
        authorization_payload = {
            "client_id": client_id,
            "billing_account_id": billing_account_id,
            "customer_actor_id": authorization["customer_actor_id"],
            "period_start": period_start,
            "period_end": period_end,
            "authorized_at": authorization["authorized_at"],
            "expires_at": authorization["expires_at"],
            "authorized_input_hashes": dict(sorted(input_hashes.items())),
            "source_hash": authorization["source_hash"],
            "source_locator": authorization["source_locator"],
            "verified": True,
        }
        review_payload = {
            "reviewer_id": review["reviewer_id"],
            "reviewed_at": review["reviewed_at"],
            "money_source_hashes": money_hashes,
            "charge_source_verified": review["charge_source_verified"],
            "meter_source_verified": review["meter_source_verified"],
            "rate_source_verified": review["rate_source_verified"],
        }
        output_raw = spec.get("outputs", {})
        if not isinstance(output_raw, Mapping):
            raise ValueError("outputs must be an object")
        diagnostic_request = {
            "diagnostic_id": diagnostic_id,
            "authorization": authorization_payload,
            "evidence_review": review_payload,
            "input_paths": dict(sorted(resolved_inputs.items())),
            "cletrics_release": release,
            "cletrics_commit": commit,
            "exported_at": exported_at,
            "currency": currency,
            "private_root": _text(
                "outputs.private_root",
                output_raw.get(
                    "private_root",
                    f"private/diagnostics/{diagnostic_id}",
                ),
            ),
            "onboarding": {
                "onboarding_id": onboarding_id,
                "note": (
                    "Readiness and processing authorization do not imply "
                    "financial evidence verification."
                ),
            },
        }

    return CloudOnboardingReadiness(
        onboarding_id=onboarding_id,
        client_id=client_id,
        provider=provider,
        billing_account_id=billing_account_id,
        diagnostic_ready=ready,
        checklist=tuple(items),
        diagnostic_request=diagnostic_request,
    )


def materialize_cloud_diagnostic_call(
    readiness: CloudOnboardingReadiness,
) -> dict[str, Any]:
    if not readiness.diagnostic_ready or readiness.diagnostic_request is None:
        raise ValueError("onboarding is not ready for a diagnostic call")
    request = readiness.diagnostic_request
    authorization: CustomerDiagnosticAuthorization = (
        build_customer_diagnostic_authorization(**request["authorization"])
    )
    evidence_review: DiagnosticEvidenceReview = build_diagnostic_evidence_review(
        **request["evidence_review"]
    )
    return {
        "diagnostic_id": request["diagnostic_id"],
        "authorization": authorization,
        "evidence_review": evidence_review,
        "input_paths": request["input_paths"],
        "cletrics_release": request["cletrics_release"],
        "cletrics_commit": request["cletrics_commit"],
        "exported_at": request["exported_at"],
        "currency": request["currency"],
        "private_root": request["private_root"],
    }


def write_onboarding_outputs(
    readiness: CloudOnboardingReadiness,
    *,
    checklist_path: str | Path,
    diagnostic_request_path: str | Path | None = None,
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
    if diagnostic_request_path is not None:
        if readiness.diagnostic_request is None:
            raise ValueError("cannot write diagnostic request until onboarding is ready")
        atomic_private_write(
            Path(diagnostic_request_path),
            (
                json.dumps(
                    readiness.diagnostic_request,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
