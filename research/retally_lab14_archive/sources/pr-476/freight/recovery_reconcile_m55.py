"""RETALLY M55: read-only independently signed recovery checkpoint reconciliation.

M53/M54 correctly deny further checkpointed reviews when the local SQLite
one-time journal is ahead of the latest independently signed checkpoint.
That also occurs during an HONEST crash gap after the local review commits
but before an external custodian countersigns its successor.

This module distinguishes an unchanged signed head from exactly ONE new
locally committed review that descends from a properly signed predecessor.
It reconstructs the predecessor's full row image from the CURRENT journal
by excluding each candidate review AND its two consumed witness nonces,
and requires exactly one reconstructed predecessor image to match the
custodian-signed hash (including the strict security mode).

NO SOURCE MUTATION, NO SIGNING, NO EXTERNAL TRUST SERVICE, NO APPROVAL:
A provable one-step descendant is classified PENDING_EXTERNAL_COUNTERSIGN,
never autoaccepted. Multiple unanchored changes, forks, changed history,
unsupported legacy-only mode, bad signer and missing source fail closed.
Signatures remain verified from caller-supplied external trust roots.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from freight.recovery_checkpoint_m53 import (
    journal_state, verify_checkpoint_signature, digest_journal_rows,
)
from freight.recovery_mode_m54 import (
    CHECKPOINT_REQUIRED,LOCAL_ONLY,mode,
)
from freight.recovery_replay_m52 import TechnicalReviewReplayLedger

SCOPE="RETALLY_M55_READ_ONLY_OFF_JOURNAL_CRASH_GAP_CLASSIFICATION_ONLY"
SIGNED_HEAD_MATCH="EXTERNAL_SIGNED_HEAD_MATCHES_LOCAL"
ONE_UNSIGNED_SUCCESSOR="ONE_UNSIGNED_SUCCESSOR_REQUIRES_EXTERNAL_COUNTERSIGN"

_REVIEW_SQL=(
    "SELECT restore_request_id,manifest_sha256,result_proof_sha256,"
    "buyer_id,business_unit,audience,reviewed_at_utc,receipt_set_sha256,decision "
    "FROM review_consumptions ORDER BY restore_request_id"
)
_NONCE_SQL=(
    "SELECT nonce_hex,restore_request_id,witness_id,role,"
    "public_key_sha256,signed_payload_sha256 "
    "FROM witness_nonce_consumptions ORDER BY nonce_hex"
)


def _fail(code:str)->None:
    raise ValueError("M55_RECONCILE_"+code)


def _direct_child_count(review_rows:list,nonce_rows:list,
                        predecessor_sha:str,predecessor_count:int,
                        local_journal_identity_sha256:str)->int:
    """Find exact one-step signed-prefix row image; never infer chronology.

    The original M52 journal has no insertion-order serial. Enumerate each
    possible removed request and its exactly two nonce rows. The remaining
    complete row image must reproduce the actual independently signed
    ancestor's canonical hash. This is bounded by at most one unanchored
    review; larger gaps are rejected BEFORE enumeration.

    Both 0->54 initial promotion and 54->54 successive technical reviews
    are supported, with neither a migration nor unsigned checkpoint issued.
    """
    matches=0
    for candidate in review_rows:
        req=candidate[0]
        ancestors=[row for row in review_rows if row[0]!=req]
        if len(ancestors)!=predecessor_count:
            continue
        ancestor_nonces=[row for row in nonce_rows if row[1]!=req]
        if len(ancestor_nonces)!=2*predecessor_count:
            continue
        for previous_mode in (LOCAL_ONLY,CHECKPOINT_REQUIRED):
            if digest_journal_rows(
                ancestors,ancestor_nonces,previous_mode,
                local_journal_identity_sha256=local_journal_identity_sha256
            )==predecessor_sha:
                matches+=1
    return matches


def inspect_replay_checkpoint_gap(
    replay_ledger:TechnicalReviewReplayLedger, *,
    independently_held_checkpoint:object,
    custodian_trust:object,
    journal_namespace:str,
    expected_audience:str,
    as_of_utc:datetime,
)->dict:
    """Classify current journal against off-journal Ed25519 signed head.

    Returns a *technical hold / reconciliation assessment*, NOT a receipt
    that can bypass M53's pre-write exact checkpoint validation, not a
    durable nonce ledger, and never a customer/production restore approval.
    """
    if type(replay_ledger) is not TechnicalReviewReplayLedger:
        _fail("JOURNAL_NOT_EXPLICITLY_PROVISIONED")
    # Keep M53 signature/authority/audience/expiry semantics EXACTLY the
    # same as the official consuming gate. Do not read trusted keys from
    # any local backup, SQLite row or helper return.
    signed=verify_checkpoint_signature(
        checkpoint=independently_held_checkpoint,
        custodian_trust=custodian_trust,
        journal_namespace=journal_namespace,
        expected_audience=expected_audience,
        as_of_utc=as_of_utc,
    )
    con=replay_ledger._connect()
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        try:
            current=journal_state(con)  # entire chain/schema in this revision
            rows=con.execute(_REVIEW_SQL).fetchall()
            nonces=con.execute(_NONCE_SQL).fetchall()
            replay_ledger._check_identity()
            if (current["review_sequence"]!=len(rows)
                or len(nonces)!=2*len(rows)):
                _fail("SOURCE_CHANGED_IN_PINNED_REVISION")
            previous_count=signed["review_sequence"]
            if previous_count>len(rows):
                _fail("SIGNED_HISTORY_AHEAD_OF_CURRENT_JOURNAL")
            if previous_count==len(rows):
                if signed["journal_state_sha256"]!=current["journal_state_sha256"]:
                    _fail("SAME_SEQUENCE_JOURNAL_FORK_OR_MODE_ROLLBACK")
                return {
                    "scope":SCOPE,
                    "state":SIGNED_HEAD_MATCH,
                    "signed_prior_sequence":previous_count,
                    "current_local_sequence":len(rows),
                    "current_local_security_mode":current["local_checkpoint_mode"],
                    "journal_matches_off_journal_signed_checkpoint":True,
                    "one_step_successor_proven":False,
                    "pending_custodian_signature":False,
                    "restore_activation_authorized":False,
                    "customer_or_bank_authority_verified":False,
                    "external_signing_or_persistent_checkpoint_updated":False,
                    "original_historical_findings_closed":0,
                    "independent_pilot_human_controls_unmet":18,
                }
            if len(rows)!=previous_count+1:
                _fail("MULTIPLE_UNCOUNTERSIGNED_REVIEWS_OR_HISTORY_GAP")
            if current["local_checkpoint_mode"]!=CHECKPOINT_REQUIRED:
                _fail("LOCAL_ONLY_UNCOUNTERSIGNED_REVIEW_NOT_ELIGIBLE")

            predecessor_matches=_direct_child_count(
                rows,nonces,signed["journal_state_sha256"],previous_count,
                current["local_journal_identity_sha256"],
            )
            if predecessor_matches!=1:
                _fail("NOT_AN_EXACT_ONE_REVIEW_SIGNED_SUCCESSOR")

            return {
                "scope":SCOPE,
                "state":ONE_UNSIGNED_SUCCESSOR,
                "signed_prior_sequence":previous_count,
                "current_local_sequence":len(rows),
                "current_local_security_mode":CHECKPOINT_REQUIRED,
                "signed_predecessor_matches_one_removed_review_and_its_two_nonces":True,
                "unique_predecessor_candidate_count":predecessor_matches,
                "unsigned_successor_state_sha256":current["journal_state_sha256"],
                "journal_matches_off_journal_signed_checkpoint":False,
                "one_step_successor_proven":True,
                "pending_custodian_signature":True,
                "external_custodian_must_independently_review_sign_and_persist":True,
                "new_review_admission_must_remain_blocked":True,
                "restore_activation_authorized":False,
                "customer_or_bank_authority_verified":False,
                "external_signing_or_persistent_checkpoint_updated":False,
                "original_historical_findings_closed":0,
                "independent_pilot_human_controls_unmet":18,
            }
        finally:
            con.rollback()
    finally:
        con.close()
