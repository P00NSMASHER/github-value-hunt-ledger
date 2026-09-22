"""Deterministic human-review packet for Freight Recovery.

The packet joins queue priority with the exact normalized charge and matched
rule evidence a reviewer needs. It is descriptive only: it does not confirm a
finding, authorize external action, or label discrepancies as savings.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from freight.contracts import REVIEW, VALIDATED, canonical_hash
from freight.finding_factory import ChargeRule, FindingFactoryBatch, InvoiceCharge, derive_charge
from freight.review_queue import ReviewQueue, build_review_queue


REVIEW_VALIDATED_FINDING = "REVIEW_VALIDATED_FINDING"
VERIFY_CONTROLLING_AUTHORITY = "VERIFY_CONTROLLING_AUTHORITY"
ADD_APPLICABLE_RULE = "ADD_APPLICABLE_RULE"
RESOLVE_RULE_AMBIGUITY = "RESOLVE_RULE_AMBIGUITY"
INVESTIGATE_EVIDENCE = "INVESTIGATE_EVIDENCE"


@dataclass(frozen=True)
class RuleEvidence:
    rule_hash: str
    authority_document_id: str
    document_source_hash: str
    verified_controlling_authority: bool
    pricing_model: str
    effective_from: str
    effective_to: str | None
    fixed_cents: int | None
    unit_rate_cents: int | None


@dataclass(frozen=True)
class ReviewCase:
    queue_position: int
    priority_class: str
    action_hint: str
    charge_id: str
    invoice_id: str
    shipment_id: str
    customer_id: str
    carrier_id: str
    currency: str
    charge_code: str
    service_date: str
    quantity_units: int
    billed_cents: int
    expected_cents: int | None
    variance_cents: int | None
    decision: str
    reason: str
    charge_source_hash: str
    charge_hash: str
    rule_evidence: tuple[RuleEvidence, ...]
    finding_id: str | None
    finding_proof_hash: str | None
    derivation_hash: str
    queue_item_hash: str
    case_hash: str


@dataclass(frozen=True)
class ReviewPacket:
    buyer_id: str
    business_unit: str
    factory_hash: str
    queue_hash: str
    truth_hash: str
    cases: tuple[ReviewCase, ...]
    packet_hash: str


def _action_hint(decision: str, reason: str) -> str:
    if decision == VALIDATED:
        return REVIEW_VALIDATED_FINDING
    if reason == "AUTHORITY_NOT_VERIFIED":
        return VERIFY_CONTROLLING_AUTHORITY
    if reason == "NO_APPLICABLE_RULE":
        return ADD_APPLICABLE_RULE
    if reason == "AMBIGUOUS_APPLICABLE_RULE":
        return RESOLVE_RULE_AMBIGUITY
    return INVESTIGATE_EVIDENCE


def build_review_packet(
    batch: FindingFactoryBatch,
    queue: ReviewQueue,
    charges: Iterable[InvoiceCharge],
    rules: Iterable[ChargeRule],
) -> ReviewPacket:
    canonical_queue = build_review_queue(batch)
    if queue != canonical_queue:
        raise ValueError("review queue does not match Finding Factory output")

    charge_index: dict[str, InvoiceCharge] = {}
    for charge in charges:
        if charge.charge_id in charge_index:
            raise ValueError("duplicate charge_id in review evidence")
        charge_index[charge.charge_id] = charge

    normalized_rules = tuple(rules)
    rule_index: dict[str, ChargeRule] = {}
    for rule in normalized_rules:
        digest = rule.rule_hash
        if digest in rule_index:
            raise ValueError("duplicate rule proof in review evidence")
        rule_index[digest] = rule

    derivation_index = {item.charge_id: item for item in batch.derivations}
    if len(derivation_index) != len(batch.derivations):
        raise ValueError("duplicate derivation charge_id")

    cases: list[ReviewCase] = []
    for item in queue.items:
        derivation = derivation_index.get(item.charge_id)
        charge = charge_index.get(item.charge_id)
        if derivation is None or charge is None:
            raise ValueError("review evidence missing charge/derivation: " + item.charge_id)
        charge_hash = canonical_hash({"schema": 1, **asdict(charge)})
        if charge_hash != derivation.charge_hash:
            raise ValueError("review charge proof does not match derivation: " + item.charge_id)
        canonical_derivation = derive_charge(charge, normalized_rules)
        if derivation != canonical_derivation:
            raise ValueError(
                "review derivation does not match canonical charge/rule calculation: "
                + item.charge_id
            )

        matched_rules: list[RuleEvidence] = []
        for digest in derivation.matched_rule_hashes:
            rule = rule_index.get(digest)
            if rule is None:
                raise ValueError("matched rule proof missing from review evidence: " + digest)
            matched_rules.append(RuleEvidence(
                rule_hash=digest,
                authority_document_id=rule.authority_document_id,
                document_source_hash=rule.document_source_hash,
                verified_controlling_authority=rule.verified_controlling_authority,
                pricing_model=rule.pricing_model,
                effective_from=rule.effective_from,
                effective_to=rule.effective_to,
                fixed_cents=rule.fixed_cents,
                unit_rate_cents=rule.unit_rate_cents,
            ))

        finding = derivation.finding
        case_body = {
            "schema": 1,
            "factory_hash": batch.factory_hash,
            "queue_hash": queue.queue_hash,
            "queue_position": item.queue_position,
            "priority_class": item.priority_class,
            "action_hint": _action_hint(derivation.decision, derivation.reason),
            "charge": asdict(charge),
            "charge_hash": charge_hash,
            "expected_cents": derivation.expected_cents,
            "variance_cents": derivation.variance_cents,
            "decision": derivation.decision,
            "reason": derivation.reason,
            "rule_evidence": [asdict(rule) for rule in matched_rules],
            "finding_id": finding.finding_id if finding else None,
            "finding_proof_hash": finding.proof_hash if finding else None,
            "derivation_hash": derivation.derivation_hash,
            "queue_item_hash": item.item_hash,
        }
        cases.append(ReviewCase(
            queue_position=item.queue_position,
            priority_class=item.priority_class,
            action_hint=case_body["action_hint"],
            charge_id=charge.charge_id,
            invoice_id=charge.invoice_id,
            shipment_id=charge.shipment_id,
            customer_id=charge.customer_id,
            carrier_id=charge.carrier_id,
            currency=charge.currency,
            charge_code=charge.charge_code,
            service_date=charge.service_date,
            quantity_units=charge.quantity_units,
            billed_cents=charge.billed_cents,
            expected_cents=derivation.expected_cents,
            variance_cents=derivation.variance_cents,
            decision=derivation.decision,
            reason=derivation.reason,
            charge_source_hash=charge.source_hash,
            charge_hash=charge_hash,
            rule_evidence=tuple(matched_rules),
            finding_id=finding.finding_id if finding else None,
            finding_proof_hash=finding.proof_hash if finding else None,
            derivation_hash=derivation.derivation_hash,
            queue_item_hash=item.item_hash,
            case_hash=canonical_hash(case_body),
        ))

    cases_tuple = tuple(cases)
    packet_body = {
        "schema": 1,
        "buyer_id": batch.truth.buyer_id,
        "business_unit": batch.truth.business_unit,
        "factory_hash": batch.factory_hash,
        "queue_hash": queue.queue_hash,
        "truth_hash": batch.truth.truth_hash,
        "cases": [asdict(case) for case in cases_tuple],
    }
    return ReviewPacket(
        buyer_id=batch.truth.buyer_id,
        business_unit=batch.truth.business_unit,
        factory_hash=batch.factory_hash,
        queue_hash=queue.queue_hash,
        truth_hash=batch.truth.truth_hash,
        cases=cases_tuple,
        packet_hash=canonical_hash(packet_body),
    )


def _money(currency: str, cents: int | None) -> str:
    if cents is None:
        return "Not established"
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{currency} {sign}{whole:,}.{fraction:02d}"


def render_review_packet_markdown(packet: ReviewPacket) -> str:
    lines = [
        "# Freight Recovery — Reviewer Work Packet",
        "",
        f"- Buyer: **{packet.buyer_id}**",
        f"- Business unit: **{packet.business_unit}**",
        f"- Packet hash: `{packet.packet_hash}`",
        "",
        "Amounts below are invoice/rule discrepancies for review. They are not realized savings.",
        "",
    ]
    for case in packet.cases:
        lines.extend([
            f"## {case.queue_position}. {case.invoice_id} / {case.charge_code}",
            "",
            f"- Priority: **{case.priority_class}**",
            f"- Required action: **{case.action_hint}**",
            f"- Decision state: **{case.decision}** ({case.reason})",
            f"- Billed: **{_money(case.currency, case.billed_cents)}**",
            f"- Expected under matched rule: **{_money(case.currency, case.expected_cents)}**",
            f"- Supported variance: **{_money(case.currency, case.variance_cents)}**",
            f"- Shipment: `{case.shipment_id}`",
            f"- Charge evidence hash: `{case.charge_source_hash}`",
            f"- Derivation hash: `{case.derivation_hash}`",
        ])
        if case.finding_proof_hash:
            lines.append(f"- Finding proof: `{case.finding_proof_hash}`")
        if case.rule_evidence:
            lines.extend(["", "### Matched rule evidence"])
            for evidence in case.rule_evidence:
                authority = "verified controlling" if evidence.verified_controlling_authority else "not verified controlling"
                lines.extend([
                    f"- **{evidence.authority_document_id}** — {authority}",
                    f"  - Model: {evidence.pricing_model}",
                    f"  - Effective: {evidence.effective_from} to {evidence.effective_to or 'open-ended'}",
                    f"  - Source document hash: `{evidence.document_source_hash}`",
                    f"  - Rule hash: `{evidence.rule_hash}`",
                ])
        else:
            lines.extend(["", "### Matched rule evidence", "- No applicable rule proof was established."])
        lines.append("")
    return "\n".join(lines)
