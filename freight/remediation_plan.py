"""Deterministic remediation plans for Freight Recovery review cases.

A remediation plan is derived only from cases already routed to evidence
remediation. It never mutates or promotes a finding. Completing remediation
requires corrected inputs and a fresh audit workflow run.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from freight.contracts import canonical_hash
from freight.review_packet import (
    ADD_APPLICABLE_RULE,
    INVESTIGATE_EVIDENCE,
    RESOLVE_RULE_AMBIGUITY,
    VERIFY_CONTROLLING_AUTHORITY,
    ReviewPacket,
)
from freight.review_routing import ReviewRouting, route_review_packet


VERIFY_AUTHORITY_AND_RERUN = "VERIFY_AUTHORITY_AND_RERUN"
ADD_RULE_AND_RERUN = "ADD_RULE_AND_RERUN"
RESOLVE_RULE_SET_AND_RERUN = "RESOLVE_RULE_SET_AND_RERUN"
INVESTIGATE_AND_RERUN = "INVESTIGATE_AND_RERUN"


@dataclass(frozen=True)
class RemediationItem:
    case_hash: str
    queue_position: int
    invoice_id: str
    shipment_id: str
    charge_id: str
    charge_code: str
    action_hint: str
    remediation_action: str
    evidence_required: tuple[str, ...]
    current_expected_cents: int | None
    current_variance_cents: int | None
    matched_rule_hashes: tuple[str, ...]
    rerun_required: bool
    item_hash: str


@dataclass(frozen=True)
class RemediationPlan:
    review_packet_hash: str
    review_routing_hash: str
    review_route: str
    buyer_review_case_count: int
    remediation_case_count: int
    rerun_required: bool
    items: tuple[RemediationItem, ...]
    plan_hash: str


def _instructions(action_hint: str) -> tuple[str, tuple[str, ...]]:
    if action_hint == VERIFY_CONTROLLING_AUTHORITY:
        return (
            VERIFY_AUTHORITY_AND_RERUN,
            (
                "Documented determination that identifies the controlling authority for this charge and service date.",
                "Source-document SHA-256 and trusted scope/identity metadata for the authority used after verification.",
            ),
        )
    if action_hint == ADD_APPLICABLE_RULE:
        return (
            ADD_RULE_AND_RERUN,
            (
                "Applicable governing rate/rule for this charge code and service date.",
                "Source-document SHA-256 plus trusted customer/carrier/currency and authority-document context.",
            ),
        )
    if action_hint == RESOLVE_RULE_AMBIGUITY:
        return (
            RESOLVE_RULE_SET_AND_RERUN,
            (
                "Documented controlling-authority decision resolving the overlapping applicable rules.",
                "Corrected normalized rule set whose effective scope yields one applicable rule for this case.",
            ),
        )
    if action_hint == INVESTIGATE_EVIDENCE:
        return (
            INVESTIGATE_AND_RERUN,
            (
                "Case-specific invoice, shipment, accessorial or authority evidence sufficient to establish one supported expected charge or a defensible no-finding result.",
            ),
        )
    raise ValueError("unsupported remediation action hint: " + action_hint)


def build_remediation_plan(
    packet: ReviewPacket,
    routing: ReviewRouting,
) -> RemediationPlan:
    canonical_routing = route_review_packet(packet)
    if routing != canonical_routing:
        raise ValueError("review routing does not match canonical review packet")

    case_index = {case.case_hash: case for case in packet.cases}
    if len(case_index) != len(packet.cases):
        raise ValueError("duplicate review case hash")

    items: list[RemediationItem] = []
    for case_hash in routing.remediation_case_hashes:
        case = case_index.get(case_hash)
        if case is None:
            raise ValueError("remediation route references unknown review case")
        remediation_action, evidence_required = _instructions(case.action_hint)
        rule_hashes = tuple(rule.rule_hash for rule in case.rule_evidence)
        body = {
            "schema": 1,
            "review_packet_hash": packet.packet_hash,
            "review_routing_hash": routing.routing_hash,
            "case_hash": case.case_hash,
            "queue_position": case.queue_position,
            "invoice_id": case.invoice_id,
            "shipment_id": case.shipment_id,
            "charge_id": case.charge_id,
            "charge_code": case.charge_code,
            "action_hint": case.action_hint,
            "remediation_action": remediation_action,
            "evidence_required": evidence_required,
            "current_expected_cents": case.expected_cents,
            "current_variance_cents": case.variance_cents,
            "matched_rule_hashes": rule_hashes,
            "rerun_required": True,
        }
        items.append(RemediationItem(
            case_hash=case.case_hash,
            queue_position=case.queue_position,
            invoice_id=case.invoice_id,
            shipment_id=case.shipment_id,
            charge_id=case.charge_id,
            charge_code=case.charge_code,
            action_hint=case.action_hint,
            remediation_action=remediation_action,
            evidence_required=evidence_required,
            current_expected_cents=case.expected_cents,
            current_variance_cents=case.variance_cents,
            matched_rule_hashes=rule_hashes,
            rerun_required=True,
            item_hash=canonical_hash(body),
        ))

    items_tuple = tuple(items)
    body = {
        "schema": 1,
        "review_packet_hash": packet.packet_hash,
        "review_routing_hash": routing.routing_hash,
        "review_route": routing.route,
        "buyer_review_case_count": routing.buyer_review_case_count,
        "remediation_case_count": routing.evidence_remediation_case_count,
        "rerun_required": routing.rerun_required,
        "items": [asdict(item) for item in items_tuple],
    }
    return RemediationPlan(
        review_packet_hash=packet.packet_hash,
        review_routing_hash=routing.routing_hash,
        review_route=routing.route,
        buyer_review_case_count=routing.buyer_review_case_count,
        remediation_case_count=routing.evidence_remediation_case_count,
        rerun_required=routing.rerun_required,
        items=items_tuple,
        plan_hash=canonical_hash(body),
    )


def _money(cents: int | None) -> str:
    if cents is None:
        return "Not established"
    return "$" + format(cents / 100, ",.2f")


def render_remediation_plan_markdown(plan: RemediationPlan) -> str:
    lines = [
        "# Freight Recovery — Evidence Remediation Plan",
        "",
        f"- Review route: **{plan.review_route}**",
        f"- Buyer-review-ready cases: **{plan.buyer_review_case_count}**",
        f"- Evidence-remediation cases: **{plan.remediation_case_count}**",
        "- Rerun required: **" + ("yes" if plan.rerun_required else "no") + "**",
        f"- Plan hash: `{plan.plan_hash}`",
        "",
    ]
    if not plan.items:
        lines.extend([
            "No evidence-remediation cases are present.",
            "",
        ])
        return "\n".join(lines)

    lines.extend([
        "Remediation changes audit inputs. Do not manually promote these cases; rerun the audit workflow after the required evidence is corrected or added.",
        "",
    ])
    for item in plan.items:
        lines.extend([
            f"## {item.queue_position}. {item.invoice_id} / {item.charge_code}",
            "",
            f"- Remediation action: **{item.remediation_action}**",
            f"- Current expected amount: **{_money(item.current_expected_cents)}**",
            f"- Current supported variance: **{_money(item.current_variance_cents)}**",
            f"- Review case hash: `{item.case_hash}`",
            "",
            "### Evidence required",
        ])
        lines.extend(f"- {evidence}" for evidence in item.evidence_required)
        lines.extend([
            "",
            "After evidence is corrected or added, rerun the audit workflow. Any prior finding/run hashes remain historical and must not be edited in place.",
            "",
        ])
    lines.append("Discrepancy amounts are not realized savings.")
    lines.append("")
    return "\n".join(lines)
