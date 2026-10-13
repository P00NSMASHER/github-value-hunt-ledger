"""RETALLY M51: externally provisioned, dual-control recovery witness policy.

M49/M50 validate local SQLite, source generations, typed cash, and self-hashed
completion receipts. Local SHA-256 is NOT an external trust anchor: a party
with file access can coherently rehash the entire bundle. Any future RESTORE
ACTIVATION must call this separate, fail-closed, two-signature gate with
public keys provisioned by the *caller*, never discovered from the bundle.

The two Ed25519 signers are independent TECHNICAL reviewers only. Even two
valid signatures do not establish bank/carrier authenticity, customer/legal
consent, real recovered revenue or human first-customer approval. The
verification action never deploys, restores, publishes or modifies a file.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Mapping

SCOPE="RETALLY_M51_OFF_BUNDLE_DUAL_TECHNICAL_WITNESS_ONLY"
PURPOSE="RETALLY_TECHNICAL_RECOVERY_WITNESS_V1"
ROLES=("RECOVERY_OPERATOR","INDEPENDENT_SECURITY_REVIEWER")
DOMAIN=b"RETALLY:M51:RECOVERY_TECHNICAL_WITNESS:V1\x00"
HEX64=re.compile(r"^[0-9a-f]{64}$")
TOKEN=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$")
TRUST_KEYS=frozenset({"role","public_key_hex"})
PAYLOAD_KEYS=frozenset({
    "schema_version","purpose","manifest_sha256","result_proof_sha256",
    "buyer_id","business_unit","restore_request_id","audience",
    "witness_id","role","issued_at_utc","expires_at_utc","nonce_hex",
})


def _reject(reason:str) -> None:
    # Codes are stable and carry no keys, private identities or payload bytes.
    raise ValueError("M51_WITNESS_"+reason)


def _canonical_time(value:object)->datetime:
    if type(value) is not str:
        _reject("BAD_TIMESTAMP")
    try:
        timestamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        _reject("BAD_TIMESTAMP")
    if (timestamp.utcoffset()!=timedelta(0)
        or timestamp.isoformat(timespec="seconds").replace("+00:00","Z")!=value):
        _reject("BAD_TIMESTAMP")
    return timestamp.astimezone(timezone.utc)


def signing_message(payload:dict)->bytes:
    """Domain-separated bytes signed by a reviewer-held Ed25519 private key.

    This serializes an exact typed payload. It intentionally does NOT sign a
    path on the reviewer's local filesystem. The manifest SHA binds all four
    local SQLite artifact SHAs, provenance labels and chain/scoped receipts.
    """
    if type(payload) is not dict or frozenset(payload)!=PAYLOAD_KEYS:
        _reject("INVALID_RECEIPT_FIELDS")
    if (type(payload["schema_version"]) is not int
        or payload["schema_version"]!=1
        or payload["purpose"]!=PURPOSE
        or any(type(payload[k]) is not str for k in PAYLOAD_KEYS-{"schema_version"})
        or not HEX64.fullmatch(payload["manifest_sha256"])
        or not HEX64.fullmatch(payload["result_proof_sha256"])
        or not HEX64.fullmatch(payload["nonce_hex"])
        or not TOKEN.fullmatch(payload["restore_request_id"])
        or not TOKEN.fullmatch(payload["audience"])
        or not TOKEN.fullmatch(payload["witness_id"])
        or not payload["buyer_id"].strip()
        or not payload["business_unit"].strip()
        or payload["role"] not in ROLES):
        _reject("INVALID_RECEIPT_FIELDS")
    _canonical_time(payload["issued_at_utc"])
    _canonical_time(payload["expires_at_utc"])
    return DOMAIN+json.dumps(
        payload,sort_keys=True,separators=(",",":"),ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")


def _trust_registry(registry:Mapping)->dict:
    if not isinstance(registry,Mapping) or not registry:
        _reject("TRUST_REGISTRY_NOT_PROVISIONED")
    indexed={}
    seen_public_keys=set()
    for witness_id, entry in registry.items():
        if (type(witness_id) is not str or not TOKEN.fullmatch(witness_id)
            or type(entry) is not dict or frozenset(entry)!=TRUST_KEYS):
            _reject("TRUST_REGISTRY_INVALID")
        role=entry.get("role")
        public_hex=entry.get("public_key_hex")
        if (role not in ROLES
            or type(public_hex) is not str
            or not HEX64.fullmatch(public_hex)):
            _reject("TRUST_REGISTRY_INVALID")
        if public_hex in seen_public_keys:
            _reject("DUPLICATE_PUBLIC_KEY_ACROSS_WITNESSES")
        seen_public_keys.add(public_hex)
        indexed[witness_id]=entry
    return indexed


def validate_technical_witnesses(
    *, manifest:dict, result, trust_registry:Mapping,
    witness_receipts:object, expected_restore_request_id:str,
    expected_audience:str, as_of_utc:datetime,
)->dict:
    """Return local technical witness assessment, NEVER activation permission.

    Caller MUST acquire trust_registry by an independent security/admin flow
    outside the recovery bundle. Never read a purported trusted public key
    from capture.complete.json or a sibling file.
    """
    if (type(expected_restore_request_id) is not str
        or not TOKEN.fullmatch(expected_restore_request_id)
        or type(expected_audience) is not str
        or not TOKEN.fullmatch(expected_audience)
        or type(as_of_utc) is not datetime
        or as_of_utc.tzinfo is None
        or as_of_utc.utcoffset() is None):
        _reject("INVALID_CALLER_CONTEXT")
    now=as_of_utc.astimezone(timezone.utc)
    keys=_trust_registry(trust_registry)
    if not isinstance(witness_receipts,(list,tuple)) or len(witness_receipts)!=2:
        _reject("MISSING_TWO_DISTINCT_WITNESSES")
    if type(manifest) is not dict:
        _reject("MANIFEST_NOT_REVIEWABLE")
    manifest_sha=manifest.get("manifest_sha256")
    if type(manifest_sha) is not str or not HEX64.fullmatch(manifest_sha):
        _reject("MANIFEST_NOT_REVIEWABLE")
    if (type(result.proof_hash) is not str
        or not HEX64.fullmatch(result.proof_hash)):
        _reject("MANIFEST_NOT_REVIEWABLE")

    seen_ids=set()
    seen_roles=set()
    seen_nonces=set()
    for receipt in witness_receipts:
        if (type(receipt) is not dict
            or frozenset(receipt)!={"payload","signature_b64"}):
            _reject("INVALID_RECEIPT_FIELDS")
        payload=receipt["payload"]
        signed_bytes=signing_message(payload)
        witness_id=payload["witness_id"]
        role=payload["role"]
        if witness_id not in keys:
            _reject("UNKNOWN_EXTERNAL_WITNESS_KEY")
        if keys[witness_id]["role"]!=role:
            _reject("WITNESS_ROLE_MISMATCH")
        if witness_id in seen_ids or role in seen_roles:
            _reject("DUPLICATE_ROLE_OR_SIGNER")
        if payload["nonce_hex"] in seen_nonces:
            _reject("DUPLICATE_RECEIPT_NONCE")
        seen_ids.add(witness_id)
        seen_roles.add(role)
        seen_nonces.add(payload["nonce_hex"])
        if (payload["manifest_sha256"]!=manifest_sha
            or payload["result_proof_sha256"]!=result.proof_hash):
            _reject("MANIFEST_OR_FINANCIAL_RECEIPT_REBOUND")
        if (payload["buyer_id"]!=result.buyer_id
            or payload["business_unit"]!=result.business_unit):
            _reject("WRONG_RECOVERY_BUYER_SCOPE")
        if payload["restore_request_id"]!=expected_restore_request_id:
            _reject("RESTORE_REQUEST_REPLAY_OR_MISMATCH")
        if payload["audience"]!=expected_audience:
            _reject("WITNESS_AUDIENCE_MISMATCH")

        issued=_canonical_time(payload["issued_at_utc"])
        expires=_canonical_time(payload["expires_at_utc"])
        if issued>now+timedelta(minutes=5):
            _reject("FUTURE_DATED_WITNESS")
        if now-issued>timedelta(hours=24):
            _reject("STALE_WITNESS")
        if expires<=now:
            _reject("EXPIRED_WITNESS")
        if expires<=issued or expires-issued>timedelta(hours=24):
            _reject("INVALID_WITNESS_LIFETIME")
        signature_b64=receipt["signature_b64"]
        if type(signature_b64) is not str or len(signature_b64)>128:
            _reject("INVALID_SIGNATURE_ENCODING")
        try:
            signature=base64.b64decode(signature_b64,validate=True)
        except (ValueError,binascii.Error):
            _reject("INVALID_SIGNATURE_ENCODING")
        if len(signature)!=64:
            _reject("INVALID_SIGNATURE_ENCODING")
        # cryptography is imported only when the explicit technical witness
        # gate is called. It is not needed for earlier read-only M49/M50 work.
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        try:
            Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(keys[witness_id]["public_key_hex"])
            ).verify(signature,signed_bytes)
        except (InvalidSignature,ValueError) as exc:
            raise ValueError("M51_WITNESS_SIGNATURE_NOT_VALID") from exc

    if seen_roles!=set(ROLES):
        _reject("MISSING_REQUIRED_INDEPENDENT_ROLE")
    return {
        "scope":SCOPE,
        "technical_review_status":"TWO_EXTERNAL_PUBLIC_KEYS_VERIFIED_LOCAL_TECHNICAL_ONLY",
        "technical_witness_count":2,
        "distinct_external_public_key_count":2,
        "required_roles_verified":list(ROLES),
        "manifest_and_scoped_money_referenced_by_both_signers":True,
        "restore_request_id_bound":True,
        "audience_and_expiry_checked":True,
        "receipt_or_private_key_written_to_disk":False,
        "full_customer_restore_activation_authorized":False,
        "real_customer_or_bank_or_carrier_consents_established":False,
        "independent_customer_pilot_approval_gates_still_unmet":18,
        "historical_original_findings_closed":0,
        "not_a_durable_nonce_replay_ledger":True,
    }
