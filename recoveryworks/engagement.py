"""Customer engagement charter for RecoveryWorks / RecoveryOS.

The charter authorizes analysis of named recovery branches and named source-data
kinds. It deliberately cannot authorize external recovery actions. Those always
require a separate scope-bound RecoveryActionAuthorization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum

from .models import Branch, canonical_hash

MAX_ENGAGEMENT_DAYS = 366
EXTERNAL_ACTION_POLICY = "SEPARATE_CUSTOMER_APPROVAL_REQUIRED"


class EngagementState(str, Enum):
    NOT_YET_ACTIVE = "NOT_YET_ACTIVE"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class RecoveryEngagementCharter:
    engagement_id: str
    client_id: str
    authorized_branches: tuple[str, ...]
    authorized_source_kinds: tuple[str, ...]
    action_approver_roles: tuple[str, ...]
    effective_from: str
    expires_on: str
    customer_data_authorized: bool
    report_generation_allowed: bool
    external_action_authorized: bool
    external_action_policy: str
    charter_hash: str


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _parse_date(name: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(name + " must be ISO date YYYY-MM-DD") from exc


def issue_engagement_charter(
    *,
    engagement_id: str,
    client_id: str,
    authorized_branches: tuple[Branch, ...],
    authorized_source_kinds: tuple[str, ...],
    action_approver_roles: tuple[str, ...],
    effective_from: str,
    expires_on: str,
    max_engagement_days: int = MAX_ENGAGEMENT_DAYS,
) -> RecoveryEngagementCharter:
    _required("engagement_id", engagement_id)
    _required("client_id", client_id)
    if not authorized_branches:
        raise ValueError("at least one authorized branch is required")
    branch_values = tuple(sorted({branch.value for branch in authorized_branches}))
    if len(branch_values) != len(authorized_branches):
        raise ValueError("duplicate authorized branch")

    source_kinds = tuple(sorted(_required("source kind", kind) for kind in authorized_source_kinds))
    if not source_kinds:
        raise ValueError("at least one authorized source kind is required")
    if len(source_kinds) != len(set(source_kinds)):
        raise ValueError("duplicate authorized source kind")

    roles = tuple(sorted(_required("action approver role", role) for role in action_approver_roles))
    if not roles:
        raise ValueError("at least one action approver role is required")
    if len(roles) != len(set(roles)):
        raise ValueError("duplicate action approver role")

    effective = _parse_date("effective_from", effective_from)
    expires = _parse_date("expires_on", expires_on)
    if expires < effective:
        raise ValueError("expires_on cannot precede effective_from")
    if max_engagement_days < 1:
        raise ValueError("max_engagement_days must be positive")
    if (expires - effective).days > max_engagement_days:
        raise ValueError("engagement validity exceeds internal maximum")

    body = {
        "engagement_id": engagement_id.strip(),
        "client_id": client_id.strip(),
        "authorized_branches": list(branch_values),
        "authorized_source_kinds": list(source_kinds),
        "action_approver_roles": list(roles),
        "effective_from": effective_from,
        "expires_on": expires_on,
        "customer_data_authorized": True,
        "report_generation_allowed": True,
        "external_action_authorized": False,
        "external_action_policy": EXTERNAL_ACTION_POLICY,
    }
    return RecoveryEngagementCharter(
        engagement_id=body["engagement_id"],
        client_id=body["client_id"],
        authorized_branches=branch_values,
        authorized_source_kinds=source_kinds,
        action_approver_roles=roles,
        effective_from=effective_from,
        expires_on=expires_on,
        customer_data_authorized=True,
        report_generation_allowed=True,
        external_action_authorized=False,
        external_action_policy=EXTERNAL_ACTION_POLICY,
        charter_hash=canonical_hash(body),
    )


def verify_engagement_charter(
    charter: RecoveryEngagementCharter,
    *,
    as_of_date: str,
) -> EngagementState:
    body = asdict(charter)
    digest = body.pop("charter_hash")
    body["authorized_branches"] = list(body["authorized_branches"])
    body["authorized_source_kinds"] = list(body["authorized_source_kinds"])
    body["action_approver_roles"] = list(body["action_approver_roles"])
    if canonical_hash(body) != digest:
        raise ValueError("engagement charter hash mismatch")
    if charter.customer_data_authorized is not True:
        raise ValueError("engagement does not authorize customer data")
    if charter.report_generation_allowed is not True:
        raise ValueError("engagement does not authorize report generation")
    if charter.external_action_authorized is not False:
        raise ValueError("engagement charter must not pre-authorize external action")
    if charter.external_action_policy != EXTERNAL_ACTION_POLICY:
        raise ValueError("unexpected external action policy")

    canonical_branches = tuple(sorted(set(charter.authorized_branches)))
    canonical_kinds = tuple(sorted(set(charter.authorized_source_kinds)))
    canonical_roles = tuple(sorted(set(charter.action_approver_roles)))
    if canonical_branches != charter.authorized_branches:
        raise ValueError("authorized branches are not canonical")
    if canonical_kinds != charter.authorized_source_kinds:
        raise ValueError("authorized source kinds are not canonical")
    if canonical_roles != charter.action_approver_roles:
        raise ValueError("action approver roles are not canonical")
    for value in charter.authorized_branches:
        Branch(value)

    as_of = _parse_date("as_of_date", as_of_date)
    effective = _parse_date("effective_from", charter.effective_from)
    expires = _parse_date("expires_on", charter.expires_on)
    if as_of < effective:
        return EngagementState.NOT_YET_ACTIVE
    if as_of > expires:
        return EngagementState.EXPIRED
    return EngagementState.ACTIVE


def assert_engagement_allows_scan(
    charter: RecoveryEngagementCharter,
    *,
    client_id: str,
    branches: tuple[Branch, ...],
    source_kinds: tuple[str, ...],
    as_of_date: str,
) -> None:
    state = verify_engagement_charter(charter, as_of_date=as_of_date)
    if state is not EngagementState.ACTIVE:
        raise ValueError("engagement is not ACTIVE: " + state.value)
    if charter.client_id != client_id:
        raise ValueError("engagement client mismatch")
    allowed_branches = set(charter.authorized_branches)
    requested_branches = {branch.value for branch in branches}
    if not requested_branches.issubset(allowed_branches):
        raise ValueError("scan branch is outside engagement authorization")
    allowed_kinds = set(charter.authorized_source_kinds)
    if not set(source_kinds).issubset(allowed_kinds):
        raise ValueError("scan source kind is outside engagement authorization")


def assert_engagement_allows_action_approval(
    charter: RecoveryEngagementCharter,
    *,
    client_id: str,
    branch: Branch,
    approver_role: str,
    as_of_date: str,
) -> None:
    state = verify_engagement_charter(charter, as_of_date=as_of_date)
    if state is not EngagementState.ACTIVE:
        raise ValueError("engagement is not ACTIVE: " + state.value)
    if charter.client_id != client_id:
        raise ValueError("engagement client mismatch")
    if branch.value not in charter.authorized_branches:
        raise ValueError("finding branch is outside engagement authorization")
    if approver_role not in charter.action_approver_roles:
        raise ValueError("approver_role is outside engagement authorization")
