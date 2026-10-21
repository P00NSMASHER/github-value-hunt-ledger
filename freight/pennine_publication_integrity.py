"""Fail-closed identity consistency for public Pennine invoice republications.

A repeated published invoice is not a second payment. However, changing the
payment annotation on the same economic invoice makes first-row-wins
reconciliation unsafe. No source identifiers enter errors or returned output.
"""
from __future__ import annotations

from collections.abc import Mapping


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
