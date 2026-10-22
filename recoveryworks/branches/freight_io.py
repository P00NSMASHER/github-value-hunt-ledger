"""Import existing FreightRecovery proof artifacts into RecoveryOS."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
import zipfile

from freight.contracts import (
    AuthorityRef,
    Finding,
    REVIEW,
    VALIDATED,
    canonical_hash as freight_hash,
)

from recoveryworks.engine import RecoveryObservation
from .freight import from_freight_finding, verify_freight_finding


@dataclass(frozen=True)
class FreightImportBatch:
    buyer_id: str
    business_unit: str
    truth_hash: str
    source_hash: str
    observations: tuple[RecoveryObservation, ...]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_json(raw: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _verify_finding(raw: Mapping[str, Any]) -> Finding:
    return verify_freight_finding(Finding(**raw))


def parse_freight_truth_manifest(
    payload: Mapping[str, Any],
    *,
    source_hash: str,
    source_locator: str,
) -> FreightImportBatch:
    buyer_id = str(payload.get("buyer_id") or "").strip()
    business_unit = str(payload.get("business_unit") or "").strip()
    population_hash = str(payload.get("population_hash") or "").strip()
    truth_hash = str(payload.get("truth_hash") or "").strip()
    if not all((buyer_id, business_unit, population_hash, truth_hash)):
        raise ValueError("freight truth manifest missing required identity/hash fields")

    authorities_raw = payload.get("authorities")
    findings_raw = payload.get("findings")
    if not isinstance(authorities_raw, list) or not isinstance(findings_raw, list):
        raise ValueError("freight truth manifest requires authorities/findings lists")

    authorities = tuple(AuthorityRef(**row) for row in authorities_raw)
    findings = tuple(_verify_finding(row) for row in findings_raw)

    authority_index: dict[str, AuthorityRef] = {}
    for authority in authorities:
        if authority.authority_id in authority_index:
            raise ValueError(f"duplicate freight authority_id: {authority.authority_id}")
        if (authority.buyer_id, authority.business_unit) != (buyer_id, business_unit):
            raise ValueError("freight authority scope mismatch")
        authority_index[authority.authority_id] = authority

    seen_finding_ids: set[str] = set()
    for finding in findings:
        if finding.finding_id in seen_finding_ids:
            raise ValueError(f"duplicate freight finding_id: {finding.finding_id}")
        seen_finding_ids.add(finding.finding_id)
        if (finding.buyer_id, finding.business_unit) != (buyer_id, business_unit):
            raise ValueError("freight finding scope mismatch")
        if finding.status not in {VALIDATED, REVIEW}:
            raise ValueError("invalid freight finding status")
        if finding.status == VALIDATED and (
            not finding.authority_id or finding.authority_id not in authority_index
        ):
            raise ValueError("validated freight finding missing authority")
        if finding.authority_id and finding.authority_id in authority_index:
            # Hash-valid manifests can still bind the wrong customer,
            # carrier or currency. Enforce the producer's exact scope rules.
            authority = authority_index[finding.authority_id]
            if (authority.customer_id, authority.carrier_id, authority.currency) != (
                finding.customer_id, finding.carrier_id, finding.currency
            ):
                raise ValueError("freight authority identity mismatch: customer/carrier/currency")

    body = {
        "schema": 3,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "population_hash": population_hash,
        "authorities": [asdict(item) for item in authorities],
        "findings": [asdict(item) for item in findings],
    }
    if freight_hash(body) != truth_hash:
        raise ValueError("freight truth manifest hash mismatch")

    observations = tuple(
        from_freight_finding(
            finding,
            authority_index.get(finding.authority_id or ""),
            source_locator=source_locator,
        )
        for finding in sorted(findings, key=lambda item: item.finding_id)
    )
    return FreightImportBatch(
        buyer_id=buyer_id,
        business_unit=business_unit,
        truth_hash=truth_hash,
        source_hash=source_hash,
        observations=observations,
    )


def load_freight_truth_manifest(path: str | Path) -> FreightImportBatch:
    source = Path(path)
    raw = source.read_bytes()
    payload = _parse_json(raw, label=str(source))
    return parse_freight_truth_manifest(
        payload,
        source_hash=_sha(raw),
        source_locator=f"file://{source.name}",
    )


def load_freight_audit_result_bundle(path: str | Path) -> FreightImportBatch:
    source = Path(path)
    bundle_raw = source.read_bytes()
    with zipfile.ZipFile(source, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate freight audit bundle entry")
        required = {"RESULT_BUNDLE_MANIFEST.json", "truth-manifest.json"}
        if not required.issubset(names):
            raise ValueError("freight audit bundle missing manifest or truth-manifest")

        manifest_raw = archive.read("RESULT_BUNDLE_MANIFEST.json")
        manifest = _parse_json(manifest_raw, label="RESULT_BUNDLE_MANIFEST.json")
        if manifest.get("bundle_type") != "AUDIT_RESULT":
            raise ValueError("not a FreightRecovery AUDIT_RESULT bundle")
        rows = manifest.get("entries")
        if not isinstance(rows, list):
            raise ValueError("freight audit bundle manifest entries missing")
        row_index = {
            row.get("path"): row
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("path"), str)
        }
        truth_row = row_index.get("truth-manifest.json")
        if truth_row is None:
            raise ValueError("freight audit bundle does not hash truth-manifest.json")

        truth_raw = archive.read("truth-manifest.json")
        if truth_row.get("sha256") != _sha(truth_raw):
            raise ValueError("freight truth-manifest bundle hash mismatch")
        if truth_row.get("size_bytes") != len(truth_raw):
            raise ValueError("freight truth-manifest bundle size mismatch")
        truth = _parse_json(truth_raw, label="truth-manifest.json")

    return parse_freight_truth_manifest(
        truth,
        source_hash=_sha(bundle_raw),
        source_locator=f"bundle://{source.name}/truth-manifest.json",
    )
