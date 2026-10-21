"""Fail-closed identity consistency for public Pennine invoice republications.

A repeated published invoice is not a second payment. However, changing the
payment annotation on the same economic invoice makes first-row-wins
reconciliation unsafe. No source identifiers enter errors or returned output.
"""
from __future__ import annotations

from collections.abc import Mapping
import unicodedata


def _annotation(record: Mapping[str, object]) -> tuple[str, str, str, str]:
    """Compare evidence semantics without changing stored published source rows."""
    return (
        str(record["payment number"]).strip(),
        str(record["payment date"]).strip(),
        str(record["payment currency"]).strip().upper(),
        " ".join(str(record["payment status name"]).split()).casefold(),
    )


def require_matching_payment_annotations(
    first: Mapping[str, object], republished: Mapping[str, object]
) -> None:
    """Reject conflicting republications before any invoice/payment pairing."""
    if _annotation(first) != _annotation(republished):
        raise ValueError(
            "REPUBLICATION_PAYMENT_ANNOTATION_CONFLICT: "
            "same economic invoice has conflicting publisher payment evidence"
        )


def require_canonical_source_identity(
    value: str, *, allow_empty: bool = False, raw_value: str | None = None,
) -> None:
    """Reject Unicode and delimiter aliases before source identity keying.

    Validate original CSV cell bytes as decoded text *before* stripping normal
    display whitespace: Python's strip removes trailing U+001F and could
    otherwise hide a collision with an unrelated clean invoice reference.
    """
    if (
        (raw_value is not None and (
            type(raw_value) is not str
            or unicodedata.normalize("NFC", raw_value) != raw_value
            or any(unicodedata.category(char).startswith("C") for char in raw_value)
        ))
        or type(value) is not str
        or (not value and not allow_empty)
        or value != value.strip()
        or unicodedata.normalize("NFC", value) != value
        or any(unicodedata.category(char).startswith("C") for char in value)
    ):
        raise ValueError("NONCANONICAL_PUBLIC_SOURCE_IDENTITY")


def require_stable_invoice_economics(
    first: Mapping[str, object], subsequent: Mapping[str, object], *,
    amount_field: str,
) -> None:
    """Hold reused supplier/invoice keys with competing issue dates or amounts.

    A legal correction or recycled invoice number needs external adjudication:
    it must not be silently classified as a second unique invoice or payment.
    """
    if (
        type(first[amount_field]) is not int
        or type(subsequent[amount_field]) is not int
        or type(first["invoice date"]) is not str
        or type(subsequent["invoice date"]) is not str
    ):
        raise ValueError("PUBLIC_INVOICE_ECONOMICS_INVALID")
    if (
        first["invoice date"] != subsequent["invoice date"]
        or first[amount_field] != subsequent[amount_field]
    ):
        raise ValueError(
            "INVOICE_ECONOMIC_IDENTITY_CONFLICT: "
            "supplier/invoice reference has competing published amounts or dates"
        )
