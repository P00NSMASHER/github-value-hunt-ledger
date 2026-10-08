"""Limited BTS T-100 airfreight ingestion evaluation, not customer invoice training.

The 2013 records are selected from a third-party GitHub mirror of publicly
reported BTS fields. They are not independent invoice/contract/overcharge labels.
Do not infer carrier authority, recovery eligibility, or customer revenue.
"""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "bts_t100_airfreight_observed_subset_2013.csv"
PUBLISHER = "U.S. Bureau of Transportation Statistics"
SOURCE_REPOSITORY = "dannguyen/bts-transstats-t100-domestic-demo"
SOURCE_SAMPLE_BLOB = "359f319355edbef944ffd103ed16c7a5877131c8"
SOURCE_SAMPLE_URL = (
    "https://github.com/dannguyen/bts-transstats-t100-domestic-demo/"
    "blob/master/data/sample-T100D-segment-data.csv"
)
BTS_FIELD_REFERENCE = "https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=GEE"
# Exact Git blob of the curated 20-row fixture. This pins integrity of the file,
# not official BTS authentication or permission to use a full dataset for ML.
PINNED_FIXTURE_BLOB = "e49629f7754186f33e4c95e95546e6a599d36254"
COLUMNS = (
    "source_row", "year", "month", "carrier_code", "origin", "destination",
    "freight_pounds", "mail_pounds", "distance_miles",
    "departures_performed", "service_class", "freight_present",
)
SOURCE_ROWS = (2, 3, 5, 10, 13, 15, 16, 17, 18, 21, 30, 31, 32, 33, 36, 103, 104, 105, 106, 110)
EXPECTED_CARRIERS = frozenset({"2E", "2F", "4W", "7H"})
EVALUATION_CARRIER = "7H"
DECIMAL_PATTERN = re.compile(r"^\d+\.\d\d$")
CARRIER_PATTERN = re.compile(r"^[A-Z0-9]{2,3}$")
AIRPORT_PATTERN = re.compile(r"^[A-Z0-9]{3}$")


class PublicReferenceError(ValueError):
    pass


@dataclass(frozen=True)
class ReportedAirfreight:
    source_row: int
    year: int
    month: int
    carrier_code: str
    origin: str
    destination: str
    freight_pounds: Decimal
    mail_pounds: Decimal
    distance_miles: Decimal
    departures_performed: Decimal
    service_class: str
    freight_present: bool

    @property
    def evidence_class(self) -> str:
        return "THIRD_PARTY_MIRROR_OF_REPORTED_BTS_TRANSPORTATION_DATA_NOT_INVOICE_GROUND_TRUTH"


def _decimal(value: str, field: str) -> Decimal:
    if not isinstance(value, str) or not DECIMAL_PATTERN.fullmatch(value):
        raise PublicReferenceError(field + " must use exact two-decimal source units")
    number = Decimal(value)
    if number < 0 or number > 100000000000:
        raise PublicReferenceError(field + " out of supported range")
    return number


def load_observations(
    path: Path = DATA_PATH, *, verify_pinned_blob: bool = True
) -> tuple[ReportedAirfreight, ...]:
    raw = path.read_bytes()
    if verify_pinned_blob:
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if git_blob != PINNED_FIXTURE_BLOB:
            raise PublicReferenceError("curated BTS sample integrity mismatch")
    try:
        stream = raw.decode("utf-8")
        reader = csv.DictReader(stream.splitlines(), strict=True)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise PublicReferenceError("unexpected BTS subset columns")
        parsed = []
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise PublicReferenceError("malformed BTS subset CSV row")
            if not str(row["source_row"]).isdigit():
                raise PublicReferenceError("source row must be a positive integer")
            carrier, orig, dest = row["carrier_code"], row["origin"], row["destination"]
            if not CARRIER_PATTERN.fullmatch(carrier):
                raise PublicReferenceError("invalid carrier identifier")
            if not AIRPORT_PATTERN.fullmatch(orig) or not AIRPORT_PATTERN.fullmatch(dest):
                raise PublicReferenceError("invalid airport identifier")
            if row["year"] != "2013" or row["month"] != "1":
                raise PublicReferenceError("observations outside pinned January 2013 vintage")
            if row["service_class"] not in ("F", "G", "L", "P"):
                raise PublicReferenceError("unrecognized T-100 service class")
            freight = _decimal(row["freight_pounds"], "freight_pounds")
            if row["freight_present"] not in ("0", "1"):
                raise PublicReferenceError("freight_present label must be exactly 0 or 1")
            reported = row["freight_present"] == "1"
            if reported != (freight > 0):
                raise PublicReferenceError("derived freight-present target contradicts source value")
            item = ReportedAirfreight(
                source_row=int(row["source_row"]), year=2013, month=1,
                carrier_code=carrier, origin=orig, destination=dest,
                freight_pounds=freight, mail_pounds=_decimal(row["mail_pounds"], "mail_pounds"),
                distance_miles=_decimal(row["distance_miles"], "distance_miles"),
                departures_performed=_decimal(row["departures_performed"], "departures_performed"),
                service_class=row["service_class"], freight_present=reported,
            )
            parsed.append(item)
    except (UnicodeDecodeError, csv.Error) as err:
        raise PublicReferenceError("invalid text encoding or CSV syntax") from err

    if tuple(x.source_row for x in parsed) != SOURCE_ROWS:
        raise PublicReferenceError("pinned source row IDs/order changed")
    if {x.carrier_code for x in parsed} != EXPECTED_CARRIERS:
        raise PublicReferenceError("missing or unexpected BTS carrier")
    for carrier in EXPECTED_CARRIERS:
        group = [x for x in parsed if x.carrier_code == carrier]
        if len(group) != 5 or sum(x.freight_present for x in group) != 3:
            raise PublicReferenceError("BTS carrier group/target coverage changed")
    return tuple(parsed)


def carrier_disjoint_eval(
    observations: tuple[ReportedAirfreight, ...]
) -> tuple[tuple[ReportedAirfreight, ...], tuple[ReportedAirfreight, ...]]:
    """Static grouped holdout for importer QA, not a statistical model evaluation."""
    if len(observations) != len(SOURCE_ROWS):
        raise PublicReferenceError("missing rows for grouped evaluation")
    training = tuple(x for x in observations if x.carrier_code != EVALUATION_CARRIER)
    evaluation = tuple(x for x in observations if x.carrier_code == EVALUATION_CARRIER)
    if (
        {x.carrier_code for x in training} != EXPECTED_CARRIERS - {EVALUATION_CARRIER}
        or len(training) != 15 or len(evaluation) != 5
        or {x.carrier_code for x in training} & {x.carrier_code for x in evaluation}
    ):
        raise PublicReferenceError("carrier leakage or incomplete grouped holdout")
    return training, evaluation
