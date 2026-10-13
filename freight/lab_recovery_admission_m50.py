"""RETALLY Lab 14 / M50 — independently re-open published recovery files.

Thirteen mutated *published* two-SQLite bundles are given valid-looking
locally recomputed SHA and M49 completion-marker receipts. The predecessor
validator would check only those unkeyed receipts; the hardened CURRENT
validator additionally reopens every actual SQLite file read-only and checks
all-tenant source integrity and the exact captured restore generation.

This is local synthetic source consistency, not external bank authentication.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict,replace
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sqlite3
import tempfile

from freight import backup_restore as backup
from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight.contracts import canonical_hash
from freight.lab_assurance import digest
from freight.settlement_store import SettlementStore,SettlementEventRecord
from freight.test_backup_restore import populated

SCOPE="RETALLY_LAB14_M50_REHASHED_BACKUP_RESTORE_ADMISSION_SYNTHETIC_ONLY"
CASES={
    "AUDIT_BACKUP_MISSING_IMMUTABLE_TRIGGER":"M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID",
    "AUDIT_BACKUP_REHASHED_INVALID_CHAIN":"M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID",
    "SETTLEMENT_BACKUP_MISSING_CAPACITY_TRIGGER":"M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID",
    "SETTLEMENT_BACKUP_WRONG_PAYER_WITH_ORIGINAL_DDL":"M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID",
    "AUDIT_BACKUP_LATER_VALID_EVENT":"M50_RECOVERY_BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH",
    "AUDIT_RESTORE_LATER_VALID_EVENT":"M50_RECOVERY_RESTORE_ALL_TENANT_SOURCE_GENERATION_MISMATCH",
    "SETTLEMENT_BACKUP_LATER_VALID_CREDIT":"M50_RECOVERY_BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH",
    "SETTLEMENT_RESTORE_LATER_VALID_CREDIT":"M50_RECOVERY_RESTORE_ALL_TENANT_SOURCE_GENERATION_MISMATCH",
    "MANIFEST_SOURCE_SEMANTIC_FIELD_CHANGED":"M50_RECOVERY_MANIFEST_SOURCE_RECEIPT_FIELDS_NOT_BOUND",
    "MANIFEST_FAKE_HUMAN_APPROVAL":"M50_RECOVERY_FALSE_RESTORE_PROVENANCE_OR_HUMAN_APPROVAL",
    "MANIFEST_FAKE_ORIGINAL_LOGICAL_DIGEST":"M50_RECOVERY_BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH",
    "LOCAL_REPORT_WRONG_TENANT_SCOPE":"M50_RECOVERY_SCOPED_AUDIT_OR_SETTLEMENT_RECEIPT_MISMATCH",
    "COMPLETION_MARKER_REPLACED_WITH_SYMLINK":"M50_RECOVERY_UNTRUSTED_BUNDLE_OR_COMPLETION_MARKER_SYMLINK",
}
FILES={
    "audit.backup.sqlite3":"audit_backup_sha256",
    "settlement.backup.sqlite3":"settlement_backup_sha256",
    "audit.restored.sqlite3":"audit_restore_sha256",
    "settlement.restored.sqlite3":"settlement_restore_sha256",
}


def _alter_catalog(db:Path,trigger:str,*,replacement_sql:str|None=None,
                   edit_sql:str|None=None)->None:
    with sqlite3.connect(db) as conn:
        original=conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
            (trigger,)
        ).fetchone()
        if original is None:
            raise ValueError("M50_TEST_EXPECTED_ORIGINAL_TRIGGER_ABSENT")
        conn.execute('DROP TRIGGER "'+trigger+'"')
        if edit_sql:
            conn.execute(edit_sql)
        if replacement_sql:
            conn.execute(replacement_sql if replacement_sql!="ORIGINAL" else original[0])


def _append_audit(db:Path,label:str)->None:
    a=AuditStore(db,buyer_id="BUYER-A",business_unit="OPS")
    a.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="m50-fictional-"+label,
        occurred_at="2026-09-27T12:00:00Z",
        evidence_hash=sha256(label.encode()).hexdigest(),
    )


def _append_settlement(db:Path,label:str)->None:
    s=SettlementStore(db,buyer_id="BUYER-A",business_unit="OPS")
    s.ingest_event(SettlementEventRecord(
        "m50-"+label,"INV-1","carrier","buyer","USD",1,
        "2026-09-27T12:00:00Z",
        sha256(("m50-credit-"+label).encode()).hexdigest(),"CREDIT-MEMO",
    ))


def _mutate(base:Path,case:str,result):
    if type(case) is not str or case not in CASES:
        raise ValueError("M50_UNREGISTERED_REHASHED_BUNDLE_ATTACK")
    audit_base=base/"audit.backup.sqlite3"
    settle_base=base/"settlement.backup.sqlite3"
    audit_restore=base/"audit.restored.sqlite3"
    settle_restore=base/"settlement.restored.sqlite3"
    marker=base/"capture.complete.json"
    if case=="AUDIT_BACKUP_MISSING_IMMUTABLE_TRIGGER":
        _alter_catalog(audit_base,"audit_events_immutable_update")
    elif case=="AUDIT_BACKUP_REHASHED_INVALID_CHAIN":
        _alter_catalog(
            audit_base,"audit_events_immutable_update",
            replacement_sql="ORIGINAL",
            edit_sql="UPDATE audit_events SET object_id='m50-fake-history' "
                     "WHERE sequence=1",
        )
    elif case=="SETTLEMENT_BACKUP_MISSING_CAPACITY_TRIGGER":
        _alter_catalog(settle_base,"allocation_event_capacity")
    elif case=="SETTLEMENT_BACKUP_WRONG_PAYER_WITH_ORIGINAL_DDL":
        _alter_catalog(
            settle_base,"immutable_event_u",replacement_sql="ORIGINAL",
            edit_sql="UPDATE settlement_events SET payer_id='m50-pretend-carrier' "
                     "WHERE event_id='e1'",
        )
    elif case=="AUDIT_BACKUP_LATER_VALID_EVENT":
        _append_audit(audit_base,"audit-backup-later")
    elif case=="AUDIT_RESTORE_LATER_VALID_EVENT":
        _append_audit(audit_restore,"audit-restore-later")
    elif case=="SETTLEMENT_BACKUP_LATER_VALID_CREDIT":
        _append_settlement(settle_base,"settlement-backup-later")
    elif case=="SETTLEMENT_RESTORE_LATER_VALID_CREDIT":
        _append_settlement(settle_restore,"settlement-restore-later")
    elif case=="MANIFEST_SOURCE_SEMANTIC_FIELD_CHANGED":
        contents=json.loads(marker.read_text())
        contents["source_semantic_hash"]="f"*64
        marker.write_text(json.dumps(contents))
    elif case=="MANIFEST_FAKE_HUMAN_APPROVAL":
        contents=json.loads(marker.read_text())
        contents["real_pilot_human_approvals_established"]=True
        marker.write_text(json.dumps(contents))
    elif case=="MANIFEST_FAKE_ORIGINAL_LOGICAL_DIGEST":
        contents=json.loads(marker.read_text())
        contents["full_file_logical_source_hashes"]["audit"]="b"*64
        marker.write_text(json.dumps(contents))
    elif case=="LOCAL_REPORT_WRONG_TENANT_SCOPE":
        result=replace(result,buyer_id="M50-FORGED-OTHER-BUYER")
    elif case=="COMPLETION_MARKER_REPLACED_WITH_SYMLINK":
        alt=base.parent/"m50-marker-symlink-target.json"
        alt.write_bytes(marker.read_bytes())
        marker.unlink()
        marker.symlink_to(alt)
    return result


def _rebind_local_unkeyed_receipts(base:Path,result):
    """Emulate a rogue local operator rehashing *every* mutable M49 field.

    A hash-repaired local receipt is not authority from a separate signer.
    """
    updates={field:backup._file_hash(base/name) for name,field in FILES.items()}
    result=replace(result,**updates)
    original={"schema":1,**{
        k:v for k,v in asdict(result).items() if k!="proof_hash"
    }}
    result=replace(result,proof_hash=canonical_hash(original))
    marker=base/"capture.complete.json"
    record=json.loads(marker.read_text())
    for name in (
        "source_semantic_hash","restored_semantic_hash",
        "audit_backup_sha256","settlement_backup_sha256",
        "audit_restore_sha256","settlement_restore_sha256","proof_hash",
    ):
        # Normally rebind hashes and M49 proof, EXCEPT malicious manifest
        # divergence, whose original self-rehashed *marker* is intentional.
        if (name=="source_semantic_hash"
            and record["source_semantic_hash"]!=result.source_semantic_hash):
            continue
        record[name]=getattr(result,name)
    record["manifest_sha256"]=canonical_hash({
        k:v for k,v in record.items() if k!="manifest_sha256"
    })
    marker.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
    return result


def _predecessor_receipt_would_pass(base:Path,result)->bool:
    """Minimal, narrow, stable M49 checks; independent pinned-CI compares code."""
    backup.verify_backup_restore_result(result)
    record=json.loads((base/"capture.complete.json").read_text())
    if (record["manifest_sha256"]!=canonical_hash({
        k:v for k,v in record.items() if k!="manifest_sha256"
    })
        or record["scope"]!="M49_SCOPED_TWO_SQLITE_STABLE_WINDOW_NOT_ATOMIC_CROSS_FILE"
        or record["proof_hash"]!=result.proof_hash
        or record["original_26_historical_findings_closed"]!=0
        or record["real_customer_bank_or_carrier_source_verified"] is not False
        or record["separate_two_file_atomic_database_commit_established"] is not False):
        return False
    return all(backup._file_hash(base/name)==getattr(result,field)
               for name,field in FILES.items())


def replay_one(case:str)->dict:
    if type(case) is not str or case not in CASES:
        raise ValueError("M50_UNKNOWN_RECOVERY_ADMISSION_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m50-published-local-") as td:
        home=Path(td)
        audit,settlement=populated(home)
        base=home/"bundle"
        original=backup.run_backup_restore_drill(
            audit,settlement,work_dir=base
        )
        known_good=backup.verify_backup_bundle(base,original)
        if known_good["source_semantic_hash"]!=original.source_semantic_hash:
            raise ValueError("M50_KNOWN_GOOD_BUNDLE_BROKEN")
        altered=_mutate(base,case,original)
        rebound=_rebind_local_unkeyed_receipts(base,altered)
        if not _predecessor_receipt_would_pass(base,rebound):
            raise ValueError("M50_NEGATIVE_PROBE_DID_NOT_REHASH_OLD_RECEIPT")
        before={name:backup._file_hash(base/name) for name in FILES}
        try:
            backup.verify_backup_bundle(base,rebound)
        except ValueError as exc:
            if CASES[case] not in str(exc):
                raise ValueError(
                    "M50_WRONG_RESTORE_ADMISSION_REJECTION:"+case+":"+str(exc)
                ) from exc
        else:
            raise ValueError("M50_REHASHED_FALSE_BACKUP_BECAME_ACCEPTED:"+case)
        after={name:backup._file_hash(base/name) for name in FILES}
        if after!=before:
            raise ValueError("M50_VERIFICATION_MUTATED_SOURCE_DB_OR_RECEIPT")
        return {
            "case":case,
            "expected_current_exact_denial":CASES[case],
            "original_good_bundle_accepted":True,
            "mutated_local_receipts_rehashed_to_look_complete":True,
            "predecessor_length_and_sha_only_gate_would_accept":True,
            "current_read_only_restoration_admission_denied":True,
            "all_four_sqlite_file_bytes_preserved_during_rejection":True,
            "original_historical_defect_closed":False,
            "real_customer_or_bank_signature_reproduced":False,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M50_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(case) for case in CASES]
    if len(cases)!=13 or any(
        x["expected_current_exact_denial"]!=CASES[x["case"]]
        or x["current_read_only_restoration_admission_denied"] is not True
        or x["original_historical_defect_closed"] is not False
        for x in cases
    ):
        raise ValueError("M50_CORRUPTED_RECOVERY_BUNDLE_ACCEPTANCE_NOT_PROVEN")
    report={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_original_labs":14,
        "new_lab_created":False,
        "valid_original_fictional_recovery_bundles":13,
        "rehash_repaired_negative_bundle_attacks":13,
        "current_exact_fail_closed_recovery_denials":13,
        "full_tenant_audit_and_settlement_semantics_checked":True,
        "published_backup_and_restore_generations_reconciled":True,
        "hash_and_schema_checks_executed_read_only":True,
        "original_two_file_shared_atomic_commit_proven":False,
        "external_immutable_or_crypto_signed_backup_proven":False,
        "historical_original_recoveryos_findings_open":26,
        "historical_original_recoveryos_findings_closed":0,
        "first_customer_independent_human_approval_gates_unmet":18,
        "real_customer_cash_recovered":None,
        "externally_publishable_empirical_claims_approved":0,
        "live_customer_or_carrier_access_used":False,
        "no_production_merge_deploy_or_new_schedules":True,
        "cases":cases,
        "caveat":(
            "M50 prevents current verifier acceptance of 13 deliberately "
            "modified real test-only SQLite recovery bundles even when "
            "their unkeyed local SHA receipts are recomputed. This does "
            "not make a trust anchor or authenticate the independently "
            "correct historical bank/carrier event data: an adversary able "
            "to rewrite every local file and receipt coherently can still "
            "create a false but consistent chain. The two SQLite files "
            "remain independently versioned; no shared ACID snapshot or "
            "production-scale recovery throughput was established. All "
            "26 historical findings and 18 human approval gates stay open."
        ),
    }
    report["receipt_sha256"]=digest(report)
    return report


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(c["case"])+"</th><td>"
        +escape(c["expected_current_exact_denial"])+"</td>"
        "<td>BLOCKED AFTER LOCAL REHASH</td></tr>"
        for c in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | M50 Read-Only Recovery Admission</title>'
        '<style>body{font:15px/1.6 system-ui;color:#1b3c2c;'
        'background:#f5f8f5;max-width:1100px;margin:auto;padding:25px}'
        'table{border-collapse:collapse;background:white;width:100%}'
        'th,td{text-align:left;border-bottom:1px solid #dbe7dc;padding:10px}'
        'small{color:#68766c}</style></head><body>'
        '<small>RETALLY / LAB 14 / M50 / SYNTHETIC INTERNAL ONLY</small>'
        '<h1>Rehashed local backup is not sufficient recovery proof</h1>'
        '<p>13 matching local receipts were generated from altered real '
        'SQLite files; all 13 were rejected by the independent read-only '
        'all-tenant chain, policy and restore-generation verifier. '
        'Original 26 findings remain open; 18 separate human first-'
        'customer authorizations are still unmet.</p><table>'
        '<thead><tr><th>Attack</th><th>Exact denial</th><th>Status</th>'
        '</tr></thead><tbody>'+rows+'</tbody></table><p><small>'
        +escape(report["caveat"])+'</small></p></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Offline synthetic recovery admission")
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"recovery_admission_m50.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.out/"recovery_admission_m50.html").write_text(
        render_html(result),encoding="utf-8")
    print(json.dumps({
        "rehashed_false_bundles_rejected":13,
        "original_defects_closed":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
