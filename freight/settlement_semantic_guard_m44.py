"""M44: read-only semantic consistency gate over PERSISTENT settlement SQLite.

The existing SettlementStore database has append-only triggers and restrictive
INSERT rules. Privileged edits, copied files and restores can nevertheless
leave financially contradictory *valid SQLite* data after bypassing triggers.
Reopening or exporting such a file must not silently count it as a good source.

This inspects relational/financial semantics only; without independently
authenticated original provider bytes or owner signatures, it CANNOT tell
whether a consistent database contains fraudulent events. No network, writes,
customer identities in results or authorization grants.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import sqlite3

SCOPE = "RETALLY_M44_PERSISTENT_SETTLEMENT_SQLITE_SEMANTIC_CONSISTENCY_ONLY"
KEYS = {
    "recovery_claims": "claim_id",
    "review_claims": "claim_id",
    "settlement_events": "event_id",
    "allocations": "allocation_id",
    "counter_events": "counter_id",
    "reversal_edges": "reversal_id",
}
SOURCE_FAMILIES = ("recovery_claims", "settlement_events", "counter_events")


def _fail(reason: str) -> None:
    # Do not expose private invoice/source identifiers or row content.
    raise RuntimeError("settlement semantic integrity rejected: M44_" + reason)


def _cents(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        _fail("NONPOSITIVE_OR_NONINTEGER_SOURCE_AMOUNT")
    return value


def _when(value: object) -> datetime:
    if type(value) is not str:
        _fail("INVALID_SOURCE_TIME")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("INVALID_SOURCE_TIME")
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        _fail("NOT_UTC_SOURCE_TIME")
    return result.astimezone(timezone.utc)


def _scope_key(row: dict, field: str) -> tuple[str, str, str]:
    scope = (row["buyer_id"], row["business_unit"], row[field])
    if any(type(x) is not str or not x for x in scope):
        _fail("INVALID_SCOPED_SOURCE_IDENTITY")
    return scope


def _snapshot(con: sqlite3.Connection, scope: tuple[str, str] | None) -> dict:
    if scope is not None and (
        type(scope) is not tuple or len(scope) != 2
        or any(type(v) is not str or not v for v in scope)
    ):
        raise ValueError("M44_INVALID_SCOPED_AUDIT_ARGUMENT")
    result = {}
    for table in KEYS:
        query = "SELECT * FROM " + table
        if scope is not None:
            query += " WHERE buyer_id=? AND business_unit=?"
        rows = con.execute(query, scope or ()).fetchall()
        names = [x[0] for x in con.execute("SELECT * FROM "+table+" LIMIT 0").description]
        result[table] = [dict(zip(names, row)) for row in rows]
    return result


def audit_connection(con: sqlite3.Connection, *,
                     scope: tuple[str, str] | None = None) -> dict:
    """Validate current DB transaction without modifying it.

    For reopen call with scope=None (all tenants). For report/backup call
    within one existing BEGIN snapshot and a specific authenticated scope.
    """
    tables = _snapshot(con, scope)
    index = {}
    counts = {}
    for table, field in KEYS.items():
        rows = tables[table]
        counts[table] = len(rows)
        keys = [_scope_key(r, field) for r in rows]
        if len(keys) != len(set(keys)):
            _fail("DUPLICATE_ROW_ID_" + table.upper())
        index[table] = {k: r for k, r in zip(keys, rows)}
    # Do not reuse the same purported original source hash across distinct
    # claims / credits / returns within a buyer/business-unit scope.
    for table in SOURCE_FAMILIES:
        known: set[tuple[str, str, str]] = set()
        for row in tables[table]:
            source = row["source_hash"]
            if type(source) is not str or len(source) != 64 or any(
                ch not in "0123456789abcdef" for ch in source
            ):
                _fail("INVALID_SOURCE_FINGERPRINT_" + table.upper())
            key = (row["buyer_id"], row["business_unit"], source)
            if key in known:
                _fail("DUPLICATE_SOURCE_FINGERPRINT_" + table.upper())
            known.add(key)

    claims = index["recovery_claims"]
    credits = index["settlement_events"]
    allocations = index["allocations"]
    counters = index["counter_events"]
    reversed_rows = tables["reversal_edges"]
    timeline: dict[tuple[str, str, str], list[tuple[datetime, int, int]]] = defaultdict(list)
    credit_gross = defaultdict(int)
    counter_gross = defaultdict(int)
    allocation_gross = defaultdict(int)
    reversal_by_allocation = defaultdict(int)
    reversal_by_counter = defaultdict(int)
    alloc_pairs = set()
    reverse_pairs = set()

    for key, claim in claims.items():
        _cents(claim["amount_cents"])
        if type(claim["fee_disqualified"]) is not int or claim["fee_disqualified"] not in (0, 1):
            _fail("INVALID_FEE_DISQUALIFICATION")
        _when(claim["issued_at"])
    for key, credit in credits.items():
        _cents(credit["amount_cents"])
        _when(credit["booked_at"])
    for key, counter in counters.items():
        _cents(counter["amount_cents"])
        parent_key = (key[0], key[1], counter["original_event_id"])
        parent = credits.get(parent_key)
        if parent is None:
            _fail("RETURN_ORIGINAL_RECEIPT_MISSING")
        if (parent["currency"] != counter["currency"]
            or _when(counter["observed_at"]) < _when(parent["booked_at"])):
            _fail("RETURN_SOURCE_CURRENCY_OR_CHRONOLOGY")
        counter_gross[parent_key] += counter["amount_cents"]

    for key, allocation in allocations.items():
        claim_key = (key[0],key[1],allocation["claim_id"])
        credit_key = (key[0],key[1],allocation["event_id"])
        claim, credit = claims.get(claim_key), credits.get(credit_key)
        if claim is None or credit is None:
            _fail("ALLOCATION_REFERENCES_MISSING_SOURCE")
        if (claim["currency"],claim["payer_id"],claim["payee_id"]) != (
            credit["currency"],credit["payer_id"],credit["payee_id"]
        ):
            _fail("ALLOCATION_CURRENCY_OR_COUNTERPARTY_DRIFT")
        if (allocation["mode"] not in ("AUTO", "REVIEW")
            or type(allocation["mode"]) is not str):
            _fail("UNREGISTERED_ALLOCATION_MODE")
        amount = _cents(allocation["amount_cents"])
        eligible = allocation["fee_eligible_cents"]
        if (type(eligible) is not int
            or eligible != (0 if claim["fee_disqualified"] else amount)):
            _fail("ALLOCATION_FEE_ELIGIBILITY_DRIFT")
        made = _when(allocation["created_at"])
        if _when(claim["issued_at"]) > _when(credit["booked_at"]) or made < _when(credit["booked_at"]):
            _fail("ALLOCATION_SOURCE_CHRONOLOGY")
        pair = (claim_key, credit_key)
        if pair in alloc_pairs:
            _fail("DUPLICATE_ECONOMIC_ALLOCATION_PAIR")
        alloc_pairs.add(pair)
        credit_gross[credit_key] += amount
        allocation_gross[claim_key] += amount
        timeline[claim_key].append((made, 0, amount))

    for reversal in reversed_rows:
        scope_key = (reversal["buyer_id"], reversal["business_unit"])
        allocation_key = (*scope_key,reversal["allocation_id"])
        counter_key = (*scope_key,reversal["counter_id"])
        allocation, counter = allocations.get(allocation_key), counters.get(counter_key)
        if allocation is None or counter is None:
            _fail("REVERSAL_ORIGINAL_SOURCE_MISSING")
        if allocation["event_id"] != counter["original_event_id"]:
            _fail("REVERSAL_WRONG_ORIGINAL_RECEIPT")
        pair=(allocation_key,counter_key)
        if pair in reverse_pairs:
            _fail("DUPLICATE_ECONOMIC_REVERSAL_PAIR")
        reverse_pairs.add(pair)
        amount=_cents(reversal["amount_cents"])
        when=_when(reversal["created_at"])
        if (when < _when(counter["observed_at"])
            or when < _when(allocation["created_at"])):
            _fail("REVERSAL_CAUSALITY_INVERSION")
        reversal_by_allocation[allocation_key] += amount
        reversal_by_counter[counter_key] += amount
        claim_key=(*scope_key,allocation["claim_id"])
        timeline[claim_key].append((when,1,-amount))

    for key, amount in counter_gross.items():
        if amount > credits[key]["amount_cents"]:
            _fail("RETURN_CAPACITY_EXCEEDS_CREDIT")
    for key, amount in credit_gross.items():
        if amount > credits[key]["amount_cents"]:
            _fail("ALLOCATION_CAPACITY_EXCEEDS_CREDIT")
    for key, amount in reversal_by_allocation.items():
        if amount > allocations[key]["amount_cents"]:
            _fail("REVERSAL_CAPACITY_EXCEEDS_ALLOCATION")
    for key, amount in reversal_by_counter.items():
        if amount > counters[key]["amount_cents"]:
            _fail("REVERSAL_CAPACITY_EXCEEDS_RETURN")
    for key, changes in timeline.items():
        current = 0
        # Equal timestamps are ambiguous: acknowledge the potential
        # over-recognition by applying credits before corresponding returns.
        for _, _, delta in sorted(changes):
            current += delta
            if current < 0:
                _fail("TRANSIENT_NEGATIVE_CLAIM_BALANCE")
            if current > claims[key]["amount_cents"]:
                _fail("TRANSIENT_CLAIM_CAPACITY_EXCEEDED")
    return {
        "scope": SCOPE,
        "input_is_current_sqlite_only_not_signed_original_evidence": True,
        "scoped_to_one_workspace": scope is not None,
        "validated_scoped_table_rows": sum(counts.values()),
        "validated_claims": len(claims),
        "validated_allocations": len(allocations),
        "validated_returns": len(counters),
        "validated_reversals": len(reversed_rows),
        "no_external_original_source_attestation": True,
        "no_real_bank_or_customer_countersigned_authority": True,
    }
