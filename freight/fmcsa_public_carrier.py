"""Read-only, exact-USDOT lookup against FMCSA's public Company Census.

Internal registration-context reference only. This module neither verifies
operating authority nor creates customer, contract, billing or recovery facts.
It never downloads an entire census or stores provider data on disk.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

DATASET_ID = "az4n-8mr2"
DATASET_URL = "https://data.transportation.gov/d/az4n-8mr2"
API_URL = "https://data.transportation.gov/resource/az4n-8mr2.json"
PUBLISHER = "Federal Motor Carrier Safety Administration"
REFERENCE_KIND = "PUBLIC_CENSUS_REGISTRATION_CONTEXT_NOT_OPERATING_AUTHORITY"
MAX_RESPONSE_BYTES = 8192
MAX_TIMEOUT_SECONDS = 10
USDOT_PATTERN = re.compile(r"^[1-9][0-9]{0,8}$", re.ASCII)
INT_PATTERN = re.compile(r"^(0|[1-9][0-9]{0,7})$", re.ASCII)
ALLOWED_FIELDS = frozenset({"dot_number", "legal_name", "power_units"})


class FMCSAReferenceError(ValueError):
    pass



class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Prevent a redirect from disclosing a requested USDOT to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FMCSAReferenceError("government API redirects are not permitted")


def _bounded_government_opener(request, *, timeout):
    """Only the fixed FMCSA HTTPS origin is allowed, with redirects disabled."""
    return urllib.request.build_opener(_RejectRedirects()).open(request, timeout=timeout)


def _unique_json_object(pairs):
    """Refuse ambiguous JSON field duplication instead of silently using last."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise FMCSAReferenceError("duplicate government JSON field")
        result[key] = value
    return result


@dataclass(frozen=True)
class CarrierCensusReference:
    usdot_number: str
    legal_name: str
    power_units: int | None
    retrieved_at_utc: str
    publisher: str = PUBLISHER
    dataset_url: str = DATASET_URL
    reference_kind: str = REFERENCE_KIND
    historical_point_in_time_verified: bool = False
    operating_authority_verified: bool = False
    customer_invoice_verified: bool = False
    recovery_fee_authorized: bool = False


def validate_usdot(number: str) -> str:
    if type(number) is not str or USDOT_PATTERN.fullmatch(number) is None:
        raise FMCSAReferenceError("USDOT number must be 1 to 9 canonical ASCII digits")
    return number


def build_query_url(number: str) -> str:
    """A bounded, explicit-column query; never an unfiltered census scan.

    Official FMCSA metadata identifies dot_number as numeric, legal_name as
    text, and power_units as text. The obsolete nbr_power_unit field is absent.
    Verified with official metadata and zero-record SoQL queries, 2026-10-08.
    """
    usdot = validate_usdot(number)
    params = urllib.parse.urlencode({
        "$select": "dot_number,legal_name,power_units",
        "$where": "dot_number=" + usdot,
        "$limit": "2",
    })
    return API_URL + "?" + params


def validate_census_response(number: str, document: object, *, retrieved_at_utc: str) -> CarrierCensusReference | None:
    """Validate source-shaped data. The timestamp is retrieval time, not a record vintage."""
    usdot = validate_usdot(number)
    if not isinstance(document, list) or len(document) > 1:
        raise FMCSAReferenceError("ambiguous or malformed carrier lookup result")
    if not document:
        return None
    row = document[0]
    if not isinstance(row, dict) or set(row) - ALLOWED_FIELDS:
        raise FMCSAReferenceError("unexpected or personal contact fields in response")
    if row.get("dot_number") != usdot:
        raise FMCSAReferenceError("USDOT number differs from requested identity")
    name = row.get("legal_name")
    if not isinstance(name, str) or not name.strip() or len(name) > 160:
        raise FMCSAReferenceError("invalid carrier legal name")
    if name != name.strip() or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise FMCSAReferenceError("unprintable or poorly normalized carrier name")
    raw_units = row.get("power_units")
    if raw_units is None or raw_units == "":
        power_units = None
    elif isinstance(raw_units, str) and INT_PATTERN.fullmatch(raw_units):
        power_units = int(raw_units)
    else:
        raise FMCSAReferenceError("power unit count must be a bounded whole number or unknown")
    try:
        timestamp = datetime.fromisoformat(retrieved_at_utc.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise FMCSAReferenceError("retrieval timestamp must include UTC timezone") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
        raise FMCSAReferenceError("retrieval timestamp must be UTC")
    return CarrierCensusReference(
        usdot_number=usdot,
        legal_name=name,
        power_units=power_units,
        retrieved_at_utc=timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def lookup_public_carrier(
    number: str,
    *,
    opener: Callable | None = None,
    timeout_seconds: int = 5,
    retrieved_at_utc: str | None = None,
) -> CarrierCensusReference | None:
    """One explicit carrier lookup; do not bulk-enrich or serialize returned names.

    The caller must have a legitimate reason to look up the specific USDOT ID.
    No automatic retries, cursor pagination, persistence or background polling.
    Tests inject a fake opener and never access DOT.
    """
    url = build_query_url(number)
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise FMCSAReferenceError("timeout must be between 1 and 10 seconds")
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "RETALLY-source-reference/1.0"},
        method="GET",
    )
    reader = opener or _bounded_government_opener
    try:
        with reader(request, timeout=timeout_seconds) as response:
            if getattr(response, "status", None) != 200:
                raise FMCSAReferenceError("government API did not return HTTP 200")
            actual_url = response.geturl() if callable(getattr(response, "geturl", None)) else url
            if actual_url != url:
                raise FMCSAReferenceError("government API response origin or query changed")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except FMCSAReferenceError:
        raise
    except (OSError, TimeoutError) as exc:
        raise FMCSAReferenceError("government reference service unavailable") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise FMCSAReferenceError("government API response exceeds bounded size")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except FMCSAReferenceError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise FMCSAReferenceError("invalid JSON carrier reference") from exc
    observed = retrieved_at_utc or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return validate_census_response(number, data, retrieved_at_utc=observed)
