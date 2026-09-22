"""Canonical manifest for one Freight Recovery audit run.

The manifest does not contain customer rows. It binds the major proof objects
that define one audit run and re-verifies their cross-object relationships.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from freight.contracts import canonical_hash
from freight.finding_factory import FindingFactoryBatch, derive_batch
from freight.invoice_csv_adapter import InvoiceChargeCSVBatch
from freight.population_builder import PopulationBuild, build_population_from_charge_batch
from freight.review_packet import ReviewPacket, build_review_packet
from freight.review_queue import ReviewQueue, build_review_queue
from freight.rule_csv_adapter import ChargeRuleCSVBatch


@dataclass(frozen=True)
class AuditRunManifest:
    buyer_id: str
    business_unit: str
    invoice_file_sha256: str
    invoice_adapter_hash: str
    population_builder_hash: str
    population_hash: str
    rule_adapter_hashes: tuple[str, ...]
    authority_document_hashes: tuple[str, ...]
    rule_hashes: tuple[str, ...]
    finding_factory_hash: str
    truth_hash: str
    review_queue_hash: str
    review_packet_hash: str
    charge_count: int
    invoice_count: int
    rule_count: int
    derivation_count: int
    review_case_count: int
    run_hash: str


def build_audit_run_manifest(
    *,
    invoice_batch: InvoiceChargeCSVBatch,
    population_build: PopulationBuild,
    rule_batches: Iterable[ChargeRuleCSVBatch],
    factory: FindingFactoryBatch,
    review_queue: ReviewQueue,
    review_packet: ReviewPacket,
) -> AuditRunManifest:
    scope = (invoice_batch.buyer_id, invoice_batch.business_unit)

    if (population_build.buyer_id, population_build.business_unit) != scope:
        raise ValueError("population builder scope mismatch")
    if population_build.invoice_charge_adapter_hash != invoice_batch.adapter_hash:
        raise ValueError("population builder does not reference invoice adapter")
    canonical_population = build_population_from_charge_batch(
        invoice_batch,
        selection_rule=population_build.selection_rule,
    )
    if population_build != canonical_population:
        raise ValueError(
            "population builder does not match the complete accepted invoice batch"
        )
    if population_build.population.manifest_hash != factory.truth.population_hash:
        raise ValueError("Finding Factory truth is not bound to frozen population")

    batches = tuple(rule_batches)
    for batch in batches:
        if (batch.buyer_id, batch.business_unit) != scope:
            raise ValueError("rule batch scope mismatch")

    rules = tuple(rule for batch in batches for rule in batch.rules)
    rule_hashes = tuple(sorted(rule.rule_hash for rule in rules))
    if len(rule_hashes) != len(set(rule_hashes)):
        raise ValueError("duplicate rule proof across rule batches")

    canonical_factory = derive_batch(
        population_build.population,
        invoice_batch.charges,
        rules,
    )
    if factory != canonical_factory:
        raise ValueError(
            "Finding Factory does not cover the complete accepted charge batch"
        )

    canonical_queue = build_review_queue(factory)
    if review_queue != canonical_queue:
        raise ValueError("review queue does not match Finding Factory output")

    canonical_packet = build_review_packet(
        factory,
        review_queue,
        invoice_batch.charges,
        rules,
    )
    if review_packet != canonical_packet:
        raise ValueError("review packet does not match canonical audit evidence")

    if review_packet.truth_hash != factory.truth.truth_hash:
        raise ValueError("review packet truth mismatch")
    if review_packet.factory_hash != factory.factory_hash:
        raise ValueError("review packet factory mismatch")
    if review_packet.queue_hash != review_queue.queue_hash:
        raise ValueError("review packet queue mismatch")

    rule_adapter_hashes = tuple(sorted(batch.adapter_hash for batch in batches))
    authority_document_hashes = tuple(sorted(batch.source_document_sha256 for batch in batches))

    body = {
        "schema": 1,
        "buyer_id": scope[0],
        "business_unit": scope[1],
        "invoice_file_sha256": invoice_batch.file_sha256,
        "invoice_adapter_hash": invoice_batch.adapter_hash,
        "population_builder_hash": population_build.builder_hash,
        "population_hash": population_build.population.manifest_hash,
        "rule_adapter_hashes": rule_adapter_hashes,
        "authority_document_hashes": authority_document_hashes,
        "rule_hashes": rule_hashes,
        "finding_factory_hash": factory.factory_hash,
        "truth_hash": factory.truth.truth_hash,
        "review_queue_hash": review_queue.queue_hash,
        "review_packet_hash": review_packet.packet_hash,
        "charge_count": len(invoice_batch.charges),
        "invoice_count": population_build.invoice_count,
        "rule_count": len(rules),
        "derivation_count": len(factory.derivations),
        "review_case_count": len(review_packet.cases),
    }
    return AuditRunManifest(
        buyer_id=scope[0],
        business_unit=scope[1],
        invoice_file_sha256=invoice_batch.file_sha256,
        invoice_adapter_hash=invoice_batch.adapter_hash,
        population_builder_hash=population_build.builder_hash,
        population_hash=population_build.population.manifest_hash,
        rule_adapter_hashes=rule_adapter_hashes,
        authority_document_hashes=authority_document_hashes,
        rule_hashes=rule_hashes,
        finding_factory_hash=factory.factory_hash,
        truth_hash=factory.truth.truth_hash,
        review_queue_hash=review_queue.queue_hash,
        review_packet_hash=review_packet.packet_hash,
        charge_count=len(invoice_batch.charges),
        invoice_count=population_build.invoice_count,
        rule_count=len(rules),
        derivation_count=len(factory.derivations),
        review_case_count=len(review_packet.cases),
        run_hash=canonical_hash(body),
    )


def verify_audit_run_manifest(
    manifest: AuditRunManifest,
    *,
    invoice_batch: InvoiceChargeCSVBatch,
    population_build: PopulationBuild,
    rule_batches: Iterable[ChargeRuleCSVBatch],
    factory: FindingFactoryBatch,
    review_queue: ReviewQueue,
    review_packet: ReviewPacket,
) -> None:
    expected = build_audit_run_manifest(
        invoice_batch=invoice_batch,
        population_build=population_build,
        rule_batches=rule_batches,
        factory=factory,
        review_queue=review_queue,
        review_packet=review_packet,
    )
    if manifest != expected:
        raise ValueError("audit run manifest does not match current proof objects")
