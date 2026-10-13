"""RETALLY Lab 14 / M44 — persistent settlement semantic drift rehearsal.

Existing SettlementStore runs SQLite constraints/triggers at ingestion, but a
privileged file edit can bypass insert-time financial rules. Replay eight
different financially contradictory CURRENT-code files in disposable, fictional
SQLite, and verify all THREE read-only sources fail closed: reopen, report
snapshot and explicit semantic audit.

No original vulnerable git baseline, bank/carrier proof, customer data or
external publication permission is produced.
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

from freight.lab_assurance import digest
from freight.settlement_store import SettlementStore
from freight.test_lab_phase3_real_chain import funded_store

SCOPE="RETALLY_LAB14_M44_PERSISTENT_SETTLEMENT_SEMANTIC_DRIFT_SYNTHETIC_ONLY"
ATTACKS={
    "RECEIPT_OVER_ALLOCATED":"M44_ALLOCATION_CAPACITY_EXCEEDS_CREDIT",
    "RETURN_OVER_CREDIT":"M44_RETURN_CAPACITY_EXCEEDS_CREDIT",
    "FEE_ELIGIBILITY_DRIFT":"M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT",
    "COUNTERPARTY_DRIFT":"M44_ALLOCATION_CURRENCY_OR_COUNTERPARTY_DRIFT",
    "REVERSAL_WRONG_ORIGINAL":"M44_REVERSAL_WRONG_ORIGINAL_RECEIPT",
    "REVERSAL_OVER_ALLOCATION":"M44_REVERSAL_CAPACITY_EXCEEDS_ALLOCATION",
    "TRANSIENT_OVERCLAIM":"M44_TRANSIENT_CLAIM_CAPACITY_EXCEEDED",
    "FEE_DISQUALIFICATION_DRIFT":"M44_ALLOCATION_FEE_ELIGIBILITY_DRIFT",
}
IMMUTABLE_TRIGGERS={
    "RECEIPT_OVER_ALLOCATED":("immutable_event_u",),
    "RETURN_OVER_CREDIT":("immutable_counter_u",),
    "FEE_ELIGIBILITY_DRIFT":("immutable_alloc_u",),
    "COUNTERPARTY_DRIFT":("immutable_event_u",),
    "REVERSAL_WRONG_ORIGINAL":("immutable_counter_u",),
    "REVERSAL_OVER_ALLOCATION":("immutable_reverse_u",),
    "TRANSIENT_OVERCLAIM":("allocation_claim_capacity",),
    "FEE_DISQUALIFICATION_DRIFT":("immutable_claim_u",),
}


def _raw_digest(db: Path) -> str:
    tables=("recovery_claims","settlement_events","allocations",
            "counter_events","reversal_edges")
    with sqlite3.connect(db) as c:
        data=[
            (name,list(c.execute("SELECT * FROM "+name+" ORDER BY rowid")))
            for name in tables
        ]
    return digest(data)


def _attack(db: Path, scenario: str) -> None:
    if type(scenario) is not str or scenario not in ATTACKS:
        raise ValueError("M44_UNKNOWN_SYNTHETIC_STORE_MUTATION")
    with sqlite3.connect(db) as c:
        for trigger in IMMUTABLE_TRIGGERS[scenario]:
            # Closed constant allowlist, no user string enters SQL identifiers.
            if trigger not in {x for xs in IMMUTABLE_TRIGGERS.values() for x in xs}:
                raise ValueError("M44_UNTRUSTED_SQLITE_MUTATION")
            c.execute('DROP TRIGGER "'+trigger+'"')
        if scenario=="RECEIPT_OVER_ALLOCATED":
            c.execute(
                "UPDATE settlement_events SET amount_cents=399 "
                "WHERE event_id='credit-400'"
            )
        elif scenario=="RETURN_OVER_CREDIT":
            c.execute(
                "UPDATE counter_events SET amount_cents=601 "
                "WHERE counter_id='return-500'"
            )
        elif scenario=="FEE_ELIGIBILITY_DRIFT":
            c.execute(
                "UPDATE allocations SET fee_eligible_cents=399 "
                "WHERE allocation_id='allocation-400'"
            )
        elif scenario=="COUNTERPARTY_DRIFT":
            c.execute(
                "UPDATE settlement_events SET payer_id='SIM-FORGER' "
                "WHERE event_id='credit-400'"
            )
        elif scenario=="REVERSAL_WRONG_ORIGINAL":
            c.execute(
                "UPDATE counter_events SET original_event_id='credit-400' "
                "WHERE counter_id='return-500'"
            )
        elif scenario=="REVERSAL_OVER_ALLOCATION":
            c.execute(
                "UPDATE reversal_edges SET amount_cents=601 "
                "WHERE reversal_id='reversal-500'"
            )
        elif scenario=="FEE_DISQUALIFICATION_DRIFT":
            c.execute(
                "UPDATE recovery_claims SET fee_disqualified=1 "
                "WHERE claim_id='case-1'"
            )
        elif scenario=="TRANSIENT_OVERCLAIM":
            # 400 original cents + 900 untrusted interim cents = peak 1300
            # against signed claim 1000. It is later returned and has a
            # superficially acceptable net 500. This synthetic file bypasses
            # INSERT-time capacity guard just as a privileged bad import can.
            c.execute(
                "INSERT INTO settlement_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "SIM-BUYER","SIM-DIVISION","m44-extra-credit","INV-100",
                    "SIM-CARRIER","SIM-BUYER","USD",900,
                    "2026-10-23T12:00:00.000000Z",
                    sha256(b"m44-extra-test-receipt").hexdigest(),"EXTERNAL",
                ),
            )
            c.execute(
                "INSERT INTO allocations VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    "SIM-BUYER","SIM-DIVISION","m44-extra-alloc","case-1",
                    "m44-extra-credit",900,"REVIEW",900,
                    "2026-10-23T13:00:00.000000Z",
                ),
            )
            c.execute(
                "INSERT INTO counter_events VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    "SIM-BUYER","SIM-DIVISION","m44-extra-return",
                    "m44-extra-credit","USD",900,
                    "2026-10-27T12:00:00.000000Z",
                    sha256(b"m44-extra-test-return").hexdigest(),"RETURN",
                ),
            )
            c.execute(
                "INSERT INTO reversal_edges VALUES (?,?,?,?,?,?,?)",
                (
                    "SIM-BUYER","SIM-DIVISION","m44-extra-reverse",
                    "m44-extra-return","m44-extra-alloc",900,
                    "2026-10-28T12:00:00.000000Z",
                ),
            )
    if scenario=="TRANSIENT_OVERCLAIM":
        with sqlite3.connect(db) as c:
            gross=c.execute("SELECT SUM(amount_cents) FROM allocations").fetchone()[0]
            reversed_cents=c.execute(
                "SELECT SUM(amount_cents) FROM reversal_edges"
            ).fetchone()[0]
        if (gross,reversed_cents,gross-reversed_cents)!=(1900,1400,500):
            raise ValueError("M44_TRANSIENT_EXCESS_TEST_FIXTURE_INVALID")


def replay_one(scenario: str) -> dict:
    if type(scenario) is not str or scenario not in ATTACKS:
        raise ValueError("M44_UNKNOWN_PERSISTENT_SETTLEMENT_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m44-synthetic-store-") as root:
        store=funded_store(root)
        db=Path(store.path)
        before=store.assert_semantic_integrity()
        good=json.loads(store.report_snapshot_json())
        if (before["validated_claims"]!=1 or before["validated_allocations"]!=2
            or before["validated_returns"]!=1 or before["validated_reversals"]!=1
            or before["no_external_original_source_attestation"] is not True
            or len(good["tables"]["recovery_claims"])!=1
            or store.realized_cents()!=500
            or store.fee_eligible_cents()!=500):
            raise ValueError("M44_KNOWN_GOOD_PERSISTENT_SOURCE_NOT_VALIDATED")
        prior=_raw_digest(db)
        _attack(db,scenario)
        changed=_raw_digest(db)
        if prior==changed:
            raise ValueError("M44_PRIVILEGED_TEST_MUTATION_WAS_NOT_APPLIED")
        outcomes={}
        for operation,action in (
            ("already_open_store_report",store.report_snapshot_json),
            ("explicit_current_store_audit",store.assert_semantic_integrity),
            ("reopen_existing_store",lambda:SettlementStore(
                db,buyer_id=store.buyer_id,business_unit=store.business_unit
            )),
        ):
            try:
                action()
            except RuntimeError as err:
                if ("M44_"+ATTACKS[scenario].split("M44_",1)[1]) not in str(err):
                    raise ValueError("M44_UNEXPECTED_REJECTION_REASON:"+operation) from err
                outcomes[operation]=True
            else:
                raise ValueError("M44_TAMPERED_FINANCIAL_SOURCE_WAS_EXPORTED:"+operation)
        return {
            "scenario":scenario,
            "positive_scoped_persistent_store_verified":True,
            "actual_sqlite_source_rows_changed":True,
            "expected_exact_rejection":ATTACKS[scenario],
            "current_store_report_rejected":outcomes["already_open_store_report"],
            "current_store_audit_rejected":outcomes["explicit_current_store_audit"],
            "reopen_existing_store_rejected":outcomes["reopen_existing_store"],
            "gross_test_recovery_after_attack_not_externally_authenticated":True,
            "before_fictional_sqlite_receipt_sha256":prior,
            "after_fictional_sqlite_receipt_sha256":changed,
            "original_historical_failure_reproduced_on_vulnerable_revision":False,
            "original_historical_recoveryos_defect_closed":False,
            "live_customer_or_bank_data_read":False,
        }


def run_campaign(*,as_of:date) -> dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M44_INVALID_AS_OF_DATE")
    cases=[replay_one(k) for k in ATTACKS]
    if (len(cases)!=8 or any(
        x["expected_exact_rejection"]!=ATTACKS[x["scenario"]]
        or not x["current_store_report_rejected"]
        or not x["current_store_audit_rejected"]
        or not x["reopen_existing_store_rejected"]
        for x in cases
    )):
        raise ValueError("M44_PERSISTENT_STORE_DRIFT_PROOFS_FAILED")
    result={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_research_lab":14,
        "new_lab_created":False,
        "current_persistent_store_cases":8,
        "positive_current_store_controls":8,
        "reported_financial_drift_denials":8,
        "explicit_audit_denials":8,
        "reopen_denials":8,
        "original_historical_findings_open":26,
        "original_historical_findings_closed":0,
        "original_vulnerable_git_baselines_replayed":0,
        "separate_independent_human_customer_pilot_controls_unmet":18,
        "actual_customer_data_imports":0,
        "actual_bank_or_carrier_evidence_verified":False,
        "external_empirical_recovery_claims_approved":0,
        "no_production_deployments_or_schedules_changed":True,
        "cases":cases,
        "caveat":(
            "Eight privileged-edit tests on disposable current SettlementStore "
            "SQLite demonstrate local semantic read/restore rejection. This is "
            "not authenticated original buyer, bank or carrier evidence, an "
            "unchanged-history guarantee or a certified security audit. Real "
            "customers, settlement funds, legal signoffs, published recovery "
            "statistics and original historical bug closures remain outside "
            "these tests. The original 26 findings stay OPEN_UNVERIFIED."
        ),
    }
    result["receipt_sha256"]=digest(result)
    return result


def render_html(report:dict)->str:
    cards="".join(
        "<tr><th>"+escape(x["scenario"])+"</th><td>"
        +escape(x["expected_exact_rejection"])
        +"</td><td>REOPEN + REPORT + AUDIT BLOCKED</td></tr>"
        for x in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M44 persistent source semantics</title>'
        '<style>body{font:15px/1.6 system-ui;color:#20392d;'
        'background:#f6f8f4;max-width:1100px;margin:auto;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'td,th{border-bottom:1px solid #dbe7dc;padding:11px;text-align:left}'
        'small{color:#68776e}</style></head><body>'
        '<small>RETALLY / LAB 14 / M44 / INTERNAL ONLY</small>'
        '<h1>Persistent settlement file tamper rejection</h1>'
        '<p>Eight fictional scenarios rejected on reopen, current report '
        'and explicit audit. The 26 historical findings remain open; '
        'no real customer or banking authority is established.</p>'
        '<table><thead><tr><th>Case</th><th>Exact local denial</th>'
        '<th>Outcome</th></tr></thead><tbody>'+cards+'</tbody></table>'
        '<p><small>'+escape(report["caveat"])+'</small></p></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Test-only persistent SQLite audit")
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=run_campaign(as_of=a.as_of_date)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"persistent_semantic_m44.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (a.out/"persistent_semantic_m44.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "positive_fictional_controls":8,"blocked_corrupted_sqlite":8,
        "original_defects_closed":0,"external_claims_approved":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
