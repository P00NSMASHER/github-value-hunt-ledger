"""RETALLY Lab 14 / M45: atomic runtime-operation safety over durable SQLite.

M44 guarded reopen, explicit audits and report snapshots but ordinary
monetary reads and already-open write operations could still trust
privileged-corrupted source rows. M45 makes every read and write transaction
validate structural settlement semantics before returning or committing.

Run eight existing M44 disposable SQLite mutations against FIVE previously
unguarded read surfaces plus a write attempt. Test-only data, synthetic actors,
no external bank/carrier/buyer authentication or original defect closure.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import tempfile

from freight.lab_assurance import digest
from freight.lab_persistent_semantic_m44 import (
    ATTACKS as M44_ATTACKS, _attack as mutate_test_sqlite,
    _raw_digest as digest_test_sqlite,
)
from freight.settlement_store import SettlementEventRecord
from freight.test_lab_phase3_real_chain import funded_store

SCOPE = "RETALLY_LAB14_M45_ATOMIC_PERSISTENT_FINANCIAL_OPERATION_GATES_SYNTHETIC_ONLY"
READ_SURFACES = (
    "realized_cents",
    "fee_eligible_cents",
    "claim_residual",
    "event_residual",
    "count",
)
WRITE_SURFACE = "new_provider_event"
EXPECTED_READS = {
    "realized_cents": 500,
    "fee_eligible_cents": 500,
    "claim_residual": 500,
    "event_residual": 0,
    "count": 2,
}


def _actions(store) -> dict:
    """Closed set of six actual SettlementStore APIs, not caller-created SQL."""
    return {
        "realized_cents": store.realized_cents,
        "fee_eligible_cents": store.fee_eligible_cents,
        "claim_residual": lambda: store.claim_residual("case-1"),
        "event_residual": lambda: store.event_residual("credit-400"),
        "count": lambda: store.count("allocations"),
        "new_provider_event": lambda: store.ingest_event(
            SettlementEventRecord(
                "m45-sim-new-credit", "INV-100",
                "SIM-CARRIER", "SIM-BUYER", "USD", 1,
                "2026-12-20T12:00:00Z",
                sha256(b"m45-test-only-new-carrier-source").hexdigest(),
                "EXTERNAL",
            )
        ),
    }


def replay_one(scenario: str) -> dict:
    if type(scenario) is not str or scenario not in M44_ATTACKS:
        raise ValueError("M45_UNREGISTERED_PERSISTENT_SOURCE_ATTACK")
    with tempfile.TemporaryDirectory(prefix="retally-m45-isolated-atomic-") as temp:
        store = funded_store(temp)
        db = Path(store.path)
        operations = _actions(store)
        good = {name: operations[name]() for name in READ_SURFACES}
        if good != EXPECTED_READS:
            raise ValueError("M45_POSITIVE_PERSISTENT_SETTLEMENT_CONTROL_FAILED")
        before = digest_test_sqlite(db)
        mutate_test_sqlite(db, scenario)
        corrupted = digest_test_sqlite(db)
        if before == corrupted:
            raise ValueError("M45_ADVERSARIAL_SQLITE_MUTATION_NOT_APPLIED")
        if set(operations) != {*READ_SURFACES, WRITE_SURFACE}:
            raise ValueError("M45_UNEXPECTED_OPERATION_SURFACES")
        expected = M44_ATTACKS[scenario]
        denied = []
        for operation in (*READ_SURFACES, WRITE_SURFACE):
            try:
                operations[operation]()
            except RuntimeError as exc:
                if expected not in str(exc):
                    raise ValueError(
                        "M45_WRONG_TYPED_SOURCE_DENIAL:" + scenario + ":" + operation
                    ) from exc
                denied.append(operation)
            else:
                raise ValueError(
                    "M45_DAMAGED_FINANCIAL_SQLITE_WAS_ACCEPTED:" +
                    scenario + ":" + operation
                )
        if digest_test_sqlite(db) != corrupted:
            raise ValueError("M45_REJECTED_OPERATION_MODIFIED_CORRUPTED_SOURCE")
        return {
            "source_attack": scenario,
            "exact_source_error_code": expected,
            "positive_read_surfaces_passed": len(good),
            "read_operation_denials": len(READ_SURFACES),
            "write_operation_denials": 1,
            "verified_denied_operation_ids": denied,
            "positive_control_is_fictional_sqlite_only": True,
            "source_hash_changed_after_test_mutation": True,
            "rejected_actions_left_source_unchanged": True,
            "pre_corruption_synthetic_source_digest": before,
            "post_corruption_synthetic_source_digest": corrupted,
            "independently_verified_bank_or_buyer_authority": False,
            "archived_vulnerable_revision_replayed": False,
            "original_historical_finding_closed": False,
        }


def run_campaign(*, as_of: date) -> dict:
    if type(as_of) is not date or as_of < date(2026, 10, 13):
        raise ValueError("M45_INVALID_RESEARCH_AS_OF")
    cases = [replay_one(name) for name in M44_ATTACKS]
    if (len(cases) != 8
        or any(
            case["exact_source_error_code"] != M44_ATTACKS[case["source_attack"]]
            or case["read_operation_denials"] != len(READ_SURFACES)
            or case["write_operation_denials"] != 1
            or case["rejected_actions_left_source_unchanged"] is not True
            for case in cases
        )):
        raise ValueError("M45_TRANSACTIONAL_FINANCIAL_GUARDS_NOT_PROVEN")
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of": as_of.isoformat(),
        "original_research_lab_count": 14,
        "new_lab_created": False,
        "original_corpus_is_unmodified": True,
        "corrupted_persistent_source_scenarios": len(cases),
        "known_good_fictional_read_surfaces_per_source": len(READ_SURFACES),
        "current_financial_read_denials": len(cases) * len(READ_SURFACES),
        "current_financial_write_denials": len(cases),
        "total_fail_closed_financial_operations": len(cases) * (len(READ_SURFACES) + 1),
        "all_rejected_financial_operations_left_source_unmodified": True,
        "financial_reconciliation_observes_one_pinned_sqlite_revision": True,
        "pre_and_post_commit_semantic_validation_enabled": True,
        "source_authenticity_or_bank_signature_established": False,
        "current_original_historical_findings_open": 26,
        "current_original_historical_findings_closed": 0,
        "independent_human_first_customer_pilot_controls_unmet": 18,
        "actual_customer_transactions_imported": 0,
        "actual_customer_cash_recovered_usd": None,
        "external_commercial_approval_granted": False,
        "production_deployment_or_schedule_changed": False,
        "cases": cases,
        "caveat": (
            "M45 validates current local persistent SettlementStore structure "
            "under a single SQLite revision for already-open money reads and "
            "writes, and fails closed on 8 different corrupt test-only "
            "databases. It does not establish independently signed actual "
            "buyer/carrier/bank evidence, authentic original data, a hostile "
            "operator proof, monetary accuracy or real customer clearance. "
            "The original 26 frozen historical findings and 18 real human "
            "first-customer approvals remain unsatisfied. Performance at "
            "real customer scale has not been benchmarked."
        ),
    }
    body["receipt_sha256"] = digest(body)
    return body


def render_html(report: dict) -> str:
    cards = "".join(
        "<tr><th>" + escape(row["source_attack"]) +
        "</th><td>" + escape(row["exact_source_error_code"]) +
        "</td><td>" + str(row["read_operation_denials"]) +
        "</td><td>" + str(row["write_operation_denials"]) +
        "</td></tr>"
        for row in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>RETALLY M45 Atomic Financial Read and Write Assurance</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f4f7f3;'
        'color:#1f3e30;max-width:1000px;margin:auto;padding:25px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'th,td{border-bottom:1px solid #dce8dd;padding:12px;text-align:left}'
        'small{color:#69776e}</style></head><body>'
        '<small>RETALLY / LAB 14 / M45 / OFFLINE SYNTHETIC ONLY</small>'
        '<h1>Atomic settlement-operation fail-closed verification</h1>'
        '<p>Eight invalid durable SQLite source variants denied on forty '
        'cash/fee/residual/count reads and eight attempted writes. '
        'Existing historical findings: 26 open / 0 closed. '
        'Real original bank and carrier authorization: none.</p>'
        '<table><thead><tr><th>Corrupted source</th><th>Typed reason</th>'
        '<th>Read blocks</th><th>Write blocks</th></tr></thead>'
        '<tbody>' + cards + '</tbody></table><p><small>' +
        escape(report["caveat"]) + '</small></p></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline read/write atomic safety check")
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "atomic_financial_operations_m45.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "atomic_financial_operations_m45.html").write_text(
        render_html(report), encoding="utf-8",
    )
    print(json.dumps({
        "source_attacks": 8,
        "read_denials": report["current_financial_read_denials"],
        "write_denials": report["current_financial_write_denials"],
        "original_findings_closed": 0,
        "receipt_sha256": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
