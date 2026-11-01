"""Independently executed synthetic Ed25519 admission service for Phase 5G.

This is a *separately executable process* using its own restricted PostgreSQL
login in DISPOSABLE CI only. The existing Floot application is NOT reconfigured.
Private keys belong to the test issuer, not the verifier, and are never stored.

Security-critical scope: CONTRACT documents only. Other kinds require real
carrier/customer/payment authority and must stay unadmitted through this
reference entry point until corresponding independent source adapters exist.

A caller with owner/table INSERT access can still bypass this service.
Do not expose or run this service using the privileged Floot database URL.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from contextlib import closing
from dataclasses import dataclass
import base64
import json
import re

import psycopg
from psycopg.types.json import Jsonb
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from freight.phase5.phase5c_oracle import signed_bytes


class AdmissionRejected(ValueError):
    pass


def _reject(message: str) -> None:
    raise AdmissionRejected(message)


def _utc(value: str | datetime) -> datetime:
    try:
        t=value if isinstance(value,datetime) else datetime.fromisoformat(
            value.replace("Z","+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:
            raise ValueError("naive")
        return t.astimezone(timezone.utc)
    except (ValueError,AttributeError) as ex:
        raise AdmissionRejected("INVALID_SIGNED_EVENT_TIMESTAMP") from ex


@dataclass(frozen=True)
class PinnedIssuer:
    issuer_key_id: str
    tenant_id: str
    role: str
    public_key_pem: str


@dataclass(frozen=True)
class AdmissionOutcome:
    record_id: str
    replay: bool
    scope: str = "DISPOSABLE_RESTRICTED_VERIFIER_SIGNED_SYNTHETIC_CONTRACT"


def admit_fictional_contract(
    conn: psycopg.Connection,
    payload: dict,
    signature_b64: str,
    trusted_issuers: dict[str,PinnedIssuer],
) -> AdmissionOutcome:
    """Verify trust pinned OUTSIDE the database before using its INSERT role.

    Never use application-declared 'verified' booleans, arbitrary session
    variables, or table-local HMAC as an authority proof.
    """
    if type(payload) is not dict or type(signature_b64) is not str:
        _reject("MALFORMED_FINANCIAL_DOCUMENT")
    mandatory={
        "tenantId","caseId","recordId","customerId","invoiceId","kind",
        "economicKey","referenceId","amountCents","feeBps","currency",
        "occurredAt","sourceHash","issuerKeyId","contractVersion","providerEventId",
    }
    if set(payload)!=mandatory or payload.get("kind")!="CONTRACT":
        _reject("UNSUPPORTED_FINANCIAL_DOCUMENT_KIND")
    for name in ("tenantId","caseId","recordId","customerId","invoiceId",
                 "economicKey","issuerKeyId"):
        if type(payload[name]) is not str or not payload[name].startswith("SIM-"):
            _reject("INVALID_SYNTHETIC_SCOPE_"+name.upper())
    if payload["currency"]!="USD" or type(payload["feeBps"]) is not int or not 1<=payload["feeBps"]<=9999:
        _reject("INVALID_CONTRACT_CURRENCY_OR_BPS")
    if type(payload["amountCents"]) is not int or payload["amountCents"]!=0:
        _reject("INVALID_CONTRACT_AMOUNT")
    if payload["referenceId"] is not None or payload["providerEventId"] is not None:
        _reject("CONTRACT_CANNOT_CLAIM_PAYMENT_EVENT")
    if type(payload["contractVersion"]) is not str or not payload["contractVersion"].startswith("SIM-"):
        _reject("INVALID_CONTRACT_VERSION")
    if type(payload["sourceHash"]) is not str or re.fullmatch("[0-9a-f]{64}",payload["sourceHash"]) is None:
        _reject("INVALID_SOURCE_HASH")
    occurred=_utc(payload["occurredAt"])
    pinned=trusted_issuers.get(payload["issuerKeyId"])
    if (pinned is None or pinned.tenant_id!=payload["tenantId"] or
        pinned.role!="BUYER"):
        _reject("UNKNOWN_OR_WRONG_SCOPE_INDEPENDENT_TRUST_ROOT")
    try:
        pub=load_pem_public_key(pinned.public_key_pem.encode())
        if not isinstance(pub,Ed25519PublicKey):
            _reject("NON_ED25519_INDEPENDENT_SIGNER")
        pub.verify(base64.b64decode(signature_b64,validate=True),signed_bytes(payload))
    except (ValueError,TypeError,Exception) as ex:
        if isinstance(ex,AdmissionRejected):
            raise
        raise AdmissionRejected("INVALID_ED25519_FINANCIAL_SIGNATURE") from ex

    # This executable process holds the verifier-only DB credential. Its
    # independent pinned issuer registry is not obtained from this DB.
    with conn.transaction():
        principal=conn.execute("SELECT current_user").fetchone()[0]
        if principal!="retally_p5g_verifier_login":
            _reject("UNAUTHORIZED_DB_VERIFIER_PRINCIPAL")
        db=conn.execute("SELECT current_database()").fetchone()[0]
        if db!="retally_phase5_ci":
            _reject("NON_DISPOSABLE_FINANCIAL_CONNECTION")
        case=conn.execute("""SELECT customer_id,invoice_id,currency FROM phase5c_qa.cases
             WHERE tenant_id=%s AND case_id=%s""",
             (payload["tenantId"],payload["caseId"])).fetchone()
        if case is None or tuple(case)!=(payload["customerId"],payload["invoiceId"],payload["currency"]):
            _reject("INDEPENDENT_CASE_SCOPE_MISMATCH")
        authority=conn.execute("""SELECT role,public_key_pem,enabled_from,
                   expires_at,revoked_at
                   FROM phase5c_qa.issuer_keys
                   WHERE tenant_id=%s AND key_id=%s""",
                   (payload["tenantId"],payload["issuerKeyId"])).fetchone()
        if authority is None or authority[0]!="BUYER" or authority[1]!=pinned.public_key_pem:
            _reject("DATABASE_ISSUER_DIFFERS_FROM_PINNED_AUTHORITY")
        _,_,from_at,expires_at,revoked_at=authority
        now=datetime.now(timezone.utc)
        if (occurred < _utc(from_at) or occurred >= _utc(expires_at)
           or now>=_utc(expires_at) or
           (revoked_at is not None and now>=_utc(revoked_at))):
            _reject("REVOKED_OR_EXPIRED_FINANCIAL_SIGNER")
        # One lock serializes exact and conflicting retries from concurrent
        # verifier workers, without allowing direct writes by the application.
        token=f"{payload['tenantId']}:{payload['recordId']}"
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,3589))",(token,))
        existing=conn.execute("""SELECT body,signature_b64 FROM phase5c_qa.documents
                     WHERE tenant_id=%s AND record_id=%s""",
                     (payload["tenantId"],payload["recordId"])).fetchone()
        if existing is not None:
            if signed_bytes(existing[0])!=signed_bytes(payload) or existing[1]!=signature_b64:
                _reject("CONFLICTING_SIGNED_DOCUMENT_REPLAY")
            return AdmissionOutcome(payload["recordId"],True)
        # Trigger preserves existing economic guards and parent-case locking;
        # its SECURITY DEFINER runs as table owner ONLY in disposable CI.
        conn.execute("""INSERT INTO phase5c_qa.documents
            (tenant_id,case_id,record_id,kind,economic_key,reference_id,
            amount_cents,fee_bps,currency,occurred_at,source_sha256,
            issuer_key_id,body,signature_b64)
            VALUES(%s,%s,%s,'CONTRACT',%s,NULL,0,%s,%s,%s,%s,%s,%s,%s)""",
            (payload["tenantId"],payload["caseId"],payload["recordId"],
             payload["economicKey"],payload["feeBps"],payload["currency"],
             occurred,payload["sourceHash"],payload["issuerKeyId"],
             Jsonb(payload),signature_b64))
        return AdmissionOutcome(payload["recordId"],False)
