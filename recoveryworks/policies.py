"""Cross-branch controls for RecoveryOS.

No branch may submit, appeal, demand, dispute, contact, or otherwise act against a
counterparty without explicit customer authorization and a human review gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Branch, RecoveryMode, RecoveryFinding, FindingState


@dataclass(frozen=True)
class BranchPolicy:
    branch: Branch
    mode: RecoveryMode
    reviewer_role: str
    source_version_required: bool = True
    deterministic_money_required: bool = True
    external_action_requires_authorization: bool = True
    sensitive_data: bool = False
    professional_review_note: str | None = None


POLICIES: dict[Branch, BranchPolicy] = {
    Branch.FREIGHT: BranchPolicy(Branch.FREIGHT, RecoveryMode.OVERPAYMENT, "freight_reviewer"),
    Branch.PAYER: BranchPolicy(
        Branch.PAYER,
        RecoveryMode.UNDERPAYMENT,
        "payer_recovery_reviewer",
        sensitive_data=True,
        professional_review_note="Appeal/claim submission remains customer-controlled.",
    ),
    Branch.UTILITY: BranchPolicy(Branch.UTILITY, RecoveryMode.OVERPAYMENT, "utility_tariff_reviewer"),
    Branch.AP: BranchPolicy(Branch.AP, RecoveryMode.OVERPAYMENT, "ap_recovery_reviewer"),
    Branch.CONSTRUCTION: BranchPolicy(
        Branch.CONSTRUCTION,
        RecoveryMode.UNDERPAYMENT,
        "construction_claims_reviewer",
        professional_review_note="Entitlement and schedule-causation conclusions require qualified human review.",
    ),
    Branch.DUTY: BranchPolicy(
        Branch.DUTY,
        RecoveryMode.OVERPAYMENT,
        "customs_reviewer",
        professional_review_note="Customs classification/refund action requires appropriate broker/counsel review.",
    ),
    Branch.SAAS: BranchPolicy(
        Branch.SAAS,
        RecoveryMode.OVERPAYMENT,
        "saas_contract_reviewer",
    ),
    Branch.TELECOM: BranchPolicy(
        Branch.TELECOM,
        RecoveryMode.OVERPAYMENT,
        "telecom_billing_reviewer",
    ),
    Branch.REBATE: BranchPolicy(
        Branch.REBATE,
        RecoveryMode.UNDERPAYMENT,
        "rebate_recovery_reviewer",
    ),
    Branch.LEASE: BranchPolicy(
        Branch.LEASE,
        RecoveryMode.OVERPAYMENT,
        "lease_recovery_reviewer",
        professional_review_note="Lease interpretation and CAM/operating-expense entitlement require qualified human review.",
    ),
}


def policy_for(branch: Branch) -> BranchPolicy:
    return POLICIES[branch]


def assert_review_ready(finding: RecoveryFinding) -> None:
    if finding.potential_recovery_cents <= 0:
        raise ValueError("finding has no positive recovery amount")
    if finding.state not in {FindingState.REVIEW, FindingState.VALIDATED}:
        raise ValueError("finding is not reviewable")


def assert_claim_authorizable(finding: RecoveryFinding, reviewer_approved: bool) -> None:
    if finding.state is not FindingState.VALIDATED:
        raise ValueError("only VALIDATED findings may be authorized")
    if not reviewer_approved:
        raise ValueError("human reviewer approval is required")
    if finding.rule is None or not finding.rule.verified_controlling:
        raise ValueError("verified controlling rule is required")
    if not all(ref.verified for ref in finding.evidence):
        raise ValueError("all load-bearing evidence must be verified")
