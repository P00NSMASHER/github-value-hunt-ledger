"""Strict CSV adapter for normalized Freight Recovery charge rules.

The CSV supplies rule semantics only. Scope, source-document identity/hash, and
whether that document has been verified as controlling authority come from
trusted caller context and cannot be self-asserted by spreadsheet content.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass
from datetime import date

from freight.contracts import canonical_hash
from freight.finding_factory import FIXED, INCLUDED, PER_UNIT, ChargeRule
from freight.input_guard import assert_accepted


REQUIRED_COLUMNS = (
    "charge_code",
    "pricing_model",
    "effective_from",
    "effective_to",
    "fixed_cents",
    "unit_rate_cents",
)
INTEGER_RE = re.compile(r"^(0|[1-9][0-9]*)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class ChargeRuleCSVBatch:
    buyer_id: str
    business_unit: str
    customer_id: str
    carrier_id: str
    currency: str
    authority_document_id: str
    source_document_sha256: str
    verified_controlling_authority: bool
    filename: str
    file_sha256: str
    rules: tuple[ChargeRule, ...]
    adapter_hash: str


def _trusted_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    return value.strip()


def _cell(name: str, value: str | None, row_number: int, *, allow_blank: bool = False) -> str | None:
    if value is None:
        raise ValueError(f"row {row_number}: {name} is missing")
    text = value.strip()
    if not text and allow_blank:
        return None
    if not text:
        raise ValueError(f"row {row_number}: {name} is required")
    return text


def _optional_cents(name: str, value: str | None, row_number: int) -> int | None:
    text = _cell(name, value, row_number, allow_blank=True)
    if text is None:
        return None
    if not INTEGER_RE.fullmatch(text):
        raise ValueError(f"row {row_number}: {name} must be an exact unsigned integer or blank")
    parsed = int(text)
    if parsed > 2**63 - 1:
        raise ValueError(f"row {row_number}: {name} exceeds integer range")
    return parsed


def parse_charge_rule_csv(
    *,
    filename: str,
    data: bytes,
    buyer_id: str,
    business_unit: str,
    customer_id: str,
    carrier_id: str,
    currency: str,
    authority_document_id: str,
    source_document_sha256: str,
    verified_controlling_authority: bool,
) -> ChargeRuleCSVBatch:
    buyer_id = _trusted_text("buyer_id", buyer_id)
    business_unit = _trusted_text("business_unit", business_unit)
    customer_id = _trusted_text("customer_id", customer_id)
    carrier_id = _trusted_text("carrier_id", carrier_id)
    currency = _trusted_text("currency", currency).upper()
    authority_document_id = _trusted_text("authority_document_id", authority_document_id)
    if not CURRENCY_RE.fullmatch(currency):
        raise ValueError("currency must be a three-letter code")
    if not isinstance(source_document_sha256, str) or not SHA256_RE.fullmatch(source_document_sha256):
        raise ValueError("source_document_sha256 must be lowercase SHA-256")
    if type(verified_controlling_authority) is not bool:
        raise ValueError("verified_controlling_authority must be a boolean")

    inspection = assert_accepted(filename, data)
    if inspection.detected_format != "csv":
        raise ValueError("charge rule adapter requires a .csv input")

    text = bytes(data).decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    headers = reader.fieldnames
    if headers is None:
        raise ValueError("CSV header row is required")
    if len(headers) != len(set(headers)):
        raise ValueError("duplicate CSV header")
    if set(headers) != set(REQUIRED_COLUMNS) or len(headers) != len(REQUIRED_COLUMNS):
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        extra = sorted(set(headers) - set(REQUIRED_COLUMNS))
        raise ValueError(
            "CSV schema mismatch; missing=" + ",".join(missing) + "; extra=" + ",".join(extra)
        )

    rules: list[ChargeRule] = []
    seen_rule_hashes: set[str] = set()
    for row in reader:
        row_number = reader.line_num
        if None in row:
            raise ValueError(f"row {row_number}: unexpected extra CSV cells")
        if all(value is None or not str(value).strip() for value in row.values()):
            continue
        if any(value is None for value in row.values()):
            raise ValueError(f"row {row_number}: missing CSV cell")

        charge_code = _cell("charge_code", row["charge_code"], row_number)
        pricing_model = _cell("pricing_model", row["pricing_model"], row_number)
        effective_from = _cell("effective_from", row["effective_from"], row_number)
        effective_to = _cell("effective_to", row["effective_to"], row_number, allow_blank=True)
        fixed_cents = _optional_cents("fixed_cents", row["fixed_cents"], row_number)
        unit_rate_cents = _optional_cents("unit_rate_cents", row["unit_rate_cents"], row_number)
        assert charge_code is not None and pricing_model is not None and effective_from is not None
        charge_code = charge_code.upper()
        pricing_model = pricing_model.upper()

        try:
            start = date.fromisoformat(effective_from)
        except ValueError as exc:
            raise ValueError(f"row {row_number}: effective_from must be YYYY-MM-DD") from exc
        if effective_to is not None:
            try:
                end = date.fromisoformat(effective_to)
            except ValueError as exc:
                raise ValueError(f"row {row_number}: effective_to must be YYYY-MM-DD or blank") from exc
            if end < start:
                raise ValueError(f"row {row_number}: effective_to cannot precede effective_from")

        if pricing_model == INCLUDED:
            if fixed_cents is not None or unit_rate_cents is not None:
                raise ValueError(f"row {row_number}: INCLUDED requires blank fixed_cents and unit_rate_cents")
        elif pricing_model == FIXED:
            if fixed_cents is None or unit_rate_cents is not None:
                raise ValueError(f"row {row_number}: FIXED requires fixed_cents only")
        elif pricing_model == PER_UNIT:
            if unit_rate_cents is None or fixed_cents is not None:
                raise ValueError(f"row {row_number}: PER_UNIT requires unit_rate_cents only")
        else:
            raise ValueError(f"row {row_number}: unsupported pricing_model")

        rule = ChargeRule(
            buyer_id=buyer_id,
            business_unit=business_unit,
            customer_id=customer_id,
            carrier_id=carrier_id,
            currency=currency,
            authority_document_id=authority_document_id,
            charge_code=charge_code,
            pricing_model=pricing_model,
            effective_from=effective_from,
            effective_to=effective_to,
            document_source_hash=source_document_sha256,
            verified_controlling_authority=verified_controlling_authority,
            fixed_cents=fixed_cents,
            unit_rate_cents=unit_rate_cents,
        )
        digest = rule.rule_hash
        if digest in seen_rule_hashes:
            raise ValueError(f"row {row_number}: duplicate normalized rule")
        seen_rule_hashes.add(digest)
        rules.append(rule)

    if not rules:
        raise ValueError("CSV must contain at least one charge rule row")

    rules_tuple = tuple(rules)
    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "customer_id": customer_id,
        "carrier_id": carrier_id,
        "currency": currency,
        "authority_document_id": authority_document_id,
        "source_document_sha256": source_document_sha256,
        "verified_controlling_authority": verified_controlling_authority,
        "filename": filename,
        "file_sha256": inspection.sha256,
        "rules": [asdict(rule) for rule in rules_tuple],
    }
    return ChargeRuleCSVBatch(
        buyer_id=buyer_id,
        business_unit=business_unit,
        customer_id=customer_id,
        carrier_id=carrier_id,
        currency=currency,
        authority_document_id=authority_document_id,
        source_document_sha256=source_document_sha256,
        verified_controlling_authority=verified_controlling_authority,
        filename=filename,
        file_sha256=inspection.sha256,
        rules=rules_tuple,
        adapter_hash=canonical_hash(body),
    )
