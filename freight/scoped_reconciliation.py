"""Reference/scoped reconciliation on top of the pinned RecoveryWorks kernel.

Different suppliers may reuse payment numbers. This controller partitions before
calling the existing bounded exact-money algorithm and does not manufacture a
bank payment by grouping invoices into self-confirming settlement rows.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from freight.contracts import canonical_hash
from recoveryworks.reconciliation_kernel import (
    ManyToOneConfig, ReconConfig, ReconTxn, reconcile,
)


@dataclass(frozen=True)
class ScopedTxn:
    txn: ReconTxn
    buyer_id: str
    business_unit: str
    counterparty_id: str
    origin: str  # source-declared ORIGINAL_INVOICE, BANK_CLEARED, CUSTOMER_DECLARATION

    def __post_init__(self) -> None:
        for value in (self.buyer_id, self.business_unit, self.counterparty_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("buyer/unit/counterparty scope is required")
        if self.origin not in {"ORIGINAL_INVOICE", "BANK_CLEARED", "CUSTOMER_DECLARATION"}:
            raise ValueError("unsupported source origin")


@dataclass(frozen=True)
class ScopeReconciliation:
    internal_count: int
    counterpart_count: int
    matched_internal: int
    matched_counterparts: int
    unmatched_internal: int
    unmatched_counterparts: int
    groups_matched: int
    matched_by_rule: dict[str, int]
    scope_review_groups: int
    bound_exceeded_groups: int
    mismatched_references: int
    proven_cleared_payment_count: int
    independent_payment_accuracy: float | None
    result_hash: str
    bank_labeled_counterpart_matches: int = 0


def _group_key(row: ScopedTxn) -> tuple[str, ...] | None:
    ref = row.txn.reference
    if not isinstance(ref, str) or not ref.strip():
        return None
    return (row.buyer_id, row.business_unit, row.counterparty_id,
            row.txn.currency, ref.strip())


def reconcile_scoped(
    internal: Iterable[ScopedTxn],
    counterpart: Iterable[ScopedTxn],
    *, group_size_limit: int = 32,
    date_window_days: int = 30,
) -> ScopeReconciliation:
    if type(group_size_limit) is not int or not 2 <= group_size_limit <= 64:
        raise ValueError("group_size_limit must be between 2 and 64")
    if type(date_window_days) is not int or not 0 <= date_window_days <= 366:
        raise ValueError("date window must be between 0 and 366 days")
    a = tuple(internal)
    b = tuple(counterpart)
    if any(not isinstance(row, ScopedTxn) for row in (*a, *b)):
        raise ValueError("all reconciliation rows must have explicit scope")
    if any(x.origin != "ORIGINAL_INVOICE" for x in a):
        raise ValueError("internal rows must be original invoice lines")
    if any(x.origin not in {"BANK_CLEARED", "CUSTOMER_DECLARATION"} for x in b):
        raise ValueError("counterparts must be explicitly typed")
    all_ids = [x.txn.id for x in (*a, *b)]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("duplicate transaction ID across population")
    aa: dict[tuple[str, ...], list[ScopedTxn]] = defaultdict(list)
    bb: dict[tuple[str, ...], list[ScopedTxn]] = defaultdict(list)
    missing_a = missing_b = 0
    for row in a:
        key = _group_key(row)
        if key is None:
            missing_a += 1
        else:
            aa[key].append(row)
    for row in b:
        key = _group_key(row)
        if key is None:
            missing_b += 1
        else:
            bb[key].append(row)
    matched_a = matched_b = 0
    matched_groups = review_groups = bound_groups = 0
    mismatches = 0
    by_rule: dict[str, int] = {}
    proof_material = []
    bank_labeled = 0
    for key in sorted(set(aa) | set(bb)):
        lhs = sorted(aa.get(key, []), key=lambda x: x.txn.id)
        rhs = sorted(bb.get(key, []), key=lambda x: x.txn.id)
        if not lhs or not rhs:
            review_groups += 1
            continue
        if len(lhs) > group_size_limit or len(rhs) > group_size_limit:
            review_groups += 1
            bound_groups += 1
            continue
        cfg = ReconConfig(
            decimals=2, date_window_days=date_window_days,
            amount_tolerance_bps=0, amount_tolerance_min_minor=0,
            many_to_one=ManyToOneConfig(
                enabled=True, date_window_days=date_window_days,
                tolerance_bps=0, max_group_size=group_size_limit,
                max_candidates=group_size_limit, max_nodes=250_000,
            ),
        )
        # Only the exact group reference and buyer/customer scope is visible
        # to the native kernel. No amount-date fallback can match other payees.
        result = reconcile((x.txn for x in lhs), (x.txn for x in rhs), cfg)
        matched_a += result.summary.matched_internal
        matched_b += result.summary.matched_settlement
        matched_groups += result.summary.match_groups
        for rule, count in result.summary.by_rule.items():
            by_rule[rule] = by_rule.get(rule, 0) + count
        a_by_id = {x.txn.id: x for x in lhs}
        b_by_id = {x.txn.id: x for x in rhs}
        for match in result.matches:
            refs = {_group_key(a_by_id[id_]) for id_ in match.internal_ids} | {
                _group_key(b_by_id[id_]) for id_ in match.settlement_ids
            }
            mismatches += int(refs != {key})
            bank_labeled += sum(b_by_id[id_].origin == "BANK_CLEARED"
                                 for id_ in match.settlement_ids)
        proof_material.append((key, result.summary.matched_internal,
                               result.summary.matched_settlement,
                               canonical_hash(result.canonical_json())))
    if matched_a + missing_a > len(a) or matched_b + missing_b > len(b):
        raise ValueError("reconciliation population-count conservation violated")
    body = {
        "schema": 1, "a": len(a), "b": len(b), "matched_a": matched_a,
        "matched_b": matched_b, "missing_a": missing_a, "missing_b": missing_b,
        "rules": by_rule, "review_groups": review_groups,
        "bound_groups": bound_groups, "errors": mismatches,
        "proof_material": proof_material,
        "source_labeled_bank_matches": bank_labeled,
        "independently_verified_bank_matches": 0,
    }
    return ScopeReconciliation(
        len(a), len(b), matched_a, matched_b,
        len(a) - matched_a, len(b) - matched_b,
        matched_groups, by_rule, review_groups, bound_groups,
        mismatches, 0,
        # A label of BANK_CLEARED is self-declared input, not an externally
        # authenticated bank receipt. Never use it to prove a cash movement.
        None, canonical_hash(body), bank_labeled,
    )
