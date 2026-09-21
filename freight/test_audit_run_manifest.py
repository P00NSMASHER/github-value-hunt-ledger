from dataclasses import replace

import pytest

from freight.audit_run_manifest import build_audit_run_manifest, verify_audit_run_manifest
from freight.finding_factory import derive_batch
from freight.invoice_csv_adapter import parse_invoice_charge_csv
from freight.population_builder import build_population_from_charge_batch
from freight.review_packet import build_review_packet
from freight.review_queue import build_review_queue
from freight.rule_csv_adapter import parse_charge_rule_csv


INVOICE_HEADER = "invoice_id,shipment_id,customer_id,carrier_id,currency,charge_id,charge_code,service_date,quantity_units,billed_cents\n"
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"


def setup():
    invoices = parse_invoice_charge_csv(
        filename="charges.csv",
        data=(INVOICE_HEADER
              + "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12500\n"
              + "I2,S2,C,K,USD,X2,MISC,2026-09-10,1,15000\n").encode(),
        buyer_id="buyer",
        business_unit="unit",
    )
    population = build_population_from_charge_batch(
        invoices,
        selection_rule="September accepted charges",
    )
    verified = parse_charge_rule_csv(
        filename="verified.csv",
        data=(RULE_HEADER + "DETENTION,FIXED,2026-09-01,,10000,\n").encode(),
        buyer_id="buyer", business_unit="unit", customer_id="C", carrier_id="K",
        currency="USD", authority_document_id="rate",
        source_document_sha256="a" * 64, verified_controlling_authority=True,
    )
    candidate = parse_charge_rule_csv(
        filename="candidate.csv",
        data=(RULE_HEADER + "MISC,FIXED,2026-09-01,,10000,\n").encode(),
        buyer_id="buyer", business_unit="unit", customer_id="C", carrier_id="K",
        currency="USD", authority_document_id="candidate",
        source_document_sha256="b" * 64, verified_controlling_authority=False,
    )
    rules = verified.rules + candidate.rules
    factory = derive_batch(population.population, invoices.charges, rules)
    queue = build_review_queue(factory)
    packet = build_review_packet(factory, queue, invoices.charges, rules)
    return invoices, population, (verified, candidate), factory, queue, packet


def build():
    invoices, population, rule_batches, factory, queue, packet = setup()
    manifest = build_audit_run_manifest(
        invoice_batch=invoices,
        population_build=population,
        rule_batches=rule_batches,
        factory=factory,
        review_queue=queue,
        review_packet=packet,
    )
    return manifest, (invoices, population, rule_batches, factory, queue, packet)


def test_manifest_binds_complete_pre_review_audit_chain():
    manifest, _ = build()
    assert manifest.charge_count == 2
    assert manifest.invoice_count == 2
    assert manifest.rule_count == 2
    assert manifest.derivation_count == 2
    assert manifest.review_case_count == 2
    assert len(manifest.rule_adapter_hashes) == 2
    assert len(manifest.authority_document_hashes) == 2
    assert len(manifest.run_hash) == 64


def test_manifest_is_deterministic_across_rule_batch_order():
    invoices, population, batches, factory, queue, packet = setup()
    a = build_audit_run_manifest(
        invoice_batch=invoices, population_build=population, rule_batches=batches,
        factory=factory, review_queue=queue, review_packet=packet,
    )
    b = build_audit_run_manifest(
        invoice_batch=invoices, population_build=population, rule_batches=reversed(batches),
        factory=factory, review_queue=queue, review_packet=packet,
    )
    assert a == b


def test_tampered_manifest_fails_verification():
    manifest, parts = build()
    bad = replace(manifest, review_packet_hash="0" * 64)
    with pytest.raises(ValueError, match="does not match"):
        verify_audit_run_manifest(
            bad,
            invoice_batch=parts[0],
            population_build=parts[1],
            rule_batches=parts[2],
            factory=parts[3],
            review_queue=parts[4],
            review_packet=parts[5],
        )


def test_wrong_population_or_queue_is_rejected_before_manifest_creation():
    invoices, population, batches, factory, queue, packet = setup()
    bad_population = replace(population, invoice_charge_adapter_hash="0" * 64)
    with pytest.raises(ValueError, match="invoice adapter"):
        build_audit_run_manifest(
            invoice_batch=invoices, population_build=bad_population, rule_batches=batches,
            factory=factory, review_queue=queue, review_packet=packet,
        )
    with pytest.raises(ValueError, match="review queue"):
        build_audit_run_manifest(
            invoice_batch=invoices, population_build=population, rule_batches=batches,
            factory=factory, review_queue=replace(queue, queue_hash="0" * 64),
            review_packet=packet,
        )


def test_rule_batch_scope_mismatch_is_rejected():
    invoices, population, batches, factory, queue, packet = setup()
    bad = replace(batches[0], buyer_id="other")
    with pytest.raises(ValueError, match="rule batch scope"):
        build_audit_run_manifest(
            invoice_batch=invoices, population_build=population,
            rule_batches=(bad, batches[1]), factory=factory,
            review_queue=queue, review_packet=packet,
        )


def test_changed_invoice_evidence_changes_run_hash():
    a, _ = build()
    invoices, population, batches, _, _, _ = setup()
    changed = parse_invoice_charge_csv(
        filename="charges.csv",
        data=(INVOICE_HEADER
              + "I1,S1,C,K,USD,X1,DETENTION,2026-09-10,1,12501\n"
              + "I2,S2,C,K,USD,X2,MISC,2026-09-10,1,15000\n").encode(),
        buyer_id="buyer", business_unit="unit",
    )
    changed_population = build_population_from_charge_batch(
        changed, selection_rule=population.selection_rule,
    )
    rules = tuple(rule for batch in batches for rule in batch.rules)
    changed_factory = derive_batch(changed_population.population, changed.charges, rules)
    changed_queue = build_review_queue(changed_factory)
    changed_packet = build_review_packet(changed_factory, changed_queue, changed.charges, rules)
    b = build_audit_run_manifest(
        invoice_batch=changed, population_build=changed_population, rule_batches=batches,
        factory=changed_factory, review_queue=changed_queue, review_packet=changed_packet,
    )
    assert a.run_hash != b.run_hash
