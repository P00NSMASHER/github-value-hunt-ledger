"""Configurable commercial package for a Cloud Recovery pilot.

This is an internal packaging artifact, not a customer contract, invoice,
outreach message, or commitment. Pricing fields are explicit hypotheses to be
tested. Recovery success fees apply only to verified recovered cash and never
to prospective savings or anomaly exposure.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import canonical_hash
from recoveryworks.private_io import atomic_private_write


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _nonnegative_int(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class CommercialPilotScope:
    provider: str
    lookback_months: int
    max_billing_accounts: int
    recovery_modes: tuple[str, ...]
    include_prospective_savings: bool
    include_diagnostics: bool
    include_remediation_plan: bool
    cloud_mutation_in_scope: bool = False
    external_recovery_actions_in_scope: bool = False

    def __post_init__(self) -> None:
        provider = _text("provider", self.provider).lower()
        if provider != "aws":
            raise ValueError("initial commercial pilot package currently supports AWS")
        object.__setattr__(self, "provider", provider)
        if type(self.lookback_months) is not int or not 1 <= self.lookback_months <= 36:
            raise ValueError("lookback_months must be in 1..36")
        if type(self.max_billing_accounts) is not int or self.max_billing_accounts < 1:
            raise ValueError("max_billing_accounts must be positive")
        modes = tuple(sorted({_text("recovery_mode", value) for value in self.recovery_modes}))
        allowed = {
            "CONTRACT_RATE_MISMATCH",
            "CONTRACT_DISCOUNT_OMISSION",
            "COMMITMENT_BENEFIT_OMISSION",
        }
        if not modes or not set(modes).issubset(allowed):
            raise ValueError("recovery_modes contains an unsupported mode")
        object.__setattr__(self, "recovery_modes", modes)
        for name in (
            "include_prospective_savings",
            "include_diagnostics",
            "include_remediation_plan",
            "cloud_mutation_in_scope",
            "external_recovery_actions_in_scope",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if self.cloud_mutation_in_scope:
            raise ValueError("pilot package must keep cloud mutation out of scope")
        if self.external_recovery_actions_in_scope:
            raise ValueError("pilot package must keep external recovery actions out of scope")


@dataclass(frozen=True)
class CommercialPilotPricing:
    currency: str
    diagnostic_fee_cents: int
    recovered_cash_success_fee_bps: int
    monthly_assurance_fee_cents: int
    savings_implementation_fee_cents: int | None = None
    pricing_is_hypothesis: bool = True

    def __post_init__(self) -> None:
        currency = _text("currency", self.currency).upper()
        if len(currency) != 3:
            raise ValueError("currency must be a three-letter code")
        object.__setattr__(self, "currency", currency)
        _nonnegative_int("diagnostic_fee_cents", self.diagnostic_fee_cents)
        if (
            type(self.recovered_cash_success_fee_bps) is not int
            or not 0 <= self.recovered_cash_success_fee_bps <= 10000
        ):
            raise ValueError("recovered_cash_success_fee_bps must be in 0..10000")
        _nonnegative_int(
            "monthly_assurance_fee_cents", self.monthly_assurance_fee_cents
        )
        if self.savings_implementation_fee_cents is not None:
            _nonnegative_int(
                "savings_implementation_fee_cents",
                self.savings_implementation_fee_cents,
            )
        if self.pricing_is_hypothesis is not True:
            raise ValueError("commercial pilot pricing must remain marked as a hypothesis")

    def success_fee_for_recovered_cash(self, recovered_cash_cents: int) -> int:
        recovered = _nonnegative_int("recovered_cash_cents", recovered_cash_cents)
        return (recovered * self.recovered_cash_success_fee_bps + 5000) // 10000


@dataclass(frozen=True)
class CommercialPilotAcceptanceCriterion:
    criterion_id: str
    description: str
    required_evidence: str

    def __post_init__(self) -> None:
        for name in ("criterion_id", "description", "required_evidence"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))


@dataclass(frozen=True)
class CloudCommercialPilotPackage:
    package_id: str
    offer_name: str
    buyer_profile: str
    scope: CommercialPilotScope
    deliverables: tuple[str, ...]
    pricing: CommercialPilotPricing
    acceptance_criteria: tuple[CommercialPilotAcceptanceCriterion, ...]
    exclusions: tuple[str, ...]
    assumptions: tuple[str, ...]
    contract_generated: bool = False
    outreach_allowed: bool = False
    external_commitment_created: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "offer_name", _text("offer_name", self.offer_name))
        object.__setattr__(self, "buyer_profile", _text("buyer_profile", self.buyer_profile))
        deliverables = tuple(_text("deliverable", value) for value in self.deliverables)
        if not deliverables:
            raise ValueError("at least one deliverable is required")
        object.__setattr__(self, "deliverables", deliverables)
        criteria = tuple(self.acceptance_criteria)
        if not criteria:
            raise ValueError("at least one acceptance criterion is required")
        if len({item.criterion_id for item in criteria}) != len(criteria):
            raise ValueError("acceptance criterion ids must be unique")
        object.__setattr__(self, "acceptance_criteria", criteria)
        object.__setattr__(
            self, "exclusions", tuple(_text("exclusion", value) for value in self.exclusions)
        )
        object.__setattr__(
            self, "assumptions", tuple(_text("assumption", value) for value in self.assumptions)
        )
        if self.contract_generated or self.outreach_allowed or self.external_commitment_created:
            raise ValueError(
                "step 9a package cannot create contracts, outreach, or external commitments"
            )
        expected = "cloud-commercial-pilot:" + canonical_hash(self._identity())
        if self.package_id != expected:
            raise ValueError("package_id does not bind the commercial pilot package")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "offer_name": self.offer_name,
            "buyer_profile": self.buyer_profile,
            "scope": {
                **asdict(self.scope),
                "recovery_modes": list(self.scope.recovery_modes),
            },
            "deliverables": list(self.deliverables),
            "pricing": asdict(self.pricing),
            "acceptance_criteria": [asdict(item) for item in self.acceptance_criteria],
            "exclusions": list(self.exclusions),
            "assumptions": list(self.assumptions),
            "contract_generated": False,
            "outreach_allowed": False,
            "external_commitment_created": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "package_id": self.package_id,
            "proof_hash": self.proof_hash,
            "status": "INTERNAL_PILOT_CONFIGURATION",
        }

    def to_markdown(self) -> str:
        lines = [
            f"# {self.offer_name}",
            "",
            f"Target buyer profile: {self.buyer_profile}",
            "",
            "## Scope",
            "",
            f"- Provider: {self.scope.provider.upper()}",
            f"- Lookback: up to {self.scope.lookback_months} months",
            f"- Billing accounts: up to {self.scope.max_billing_accounts}",
            "- Recovery modes: " + ", ".join(self.scope.recovery_modes),
            f"- Prospective savings: {self.scope.include_prospective_savings}",
            f"- Diagnostics: {self.scope.include_diagnostics}",
            f"- Remediation planning: {self.scope.include_remediation_plan}",
            "- Cloud mutation: out of scope",
            "- External recovery actions: out of scope",
            "",
            "## Deliverables",
            "",
        ]
        lines.extend(f"- {item}" for item in self.deliverables)
        lines.extend([
            "",
            "## Pricing configuration (hypothesis to test)",
            "",
            f"- Diagnostic fee: {self.pricing.diagnostic_fee_cents} {self.pricing.currency} cents",
            f"- Success fee on verified recovered cash only: {self.pricing.recovered_cash_success_fee_bps} bps",
            f"- Monthly assurance fee: {self.pricing.monthly_assurance_fee_cents} {self.pricing.currency} cents",
            "- Prospective savings and anomaly estimates are not success-fee recovery.",
            "",
            "## Customer acceptance criteria",
            "",
        ])
        for item in self.acceptance_criteria:
            lines.append(f"- [{item.criterion_id}] {item.description} — evidence: {item.required_evidence}")
        lines.extend([
            "",
            "## Exclusions",
            "",
        ])
        lines.extend(f"- {item}" for item in self.exclusions)
        lines.extend([
            "",
            "## Assumptions",
            "",
        ])
        lines.extend(f"- {item}" for item in self.assumptions)
        lines.extend([
            "",
            "This artifact is an internal pilot configuration, not a contract, invoice, proposal acceptance, or external commitment.",
            "",
        ])
        return "\n".join(lines)


def build_commercial_pilot_package(spec: Mapping[str, Any]) -> CloudCommercialPilotPackage:
    if spec.get("schema") != 1:
        raise ValueError("unsupported commercial pilot package schema")
    scope_raw = spec.get("scope")
    pricing_raw = spec.get("pricing")
    if not isinstance(scope_raw, Mapping) or not isinstance(pricing_raw, Mapping):
        raise ValueError("scope and pricing must be objects")
    scope = CommercialPilotScope(
        provider=_text("scope.provider", scope_raw.get("provider")),
        lookback_months=scope_raw.get("lookback_months"),
        max_billing_accounts=scope_raw.get("max_billing_accounts"),
        recovery_modes=tuple(scope_raw.get("recovery_modes") or ()),
        include_prospective_savings=scope_raw.get("include_prospective_savings"),
        include_diagnostics=scope_raw.get("include_diagnostics"),
        include_remediation_plan=scope_raw.get("include_remediation_plan"),
        cloud_mutation_in_scope=scope_raw.get("cloud_mutation_in_scope", False),
        external_recovery_actions_in_scope=scope_raw.get(
            "external_recovery_actions_in_scope", False
        ),
    )
    pricing = CommercialPilotPricing(
        currency=_text("pricing.currency", pricing_raw.get("currency")),
        diagnostic_fee_cents=pricing_raw.get("diagnostic_fee_cents"),
        recovered_cash_success_fee_bps=pricing_raw.get(
            "recovered_cash_success_fee_bps"
        ),
        monthly_assurance_fee_cents=pricing_raw.get("monthly_assurance_fee_cents"),
        savings_implementation_fee_cents=pricing_raw.get(
            "savings_implementation_fee_cents"
        ),
        pricing_is_hypothesis=pricing_raw.get("pricing_is_hypothesis", True),
    )
    criteria_raw = spec.get("acceptance_criteria")
    if not isinstance(criteria_raw, list):
        raise ValueError("acceptance_criteria must be a list")
    criteria = tuple(
        CommercialPilotAcceptanceCriterion(
            criterion_id=_text(
                f"acceptance_criteria[{index}].criterion_id",
                item.get("criterion_id") if isinstance(item, Mapping) else None,
            ),
            description=_text(
                f"acceptance_criteria[{index}].description",
                item.get("description") if isinstance(item, Mapping) else None,
            ),
            required_evidence=_text(
                f"acceptance_criteria[{index}].required_evidence",
                item.get("required_evidence") if isinstance(item, Mapping) else None,
            ),
        )
        for index, item in enumerate(criteria_raw)
    )
    identity = {
        "schema": 1,
        "offer_name": _text("offer_name", spec.get("offer_name")),
        "buyer_profile": _text("buyer_profile", spec.get("buyer_profile")),
        "scope": {
            **asdict(scope),
            "recovery_modes": list(scope.recovery_modes),
        },
        "deliverables": list(spec.get("deliverables") or ()),
        "pricing": asdict(pricing),
        "acceptance_criteria": [asdict(item) for item in criteria],
        "exclusions": list(spec.get("exclusions") or ()),
        "assumptions": list(spec.get("assumptions") or ()),
        "contract_generated": False,
        "outreach_allowed": False,
        "external_commitment_created": False,
    }
    return CloudCommercialPilotPackage(
        package_id="cloud-commercial-pilot:" + canonical_hash(identity),
        offer_name=identity["offer_name"],
        buyer_profile=identity["buyer_profile"],
        scope=scope,
        deliverables=tuple(identity["deliverables"]),
        pricing=pricing,
        acceptance_criteria=criteria,
        exclusions=tuple(identity["exclusions"]),
        assumptions=tuple(identity["assumptions"]),
    )


def write_commercial_pilot_package(
    package: CloudCommercialPilotPackage,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                package.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (package.to_markdown() + "\n").encode("utf-8"),
    )


def load_commercial_pilot_spec(path: str | Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("commercial pilot spec must be readable JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError("commercial pilot spec must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the internal Cloud Recovery commercial pilot package."
    )
    parser.add_argument("--spec", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args(argv)
    package = build_commercial_pilot_package(
        load_commercial_pilot_spec(args.spec)
    )
    write_commercial_pilot_package(
        package,
        json_path=args.json_output,
        markdown_path=args.markdown_output,
    )
    print(json.dumps(package.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
