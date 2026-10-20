"""Reproducible first-party before/after rehearsal; synthetic data only.

This is not a production dataset, independently adjudicated truth, a calibrated
false-positive estimate, or a revenue experiment. Positive review scenarios and
known-benign review burden are reported separately; neither is hidden by a score.
Run: python -m freight.brain_review_measurement
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter_ns

from freight.contracts import PopulationRow, canonical_hash, freeze_population
from freight.duplicate_charge_review import review_duplicate_charges
from freight.finding_factory import InvoiceCharge
from freight.reviewer_cockpit import build_invoice_review_queue

SOURCE_BASE_SHA = "9f68a2a0d22abd671ce7be353506a8b8cf9e5a52"


def scenarios():
    first = InvoiceCharge(buyer_id="synthetic-buyer", business_unit="test-unit",
        invoice_id="INV-1", shipment_id="LOAD-1", customer_id="fictional-customer",
        carrier_id="fictional-carrier", currency="USD", charge_id="C1",
        charge_code="LINEHAUL", service_date="2026-09-10", quantity_units=1,
        billed_cents=100000, source_hash="synthetic-source-1")
    other = replace(first, charge_id="C2", source_hash="synthetic-source-2")
    cross = replace(other, shipment_id="LOAD-2")
    return (
        ("same-shipment-line-repeat", "REVIEW_SCENARIO", (first, other)),
        ("same-shipment-economic-repeat", "REVIEW_SCENARIO", (first, replace(other, invoice_id="INV-2"))),
        ("cross-shipment-reference-repeat", "REVIEW_SCENARIO", (first, cross)),
        ("three-shipment-reference-repeat", "REVIEW_SCENARIO", (first, cross, replace(cross, charge_id="C3", shipment_id="LOAD-3", source_hash="synthetic-source-3"))),
        ("cross-shipment-different-amount", "REVIEW_SCENARIO", (first, replace(cross, billed_cents=120000))),
        ("legitimate-consolidation", "KNOWN_BENIGN_SYNTHETIC_TRUTH", (first, cross)),
        ("legitimate-rebill", "KNOWN_BENIGN_SYNTHETIC_TRUTH", (first, replace(cross, billed_cents=120000))),
        ("different-reference", "NONMATCH_CONTROL", (first, replace(cross, invoice_id="INV-2"))),
        ("different-service-same-shipment", "NONMATCH_CONTROL", (first, replace(other, charge_code="FUEL"))),
        ("different-customer", "NONMATCH_CONTROL", (first, replace(cross, customer_id="other-customer"))),
        ("different-carrier", "NONMATCH_CONTROL", (first, replace(cross, carrier_id="other-carrier"))),
        ("different-currency", "NONMATCH_CONTROL", (first, replace(cross, currency="EUR"))),
    )


def measure():
    rows = []
    for case_id, truth_class, charges in scenarios():
        population_rows = {}
        for c in charges:
            row = PopulationRow(c.invoice_id, c.shipment_id, c.customer_id,
                                c.carrier_id, c.currency, c.source_hash)
            population_rows.setdefault(row.row_key, row)
        population = freeze_population("synthetic-buyer", "test-unit", "SYNTHETIC_ONLY", tuple(population_rows.values()))
        started = perf_counter_ns()
        baseline = review_duplicate_charges(population, charges)
        baseline_ns = perf_counter_ns() - started
        started = perf_counter_ns()
        candidate = build_invoice_review_queue(population, charges)
        candidate_ns = perf_counter_ns() - started
        if baseline.validated_cents != 0 or any(x.amount_cents != 0 for x in candidate.items):
            raise AssertionError("Review evidence gained unauthorized monetary meaning")
        rows.append({"case_id": case_id, "truth_class": truth_class,
            "population_hash": population.manifest_hash,
            "input_hash": canonical_hash([asdict(c) for c in charges]),
            "baseline_reviews": baseline.review_count, "candidate_reviews": len(candidate.items),
            "baseline_batch_hash": baseline.batch_hash, "candidate_queue_hash": candidate.queue_hash,
            "candidate_case_hashes": [x.case_hash for x in candidate.items],
            "baseline_runtime_ns_single_sample": baseline_ns,
            "candidate_runtime_ns_single_sample": candidate_ns})
    summary = {}
    for label in ("REVIEW_SCENARIO", "NONMATCH_CONTROL", "KNOWN_BENIGN_SYNTHETIC_TRUTH"):
        selected = [x for x in rows if x["truth_class"] == label]
        summary[label] = {"cases": len(selected),
            "baseline_cases_flagged": sum(x["baseline_reviews"] > 0 for x in selected),
            "candidate_cases_flagged": sum(x["candidate_reviews"] > 0 for x in selected)}
    base = Path(__file__).parent
    return {"schema_version": 1, "evidence_kind": "SYNTHETIC_FIRST_PARTY_COMPARISON",
        "actor": "ASSISTANT_PREPARED_AND_RUN_NOT_AUTONOMOUS_BRAIN_DEPLOYMENT",
        "source_base_sha": SOURCE_BASE_SHA,
        "source_sha256": {name: hashlib.sha256((base / name).read_bytes()).hexdigest()
                          for name in ("contracts.py", "finding_factory.py", "duplicate_charge_review.py",
                                       "reviewer_cockpit.py", "brain_review_measurement.py")},
        "summary": summary, "cases": rows, "validated_recovery_cents": 0,
        "production_deployed": False, "real_customer_outcome": "NOT_MEASURED",
        "human_time_saved": None, "verified_revenue": None,
        "limits": ["Scenario labels were written by the same developer; no independent adjudication.",
                   "Benign and suspicious examples deliberately share identical detector inputs.",
                   "Two benign cases add human-review burden; invoice identity cannot establish overpayment.",
                   "Single-sample runtimes include cold caches; no speedup or human-time claim.",
                   "Case counts do not establish representative accuracy or customer value."]}


if __name__ == "__main__":
    print(json.dumps(measure(), indent=2, sort_keys=True))
