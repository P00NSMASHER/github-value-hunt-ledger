"""Machine-checkable Freight Recovery pilot data-room and proof-package manifests."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

from freight.contracts import (
    IncumbentOutput,
    PopulationManifest,
    SealedIncumbentSubmission,
    TruthManifest,
    canonical_hash,
)
from freight.launch_authorization import (
    LaunchAuthorizationReceipt,
    verify_launch_authorization,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_SOURCE_TYPES = {
    "invoice",
    "authority",
    "shipment_evidence",
    "identity_map",
    "incumbent_output",
    "settlement_observation",
    "other",
}


@dataclass(frozen=True)
class SourceEntry:
    source_id: str
    buyer_id: str
    business_unit: str
    source_type: str
    source_hash: str
    read_only: bool
    authorized: bool
    contains_secrets: bool
    retention_days: int
    source_locator: str | None = None


@dataclass(frozen=True)
class DataRoomManifest:
    buyer_id: str
    business_unit: str
    engagement_id: str
    launch_authorization_hash: str
    launch_authorization_valid_until: str
    entries: tuple[SourceEntry, ...]
    manifest_hash: str


@dataclass(frozen=True)
class PilotPackageManifest:
    buyer_id: str
    business_unit: str
    engagement_id: str
    launch_authorization_hash: str
    launch_authorization_valid_until: str
    data_room_hash: str
    population_hash: str
    truth_hash: str
    incumbent_submission_hash: str
    incumbent_output_hash: str
    package_hash: str


def _required(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")


def _valid_sha256(value: str) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _verify_authorization_scope(
    authorization: LaunchAuthorizationReceipt,
    *,
    buyer_id: str,
    business_unit: str,
    as_of_date: str,
) -> None:
    errors = verify_launch_authorization(
        authorization,
        as_of_date=as_of_date,
    )
    if errors:
        raise ValueError(
            "invalid launch authorization: " + ",".join(errors)
        )
    if (authorization.buyer_id, authorization.business_unit) != (
        buyer_id,
        business_unit,
    ):
        raise ValueError("launch authorization scope mismatch")


def build_data_room_manifest(
    buyer_id: str,
    business_unit: str,
    entries: Iterable[SourceEntry],
    *,
    authorization: LaunchAuthorizationReceipt,
    authorization_as_of_date: str,
    require_pilot_read_only: bool = True,
) -> DataRoomManifest:
    _required("buyer_id", buyer_id)
    _required("business_unit", business_unit)
    _verify_authorization_scope(
        authorization,
        buyer_id=buyer_id,
        business_unit=business_unit,
        as_of_date=authorization_as_of_date,
    )

    normalized = tuple(sorted(entries, key=lambda x: x.source_id))
    if not normalized:
        raise ValueError("data room must contain at least one source")

    seen_ids: set[str] = set()
    for entry in normalized:
        _required("source_id", entry.source_id)
        _required("buyer_id", entry.buyer_id)
        _required("business_unit", entry.business_unit)
        _required("source_type", entry.source_type)
        if entry.source_id in seen_ids:
            raise ValueError("duplicate source_id: " + entry.source_id)
        seen_ids.add(entry.source_id)

        if (entry.buyer_id, entry.business_unit) != (buyer_id, business_unit):
            raise ValueError("source scope mismatch")
        if entry.source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError("unsupported source_type: " + entry.source_type)
        if not _valid_sha256(entry.source_hash):
            raise ValueError("source_hash must be lowercase SHA-256")
        if not entry.authorized:
            raise ValueError("unauthorized source cannot enter pilot data room")
        if require_pilot_read_only and not entry.read_only:
            raise ValueError("pilot source must be read-only")
        if entry.contains_secrets:
            raise ValueError("credential/secret-bearing source cannot enter evidence room")
        if not isinstance(entry.retention_days, int) or entry.retention_days <= 0:
            raise ValueError("retention_days must be a positive integer")

    body = {
        "schema": 2,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "engagement_id": authorization.engagement_id,
        "launch_authorization_hash": authorization.receipt_hash,
        "launch_authorization_valid_until": authorization.valid_until,
        "entries": [asdict(x) for x in normalized],
    }
    return DataRoomManifest(
        buyer_id=buyer_id,
        business_unit=business_unit,
        engagement_id=authorization.engagement_id,
        launch_authorization_hash=authorization.receipt_hash,
        launch_authorization_valid_until=authorization.valid_until,
        entries=normalized,
        manifest_hash=canonical_hash(body),
    )


def build_pilot_package(
    data_room: DataRoomManifest,
    population: PopulationManifest,
    truth: TruthManifest,
    submission: SealedIncumbentSubmission,
    incumbent: IncumbentOutput,
    *,
    authorization: LaunchAuthorizationReceipt,
    authorization_as_of_date: str,
) -> PilotPackageManifest:
    _verify_authorization_scope(
        authorization,
        buyer_id=data_room.buyer_id,
        business_unit=data_room.business_unit,
        as_of_date=authorization_as_of_date,
    )
    if data_room.engagement_id != authorization.engagement_id:
        raise ValueError("data room/launch authorization engagement mismatch")
    if data_room.launch_authorization_hash != authorization.receipt_hash:
        raise ValueError("data room/launch authorization hash mismatch")
    if data_room.launch_authorization_valid_until != authorization.valid_until:
        raise ValueError("data room/launch authorization expiry mismatch")

    scope = (data_room.buyer_id, data_room.business_unit)
    objects = (
        ("population", population.buyer_id, population.business_unit),
        ("truth", truth.buyer_id, truth.business_unit),
        ("incumbent submission", submission.buyer_id, submission.business_unit),
        ("incumbent output", incumbent.buyer_id, incumbent.business_unit),
    )
    for label, buyer_id, business_unit in objects:
        if (buyer_id, business_unit) != scope:
            raise ValueError(label + " scope mismatch")

    if truth.population_hash != population.manifest_hash:
        raise ValueError("truth/population hash mismatch")
    if submission.population_hash != population.manifest_hash:
        raise ValueError("incumbent submission/population hash mismatch")
    if incumbent.population_hash != population.manifest_hash:
        raise ValueError("incumbent output/population hash mismatch")
    if incumbent.truth_hash != truth.truth_hash:
        raise ValueError("incumbent output/truth hash mismatch")
    if incumbent.submission_hash != submission.sealed_hash:
        raise ValueError("incumbent output/submission hash mismatch")
    if incumbent.source_hash != submission.source_hash:
        raise ValueError("incumbent output/source hash mismatch")

    incumbent_sources = {
        e.source_hash
        for e in data_room.entries
        if e.source_type == "incumbent_output"
    }
    if submission.source_hash not in incumbent_sources:
        raise ValueError("sealed incumbent source missing from data-room manifest")

    source_types = {e.source_type for e in data_room.entries}
    required_types = {"invoice", "authority", "incumbent_output"}
    missing = sorted(required_types - source_types)
    if missing:
        raise ValueError(
            "pilot data room missing required source types: " + ",".join(missing)
        )

    body = {
        "schema": 2,
        "buyer_id": data_room.buyer_id,
        "business_unit": data_room.business_unit,
        "engagement_id": data_room.engagement_id,
        "launch_authorization_hash": data_room.launch_authorization_hash,
        "launch_authorization_valid_until": data_room.launch_authorization_valid_until,
        "data_room_hash": data_room.manifest_hash,
        "population_hash": population.manifest_hash,
        "truth_hash": truth.truth_hash,
        "incumbent_submission_hash": submission.sealed_hash,
        "incumbent_output_hash": incumbent.output_hash,
    }
    return PilotPackageManifest(
        buyer_id=data_room.buyer_id,
        business_unit=data_room.business_unit,
        engagement_id=data_room.engagement_id,
        launch_authorization_hash=data_room.launch_authorization_hash,
        launch_authorization_valid_until=data_room.launch_authorization_valid_until,
        data_room_hash=data_room.manifest_hash,
        population_hash=population.manifest_hash,
        truth_hash=truth.truth_hash,
        incumbent_submission_hash=submission.sealed_hash,
        incumbent_output_hash=incumbent.output_hash,
        package_hash=canonical_hash(body),
    )
