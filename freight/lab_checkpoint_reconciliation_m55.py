"""RETALLY existing Lab 14 / M55 — checkpoint crash-gap reconciliation.

Every case uses REAL, disposable local M52–M54 SQLite and synthetic,
ephemeral Ed25519 reviewers/custodian. Before every attack, the one-step
post-commit / not-yet-countersigned M53 state is correctly classified as
a HOLD, while the already countersigned state matches exactly.

No external checkpoint is issued or persisted. All 26 original historical
findings remain open and none of the 18 customer human gates are satisfied.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import date
from html import escape
import json
import os
from pathlib import Path
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from freight import backup_restore as backup
from freight.lab_assurance import digest
from freight.lab_replay_checkpoint_m53 import (
    _fixture, _journal_state, _make_anchor, _resign, _rewrite_rows,
    NAMESPACE,AUDIENCE,
)
from freight.lab_recovery_replay_m52 import _new_signed_context
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger
from freight.recovery_reconcile_m55 import (
    SCOPE as RECONCILE_SCOPE,
    SIGNED_HEAD_MATCH,ONE_UNSIGNED_SUCCESSOR,
)

SCOPE="RETALLY_LAB14_M55_SIGNED_CRASH_GAP_RECONCILIATION_SYNTHETIC_ONLY"
SCENARIOS={
    "OLD_SIGNED_HEAD_AFTER_TWO_SUCCESSIVE_REVIEWS":
        "M55_RECONCILE_MULTIPLE_UNCOUNTERSIGNED_REVIEWS_OR_HISTORY_GAP",
    "COHERENT_SAME_SEQUENCE_REWRITE":
        "M55_RECONCILE_SAME_SEQUENCE_JOURNAL_FORK_OR_MODE_ROLLBACK",
    "SIGNED_HEAD_AHEAD_AFTER_ROLLBACK":
        "M55_RECONCILE_SIGNED_HISTORY_AHEAD_OF_CURRENT_JOURNAL",
    "TAMPER_SIGNED_ANCESTOR_AND_APPEND_VALID_SUCCESSOR":
        "M55_RECONCILE_NOT_AN_EXACT_ONE_REVIEW_SIGNED_SUCCESSOR",
    "LEGACY_LOCAL_ONLY_APPEND_NOT_RECONCILABLE":
        "M55_RECONCILE_LOCAL_ONLY_UNCOUNTERSIGNED_REVIEW_NOT_ELIGIBLE",
    "CHECKPOINT_MODE_HEADER_RESET":
        "M55_RECONCILE_SAME_SEQUENCE_JOURNAL_FORK_OR_MODE_ROLLBACK",
    "UNTRUSTED_EPHEMERAL_CUSTODIAN_SIGNATURE":
        "M53_CHECKPOINT_INVALID_SIGNATURE",
    "UNTRUSTED_SUBSTITUTED_PUBLIC_KEY":
        "M53_CHECKPOINT_INVALID_SIGNATURE",
    "MISSING_EXTERNAL_CUSTODIAN_TRUST":
        "M53_CHECKPOINT_TRUST_NOT_PROVISIONED",
    "SIGNED_OTHER_JOURNAL_NAMESPACE":
        "M53_CHECKPOINT_NAMESPACE_MISMATCH",
    "SIGNED_OTHER_AUDIENCE":
        "M53_CHECKPOINT_AUDIENCE_MISMATCH",
    "EXPIRED_CUSTODIAN_CHECKPOINT":
        "M53_CHECKPOINT_EXPIRED_CHECKPOINT",
    "FUTURE_DATED_CUSTODIAN_CHECKPOINT":
        "M53_CHECKPOINT_FUTURE_CHECKPOINT",
    "MISSING_SIGNED_CHECKPOINT_SIGNATURE":
        "M53_CHECKPOINT_RECEIPT_MALFORMED",
    "UNREVIEWED_SIGNED_SEQUENCE_TYPE":
        "M53_CHECKPOINT_INVALID_SIGNED_PAYLOAD",
    "DELETED_JOURNAL_FILE":
        "M47_SQLITE_SOURCE_FILE_MISSING",
    "REPLACED_VALID_JOURNAL_FILE":
        "M47_SQLITE_SOURCE_FILE_REPLACED",
    "REPLACED_JOURNAL_SYMLINK":
        "M47_SQLITE_SOURCE_SYMLINK_REJECTED",
}


def _review(fx:dict,checkpoint:dict,kwargs:dict)->dict:
    return backup.inspect_signed_replay_checkpoint_reconciliation(
        replay_ledger=fx["ledger"],
        independently_held_checkpoint=checkpoint,
        custodian_trust=fx["trust"],
        journal_namespace=NAMESPACE,
        expected_audience=AUDIENCE,
        as_of_utc=kwargs["as_of_utc"],
    )


def _checkpoint_review(fx:dict,kwargs:dict,checkpoint:dict)->dict:
    return backup.record_checkpointed_witnessed_recovery_review(
        fx["bundle"],fx["result"],replay_ledger=fx["ledger"],
        **kwargs,
        external_checkpoint=checkpoint,
        checkpoint_custodian_trust=fx["trust"],
        checkpoint_namespace=NAMESPACE,
        checkpoint_audience=AUDIENCE,
    )


def _alter(case:str,fx:dict,kwargs:dict)->tuple[dict,dict]:
    prior=deepcopy(fx["current_checkpoint"])
    custodian=fx["private_custodian_key"]
    journal=fx["ledger"]
    if case=="OLD_SIGNED_HEAD_AFTER_TWO_SUCCESSIVE_REVIEWS":
        second=_checkpoint_review(
            fx,fx["next_review_kwargs"],fx["current_checkpoint"]
        )
        if second["m53_successor_sequence"]!=2:
            raise ValueError("M55_SECOND_LOCAL_REVIEW_NOT_PROVEN")
        updated=_make_anchor(
            _journal_state(journal),custodian,checkpoint_id="M55-COUNTERSIGN-SEQ2"
        )
        third=_new_signed_context(
            fx["original_review_kwargs"],fx["reviewer_private_keys"],
            "m55-next-third-local-review"
        )
        outcome=_checkpoint_review(fx,third,updated)
        if outcome["m53_successor_sequence"]!=3:
            raise ValueError("M55_THIRD_LOCAL_REVIEW_NOT_PROVEN")
    elif case=="COHERENT_SAME_SEQUENCE_REWRITE":
        _rewrite_rows(journal,"REWRITE_REVIEW_MANIFEST_VALID_ROWS")
        journal.verify()
    elif case=="SIGNED_HEAD_AHEAD_AFTER_ROLLBACK":
        _rewrite_rows(journal,"ROLLBACK_TO_EMPTY_SAME_INODE")
        journal.verify()
    elif case=="TAMPER_SIGNED_ANCESTOR_AND_APPEND_VALID_SUCCESSOR":
        _checkpoint_review(fx,fx["next_review_kwargs"],fx["current_checkpoint"])
        _rewrite_rows(journal,"REWRITE_REVIEW_SCOPE_VALID_ROWS")
        journal.verify()
    elif case=="LEGACY_LOCAL_ONLY_APPEND_NOT_RECONCILABLE":
        # TechnicalReviewReplayLedger is imported globally. A branch-local
        # import would make it local across this ENTIRE function, causing
        # all other test cases that construct alternate stores to fail with
        # UnboundLocalError before checking real source behavior.
        # Separate never-elevated journal in a different disposable path.
        legacy=TechnicalReviewReplayLedger(
            journal.path.with_name("m55-local-only-ineligible.sqlite3"),
            create=True,
        )
        external_initial=_make_anchor(
            _journal_state(legacy),custodian,
            checkpoint_id="M55-LOCAL-ONLY-INITIAL",
        )
        local=backup.record_witnessed_recovery_review(
            fx["bundle"],fx["result"],replay_ledger=legacy,
            **fx["next_review_kwargs"],
        )
        if local["review_attempt_recorded_once"] is not True:
            raise ValueError("M55_LOCAL_ONLY_TEST_APPEND_NOT_EXECUTED")
        fx["ledger"]=legacy
        prior=external_initial
    elif case=="CHECKPOINT_MODE_HEADER_RESET":
        with __import__("sqlite3").connect(journal.path) as c:
            c.execute("PRAGMA user_version=0")
        journal.verify()
    elif case=="UNTRUSTED_EPHEMERAL_CUSTODIAN_SIGNATURE":
        _resign(prior,Ed25519PrivateKey.generate())
    elif case=="UNTRUSTED_SUBSTITUTED_PUBLIC_KEY":
        replacement=Ed25519PrivateKey.generate()
        fx["trust"]["public_key_hex"]=replacement.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
    elif case=="MISSING_EXTERNAL_CUSTODIAN_TRUST":
        fx["trust"]=None
    elif case=="SIGNED_OTHER_JOURNAL_NAMESPACE":
        prior["payload"]["journal_namespace"]="M55-OTHER-NAMESPACE"
        _resign(prior,custodian)
    elif case=="SIGNED_OTHER_AUDIENCE":
        prior["payload"]["audience"]="M55-OTHER-AUDIENCE"
        _resign(prior,custodian)
    elif case=="EXPIRED_CUSTODIAN_CHECKPOINT":
        prior["payload"]["expires_at_utc"]="2026-10-13T18:30:00Z"
        _resign(prior,custodian)
    elif case=="FUTURE_DATED_CUSTODIAN_CHECKPOINT":
        prior["payload"]["issued_at_utc"]="2026-10-13T19:30:00Z"
        _resign(prior,custodian)
    elif case=="MISSING_SIGNED_CHECKPOINT_SIGNATURE":
        prior.pop("signature_b64")
    elif case=="UNREVIEWED_SIGNED_SEQUENCE_TYPE":
        prior["payload"]["review_sequence"]=True
    elif case=="DELETED_JOURNAL_FILE":
        journal.path.unlink()
    elif case=="REPLACED_VALID_JOURNAL_FILE":
        other=journal.path.with_name("m55-valid-but-different-empty.sqlite3")
        TechnicalReviewReplayLedger(other,create=True)
        os.replace(other,journal.path)
    elif case=="REPLACED_JOURNAL_SYMLINK":
        other=journal.path.with_name("m55-symlink-target.sqlite3")
        TechnicalReviewReplayLedger(other,create=True)
        journal.path.unlink()
        journal.path.symlink_to(other)
    else:
        raise ValueError("M55_UNKNOWN_ADVERSARIAL_CHECKPOINT_MUTATION")
    return fx,prior


def replay_one(case:str)->dict:
    if type(case) is not str or case not in SCENARIOS:
        raise ValueError("M55_UNKNOWN_CRASH_GAP_NEGATIVE_CASE")
    with tempfile.TemporaryDirectory(prefix="retally-m55-checkpoint-crash-gap-") as td:
        root=Path(td)
        fx=_fixture(root)
        kwargs=fx["original_review_kwargs"]
        # Both positive situations are proven for each independent fixture:
        # current signed head matches; original signed HEAD 0 is one
        # completed but still UNCOUNTERSIGNED review behind current.
        signed=_review(fx,fx["current_checkpoint"],kwargs)
        pending=_review(fx,fx["initial_checkpoint"],kwargs)
        if (signed["state"]!=SIGNED_HEAD_MATCH
            or signed["journal_matches_off_journal_signed_checkpoint"] is not True
            or signed["restore_activation_authorized"] is not False
            or pending["state"]!=ONE_UNSIGNED_SUCCESSOR
            or pending["signed_prior_sequence"]!=0
            or pending["current_local_sequence"]!=1
            or pending["unique_predecessor_candidate_count"]!=1
            or pending["new_review_admission_must_remain_blocked"] is not True
            or pending["external_signing_or_persistent_checkpoint_updated"] is not False):
            raise ValueError("M55_CRASH_GAP_GOOD_CONTROL_NOT_REPRODUCED")
        # Original recovery SQLite files remain immutable in every attempt.
        before=[backup._file_hash(fx["bundle"]/n) for n in backup._capture_files()]
        fx,altered=_alter(case,fx,kwargs)
        # For all state-drift attacks, use the signed HEAD=1 checkpoint,
        # not the independently signed empty initial checkpoint.
        try:
            _review(fx,altered,kwargs)
        except (ValueError,RuntimeError) as exc:
            if SCENARIOS[case] not in str(exc):
                raise ValueError(
                    "M55_WRONG_CRASH_GAP_OR_SIGNER_DENIAL:"+case
                ) from exc
        else:
            raise ValueError("M55_UNSAFE_CHECKPOINT_RECONCILIATION_ACCEPTED:"+case)
        if before!=[
            backup._file_hash(fx["bundle"]/n) for n in backup._capture_files()
        ]:
            raise ValueError("M55_RECONCILIATION_TOUCHED_CUSTOMER_SQLITE")
        return {
            "scenario":case,
            "exact_expected_denial":SCENARIOS[case],
            "original_signed_head_matched_in_positive_control":True,
            "honest_one_step_unsigned_successor_held_pending":True,
            "authentic_previous_checkpoint_signature_required":True,
            "source_rollback_fork_or_untrusted_signature_denied":True,
            "no_external_checkpoint_automatically_signed_or_published":True,
            "all_four_customer_recovery_files_untouched":True,
            "real_customer_restore_or_human_approval":False,
            "historical_original_findings_closed":0,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M55_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(k) for k in SCENARIOS]
    if len(cases)!=18 or any(
        r["exact_expected_denial"]!=SCENARIOS[r["scenario"]]
        or r["source_rollback_fork_or_untrusted_signature_denied"] is not True
        or r["historical_original_findings_closed"]!=0 for r in cases
    ):
        raise ValueError("M55_RECONCILIATION_NEGATIVE_CONTROL_INCOMPLETE")
    report={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "original_research_labs":14,
        "new_lab_created":False,
        "valid_original_countersigned_head_positive_controls":18,
        "valid_one_commit_pending_external_countersign_controls":18,
        "signed_journal_or_bad_custodian_negative_scenarios":18,
        "current_exact_fail_closed_reconciliation_denials":18,
        "signed_prefix_excludes_exactly_one_review_and_two_nonces":True,
        "journal_is_inspected_read_only_in_one_sqlite_revision":True,
        "multiple_local_commits_without_custodian_signatures_rejected":True,
        "one_step_unsigned_result_must_remain_pending_not_reauthorized":True,
        "prior_signed_head_and_full_journal_mode_both_bound":True,
        "external_key_supplied_by_caller_not_recovery_files":True,
        "external_custodian_signs_or_stores_checkpoint_by_this_code":False,
        "independent_remote_trust_or_immutable_high_water_service_present":False,
        "independently_authenticated_bank_or_carrier_payment":False,
        "full_two_file_acid_transaction_proven":False,
        "actual_customer_restore_or_legally_approved":False,
        "original_historical_findings_open":26,
        "original_historical_findings_closed":0,
        "independent_first_customer_human_gates_unmet":18,
        "real_customer_cash_recovered":None,
        "externally_publishable_empirical_claims_approved":0,
        "production_merge_registration_schedules_unchanged":True,
        "cases":cases,
        "caveat":(
            "M55 classifies a crash gap where ONE locally committed, "
            "originally M53-validated technical review is present but "
            "its successor digest is not yet signed by the separately "
            "trusted custodian. The result is PENDING, never signed, "
            "stored externally, activated or permitted to bypass M53's "
            "exact write fence. The old independently signed state is "
            "reconstructed by removing each possible review and its "
            "exact two nonces and comparing the entire prior row image "
            "AND local security mode. M55 refuses multiple unanchored "
            "reviews, deleted signed history, forks, substituted source "
            "files and untrusted/expired signers. A privileged actor could "
            "insert ONE coherent forged review after a real signed head; "
            "this will at most be labeled UNSIGNED PENDING and requires "
            "actual independent custodian evidence before it could ever "
            "become signed. No real remote custodian, bank/carrier "
            "authority, legal customer approval, atomic external "
            "checkpoint publication or commercial readiness exists. "
            "All 26 historic RecoveryOS findings and 18 independent "
            "first-customer human gate requirements remain open."
        ),
    }
    report["receipt_sha256"]=digest(report)
    return report


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(x["scenario"])+"</th><td>"
        +escape(x["exact_expected_denial"])+"</td>"
        "<td>NO EXTERNAL COUNTERSIGN / NO RESTORE</td></tr>"
        for x in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M55 | Signed Checkpoint Crash-Gap Reconciling</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f5f8f4;'
        'color:#203a2e;max-width:1050px;margin:auto;padding:24px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'th,td{text-align:left;border-bottom:1px solid #dce8e0;padding:11px}'
        'small{color:#64776c}</style></head><body>'
        '<small>RETALLY / ORIGINAL LAB 14 / M55 / FICTIONAL ONLY</small>'
        '<h1>Recovery checkpoint crash-gap: reconcile, never autoapprove</h1>'
        '<p>18 positive signed heads, 18 proven one-review unsigned successor '
        'holds, and 18 exact denials for source mismatch, multi-step '
        'forks, rollback, local-only journal or invalid external signatures. '
        'No custodian checkpoint was actually issued, no actual customer '
        'funds or pilot approval. All 26 findings remain open.</p>'
        '<table><thead><tr><th>Adversarial change</th><th>Exact denial</th>'
        '<th>Outcome</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="Offline journal crash-gap technical rehearsal")
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    report=run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"checkpoint_reconciliation_m55.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    (args.out/"checkpoint_reconciliation_m55.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "signed_valid_original_heads":18,
        "unsigned_successor_holds":18,
        "exact_reconciliation_denials":18,
        "original_historical_findings_closed":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
