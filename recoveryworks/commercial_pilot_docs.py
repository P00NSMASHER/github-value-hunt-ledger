"""Proposal/SOW-ready draft artifacts for the commercial cloud pilot.

These are internal draft documents tied to an exact commercial-pilot package.
They are not signed agreements, invoices, payment requests, accepted proposals,
or external commitments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from recoveryworks.commercial_pilot import CloudCommercialPilotPackage
from recoveryworks.models import canonical_hash
from recoveryworks.private_io import atomic_private_write


@dataclass(frozen=True)
class PilotFeeScenario:
    scenario_id: str
    package_proof_hash: str
    assumed_recovered_cash_cents: int
    diagnostic_fee_cents: int
    success_fee_cents: int
    monthly_assurance_fee_cents: int
    optional_savings_implementation_fee_cents: int
    total_if_all_assumptions_occur_cents: int
    is_forecast: bool = False
    is_pricing_hypothesis: bool = True

    def __post_init__(self) -> None:
        if self.is_forecast:
            raise ValueError("fee scenario is arithmetic, not a revenue forecast")
        if self.is_pricing_hypothesis is not True:
            raise ValueError("fee scenario must remain marked as pricing hypothesis")
        expected = "cloud-pilot-fee-scenario:" + canonical_hash(self._identity())
        if self.scenario_id != expected:
            raise ValueError("scenario_id does not bind the fee scenario")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "package_proof_hash": self.package_proof_hash,
            "assumed_recovered_cash_cents": self.assumed_recovered_cash_cents,
            "diagnostic_fee_cents": self.diagnostic_fee_cents,
            "success_fee_cents": self.success_fee_cents,
            "monthly_assurance_fee_cents": self.monthly_assurance_fee_cents,
            "optional_savings_implementation_fee_cents":
                self.optional_savings_implementation_fee_cents,
            "total_if_all_assumptions_occur_cents":
                self.total_if_all_assumptions_occur_cents,
            "is_forecast": False,
            "is_pricing_hypothesis": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "scenario_id": self.scenario_id,
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class CommercialPilotDraftBundle:
    draft_id: str
    package_id: str
    package_proof_hash: str
    fee_scenario: PilotFeeScenario
    proposal_markdown: str
    sow_markdown: str
    signature_ready: bool = False
    accepted: bool = False
    invoice_generated: bool = False
    payment_request_generated: bool = False
    external_commitment_created: bool = False

    def __post_init__(self) -> None:
        for flag in (
            self.signature_ready,
            self.accepted,
            self.invoice_generated,
            self.payment_request_generated,
            self.external_commitment_created,
        ):
            if flag:
                raise ValueError(
                    "step 9b drafts cannot be signed, accepted, invoiced, paid, or committed"
                )
        expected = "cloud-pilot-draft-bundle:" + canonical_hash(self._identity())
        if self.draft_id != expected:
            raise ValueError("draft_id does not bind the draft bundle")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "package_id": self.package_id,
            "package_proof_hash": self.package_proof_hash,
            "fee_scenario_proof_hash": self.fee_scenario.proof_hash,
            "proposal_markdown": self.proposal_markdown,
            "sow_markdown": self.sow_markdown,
            "signature_ready": False,
            "accepted": False,
            "invoice_generated": False,
            "payment_request_generated": False,
            "external_commitment_created": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "draft_id": self.draft_id,
            "proof_hash": self.proof_hash,
            "fee_scenario": self.fee_scenario.as_dict(),
            "status": "DRAFT_ONLY",
        }


def build_fee_scenario(
    package: CloudCommercialPilotPackage,
    *,
    assumed_recovered_cash_cents: int,
    include_one_month_assurance: bool = True,
    include_optional_savings_implementation: bool = False,
) -> PilotFeeScenario:
    if type(assumed_recovered_cash_cents) is not int or assumed_recovered_cash_cents < 0:
        raise ValueError("assumed_recovered_cash_cents must be non-negative integer cents")
    success = package.pricing.success_fee_for_recovered_cash(
        assumed_recovered_cash_cents
    )
    assurance = (
        package.pricing.monthly_assurance_fee_cents
        if include_one_month_assurance
        else 0
    )
    implementation = (
        package.pricing.savings_implementation_fee_cents or 0
        if include_optional_savings_implementation
        else 0
    )
    identity = {
        "schema": 1,
        "package_proof_hash": package.proof_hash,
        "assumed_recovered_cash_cents": assumed_recovered_cash_cents,
        "diagnostic_fee_cents": package.pricing.diagnostic_fee_cents,
        "success_fee_cents": success,
        "monthly_assurance_fee_cents": assurance,
        "optional_savings_implementation_fee_cents": implementation,
        "total_if_all_assumptions_occur_cents":
            package.pricing.diagnostic_fee_cents + success + assurance + implementation,
        "is_forecast": False,
        "is_pricing_hypothesis": True,
    }
    return PilotFeeScenario(
        scenario_id="cloud-pilot-fee-scenario:" + canonical_hash(identity),
        **{key: value for key, value in identity.items() if key != "schema"},
    )


def _money(cents: int, currency: str) -> str:
    return f"{currency} {cents / 100:,.2f}"


def build_commercial_pilot_drafts(
    package: CloudCommercialPilotPackage,
    *,
    assumed_recovered_cash_cents: int = 0,
) -> CommercialPilotDraftBundle:
    scenario = build_fee_scenario(
        package,
        assumed_recovered_cash_cents=assumed_recovered_cash_cents,
    )
    pricing = package.pricing
    proposal = "\n".join([
        f"# DRAFT — {package.offer_name}",
        "",
        "**Status: internal draft only; not accepted, signed, invoiced, or binding.**",
        "",
        "## Objective",
        "",
        "Analyze authorized AWS billing and independent usage evidence to identify "
        "contract-backed recovery candidates, prospective savings opportunities, "
        "and diagnostic anomalies while preserving a strict evidence boundary.",
        "",
        "## Pilot scope",
        "",
        f"- Provider: {package.scope.provider.upper()}",
        f"- Lookback: up to {package.scope.lookback_months} months",
        f"- Billing accounts: up to {package.scope.max_billing_accounts}",
        "- Recovery modes: " + ", ".join(package.scope.recovery_modes),
        "- Cloud mutation: excluded",
        "- External dispute/recovery submission: excluded unless separately authorized later",
        "",
        "## Deliverables",
        "",
        *[f"- {item}" for item in package.deliverables],
        "",
        "## Pricing hypothesis",
        "",
        f"- Diagnostic: {_money(pricing.diagnostic_fee_cents, pricing.currency)}",
        f"- Success fee: {pricing.recovered_cash_success_fee_bps / 100:.2f}% "
        "of verified recovered cash only",
        f"- Continuous assurance: "
        f"{_money(pricing.monthly_assurance_fee_cents, pricing.currency)} / month",
        "- Savings estimates and anomaly exposure are not treated as recovered cash.",
        "",
        "## Illustrative fee arithmetic",
        "",
        f"If recovered cash were {_money(assumed_recovered_cash_cents, pricing.currency)}, "
        f"the configured success-fee arithmetic would be "
        f"{_money(scenario.success_fee_cents, pricing.currency)}.",
        "This is not a forecast of recovery.",
        "",
        "## Acceptance",
        "",
        "Acceptance would require a separately finalized and signed agreement. "
        "This draft itself creates no commitment.",
        "",
    ])
    sow = "\n".join([
        f"# DRAFT SOW — {package.offer_name}",
        "",
        "**Status: drafting artifact only; not an executed statement of work.**",
        "",
        "## Workstream 1 — Authorized data intake",
        "",
        "- Receive customer-authorized FOCUS billing export, independent meter evidence, "
        "and reviewed commercial authority.",
        "- Validate provider/account/period scope before creating RecoveryOS state.",
        "",
        "## Workstream 2 — Recovery analysis",
        "",
        "- Evaluate contracted-rate mismatches.",
        "- Evaluate reviewed contractual discount omissions.",
        "- Evaluate reviewed commitment-benefit omissions.",
        "- Keep unverified candidates in REVIEW.",
        "",
        "## Workstream 3 — Savings and diagnostics",
        "",
        "- Report prospective savings independently from recovery.",
        "- Report anomaly exposure and reconciliation drift as diagnostics.",
        "- Produce plan-only remediation recommendations where included.",
        "",
        "## Deliverables",
        "",
        *[f"- {item}" for item in package.deliverables],
        "",
        "## Acceptance criteria",
        "",
        *[
            f"- {item.criterion_id}: {item.description} "
            f"(evidence: {item.required_evidence})"
            for item in package.acceptance_criteria
        ],
        "",
        "## Explicit exclusions",
        "",
        *[f"- {item}" for item in package.exclusions],
        "",
        "## Commercial terms — draft configuration",
        "",
        f"- Diagnostic fee: {_money(pricing.diagnostic_fee_cents, pricing.currency)}",
        f"- Success fee: {pricing.recovered_cash_success_fee_bps / 100:.2f}% "
        "of verified recovered cash only",
        f"- Monthly assurance: "
        f"{_money(pricing.monthly_assurance_fee_cents, pricing.currency)}",
        "",
        "All commercial values remain hypotheses to test until separately agreed.",
        "",
    ])
    identity = {
        "schema": 1,
        "package_id": package.package_id,
        "package_proof_hash": package.proof_hash,
        "fee_scenario_proof_hash": scenario.proof_hash,
        "proposal_markdown": proposal,
        "sow_markdown": sow,
        "signature_ready": False,
        "accepted": False,
        "invoice_generated": False,
        "payment_request_generated": False,
        "external_commitment_created": False,
    }
    return CommercialPilotDraftBundle(
        draft_id="cloud-pilot-draft-bundle:" + canonical_hash(identity),
        package_id=package.package_id,
        package_proof_hash=package.proof_hash,
        fee_scenario=scenario,
        proposal_markdown=proposal,
        sow_markdown=sow,
    )


def write_commercial_pilot_drafts(
    drafts: CommercialPilotDraftBundle,
    *,
    directory: str | Path,
) -> tuple[Path, Path, Path]:
    target = Path(directory)
    proposal = target / "proposal-draft.md"
    sow = target / "sow-draft.md"
    manifest = target / "draft-manifest.json"
    atomic_private_write(proposal, (drafts.proposal_markdown + "\n").encode("utf-8"))
    atomic_private_write(sow, (drafts.sow_markdown + "\n").encode("utf-8"))
    atomic_private_write(
        manifest,
        (
            json.dumps(
                drafts.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    return proposal, sow, manifest
