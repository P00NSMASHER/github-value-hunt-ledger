"""Read-only *same-source* Pennine real-record integration verification.

This is a licensed public disclosure census for GENERAL ACCOUNTING schema
interoperability, never a freight-accuracy benchmark or bank settlement record.
Raw source rows, vendor identities and payment identifiers are not logged or
committed. Only a bounded, pinned, ephemeral CI replay is permitted.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import csv
import io
import re

from freight.pennine_publication_integrity import (
    require_canonical_source_identity,
    require_matching_payment_annotations,
    require_stable_invoice_economics,
)
from freight.scoped_reconciliation import ScopedTxn, reconcile_scoped
from recoveryworks.reconciliation_kernel import ReconTxn, parse_amount_to_minor

ROOT = "https://www.penninecare.nhs.uk"
SOURCES = {
    "2026-04": ("5855/277", "314cd0c021f137b43b94e81bb93f26aece5b3b0a021e99c42d43546a640c3d90", 67),
    "2026-05": ("5874/277", "5957ead9c23d57039e267dc18076c7b8d711a14b97cbea6d9a9ff0629aeb5028", 53),
    "2026-06": ("5910/277", "318aeeedbf55d05bcffce5076ac893a84bdb6ebe5e7c851bb3f3c45dbbdea8fc", 50),
    "2026-07": ("5920/277", "ecb986bd0e33cf402f7cb86ff68bc91368d18a5dfc39410e4e2019c045c3de15", 103),
    "2026-08": ("5941/277", "4153ccbbbe27307afddba1d6651bfd9db8a774cc84e4fd23d62b3a2d1059d796", 41),
}
MAX_CSV_BYTES = 250_000
AMOUNT_RE = re.compile(r"^-?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?$")
REQUIRED = ("supplier number", "invoice number", "invoice date", "invoice amount",
            "payment number", "payment date", "payment currency", "payment status name")


class _NoCrossOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme != "https" or target.hostname != "www.penninecare.nhs.uk":
            raise ValueError("public disclosure redirect left approved HTTPS origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_pinned_month(month: str) -> bytes:
    if month not in SOURCES:
        raise ValueError("unapproved public month")
    route, expected, _ = SOURCES[month]
    url = ROOT + "/download_file/" + route
    with build_opener(_NoCrossOriginRedirect()).open(
        Request(url, headers={"User-Agent": "RETALLY-public-research-accounting-replay/1.0"}),
        timeout=30,
    ) as response:
        actual = urlparse(response.geturl())
        if actual.scheme != "https" or actual.hostname != "www.penninecare.nhs.uk":
            raise ValueError("public disclosure escaped approved HTTPS origin")
        raw = response.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES or sha256(raw).hexdigest() != expected:
        raise ValueError("public disclosure source bytes changed; human reapproval required")
    return raw


def _cents(s: str) -> int:
    value = s.strip()
    if not AMOUNT_RE.fullmatch(value):
        raise ValueError("malformed public invoice currency")
    return parse_amount_to_minor(value.replace(",", ""), 2)


def _date(s: str) -> str:
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError as exc:
        raise ValueError("unexpected public record date") from exc


def decode_month(raw: bytes, month: str) -> tuple[dict, ...]:
    if month not in SOURCES:
        raise ValueError("unapproved month")
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    heading = None
    parsed = []
    for fields in reader:
        norm = [re.sub(r"\s+", " ", x.strip().lower()) for x in fields]
        if heading is None:
            if all(x in norm for x in REQUIRED):
                heading = {key: norm.index(key) for key in REQUIRED}
            continue
        if not fields or not any(f.strip() for f in fields):
            continue
        if max(heading.values()) >= len(fields):
            raise ValueError("truncated public CSV record")
        record = {key: fields[index].strip() for key, index in heading.items()}
        if not record["invoice number"] and not record["payment number"]:
            continue
        for key in ("supplier number", "invoice number", "payment number"):
            if not record[key]:
                raise ValueError("missing publicly disclosed source identity")
            require_canonical_source_identity(record[key])
        if record["payment currency"].upper() != "GBP":
            raise ValueError("unexpected public currency")
        record["invoice date"] = _date(record["invoice date"])
        record["payment date"] = _date(record["payment date"])
        record["invoice amount minor"] = _cents(record["invoice amount"])
        parsed.append(record)
    if heading is None:
        raise ValueError("required original disclosure headers missing")
    if not parsed:
        raise ValueError("empty public invoice disclosure")
    return tuple(parsed)


def _anon(parts: tuple[str, ...]) -> str:
    return sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]


def run_public_census_replay() -> dict:
    rows: list[dict] = []
    month_counts = {}
    for month in SOURCES:
        month_rows = decode_month(read_pinned_month(month), month)
        if len(month_rows) != SOURCES[month][2]:
            raise ValueError("published original month row count drift")
        month_counts[month] = len(month_rows)
        rows.extend(month_rows)
    identity: dict[tuple[str, str, str, int], dict] = {}
    supplier_invoice_first: dict[tuple[str, str], dict] = {}
    for row in rows:
        supplier_invoice = (row["supplier number"], row["invoice number"])
        if supplier_invoice in supplier_invoice_first:
            require_stable_invoice_economics(
                supplier_invoice_first[supplier_invoice], row,
                amount_field="invoice amount minor",
            )
        else:
            supplier_invoice_first[supplier_invoice] = row
        key = (row["supplier number"], row["invoice number"],
               row["invoice date"], row["invoice amount minor"])
        if key in identity:
            # Repeated disclosures are not a second payment, but silently
            # choosing the first conflicting annotation is also invalid.
            require_matching_payment_annotations(identity[key], row)
            continue
        identity[key] = row
    invoices: list[ScopedTxn] = []
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for key, row in identity.items():
        supplier = row["supplier number"]
        payment_key = (supplier, row["payment number"], row["payment date"], "GBP")
        groups[payment_key].append(row)
        amount_minor = row["invoice amount minor"]
        amount_text = ("-" if amount_minor < 0 else "") + str(abs(amount_minor)//100) + "." + f"{abs(amount_minor)%100:02d}"
        invoices.append(ScopedTxn(
            ReconTxn("original:" + _anon(tuple(str(x) for x in key)),
                     amount_text, row["payment date"], "GBP", row["payment number"]),
            buyer_id="PUBLIC_NHS_RESEARCH", business_unit="PUBLIC_FINANCE",
            counterparty_id=supplier, origin="ORIGINAL_INVOICE",
        ))
    declarations: list[ScopedTxn] = []
    for key, group in groups.items():
        supplier, ref, paid_at, curr = key
        aggregate_minor = sum(x["invoice amount minor"] for x in group)
        # Convert through integer formatting, never binary float.
        amount_str = ("-" if aggregate_minor < 0 else "") + str(abs(aggregate_minor)//100) + "." + f"{abs(aggregate_minor)%100:02d}"
        declarations.append(ScopedTxn(
            ReconTxn("declared:" + _anon(key), amount_str, paid_at, curr, ref),
            buyer_id="PUBLIC_NHS_RESEARCH", business_unit="PUBLIC_FINANCE",
            counterparty_id=supplier, origin="CUSTOMER_DECLARATION",
        ))
    result = reconcile_scoped(
        invoices, declarations, group_size_limit=32, date_window_days=0)
    amount_total = sum(x["invoice amount minor"] for x in identity.values())
    return {
        "scope": "PUBLIC_SAME_SOURCE_ACCOUNTING_ONLY",
        "source_months": len(SOURCES),
        "disclosed_rows": len(rows),
        "unique_economic_invoices": len(identity),
        "repeated_disclosures_not_duplicate_payments": len(rows)-len(identity),
        "republication_payment_annotations_consistent": True,
        "supplier_reference_payment_declaration_groups": len(groups),
        "exact_invoiced_source_minor": amount_total,
        "exact_grouped_source_minor": sum(
            sum(x["invoice amount minor"] for x in group) for group in groups.values()),
        "matched_original_invoices": result.matched_internal,
        "unmatched_original_invoices": result.unmatched_internal,
        "mismatched_source_references": result.mismatched_references,
        "independently_proven_bank_settlements": result.proven_cleared_payment_count,
        "actual_freight_detection_accuracy": None,
        "realized_recovery_minor": 0,
        "replay_hash": result.result_hash,
        "monthly_rows": month_counts,
        "publication_claim_approved": False,
    }


def assert_public_census_result(result: dict) -> None:
    expected = {
        "source_months": 5,
        "disclosed_rows": 314,
        "unique_economic_invoices": 273,
        "repeated_disclosures_not_duplicate_payments": 41,
        "exact_invoiced_source_minor": 7423667742,
        "exact_grouped_source_minor": 7423667742,
        "matched_original_invoices": 273,
        "unmatched_original_invoices": 0,
        "mismatched_source_references": 0,
        "independently_proven_bank_settlements": 0,
        "realized_recovery_minor": 0,
        "publication_claim_approved": False,
    }
    for field, value in expected.items():
        if result.get(field) != value:
            raise ValueError("public accounting regression mismatch: " + field)
    if result.get("republication_payment_annotations_consistent") is not True:
        raise ValueError("public accounting replay lacks verified republication consistency")
    if result.get("actual_freight_detection_accuracy") is not None:
        raise ValueError("general accounting data cannot label freight accuracy")
