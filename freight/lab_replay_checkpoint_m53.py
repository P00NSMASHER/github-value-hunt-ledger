"""RETALLY existing Lab14 / M53: off-journal signed replay checkpoints.

Every case creates a real fictional M50 dual-SQLite bundle, two ephemeral
M51 Ed25519 reviewers, a durable M52 one-time SQLite journal, and a THIRD
ephemeral test custodian signing the *entire* current journal state.

After a valid checkpointed review, sixteen tests present a different,
stale or forged checkpoint OR coherently alter the original replay journal
without changing its pathname, schema or valid local row relationships.
The M53 higher-assurance gate must refuse with an exact typed reason
BEFORE writing the next request/nonce. An out-of-band REAL custodian,
immutable remote anchor, distributed transaction, real customer authority
and independent key provisioning are NOT created in this campaign.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sqlite3
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from freight import backup_restore as backup
from freight.lab_assurance import digest
from freight.lab_recovery_witness_m51 import _make_known_good
from freight.lab_recovery_replay_m52 import _new_signed_context
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger
from freight.recovery_checkpoint_m53 import (
    SCOPE as CHECKPOINT_SCOPE,PURPOSE,signing_message,journal_state,
)

SCOPE="RETALLY_LAB14_M53_SIGNED_EXTERNAL_CHECKPOINT_ROLLBACK_TEST_SYNTHETIC"
NAMESPACE="M53-DEDICATED-REVIEW-STATE"
AUDIENCE="M53-INDEPENDENT-REPLAY-REVIEW"
AUTHORITY="M53-IN-MEMORY-ONLY-CUSTODIAN"
NOW="2026-10-13T19:00:00Z"
FAILURES={
    "ROLLBACK_TO_EMPTY_SAME_INODE":"M53_CHECKPOINT_STATE_MISMATCH",
    "ROLLBACK_LAST_REVIEW_SAME_INODE":"M53_CHECKPOINT_STATE_MISMATCH",
    "REWRITE_REVIEW_MANIFEST_VALID_ROWS":"M53_CHECKPOINT_STATE_MISMATCH",
    "REWRITE_REVIEW_SCOPE_VALID_ROWS":"M53_CHECKPOINT_STATE_MISMATCH",
    "REWRITE_SIGNED_PAYLOAD_DIGEST_VALID_ROWS":"M53_CHECKPOINT_STATE_MISMATCH",
    "REWRITE_TRUSTED_KEY_FINGERPRINT_VALID_ROWS":"M53_CHECKPOINT_STATE_MISMATCH",
    "REUSE_SIGNED_EMPTY_CHECKPOINT":"M53_CHECKPOINT_STATE_MISMATCH",
    "TRUSTED_CUSTODIAN_SIGNS_WRONG_DIGEST":"M53_CHECKPOINT_STATE_MISMATCH",
    "TRUSTED_CUSTODIAN_SIGNS_FUTURE_SEQUENCE":"M53_CHECKPOINT_STATE_MISMATCH",
    "FORGED_UNTRUSTED_CHECKPOINT_SIGNATURE":"M53_CHECKPOINT_INVALID_SIGNATURE",
    "UNPROVISIONED_CUSTODIAN_TRUST":"M53_CHECKPOINT_TRUST_NOT_PROVISIONED",
    "CUSTODIAN_KEY_SUBSTITUTION":"M53_CHECKPOINT_INVALID_SIGNATURE",
    "SIGNED_OTHER_JOURNAL_NAMESPACE":"M53_CHECKPOINT_NAMESPACE_MISMATCH",
    "SIGNED_DIFFERENT_AUDIENCE":"M53_CHECKPOINT_AUDIENCE_MISMATCH",
    "EXPIRED_SIGNED_CHECKPOINT":"M53_CHECKPOINT_EXPIRED_CHECKPOINT",
    "FUTURE_DATED_SIGNED_CHECKPOINT":"M53_CHECKPOINT_FUTURE_CHECKPOINT",
    "STALE_SIGNED_CHECKPOINT":"M53_CHECKPOINT_STALE_CHECKPOINT",
    "INVALID_LONG_LIVED_CHECKPOINT":"M53_CHECKPOINT_INVALID_CHECKPOINT_LIFETIME",
    "MISSING_CHECKPOINT_SIGNATURE":"M53_CHECKPOINT_RECEIPT_MALFORMED",
}


def _journal_state(ledger:TechnicalReviewReplayLedger)->dict:
    con=ledger._connect()
    try:
        con.execute("BEGIN")
        try:
            return journal_state(con)
        finally:
            con.rollback()
    finally:
        con.close()


def _make_anchor(state:dict, key:Ed25519PrivateKey, *,
                 checkpoint_id:str)->dict:
    payload={
        "schema_version":1,
        "purpose":PURPOSE,
        "authority_id":AUTHORITY,
        "journal_namespace":NAMESPACE,
        "audience":AUDIENCE,
        "checkpoint_id":checkpoint_id,
        "review_sequence":state["review_sequence"],
        "journal_state_sha256":state["journal_state_sha256"],
        "issued_at_utc":"2026-10-13T18:00:00Z",
        "expires_at_utc":"2026-10-13T20:00:00Z",
    }
    return {
        "payload":payload,
        "signature_b64":base64.b64encode(
            key.sign(signing_message(payload))
        ).decode("ascii"),
    }


def _resign(anchor:dict,key:Ed25519PrivateKey)->None:
    anchor["signature_b64"]=base64.b64encode(
        key.sign(signing_message(anchor["payload"]))
    ).decode("ascii")


def _fixture(root:Path)->dict:
    bundle,result,manifest,reviewers,original=_make_known_good(root)
    ledger=TechnicalReviewReplayLedger(
        root/"separate-only-test-replay-journal.sqlite3",create=True
    )
    key=Ed25519PrivateKey.generate()
    trust={
        "authority_id":AUTHORITY,
        "public_key_hex":key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ).hex(),
    }
    initial=_make_anchor(_journal_state(ledger),key,checkpoint_id="M53-INITIAL-0001")
    initial_state=_journal_state(ledger)
    if initial_state["review_sequence"]!=0:
        raise ValueError("M53_TEST_FIRST_JOURNAL_NOT_EMPTY")
    extra={
        "external_checkpoint":initial,
        "checkpoint_custodian_trust":trust,
        "checkpoint_namespace":NAMESPACE,
        "checkpoint_audience":AUDIENCE,
    }
    first=backup.record_checkpointed_witnessed_recovery_review(
        bundle,result,replay_ledger=ledger,**original,**extra
    )
    state=_journal_state(ledger)
    if (first["m53_successor_sequence"]!=1
        or first["m53_successor_state_sha256"]!=state["journal_state_sha256"]
        or first["m53_successor_requires_independent_external_signature"] is not True
        or first["m53_external_checkpoint_updated_by_this_operation"] is not False
        or first["real_customer_restore_activation_authorized"] is not False):
        raise ValueError("M53_INITIAL_ATOMIC_CHECKPOINT_COMMIT_INVALID")
    current=_make_anchor(state,key,checkpoint_id="M53-SEQUENCE-0001")
    return {
        "bundle":bundle,"result":result,"manifest":manifest,
        "ledger":ledger,"private_custodian_key":key,"trust":trust,
        "current_checkpoint":current,"initial_checkpoint":initial,
        "reviewer_private_keys":reviewers,
        "original_review_kwargs":original,
        "next_review_kwargs":_new_signed_context(
            original,reviewers,"m53-second"
        ),
    }


def _rewrite_rows(ledger:TechnicalReviewReplayLedger,scenario:str,
                  *,recent_request:str|None=None)->None:
    """Modify disposable SQLite THROUGH actual privileged SQL, restore DDL.

    All returned coherent-row cases still pass original M52's _validate.
    They would not be detectable without an externally held checkpoint.
    """
    with sqlite3.connect(ledger.path) as con:
        if scenario in ("ROLLBACK_TO_EMPTY_SAME_INODE","ROLLBACK_LAST_REVIEW_SAME_INODE"):
            names=("immutable_witness_nonce_d","immutable_review_consumptions_d")
            original={
                name:con.execute(
                    "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                    (name,)
                ).fetchone()[0] for name in names
            }
            for name in names:
                con.execute('DROP TRIGGER "'+name+'"')
            if recent_request is None:
                con.execute("DELETE FROM witness_nonce_consumptions")
                con.execute("DELETE FROM review_consumptions")
            else:
                con.execute(
                    "DELETE FROM witness_nonce_consumptions WHERE restore_request_id=?",
                    (recent_request,)
                )
                con.execute(
                    "DELETE FROM review_consumptions WHERE restore_request_id=?",
                    (recent_request,)
                )
            for name in reversed(names):
                con.execute(original[name])
        elif scenario in ("REWRITE_REVIEW_MANIFEST_VALID_ROWS","REWRITE_REVIEW_SCOPE_VALID_ROWS"):
            name="immutable_review_consumptions_u"
            ddl=con.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                (name,)
            ).fetchone()[0]
            con.execute('DROP TRIGGER "'+name+'"')
            if scenario=="REWRITE_REVIEW_MANIFEST_VALID_ROWS":
                con.execute(
                    "UPDATE review_consumptions SET manifest_sha256=?",
                    ("f"*64,)
                )
            else:
                con.execute(
                    "UPDATE review_consumptions SET buyer_id=?",
                    ("M53-FORGED-OTHER-OWNER",)
                )
            con.execute(ddl)
        elif scenario in (
            "REWRITE_SIGNED_PAYLOAD_DIGEST_VALID_ROWS",
            "REWRITE_TRUSTED_KEY_FINGERPRINT_VALID_ROWS",
        ):
            name="immutable_witness_nonce_u"
            ddl=con.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                (name,)
            ).fetchone()[0]
            con.execute('DROP TRIGGER "'+name+'"')
            if scenario=="REWRITE_SIGNED_PAYLOAD_DIGEST_VALID_ROWS":
                con.execute(
                    "UPDATE witness_nonce_consumptions "
                    "SET signed_payload_sha256=? "
                    "WHERE role='RECOVERY_OPERATOR'",
                    ("e"*64,)
                )
            else:
                con.execute(
                    "UPDATE witness_nonce_consumptions SET public_key_sha256=? "
                    "WHERE role='RECOVERY_OPERATOR'",
                    ("d"*64,)
                )
            con.execute(ddl)
        else:
            raise ValueError("M53_UNKNOWN_PRIVILEGED_SQLITE_MUTATION")


def replay_one(case:str)->dict:
    if type(case) is not str or case not in FAILURES:
        raise ValueError("M53_UNKNOWN_SIGNED_CHECKPOINT_ATTACK")
    with tempfile.TemporaryDirectory(prefix="retally-m53-off-journal-checkpoint-") as tmp:
        root=Path(tmp)
        fx=_fixture(root)
        private=fx["private_custodian_key"]
        checkpoint=deepcopy(fx["current_checkpoint"])
        trust=deepcopy(fx["trust"])
        review=deepcopy(fx["next_review_kwargs"])
        ledger=fx["ledger"]
        original_identity=(ledger.path.stat().st_dev,ledger.path.stat().st_ino)
        baseline=[backup._file_hash(fx["bundle"]/n) for n in backup._capture_files()]
        if case in (
            "ROLLBACK_TO_EMPTY_SAME_INODE",
            "REWRITE_REVIEW_MANIFEST_VALID_ROWS",
            "REWRITE_REVIEW_SCOPE_VALID_ROWS",
            "REWRITE_SIGNED_PAYLOAD_DIGEST_VALID_ROWS",
            "REWRITE_TRUSTED_KEY_FINGERPRINT_VALID_ROWS",
        ):
            _rewrite_rows(ledger,case)
            ledger.verify()
        elif case=="ROLLBACK_LAST_REVIEW_SAME_INODE":
            # A second correctly checkpointed review advances the current
            # journal to SEQUENCE=2, then an attacker rewinds it to seq1.
            second=backup.record_checkpointed_witnessed_recovery_review(
                fx["bundle"],fx["result"],replay_ledger=ledger,**review,
                external_checkpoint=checkpoint,
                checkpoint_custodian_trust=trust,
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
            checkpoint=_make_anchor(
                _journal_state(ledger),private,
                checkpoint_id="M53-SEQUENCE-0002"
            )
            review=_new_signed_context(
                fx["original_review_kwargs"],fx["reviewer_private_keys"],
                "m53-third"
            )
            _rewrite_rows(
                ledger,case,
                recent_request=fx["next_review_kwargs"]["expected_restore_request_id"],
            )
            ledger.verify()
            if second["m53_successor_sequence"]!=2:
                raise ValueError("M53_SECOND_POSITIVE_GENERATION_MISSING")
        elif case=="REUSE_SIGNED_EMPTY_CHECKPOINT":
            checkpoint=deepcopy(fx["initial_checkpoint"])
        elif case=="TRUSTED_CUSTODIAN_SIGNS_WRONG_DIGEST":
            checkpoint["payload"]["journal_state_sha256"]="a"*64
            _resign(checkpoint,private)
        elif case=="TRUSTED_CUSTODIAN_SIGNS_FUTURE_SEQUENCE":
            checkpoint["payload"]["review_sequence"]=999
            _resign(checkpoint,private)
        elif case=="FORGED_UNTRUSTED_CHECKPOINT_SIGNATURE":
            _resign(checkpoint,Ed25519PrivateKey.generate())
        elif case=="UNPROVISIONED_CUSTODIAN_TRUST":
            trust=None
        elif case=="CUSTODIAN_KEY_SUBSTITUTION":
            other=Ed25519PrivateKey.generate()
            trust["public_key_hex"]=other.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            ).hex()
        elif case=="SIGNED_OTHER_JOURNAL_NAMESPACE":
            checkpoint["payload"]["journal_namespace"]="M53-OTHER-SIGNED-JOURNAL"
            _resign(checkpoint,private)
        elif case=="SIGNED_DIFFERENT_AUDIENCE":
            checkpoint["payload"]["audience"]="M53-OTHER-SIGNED-AUDIENCE"
            _resign(checkpoint,private)
        elif case=="EXPIRED_SIGNED_CHECKPOINT":
            checkpoint["payload"]["expires_at_utc"]="2026-10-13T18:30:00Z"
            _resign(checkpoint,private)
        elif case=="FUTURE_DATED_SIGNED_CHECKPOINT":
            checkpoint["payload"]["issued_at_utc"]="2026-10-13T19:30:00Z"
            _resign(checkpoint,private)
        elif case=="STALE_SIGNED_CHECKPOINT":
            checkpoint["payload"]["issued_at_utc"]="2026-10-11T18:00:00Z"
            _resign(checkpoint,private)
        elif case=="INVALID_LONG_LIVED_CHECKPOINT":
            checkpoint["payload"]["expires_at_utc"]="2026-10-15T20:00:00Z"
            _resign(checkpoint,private)
        elif case=="MISSING_CHECKPOINT_SIGNATURE":
            checkpoint.pop("signature_b64")

        pre_state=_journal_state(ledger)
        if original_identity!=(ledger.path.stat().st_dev,ledger.path.stat().st_ino):
            raise ValueError("M53_DISPOSABLE_REWRITE_WRONG_FILE_IDENTITY")
        try:
            backup.record_checkpointed_witnessed_recovery_review(
                fx["bundle"],fx["result"],
                replay_ledger=ledger,**review,
                external_checkpoint=checkpoint,
                checkpoint_custodian_trust=trust,
                checkpoint_namespace=NAMESPACE,
                checkpoint_audience=AUDIENCE,
            )
        except ValueError as exc:
            if FAILURES[case] not in str(exc):
                raise ValueError(
                    "M53_WRONG_ROLLBACK_OR_SIGNATURE_DENIAL:"+case+":"+str(exc)
                ) from exc
        else:
            raise ValueError("M53_SIGNED_OFF_JOURNAL_CHECKPOINT_FALSE_ACCEPT:"+case)
        if _journal_state(ledger)!=pre_state:
            raise ValueError("M53_DENIED_CHECKPOINT_STAGED_REPLAY_JOURNAL_WRITE")
        if baseline!=[
            backup._file_hash(fx["bundle"]/n) for n in backup._capture_files()
        ]:
            raise ValueError("M53_DENIED_CHECKPOINT_MUTATED_CUSTOMER_BACKUP")
        return {
            "scenario":case,
            "expected_exact_denial":FAILURES[case],
            "prior_valid_signed_off_journal_positive_review":True,
            "actual_same_file_local_journal_read_and_checked":True,
            "negative_checkpoint_or_coherent_rollback_rejected":True,
            "denied_review_left_journal_state_unchanged":True,
            "original_four_sqlite_recovery_images_untouched":True,
            "one_local_checkpoint_not_a_distributed_trust_service":True,
            "independent_real_signing_custodian_provisioned":False,
            "original_historical_findings_closed":0,
            "human_first_customer_controls_unmet":18,
            "actual_customer_restore_activation":False,
        }


def run_campaign(*,as_of:date)->dict:
    if type(as_of) is not date or as_of<date(2026,10,13):
        raise ValueError("M53_INVALID_RESEARCH_AS_OF")
    cases=[replay_one(name) for name in FAILURES]
    if len(cases)!=19 or any(
        c["expected_exact_denial"]!=FAILURES[c["scenario"]]
        or c["negative_checkpoint_or_coherent_rollback_rejected"] is not True
        or c["denied_review_left_journal_state_unchanged"] is not True
        or c["original_historical_findings_closed"]!=0
        for c in cases
    ):
        raise ValueError("M53_INCOMPLETE_CHECKPOINT_ROLLBACK_PROOFS")
    report={
        "schema_version":1,
        "scope":SCOPE,
        "as_of":as_of.isoformat(),
        "existing_research_labs":14,
        "new_lab_created":False,
        "synthetic_checkpointed_positive_reviews":len(cases),
        "same_journal_state_or_signature_negative_scenarios":len(cases),
        "exact_current_checkpoint_denials":len(cases),
        "coherent_same_inode_journal_rollback_cases":2,
        "same_inode_coherent_row_tamper_cases":4,
        "checkpoint_verification_occurs_under_same_sqlite_write_lock":True,
        "independent_custodian_public_key_must_be_supplied_by_caller":True,
        "successor_checkpoint_requires_separate_external_signature":True,
        "successor_checkpoint_externally_persisted_by_this_code":False,
        "original_m50_m51_validation_still_required":True,
        "old_m52_local_only_entrypoint_still_rollback_susceptible":True,
        "externally_operated_nonrollbackable_checkpoint_service_provisioned":False,
        "two_sqlite_sources_share_one_acid_commit":False,
        "real_customer_or_carrier_signatures_or_legal_consent_verified":False,
        "real_restore_or_customer_activation_executed":False,
        "historical_original_findings_open":26,
        "historical_original_findings_closed":0,
        "human_first_customer_pilot_gates_unmet":18,
        "actual_customer_cash_recovered":None,
        "externally_publishable_empirical_claims_approved":0,
        "production_deployment_business_registration_or_schedules_changed":False,
        "cases":cases,
        "caveat":(
            "Nineteen test-only current-code negative scenarios use in-memory "
            "ephemeral Ed25519 external-custodian simulations, not a real "
            "independently managed signer or durable remote high-water service. "
            "M53's new explicit checkpointed technical review compares the "
            "entire valid M52 journal to a caller-held signed state INSIDE "
            "the consuming write transaction and catches coherent same-inode "
            "rollbacks that M52's local-only API still accepts. After a "
            "successful locally committed review, its successor digest is "
            "UNSIGNED; a real custodian must attest and persist it before "
            "additional checkpointed reviews. Without a separate trusted "
            "signer and atomic external checkpoint service, an adversary "
            "controlling both local storage and trust context can still "
            "defeat this boundary. This is not customer approval or a "
            "real bank/carrier signature, customer recovery cash or "
            "independently attested rollback prevention. The original 26 "
            "historical defects and 18 independent first-customer human "
            "approval gates remain unfulfilled."
        ),
    }
    report["receipt_sha256"]=digest(report)
    return report


def render_html(report:dict)->str:
    rows="".join(
        "<tr><th>"+escape(c["scenario"])+"</th><td>"
        +escape(c["expected_exact_denial"])+"</td>"
        "<td>OFF-JOURNAL CHECKPOINT REJECTED</td></tr>"
        for c in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY M53 | Signed replay journal checkpoints</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f5f8f3;'
        'color:#233b2d;max-width:1050px;margin:auto;padding:24px}'
        'table{border-collapse:collapse;width:100%;background:white}'
        'th,td{text-align:left;border-bottom:1px solid #dbe6de;padding:11px}'
        'small{color:#687a70}</style></head><body>'
        '<small>RETALLY / EXISTING LAB 14 / M53 / INTERNAL FICTIONAL ONLY</small>'
        '<h1>Externally signed checkpoint vs rolled-back journal</h1>'
        '<p>19 synthetic valid original checkpointed reviews and 19 denied '
        'rollback/altered-signature cases. The external custodian is an '
        'EPHEMERAL TEST KEY ONLY; no independent remote signer was connected. '
        '26 historical findings and 18 customer human gates remain open.</p>'
        '<table><thead><tr><th>Fault</th><th>Exact denial</th>'
        '<th>Outcome</th></tr></thead><tbody>'+rows+
        '</tbody></table><p><small>'+escape(report["caveat"])+
        '</small></p></body></html>'
    )


def main()->None:
    parser=argparse.ArgumentParser(description="M53 offline checkpoint simulation")
    parser.add_argument("--as-of-date",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    report=run_campaign(as_of=a.as_of_date)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"signed_replay_checkpoint_m53.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    (a.out/"signed_replay_checkpoint_m53.html").write_text(
        render_html(report),encoding="utf-8"
    )
    print(json.dumps({
        "checkpointed_good_fictional_reviews":19,
        "current_exact_rollback_or_checkpoint_denials":19,
        "historical_original_findings_closed":0,
        "receipt_sha256":report["receipt_sha256"],
    },sort_keys=True))


if __name__=="__main__":
    main()
