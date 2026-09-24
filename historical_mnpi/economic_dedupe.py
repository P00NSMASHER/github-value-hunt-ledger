"""Economic-transaction deduplication for historical public-record research.

Step 11 detects when multiple normalized rows may describe the same underlying
trade while preserving every original row/source proof.

Automatic comparison is conservative. It produces a proposal only. Building a
cluster requires explicit pairwise SAME_TRANSACTION decisions for every member
pair; fuzzy transitive closure cannot silently merge rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from itertools import combinations
import re

from .case_model import CaseRegistry
from .entity_resolution import EntityKind, EntityRegistry
from .raw_artifacts import RawArtifactManifest
from .source_registry import SourceRegistry, canonical_hash
from .transaction_model import HistoricalTransaction, verify_transaction_provenance


class DedupeRelation(str, Enum):
    EXACT_SAME = "EXACT_SAME"
    POSSIBLE_SAME = "POSSIBLE_SAME"
    DISTINCT = "DISTINCT"
    INSUFFICIENT = "INSUFFICIENT"


class DedupeDecisionType(str, Enum):
    SAME_TRANSACTION = "SAME_TRANSACTION"
    DISTINCT = "DISTINCT"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class DedupeProposal:
    left_trade_id: str
    left_transaction_hash: str
    right_trade_id: str
    right_transaction_hash: str
    trader_entity_id: str | None
    issuer_entity_id: str | None
    relation: DedupeRelation
    matching_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]
    proposal_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "left_trade_id": self.left_trade_id,
            "left_transaction_hash": self.left_transaction_hash,
            "right_trade_id": self.right_trade_id,
            "right_transaction_hash": self.right_transaction_hash,
            "trader_entity_id": self.trader_entity_id,
            "issuer_entity_id": self.issuer_entity_id,
            "relation": self.relation.value,
            "matching_fields": list(self.matching_fields),
            "conflicting_fields": list(self.conflicting_fields),
            "reason_codes": list(self.reason_codes),
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.proposal_hash:
            raise ValueError("dedupe proposal hash mismatch")


@dataclass(frozen=True)
class DedupeDecision:
    proposal_hash: str
    left_trade_id: str
    left_transaction_hash: str
    right_trade_id: str
    right_transaction_hash: str
    trader_entity_id: str | None
    issuer_entity_id: str | None
    decision: DedupeDecisionType
    reviewer_id: str
    rationale: str
    decision_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "proposal_hash": self.proposal_hash,
            "left_trade_id": self.left_trade_id,
            "left_transaction_hash": self.left_transaction_hash,
            "right_trade_id": self.right_trade_id,
            "right_transaction_hash": self.right_transaction_hash,
            "trader_entity_id": self.trader_entity_id,
            "issuer_entity_id": self.issuer_entity_id,
            "decision": self.decision.value,
            "reviewer_id": self.reviewer_id,
            "rationale": self.rationale,
        }

    def verify_integrity(self) -> None:
        if canonical_hash(self.integrity_body()) != self.decision_hash:
            raise ValueError("dedupe decision hash mismatch")


@dataclass(frozen=True)
class EconomicTransactionMember:
    trade_id: str
    transaction_hash: str
    case_id: str
    source_ref_hash: str
    status_ref_hash: str
    fact_status: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **self.__dict__})


@dataclass(frozen=True)
class EconomicTransactionCluster:
    economic_transaction_id: str
    trader_entity_id: str
    issuer_entity_id: str
    members: tuple[EconomicTransactionMember, ...]
    same_transaction_decision_hashes: tuple[str, ...]
    cluster_hash: str

    def integrity_body(self) -> dict:
        return {
            "schema": 1,
            "trader_entity_id": self.trader_entity_id,
            "issuer_entity_id": self.issuer_entity_id,
            "member_hashes": sorted(x.proof_hash for x in self.members),
            "same_transaction_decision_hashes": sorted(
                self.same_transaction_decision_hashes
            ),
        }

    def verify_integrity(self) -> None:
        expected = canonical_hash(self.integrity_body())
        if self.cluster_hash != expected:
            raise ValueError("economic transaction cluster hash mismatch")
        if self.economic_transaction_id != "economic:" + expected:
            raise ValueError("economic transaction id/hash mismatch")


def _date_interval(tx: HistoricalTransaction) -> tuple[date, date]:
    if tx.trade_timestamp is not None:
        day = datetime.fromisoformat(
            tx.trade_timestamp.replace("Z", "+00:00")
        ).date()
        return day, day
    if tx.trade_date is not None:
        day = date.fromisoformat(tx.trade_date)
        return day, day
    return (
        date.fromisoformat(tx.trade_date_range_start or ""),
        date.fromisoformat(tx.trade_date_range_end or ""),
    )


def _temporal_relation(
    left: HistoricalTransaction,
    right: HistoricalTransaction,
) -> tuple[bool, bool]:
    """Return (compatible_time, exact_instant_match).

    Date-only or date-range equality is never treated as an exact instant.
    Multiple economically identical fills can occur on the same trading day,
    so coarse temporal agreement may support POSSIBLE_SAME but never
    EXACT_SAME.
    """
    left_start, left_end = _date_interval(left)
    right_start, right_end = _date_interval(right)
    if left_end < right_start or right_end < left_start:
        return False, False

    if left.trade_timestamp is not None and right.trade_timestamp is not None:
        same = (
            datetime.fromisoformat(left.trade_timestamp.replace("Z", "+00:00"))
            == datetime.fromisoformat(right.trade_timestamp.replace("Z", "+00:00"))
        )
        return same, same

    # Same-day/date-range overlap is compatible, but not an exact trade instant.
    return True, False


def _economic_values(tx: HistoricalTransaction) -> dict[str, str]:
    values = {}
    if tx.instrument_type.value != "UNKNOWN":
        values["instrument_type"] = tx.instrument_type.value
    if tx.side.value != "UNKNOWN":
        values["side"] = tx.side.value
    for name in (
        "quantity",
        "execution_price",
        "trade_amount",
        "option_strike",
        "option_expiry",
    ):
        value = getattr(tx, name)
        if value is not None:
            values[name] = value
    return values


def _proposal_body(
    left: HistoricalTransaction,
    right: HistoricalTransaction,
    *,
    trader_entity_id: str | None,
    issuer_entity_id: str | None,
    relation: DedupeRelation,
    matching_fields: tuple[str, ...],
    conflicting_fields: tuple[str, ...],
    reason_codes: tuple[str, ...],
) -> dict:
    ordered = sorted(
        ((left.trade_id, left.proof_hash), (right.trade_id, right.proof_hash))
    )
    return {
        "schema": 1,
        "left_trade_id": ordered[0][0],
        "left_transaction_hash": ordered[0][1],
        "right_trade_id": ordered[1][0],
        "right_transaction_hash": ordered[1][1],
        "trader_entity_id": trader_entity_id,
        "issuer_entity_id": issuer_entity_id,
        "relation": relation.value,
        "matching_fields": list(sorted(matching_fields)),
        "conflicting_fields": list(sorted(conflicting_fields)),
        "reason_codes": list(sorted(reason_codes)),
    }


def _make_proposal(
    left: HistoricalTransaction,
    right: HistoricalTransaction,
    *,
    trader_entity_id: str | None,
    issuer_entity_id: str | None,
    relation: DedupeRelation,
    matching_fields: tuple[str, ...],
    conflicting_fields: tuple[str, ...],
    reason_codes: tuple[str, ...],
) -> DedupeProposal:
    body = _proposal_body(
        left,
        right,
        trader_entity_id=trader_entity_id,
        issuer_entity_id=issuer_entity_id,
        relation=relation,
        matching_fields=matching_fields,
        conflicting_fields=conflicting_fields,
        reason_codes=reason_codes,
    )
    return DedupeProposal(
        left_trade_id=body["left_trade_id"],
        left_transaction_hash=body["left_transaction_hash"],
        right_trade_id=body["right_trade_id"],
        right_transaction_hash=body["right_transaction_hash"],
        trader_entity_id=trader_entity_id,
        issuer_entity_id=issuer_entity_id,
        relation=relation,
        matching_fields=tuple(sorted(matching_fields)),
        conflicting_fields=tuple(sorted(conflicting_fields)),
        reason_codes=tuple(sorted(reason_codes)),
        proposal_hash=canonical_hash(body),
    )


def propose_transaction_dedupe(
    left: HistoricalTransaction,
    right: HistoricalTransaction,
    *,
    entities: EntityRegistry,
    cases: CaseRegistry,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> DedupeProposal:
    if left.trade_id == right.trade_id:
        raise ValueError("dedupe comparison requires distinct trade_ids")

    for tx in (left, right):
        verify_transaction_provenance(
            tx,
            cases=cases,
            source_registry=source_registry,
            artifact_manifest=artifact_manifest,
        )

    reasons = []
    try:
        left_trader = entities.resolved_entity_for(
            left.case_id, left.trader_party_id, EntityKind.PERSON
        )
        right_trader = entities.resolved_entity_for(
            right.case_id, right.trader_party_id, EntityKind.PERSON
        )
        left_issuer = entities.resolved_entity_for(
            left.case_id, left.issuer_id, EntityKind.ISSUER
        )
        right_issuer = entities.resolved_entity_for(
            right.case_id, right.issuer_id, EntityKind.ISSUER
        )
    except ValueError:
        relation = DedupeRelation.INSUFFICIENT
        reasons.append("IDENTITY_NOT_RESOLVED")
        return _make_proposal(
            left,
            right,
            trader_entity_id=None,
            issuer_entity_id=None,
            relation=relation,
            matching_fields=(),
            conflicting_fields=(),
            reason_codes=tuple(reasons),
        )

    if left_trader.entity_id != right_trader.entity_id:
        relation = DedupeRelation.DISTINCT
        reasons.append("DIFFERENT_CANONICAL_TRADER")
    elif left_issuer.entity_id != right_issuer.entity_id:
        relation = DedupeRelation.DISTINCT
        reasons.append("DIFFERENT_CANONICAL_ISSUER")
    else:
        compatible_time, exact_time = _temporal_relation(left, right)
        if not compatible_time:
            relation = DedupeRelation.DISTINCT
            reasons.append("NON_OVERLAPPING_TRADE_TIME")
        else:
            left_values = _economic_values(left)
            right_values = _economic_values(right)
            shared = sorted(set(left_values) & set(right_values))
            matching = tuple(
                name for name in shared
                if left_values[name] == right_values[name]
            )
            conflicting = tuple(
                name for name in shared
                if left_values[name] != right_values[name]
            )
            strong_anchor_fields = {
                "quantity",
                "execution_price",
                "trade_amount",
                "option_strike",
                "option_expiry",
            }
            strong_matches = strong_anchor_fields.intersection(matching)
            exact_anchor_ok = (
                "quantity" in strong_matches
                and (
                    "execution_price" in strong_matches
                    or "trade_amount" in strong_matches
                )
                and (
                    "instrument_type" in matching
                    or "side" in matching
                )
            )
            option_types = {
                "CALL_OPTION",
                "PUT_OPTION",
                "OPTION_OTHER",
            }
            option_contract_requires_identity = (
                left.instrument_type.value in option_types
                or right.instrument_type.value in option_types
            )
            if option_contract_requires_identity:
                option_contract_identified = (
                    "instrument_type" in matching
                    and "option_strike" in matching
                    and "option_expiry" in matching
                )
                if not option_contract_identified:
                    exact_anchor_ok = False
                    reasons.append("OPTION_CONTRACT_NOT_FULLY_IDENTIFIED")

            if conflicting:
                relation = DedupeRelation.DISTINCT
                reasons.append("CONFLICTING_ECONOMIC_FIELDS")
            elif exact_time and exact_anchor_ok:
                relation = DedupeRelation.EXACT_SAME
                reasons.append("EXACT_TIMESTAMP_AND_STRONG_ECONOMIC_ANCHORS")
            elif strong_matches:
                relation = DedupeRelation.POSSIBLE_SAME
                reasons.append("COMPATIBLE_TIME_AND_STRONG_ECONOMIC_MATCH")
            elif matching:
                relation = DedupeRelation.INSUFFICIENT
                reasons.append("ONLY_GENERIC_ECONOMIC_FIELDS_MATCH")
            else:
                relation = DedupeRelation.INSUFFICIENT
                reasons.append("NO_SHARED_ECONOMIC_DISCRIMINATOR")

            return _make_proposal(
                left,
                right,
                trader_entity_id=left_trader.entity_id,
                issuer_entity_id=left_issuer.entity_id,
                relation=relation,
                matching_fields=matching,
                conflicting_fields=conflicting,
                reason_codes=tuple(reasons),
            )

    return _make_proposal(
        left,
        right,
        trader_entity_id=(
            left_trader.entity_id
            if left_trader.entity_id == right_trader.entity_id else None
        ),
        issuer_entity_id=(
            left_issuer.entity_id
            if left_issuer.entity_id == right_issuer.entity_id else None
        ),
        relation=relation,
        matching_fields=(),
        conflicting_fields=(),
        reason_codes=tuple(reasons),
    )


def decide_dedupe(
    proposal: DedupeProposal,
    *,
    decision: DedupeDecisionType,
    reviewer_id: str,
    rationale: str,
) -> DedupeDecision:
    proposal.verify_integrity()
    if not reviewer_id.strip() or not rationale.strip():
        raise ValueError("reviewer_id and rationale are required")
    if decision is DedupeDecisionType.SAME_TRANSACTION and proposal.relation not in {
        DedupeRelation.EXACT_SAME,
        DedupeRelation.POSSIBLE_SAME,
    }:
        raise ValueError(
            "SAME_TRANSACTION requires exact/possible duplicate proposal"
        )
    body = {
        "schema": 1,
        "proposal_hash": proposal.proposal_hash,
        "left_trade_id": proposal.left_trade_id,
        "left_transaction_hash": proposal.left_transaction_hash,
        "right_trade_id": proposal.right_trade_id,
        "right_transaction_hash": proposal.right_transaction_hash,
        "trader_entity_id": proposal.trader_entity_id,
        "issuer_entity_id": proposal.issuer_entity_id,
        "decision": decision.value,
        "reviewer_id": reviewer_id.strip(),
        "rationale": rationale.strip(),
    }
    return DedupeDecision(
        proposal_hash=proposal.proposal_hash,
        left_trade_id=proposal.left_trade_id,
        left_transaction_hash=proposal.left_transaction_hash,
        right_trade_id=proposal.right_trade_id,
        right_transaction_hash=proposal.right_transaction_hash,
        trader_entity_id=proposal.trader_entity_id,
        issuer_entity_id=proposal.issuer_entity_id,
        decision=decision,
        reviewer_id=reviewer_id.strip(),
        rationale=rationale.strip(),
        decision_hash=canonical_hash(body),
    )


def build_economic_transaction_cluster(
    transactions: tuple[HistoricalTransaction, ...] | list[HistoricalTransaction],
    *,
    decisions: tuple[DedupeDecision, ...] | list[DedupeDecision],
    trader_entity_id: str,
    issuer_entity_id: str,
) -> EconomicTransactionCluster:
    txs = tuple(sorted(transactions, key=lambda tx: tx.trade_id))
    if len(txs) < 2:
        raise ValueError("economic cluster requires at least two transactions")
    if len({tx.trade_id for tx in txs}) != len(txs):
        raise ValueError("duplicate trade_id in economic cluster")

    tx_by_id = {tx.trade_id: tx for tx in txs}
    decision_map = {}
    for decision in decisions:
        decision.verify_integrity()
        if (
            decision.left_trade_id not in tx_by_id
            or decision.right_trade_id not in tx_by_id
        ):
            raise ValueError("dedupe decision references trade outside cluster")
        if (
            decision.left_transaction_hash
            != tx_by_id[decision.left_trade_id].proof_hash
            or decision.right_transaction_hash
            != tx_by_id[decision.right_trade_id].proof_hash
        ):
            raise ValueError(
                "dedupe decision transaction hash does not match current cluster row"
            )
        if (
            decision.trader_entity_id != trader_entity_id
            or decision.issuer_entity_id != issuer_entity_id
        ):
            raise ValueError(
                "dedupe decision canonical entity identity mismatch"
            )
        key = tuple(sorted((decision.left_trade_id, decision.right_trade_id)))
        if key in decision_map:
            raise ValueError("duplicate pairwise dedupe decision")
        decision_map[key] = decision

    needed_pairs = {
        tuple(sorted((left.trade_id, right.trade_id)))
        for left, right in combinations(txs, 2)
    }
    if set(decision_map) != needed_pairs:
        raise ValueError(
            "economic cluster requires a complete pairwise decision set"
        )
    for key, decision in decision_map.items():
        if decision.decision is not DedupeDecisionType.SAME_TRANSACTION:
            raise ValueError(
                "economic cluster contains non-SAME_TRANSACTION decision"
            )

    members = tuple(
        EconomicTransactionMember(
            trade_id=tx.trade_id,
            transaction_hash=tx.proof_hash,
            case_id=tx.case_id,
            source_ref_hash=tx.source_ref.proof_hash,
            status_ref_hash=tx.status_ref.proof_hash,
            fact_status=tx.fact_status.value,
        )
        for tx in txs
    )
    body = {
        "schema": 1,
        "trader_entity_id": trader_entity_id,
        "issuer_entity_id": issuer_entity_id,
        "member_hashes": sorted(x.proof_hash for x in members),
        "same_transaction_decision_hashes": sorted(
            decision.decision_hash for decision in decision_map.values()
        ),
    }
    cluster_hash = canonical_hash(body)
    return EconomicTransactionCluster(
        economic_transaction_id="economic:" + cluster_hash,
        trader_entity_id=trader_entity_id,
        issuer_entity_id=issuer_entity_id,
        members=members,
        same_transaction_decision_hashes=tuple(sorted(
            decision.decision_hash for decision in decision_map.values()
        )),
        cluster_hash=cluster_hash,
    )


__all__ = [
    "DedupeDecision",
    "DedupeDecisionType",
    "DedupeProposal",
    "DedupeRelation",
    "EconomicTransactionCluster",
    "EconomicTransactionMember",
    "build_economic_transaction_cluster",
    "decide_dedupe",
    "propose_transaction_dedupe",
]
