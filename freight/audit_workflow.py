"""One-call operational workflow for a Freight Recovery audit run.

This module composes the controlled pre-human-decision pipeline:

invoice CSV -> guarded normalization -> evidence-derived population ->
trusted-context authority rule normalization -> Finding Factory ->
review queue -> reviewer packet -> canonical audit-run manifest.

It does not confirm findings, open incumbent output, contact carriers, move money,
or claim realized savings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

from freight.audit_run_manifest import AuditRunManifest, build_audit_run_manifest
from freight.contracts import canonical_hash
from freight.finding_factory import FindingFactoryBatch, derive_batch
from freight.invoice_csv_adapter import InvoiceChargeCSVBatch, parse_invoice_charge_csv
from freight.population_builder import PopulationBuild, build_population_from_charge_batch
from freight.review_packet import ReviewPacket, build_review_packet, render_review_packet_markdown
from freight.review_queue import ReviewQueue, build_review_queue
from freight.rule_csv_adapter import ChargeRuleCSVBatch, parse_charge_rule_csv


class AuditWorkflowStatus(str, Enum):
    CLEAN = "CLEAN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class RuleSourceInput:
    rule_filename: str
    rule_csv: bytes
    customer_id: str
    carrier_id: str
    currency: str
    authority_document_id: str
    authority_document_data: bytes
    verified_controlling_authority: bool


@dataclass(frozen=True)
class AuditWorkflowRequest:
    buyer_id: str
    business_unit: str
    selection_rule: str
    invoice_filename: str
    invoice_csv: bytes
    rule_sources: tuple[RuleSourceInput, ...] = ()


@dataclass(frozen=True)
class AuditWorkflowResult:
    status: AuditWorkflowStatus
    invoice_batch: InvoiceChargeCSVBatch
    population_build: PopulationBuild
    rule_batches: tuple[ChargeRuleCSVBatch, ...]
    factory: FindingFactoryBatch
    review_queue: ReviewQueue
    review_packet: ReviewPacket
    run_manifest: AuditRunManifest
    result_hash: str


def _sha256(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("authority_document_data must be bytes")
    return hashlib.sha256(bytes(data)).hexdigest()


def run_audit_workflow(request: AuditWorkflowRequest) -> AuditWorkflowResult:
    if not isinstance(request, AuditWorkflowRequest):
        raise TypeError("request must be an AuditWorkflowRequest")

    invoice_batch = parse_invoice_charge_csv(
        filename=request.invoice_filename,
        data=request.invoice_csv,
        buyer_id=request.buyer_id,
        business_unit=request.business_unit,
    )
    population_build = build_population_from_charge_batch(
        invoice_batch,
        selection_rule=request.selection_rule,
    )

    rule_batches: list[ChargeRuleCSVBatch] = []
    for source in request.rule_sources:
        if not isinstance(source, RuleSourceInput):
            raise TypeError("rule_sources must contain RuleSourceInput values")
        batch = parse_charge_rule_csv(
            filename=source.rule_filename,
            data=source.rule_csv,
            buyer_id=invoice_batch.buyer_id,
            business_unit=invoice_batch.business_unit,
            customer_id=source.customer_id,
            carrier_id=source.carrier_id,
            currency=source.currency,
            authority_document_id=source.authority_document_id,
            source_document_sha256=_sha256(source.authority_document_data),
            verified_controlling_authority=source.verified_controlling_authority,
        )
        rule_batches.append(batch)

    rule_batches_tuple = tuple(rule_batches)
    rules = tuple(rule for batch in rule_batches_tuple for rule in batch.rules)
    factory = derive_batch(
        population_build.population,
        invoice_batch.charges,
        rules,
    )
    review_queue = build_review_queue(factory)
    review_packet = build_review_packet(
        factory,
        review_queue,
        invoice_batch.charges,
        rules,
    )
    run_manifest = build_audit_run_manifest(
        invoice_batch=invoice_batch,
        population_build=population_build,
        rule_batches=rule_batches_tuple,
        factory=factory,
        review_queue=review_queue,
        review_packet=review_packet,
    )
    status = (
        AuditWorkflowStatus.CLEAN
        if not review_queue.items
        else AuditWorkflowStatus.REVIEW_REQUIRED
    )
    body = {
        "schema": 1,
        "status": status.value,
        "run_hash": run_manifest.run_hash,
        "review_packet_hash": review_packet.packet_hash,
        "clear_count": factory.clear_count,
        "validated_count": factory.validated_count,
        "review_count": factory.review_count,
    }
    return AuditWorkflowResult(
        status=status,
        invoice_batch=invoice_batch,
        population_build=population_build,
        rule_batches=rule_batches_tuple,
        factory=factory,
        review_queue=review_queue,
        review_packet=review_packet,
        run_manifest=run_manifest,
        result_hash=canonical_hash(body),
    )


def _summary(result: AuditWorkflowResult) -> dict:
    return {
        "schema": 1,
        "status": result.status.value,
        "result_hash": result.result_hash,
        "run_hash": result.run_manifest.run_hash,
        "buyer_id": result.run_manifest.buyer_id,
        "business_unit": result.run_manifest.business_unit,
        "charge_count": result.run_manifest.charge_count,
        "invoice_count": result.run_manifest.invoice_count,
        "rule_count": result.run_manifest.rule_count,
        "clear_count": result.factory.clear_count,
        "validated_count": result.factory.validated_count,
        "review_count": result.factory.review_count,
        "review_case_count": result.run_manifest.review_case_count,
        "review_packet_hash": result.review_packet.packet_hash,
        "truth_hash": result.factory.truth.truth_hash,
        "claim_boundary": (
            "Amounts in the review packet are discrepancies for review, not realized savings."
        ),
    }


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def write_audit_result_package(
    result: AuditWorkflowResult,
    destination: Path | str,
) -> dict:
    path = Path(destination)
    if path.exists() and any(path.iterdir()):
        raise ValueError("audit result destination must be new or empty")
    path.mkdir(parents=True, exist_ok=True)

    entries = {
        "audit-run-manifest.json": _json_bytes(asdict(result.run_manifest)),
        "audit-summary.json": _json_bytes(_summary(result)),
        "review-packet.md": render_review_packet_markdown(result.review_packet).encode("utf-8"),
    }
    entry_manifest = [
        {
            "path": name,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for name, data in sorted(entries.items())
    ]
    package_body = {
        "schema": 1,
        "run_hash": result.run_manifest.run_hash,
        "result_hash": result.result_hash,
        "entries": entry_manifest,
    }
    package_manifest = package_body | {
        "package_hash": canonical_hash(package_body)
    }
    entries["PACKAGE_MANIFEST.json"] = _json_bytes(package_manifest)

    for name, data in entries.items():
        (path / name).write_bytes(data)
    return package_manifest


def _read_rule_source(spec_dir: Path, row: dict) -> RuleSourceInput:
    required = (
        "rule_csv_path",
        "customer_id",
        "carrier_id",
        "currency",
        "authority_document_id",
        "authority_document_path",
        "verified_controlling_authority",
    )
    missing = [key for key in required if key not in row]
    if missing:
        raise ValueError("rule source missing fields: " + ",".join(missing))
    if type(row["verified_controlling_authority"]) is not bool:
        raise ValueError("verified_controlling_authority must be a boolean")

    rule_path = (spec_dir / str(row["rule_csv_path"])).resolve()
    authority_path = (spec_dir / str(row["authority_document_path"])).resolve()
    return RuleSourceInput(
        rule_filename=rule_path.name,
        rule_csv=rule_path.read_bytes(),
        customer_id=str(row["customer_id"]),
        carrier_id=str(row["carrier_id"]),
        currency=str(row["currency"]),
        authority_document_id=str(row["authority_document_id"]),
        authority_document_data=authority_path.read_bytes(),
        verified_controlling_authority=row["verified_controlling_authority"],
    )


def request_from_trusted_spec(spec_path: Path | str) -> AuditWorkflowRequest:
    path = Path(spec_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "buyer_id",
        "business_unit",
        "selection_rule",
        "invoice_csv_path",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError("trusted spec missing fields: " + ",".join(missing))
    spec_dir = path.parent
    invoice_path = (spec_dir / str(raw["invoice_csv_path"])).resolve()
    rule_sources = tuple(
        _read_rule_source(spec_dir, row)
        for row in raw.get("rule_sources", [])
    )
    return AuditWorkflowRequest(
        buyer_id=str(raw["buyer_id"]),
        business_unit=str(raw["business_unit"]),
        selection_rule=str(raw["selection_rule"]),
        invoice_filename=invoice_path.name,
        invoice_csv=invoice_path.read_bytes(),
        rule_sources=rule_sources,
    )


def run_audit_spec(
    spec_path: Path | str,
    destination: Path | str,
) -> AuditWorkflowResult:
    result = run_audit_workflow(request_from_trusted_spec(spec_path))
    write_audit_result_package(result, destination)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one controlled Freight Recovery pre-review audit workflow."
    )
    parser.add_argument("trusted_spec")
    parser.add_argument("output_directory")
    args = parser.parse_args()
    result = run_audit_spec(args.trusted_spec, args.output_directory)
    print(json.dumps(_summary(result), sort_keys=True))


if __name__ == "__main__":
    main()
