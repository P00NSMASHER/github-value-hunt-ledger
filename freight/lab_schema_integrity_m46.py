"""Lab 14 / M46: defend current persistent settlement schema against silent DDL drift.

Ten controlled edits to a fully valid, disposable and fictional SQLite store.
Every mutation preserves baseline money/cash rows (tampered DDL only), yet
must be denied at each existing financial read, report, writer and reopen.
This does NOT authenticate independent bank evidence or close prior defects.
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
from freight.settlement_store import SettlementEventRecord, SettlementStore
from freight.test_lab_phase3_real_chain import funded_store
from freight.settlement_schema_guard_m46 import assert_sqlite_schema, SCOPE as POLICY_SCOPE

SCOPE="RETALLY_LAB14_M46_PERSISTENT_SCHEMA_DDL_NEGATIVE_TESTS_SYNTHETIC_ONLY"
DDL_ATTACKS={
    "REMOVE_ALLOCATION_CAPACITY_TRIGGER": (
        "DROP TRIGGER allocation_event_capacity",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "REMOVE_APPEND_ONLY_TRIGGER": (
        "DROP TRIGGER immutable_alloc_u",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "REPLACE_IMMUTABILITY_WITH_NOOP": (
        "DROP TRIGGER immutable_alloc_u;"
        "CREATE TRIGGER immutable_alloc_u BEFORE UPDATE ON allocations "
        "BEGIN SELECT 1; END",
        "M46_SQLITE_DEFINITION_CHANGED",
    ),
    "REMOVE_CLAIM_SOURCE_ADMISSION": (
        "DROP TRIGGER claim_input_guard",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "REMOVE_REVERSAL_CAPACITY": (
        "DROP TRIGGER reversal_counter_capacity",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "REMOVE_AUTO_REVIEW_LOCK": (
        "DROP TRIGGER allocation_auto_review_lock",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "REMOVE_REQUIRED_INDEX": (
        "DROP INDEX idx_alloc_claim",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "INJECT_UNREVIEWED_INDEX": (
        "CREATE INDEX m46_shadow_idx ON allocations(event_id)",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "INJECT_UNREVIEWED_VIEW": (
        "CREATE VIEW m46_shadow_view AS SELECT * FROM recovery_claims",
        "M46_SQLITE_CATALOG_OBJECTS_CHANGED",
    ),
    "ALTER_FINANCIAL_LEDGER_TABLE": (
        "ALTER TABLE allocations ADD COLUMN m46_unapproved_field TEXT",
        "M46_SQLITE_DEFINITION_CHANGED",
    ),
}
READ_ACTIONS=(
    "realized_cents",
    "fee_eligible_cents",
    "claim_residual",
    "event_residual",
    "count",
    "report_snapshot_json",
    "assert_semantic_integrity",
)
EXPECTED_READ={
    "realized_cents":500,
    "fee_eligible_cents":500,
    "claim_residual":500,
    "event_residual":0,
    "count":2,
}


def _catalog_receipt(db:Path)->str:
    with sqlite3.connect(db) as conn:
        result=list(conn.execute(
            "SELECT type,name,sql FROM sqlite_master "
            "WHERE type IN ('table','index','trigger','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ))
    return digest(result)


def _actions(store:SettlementStore)->dict:
    return {
        "realized_cents":store.realized_cents,
        "fee_eligible_cents":store.fee_eligible_cents,
        "claim_residual":lambda:store.claim_residual("case-1"),
        "event_residual":lambda:store.event_residual("credit-400"),
        "count":lambda:store.count("allocations"),
        "report_snapshot_json":store.report_snapshot_json,
        "assert_semantic_integrity":store.assert_semantic_integrity,
        "new_provider_write":lambda:store.ingest_event(SettlementEventRecord(
            "m46-test-source-only", "INV-100", "SIM-CARRIER", "SIM-BUYER",
            "USD", 1, "2026-12-20T12:00:00Z",
            sha256(b"m46-fictional-unrelated-provider-credit").hexdigest(),"EXTERNAL",
        )),
    }


def mutate_disposable_sqlite(db:Path,scenario:str)->None:
    if type(scenario) is not str or scenario not in DDL_ATTACKS:
        raise ValueError("M46_UNREGISTERED_SCHEMA_MUTATION")
    script=DDL_ATTACKS[scenario][0]
    # Predefined allowlist of static literal SQL only.
    with sqlite3.connect(db) as con:
        con.executescript(script)
    # Identities/amounts must be identical. No raw customer data leaves tmp.


def replay_one(scenario:str)->dict:
    if type(scenario) is not str or scenario not in DDL_ATTACKS:
        raise ValueError("M46_UNKNOWN_SCHEMA_ATTACK")
    expected=DDL_ATTACKS[scenario][1]
    with tempfile.TemporaryDirectory(prefix="retally-m46-disposable-schema-") as tmp:
        store=funded_store(tmp)
        db=Path(store.path)
        actions=_actions(store)
        baseline={key:actions[key]() for key in EXPECTED_READ}
        if baseline!=EXPECTED_READ:
            raise ValueError("M46_VALID_FINANCIAL_BASELINE_REJECTED")
        valid_policy=store.assert_semantic_integrity()
        if (valid_policy.get("validated_claims")!=1
            or valid_policy.get("validated_allocations")!=2
            or valid_policy.get("validated_returns")!=1
            or valid_policy.get("validated_reversals")!=1):
            raise ValueError("M46_POSITIVE_PERSISTENT_SCOPED_SEMANTICS_INVALID")
        before_catalog=_catalog_receipt(db)
        mutate_disposable_sqlite(db,scenario)
        tampered_catalog=_catalog_receipt(db)
        if before_catalog==tampered_catalog:
            raise ValueError("M46_SCHEMA_ATTACK_DID_NOT_CHANGE_CATALOG")
        # Financial rows stay sound. This specifically proves schema policy
        # drift detection, not unrelated amounts/semantic rejection.
        actions_after=_actions(store)
        denied=[]
        for label in (*READ_ACTIONS,"new_provider_write"):
            try:
                actions_after[label]()
            except RuntimeError as error:
                if expected not in str(error):
                    raise ValueError(
                        "M46_WRONG_SOURCE_DENIAL:"+scenario+":"+label
                    ) from error
                denied.append(label)
            else:
                raise ValueError(
                    "M46_DAMAGED_SCHEMA_WAS_ACCEPTED:"+scenario+":"+label
                )
        try:
            SettlementStore(db,buyer_id=store.buyer_id,
                            business_unit=store.business_unit)
        except RuntimeError as error:
            if expected not in str(error):
                raise ValueError(
                    "M46_REOPEN_DENIAL_REASON_CHANGED:"+scenario
                ) from error
        else:
            raise ValueError("M46_CORRUPT_SOURCE_AUTO_REPAIRED_ON_REOPEN")
        if _catalog_receipt(db)!=tampered_catalog:
            raise ValueError("M46_DENIED_REOPEN_OR_OPERATION_REPAIRED_SCHEMA")
        return {
            "schema_mutation":scenario,
            "expected_denial":expected,
            "positive_original_money_reads":len(EXPECTED_READ),
            "read_surface_exact_denials":len(READ_ACTIONS),
            "write_attempt_denied":True,
            "reopen_denied_without_recreating_triggers":True,
            "denied_sources_did_not_change_mutated_schema":True,
            "denied_api_surface_ids":denied,
            "original_schema_catalog_digest":before_catalog,
            "test_only_mutated_schema_catalog_digest":tampered_catalog,
            "original_historical_vulnerable_revision_reproduced":False,
            "original_historical_defect_closed":False,
            "real_customer_carrier_or_bank_credentials_used":False,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of < date(2026,10,13):
        raise ValueError("M46_INVALID_AS_OF_DATE")
    cases=[replay_one(scenario) for scenario in DDL_ATTACKS]
    if (len(cases)!=10
        or any(c["expected_denial"]!=DDL_ATTACKS[c["schema_mutation"]][1]
               or c["read_surface_exact_denials"]!=len(READ_ACTIONS)
               or c["write_attempt_denied"] is not True
               or c["reopen_denied_without_recreating_triggers"] is not True
               for c in cases)):
        raise ValueError("M46_MISSING_VALIDATED_SCHEMA_MUTATION_PROOF")
    body={
        "schema_version":1,
        "scope":SCOPE,
        "existing_research_lab_count":14,
        "new_lab_created":False,
        "as_of":as_of.isoformat(),
        "approved_schema_policy_scope":POLICY_SCOPE,
        "disposable_ddl_mutation_cases":10,
        "positive_synthetic_money_controls":len(EXPECTED_READ)*10,
        "financial_read_denials":len(READ_ACTIONS)*10,
        "attempted_write_denials":10,
        "preexisting_file_reopen_denials":10,
        "denied_mutations_preserved_test_source":True,
        "original_historical_findings_open":26,
        "original_historical_findings_closed":0,
        "human_first_customer_pilot_gates_unmet":18,
        "independent_real_bank_evidence_reproduced":False,
        "actual_customer_invoices_imported":0,
        "actual_company_revenue_cents":0,
        "public_empirical_claims_approved":0,
        "no_live_deployments_or_schedules_changed":True,
        "cases":cases,
        "caveat":(
            "A consistent SQLite ledger with weakened or missing triggers "
            "is structurally unsafe even before financial rows diverge. M46 "
            "checks exact first-party schema definition and validates only "
            "disposable fictional SQLite. It does not independently prove "
            "original invoice ownership, real provider signatures, customer "
            "cash, legal authorizations or any historical bug closure. "
            "All 26 original findings and 18 human pilot gates stay open."
        ),
    }
    body["receipt_sha256"]=digest(body)
    return body


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(x["schema_mutation"])+"</th><td>"+
        escape(x["expected_denial"])+"</td><td>7 READ / 1 WRITE / 1 REOPEN</td></tr>"
        for x in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M46 | Durable Financial Schema Integrity</title>'
        '<style>body{font:15px/1.6 system-ui;max-width:1100px;margin:auto;'
        'padding:25px;background:#f5f8f4;color:#1f3f2e}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'th,td{border-bottom:1px solid #dce8df;padding:10px;text-align:left}'
        'small{color:#687b6e}</style></head><body>'
        '<small>RETALLY / LAB 14 / M46 / SYNTHETIC INTERNAL ONLY</small>'
        '<h1>Financial schema tampering is blocked before records change</h1>'
        '<p>10 DDL attacks, 70 denied reads, 10 denied writes, 10 denied '
        'reopens. All historical original defects stay open: 26/26. '
        'No verified real bank, carrier, customer or recovered cash.</p>'
        '<table><thead><tr><th>Schema mutation</th><th>Exact denial</th>'
        '<th>Protected operations</th></tr></thead><tbody>'+
        rows+'</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="Internal disposable SQLite DDL test")
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"sqlite_schema_integrity_m46.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (args.out/"sqlite_schema_integrity_m46.html").write_text(
        render_html(result),encoding="utf-8")
    print(json.dumps({
        "read_denials":result["financial_read_denials"],
        "write_denials":result["attempted_write_denials"],
        "reopen_denials":result["preexisting_file_reopen_denials"],
        "historical_findings_closed":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
