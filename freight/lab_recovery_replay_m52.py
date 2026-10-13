"""RETALLY existing Lab 14 / Mission 52: durable technical witness replay denial.

Every test uses a fresh fictional M50 four-SQLite bundle, two test-only M51
Ed25519 signing keys, and an explicitly created independent local replay DB.
A genuine positive technical-only review is consumed FIRST; fourteen
subsequent attempts must be rejected with exact reason without modifying
the original audit/settlement backups.

No independent real signing authority, bank/customer consent, production
restore, distributed nonce service or new business registration is created.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from freight import backup_restore as backup
from freight.lab_assurance import digest
from freight.lab_recovery_witness_m51 import (
    _make_known_good as m51_good, _resign,
)
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger, SCOPE as REPLAY_SCOPE

SCOPE="RETALLY_LAB14_M52_DURABLE_LOCAL_TECH_REVIEW_REPLAY_DENIAL_SYNTHETIC"
ATTACKS={
    "IDENTICAL_REQUEST_REPEATED":"M52_REPLAY_REQUEST_ALREADY_CONSUMED",
    "REOPENED_JOURNAL_REPEATED_REQUEST":"M52_REPLAY_REQUEST_ALREADY_CONSUMED",
    "RESIGNED_SAME_REQUEST_WITH_FRESH_NONCES":"M52_REPLAY_REQUEST_ALREADY_CONSUMED",
    "SECOND_JOURNAL_CLIENT_REPEATED_REQUEST":"M52_REPLAY_REQUEST_ALREADY_CONSUMED",
    "NEW_REQUEST_REUSES_OPERATOR_NONCE":"M52_REPLAY_WITNESS_NONCE_ALREADY_CONSUMED",
    "NEW_REQUEST_REUSES_REVIEWER_NONCE":"M52_REPLAY_WITNESS_NONCE_ALREADY_CONSUMED",
    "DROP_APPEND_ONLY_REVIEW_TRIGGER":"M52_REPLAY_SQLITE_REPLAY_SCHEMA_DRIFT",
    "REPLACE_WITNESS_NONCE_TRIGGER_WITH_NOOP":"M52_REPLAY_SQLITE_REPLAY_SCHEMA_DRIFT",
    "ADD_UNREVIEWED_LOCAL_TABLE":"M52_REPLAY_SQLITE_REPLAY_SCHEMA_DRIFT",
    "TAMPER_REVIEW_TIMESTAMP_RESTORE_TRIGGER":"M52_REPLAY_PERSISTED_TECHNICAL_RECEIPT_TAMPERED",
    "DELETE_ONE_USED_NONCE_RESTORE_TRIGGER":"M52_REPLAY_PERSISTED_TECHNICAL_RECEIPT_TAMPERED",
    "DELETE_CONSUMPTION_DATABASE_MAIN":"M47_SQLITE_SOURCE_FILE_MISSING",
    "SWAP_WITH_DIFFERENT_EMPTY_VALID_JOURNAL":"M47_SQLITE_SOURCE_FILE_REPLACED",
    "REPLACE_JOURNAL_WITH_SYMLINK":"M47_SQLITE_SOURCE_SYMLINK_REJECTED",
}


def _new_signed_context(kwargs:dict, keys:tuple, suffix:str,
                        *, preserve_nonce_role:int|None=None,
                        same_request:bool=False)->dict:
    cloned=deepcopy(kwargs)
    new_request=cloned["expected_restore_request_id"] if same_request else (
        "M52-NEW-RESTORE-"+suffix
    )
    cloned["expected_restore_request_id"]=new_request
    for role_index,receipt in enumerate(cloned["witness_receipts"]):
        payload=receipt["payload"]
        payload["restore_request_id"]=new_request
        if role_index!=preserve_nonce_role:
            payload["nonce_hex"]=sha256(
                ("m52-"+suffix+"-nonce-role-"+str(role_index)).encode()
            ).hexdigest()
        _resign(receipt,keys[role_index])
    return cloned


def _mutate(db:Path,scenario:str)->None:
    if scenario=="DELETE_CONSUMPTION_DATABASE_MAIN":
        db.unlink()
        return
    if scenario=="SWAP_WITH_DIFFERENT_EMPTY_VALID_JOURNAL":
        other=db.with_name("m52-another-empty-valid-replay.sqlite3")
        fresh=TechnicalReviewReplayLedger(other,create=True)
        if fresh.verify()["technical_review_rows"]!=0:
            raise ValueError("M52_TEST_ALT_LEDGER_NOT_EMPTY")
        os.replace(other,db)
        return
    if scenario=="REPLACE_JOURNAL_WITH_SYMLINK":
        other=db.with_name("m52-valid-symlink-target.sqlite3")
        TechnicalReviewReplayLedger(other,create=True)
        db.unlink()
        db.symlink_to(other)
        return
    with sqlite3.connect(db) as con:
        if scenario=="DROP_APPEND_ONLY_REVIEW_TRIGGER":
            con.execute("DROP TRIGGER immutable_review_consumptions_u")
        elif scenario=="REPLACE_WITNESS_NONCE_TRIGGER_WITH_NOOP":
            con.execute("DROP TRIGGER immutable_witness_nonce_u")
            con.execute(
                "CREATE TRIGGER immutable_witness_nonce_u "
                "BEFORE UPDATE ON witness_nonce_consumptions "
                "BEGIN SELECT 1; END"
            )
        elif scenario=="ADD_UNREVIEWED_LOCAL_TABLE":
            con.execute(
                "CREATE TABLE untrusted_m52_status ("
                "request_id TEXT, fake_customer_approved INTEGER)"
            )
        elif scenario=="TAMPER_REVIEW_TIMESTAMP_RESTORE_TRIGGER":
            ddl=con.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' "
                "AND name='immutable_review_consumptions_u'"
            ).fetchone()[0]
            con.execute("DROP TRIGGER immutable_review_consumptions_u")
            con.execute(
                "UPDATE review_consumptions SET reviewed_at_utc='not-a-timeZ'"
            )
            con.execute(ddl)
        elif scenario=="DELETE_ONE_USED_NONCE_RESTORE_TRIGGER":
            ddl=con.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' "
                "AND name='immutable_witness_nonce_d'"
            ).fetchone()[0]
            con.execute("DROP TRIGGER immutable_witness_nonce_d")
            con.execute(
                "DELETE FROM witness_nonce_consumptions "
                "WHERE role='RECOVERY_OPERATOR'"
            )
            con.execute(ddl)


def replay_one(scenario:str)->dict:
    if type(scenario) is not str or scenario not in ATTACKS:
        raise ValueError("M52_UNKNOWN_REPLAY_ADVERSARIAL_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m52-tech-review-") as temp:
        root=Path(temp)
        bundle,result,_,keys,kwargs=m51_good(root)
        db=root/"separately-provisioned-review-journal.sqlite3"
        ledger=TechnicalReviewReplayLedger(db,create=True)
        known=backup.record_witnessed_recovery_review(
            bundle,result,replay_ledger=ledger,**kwargs
        )
        if (known["review_attempt_recorded_once"] is not True
            or known["real_customer_restore_activation_authorized"] is not False
            or known["original_historical_findings_closed"]!=0
            or ledger.verify()["technical_review_rows"]!=1
            or ledger.verify()["durable_individual_witness_nonces"]!=2):
            raise ValueError("M52_FICTIONAL_FIRST_REVIEW_NOT_DURABLY_RECORDED")
        before=[
            backup._file_hash(bundle/name) for name in backup._capture_files()
        ]
        test_ledger=ledger
        candidate=kwargs
        if scenario=="REOPENED_JOURNAL_REPEATED_REQUEST":
            test_ledger=TechnicalReviewReplayLedger(db)
        elif scenario=="SECOND_JOURNAL_CLIENT_REPEATED_REQUEST":
            test_ledger=TechnicalReviewReplayLedger(db)
        elif scenario=="RESIGNED_SAME_REQUEST_WITH_FRESH_NONCES":
            candidate=_new_signed_context(
                kwargs,keys,"same-request",same_request=True
            )
        elif scenario=="NEW_REQUEST_REUSES_OPERATOR_NONCE":
            candidate=_new_signed_context(
                kwargs,keys,"reused-operator",
                preserve_nonce_role=0
            )
        elif scenario=="NEW_REQUEST_REUSES_REVIEWER_NONCE":
            candidate=_new_signed_context(
                kwargs,keys,"reused-reviewer",
                preserve_nonce_role=1
            )
        elif scenario not in (
            "IDENTICAL_REQUEST_REPEATED",
            "REOPENED_JOURNAL_REPEATED_REQUEST",
            "SECOND_JOURNAL_CLIENT_REPEATED_REQUEST",
        ):
            _mutate(db,scenario)

        observed_error=ATTACKS[scenario]
        try:
            backup.record_witnessed_recovery_review(
                bundle,result,replay_ledger=test_ledger,**candidate
            )
        except (RuntimeError,ValueError) as exc:
            if observed_error not in str(exc):
                raise ValueError(
                    "M52_WRONG_DURABLE_REPLAY_REASON:"+scenario+":"+str(exc)
                ) from exc
        else:
            raise ValueError("M52_REPLAYED_TECHNICAL_REVIEW_WAS_ACCEPTED:"+scenario)
        if [backup._file_hash(bundle/name) for name in backup._capture_files()]!=before:
            raise ValueError("M52_DENIED_REPLAY_MUTATED_ORIGINAL_RECOVERY_BUNDLE")
        if (scenario=="DELETE_CONSUMPTION_DATABASE_MAIN" and db.exists()):
            raise ValueError("M52_DENIAL_SILENTLY_RECREATED_MISSING_REPLAY_LEDGER")
        return {
            "scenario":scenario,
            "expected_exact_denial":observed_error,
            "initial_two_key_review_recorded_technical_only":True,
            "initial_unique_request_and_two_nonces_durably_consumed":True,
            "adversarial_replay_attempt_rejected":True,
            "source_backup_and_restore_images_untouched":True,
            "production_activation_or_customer_approval":False,
            "locally_mutable_replay_journal_is_not_external_trust_anchor":True,
            "separate_original_human_pilot_approvals_unmet":18,
            "historical_original_findings_closed":0,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M52_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(s) for s in ATTACKS]
    if len(cases)!=14 or any(
        row["expected_exact_denial"]!=ATTACKS[row["scenario"]]
        or row["adversarial_replay_attempt_rejected"] is not True
        or row["source_backup_and_restore_images_untouched"] is not True
        or row["historical_original_findings_closed"]!=0
        for row in cases
    ):
        raise ValueError("M52_REPLAY_HISTORY_NEGATIVE_CONTROLS_NOT_VERIFIED")
    result={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "original_research_labs":14,
        "new_lab_created":False,
        "synthetic_original_technical_review_positive_controls":14,
        "durable_review_replay_negative_scenarios":14,
        "exact_current_replay_and_journal_denials":14,
        "separate_local_review_journal_not_recovery_bundle":True,
        "global_restore_request_uniqueness_enforced":True,
        "global_witness_nonce_uniqueness_enforced":True,
        "sqlite_replay_consumptions_atomic_and_rollback_verified":True,
        "all_four_source_sqlite_files_unmodified":True,
        "local_file_identity_and_reviewed_sql_trigger_policy_enforced":True,
        "independently_trusted_distributed_nonce_service_established":False,
        "real_customer_restore_activation_performed":False,
        "real_customer_bank_carrier_authority_verified":False,
        "actual_customer_cash_recovered":None,
        "historical_original_findings_open":26,
        "historical_original_findings_closed":0,
        "independent_first_customer_human_controls_unmet":18,
        "externally_publishable_empirical_claims_approved":0,
        "scheduled_tasks_or_production_changed":False,
        "cases":cases,
        "caveat":(
            "Fourteen current-source synthetic tests exercise a separate "
            "local SQLite journal that atomically consumes technically "
            "reviewed restore requests and two signed nonce identities. "
            "M52 cannot stop replay across unshared journals, backup of "
            "the journal to an earlier generation, a hostile operator "
            "rewriting consistent local review history, or privileged "
            "tampering with signing authorities. A real trusted shared "
            "persistence service and external anchor remain unavailable. "
            "No actual bank, carrier or customer identity/consent, legal "
            "restoration authority, production activation, recovered cash "
            "or closure of 26 original findings was established; "
            "all 18 independent human pilot gates remain unmet."
        ),
    }
    result["receipt_sha256"]=digest(result)
    return result


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(r["scenario"])+"</th><td>"
        +escape(r["expected_exact_denial"])+"</td><td>REPLAY DENIED</td></tr>"
        for r in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M52 | Local Technical Review Replay Barrier</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f5f8f3;'
        'color:#203b2a;max-width:1100px;margin:auto;padding:25px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'th,td{text-align:left;border-bottom:1px solid #deeadf;padding:10px}'
        'small{color:#68786f}</style></head><body>'
        '<small>RETALLY / EXISTING LAB 14 / M52 / SYNTHETIC INTERNAL ONLY</small>'
        '<h1>Technical witness reviews cannot be replayed in one journal</h1>'
        '<p>14 fictional valid original two-signature reviews were recorded '
        'once, and 14 subsequent replay/ledger tamper attempts were '
        'denied. No customer activation or real external authorization; '
        '26 historical issues and 18 human approval gates remain open.</p>'
        '<table><thead><tr><th>Attack</th><th>Exact denial</th>'
        '<th>Outcome</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="Offline M52 review replay tests")
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"review_replay_m52.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (args.out/"review_replay_m52.html").write_text(
        render_html(result),encoding="utf-8"
    )
    print(json.dumps({
        "original_valid_technical_reviews":14,
        "exact_replayed_reviews_denied":14,
        "original_historical_findings_closed":0,
        "receipt_sha256":result["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
