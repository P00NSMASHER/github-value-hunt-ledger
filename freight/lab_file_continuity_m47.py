"""M47: prove current persistent settlement file continuity.

Every case uses a fresh, disposable fictional SQLite database. The already
opened session must refuse missing/renamed/substituted file paths on seven
money/report audit read surfaces and one attempted append. Validity of
replacement SQLite rows alone is NOT continuity with the prior session.
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
import stat
import tempfile

from freight.lab_assurance import digest
from freight.settlement_store import SettlementStore, SettlementEventRecord
from freight.test_lab_phase3_real_chain import funded_store

SCOPE = "RETALLY_LAB14_M47_CURRENT_SESSION_SQLITE_FILE_CONTINUITY_SYNTHETIC_ONLY"
ATTACKS = {
    "DELETE_DATABASE_MAIN_FILE": "M47_SQLITE_SOURCE_FILE_MISSING",
    "RENAME_DATABASE_AWAY": "M47_SQLITE_SOURCE_FILE_MISSING",
    "REPLACE_WITH_EQUIVALENT_VALID_SQLITE": "M47_SQLITE_SOURCE_FILE_REPLACED",
    "REPLACE_WITH_EMPTY_VALID_SQLITE": "M47_SQLITE_SOURCE_FILE_REPLACED",
    "REPLACE_WITH_OTHER_TENANT_VALID_SQLITE": "M47_SQLITE_SOURCE_FILE_REPLACED",
    "REPLACE_WITH_VALID_SQLITE_SYMLINK": "M47_SQLITE_SOURCE_SYMLINK_REJECTED",
    "REPLACE_WITH_DANGLING_SYMLINK": "M47_SQLITE_SOURCE_SYMLINK_REJECTED",
    "REPLACE_FILE_WITH_DIRECTORY": "M47_SQLITE_SOURCE_NOT_REGULAR_FILE",
}
READ_SURFACES = (
    "realized_cents",
    "fee_eligible_cents",
    "claim_residual",
    "event_residual",
    "count",
    "report_snapshot_json",
    "assert_semantic_integrity",
)
GOOD = {
    "realized_cents": 500,
    "fee_eligible_cents": 500,
    "claim_residual": 500,
    "event_residual": 0,
    "count": 2,
}


def _actions(store: SettlementStore) -> dict:
    return {
        "realized_cents": store.realized_cents,
        "fee_eligible_cents": store.fee_eligible_cents,
        "claim_residual": lambda: store.claim_residual("case-1"),
        "event_residual": lambda: store.event_residual("credit-400"),
        "count": lambda: store.count("allocations"),
        "report_snapshot_json": store.report_snapshot_json,
        "assert_semantic_integrity": store.assert_semantic_integrity,
        "attempt_new_credit": lambda: store.ingest_event(
            SettlementEventRecord(
                "m47-unrelated-new-credit", "INV-100",
                "SIM-CARRIER", "SIM-BUYER", "USD", 1,
                "2026-12-20T12:00:00Z",
                sha256(b"m47-disposable-not-real").hexdigest(), "EXTERNAL",
            )
        ),
    }


def _copy_valid(db: Path, alternate: Path) -> None:
    src = sqlite3.connect(db)
    dst = sqlite3.connect(alternate)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()


def _mutate(db: Path, case: str, original_scope: tuple[str, str]) -> None:
    if type(case) is not str or case not in ATTACKS:
        raise ValueError("M47_UNKNOWN_DISPOSABLE_SOURCE_REPLACEMENT")
    other = db.with_name("m47-test-only-other.sqlite3")
    if case == "DELETE_DATABASE_MAIN_FILE":
        db.unlink()
    elif case == "RENAME_DATABASE_AWAY":
        db.rename(db.with_name(db.name+".renamed"))
    elif case == "REPLACE_WITH_EQUIVALENT_VALID_SQLITE":
        _copy_valid(db, other)
        os.replace(other,db)
    elif case == "REPLACE_WITH_EMPTY_VALID_SQLITE":
        SettlementStore(other,buyer_id=original_scope[0],
                        business_unit=original_scope[1])
        os.replace(other, db)
    elif case == "REPLACE_WITH_OTHER_TENANT_VALID_SQLITE":
        SettlementStore(other,buyer_id="M47-DIFFERENT-TENANT",
                        business_unit=original_scope[1])
        os.replace(other,db)
    elif case == "REPLACE_WITH_VALID_SQLITE_SYMLINK":
        _copy_valid(db,other)
        db.unlink()
        db.symlink_to(other)
    elif case == "REPLACE_WITH_DANGLING_SYMLINK":
        db.unlink()
        db.symlink_to(other)
    elif case == "REPLACE_FILE_WITH_DIRECTORY":
        db.unlink()
        db.mkdir()


def _state(path: Path) -> dict:
    if not os.path.lexists(path):
        return {"state": "MAIN_FILE_ABSENT"}
    entry = os.lstat(path)
    if stat.S_ISLNK(entry.st_mode):
        kind = "DIRECT_SYMLINK"
    elif stat.S_ISDIR(entry.st_mode):
        kind = "DIRECTORY"
    elif stat.S_ISREG(entry.st_mode):
        kind = "REGULAR_FILE"
    else:
        kind = "UNSUPPORTED_FILE_TYPE"
    return {"state":kind, "device":entry.st_dev, "inode":entry.st_ino}


def replay_one(case: str) -> dict:
    if type(case) is not str or case not in ATTACKS:
        raise ValueError("M47_UNKNOWN_PERSISTENT_FILE_CONTINUITY_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m47-file-integrity-synthetic-") as td:
        store=funded_store(td)
        path=Path(store.path)
        actions=_actions(store)
        good={key:actions[key]() for key in GOOD}
        if good!=GOOD or len(json.loads(actions["report_snapshot_json"]())["tables"]["recovery_claims"])!=1:
            raise ValueError("M47_ORIGINAL_FICTIONAL_STORE_MONEY_CONTROL_FAILED")
        source_start=_state(path)
        if source_start["state"]!="REGULAR_FILE":
            raise ValueError("M47_ORIGINAL_STORE_PATH_NOT_REGULAR")
        _mutate(path,case,(store.buyer_id,store.business_unit))
        damaged=_state(path)
        if damaged==source_start:
            raise ValueError("M47_DISPOSABLE_FILE_REPLACEMENT_NOT_PROVEN")
        denied=[]
        for operation in (*READ_SURFACES,"attempt_new_credit"):
            try:
                actions[operation]()
            except RuntimeError as exc:
                if ATTACKS[case] not in str(exc):
                    raise ValueError(
                        "M47_WRONG_PATH_IDENTITY_REJECTION:"+case+":"+operation
                    ) from exc
                denied.append(operation)
            else:
                raise ValueError(
                    "M47_ABANDONED_DATABASE_ACCEPTED:"+case+":"+operation
                )
        if _state(path)!=damaged:
            raise ValueError("M47_REJECTED_OPERATION_RECREATED_OR_REPLACED_SOURCE")
        return {
            "source_path_attack":case,
            "exact_expected_denial":ATTACKS[case],
            "original_synthetic_money_controls_passed":5,
            "existing_session_read_denials":7,
            "existing_session_write_denials":1,
            "all_synthetic_operation_ids_denied":denied,
            "database_file_identity_changed":True,
            "rejected_actions_did_not_create_or_replace_file":True,
            "main_file_exists_after_attack":os.path.lexists(path),
            "original_historical_vulnerable_revision_replayed":False,
            "original_historical_finding_closed":False,
            "external_customer_bank_carrier_source_verified":False,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M47_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(case) for case in ATTACKS]
    if len(cases)!=8 or any(
        c["existing_session_read_denials"]!=7
        or c["existing_session_write_denials"]!=1
        or c["rejected_actions_did_not_create_or_replace_file"] is not True
        or c["exact_expected_denial"]!=ATTACKS[c["source_path_attack"]]
        for c in cases
    ):
        raise ValueError("M47_CURRENT_SESSION_FILE_CONTINUITY_NOT_PROVEN")
    body={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_research_lab":14,
        "new_lab_created":False,
        "disposed_current_sqlite_path_attack_cases":8,
        "positive_fictional_money_baseline_checks":40,
        "existing_session_money_and_report_read_denials":56,
        "existing_session_write_denials":8,
        "total_file_path_attacks_blocked_on_current_operations":64,
        "new_instances_may_explicitly_review_valid_replacements":True,
        "orphan_wal_shm_recovery_requires_separate_operator_review":True,
        "file_identity_is_local_device_inode_not_bank_proof":True,
        "all_26_original_findings_still_open":26,
        "original_historical_findings_closed":0,
        "independent_first_customer_human_approval_gates_unmet":18,
        "real_customers_or_payment_accounts_contacted":0,
        "real_recovered_company_cash_cents":None,
        "external_empirical_freight_recovery_claims_allowed":0,
        "no_registration_hosted_deployment_or_schedule_changes":True,
        "cases":cases,
        "caveat":(
            "Eight disposal-only local SQLite file deletion, rename, swap, "
            "symlink and type-substitution scenarios were rejected by an "
            "ALREADY-OPEN store. Device/inode continuity does not prove real "
            "bank or carrier events, prevent same-inode file edits, defeat "
            "kernel-level races, or authenticate an independently trusted "
            "source. Freshly constructed stores may intentionally open "
            "valid replacement files after reviewed recovery. All 26 "
            "historical findings and 18 human pilot approvals remain open."
        ),
    }
    body["receipt_sha256"]=digest(body)
    return body


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(x["source_path_attack"])+"</th><td>"
        +escape(x["exact_expected_denial"])+"</td><td>7 READ / 1 WRITE</td></tr>"
        for x in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY / M47 Current SQLite Database File Continuity</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f5f8f4;'
        'color:#193729;max-width:1060px;margin:auto;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'th,td{text-align:left;border-bottom:1px solid #e0e7df;padding:11px}'
        'small{color:#68786e}</style></head><body>'
        '<small>RETALLY / EXISTING LAB 14 / M47 / INTERNAL SYNTHETIC ONLY</small>'
        '<h1>Original SQLite file path cannot silently change</h1>'
        '<p>8 synthetic source file substitutions denied across 56 reads '
        'and 8 write attempts. 26 historical defects still open; '
        'no real customer funds, bank/carrier receipts or external claims.</p>'
        '<table><thead><tr><th>Disposable attack</th><th>Denial</th>'
        '<th>Current session</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    p=argparse.ArgumentParser(description="Offline M47 database path continuity")
    p.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"sqlite_file_continuity_m47.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"sqlite_file_continuity_m47.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "source_substitution_cases":8,
        "financial_read_denials":56,
        "financial_write_denials":8,
        "original_historical_defects_closed":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
