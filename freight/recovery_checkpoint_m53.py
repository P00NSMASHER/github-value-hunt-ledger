"""RETALLY M53: independent checkpoint verification for M52 replay journal.

M52 one-time SQLite deduplication can be rolled back to an older internally
consistent history (including an empty one), enabling reuse of still-valid
M51 signed requests. This adds an EXPLICIT checkpointed review mode that
compares a caller-held, Ed25519 signed journal state with the actual entire
journal under the SAME BEGIN IMMEDIATE transaction that consumes the review.

No real anchor service or trusted signing authority is provisioned here.
M52's local-only entrypoint remains available and must never be described
as protected against malicious journal rollback. An outside custodian must
independently safeguard BOTH the signing key and latest signed checkpoint.
The next checkpoint must be signed outside the journal; recording and
external publication cannot form a distributed atomic transaction.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from typing import Mapping

from freight.contracts import canonical_hash
from freight.recovery_witness_m51 import HEX64,TOKEN
from freight.recovery_replay_m52 import _validate

SCOPE="RETALLY_M53_EXTERNALLY_HELD_REPLAY_CHECKPOINT_LOCAL_TEST_ONLY"
PURPOSE="RETALLY_REVIEW_JOURNAL_CHECKPOINT_V1"
DOMAIN=b"RETALLY:M53:EXTERNAL_REPLAY_CHECKPOINT:V1\x00"
PAYLOAD_KEYS=frozenset({
    "schema_version","purpose","authority_id","journal_namespace",
    "audience","checkpoint_id","review_sequence","journal_state_sha256",
    "issued_at_utc","expires_at_utc",
})
RECEIPT_KEYS=frozenset({"payload","signature_b64"})
TRUST_KEYS=frozenset({"authority_id","public_key_hex"})


def _fail(reason:str)->None:
    # Never echo paths, tenant, public key, customer, review or receipt data.
    raise ValueError("M53_CHECKPOINT_"+reason)


def _canonical_utc(value:object)->datetime:
    if type(value) is not str:
        _fail("BAD_TIMESTAMP")
    try:
        moment=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        _fail("BAD_TIMESTAMP")
    if (moment.utcoffset()!=timedelta(0)
        or moment.isoformat(timespec="seconds").replace("+00:00","Z")!=value):
        _fail("BAD_TIMESTAMP")
    return moment.astimezone(timezone.utc)


def journal_state(conn)->dict:
    """Verify entire persistent journal and SHA all typed rows in one snapshot.

    This is a LOCAL digest and cannot prove prior history without a truly
    independently held anchor. Stable row ordering and exact schema/rows
    match across reopening and SQLite WAL checkpoints.
    """
    assurance=_validate(conn)
    reviewed=conn.execute(
        "SELECT restore_request_id,manifest_sha256,result_proof_sha256,"
        "buyer_id,business_unit,audience,reviewed_at_utc,receipt_set_sha256,decision "
        "FROM review_consumptions ORDER BY restore_request_id"
    ).fetchall()
    nonces=conn.execute(
        "SELECT nonce_hex,restore_request_id,witness_id,role,"
        "public_key_sha256,signed_payload_sha256 "
        "FROM witness_nonce_consumptions ORDER BY nonce_hex"
    ).fetchall()
    if (assurance["technical_review_rows"]!=len(reviewed)
        or assurance["durable_individual_witness_nonces"]!=len(nonces)):
        _fail("SOURCE_CHANGED_INSIDE_SNAPSHOT")
    return {
        "review_sequence":len(reviewed),
        "journal_state_sha256":canonical_hash({
            "schema_version":1,
            "purpose":"M53_COMPLETE_LOCAL_REPLAY_JOURNAL_ROW_IMAGE",
            "review_rows":[list(row) for row in reviewed],
            "nonce_rows":[list(row) for row in nonces],
        }),
    }


def signing_message(payload:dict)->bytes:
    if type(payload) is not dict or frozenset(payload)!=PAYLOAD_KEYS:
        _fail("INVALID_SIGNED_PAYLOAD")
    if (type(payload["schema_version"]) is not int
        or payload["schema_version"]!=1
        or payload["purpose"]!=PURPOSE
        or any(type(payload[k]) is not str
               for k in PAYLOAD_KEYS-{"schema_version","review_sequence"})
        or type(payload["review_sequence"]) is not int
        or payload["review_sequence"]<0
        or payload["review_sequence"]>1000000000
        or not HEX64.fullmatch(payload["journal_state_sha256"])
        or not all(TOKEN.fullmatch(payload[k]) for k in (
            "authority_id","journal_namespace","audience","checkpoint_id"
        ))):
        _fail("INVALID_SIGNED_PAYLOAD")
    _canonical_utc(payload["issued_at_utc"])
    _canonical_utc(payload["expires_at_utc"])
    return DOMAIN+json.dumps(
        payload,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False
    ).encode("utf-8")


def verify_checkpoint_locked(
    conn, *,
    checkpoint:object,
    custodian_trust:object,
    journal_namespace:str,
    expected_audience:str,
    as_of_utc:datetime,
)->dict:
    """Verify independently provisioned signing key against a PINNED lock.

    Caller must hold BEGIN or BEGIN IMMEDIATE. This function neither
    writes the review DB nor downloads/loads any purported keys from
    within a backup bundle, and never accepts arbitrary attacker keys.
    """
    if (type(journal_namespace) is not str
        or not TOKEN.fullmatch(journal_namespace)
        or type(expected_audience) is not str
        or not TOKEN.fullmatch(expected_audience)
        or type(as_of_utc) is not datetime or as_of_utc.tzinfo is None
        or as_of_utc.utcoffset() is None):
        _fail("INVALID_CALLER_CONTEXT")
    if custodian_trust is None or custodian_trust=={}:
        _fail("TRUST_NOT_PROVISIONED")
    if (type(custodian_trust) is not dict
        or frozenset(custodian_trust)!=TRUST_KEYS
        or type(custodian_trust["authority_id"]) is not str
        or not TOKEN.fullmatch(custodian_trust["authority_id"])
        or type(custodian_trust["public_key_hex"]) is not str
        or not HEX64.fullmatch(custodian_trust["public_key_hex"])):
        _fail("TRUST_NOT_PROVISIONED")
    if type(checkpoint) is not dict or frozenset(checkpoint)!=RECEIPT_KEYS:
        _fail("RECEIPT_MALFORMED")
    payload=checkpoint["payload"]
    message=signing_message(payload)
    if payload["authority_id"]!=custodian_trust["authority_id"]:
        _fail("UNKNOWN_SIGNING_AUTHORITY")
    if payload["journal_namespace"]!=journal_namespace:
        _fail("NAMESPACE_MISMATCH")
    if payload["audience"]!=expected_audience:
        _fail("AUDIENCE_MISMATCH")

    now=as_of_utc.astimezone(timezone.utc)
    issue=_canonical_utc(payload["issued_at_utc"])
    expiry=_canonical_utc(payload["expires_at_utc"])
    if issue>now+timedelta(minutes=5):
        _fail("FUTURE_CHECKPOINT")
    if now-issue>timedelta(hours=24):
        _fail("STALE_CHECKPOINT")
    if expiry<=now:
        _fail("EXPIRED_CHECKPOINT")
    if expiry<=issue or expiry-issue>timedelta(hours=24):
        _fail("INVALID_CHECKPOINT_LIFETIME")

    encoded=checkpoint["signature_b64"]
    if type(encoded) is not str or len(encoded)>128:
        _fail("INVALID_SIGNATURE_ENCODING")
    try:
        signature=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):
        _fail("INVALID_SIGNATURE_ENCODING")
    if len(signature)!=64:
        _fail("INVALID_SIGNATURE_ENCODING")
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(custodian_trust["public_key_hex"])
        ).verify(signature,message)
    except (InvalidSignature,ValueError) as exc:
        raise ValueError("M53_CHECKPOINT_INVALID_SIGNATURE") from exc

    state=journal_state(conn)
    if (state["review_sequence"]!=payload["review_sequence"]
        or state["journal_state_sha256"]!=payload["journal_state_sha256"]):
        _fail("STATE_MISMATCH")
    return {
        "scope":SCOPE,
        "checkpoint_verified_inside_sqlite_transaction":True,
        "caller_trusted_external_custodian_signature_verified":True,
        "journal_state_matches_signed_external_receipt":True,
        "prior_signed_sequence":state["review_sequence"],
        "prior_state_sha256":state["journal_state_sha256"],
        "no_external_signing_service_or_customer_authority_provisioned":True,
        "restore_activation_or_business_registration_authorized":False,
    }
