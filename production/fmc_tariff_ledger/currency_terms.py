"""Additional monetary extraction for non-USD tariff currencies."""

from __future__ import annotations

import re

import crawler as base

PREFIX_TO_CURRENCY = {
    "EUR": "EUR", "€": "EUR",
    "GBP": "GBP", "£": "GBP",
    "CAD": "CAD", "C$": "CAD",
    "AUD": "AUD", "A$": "AUD",
    "SGD": "SGD", "S$": "SGD",
    "HKD": "HKD", "HK$": "HKD",
    "JPY": "JPY",
    "CNY": "CNY", "RMB": "CNY", "CN¥": "CNY",
    "INR": "INR", "₹": "INR",
    "AED": "AED",
    "PKR": "PKR",
    "BDT": "BDT",
    "THB": "THB", "฿": "THB",
    "MYR": "MYR", "RM": "MYR",
    "LKR": "LKR",
    "ZAR": "ZAR", "R": "ZAR",
    "MXN": "MXN",
    "BRL": "BRL", "R$": "BRL",
    "KRW": "KRW", "₩": "KRW",
    "TWD": "TWD", "NT$": "TWD",
    "NZD": "NZD", "NZ$": "NZD",
    "CHF": "CHF",
    "SEK": "SEK",
    "NOK": "NOK",
    "DKK": "DKK",
}

PREFIXES = sorted(PREFIX_TO_CURRENCY, key=len, reverse=True)
PREFIX_ALT = "|".join(re.escape(x) for x in PREFIXES)
AMOUNT = r"(?:\d{1,3}(?:,\d{3})*(?:\.\d{1,4})?|\d+(?:\.\d{1,4})?)"
UNIT = (
    r"(?:/\s*[A-Za-z0-9'\-]+|per\s+(?:calendar\s+)?"
    r"(?:day|hour|container|unit|shipment|bill|document|B/?L|TEU|FEU|ton|"
    r"metric\s+ton|1000\s+kg|CBM))"
)

PREFIX_RE = re.compile(
    rf"(?P<currency>{PREFIX_ALT})\s*(?P<amount>{AMOUNT})(?:\s*(?P<unit>{UNIT}))?",
    re.I,
)
SUFFIX_RE = re.compile(
    rf"(?P<amount>{AMOUNT})\s*(?P<currency>"
    + "|".join(re.escape(x) for x in PREFIX_TO_CURRENCY if len(x) == 3)
    + rf")(?:\s*(?P<unit>{UNIT}))?",
    re.I,
)
RULE_INLINE_RE = re.compile(
    r"(?im)^\s*(?:RULE|ITEM)\s+([A-Z0-9]+(?:\.[A-Z0-9]+)*)\b"
)


def normalize_currency(raw: str) -> str | None:
    raw_clean = raw.strip()
    for token, code in PREFIX_TO_CURRENCY.items():
        if raw_clean.upper() == token.upper():
            return code
    return None


def _matches(block: str):
    spans = set()
    for regex in (PREFIX_RE, SUFFIX_RE):
        for match in regex.finditer(block):
            span = match.span()
            if span in spans:
                continue
            spans.add(span)
            code = normalize_currency(match.group("currency"))
            if not code or code == "USD":
                continue
            yield match, code


def extract_non_usd_terms(text: str, url: str) -> list[base.ExtractedTerm]:
    doc_start, doc_end = base.detect_effective_dates(text)
    source_version = base.detect_source_version(text, url)
    out: list[base.ExtractedTerm] = []
    seen: set[tuple] = set()

    for locator, block in base.split_evidence_blocks(text):
        rule_types = base.classify_rules(block)
        rule_ids = [f"rule:{x}" for x in RULE_INLINE_RE.findall(block)]
        rule_types = list(dict.fromkeys([*rule_types, *rule_ids]))
        if not rule_types:
            continue

        local_start, local_end = base.detect_effective_dates(block)
        effective_from = local_start or doc_start
        effective_to = local_end or doc_end

        for match, currency in _matches(block):
            amount = match.group("amount").replace(",", "")
            unit = (match.group("unit") or "").strip() or None
            for rule_type in rule_types:
                key = (
                    rule_type, amount, currency, unit, effective_from,
                    effective_to, locator, block[:1000],
                )
                if key in seen:
                    continue
                seen.add(key)
                out.append(base.ExtractedTerm(
                    rule_type=rule_type,
                    term_kind="money",
                    amount_value=amount,
                    currency=currency,
                    unit=unit,
                    quantity_value=None,
                    effective_from=effective_from,
                    effective_to=effective_to,
                    source_version=source_version,
                    evidence_locator=locator,
                    evidence_excerpt=block[:4000],
                    confidence=0.92,
                ))

    return out
