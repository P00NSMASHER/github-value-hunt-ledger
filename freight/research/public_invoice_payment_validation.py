"""Read-only, bounded profile of official OGL public invoice/payment CSV.

Research-only: no source rows or personally identifying supplier details persisted,
no assertions of bank clearance, real freight rating accuracy, or RETALLY recovery.
Run: python -m freight.research.public_invoice_payment_validation --live
An offline stdin/file path can instead be used by calling profile_csv(bytes).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Exact URL obtained from the publisher's OGL-licensed official data.gov.uk record.
PUBLISHER_DATASET = (
    "https://www.data.gov.uk/dataset/31ef5153-cf9c-45f7-9bcf-e2c86200d00b/"
    "spend-over-25-000-in-pennine-care-nhs-foundation-trust"
)
SOURCE_URL = "https://www.penninecare.nhs.uk/download_file/5920/277"
LICENSE_LABEL = "UK Open Government Licence v3.0 (publisher's catalog metadata)"
LICENSE_URL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
MAX_SOURCE_BYTES = 4_000_000
MAX_DATA_ROWS = 60_000
REQUIRED = (
    "Supplier Number", "Invoice Number", "Invoice Date", "Invoice Amount",
    "Payment Number", "Payment Date", "Payment Method", "Payment Status Name",
    "Payment Currency",
)


class SourceHold(ValueError):
    """Fail closed when public file identity, format, or evidence is insufficient."""


class _SameHostOnly(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect is safe only if the same HTTPS official publisher serves it.
        parsed = urlsplit(newurl)
        if (parsed.scheme != "https" or parsed.hostname != "www.penninecare.nhs.uk"
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)):
            raise SourceHold("OFF_PUBLISHER_REDIRECT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_official_csv(url: str = SOURCE_URL) -> bytes:
    if url != SOURCE_URL:
        raise SourceHold("SOURCE_NOT_PINNED")
    req = Request(url, headers={
        "User-Agent": "RETALLY-PublicEvidence-Research/1.0",
        "Accept": "text/csv,application/octet-stream",
    })
    opener = build_opener(_SameHostOnly())
    try:
        with opener.open(req, timeout=20) as response:
            if response.status != 200:
                raise SourceHold("SOURCE_HTTP_NON_200")
            final = urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname != "www.penninecare.nhs.uk":
                raise SourceHold("SOURCE_IDENTITY_LOST")
            content = response.read(MAX_SOURCE_BYTES + 1)
    except SourceHold:
        raise
    except Exception as exc:
        # Never print external response bodies, redirects, tokens, or dataset rows.
        raise SourceHold("OFFICIAL_SOURCE_FETCH_UNAVAILABLE") from exc
    if len(content) > MAX_SOURCE_BYTES or not content:
        raise SourceHold("SOURCE_SIZE_HOLD")
    return content


def money_cents(value: str) -> int:
    """Parse exact GBP cents without float/rounding; reject malformed values."""
    if not isinstance(value, str):
        raise ValueError("BAD_AMOUNT")
    cleaned = value.strip().replace(",", "").replace("£", "")
    if not re.fullmatch(r"-?[0-9]+(?:\.[0-9]{1,2})?", cleaned):
        raise ValueError("BAD_AMOUNT")
    try:
        dec = Decimal(cleaned)
        cents = dec * 100
        if cents != cents.to_integral_value():
            raise ValueError("BAD_AMOUNT")
        if abs(cents) > 10**17:
            raise ValueError("BAD_AMOUNT")
        return int(cents)
    except (InvalidOperation, OverflowError) as exc:
        raise ValueError("BAD_AMOUNT") from exc


def date_value(value: str):
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except (ValueError, AttributeError):
            pass
    raise ValueError("BAD_DATE")


def profile_csv(raw: bytes) -> dict:
    """Returns only aggregate statistics and SHA-256; source rows never leave memory.

    The published 'Fully paid' flag + EFT/reference is accounting ledger evidence,
    not an independently verified bank settlement or a source invoice image.
    Payment identifiers may cover multiple invoices (normal many-to-one payment).
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise SourceHold("SOURCE_SIZE_HOLD")
    sha = hashlib.sha256(raw).hexdigest()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceHold("UNRECOGNIZED_CSV_ENCODING") from exc
    if "\x00" in decoded[:2000] or "<html" in decoded[:1000].lower():
        raise SourceHold("NOT_CSV_CONTENT")
    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    if not reader.fieldnames:
        raise SourceHold("MISSING_HEADER")
    headers = [" ".join(h.replace("\ufeff", "").split()) for h in reader.fieldnames]
    if len(set(headers)) != len(headers):
        raise SourceHold("DUPLICATE_HEADER")
    if not set(REQUIRED).issubset(headers):
        raise SourceHold("MISSING_REQUIRED_FIELDS")
    # DictReader keys are original header spellings; normalize only header keys.
    original_to_normal = dict(zip(reader.fieldnames, headers))
    total = complete = fully_paid = invalid_amount = invalid_date = before_invoice = 0
    missing = Counter()
    statuses = Counter()
    currency = Counter()
    payment_to_invoice = defaultdict(set)
    invoice_keys = Counter()
    amount_cents_total = 0
    for original_row in reader:
        total += 1
        if total > MAX_DATA_ROWS:
            raise SourceHold("ROW_LIMIT_EXCEEDED")
        if None in original_row:
            raise SourceHold("MALFORMED_CSV_EXTRA_CELLS")
        row = {original_to_normal[key]: (value or "").strip()
               for key, value in original_row.items()}
        empty = [field for field in REQUIRED if not row[field]]
        for field in empty:
            missing[field] += 1
        if empty:
            continue
        statuses[row["Payment Status Name"].casefold()] += 1
        currency[row["Payment Currency"].upper()] += 1
        try:
            cents = money_cents(row["Invoice Amount"])
        except ValueError:
            invalid_amount += 1
            continue
        try:
            invoice_date = date_value(row["Invoice Date"])
            payment_date = date_value(row["Payment Date"])
        except ValueError:
            invalid_date += 1
            continue
        if payment_date < invoice_date:
            before_invoice += 1
            continue
        # A non-GBP or unpaid row must not be counted as a complete GBP payment.
        if row["Payment Currency"].upper() != "GBP":
            continue
        if row["Payment Status Name"].strip().casefold() != "fully paid":
            continue
        fully_paid += 1
        complete += 1
        amount_cents_total += cents
        invoice_id = (
            row["Supplier Number"].upper(),
            row["Invoice Number"].upper(),
            row["Invoice Date"],
        )
        invoice_keys[invoice_id] += 1
        payment_to_invoice[row["Payment Number"]].add(invoice_id)
    if not total:
        raise SourceHold("ZERO_SOURCE_ROWS")
    return {
        "dataset": "Pennine Care NHS Foundation Trust | expenditure over GBP25000",
        "publisher_dataset_url": PUBLISHER_DATASET,
        "source_url": SOURCE_URL,
        "source_sha256": sha,
        "source_bytes": len(raw),
        "license_label": LICENSE_LABEL,
        "license_url": LICENSE_URL,
        "grain": "supplier invoice reference and reported payment",
        "source_row_count": total,
        "complete_paid_reference_rows": complete,
        "complete_paid_reference_fraction": round(complete / total, 6),
        "fully_paid_eligible_rows": fully_paid,
        "invalid_amount_rows": invalid_amount,
        "invalid_date_rows": invalid_date,
        "payment_precedes_invoice_rows": before_invoice,
        "missing_required_field_counts": dict(sorted(missing.items())),
        "payment_status_counts": dict(sorted(statuses.items())),
        "currency_counts": dict(sorted(currency.items())),
        "composite_invoice_key_duplicate_rows": sum(
            count - 1 for count in invoice_keys.values() if count > 1),
        "distinct_invoice_keys": len(invoice_keys),
        "distinct_payment_numbers": len(payment_to_invoice),
        "payment_numbers_covering_multiple_invoices": sum(
            len(inv) > 1 for inv in payment_to_invoice.values()),
        "total_reported_invoice_amount_gbp_cents_for_complete_rows": amount_cents_total,
        "rights_assessment": "OGL_SOURCE_LICENSED_WITH_ATTRIBUTION",
        "actual_bank_settlement_independently_verified": False,
        "original_invoice_document_present": False,
        "freight_rate_and_shipment_evidence_present": False,
        "independently_adjudicated_freight_error_labels": False,
        "verified_retally_recovered_cents": 0,
        "commercial_freight_accuracy_validation_ready": False,
        "raw_invoice_rows_persisted": False,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Fetch exact official public CSV.")
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("No source download without an explicit --live flag")
    try:
        result = profile_csv(fetch_official_csv())
    except SourceHold as exc:
        # Non-sensitive failure message; command nonzero fails CI without false green.
        print(json.dumps({"status": "PUBLIC_REPLAY_HELD", "reason": str(exc)}))
        raise SystemExit(2) from None
    print(json.dumps({"status": "PUBLIC_LEDGER_REPLAY_PROFILING_ONLY", **result},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
