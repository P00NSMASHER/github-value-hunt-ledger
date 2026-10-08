"""Read-only independent laboratory assurance over existing settlement-store records.

Financial results are *only* anchored to the separately supplied verification
policy and assertions. HMAC is deliberately a synthetic integration transport;
its use here does not authenticate actual buyers, banks, contracts, or carriers.
Never ship test signers or signing keys as an application-level authority.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
from pathlib import Path
import re
import sqlite3
from typing import Mapping, Sequence

ROLE_BY_KIND = {
    "SOURCE_OWNER": "BUYER",
    "CREDIT_RECEIPT": "PROVIDER",
    "CREDIT_RETURN": "PROVIDER",
    "FEE_CONTRACT": "BUYER",
    "FEE_PAYMENT": "PAYMENT_OBSERVER",
    "FEE_REFUND": "PAYMENT_OBSERVER",
    "WRITE_OFF_APPROVAL": "ACCOUNTING_APPROVER",
}
FEE_KINDS = frozenset({
    "ACCRUE", "INVOICE", "COLLECT", "REDUCE", "CREDIT_NOTE", "REFUND", "WRITE_OFF",
})
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_SCOPE_FIELDS = ("buyer_id", "business_unit")


class AssuranceRejected(ValueError):
    """Typed failure, without leaking private invoice/provider source material."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise AssuranceRejected(code)


def _name(value: str, field: str) -> str:
    if type(value) is not str or not value or value != value.strip() or any(ord(x) < 32 for x in value):
        _fail("INVALID_" + field.upper())
    return value


def _money(value: int, field: str, positive: bool = False) -> int:
    if type(value) is not int or not (1 if positive else 0) <= value <= 2**63 - 1:
        _fail("INVALID_" + field.upper())
    return value


def _hash(value: str, field: str) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        _fail("INVALID_" + field.upper())
    return value


def _utc(value: str, field: str) -> datetime:
    _name(value, field)
    try:
        obj = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("INVALID_" + field.upper())
    if obj.tzinfo is None or obj.utcoffset() is None:
        _fail("NAIVE_" + field.upper())
    return obj.astimezone(timezone.utc)


def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf8")
    except (TypeError, ValueError, OverflowError):
        _fail("INVALID_CANONICAL_EVIDENCE")


def digest(value: object) -> str:
    return sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    kind: str
    issuer: str
    issued_at: str
    payload: Mapping[str, object]
    signature: str

    def message(self) -> dict:
        return {"schema": 1, "evidence_id": self.evidence_id, "kind": self.kind,
                "issuer": self.issuer, "issued_at": self.issued_at, "payload": self.payload}


@dataclass(frozen=True)
class TrustAnchor:
    issuer: str
    role: str
    verification_key: bytes
    valid_from: str
    valid_until: str | None = None


@dataclass(frozen=True)
class FeeEvent:
    event_id: str
    claim_id: str
    kind: str
    amount_cents: int
    occurred_at: str
    evidence_id: str | None = None


@dataclass(frozen=True)
class AssuranceReceipt:
    status: str
    scope: str
    verified_claims: int
    verified_receipts: int
    claim_balances: tuple[Mapping[str, object], ...]
    currency_totals: Mapping[str, Mapping[str, int]]
    source_snapshot_hash: str
    evidence_manifest_hash: str
    receipt_hash: str


class EvidenceVerifier:
    """Verifier-held policy. Caller must protect trust anchors outside lab writers."""
    def __init__(self, anchors: Sequence[TrustAnchor], *, as_of: str):
        self.as_of = _utc(as_of, "as_of")
        self._anchors: dict[str, TrustAnchor] = {}
        for a in anchors:
            _name(a.issuer, "issuer")
            if a.issuer in self._anchors: _fail("DUPLICATE_TRUST_ISSUER")
            if a.role not in ROLE_BY_KIND.values(): _fail("INVALID_ISSUER_ROLE")
            if type(a.verification_key) is not bytes or len(a.verification_key) < 32:
                _fail("WEAK_VERIFICATION_KEY")
            start = _utc(a.valid_from, "trust_valid_from")
            if a.valid_until is not None and _utc(a.valid_until, "trust_valid_until") <= start:
                _fail("INVALID_TRUST_INTERVAL")
            self._anchors[a.issuer] = a

    def check(self, assertions: Sequence[Evidence]) -> dict[str, Evidence]:
        result: dict[str, Evidence] = {}
        for e in assertions:
            _name(e.evidence_id, "evidence_id")
            _name(e.issuer, "issuer")
            if e.evidence_id in result: _fail("DUPLICATE_EVIDENCE_ID")
            kind_role = ROLE_BY_KIND.get(e.kind)
            if kind_role is None: _fail("EVIDENCE_KIND_UNKNOWN")
            a = self._anchors.get(e.issuer)
            if a is None or a.role != kind_role: _fail("UNTRUSTED_EVIDENCE_ISSUER")
            when = _utc(e.issued_at, "evidence_issued_at")
            if not _utc(a.valid_from,"trust_valid_from") <= when <= self.as_of:
                _fail("EVIDENCE_OUTSIDE_TRUST_WINDOW")
            if a.valid_until is not None and when >= _utc(a.valid_until,"trust_valid_until"):
                _fail("EVIDENCE_OUTSIDE_TRUST_WINDOW")
            if type(e.payload) is not dict: _fail("INVALID_EVIDENCE_PAYLOAD")
            _hash(e.signature, "signature")
            expected = hmac.new(a.verification_key, canonical(e.message()), sha256).hexdigest()
            if not hmac.compare_digest(expected, e.signature):
                _fail("EVIDENCE_SIGNATURE_INVALID")
            result[e.evidence_id] = e
        return result


def _scope(e: Evidence, buyer: str, bu: str):
    if e.payload.get("buyer_id") != buyer or e.payload.get("business_unit") != bu:
        _fail("EVIDENCE_TENANT_MISMATCH")


def _lookup(index: Mapping[tuple[str, str], Evidence], kind: str, id: str) -> Evidence:
    item = index.get((kind, id))
    if item is None: _fail("MISSING_" + kind)
    return item


def _rows(con: sqlite3.Connection, table: str, buyer: str, bu: str) -> list[dict]:
    return [dict(row) for row in con.execute(
        f"SELECT * FROM {table} WHERE buyer_id=? AND business_unit=?",
        (buyer, bu))]


def verify_settlement(
    db_path: str | Path,
    *,
    buyer_id: str,
    business_unit: str,
    assertions: Sequence[Evidence],
    fee_events: Sequence[FeeEvent],
    verifier: EvidenceVerifier,
    reported_totals: Mapping[str, Mapping[str, int]] | None = None,
) -> AssuranceReceipt:
    """Independently recompute SQLite settlement edges and fee journal.

    Read-only DB snapshot is not authentic bank data. Separate verifier-controlled
    source/contract/provider assertions are required. Empty evidence fails closed.
    """
    buyer_id = _name(buyer_id, "buyer_id")
    business_unit = _name(business_unit, "business_unit")
    verified = verifier.check(assertions)
    by_identity: dict[tuple[str, str], Evidence] = {}
    for proof in verified.values():
        _scope(proof, buyer_id, business_unit)
        key_field = {
            "SOURCE_OWNER": "claim_id", "CREDIT_RECEIPT": "event_id",
            "CREDIT_RETURN": "counter_id", "FEE_CONTRACT": "claim_id",
            "FEE_PAYMENT": "fee_event_id", "FEE_REFUND": "fee_event_id",
            "WRITE_OFF_APPROVAL": "fee_event_id",
        }[proof.kind]
        key = (proof.kind, _name(proof.payload.get(key_field), key_field))
        if key in by_identity: _fail("DUPLICATE_AUTHORITY_BINDING")
        by_identity[key] = proof

    path = Path(db_path)
    if not path.is_file(): _fail("MISSING_SETTLEMENT_DATABASE")
    # URI mode=ro avoids accidentally creating a database if the file is missing.
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        try:
            tables = {table: _rows(con, table, buyer_id, business_unit) for table in (
                "recovery_claims", "settlement_events", "allocations",
                "counter_events", "reversal_edges",
            )}
            con.execute("COMMIT")
        except (sqlite3.Error, ValueError):
            con.execute("ROLLBACK")
            _fail("UNREADABLE_SETTLEMENT_SNAPSHOT")
    finally:
        con.close()

    snapshot_hash = digest(tables)
    claims = {r["claim_id"]: r for r in tables["recovery_claims"]}
    credits = {r["event_id"]: r for r in tables["settlement_events"]}
    counters = {r["counter_id"]: r for r in tables["counter_events"]}
    allocations = {r["allocation_id"]: r for r in tables["allocations"]}
    if not claims: _fail("EMPTY_CLAIM_POPULATION")
    if len(claims) != len(tables["recovery_claims"]) or len(credits) != len(tables["settlement_events"]):
        _fail("DUPLICATE_LOCAL_ID")
    issue_ids: set[tuple] = set()
    terms: dict[str, dict] = {}
    for cid, claim in claims.items():
        owner = _lookup(by_identity, "SOURCE_OWNER", cid)
        p = owner.payload
        for local, signed in (("claim_id", cid), ("reference", claim["reference"]),
                              ("currency", claim["currency"]), ("source_hash", claim["source_hash"]),
                              ("amount_cents", claim["amount_cents"])):
            if p.get(local) != signed: _fail("SOURCE_OWNER_BINDING_MISMATCH")
        if p.get("payer_id") != claim["payer_id"] or p.get("payee_id") != claim["payee_id"]:
            _fail("SOURCE_OWNER_COUNTERPARTY_MISMATCH")
        if _utc(p.get("issued_at"),"owner_claim_issued_at") != _utc(claim["issued_at"],"claim_issued_at"):
            _fail("SOURCE_OWNER_TIME_MISMATCH")
        issue_key = (buyer_id, business_unit, claim["reference"],
                     _name(p.get("economic_issue_id"), "economic_issue_id"))
        if issue_key in issue_ids: _fail("DUPLICATE_ECONOMIC_RECOVERY")
        issue_ids.add(issue_key)
        if _utc(owner.issued_at,"owner_asserted_at") > _utc(claim["issued_at"],"claim_issued_at"):
            _fail("SOURCE_OWNER_POSTDATES_CLAIM")
        if type(claim["amount_cents"]) is not int or claim["amount_cents"] <= 0:
            _fail("INVALID_CLAIM_AMOUNT")

        mandate = _lookup(by_identity, "FEE_CONTRACT", cid)
        t = mandate.payload
        if t.get("claim_id") != cid or t.get("currency") != claim["currency"]:
            _fail("CONTRACT_BINDING_MISMATCH")
        if t.get("source_hash") != claim["source_hash"]:
            _fail("CONTRACT_SOURCE_MISMATCH")
        bps = t.get("fee_bps")
        if type(bps) is not int or bps < 0 or bps > 10_000:
            _fail("INVALID_FEE_RATE")
        cap = t.get("fee_cap_cents")
        if cap is not None: _money(cap,"fee_cap_cents")
        if _utc(mandate.issued_at,"mandate_issued_at") > _utc(claim["issued_at"],"claim_issued_at"):
            _fail("FEE_TERMS_NOT_SIGNED_BEFORE_CLAIM")
        issued = _utc(claim["issued_at"],"claim_issued_at")
        if not _utc(t.get("effective_from"),"effective_from") <= issued < _utc(t.get("effective_until"),"effective_until"):
            _fail("FEE_CONTRACT_NOT_EFFECTIVE")
        if t.get("revoked_at") is not None and issued >= _utc(t["revoked_at"],"revoked_at"):
            _fail("REVOKED_CONTRACT_FOR_NEW_CLAIM")
        terms[cid] = {"bps":bps,"cap":cap,"time":issued,"currency":claim["currency"]}

    for eid, credit in credits.items():
        proof = _lookup(by_identity,"CREDIT_RECEIPT",eid)
        p = proof.payload
        for field in ("event_id","reference","payer_id","payee_id","currency",
                      "amount_cents","source_hash","booked_at"):
            if field == "booked_at":
                if _utc(p.get(field),"provider_booked_at") != _utc(credit[field],"settlement_booked_at"):
                    _fail("CREDIT_PROVENANCE_MISMATCH")
            elif p.get(field) != credit[field]:
                _fail("CREDIT_PROVENANCE_MISMATCH")
        if _utc(proof.issued_at,"credit_proof_time") > verifier.as_of:
            _fail("CREDIT_PROOF_FUTURE")
        _money(credit["amount_cents"],"credit_cents",positive=True)

    for counter_id, counter in counters.items():
        proof = _lookup(by_identity,"CREDIT_RETURN",counter_id)
        p = proof.payload
        for field in ("counter_id","original_event_id","amount_cents","currency","source_hash","observed_at"):
            if field == "observed_at":
                if _utc(p.get(field),"provider_return_at") != _utc(counter[field],"counter_observed_at"):
                    _fail("CREDIT_RETURN_PROVENANCE_MISMATCH")
            elif p.get(field) != counter[field]:
                _fail("CREDIT_RETURN_PROVENANCE_MISMATCH")
        linked = credits.get(counter["original_event_id"])
        if linked is None or linked["currency"] != counter["currency"]:
            _fail("COUNTER_MISSING_ORIGINAL")
        if _utc(counter["observed_at"],"counter_time") < _utc(linked["booked_at"],"credit_time"):
            _fail("COUNTER_PREDATES_ORIGINAL")
    returned_by_original = defaultdict(int)
    for record in counters.values():
        returned_by_original[record["original_event_id"]] += record["amount_cents"]
    for original, amount in returned_by_original.items():
        if amount > credits[original]["amount_cents"]:
            _fail("RETURNS_EXCEED_ORIGINAL_CREDIT")
    gross_claim = defaultdict(int); gross_credit = defaultdict(int)
    credit_net_by_claim = defaultdict(int)
    credit_timelines = defaultdict(list)
    reversed_allocation = defaultdict(int); reversed_counter = defaultdict(int)
    for aid, allocation in allocations.items():
        cid,eid = allocation["claim_id"], allocation["event_id"]
        claim, credit = claims.get(cid), credits.get(eid)
        if claim is None or credit is None: _fail("ALLOCATED_SOURCE_MISSING")
        if (claim["currency"],claim["payer_id"],claim["payee_id"]) != (
                credit["currency"],credit["payer_id"],credit["payee_id"]):
            _fail("ALLOCATION_COUNTERPARTY_MISMATCH")
        cents = _money(allocation["amount_cents"],"allocated_cents",positive=True)
        if _utc(credit["booked_at"],"credit_booked_at") > _utc(allocation["created_at"],"allocated_at"):
            _fail("ALLOCATION_PREDATES_CREDIT")
        if _utc(claim["issued_at"],"claim_issued_at") > _utc(credit["booked_at"],"credit_booked_at"):
            _fail("CREDIT_PREDATES_CLAIM")
        gross_claim[cid]+=cents; gross_credit[eid]+=cents
        credit_net_by_claim[cid]+=cents
        credit_timelines[cid].append((
            _utc(allocation["created_at"], "allocated_at"), cents))
    for reversal in tables["reversal_edges"]:
        aid, counter_id = reversal["allocation_id"], reversal["counter_id"]
        allocation, counter = allocations.get(aid), counters.get(counter_id)
        if allocation is None or counter is None: _fail("REVERSAL_SOURCE_MISSING")
        if allocation["event_id"] != counter["original_event_id"]:
            _fail("REVERSAL_WRONG_RECEIPT")
        if _utc(counter["observed_at"],"counter_observed_at") > _utc(reversal["created_at"],"reversed_at"):
            _fail("REVERSAL_PREDATES_RETURN")
        cents = _money(reversal["amount_cents"],"reversal_cents",positive=True)
        reversed_allocation[aid]+=cents
        reversed_counter[counter_id]+=cents
        credit_net_by_claim[allocation["claim_id"]]-=cents
        credit_timelines[allocation["claim_id"]].append((
            _utc(reversal["created_at"], "reversed_at"), -cents))
    for aid, amount in reversed_allocation.items():
        if amount>allocations[aid]["amount_cents"]: _fail("ALLOCATION_OVER_REVERSED")
    for kid, amount in reversed_counter.items():
        if amount>counters[kid]["amount_cents"]: _fail("RETURN_OVER_REVERSED")
    for eid, amount in gross_credit.items():
        if amount>credits[eid]["amount_cents"]: _fail("RECEIPT_OVER_ALLOCATED")
    for cid, amount in credit_net_by_claim.items():
        if amount<0 or amount>claims[cid]["amount_cents"]:
            _fail("CLAIM_NET_CAPACITY_EXCEEDED")

    # Fee journal is deliberately external to existing SettlementStore, which
    # holds only underlying settlement allocations and reversals.
    ledger = defaultdict(list); seen_fees=set()
    for event in fee_events:
        if event.event_id in seen_fees: _fail("DUPLICATE_FEE_EVENT")
        seen_fees.add(_name(event.event_id,"fee_event_id"))
        if event.kind not in FEE_KINDS: _fail("UNKNOWN_FEE_EVENT_KIND")
        if event.claim_id not in claims: _fail("FEE_UNKNOWN_CLAIM")
        _money(event.amount_cents,"fee_amount",positive=True)
        occurred = _utc(event.occurred_at,"fee_event_time")
        if occurred < terms[event.claim_id]["time"] or occurred > verifier.as_of:
            _fail("FEE_EVENT_OUTSIDE_CLAIM_WINDOW")
        ext_kind = {"COLLECT":"FEE_PAYMENT", "REFUND":"FEE_REFUND", "WRITE_OFF":"WRITE_OFF_APPROVAL"}.get(event.kind)
        if ext_kind:
            proof = _lookup(by_identity,ext_kind,event.event_id)
            if event.evidence_id != proof.evidence_id:
                _fail("FEE_EXTERNAL_EVIDENCE_REFERENCE_MISMATCH")
            if proof.payload.get("amount_cents") != event.amount_cents or proof.payload.get("claim_id") != event.claim_id:
                _fail("FEE_EXTERNAL_AMOUNT_MISMATCH")
            if proof.payload.get("currency") != terms[event.claim_id]["currency"]:
                _fail("FEE_EXTERNAL_CURRENCY_MISMATCH")
            if _utc(proof.issued_at,"fee_external_proof_time") < occurred:
                _fail("FEE_EXTERNAL_PROOF_PREDATES_OPERATION")
        elif event.evidence_id is not None:
            _fail("UNEXPECTED_FEE_EVIDENCE")
        ledger[event.claim_id].append(event)

    balances=[]; totals=defaultdict(lambda:defaultdict(int))
    for cid, claim in sorted(claims.items()):
        net = credit_net_by_claim[cid]
        t = terms[cid]
        eligible = net*t["bps"]//10_000
        if t["cap"] is not None: eligible=min(eligible,t["cap"])
        if claim["fee_disqualified"]: eligible=0
        sums=defaultdict(int)
        running = defaultdict(int)
        for fee in sorted(ledger[cid], key=lambda f:(_utc(f.occurred_at,"fee_event_time"), f.event_id)):
            when = _utc(fee.occurred_at, "fee_event_time")
            credit_at_time = sum(amount for time, amount in credit_timelines[cid] if time <= when)
            if credit_at_time < 0:
                _fail("CREDIT_CHRONOLOGY_IMPOSSIBLE")
            running[fee.kind] += fee.amount_cents
            earned_so_far = running["ACCRUE"] - running["REDUCE"]
            eligible_at_time = credit_at_time * t["bps"] // 10_000
            if t["cap"] is not None: eligible_at_time = min(eligible_at_time,t["cap"])
            if claim["fee_disqualified"]: eligible_at_time = 0
            if earned_so_far < 0 or earned_so_far > eligible_at_time:
                _fail("FEE_ACCRUED_BEFORE_SUPPORTED_CREDIT")
            if running["INVOICE"] > running["ACCRUE"]:
                _fail("FEE_INVOICE_PREDATES_ACCRUAL")
            if running["COLLECT"] > running["INVOICE"]:
                _fail("FEE_COLLECTION_PREDATES_INVOICE")
            if running["REFUND"] > running["COLLECT"]:
                _fail("FEE_REFUND_EXCEEDS_CASH")
            if running["CREDIT_NOTE"] > running["INVOICE"]:
                _fail("FEE_CREDIT_NOTE_EXCEEDS_INVOICE")
            sums[fee.kind] += fee.amount_cents
        earned=sums["ACCRUE"]-sums["REDUCE"]
        invoiced=sums["INVOICE"]-sums["CREDIT_NOTE"]
        collected=sums["COLLECT"]-sums["REFUND"]
        if earned<0 or earned!=eligible: _fail("FEE_ACCRUAL_NOT_RECONCILED")
        if invoiced<0 or invoiced>earned: _fail("FEE_INVOICE_NOT_RECONCILED")
        if sums["REFUND"]>sums["COLLECT"]: _fail("FEE_REFUND_EXCEEDS_CASH")
        if sums["CREDIT_NOTE"]>sums["INVOICE"]: _fail("FEE_CREDIT_NOTE_EXCEEDS_INVOICE")
        receivable=invoiced-sums["COLLECT"]+sums["REFUND"]-sums["WRITE_OFF"]
        if receivable<0 and -receivable>max(0,collected-earned):
            _fail("FEE_OVER_COLLECTION_OR_WRITE_OFF")
        if sums["WRITE_OFF"]>max(0,invoiced-sums["COLLECT"]):
            _fail("WRITE_OFF_EXCEEDS_UNPAID_INVOICE")
        receivable=max(0,receivable)
        refund_due=max(0,collected-earned)
        currencies=totals[claim["currency"]]
        values={"recovered_cents":net,"earned_fee_cents":earned,
                "invoiced_fee_cents":invoiced,"collected_fee_cents":collected,
                "fee_receivable_cents":receivable,"fee_refund_due_cents":refund_due,
                "written_off_cents":sums["WRITE_OFF"]}
        for k,v in values.items(): currencies[k]+=v
        balances.append({"claim_id":cid,"currency":claim["currency"],**values})
    normalized={c:dict(values) for c,values in sorted(totals.items())}
    if reported_totals is not None:
        if canonical(normalized) != canonical(reported_totals):
            _fail("REPORTED_FINANCIAL_TOTAL_MISMATCH")
    body={"scope":"SIGNED_SYNTHETIC_EVIDENCE_ONLY", "buyer_id":buyer_id,
          "business_unit":business_unit,"balances":balances,"totals":normalized,
          "database_hash":snapshot_hash,
          "evidence_manifest_hash":digest([e.message()|{"signature":e.signature} for e in assertions])}
    return AssuranceReceipt("PASS_SYNTHETIC_ONLY",body["scope"],len(claims),len(credits),
            tuple(balances),normalized,snapshot_hash,body["evidence_manifest_hash"],digest(body))
