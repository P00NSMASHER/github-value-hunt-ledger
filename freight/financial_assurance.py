"""Exact-money and source-attestation primitives for RETALLY's financial boundary.

Source attestations prove only possession of a separately configured issuer key.
They do NOT prove customer identity, bank clearing, legal consent, or release
authority. No credentials, bank connections, payment rails, or signing services
are provisioned here. Without a trusted externally approved issuer: FAIL CLOSED.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hmac
import json
import re
from hashlib import sha256
from typing import Mapping

from freight.contracts import canonical_hash

MAX_MINOR = 2**63 - 1
# Only explicitly reviewed currency precision is supported. Other currencies
# must go to REVIEW, never silently assume US-style cents or convert at spot FX.
CURRENCY_MINOR_DIGITS = {
    "USD": 2, "EUR": 2, "GBP": 2, "CAD": 2, "AUD": 2,
    "NZD": 2, "CHF": 2, "SGD": 2, "HKD": 2,
    "JPY": 0, "KWD": 3,
}
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z", re.ASCII)


def require_exact_cents(name: str, value: int, *, positive: bool = False) -> int:
    minimum = 1 if positive else 0
    if type(value) is not int or not minimum <= value <= MAX_MINOR:
        if positive:
            raise ValueError(f"{name} must be positive integer cents within SQLite range")
        raise ValueError(f"{name} must be nonnegative exact integer cents within SQLite range")
    return value


def require_currency(currency: str) -> tuple[str, int]:
    if not isinstance(currency, str):
        raise ValueError("currency code must be a string")
    code = currency.upper()
    if not re.fullmatch(r"[A-Z]{3}", code, re.ASCII) or code not in CURRENCY_MINOR_DIGITS:
        raise ValueError("unsupported currency or undefined minor-unit precision")
    return code, CURRENCY_MINOR_DIGITS[code]


def require_cent_currency(currency: str) -> str:
    code, exponent = require_currency(currency)
    if exponent != 2:
        raise ValueError("cent-based financial engine does not support this currency's minor units")
    return code


@dataclass(frozen=True)
class ExactMoney:
    currency: str
    minor: int
    exponent: int


def parse_major_exact(value: str, currency: str, *, allow_negative: bool = False) -> ExactMoney:
    code, exponent = require_currency(currency)
    if not isinstance(value, str) or not value.isascii() or not value:
        raise ValueError("money must be exact, nonblank ASCII major-unit text")
    regex = (
        r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1," + str(exponent) + r"})?\Z"
        if exponent else r"-?(?:0|[1-9][0-9]*)\Z"
    )
    if re.fullmatch(regex, value, re.ASCII) is None:
        raise ValueError("invalid money format, fraction, or precision")
    if value.startswith("-") and not allow_negative:
        raise ValueError("negative amount requires an explicit signed-money scope")
    body = value[1:] if value.startswith("-") else value
    major, _, frac = body.partition(".")
    minor = int(major) * (10**exponent) + int(frac.ljust(exponent, "0") or "0")
    if minor > MAX_MINOR:
        raise ValueError("amount exceeds supported minor-unit integer range")
    return ExactMoney(code, -minor if value.startswith("-") else minor, exponent)


def canonical_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp is required")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        when = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("timestamp must be timezone-aware ISO-8601") from exc
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware ISO-8601")
    return when.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class SourceAttestation:
    issuer_id: str
    purpose: str
    scope_hash: str
    subject_sha256: str
    issued_at: str
    mac_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.issuer_id, str) or _NAME.fullmatch(self.issuer_id) is None:
            raise ValueError("issuer identity must be canonical")
        if self.purpose not in {"APPROVAL", "FEE_TERMS", "BANK_CLEARED", "CARRIER_CREDIT"}:
            raise ValueError("unsupported financial attestation purpose")
        for name in ("scope_hash", "subject_sha256", "mac_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or _SHA.fullmatch(value) is None:
                raise ValueError(f"{name} must be lowercase SHA-256")
        object.__setattr__(self, "issued_at", canonical_timestamp(self.issued_at))


def receipt_message(receipt: SourceAttestation) -> bytes:
    """Stable tagged signing bytes; no secret in the receipt or artifact."""
    data = {
        "schema": "retally-financial-evidence-v1",
        "issuer_id": receipt.issuer_id,
        "purpose": receipt.purpose,
        "scope_hash": receipt.scope_hash,
        "subject_sha256": receipt.subject_sha256,
        "issued_at": receipt.issued_at,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def verify_source_attestation(
    receipt: SourceAttestation,
    *,
    trusted_issuers: Mapping[str, bytes] | None,
    purpose: str,
    scope_hash: str,
    subject_sha256: str,
) -> None:
    """Fail closed without externally provisioned verifier key and exact binding.

    This does not establish actual human identity or a bank/provider payment.
    Genuine provenance needs an independently authorized issuer, its protected
    keys and matching original source evidence outside this source module.
    """
    if not isinstance(receipt, SourceAttestation):
        raise ValueError("typed source attestation required")
    if receipt.purpose != purpose or receipt.scope_hash != scope_hash or receipt.subject_sha256 != subject_sha256:
        raise ValueError("attestation purpose, scope, or subject mismatch")
    key = trusted_issuers.get(receipt.issuer_id) if trusted_issuers is not None else None
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("untrusted or unconfigured financial issuer")
    expected = hmac.new(key, receipt_message(receipt), sha256).hexdigest()
    if not hmac.compare_digest(expected, receipt.mac_sha256):
        raise ValueError("financial source attestation MAC mismatch")


@dataclass(frozen=True)
class FeeTerms:
    buyer_id: str
    business_unit: str
    currency: str
    rate_bps: int
    cap_cents: int
    signed_terms_sha256: str

    def __post_init__(self) -> None:
        if not self.buyer_id or not self.business_unit:
            raise ValueError("fee terms require exact buyer and business-unit scope")
        require_cent_currency(self.currency)
        if type(self.rate_bps) is not int or not 0 <= self.rate_bps <= 10000:
            raise ValueError("fee rate must be 0-10000 exact basis points")
        require_exact_cents("fee cap", self.cap_cents)
        if not isinstance(self.signed_terms_sha256, str) or _SHA.fullmatch(self.signed_terms_sha256) is None:
            raise ValueError("fee terms must refer to a fixed source hash")

    @property
    def terms_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class FeeQuote:
    currency: str
    eligible_cents: int
    estimated_fee_cents: int
    billable_cents: int
    terms_hash: str
    blockers: tuple[str, ...]
    quote_hash: str


def quote_contingent_fee(
    terms: FeeTerms,
    *,
    net_declared_cents: int,
    reversed_cents: int = 0,
    incumbent_cents: int = 0,
    disputed_cents: int = 0,
    disqualified: bool = False,
    terms_attestation: SourceAttestation | None = None,
    trusted_issuers: Mapping[str, bytes] | None = None,
) -> FeeQuote:
    """Review-only fee estimate, never a bill/payment instruction.

    An attested terms hash still does not prove signed buyer consent or bank
    settlement; actual fee billability remains zero pending separate gates.
    """
    if not isinstance(terms, FeeTerms):
        raise ValueError("fee terms must be typed")
    amount = require_exact_cents("net declared", net_declared_cents)
    exclusions = tuple(require_exact_cents(n, v) for n, v in (
        ("reversed", reversed_cents),
        ("incumbent", incumbent_cents),
        ("disputed", disputed_cents),
    ))
    if sum(exclusions) > amount:
        raise ValueError("excluded or reversed amounts exceed declared gross")
    if type(disqualified) is not bool:
        raise ValueError("fee disqualified must be boolean")
    blockers = ["NO_AUTHENTICATED_CUSTOMER_SETTLEMENT", "NO_CUSTOMER_FEE_RELEASE_AUTHORITY"]
    if terms_attestation is None:
        blockers.append("NO_AUTHENTICATED_FEE_TERMS")
    else:
        verify_source_attestation(
            terms_attestation, trusted_issuers=trusted_issuers,
            purpose="FEE_TERMS",
            scope_hash=sha256((terms.buyer_id + "|" + terms.business_unit).encode()).hexdigest(),
            subject_sha256=terms.terms_hash,
        )
    if disqualified:
        blockers.append("RECOVERY_FEE_DISQUALIFIED")
    eligible = 0 if disqualified else amount - sum(exclusions)
    estimated = min((eligible * terms.rate_bps) // 10000, terms.cap_cents)
    content = {
        "schema": 1, "terms": terms.terms_hash, "currency": terms.currency,
        "declared": amount, "exclusions": exclusions, "disqualified": disqualified,
        "eligible": eligible, "estimated": estimated, "billable": 0,
        "blockers": sorted(blockers),
    }
    return FeeQuote(
        terms.currency, eligible, estimated, 0, terms.terms_hash,
        tuple(sorted(blockers)), canonical_hash(content),
    )
