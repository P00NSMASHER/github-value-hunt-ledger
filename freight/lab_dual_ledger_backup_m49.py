"""RETALLY existing Lab 14 / Mission 49 — fail-closed two-file backup rehearsal.

Attack the actual persistent AuditStore and SettlementStore backup/restore
workflow with synchronized source changes, a concurrent other-tenant writer,
source deletion, partial file publication, and a faulty restore.

All inputs are fictional local SQLite. An all-tenant before/after stable
window is NOT an atomic cross-database snapshot or independently anchored
financial evidence; a sophisticated concurrent writer can evade an entirely
local observational comparison. No original historical issue is closed.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from freight import backup_restore as backup
from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight.lab_assurance import digest
from freight.settlement_store import SettlementStore, SettlementEventRecord
from freight.test_backup_restore import populated

SCOPE = "RETALLY_LAB14_M49_DUAL_SQLITE_BUNDLE_STABLE_WINDOW_SYNTHETIC_ONLY"
SCENARIOS = {
    "AUDIT_APPEND_AFTER_FIRST_COPY": "M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE",
    "SETTLEMENT_APPEND_AFTER_SECOND_COPY": "M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE",
    "OTHER_TENANT_AUDIT_APPEND": "M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE",
    "OTHER_TENANT_SETTLEMENT_APPEND": "M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE",
    "PREEXISTING_ARTIFACT_NO_CLOBBER": "M49_EXISTING_BACKUP_ARTIFACT_MUST_NOT_BE_OVERWRITTEN",
    "FAILED_RESTORE_COPY": "M49_TEST_ONLY_RESTORE_INTERRUPTED",
    "FAILED_THIRD_BUNDLE_PUBLISH": "M49_TEST_ONLY_BUNDLE_PUBLICATION_INTERRUPTED",
    "AUDIT_MAIN_FILE_DELETED": "M47_SQLITE_SOURCE_FILE_MISSING",
    "SETTLEMENT_MAIN_FILE_DELETED": "M47_SQLITE_SOURCE_FILE_MISSING",
}


def _new_event(label: str) -> SettlementEventRecord:
    return SettlementEventRecord(
        "m49-"+label, "INV-1", "carrier", "buyer", "USD", 1,
        "2026-09-26T10:00:00Z",
        sha256(("fictional-m49-"+label).encode()).hexdigest(),
        "CREDIT-MEMO",
    )


def _extra_audit(store: AuditStore, label: str) -> None:
    store.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="m49-"+label,
        occurred_at="2026-09-26T11:00:00Z",
        evidence_hash=sha256(("m49-"+label).encode()).hexdigest(),
    )


def _run_attack(scenario: str, audit: AuditStore,
                settlement: SettlementStore, target: Path) -> None:
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise ValueError("M49_UNKNOWN_RESEARCH_BACKUP_ATTACK")
    raw_backup=backup._sqlite_backup
    raw_restore=backup._restore_copy
    real_link=backup.os.link

    if scenario=="PREEXISTING_ARTIFACT_NO_CLOBBER":
        target.mkdir()
        (target/"audit.backup.sqlite3").write_bytes(b"M49_EXISTING_DO_NOT_OVERWRITE")
        backup.run_backup_restore_drill(audit,settlement,work_dir=target)
        return

    if scenario in ("OTHER_TENANT_AUDIT_APPEND","OTHER_TENANT_SETTLEMENT_APPEND"):
        if scenario=="OTHER_TENANT_AUDIT_APPEND":
            secondary=AuditStore(
                audit.path,buyer_id="SECOND-TEST-TENANT",business_unit="OPS"
            )
            _extra_audit(secondary,"secondary-preexisting")
        else:
            secondary=SettlementStore(
                settlement.path,buyer_id="SECOND-TEST-TENANT",business_unit="OPS"
            )
            # Unallocated original source, but still relevant to a WHOLE-FILE
            # backup; tenant A's scoped settlement totals remain unchanged.
            secondary.ingest_event(_new_event("second-preexisting"))

    if scenario in (
        "AUDIT_APPEND_AFTER_FIRST_COPY",
        "SETTLEMENT_APPEND_AFTER_SECOND_COPY",
        "OTHER_TENANT_AUDIT_APPEND",
        "OTHER_TENANT_SETTLEMENT_APPEND",
        "AUDIT_MAIN_FILE_DELETED",
        "SETTLEMENT_MAIN_FILE_DELETED",
    ):
        injected=[False]
        def competing_copy(source: Path, destination: Path) -> None:
            first=destination.name=="audit.backup.sqlite3"
            second=destination.name=="settlement.backup.sqlite3"
            if scenario=="AUDIT_MAIN_FILE_DELETED" and first and not injected[0]:
                injected[0]=True
                Path(audit.path).unlink()
            if scenario=="SETTLEMENT_MAIN_FILE_DELETED" and second and not injected[0]:
                injected[0]=True
                Path(settlement.path).unlink()
            raw_backup(source,destination)
            if injected[0]:
                return
            if first and scenario=="AUDIT_APPEND_AFTER_FIRST_COPY":
                injected[0]=True
                _extra_audit(audit,"writer-between-file-copies")
            elif second and scenario=="SETTLEMENT_APPEND_AFTER_SECOND_COPY":
                injected[0]=True
                settlement.ingest_event(_new_event("write-after-settle-copy"))
            elif first and scenario=="OTHER_TENANT_AUDIT_APPEND":
                injected[0]=True
                _extra_audit(secondary,"other-tenant-write")
            elif second and scenario=="OTHER_TENANT_SETTLEMENT_APPEND":
                injected[0]=True
                secondary.ingest_event(_new_event("other-tenant-new"))
        with patch.object(backup,"_sqlite_backup",side_effect=competing_copy):
            backup.run_backup_restore_drill(audit,settlement,work_dir=target)
        if not injected[0]:
            raise ValueError("M49_TEST_ONLY_CONCURRENT_ATTACK_DID_NOT_FIRE")
        return

    if scenario=="FAILED_RESTORE_COPY":
        def interrupted_restore(source: Path, destination: Path) -> None:
            if destination.name=="settlement.restored.sqlite3":
                raise RuntimeError("M49_TEST_ONLY_RESTORE_INTERRUPTED")
            return raw_restore(source,destination)
        with patch.object(backup,"_restore_copy",side_effect=interrupted_restore):
            backup.run_backup_restore_drill(audit,settlement,work_dir=target)
        return

    if scenario=="FAILED_THIRD_BUNDLE_PUBLISH":
        calls=[0]
        def interrupted_link(source, destination, *args, **kwargs):
            calls[0]+=1
            if calls[0]==3:
                raise RuntimeError("M49_TEST_ONLY_BUNDLE_PUBLICATION_INTERRUPTED")
            return real_link(source,destination,*args,**kwargs)
        with patch.object(backup.os,"link",side_effect=interrupted_link):
            backup.run_backup_restore_drill(audit,settlement,work_dir=target)
        if calls[0]!=3:
            raise ValueError("M49_TEST_ONLY_THIRD_PUBLICATION_WAS_NOT_ATTEMPTED")
        return

    raise ValueError("M49_NO_SUPPORTED_MUTATION_ROUTER")


def replay_one(scenario: str) -> dict:
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise ValueError("M49_UNKNOWN_DUAL_LEDGER_SOURCE_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m49-two-ledgers-") as tmp:
        root=Path(tmp)
        audit,settlement=populated(root)
        positive_dir=root/"validated-positive"
        good=backup.run_backup_restore_drill(
            audit,settlement,work_dir=positive_dir
        )
        manifest=backup.verify_backup_bundle(positive_dir,good)
        if (good.source_semantic_hash!=good.restored_semantic_hash
            or manifest["source_semantic_hash"]!=good.source_semantic_hash
            or manifest["original_26_historical_findings_closed"]!=0
            or manifest["separate_two_file_atomic_database_commit_established"] is not False):
            raise ValueError("M49_POSITIVE_TWO_FILE_BUNDLE_UNTRUSTWORTHY")
        target=root/"failed-capture"
        expected=SCENARIOS[scenario]
        try:
            _run_attack(scenario,audit,settlement,target)
        except (RuntimeError,ValueError,OSError) as exc:
            if expected not in str(exc):
                raise ValueError(
                    "M49_WRONG_DUAL_LEDGER_NEGATIVE_DENIAL:"+scenario
                ) from exc
        else:
            raise ValueError("M49_UNSAFE_TWO_LEDGER_BACKUP_CLAIMED_SUCCESS:"+scenario)
        # Never accept leftovers as a complete bundle. In particular,
        # a staging or partial-publication exception must not leave files
        # with valid names that a customer could mistake for a verified set.
        complete=target/"capture.complete.json"
        if complete.exists():
            raise ValueError("M49_FAILED_BACKUP_HAS_FALSE_COMPLETION_MARKER")
        if scenario=="PREEXISTING_ARTIFACT_NO_CLOBBER":
            if (target/"audit.backup.sqlite3").read_bytes()!=b"M49_EXISTING_DO_NOT_OVERWRITE":
                raise ValueError("M49_EXISTING_CUSTOMER_ARTIFACT_OVERWRITTEN")
        elif any((target/name).exists() for name in backup._capture_files()):
            raise ValueError("M49_FAILED_DUAL_LEDGER_CAPTURE_LEFT_PARTIAL_FILES")
        return {
            "scenario":scenario,
            "expected_failure":expected,
            "one_known_good_synthetic_backup_and_restore_verified":True,
            "original_full_tenant_baseline_compared":True,
            "negative_current_code_fails_closed":True,
            "no_false_completion_marker_published":True,
            "no_partial_new_sqlite_bundle_published":True,
            "preexisting_user_artifacts_remain_untouched":True,
            "original_historical_bug_replayed":False,
            "original_historical_finding_closed":False,
            "actual_customer_bank_carrier_authority_attested":False,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M49_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(name) for name in SCENARIOS]
    if (len(cases)!=9 or any(
        x["expected_failure"]!=SCENARIOS[x["scenario"]]
        or x["negative_current_code_fails_closed"] is not True
        or x["no_false_completion_marker_published"] is not True
        or x["no_partial_new_sqlite_bundle_published"] is not True
        for x in cases
    )):
        raise ValueError("M49_INCOMPLETE_TWO_LEDGER_CAPTURE_ACCEPTANCE")
    body={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_research_labs":14,
        "new_lab_created":False,
        "disposable_dual_source_attack_scenarios":9,
        "matching_positive_fictional_bundles":9,
        "current_code_exact_negative_denials":9,
        "original_sqlite_sources_single_revision_each":True,
        "all_tenant_source_content_checked_before_and_after_capture":True,
        "completed_bundles_use_commit_marker_last":True,
        "failed_bundles_leave_no_new_final_sqlite_files":True,
        "two_sqlite_files_atomically_committed_together":False,
        "reproducible_real_customer_cash_recovery":None,
        "externally_authenticated_invoice_or_bank_data":False,
        "original_historical_findings_open":26,
        "original_historical_findings_closed":0,
        "first_customer_independent_human_controls_unmet":18,
        "externally_publishable_empirical_claims_approved":0,
        "no_live_deployments_customer_messages_or_schedules":True,
        "cases":cases,
        "caveat":(
            "A bounded before/after stable-window comparison does not make "
            "two separate SQLite files one ACID database. It rejects the "
            "tested concurrent audited writes, other-tenant row changes, "
            "source deletion and interrupted backup publication, but a "
            "malicious actor who can change/revert all bytes, modify the "
            "code or provide false original bank/carrier content is outside "
            "this model. Completion markers and SHA receipts are local "
            "application claims, NOT independently trusted historical "
            "anchors. Original 26 findings and 18 real first-customer "
            "approval gates remain unmet."
        ),
    }
    body["receipt_sha256"]=digest(body)
    return body


def render_html(result:dict)->str:
    rows="".join(
        "<tr><th>"+escape(x["scenario"])+"</th><td>"+
        escape(x["expected_failure"])+"</td>"
        "<td>NO PARTIAL BUNDLE / NO COMPLETION MARKER</td></tr>"
        for x in result["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M49 Cross-File Backup Integrity</title>'
        '<style>body{font:15px/1.6 system-ui;color:#20372d;'
        'background:#f7f9f5;max-width:1100px;margin:auto;padding:25px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'td,th{border-bottom:1px solid #dce8df;padding:11px;text-align:left}'
        'small{color:#65766a}</style></head><body>'
        '<small>RETALLY / LAB 14 / M49 / SYNTHETIC INTERNAL ONLY</small>'
        '<h1>Dual-ledger backup: stale and incomplete evidence denied</h1>'
        '<p>9 valid local backup positives; 9 failed capture/restore '
        'negative cases rejected. This is a stable-window check across '
        'two SQLite files, NOT an atomic distributed snapshot. '
        'All 26 original historical findings remain open.</p>'
        '<table><thead><tr><th>Adversarial capture</th>'
        '<th>Exact denial</th><th>Outcome</th></tr></thead><tbody>'+
        rows+'</tbody></table><p><small>'+escape(result["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Test-only two-ledger backup validation")
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    report=run_campaign(as_of=a.as_of_date)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"dual_ledger_backup_m49.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (a.out/"dual_ledger_backup_m49.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "stable_window_positive_bundles":9,
        "fail_closed_negative_scenarios":9,
        "historical_findings_closed":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
