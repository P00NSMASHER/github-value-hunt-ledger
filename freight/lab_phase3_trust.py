"""External-verifier interface with Ed25519 asymmetric evidence and role policy.

Keys must be provisioned outside RETALLY labs. Passing verification authenticates
only possession of the configured private key, NOT the truth of any financial
claim, bank transfer, signed engagement, or the actual issuer's authority.
Tests use ephemeral, fictitious issuer keys. No secret is committed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import base64
import json
from typing import Sequence

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # Fail closed. Do not treat a missing crypto dependency as PASS.
    InvalidSignature = None
    Ed25519PublicKey = None

ROLE_BY_KIND = {
    "BUYER_SOURCE_ENTITLEMENT":"BUYER",
    "FEE_CONTRACT":"BUYER",
    "CARRIER_CREDIT":"CARRIER",
    "CARRIER_REVERSAL":"CARRIER",
    "CUSTOMER_POSTED_CREDIT":"BUYER_ACCOUNTING",
    "FEE_REMITTANCE":"PAYMENT_PROCESSOR",
    "FEE_REFUND":"PAYMENT_PROCESSOR",
}

class TrustRejected(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _utc(s: str) -> datetime:
    if type(s) is not str:
        raise TrustRejected("INVALID_TIMESTAMP")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as ex:
        raise TrustRejected("INVALID_TIMESTAMP") from ex
    if d.tzinfo is None or d.utcoffset() is None:
        raise TrustRejected("NAIVE_TIMESTAMP")
    return d.astimezone(timezone.utc)


def canonical_bytes(v: object) -> bytes:
    try:
        return json.dumps(v,sort_keys=True,separators=(",", ":"),allow_nan=False,
                          ensure_ascii=False).encode("utf8")
    except (TypeError,ValueError,OverflowError) as ex:
        raise TrustRejected("INVALID_CANONICAL_EVIDENCE") from ex


@dataclass(frozen=True)
class TrustRoot:
    issuer: str
    key_id: str
    role: str
    tenant_id: str
    public_key_b64: str
    enabled_from: str
    disabled_at: str | None = None


@dataclass(frozen=True)
class SignedRecord:
    record_id: str
    kind: str
    issuer: str
    key_id: str
    tenant_id: str
    currency: str
    source_sha256: str
    amount_cents: int
    occurred_at: str
    signature_b64: str

    def signed_body(self) -> dict:
        return {"schema":1,"record_id":self.record_id,"kind":self.kind,
                "issuer":self.issuer,"key_id":self.key_id,
                "tenant_id":self.tenant_id,"currency":self.currency,
                "source_sha256":self.source_sha256,"amount_cents":self.amount_cents,
                "occurred_at":self.occurred_at}


class ExternalTrustGateway:
    def __init__(self, roots: Sequence[TrustRoot], *, as_of: str):
        self.as_of = _utc(as_of)
        self.roots = {}
        for root in roots:
            key = (root.issuer,root.key_id)
            if key in self.roots:
                raise TrustRejected("DUPLICATE_TRUST_ROOT")
            if root.role not in ROLE_BY_KIND.values() or not root.tenant_id:
                raise TrustRejected("INVALID_TRUST_ROLE_OR_SCOPE")
            begin = _utc(root.enabled_from)
            if root.disabled_at is not None and _utc(root.disabled_at) <= begin:
                raise TrustRejected("INVALID_TRUST_VALIDITY")
            try:
                raw=base64.b64decode(root.public_key_b64,validate=True)
            except (ValueError,base64.binascii.Error) as ex:
                raise TrustRejected("INVALID_PUBLIC_KEY") from ex
            if len(raw)!=32:
                raise TrustRejected("INVALID_PUBLIC_KEY")
            self.roots[key]=root

    def admit(self, records: Sequence[SignedRecord], *, tenant_id: str,
              required_kinds: frozenset[str] = frozenset()) -> dict:
        if Ed25519PublicKey is None or InvalidSignature is None:
            raise TrustRejected("CRYPTO_PROVIDER_UNAVAILABLE")
        if not tenant_id or not records:
            raise TrustRejected("MISSING_ENTITLEMENT")
        seen=set();accepted=[];roles=set()
        for record in records:
            if not record.record_id or record.record_id in seen:
                raise TrustRejected("DUPLICATE_OR_MISSING_RECORD")
            seen.add(record.record_id)
            role=ROLE_BY_KIND.get(record.kind)
            if role is None:
                raise TrustRejected("UNSUPPORTED_EVIDENCE_KIND")
            root=self.roots.get((record.issuer,record.key_id))
            if root is None or root.role!=role or root.tenant_id!=tenant_id or record.tenant_id!=tenant_id:
                raise TrustRejected("WRONG_ISSUER_OR_TENANT")
            moment=_utc(record.occurred_at)
            if not _utc(root.enabled_from) <= moment <= self.as_of:
                raise TrustRejected("OUTSIDE_SIGNER_WINDOW")
            if root.disabled_at is not None and moment>=_utc(root.disabled_at):
                raise TrustRejected("REVOKED_SIGNER")
            if type(record.amount_cents) is not int or record.amount_cents < 0 or record.amount_cents > 2**63-1:
                raise TrustRejected("INVALID_EVIDENCE_AMOUNT")
            if (type(record.currency) is not str or len(record.currency)!=3
                    or not record.currency.isalpha() or not record.currency.isupper()):
                raise TrustRejected("INVALID_EVIDENCE_CURRENCY")
            if (len(record.source_sha256)!=64 or any(ch not in '0123456789abcdef' for ch in record.source_sha256)):
                raise TrustRejected("INVALID_EVIDENCE_HASH")
            try:
                sig=base64.b64decode(record.signature_b64,validate=True)
                pub=base64.b64decode(root.public_key_b64,validate=True)
                Ed25519PublicKey.from_public_bytes(pub).verify(sig,canonical_bytes(record.signed_body()))
            except (ValueError,base64.binascii.Error, InvalidSignature) as ex:
                raise TrustRejected("INVALID_SIGNATURE") from ex
            roles.add(record.kind)
            accepted.append({"record_id":record.record_id,"kind":record.kind,
                             "issuer":record.issuer,"source_sha256":record.source_sha256,
                             "document_hash":sha256(canonical_bytes(record.signed_body())).hexdigest()})
        if not required_kinds.issubset(roles):
            raise TrustRejected("MISSING_REQUIRED_SIGNED_SOURCE")
        body={"scope":"PUBLIC_KEY_CRYPTOGRAPHY_SIMULATED_ISSUERS",
              "tenant_id":tenant_id,"records":accepted,
              "actual_buyer_bank_carrier_authority_proven":False}
        return {**body,"receipt_sha256":sha256(canonical_bytes(body)).hexdigest()}
