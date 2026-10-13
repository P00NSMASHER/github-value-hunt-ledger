"""RETALLY existing Lab 14 M42: legacy SQLite duplicate-row identity protection.

Tests actual freight.lab_assurance verification against imported, deliberately
UNCONSTRAINED fictional SQLite tables. Production SettlementStore already has
stronger schema constraints; this closes the separate *read-only independent
verifier* boundary that formerly converted repeated row identifiers to a
dictionary before noticing duplicates. No original historical defect is closed.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sqlite3
import tempfile

from freight.lab_assurance import AssuranceRejected, digest, verify_settlement
from freight.test_lab_assurance import (
    BUYER, BU, assertions_and_fees, populate, verifier,
)

SCOPE = "RETALLY_LAB14_M42_INDEPENDENT_SETTLEMENT_ROW_IDENTITY_SYNTHETIC_ONLY"
ATTACKS = (
    ("ALLOCATION", "allocations", "allocation_id", "allocation-400",
     "DUPLICATE_ALLOCATION_ID"),
    ("COUNTER", "counter_events", "counter_id", "return-500",
     "DUPLICATE_COUNTER_ID"),
    ("REVERSAL", "reversal_edges", "reversal_id", "reversal-500",
     "DUPLICATE_OR_INVALID_REVERSAL_ID"),
)
EXPECTED_USD = {
    "recovered_cents": 500,
    "earned_fee_cents": 100,
    "invoiced_fee_cents": 100,
    "collected_fee_cents": 100,
    "fee_receivable_cents": 0,
    "fee_refund_due_cents": 0,
    "written_off_cents": 0,
}


def _observe(db: Path, proofs: list, fee_events: list):
    return verify_settlement(
        db, buyer_id=BUYER, business_unit=BU,
        assertions=proofs, fee_events=fee_events, verifier=verifier()
    )


def _attack(db: Path, scenario: str) -> dict:
    """Mutate only the bounded disposable test database, never user data."""
    cases = {a[0]: a for a in ATTACKS}
    if type(scenario) is not str or scenario not in cases:
        raise ValueError("M42_UNREGISTERED_IDENTITY_ATTACK")
    _, table, field, target, _ = cases[scenario]
    # Table and field are hardcoded internal constants, NOT caller-supplied SQL.
    with sqlite3.connect(db) as con:
        before = con.execute(
            f"SELECT COUNT(*),COUNT(DISTINCT {field}) FROM {table} "
            f"WHERE {field}=?", (target,)
        ).fetchone()
        if before != (1, 1):
            raise ValueError("M42_EXPECTED_SINGLE_ORIGINAL_ROW_MISSING")
        if scenario == "ALLOCATION":
            con.execute(
                "INSERT INTO allocations SELECT * FROM allocations "
                "WHERE allocation_id='allocation-400'"
            )
        elif scenario == "COUNTER":
            con.execute(
                "INSERT INTO counter_events SELECT * FROM counter_events "
                "WHERE counter_id='return-500'"
            )
        else:
            # Preserve the economic aggregate of the original reversal
            # (499+1=500) while duplicating its identity. A simple amount
            # comparison would therefore miss the conflicting rows.
            con.execute(
                "UPDATE reversal_edges SET amount_cents=499 "
                "WHERE reversal_id='reversal-500'"
            )
            con.execute(
                "INSERT INTO reversal_edges "
                "SELECT buyer_id,business_unit,reversal_id,counter_id,"
                "allocation_id,1,created_at FROM reversal_edges "
                "WHERE reversal_id='reversal-500'"
            )
        after = con.execute(
            f"SELECT COUNT(*),COUNT(DISTINCT {field}) FROM {table} "
            f"WHERE {field}=?", (target,)
        ).fetchone()
    if after != (2, 1):
        raise ValueError("M42_DUPLICATE_IDENTITY_PROBE_DID_NOT_RUN")
    return {
        "source_table": table,
        "identity_column": field,
        "before_row_count": before[0],
        "after_row_count": after[0],
        "after_distinct_identity_count": after[1],
        "actual_duplicate_present_in_disposable_sqlite": True,
    }


def replay_one(scenario: str) -> dict:
    cases = {a[0]: a for a in ATTACKS}
    if type(scenario) is not str or scenario not in cases:
        raise ValueError("M42_UNKNOWN_DUPLICATE_SOURCE_SCENARIO")
    expected_code = cases[scenario][4]
    with tempfile.TemporaryDirectory(prefix="retally-m42-unconstrained-sqlite-") as root:
        db = Path(root) / "isolated-test-only.sqlite3"
        populate(db)  # Explicitly no PK constraints: simulates a legacy import.
        proofs, events = assertions_and_fees()
        positive = _observe(db, proofs, events)
        if (positive.status != "PASS_SYNTHETIC_ONLY"
            or positive.scope != "SIGNED_SYNTHETIC_EVIDENCE_ONLY"
            or positive.verified_claims != 1
            or positive.verified_receipts != 2
            or positive.currency_totals != {"USD": EXPECTED_USD}):
            raise ValueError("M42_KNOWN_GOOD_SYNTHETIC_SETTLEMENT_REJECTED")
        before = sha256(db.read_bytes()).hexdigest()
        mutation = _attack(db, scenario)
        after = sha256(db.read_bytes()).hexdigest()
        if after == before:
            raise ValueError("M42_SQLITE_ATTACK_NOT_APPLIED")
        try:
            _observe(db, proofs, events)
        except AssuranceRejected as exc:
            if exc.code != expected_code:
                raise ValueError(
                    "M42_WRONG_DUPLICATE_ROW_REJECTION:" + scenario + ":" + exc.code
                ) from exc
        else:
            raise ValueError(
                "M42_VERIFIER_SILENTLY_ACCEPTED_DUPLICATE_SQLITE_ROWS:" + scenario
            )
        return {
            "scenario": scenario,
            "current_verifier_expected_denial": expected_code,
            "current_verifier_actual_denial": expected_code,
            "positive_control_verified_with_test_only_signers": True,
            "negative_case_rejected_exactly": True,
            "source_row_observation": mutation,
            "isolated_before_sha256": before,
            "isolated_after_sha256": after,
            "legacy_import_without_primary_key_constraints": True,
            "historical_vulnerable_revision_replayed": False,
            "historical_defect_closed": False,
            "real_customer_cash_or_bank_receipt_proven": False,
        }


def run_campaign(*, as_of: date) -> dict:
    if type(as_of) is not date or as_of < date(2026, 10, 13):
        raise ValueError("M42_INVALID_AS_OF_DATE")
    cases = [replay_one(spec[0]) for spec in ATTACKS]
    if (len(cases) != 3
        or any(x["current_verifier_actual_denial"] !=
               dict((spec[0], spec[4]) for spec in ATTACKS)[x["scenario"]]
               or not x["negative_case_rejected_exactly"]
               for x in cases)):
        raise ValueError("M42_ROW_IDENTITY_PROBE_INCOMPLETE")
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of": as_of.isoformat(),
        "existing_lab_number": 14,
        "new_lab_created": False,
        "source": "CURRENT_FREIGHT_LAB_ASSURANCE_WITH_LEGACY_TEST_ONLY_SQLITE",
        "unconstrained_duplicate_row_attacks": 3,
        "independent_verifier_expected_denials": 3,
        "cases": cases,
        "historical_original_findings_open": 26,
        "historical_original_findings_closed": 0,
        "original_vulnerable_baseline_replays": 0,
        "separate_human_pilot_controls_unmet": 18,
        "actual_real_customer_transactions_imported": 0,
        "actual_verified_cash_recovered_usd": None,
        "external_publication_claims_authorized": 0,
        "source_tests_are_not_real_bank_or_carrier_attestation": True,
        "no_customer_contact_production_deployment_or_schedules": True,
        "caveat": (
            "M42 protects independent read-only reconciliation of untrusted "
            "legacy SQLite rows. Three duplicated identifier classes were "
            "rejected using existing current Python verifier code and "
            "mocked buyer/carrier/bank test signers. These tests do not "
            "prove an original vulnerable historical source revision was "
            "replayed, that the original 26 findings were repaired, that "
            "actual buyer/provider financial records were authenticated, "
            "or that any public recovery/commercial claim is authorized."
        ),
    }
    body["receipt_sha256"] = digest(body)
    return body


def render_html(result: dict) -> str:
    sections = "".join(
        '<article><h2>' + escape(x["scenario"]) + '</h2><p>' +
        escape(x["source_row_observation"]["source_table"]) +
        ': <strong>' + escape(x["current_verifier_actual_denial"]) +
        '</strong> (2 records, 1 identity).</p></article>'
        for x in result["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | M42 SQLite Row Identity Evidence</title>'
        '<style>body{font:15px/1.6 system-ui;max-width:1000px;margin:auto;'
        'padding:24px;background:#f4f7f5;color:#20382b}article{padding:16px;'
        'border:1px solid #dbe7dc;border-radius:12px;background:white;'
        'margin:12px 0}</style></head><body>'
        '<small>RETALLY LAB 14 / M42 / INTERNAL ONLY</small>'
        '<h1>Duplicate financial row identifiers fail closed</h1>'
        '<p>Three constrained current-verifier negative probes passed. '
        'The original 26 historical findings remain OPEN_UNVERIFIED; no '
        'real customer cash or bank authority was tested.</p>' +
        sections + '<small>' + escape(result["caveat"]) + '</small></body></html>'
    )


def main() -> None:
    p = argparse.ArgumentParser(description="No-network isolated ledger identity test")
    p.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    report = run_campaign(as_of=a.as_of_date)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "settlement_identity_m42.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (a.out / "settlement_identity_m42.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({
        "duplicate_identity_attacks_rejected": 3,
        "historical_findings_closed": 0,
        "pilot_gate_controls_unmet": 18,
        "receipt_sha256": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
