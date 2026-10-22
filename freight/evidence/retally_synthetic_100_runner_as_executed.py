"""Offline, source-pinned RETALLY synthetic evidence-lab audit rehearsal.
Runs 100 distinct three-invoice FULL lifecycles through actual project modules
and 100 separate intentionally varied pre-review audit fault-injection probes.
No original PDFs, real payment events, external provider calls or customer actions.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from freight import synthetic_rehearsal as sr
from freight.audit_workflow import RuleCSVInput, run_audit_workflow

ROOT = Path(__file__).resolve().parent
EXPECTED_HEAD = "7a43c19f0b298285a28b46ff1fd0f3d4349f4344"
HEAD = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
if HEAD != EXPECTED_HEAD:
    raise SystemExit("REFUSED_SOURCE_HEAD_MISMATCH")
ORIGINAL_INVOICE = sr.INVOICE_CSV
ORIGINAL_SETTLEMENT = sr.SETTLEMENT_CSV
ORIGINAL_SCENARIO_ID = sr.SCENARIO_ID

INVOICE_HEADER = ("invoice_id,shipment_id,customer_id,carrier_id,currency,"
                  "charge_id,charge_code,service_date,quantity_units,billed_cents\n")
RULE_HEADER = "charge_code,pricing_model,effective_from,effective_to,fixed_cents,unit_rate_cents\n"
RULE_LINE = "DETENTION,FIXED,2026-09-01,2026-09-30,10000,\n"
CATEGORIES = (
    "verified-overbill",
    "verified-exact",
    "verified-underbill",
    "unverified-rate-authority",
    "missing-rate-authority",
    "invalid-service-date",
    "conflicting-invoice-identity",
    "incomplete-fixed-rate",
    "mismatched-currency",
    "fractional-cent-input",
    "negative-billed-cents",
    "unicode-numeric-alias",
    "duplicate-charge-evidence",
)

def changed_sources(i: int) -> tuple[bytes, bytes]:
    prefix = f"SIM-{i:03d}"
    invoice = ORIGINAL_INVOICE
    settlement = ORIGINAL_SETTLEMENT
    for n in (1, 2, 3):
        invoice = invoice.replace(f"inv-{n}".encode(), f"{prefix}-inv-{n}".encode())
        invoice = invoice.replace(f"shp-{n}".encode(), f"{prefix}-shp-{n}".encode())
    for n in (1, 2):
        settlement = settlement.replace(f"inv-{n}".encode(), f"{prefix}-inv-{n}".encode())
    service_date = (date(2026, 9, 1) + timedelta(days=i % 15)).isoformat()
    invoice = invoice.replace(b"2026-09-15", service_date.encode())
    return invoice, settlement

def sample_invoice(i: int, cents="12500", when="2026-09-12", currency="USD", customer="cust", suffix="0") -> str:
    return (f"SIM-{i:03d},SHIP-{i:03d},{customer},carrier,{currency},"
            f"CHG-{i:03d}-{suffix},DETENTION,{when},1,{cents}\n")

def audit_probe(i: int) -> dict:
    category = CATEGORIES[i % len(CATEGORIES)]
    kwargs = {}
    invoice_row = sample_invoice(i)
    if category == "verified-exact":
        invoice_row = sample_invoice(i, cents="10000")
    elif category == "verified-underbill":
        invoice_row = sample_invoice(i, cents="9500")
    elif category == "invalid-service-date":
        invoice_row = sample_invoice(i, when="09/12/2026")
    elif category == "conflicting-invoice-identity":
        invoice_row += sample_invoice(i, customer="other-customer", suffix="1")
    elif category == "mismatched-currency":
        invoice_row = sample_invoice(i, currency="EUR")
    elif category == "fractional-cent-input":
        invoice_row = sample_invoice(i, cents="12500.5")
    elif category == "negative-billed-cents":
        invoice_row = sample_invoice(i, cents="-100")
    elif category == "unicode-numeric-alias":
        invoice_row = sample_invoice(i, cents="１２５００")
    elif category == "duplicate-charge-evidence":
        invoice_row += invoice_row
    rule_line = "DETENTION,FIXED,2026-09-01,2026-09-30,,\n" if category == "incomplete-fixed-rate" else RULE_LINE
    spec = RuleCSVInput(
        filename="synthetic-rate.csv",
        data=(RULE_HEADER + rule_line).encode(),
        customer_id="cust", carrier_id="carrier", currency="USD",
        authority_document_id="SYNTHETIC-ONLY",
        source_document_sha256=None,
        source_document_data=f"SYNTHETIC-NONCONTRACT-AUTHORITY-{i}".encode(),
        verified_controlling_authority=category != "unverified-rate-authority",
    )
    outcome = run_audit_workflow(
        invoice_filename="synthetic-invoices.csv",
        invoice_data=(INVOICE_HEADER + invoice_row).encode(),
        buyer_id="buyer-synthetic", business_unit="unit-synthetic",
        selection_rule="synthetic offline fault-injection",
        rule_inputs=() if category == "missing-rate-authority" else (spec,),
    )
    blocked = {
        "invalid-service-date": "INVOICE_INGEST",
        "conflicting-invoice-identity": "POPULATION_FREEZE",
        "incomplete-fixed-rate": "RULE_INGEST",
        "fractional-cent-input": "INVOICE_INGEST",
        "negative-billed-cents": "INVOICE_INGEST",
        "unicode-numeric-alias": "INVOICE_INGEST",
        "duplicate-charge-evidence": "INVOICE_INGEST",
    }
    if category in blocked:
        assert outcome.state == "BLOCKED" and outcome.stage == blocked[category], (
            f"{category}: expected fail-closed at {blocked[category]}, got {outcome.state}/{outcome.stage}")
        assert outcome.summary is None and outcome.artifacts is None
    elif category in ("verified-exact", "verified-underbill"):
        assert outcome.state == "CLEAN" and outcome.summary is not None
        assert outcome.summary.validated_finding_count == 0
        assert outcome.summary.review_finding_count == 0
    else:
        assert outcome.state == "REVIEW_REQUIRED" and outcome.summary is not None
        assert outcome.artifacts is not None
        if category == "verified-overbill":
            assert outcome.summary.validated_finding_count == 1
            assert outcome.summary.validated_discrepancy_cents == 2500
        elif category == "unverified-rate-authority":
            assert outcome.summary.validated_finding_count == 0
            assert outcome.summary.review_finding_count == 1
        elif category in ("missing-rate-authority", "mismatched-currency"):
            assert outcome.summary.validated_finding_count == 0
            assert outcome.summary.unknown_expected_count == 1
    return {"category": category, "state": outcome.state, "stage": outcome.stage,
            "error_code": outcome.error_code, "manifest": outcome.summary.run_hash if outcome.summary else None}

rows = []
failures = []
counts = Counter()
audit_hashes = set()
settlement_hashes = set()
for i in range(100):
    try:
        inp, settlement = changed_sources(i)
        sr.INVOICE_CSV = inp
        sr.SETTLEMENT_CSV = settlement
        sr.SCENARIO_ID = f"SYNTHETIC-LAB-FREIGHT-AUDIT-{i:03d}"
        result = sr.run_rehearsal()
        expected = {
            "synthetic": True,
            "population_invoice_count": 3,
            "population_charge_count": 3,
            "audit_workflow_state": "REVIEW_REQUIRED",
            "buyer_review_confirmed_count": 2,
            "recovery_claim_count": 2,
            "carrier_action_external_action_simulated": True,
            "carrier_action_external_action_performed": False,
            "settlement_event_count": 2,
            "counter_event_count": 1,
            "commercial_value_claimed": False,
        }
        for field, value in expected.items():
            assert result[field] == value, (field, result[field], value)
        assert result["persistent_reporting"]["stale_report_rejected"] is True
        assert result["audit_result_bundle_entry_count"] == 14
        assert result["audit_result_bundle_sha256"] and len(result["audit_result_bundle_sha256"]) == 64
        assert result["metrics"]["realized_cents"] == result["persistent_store"]["realized_cents"]
        assert result["metrics"]["fee_eligible_realized_cents"] == result["persistent_store"]["fee_eligible_cents"]
        assert result["audit_run_hash"] not in audit_hashes, "nonunique audited population manifest"
        audit_hashes.add(result["audit_run_hash"])
        settlement_hashes.add(result["persistent_reporting"]["settlement_snapshot_hash"])
        probe = audit_probe(i)
        counts[probe["category"] + ":" + probe["state"]] += 1
        rows.append({
            "case": f"SYNTH-AUDIT-{i:03d}",
            "invoice_fixture_sha256": sha256(inp).hexdigest(),
            "declared_settlement_fixture_sha256": sha256(settlement).hexdigest(),
            "audit_manifest_sha256": result["audit_run_hash"],
            "bundle_sha256": result["audit_result_bundle_sha256"],
            "snapshot_sha256": result["persistent_reporting"]["settlement_snapshot_hash"],
            "probe": probe,
            "external_action_performed": False,
            "customer_money_observed": False,
        })
    except Exception as exc:
        failures.append({"case": i, "error_class": type(exc).__name__,
                         "failure": str(exc)[:200]})
    finally:
        sr.INVOICE_CSV = ORIGINAL_INVOICE
        sr.SETTLEMENT_CSV = ORIGINAL_SETTLEMENT
        sr.SCENARIO_ID = ORIGINAL_SCENARIO_ID
    if (i + 1) % 25 == 0:
        print(f"CHECKPOINT processed={i+1} full_success={len(rows)} failures={len(failures)}", flush=True)

canonical_cases = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
report = {
    "schema": 1,
    "classification": "SYNTHETIC_ONLY_NOT_CUSTOMER_FREIGHT_ACCURACY",
    "source": {
        "repository": "P00NSMASHER/github-value-hunt-ledger",
        "commit": HEAD,
        "full_lifecycle_module": "freight/synthetic_rehearsal.py",
        "pre_review_module": "freight/audit_workflow.py",
        "base_invoice_fixture_sha256": sha256(ORIGINAL_INVOICE).hexdigest(),
        "base_settlement_fixture_sha256": sha256(ORIGINAL_SETTLEMENT).hexdigest(),
        "lab_result_doc_sha256": sha256((ROOT / "freight/REAL_DOCUMENT_LAB_RESULTS_2026-10-20.md").read_bytes()).hexdigest(),
        "phase3_synthetic_gold_fixture_sha256": sha256((ROOT / "freight/fixtures/phase3_accuracy_gold_v1.json").read_bytes()).hexdigest(),
        "original_document_bytes_refetched": False,
    },
    "observed": {
        "requested_full_lifecycle_audits": 100,
        "full_lifecycle_audits_passed": len(rows),
        "full_lifecycle_audits_failed": len(failures),
        "distinct_freight_invoice_identities": 3 * len(rows),
        "distinct_full_lifecycle_run_hashes": len(audit_hashes),
        "distinct_synthetic_settlement_snapshots": len(settlement_hashes),
        "pre_review_fault_injection_cases_tested": sum(counts.values()),
        "probe_categories_and_outcomes": dict(sorted(counts.items())),
        "verified_real_settlements": None,
        "independently_adjudicated_original_freight_labels": None,
        "real_false_positive_rate": None,
        "real_false_negative_rate": None,
    },
    "cases_sha256": sha256(canonical_cases).hexdigest(),
    "cases": rows,
    "failures": failures,
    "limitations": [
        "Source-pinned synthetic fixture variants, not 100 independent real freight invoices.",
        "Fictional approvals, carrier actions, credit memos and reversals are simulated locally, not observed external events.",
        "No customer bank payments, carrier tariffs, independent adjudications or recovered funds verified.",
        "Lab real-document totals are historical reference, not rerun or revalidated here.",
        "No software engine or public GitHub files changed, and no network actions initiated by this script."
    ],
}
out = ROOT / "_retally_simulation_100_report.json"
out.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
print("FINAL_SUMMARY=" + json.dumps({**report["observed"], "source_commit": HEAD, "cases_sha256": report["cases_sha256"], "local_report": str(out)}, sort_keys=True), flush=True)
if failures or len(rows) != 100 or len(audit_hashes) != 100 or sum(counts.values()) != 100:
    sys.exit(1)
