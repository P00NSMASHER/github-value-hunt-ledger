"""Separate-currency accounting view of RETALLY's immutable settlement ledger.

This is a source-declared reconciliation snapshot, never a bank-clearance or
fee authorization. There is deliberately no total across currencies or FX.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from freight.contracts import canonical_hash
from freight.financial_assurance import require_cent_currency, require_exact_cents
from freight.settlement_store import SettlementStore


@dataclass(frozen=True)
class CurrencyLedgerRow:
    currency: str
    declared_claim_cents: int
    declared_allocated_cents: int
    declared_reversed_cents: int
    declared_net_allocated_cents: int
    declared_fee_eligible_net_cents: int
    unresolved_counter_cents: int


@dataclass(frozen=True)
class CurrencySettlementReport:
    buyer_id: str
    business_unit: str
    by_currency: tuple[CurrencyLedgerRow, ...]
    snapshot_hash: str
    report_hash: str
    external_settlement_verified: bool = False
    single_aggregated_total_cents: None = None
    classification: str = "SOURCE_DECLARED_NOT_BANK_VERIFIED"


def build_currency_settlement_report(store: SettlementStore) -> CurrencySettlementReport:
    if not isinstance(store, SettlementStore):
        raise ValueError("currency reports require a scoped SettlementStore")
    source = json.loads(store.report_snapshot_json())
    if (source.get("buyer_id"), source.get("business_unit")) != (
        store.buyer_id, store.business_unit
    ):
        raise ValueError("currency report source scope mismatch")
    snap = canonical_hash(source)
    tables = source["tables"]
    claims = {x["claim_id"]: x for x in tables["recovery_claims"]}
    events = {x["event_id"]: x for x in tables["settlement_events"]}
    allocations = {x["allocation_id"]: x for x in tables["allocations"]}
    disputed_claim_ids = {x["claim_id"]
                          for x in tables.get("claim_dispute_holds", ())}
    counters = {x["counter_id"]: x for x in tables["counter_events"]}
    rows = {}
    # Fee candidates tied to a still-unapplied source return must be held,
    # not counted as fee eligible, even when the return spans multiple claims.
    provisional_fee_by_event: dict[str, int] = {}
    def bucket(currency: str) -> dict[str, int]:
        canonical = require_cent_currency(currency)
        return rows.setdefault(canonical, {
            "claims": 0, "allocations": 0, "reversals": 0,
            "fee_net": 0, "unresolved": 0,
        })
    for claim in claims.values():
        bucket(claim["currency"])["claims"] += require_exact_cents(
            "claim amount", claim["amount_cents"], positive=True
        )
    for event in events.values():
        bucket(event["currency"])
    for allocation in allocations.values():
        claim = claims.get(allocation["claim_id"])
        event = events.get(allocation["event_id"])
        if not claim or not event or claim["currency"] != event["currency"]:
            raise ValueError("allocation has an unbound or mixed-currency financial source")
        if (claim["payer_id"],claim["payee_id"]) != (
            event["payer_id"], event["payee_id"]
        ):
            raise ValueError("allocation source-party mismatch")
        amt = require_exact_cents("allocation amount", allocation["amount_cents"], positive=True)
        fee = require_exact_cents("eligible allocation", allocation["fee_eligible_cents"])
        if fee not in (0, amt) or bool(claim["fee_disqualified"]) != (fee == 0):
            raise ValueError("allocation fee eligibility is inconsistent")
        target = bucket(claim["currency"])
        target["allocations"] += amt
        if allocation["claim_id"] not in disputed_claim_ids:
            target["fee_net"] += fee
            provisional_fee_by_event[event["event_id"]] = (
                provisional_fee_by_event.get(event["event_id"], 0) + fee
            )
    counter_applied = {}
    for reversal in tables["reversal_edges"]:
        allocation = allocations.get(reversal["allocation_id"])
        counter = counters.get(reversal["counter_id"])
        if not allocation or not counter:
            raise ValueError("reversal references unknown immutable evidence")
        event = events.get(allocation["event_id"])
        if not event or counter["original_event_id"] != event["event_id"]:
            raise ValueError("reversal source does not match allocation event")
        if counter["currency"] != event["currency"]:
            raise ValueError("reversal currency mismatch")
        amt = require_exact_cents("reversed amount", reversal["amount_cents"], positive=True)
        row = bucket(event["currency"])
        row["reversals"] += amt
        if allocation["fee_eligible_cents"] and allocation["claim_id"] not in disputed_claim_ids:
            row["fee_net"] -= amt
            provisional_fee_by_event[event["event_id"]] -= amt
        counter_applied[counter["counter_id"]] = counter_applied.get(counter["counter_id"], 0) + amt
    unresolved_event_ids = set()
    for counter in counters.values():
        row = bucket(counter["currency"])
        outstanding = require_exact_cents("counter amount", counter["amount_cents"], positive=True) - counter_applied.get(counter["counter_id"],0)
        if outstanding < 0:
            raise ValueError("counter replay exceeds immutable reversal capacity")
        row["unresolved"] += outstanding
        if outstanding:
            unresolved_event_ids.add(counter["original_event_id"])
    # The retained allocation and return evidence remains unchanged. Only the
    # unverified fee-base candidate is suppressed until source reconciliation.
    for event_id in unresolved_event_ids:
        event = events.get(event_id)
        if event is None:
            raise ValueError("unresolved return references an unknown source event")
        bucket(event["currency"])["fee_net"] -= provisional_fee_by_event.get(event_id, 0)
    output = []
    for currency, value in sorted(rows.items()):
        net = value["allocations"] - value["reversals"]
        if net < 0 or value["fee_net"] < 0 or value["fee_net"] > net:
            raise ValueError("currency-level settlement conservation failed")
        output.append(CurrencyLedgerRow(
            currency,
            value["claims"],
            value["allocations"],
            value["reversals"],
            net,
            value["fee_net"],
            value["unresolved"],
        ))
    body = {
        "schema": 1, "snapshot_hash": snap,
        "buyer_id": store.buyer_id, "business_unit": store.business_unit,
        "currency_rows": [asdict(x) for x in output],
        "external_settlement_verified": False,
        "aggregated_currency_total": None,
        "classification": "SOURCE_DECLARED_NOT_BANK_VERIFIED",
    }
    return CurrencySettlementReport(
        store.buyer_id, store.business_unit,
        tuple(output), snap, canonical_hash(body),
    )


def assert_currency_report_current(
    report: CurrencySettlementReport, store: SettlementStore
) -> None:
    current = build_currency_settlement_report(store)
    if not isinstance(report, CurrencySettlementReport):
        raise ValueError("typed report required")
    if report != current:
        raise ValueError("currency settlement snapshot changed or report was modified")


def render_currency_report(report: CurrencySettlementReport) -> str:
    if not isinstance(report, CurrencySettlementReport):
        raise ValueError("typed report required")
    heading = [
        "# RETALLY currency-partitioned accounting snapshot",
        "**SOURCE-DECLARED / NOT BANK-VERIFIED — no demonstrated recovery or billable fee.**",
        "Currencies are isolated; no FX or combined total is calculated.",
        "",
    ]
    for row in report.by_currency:
        code = require_cent_currency(row.currency)
        def fmt(x: int) -> str:
            return f"{code} {x // 100}.{x % 100:02d}"
        heading.append(
            f"- {code}: original claims {fmt(row.declared_claim_cents)}; "
            f"allocated {fmt(row.declared_allocated_cents)}; "
            f"reversed {fmt(row.declared_reversed_cents)}; "
            f"net declared {fmt(row.declared_net_allocated_cents)}; "
            f"fee-base candidate {fmt(row.declared_fee_eligible_net_cents)}; "
            f"unresolved returns {fmt(row.unresolved_counter_cents)}."
        )
    heading.append(f"Snapshot: `{report.snapshot_hash}`")
    heading.append(f"Report: `{report.report_hash}`")
    return "\n".join(heading) + "\n"
