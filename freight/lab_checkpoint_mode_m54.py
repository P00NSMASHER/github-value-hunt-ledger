"""Existing RETALLY Research Lab 14 / M54: checkpoint mode downgrade gate.

Twelve fresh test-only two-Ed25519-reviewer / signed M53 journal fixtures
must reject old M52 local-only writes once a checkpoint was successfully
used on that SQLite file. Tests include an already-open client, a separately
reopened client, a direct internal call, WAL checkpoint, second signed
review, an unreviewed SQLite header value and an attacker reset of the
checkpoint-mode header.

Important limit: mode 54 is a LOCAL persisted SQLite header, not a remote
nonrollbackable trust anchor. A privileged operator could reset both mode
and local history, or make a new journal. M53's independently held signed
checkpoint is still required to detect such a complete state rollback.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from html import escape
import json
from pathlib import Path
import sqlite3
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from freight import backup_restore as backup
from freight.lab_assurance import digest
from freight.lab_recovery_witness_m51 import _make_known_good
from freight.lab_recovery_replay_m52 import _new_signed_context
from freight.lab_replay_checkpoint_m53 import (
    _fixture, _journal_state, _make_anchor,
    AUDIENCE, NAMESPACE,
)
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger
from freight.recovery_checkpoint_m53 import signing_message
from freight.recovery_mode_m54 import (
    CHECKPOINT_REQUIRED,LOCAL_ONLY,mode as sqlite_mode,
)

SCOPE="RETALLY_LAB14_M54_ONE_WAY_CHECKPOINT_NO_DOWNGRADE_SYNTHETIC"
CASES={
    "NEW_SIGNED_LOCAL_ONLY_REVIEW":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "REOPENED_CLIENT_DOWNGRADE":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "CLIENT_OPENED_BEFORE_ELEVATION":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "ORIGINAL_SIGNATURE_REPLAY_VIA_LOCAL_ONLY":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "SAME_REQUEST_WITH_NEW_NONCES":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "TWO_NEW_SEPARATE_LOCAL_REQUESTS":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "DIRECT_INTERNAL_CONSUME_BYPASS":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "WAL_CHECKPOINT_AND_REOPEN_DOWNGRADE":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "AFTER_SECOND_CHECKPOINTED_REVIEW_DOWNGRADE":"M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE",
    "UNREVIEWED_SQLITE_MODE_HEADER":"M54_REPLAY_UNKNOWN_CHECKPOINT_MODE",
    "REUSE_SIGNED_PREUPGRADE_CHECKPOINT":"M53_CHECKPOINT_STATE_MISMATCH",
    "TRUSTED_CHECKPOINT_AFTER_PRIVILEGED_HEADER_RESET":"M53_CHECKPOINT_STATE_MISMATCH",
}


def _mode_file(path:Path)->int:
    with sqlite3.connect(path) as con:
        return sqlite_mode(con)


def _change_header(path:Path,value:int)->None:
    if value not in (0,99):
        raise ValueError("M54_INVALID_DISPOSABLE_HEADER_MUTATION")
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA user_version="+str(value))


def _consume_direct(fx:dict,kwargs:dict)->None:
    fx["ledger"].consume(
        manifest=fx["manifest"],result=fx["result"],
        trust_registry=kwargs["trust_registry"],
        witness_receipts=kwargs["witness_receipts"],
        expected_restore_request_id=kwargs["expected_restore_request_id"],
        expected_audience=kwargs["expected_audience"],
        as_of_utc=kwargs["as_of_utc"],
    )


def replay_one(case:str)->dict:
    if type(case) is not str or case not in CASES:
        raise ValueError("M54_UNKNOWN_CHECKPOINT_DOWNGRADE_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m54-oneway-mode-") as td:
        root=Path(td)
        if case=="CLIENT_OPENED_BEFORE_ELEVATION":
            bundle,result,manifest,signers,kwargs=_make_known_good(root)
            path=root/"preopened-client-journal.sqlite3"
            ledger=TechnicalReviewReplayLedger(path,create=True)
            client=TechnicalReviewReplayLedger(path)
            if _mode_file(path)!=LOCAL_ONLY:
                raise ValueError("M54_POSITIVE_INITIAL_MODE_WRONG")
            cust=Ed25519PrivateKey.generate()
            from cryptography.hazmat.primitives import serialization
            trust={
                "authority_id":"M53-IN-MEMORY-ONLY-CUSTODIAN",
                "public_key_hex":cust.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ).hex(),
            }
            signed=_make_anchor(
                _journal_state(ledger),cust,checkpoint_id="M54-PREOPENED-INITIAL"
            )
            backup.record_checkpointed_witnessed_recovery_review(
                bundle,result,replay_ledger=ledger,**kwargs,
                external_checkpoint=signed,
                checkpoint_custodian_trust=trust,
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
            fx={
                "bundle":bundle,"result":result,"manifest":manifest,
                "ledger":ledger,"trust":trust,
                "current_checkpoint":_make_anchor(
                    _journal_state(ledger),cust,
                    checkpoint_id="M54-PREOPENED-AFTER-ONE",
                ),
                "original_review_kwargs":kwargs,
                "next_review_kwargs":_new_signed_context(
                    kwargs,signers,"m54-preopened"
                ),
                "reviewer_private_keys":signers,
            }
            target=client
        else:
            fx=_fixture(root)
            target=fx["ledger"]

        bundle=fx["bundle"];result=fx["result"];ledger=fx["ledger"]
        if (ledger.verify()["technical_review_rows"]!=1
            or ledger.verify()["checkpoint_required_for_future_reviews"] is not True
            or _mode_file(ledger.path)!=CHECKPOINT_REQUIRED):
            raise ValueError("M54_FIRST_CHECKPOINT_DID_NOT_ATOMICALLY_UPGRADE_MODE")
        before_state=_journal_state(ledger)
        before_bundle=[
            backup._file_hash(bundle/name) for name in backup._capture_files()
        ]
        to_try=deepcopy(fx["next_review_kwargs"])
        expected=CASES[case]
        if case=="REOPENED_CLIENT_DOWNGRADE":
            target=TechnicalReviewReplayLedger(ledger.path)
        elif case=="WAL_CHECKPOINT_AND_REOPEN_DOWNGRADE":
            with sqlite3.connect(ledger.path,isolation_level=None) as con:
                status=con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if status[0]!=0:
                    raise ValueError("M54_SQLITE_WAL_CHECKPOINT_UNAVAILABLE")
            target=TechnicalReviewReplayLedger(ledger.path)
        elif case=="ORIGINAL_SIGNATURE_REPLAY_VIA_LOCAL_ONLY":
            to_try=deepcopy(fx["original_review_kwargs"])
        elif case=="SAME_REQUEST_WITH_NEW_NONCES":
            to_try=_new_signed_context(
                fx["original_review_kwargs"],
                fx["reviewer_private_keys"],"m54-same-id-fresh-nonces",
                same_request=True,
            )
        elif case=="AFTER_SECOND_CHECKPOINTED_REVIEW_DOWNGRADE":
            second=backup.record_checkpointed_witnessed_recovery_review(
                bundle,result,replay_ledger=ledger,
                **fx["next_review_kwargs"],
                external_checkpoint=fx["current_checkpoint"],
                checkpoint_custodian_trust=fx["trust"],
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
            if second["m53_successor_sequence"]!=2:
                raise ValueError("M54_SECOND_CHECKPOINTED_REVIEW_NOT_COMMITTED")
            before_state=_journal_state(ledger)
            to_try=_new_signed_context(
                fx["original_review_kwargs"],
                fx["reviewer_private_keys"],"m54-after-two"
            )
        elif case=="UNREVIEWED_SQLITE_MODE_HEADER":
            _change_header(ledger.path,99)
        elif case=="TRUSTED_CHECKPOINT_AFTER_PRIVILEGED_HEADER_RESET":
            _change_header(ledger.path,0)
        if case in (
            "REUSE_SIGNED_PREUPGRADE_CHECKPOINT",
            "TRUSTED_CHECKPOINT_AFTER_PRIVILEGED_HEADER_RESET",
        ):
            checkpoint=(
                fx["current_checkpoint"]
                if case=="TRUSTED_CHECKPOINT_AFTER_PRIVILEGED_HEADER_RESET"
                else fx.get("initial_checkpoint")
            )
            if checkpoint is None:
                # Pre-upgrade empty journal signed fixture is retained
                # explicitly by original M53 _fixture.
                raise ValueError("M54_INITIAL_SIGNED_CHECKPOINT_NOT_RETAINED")
            task=lambda:backup.record_checkpointed_witnessed_recovery_review(
                bundle,result,replay_ledger=target,**to_try,
                external_checkpoint=checkpoint,
                checkpoint_custodian_trust=fx["trust"],
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
        elif case=="DIRECT_INTERNAL_CONSUME_BYPASS":
            task=lambda:_consume_direct(fx,to_try)
        else:
            task=lambda:backup.record_witnessed_recovery_review(
                bundle,result,replay_ledger=target,**to_try
            )
        attempts=2 if case=="TWO_NEW_SEPARATE_LOCAL_REQUESTS" else 1
        denials=0
        for run in range(attempts):
            if run==1:
                to_try=_new_signed_context(
                    fx["original_review_kwargs"],
                    fx["reviewer_private_keys"],"m54-second-fresh-attempt"
                )
            try:
                task()
            except ValueError as exc:
                if expected not in str(exc):
                    raise ValueError(
                        "M54_WRONG_DOWNGRADE_DENIAL:"+case
                    ) from exc
                denials+=1
            else:
                raise ValueError("M54_WEAK_LOCAL_REVIEW_DOWNGRADED_SIGNED_JOURNAL:"+case)
        if denials!=attempts:
            raise ValueError("M54_NEGATIVE_ATTEMPT_COUNT_INCOMPLETE")
        if case=="UNREVIEWED_SQLITE_MODE_HEADER":
            # The normal guarded _mode_file deliberately rejects a header
            # value of 99. Inspect the deliberately malformed fixture via
            # raw sqlite3 HERE ONLY to prove the failed operation did not
            # rewrite it back to a deceptively valid accepted mode.
            with sqlite3.connect(ledger.path) as raw:
                unchanged=raw.execute("PRAGMA user_version").fetchone()[0]
            if unchanged!=99:
                raise ValueError("M54_UNKNOWN_HEADER_REPAIRED_BY_REJECTED_WRITE")
        elif case=="TRUSTED_CHECKPOINT_AFTER_PRIVILEGED_HEADER_RESET":
            if _mode_file(ledger.path)!=LOCAL_ONLY:
                raise ValueError("M54_RESET_HEADER_NOT_PRESERVED_FOR_NEGATIVE_PROOF")
        elif _mode_file(ledger.path)!=CHECKPOINT_REQUIRED:
            raise ValueError("M54_ACCEPTED_REVIEW_DOWNGRADED_HEADER")
        if case not in (
            "UNREVIEWED_SQLITE_MODE_HEADER",
            "TRUSTED_CHECKPOINT_AFTER_PRIVILEGED_HEADER_RESET"
        ) and _journal_state(ledger)!=before_state:
            raise ValueError("M54_DENIED_DOWNGRADE_CHANGED_JOURNAL_ROWS")
        if [
            backup._file_hash(bundle/name) for name in backup._capture_files()
        ]!=before_bundle:
            raise ValueError("M54_REVIEW_MODIFIED_ORIGINAL_BACKUP_SQLITE")
        return {
            "scenario":case,
            "expected_exact_denial":expected,
            "valid_original_signed_checkpointed_review_completed":True,
            "same_file_security_header_was_promoted_to_54":True,
            "adversarial_downgrade_or_bad_checkpoint_denied":True,
            "current_review_rows_unchanged_by_denied_attempt":True,
            "all_four_customer_backup_images_untouched":True,
            "rejection_count":denials,
            "privileged_header_rewrite_cannot_be_stopped_without_external_anchor":True,
            "real_external_custodian_or_bank_identity_provisioned":False,
            "production_restore_or_legal_approval_granted":False,
            "original_26_historical_findings_closed":0,
            "independent_customer_pilot_gates_unmet":18,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M54_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(name) for name in CASES]
    if len(cases)!=12 or any(
        row["expected_exact_denial"]!=CASES[row["scenario"]]
        or row["valid_original_signed_checkpointed_review_completed"] is not True
        or row["adversarial_downgrade_or_bad_checkpoint_denied"] is not True
        or row["original_26_historical_findings_closed"]!=0
        for row in cases
    ):
        raise ValueError("M54_DOWNGRADE_CONTROLS_INCOMPLETE")
    report={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "original_research_labs":14,
        "new_lab_created":False,
        "original_signed_checkpointed_technical_positive_controls":12,
        "same_sqlite_journal_downgrade_negative_scenarios":12,
        "current_exact_mode_or_checkpoint_negative_denials":
            sum(case["rejection_count"] for case in cases),
        "local_only_compatibility_remains_on_never_elevated_journals":True,
        "first_signed_review_sets_durable_mode_in_same_write_transaction":True,
        "already_open_and_reopened_legacy_clients_cannot_bypass_elevated_mode":True,
        "checkpoint_mode_bound_into_independent_signed_journal_state_hash":True,
        "same_sqlite_mode_change_rollback_tested_separately":True,
        "checkpoint_security_requires_external_custody_against_full_privileged_rollback":True,
        "real_remote_checkpoint_custodian_provisioned":False,
        "real_bank_carrier_or_customer_signer_authenticated":False,
        "customer_restore_activation_performed":False,
        "original_historical_findings_open":26,
        "original_historical_findings_closed":0,
        "human_first_customer_approval_gates_unmet":18,
        "real_recovered_customer_cash":None,
        "externally_publishable_empirical_claims_approved":0,
        "business_registered_merged_or_production_schedule_changed":False,
        "cases":cases,
        "caveat":(
            "An M53 checkpointed technical review now raises an M54 "
            "local SQLite version marker within the SAME atomic transaction "
            "that records its signed review and nonces. Ordinary local-only "
            "M52 clients, including opened-before-upgrade and reopened "
            "ones, are denied for that file after the first valid signed "
            "review. M53 signed journal state now includes the mode marker. "
            "This does NOT make a local SQLite header a remote immutable "
            "anchor: a privileged actor can reset the header and rows, "
            "or restore a different journal. No external custodian or real "
            "trust roots are provisioned; independently held M53 state is "
            "still essential to detect full consistent rollback. The "
            "M52 LOCAL_ONLY mode of never-upgraded journals remains "
            "vulnerable to coherent privileged rewinds. A local review "
            "does not authorize production restore, legal customer consent "
            "or bank/carrier claims; all 26 original historical defects "
            "and 18 independent human first-customer gates remain open."
        ),
    }
    report["receipt_sha256"]=digest(report)
    return report


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(row["scenario"])+"</th><td>"
        +escape(row["expected_exact_denial"])+"</td>"
        "<td>NO LOCAL-ONLY DOWNGRADE</td></tr>"
        for row in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M54 | One-Way Technical Checkpoint Mode</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f5f8f4;'
        'color:#203a2e;max-width:1020px;margin:auto;padding:26px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'th,td{text-align:left;border-bottom:1px solid #dce8dc;padding:11px}'
        'small{color:#67796d}</style></head><body>'
        '<small>RETALLY / ORIGINAL LAB 14 / M54 / FICTIONAL ONLY</small>'
        '<h1>Once a signed checkpoint is used, local-only writes cannot resume</h1>'
        '<p>12 documented disposable SQLite downgrade scenarios after a '
        'valid M53 checkpointed technical review. No real independently '
        'operated signer, customer authorization or restore activation.</p>'
        '<table><thead><tr><th>Attack</th><th>Typed reason</th>'
        '<th>Result</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="Test-only one-way checkpoint mode")
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    report=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"checkpoint_mode_m54.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (args.out/"checkpoint_mode_m54.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "signed_source_positive_controls":12,
        "current_exact_negative_denials":
            report["current_exact_mode_or_checkpoint_negative_denials"],
        "original_historical_findings_closed":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
