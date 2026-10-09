"""Immutable EIA weekly retail diesel reference. Never proves a freight billing error.

These public observations are for historical market context only. They cannot
authorize a carrier surcharge, customer claim, settlement, or RETALLY fee.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

SOURCE_URL = "https://www.eia.gov/petroleum/gasdiesel/index.php"
SOURCE_PUBLISHER = "U.S. Energy Information Administration"
RELEASE_DATE = "2026-10-06"
UNITS = "USD_PER_GALLON_INCLUDING_TAXES"
ROLE = "OBSERVED_PUBLIC_MARKET_REFERENCE_ONLY"
SUPPORTED_REGIONS = frozenset({"US", "EAST_COAST", "CENTRAL_ATLANTIC"})
SUPPORTED_WEEKS = frozenset({"2026-09-21", "2026-09-28", "2026-10-05"})
DECIMAL_3 = re.compile(r"^[0-9]+\.[0-9]{3}$")
PATH = Path(__file__).resolve().parent / "data" / "eia_on_highway_diesel_2026-10-06.csv"
# Protects exact published-transcription bytes from accidental edits.
# Not an EIA-issued signature, authenticity attestation or external authority.
PINNED_SHA256 = "20c3e8cec1c7e13aa9e7d61bdfd95e3d1ee75913e932887efbcd2be946ce97b6"


@dataclass(frozen=True)
class ReferenceObservation:
    week: date
    region: str
    price: Decimal
    publisher: str = SOURCE_PUBLISHER
    source_url: str = SOURCE_URL
    units: str = UNITS
    role: str = ROLE


class ReferenceDataError(ValueError):
    pass


def load_reference(path: Path = PATH, *, require_pin: bool = True) -> dict[tuple[str, str], ReferenceObservation]:
    """Load exactly three published weeks and regions; no customer data or fees."""
    raw = path.read_bytes()
    if require_pin and hashlib.sha256(raw).hexdigest() != PINNED_SHA256:
        raise ReferenceDataError("pinned reference digest mismatch")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ReferenceDataError("reference must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
    if reader.fieldnames != ["week", "region", "usd_per_gallon"]:
        raise ReferenceDataError("unexpected reference columns")
    entries: dict[tuple[str, str], ReferenceObservation] = {}
    try:
        for row in reader:
            if None in row or any(x is None for x in row.values()):
                raise ReferenceDataError("malformed CSV row")
            week_string, region, price_string = row["week"], row["region"], row["usd_per_gallon"]
            if week_string not in SUPPORTED_WEEKS or region not in SUPPORTED_REGIONS:
                raise ReferenceDataError("unexpected week or region")
            parsed = date.fromisoformat(week_string)
            if parsed.weekday() != 0 or parsed > date.fromisoformat(RELEASE_DATE):
                raise ReferenceDataError("invalid weekly observation date")
            if not DECIMAL_3.fullmatch(price_string):
                raise ReferenceDataError("price must have exactly three decimals")
            price = Decimal(price_string)
            if not Decimal("0") < price < Decimal("25"):
                raise ReferenceDataError("price outside bounded observation range")
            key = (week_string, region)
            if key in entries:
                raise ReferenceDataError("duplicate EIA observation")
            entries[key] = ReferenceObservation(parsed, region, price)
    except (csv.Error, ValueError) as exc:
        if isinstance(exc, ReferenceDataError):
            raise
        raise ReferenceDataError("malformed reference dataset") from exc
    expected = {(week, region) for week in SUPPORTED_WEEKS for region in SUPPORTED_REGIONS}
    if set(entries) != expected:
        raise ReferenceDataError("reference coverage incomplete")
    return entries


def reference_price(week: str, region: str, *, path: Path = PATH) -> ReferenceObservation:
    if (week, region) not in {(w, r) for w in SUPPORTED_WEEKS for r in SUPPORTED_REGIONS}:
        raise ReferenceDataError("observation outside pinned EIA scope")
    return load_reference(path)[(week, region)]
