"""RETALLY Lab 14 M43 — independent synthetic settlement-source consistency.

The current read-only verifier accepts externally supplied SQLite that may not
have SettlementStore's provenance/chronology/fee constraints. Exercise 12
current-code negative cases, each with a passing fictional baseline and exact
typed denial. All original historical defects remain OPEN_UNVERIFIED.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sqlite3
import tempfile

from freight.lab_assurance import AssuranceRejected, digest, verify_settlement
from freight.test_lab_assurance import (
    BUYER, BU, CLAIM, SRC, assertions_and_fees, populate, stamp, verifier,
)

SCOPE = "RETALLY_LAB14_M43_SYNTHETIC_SETTLEMENT_PROVENANCE_AND_CHRONOLOGY"
REJECTIONS = {
    "INVALID_ALLOCATION_MODE": "INVALID_ALLOCATION_MODE",
    "FEE_ELIGIBILITY_TAMPER": "ALLOCATION_FEE_ELIGIBILITY_MISMATCH",
    "INVALID_DISQUALIFICATION": "INVALID_FEE_DISQUALIFICATION_FLAG",
    "REVERSAL_BEFORE_ALLOCATION": "REVERSAL_PREDATES_ALLOCATION",
    "TRANSIENT_OVER_CLAIM_LIMIT": "TRANSIENT_CLAIM_CAPACITY_EXCEEDED",
    "DUPLICATE_ALLOCATION_PAIR": "DUPLICATE_CLAIM_EVENT_ALLOCATION",
    "DUPLICATE_REVERSAL_PAIR": "DUPLICATE_COUNTER_ALLOCATION_REVERSAL",
    "DUPLICATE_CLAIM_SOURCE_HASH": "DUPLICATE_CLAIM_SOURCE",
    "DUPLICATE_CREDIT_SOURCE_HASH": "DUPLICATE_CREDIT_SOURCE",
    "DUPLICATE_RETURN_SOURCE_HASH": "DUPLICATE_RETURN_SOURCE",
    "SIGNED_NEGATIVE_RETURN": "INVALID_COUNTER_CENTS",
    "SIGNED_MALFORMED_SOURCE_HASH": "INVALID_SOURCE_HASH",
}
BASELINE_USD = {
    "recovered_cents": 500,
    "earned_fee_cents": 100,
    "invoiced_fee_cents": 100,
    "collected_fee_cents": 100,
    "fee_receivable_cents": 0,
    "fee_refund_due_cents": 0,
    "written_off_cents": 0,
}


def _observe(db: Path, proofs: list, fees: list):
    return verify_settlement(
        db, buyer_id=BUYER, business_unit=BU,
        assertions=proofs, fee_events=fees, verifier=verifier()
    )


def _new_credit(con, *, event_id: str, amount: int, at: str,
                source_hash: str, proofs: list) -> None:
    con.execute(
        "INSERT INTO settlement_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (BUYER, BU, event_id, "INV-100", "SIM-CARRIER", "SIM-BUYER",
         "USD", amount, at, source_hash, "EXTERNAL"),
    )
    proofs.append(stamp(
        "CREDIT_RECEIPT", "m43-" + event_id, "carrier-signer", at,
        event_id=event_id, reference="INV-100", payer_id="SIM-CARRIER",
        payee_id="SIM-BUYER", currency="USD", amount_cents=amount,
        source_hash=source_hash, booked_at=at, source_kind="EXTERNAL",
    ))


def _new_counter(con, *, counter_id: str, credit_id: str, amount: int,
                 at: str, source_hash: str, proofs: list) -> None:
    con.execute(
        "INSERT INTO counter_events VALUES (?,?,?,?,?,?,?,?,?)",
        (BUYER, BU, counter_id, credit_id, "USD", amount,
         at, source_hash, "BANK-RETURN"),
    )
    proofs.append(stamp(
        "CREDIT_RETURN", "m43-" + counter_id, "carrier-signer", at,
        counter_id=counter_id, original_event_id=credit_id,
        currency="USD", amount_cents=amount, observed_at=at,
        source_hash=source_hash, source_kind="BANK-RETURN",
    ))


def _mutate(db: Path, scenario: str, proofs: list) -> list:
    """Bounded fixed SQL against one disposable database; no dynamic identifiers."""
    if type(scenario) is not str or scenario not in REJECTIONS:
        raise ValueError("M43_UNKNOWN_ADVERSARIAL_SCENARIO")
    proof = list(proofs)
    with sqlite3.connect(db) as con:
        if scenario == "INVALID_ALLOCATION_MODE":
            con.execute(
                "UPDATE allocations SET mode='REVIEW_APPROVED' "
                "WHERE allocation_id='allocation-400'"
            )
        elif scenario == "FEE_ELIGIBILITY_TAMPER":
            con.execute(
                "UPDATE allocations SET fee_eligible_cents=0 "
                "WHERE allocation_id='allocation-400'"
            )
        elif scenario == "INVALID_DISQUALIFICATION":
            # NULL was treated as Boolean false by the old verifier but is
            # not a valid strict integer 0/1 in SettlementStore's schema.
            con.execute(
                "UPDATE recovery_claims SET fee_disqualified=NULL "
                "WHERE claim_id='case-1'"
            )
        elif scenario == "REVERSAL_BEFORE_ALLOCATION":
            # Unallocated after all fee evidence events, so only causality
            # violation is inversion between new allocation and its reversal.
            source_hash=sha256(b"m43-late-credit").hexdigest()
            return_hash=sha256(b"m43-late-return").hexdigest()
            _new_credit(con,event_id="m43-late-credit",amount=1,
                        at="2026-12-14T12:00:00Z",
                        source_hash=source_hash,proofs=proof)
            _new_counter(con,counter_id="m43-late-return",
                         credit_id="m43-late-credit",amount=1,
                         at="2026-12-15T12:00:00Z",
                         source_hash=return_hash,proofs=proof)
            con.execute(
                "INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-late-allocation","case-1",
                 "m43-late-credit",1,"REVIEW",1,"2026-12-17T12:00:00Z"),
            )
            con.execute(
                "INSERT INTO reversal_edges VALUES (?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-early-reversal","m43-late-return",
                 "m43-late-allocation",1,"2026-12-16T12:00:00Z"),
            )
        elif scenario == "TRANSIENT_OVER_CLAIM_LIMIT":
            # During 2026-10-23 -> 10-28, the claim rises 400+900=1300
            # against a signed 1000 original; it later reverses 900 and
            # finishes with a legal NET 500, hiding a transient false balance.
            source_hash=sha256(b"m43-interim-provider-credit").hexdigest()
            return_hash=sha256(b"m43-interim-provider-return").hexdigest()
            _new_credit(con,event_id="m43-interim-credit",amount=900,
                        at="2026-10-23T12:00:00Z",
                        source_hash=source_hash,proofs=proof)
            _new_counter(con,counter_id="m43-interim-return",
                         credit_id="m43-interim-credit",amount=900,
                         at="2026-10-27T12:00:00Z",
                         source_hash=return_hash,proofs=proof)
            con.execute(
                "INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-interim-alloc","case-1",
                 "m43-interim-credit",900,"REVIEW",900,"2026-10-23T13:00:00Z"),
            )
            con.execute(
                "INSERT INTO reversal_edges VALUES (?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-interim-reverse","m43-interim-return",
                 "m43-interim-alloc",900,"2026-10-28T12:00:00Z"),
            )
        elif scenario == "DUPLICATE_ALLOCATION_PAIR":
            con.execute(
                "UPDATE allocations SET amount_cents=200,fee_eligible_cents=200 "
                "WHERE allocation_id='allocation-400'"
            )
            con.execute(
                "INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-second-alloc","case-1","credit-400",
                 200,"REVIEW",200,"2026-10-18T13:30:00Z"),
            )
        elif scenario == "DUPLICATE_REVERSAL_PAIR":
            con.execute(
                "UPDATE reversal_edges SET amount_cents=499 "
                "WHERE reversal_id='reversal-500'"
            )
            con.execute(
                "INSERT INTO reversal_edges VALUES (?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-second-reversal","return-500",
                 "allocation-600",1,"2026-12-12T13:30:00Z"),
            )
        elif scenario == "DUPLICATE_CLAIM_SOURCE_HASH":
            con.execute(
                "INSERT INTO recovery_claims VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (BUYER,BU,"m43-second-claim","INV-101",
                 "SIM-CARRIER","SIM-BUYER","USD",1000,CLAIM,SRC,0),
            )
            proof.append(stamp(
                "SOURCE_OWNER","m43-second-owner","buyer-signer",
                "2026-10-01T10:00:00Z",
                claim_id="m43-second-claim",reference="INV-101",
                payer_id="SIM-CARRIER",payee_id="SIM-BUYER",
                currency="USD",amount_cents=1000,issued_at=CLAIM,
                source_hash=SRC,economic_issue_id="distinct-issue",
            ))
            proof.append(stamp(
                "FEE_CONTRACT","m43-second-terms","buyer-signer",
                "2026-10-01T10:00:00Z",claim_id="m43-second-claim",
                currency="USD",source_hash=SRC,fee_bps=2000,
                fee_cap_cents=400,contract_version="test-v2",
                agreement_sha256=sha256(b"m43-fake-terms").hexdigest(),
                effective_from="2026-10-01T00:00:00Z",
                effective_until="2027-01-01T00:00:00Z",
                revoked_at=None,
            ))
        elif scenario == "DUPLICATE_CREDIT_SOURCE_HASH":
            _new_credit(con,event_id="m43-shadow-credit",amount=1,
                        at="2026-10-18T15:00:00Z",
                        source_hash=sha256(b"credit-400").hexdigest(),proofs=proof)
        elif scenario == "DUPLICATE_RETURN_SOURCE_HASH":
            _new_counter(con,counter_id="m43-shadow-counter",
                         credit_id="credit-600",amount=1,
                         at="2026-12-12T14:00:00Z",
                         source_hash=sha256(b"return-500").hexdigest(),proofs=proof)
        elif scenario == "SIGNED_NEGATIVE_RETURN":
            _new_counter(con,counter_id="m43-negative-counter",
                         credit_id="credit-600",amount=-1,
                         at="2026-12-12T14:00:00Z",
                         source_hash=sha256(b"m43-negative-counter").hexdigest(),
                         proofs=proof)
        elif scenario == "SIGNED_MALFORMED_SOURCE_HASH":
            bogus = "NOT_A_SHA256_SOURCE"
            con.execute(
                "UPDATE settlement_events SET source_hash=? "
                "WHERE event_id='credit-400'", (bogus,),
            )
            idx=next(i for i,p in enumerate(proof)
                     if p.kind=="CREDIT_RECEIPT" and p.payload["event_id"]=="credit-400")
            old=proof[idx]
            proof[idx]=stamp(old.kind,old.evidence_id,old.issuer,old.issued_at,
                             **{**old.payload,"source_hash":bogus})
    return proof


def replay_one(scenario: str) -> dict:
    if type(scenario) is not str or scenario not in REJECTIONS:
        raise ValueError("M43_UNKNOWN_ADVERSARIAL_SCENARIO")
    with tempfile.TemporaryDirectory(prefix="retally-m43-current-verifier-only-") as temp:
        db=Path(temp)/"unconstrained-test.sqlite3"
        populate(db)
        proofs, fees=assertions_and_fees()
        positive=_observe(db, proofs, fees)
        if (positive.status!="PASS_SYNTHETIC_ONLY"
            or positive.scope!="SIGNED_SYNTHETIC_EVIDENCE_ONLY"
            or positive.verified_claims!=1
            or positive.verified_receipts!=2
            or positive.currency_totals!={"USD":BASELINE_USD}):
            raise ValueError("M43_POSITIVE_SYNTHETIC_MONEY_CHAIN_BROKEN")
        pre=sha256(db.read_bytes()).hexdigest()
        updated=_mutate(db, scenario, proofs)
        post=sha256(db.read_bytes()).hexdigest()
        if pre==post:
            raise ValueError("M43_NEGATIVE_SOURCE_SQLITE_NOT_MUTATED")
        try:
            _observe(db, updated, fees)
        except AssuranceRejected as exc:
            if exc.code!=REJECTIONS[scenario]:
                raise ValueError("M43_WRONG_REASON_IN_NEGATIVE_ASSURANCE:"+scenario+":"+exc.code) from exc
        else:
            raise ValueError("M43_CURRENT_VERIFIER_ACCEPTED_UNSAFE_SETTLEMENT:"+scenario)
        return {
            "scenario":scenario,
            "expected_exact_denial":REJECTIONS[scenario],
            "actual_exact_denial":REJECTIONS[scenario],
            "positive_control_passed":True,
            "negative_counterexample_rejected":True,
            "isolated_sqlite_changed":True,
            "isolated_before_sha256":pre,
            "isolated_after_sha256":post,
            "source_input_had_real_bank_carrier_signatures":False,
            "original_archived_vulnerable_revision_replayed":False,
            "historical_recoveryos_finding_closed":False,
        }


def run_campaign(*, as_of: date) -> dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M43_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(scenario) for scenario in REJECTIONS]
    if (len(cases)!=12
        or any(c["actual_exact_denial"]!=REJECTIONS[c["scenario"]]
               or c["historical_recoveryos_finding_closed"] is not False
               for c in cases)):
        raise ValueError("M43_UNTRUSTED_SOURCE_COUNTEREXAMPLE_NOT_REJECTED")
    result={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_research_lab":14,
        "new_lab_created":False,
        "current_verifier_negative_scenarios":12,
        "known_good_synthetic_positive_controls":12,
        "current_verifier_exact_negative_denials":12,
        "source_capabilities":[
            "STRICT_ALLOCATION_FEE_MODE_AND_DISQUALIFICATION",
            "REVERSAL_CHRONOLOGY_AND_CLAIM_BALANCE_PEAK",
            "UNIQUE_SCOPED_SOURCE_PROVENANCE_AND_LEDGER_EDGE",
            "SIGNED_INVALID_COUNTER_OR_DIGEST_EVIDENCE_REJECTED",
        ],
        "historical_original_findings_open":26,
        "historical_original_findings_closed":0,
        "archived_original_vulnerable_source_replayed":0,
        "unmet_independent_human_pilot_controls":18,
        "independent_customer_invoices_observed":0,
        "actual_customer_cash_recovered":None,
        "external_empirical_claims_authorized":0,
        "live_carrier_or_bank_evidence_used":False,
        "production_deployment_or_schedules_modified":False,
        "cases":cases,
        "caveat":(
            "All 12 direct source-level scenarios use disposable unconstrained "
            "fictional SQLite and test-only HMAC signing keys. They exercise "
            "the CURRENT read-only settlement verifier, not original "
            "historical vulnerable commits or independent bank/carrier data. "
            "A pass does not authorize real customer cash, actual invoice "
            "accuracy, company revenue, legal buyer consent or public claims. "
            "All 26 original findings and 18 independent human pilot controls "
            "remain unmet."
        ),
    }
    result["receipt_sha256"]=digest(result)
    return result


def render_html(report: dict) -> str:
    rows="".join(
        "<tr><th>"+escape(c["scenario"])+"</th><td>"
        +escape(c["actual_exact_denial"])+"</td><td>REJECTED / SYNTHETIC</td></tr>"
        for c in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY / M43 untrusted settlement verification</title>'
        '<style>body{font:15px/1.6 system-ui;color:#203a2a;'
        'background:#f6f8f5;max-width:1100px;margin:auto;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'td,th{border-bottom:1px solid #dce6de;padding:12px;text-align:left}'
        'small{color:#65746e}</style></head><body>'
        '<small>RETALLY / EXISTING LAB 14 / M43 / INTERNAL ONLY</small>'
        '<h1>Untrusted settlement source: 12 fail-closed tests</h1>'
        '<p>12 known-good fictional baselines and 12 exact negative denials. '
        '26 original findings remain open; no real recovered cash or '
        'bank, customer or carrier authority was established.</p>'
        '<table><thead><tr><th>Scenario</th><th>Exact denial</th>'
        '<th>State</th></tr></thead><tbody>'+rows+'</tbody></table>'
        '<p><small>'+escape(report["caveat"])+'</small></p></body></html>'
    )


def main() -> None:
    p=argparse.ArgumentParser(description="Read-only current-code negative replay")
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"settlement_source_m43.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (args.out/"settlement_source_m43.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "positive_controls":12,"exact_denials":12,
        "historical_defects_closed":0,"external_claims_approved":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
