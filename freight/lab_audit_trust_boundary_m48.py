"""RETALLY existing Lab 14 / M48: real persistent audit-log trust boundary.

M47 protected the settlement file, but the audit SQLite behind backup/restore
still auto-repaired missing triggers and silently reopened replaced files.
Exercise thirteen *current implementation* mutations against two fictional
hash-chained audit records, requiring exact safe denial of five reads, one
append, and one reopen. No historical bug closure or actual external evidence.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight.contracts import canonical_hash
from freight.settlement_file_identity_m47 import identity
from freight.audit_store_integrity_m48 import SCOPE as AUDIT_POLICY_SCOPE

SCOPE="RETALLY_LAB14_M48_PERSISTENT_AUDIT_PROTECTION_SYNTHETIC_ONLY"
ATTACKS={
    "REMOVE_IMMUTABLE_UPDATE":"M48_AUDIT_SCHEMA_CATALOG_DRIFT",
    "REMOVE_IMMUTABLE_DELETE":"M48_AUDIT_SCHEMA_CATALOG_DRIFT",
    "REMOVE_AUDIT_INPUT_ADMISSION":"M48_AUDIT_SCHEMA_CATALOG_DRIFT",
    "REPLACE_IMMUTABLE_UPDATE_WITH_NOOP":"M48_AUDIT_SCHEMA_CATALOG_DRIFT",
    "ADD_UNREVIEWED_AUDIT_INDEX":"M48_AUDIT_SCHEMA_CATALOG_DRIFT",
    "ALTER_AUDIT_TABLE_STRUCTURE":"M48_AUDIT_SCHEMA_CATALOG_DRIFT",
    "TAMPER_ORIGINAL_EVENT_RESTORE_TRIGGER":"M48_AUDIT_CHAIN_INVALID",
    "FORGE_AUDIT_SEQUENCE_GAP_RESTORE_TRIGGER":"M48_AUDIT_CHAIN_INVALID",
    "FORGE_INVALID_EVENT_TYPE_RESTORE_TRIGGER":"M48_AUDIT_CHAIN_INVALID",
    "REPLACE_WITH_EQUIVALENT_VALID_AUDIT":"M47_SQLITE_SOURCE_FILE_REPLACED",
    "REPLACE_WITH_EMPTY_VALID_AUDIT":"M47_SQLITE_SOURCE_FILE_REPLACED",
    "DELETE_AUDIT_FILE":"M47_SQLITE_SOURCE_FILE_MISSING",
    "SYMLINK_TO_VALID_AUDIT":"M47_SQLITE_SOURCE_SYMLINK_REJECTED",
}
READS=("count","records","head","verify","semantic_summary")


def _start(root:Path)->AuditStore:
    store=AuditStore(root/"audit.sqlite3",buyer_id="SIM-OWNER",
                     business_unit="SIM-BU")
    store.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="fictional-source-a",
        occurred_at="2026-10-01T10:00:00Z",
        evidence_hash="a"*64,
    )
    store.append(
        event_type=AuditEventType.TRUTH_FROZEN,
        object_id="fictional-truth-b",
        occurred_at="2026-10-01T11:00:00Z",
        evidence_hash="b"*64,
    )
    return store


def _catalog_fingerprint(db:Path)->str:
    if not os.path.lexists(db):
        return "MAIN_FILE_ABSENT"
    if db.is_symlink():
        return "SYMLINK_NOT_FOLLOWED"
    with sqlite3.connect(db.as_uri()+"?mode=ro",uri=True) as con:
        catalog=list(con.execute(
            "SELECT type,name,sql FROM sqlite_master "
            "WHERE type IN ('table','trigger','index','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ))
        records=list(con.execute(
            "SELECT * FROM audit_events ORDER BY buyer_id,business_unit,sequence"
        ))
    return canonical_hash({"catalog":catalog,"records":records})


def _copy_valid(src:Path,dst:Path)->None:
    con=sqlite3.connect(src.as_uri()+"?mode=ro",uri=True)
    out=sqlite3.connect(dst)
    try:
        con.backup(out)
        out.commit()
    finally:
        out.close()
        con.close()


def mutate_fixture(db:Path,scenario:str)->None:
    if type(scenario) is not str or scenario not in ATTACKS:
        raise ValueError("M48_UNREGISTERED_DISPOSABLE_AUDIT_MUTATION")
    alternate=db.with_name("m48-different-synthetic-audit.sqlite3")
    if scenario=="DELETE_AUDIT_FILE":
        db.unlink()
        return
    if scenario=="SYMLINK_TO_VALID_AUDIT":
        _copy_valid(db,alternate)
        db.unlink()
        db.symlink_to(alternate)
        return
    if scenario=="REPLACE_WITH_EQUIVALENT_VALID_AUDIT":
        _copy_valid(db,alternate)
        os.replace(alternate,db)
        return
    if scenario=="REPLACE_WITH_EMPTY_VALID_AUDIT":
        empty=AuditStore(alternate,buyer_id="SIM-OWNER",business_unit="SIM-BU")
        if empty.count()!=0:
            raise ValueError("M48_EMPTY_ALTERNATE_FIXTURE_NOT_EMPTY")
        os.replace(alternate,db)
        return

    with sqlite3.connect(db) as con:
        if scenario=="REMOVE_IMMUTABLE_UPDATE":
            con.execute("DROP TRIGGER audit_events_immutable_update")
        elif scenario=="REMOVE_IMMUTABLE_DELETE":
            con.execute("DROP TRIGGER audit_events_immutable_delete")
        elif scenario=="REMOVE_AUDIT_INPUT_ADMISSION":
            con.execute("DROP TRIGGER audit_events_input_guard")
        elif scenario=="REPLACE_IMMUTABLE_UPDATE_WITH_NOOP":
            con.execute("DROP TRIGGER audit_events_immutable_update")
            con.execute(
                "CREATE TRIGGER audit_events_immutable_update "
                "BEFORE UPDATE ON audit_events BEGIN SELECT 1; END"
            )
        elif scenario=="ADD_UNREVIEWED_AUDIT_INDEX":
            con.execute("CREATE INDEX m48_unauthorized_idx ON audit_events(object_id)")
        elif scenario=="ALTER_AUDIT_TABLE_STRUCTURE":
            con.execute("ALTER TABLE audit_events ADD COLUMN m48_unapproved TEXT")
        elif scenario in (
            "TAMPER_ORIGINAL_EVENT_RESTORE_TRIGGER",
            "FORGE_AUDIT_SEQUENCE_GAP_RESTORE_TRIGGER",
            "FORGE_INVALID_EVENT_TYPE_RESTORE_TRIGGER",
        ):
            original={
                row[0]:row[1] for row in con.execute(
                    "SELECT name,sql FROM sqlite_master WHERE type='trigger'"
                )
            }
            if scenario=="FORGE_AUDIT_SEQUENCE_GAP_RESTORE_TRIGGER":
                trigger="audit_events_immutable_delete"
                con.execute("DROP TRIGGER audit_events_immutable_delete")
                con.execute(
                    "DELETE FROM audit_events WHERE sequence=1"
                )
            else:
                trigger="audit_events_immutable_update"
                con.execute("DROP TRIGGER audit_events_immutable_update")
                if scenario=="TAMPER_ORIGINAL_EVENT_RESTORE_TRIGGER":
                    con.execute(
                        "UPDATE audit_events SET object_id='m48-forged-object' "
                        "WHERE sequence=1"
                    )
                else:
                    con.execute(
                        "UPDATE audit_events SET event_type='FORGED_STATUS' "
                        "WHERE sequence=1"
                    )
            # The DDL is restored exactly; only the hash-chain / business
            # content is now false. M48 must distinguish that from DDL drift.
            con.execute(original[trigger])


def _actions(store:AuditStore)->dict:
    return {
        "count":store.count,
        "records":store.records,
        "head":store.head,
        "verify":store.verify,
        "semantic_summary":store.semantic_summary,
        "append_new":lambda:store.append(
            event_type=AuditEventType.SOURCE_PRESENT,
            object_id="m48-synthetic-follow-up",
            occurred_at="2026-10-01T12:00:00Z",
            evidence_hash=sha256(b"m48-fictional-follow-up").hexdigest(),
        ),
    }


def replay_one(scenario:str)->dict:
    if type(scenario) is not str or scenario not in ATTACKS:
        raise ValueError("M48_UNKNOWN_AUDIT_TRUST_BOUNDARY_ATTACK")
    with tempfile.TemporaryDirectory(prefix="retally-m48-audit-src-") as temp:
        store=_start(Path(temp))
        path=Path(store.path)
        actions=_actions(store)
        if (actions["count"]()!=2
            or len(actions["records"]())!=2
            or actions["head"]()!=store.records()[-1].event_hash
            or actions["semantic_summary"]()["record_count"]!=2):
            raise ValueError("M48_POSITIVE_HASH_CHAIN_SOURCE_NOT_VALID")
        before=_catalog_fingerprint(path)
        start_inode=identity(path)
        mutate_fixture(path,scenario)
        if scenario not in ("DELETE_AUDIT_FILE","SYMLINK_TO_VALID_AUDIT"):
            if before==_catalog_fingerprint(path) and start_inode==identity(path):
                raise ValueError("M48_NEGATIVE_SOURCE_MUTATION_NOT_APPLIED")
        altered=_catalog_fingerprint(path)
        denied=[]
        for method in (*READS,"append_new"):
            try:
                actions[method]()
            except RuntimeError as exc:
                if ATTACKS[scenario] not in str(exc):
                    raise ValueError(
                        "M48_WRONG_HASH_CHAIN_OR_SCHEMA_REJECTION:"+scenario+":"+method
                    ) from exc
                denied.append(method)
            else:
                raise ValueError("M48_UNSAFE_AUDIT_EVENT_SOURCE_ACCEPTED:"+scenario+":"+method)
        # A legitimately restored valid file can be accepted only through
        # EXPLICIT construction of a NEW session. That is not approval by the
        # already-open instance or independently attested historical truth.
        reviewed_new_session_allowed = scenario in (
            "REPLACE_WITH_EQUIVALENT_VALID_AUDIT",
            "REPLACE_WITH_EMPTY_VALID_AUDIT",
        )
        if reviewed_new_session_allowed:
            fresh = AuditStore(path,buyer_id=store.buyer_id,
                               business_unit=store.business_unit)
            expected_count = (
                0 if scenario == "REPLACE_WITH_EMPTY_VALID_AUDIT" else 2
            )
            if fresh.count() != expected_count:
                raise ValueError("M48_EXPLICIT_NEW_SESSION_INVALID_SOURCE")
        elif scenario != "DELETE_AUDIT_FILE":
            try:
                AuditStore(path,buyer_id=store.buyer_id,
                           business_unit=store.business_unit)
            except RuntimeError as exc:
                if ATTACKS[scenario] not in str(exc):
                    raise ValueError(
                        "M48_REOPEN_WRONG_FAILURE:"+scenario
                    ) from exc
            else:
                raise ValueError(
                    "M48_MALFORMED_AUDIT_REOPENED_OR_REPAIRED:"+scenario
                )
        # Deliberately do NOT construct a fresh file after deletion; it
        # could erase last-known audit history unless a human reviews it.
        if scenario!="DELETE_AUDIT_FILE" and _catalog_fingerprint(path)!=altered:
            raise ValueError("M48_REJECTED_TEST_MUTATION_WAS_REPAIRED")
        return {
            "scenario":scenario,
            "exact_expected_denial":ATTACKS[scenario],
            "positive_original_test_events":2,
            "existing_session_read_denials":len(READS),
            "existing_session_append_denials":1,
            "reopened_invalid_existing_file_rejected":
                not reviewed_new_session_allowed and scenario!="DELETE_AUDIT_FILE",
            "explicit_new_session_review_required_for_valid_replacement":
                reviewed_new_session_allowed,
            "original_source_modified_only_in_disposable_sqlite":True,
            "original_hash_chain_event_bytes_not_externally_attested":True,
            "original_historical_defect_closed":False,
            "actual_customer_account_or_carrier_records_used":False,
            "denied_source_action_ids":denied,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M48_INVALID_RESEARCH_DATE")
    cases=[replay_one(scenario) for scenario in ATTACKS]
    if (len(cases)!=13
        or any(c["exact_expected_denial"]!=ATTACKS[c["scenario"]]
               or c["existing_session_read_denials"]!=5
               or c["existing_session_append_denials"]!=1
               for c in cases)):
        raise ValueError("M48_INCOMPLETE_AUDIT_SOURCE_PROOF")
    result={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "original_research_labs":14,
        "new_lab_created":False,
        "reviewed_audit_source_policy_scope":AUDIT_POLICY_SCOPE,
        "current_real_audit_file_attack_classes":len(cases),
        "verified_fictional_positive_source_records_per_attack":2,
        "current_audit_read_denials":len(cases)*len(READS),
        "current_audit_append_denials":len(cases),
        "original_historical_findings_open":26,
        "original_historical_findings_closed":0,
        "independent_first_customer_approval_gates_unmet":18,
        "independently_attested_audit_log_or_original_customer_data":False,
        "actual_customer_or_bank_transactions_imported":0,
        "externally_publishable_empirical_claims":0,
        "production_deployed_or_schedules_modified":False,
        "cases":cases,
        "caveat":(
            "Thirteen current-code synthetic audit-log attacks show exact "
            "rejection by already-open AuditStore reads/appends. The local "
            "application hash chain is not an external immutable log and "
            "has no independently trusted historical anchor or timestamp. "
            "An attacker can potentially rewrite a whole internally valid "
            "chain; the test does not prevent that. No real bank/carrier "
            "consent, customer data, financial recovery or original "
            "historical finding closure is established. All 26 historical "
            "findings and 18 first-customer approval controls remain open."
        ),
    }
    result["receipt_sha256"]=canonical_hash(result)
    return result


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(c["scenario"])+"</th><td>"
        +escape(c["exact_expected_denial"])+"</td>"
        "<td>5 READ / 1 APPEND</td></tr>"
        for c in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | M48 Audit Evidence Trust</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f5f8f4;'
        'color:#20372a;max-width:1050px;margin:auto;padding:24px}'
        'table{background:white;width:100%;border-collapse:collapse}'
        'td,th{border-bottom:1px solid #d5e1d7;padding:11px;text-align:left}'
        'small{color:#68776d}</style></head><body>'
        '<small>RETALLY / EXISTING LAB 14 / M48 / INTERNAL ONLY</small>'
        '<h1>Audit trail does not silently repair or switch sources</h1>'
        '<p>13 disposable source attacks; 65 blocked reads and 13 blocked '
        'append attempts. Local hash-chain consistency only, NOT '
        'independently anchored evidence. All 26 historical findings open.</p>'
        '<table><thead><tr><th>Attack</th><th>Typed source denial</th>'
        '<th>Current session</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="Synthetic audit trail failure rehearsal")
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    report=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"audit_trust_boundary_m48.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (args.out/"audit_trust_boundary_m48.html").write_text(
        render_html(report),encoding="utf-8")
    print(json.dumps({
        "current_audit_source_attacks":13,
        "read_denials":report["current_audit_read_denials"],
        "append_denials":report["current_audit_append_denials"],
        "historical_findings_closed":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
