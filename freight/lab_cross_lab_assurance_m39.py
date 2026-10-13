"""RETALLY Phase 4 / Mission 39: independent cross-lab receipt consistency.

Checks the *entire* existing 14-lab synthetic execution ledger and its
three-customer fictional pilot for false success, forged money, bad provenance,
skipped labs and rehashed negative-probe changes. A SHA receipt is NOT real
provider/buyer/bank evidence, and this code is NOT production certification.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from html import escape
import argparse
import json
from pathlib import Path
import re

from freight.lab_assurance import digest
from freight.lab_phase4_director import LAB_LABELS, BASE_FIVE, EXTENSIONS
from freight.lab_phase3_simulated_pilot import simulated_cohort

SCOPE = "RETALLY_PHASE4_M39_CROSS_LAB_INVARIANT_ASSURANCE_SYNTHETIC_ONLY"
FULL = "ALL_14_LOCAL_SYNTHETIC_MODULES_CONSISTENT_NOT_REAL_CUSTOMER_ASSURANCE"
INCOMPLETE = "INCOMPLETE_OR_BLOCKED_LABS_NO_ACCEPTANCE"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
RECEIPT_FIELDS = {
    "schema", "scope", "production_api_executed", "actual_revenue_cents",
    "hosted_staging_certified", "customer_bank_carrier_authority_proven",
    "source_first_party", "lab_runs", "executed_labs", "failed_or_blocked_labs",
    "three_customer_pilot", "historical_findings_open",
    "laboratory_executions_not_equivalent_to_customer_accuracy",
    "prior_chain_receipt", "receipt_sha256",
}
SUCCESS_FIELDS = {
    "lab", "title", "status", "proof", "negative_probe", "scope", "elapsed_ms",
}
FAILURE_FIELDS = {
    "lab", "title", "status", "reason", "negative_probe", "scope", "elapsed_ms",
}
BUDGET_FIELDS = {
    "lab", "title", "status", "scope", "negative_probe", "elapsed_ms",
}
NEGATIVE_PROBE = {
    1: "INHERITED_PHASE3_VALIDATED_CASES",
    2: "NEGATIVE_REFUND_REJECTED",
    3: "REPORT_VERSION_TAMPER_REJECTED",
    4: "INHERITED_PHASE3_VALIDATED_CASES",
    5: "INHERITED_PHASE3_VALIDATED_CASES",
    6: "BAD_SESSION_COOKIE_REJECTED",
    7: "NEGATIVE_SPEND_REJECTED",
    8: "INHERITED_PHASE3_VALIDATED_CASES",
    9: "MISSING_BUYER_AUTH_REJECTED",
    10: "ALTERED_TARIFF_HASH_REJECTED",
    11: "INHERITED_PHASE3_VALIDATED_CASES",
    12: "NEGATIVE_INSTRUCTION_AMOUNT_REJECTED",
    13: "DOWNWARD_SENSITIVITY_PRESERVED",
    14: "STALE_AND_TAMPERED_SOURCE_ASSERTIONS_REJECTED",
}
DOMAIN_STEP = {
    1: "EXECUTED_REAL_PYTHON_DOMAIN",
    4: "EXECUTED_SYNTHETIC_SIGNED_SOURCE_MATCH",
    5: "EXECUTED_REAL_SETTLEMENT_DOMAIN",
    8: "EXECUTED_CONTINGENCY_MODEL",
    11: "EXECUTED_NEGATIVE_RESTORE_PROBE",
}
PROOF_FIELDS = {
    1: {"phase3_step", "evidence"},
    2: {"synthetic_customer_reactions", "receipt"},
    3: {"fixture", "report_sha256"},
    4: {"phase3_step", "evidence"},
    5: {"phase3_step", "evidence"},
    6: {"validated_controls", "external_security_assurance"},
    7: {"decision", "reasons"},
    8: {"phase3_step", "evidence"},
    9: {"readiness", "score", "external_procurement_certification"},
    10: {"authority_hash", "effective_from", "source_authenticity"},
    11: {"phase3_step", "evidence"},
    12: {"evaluated_payment_cases", "source", "outcome_digest"},
    13: {"modeled_margin_cents", "downside_margin_cents", "actual_customer_margin_cents"},
}
ACTUAL_EXTERNAL_FALSE = (
    "production_api_executed", "hosted_staging_certified",
    "customer_bank_carrier_authority_proven",
)


def _check(ok: object, code: str) -> None:
    if ok is not True:
        raise ValueError("M39_" + code)


def _hex(raw: object) -> bool:
    return type(raw) is str and HEX64.fullmatch(raw) is not None


def _proof(lab: int, proof: dict) -> None:
    _check(type(proof) is dict and bool(proof),
           "EXECUTED_LAB_WITHOUT_STRUCTURED_PROOF")
    expected = PROOF_FIELDS.get(lab)
    if expected is not None:
        _check(set(proof) == expected, "LAB_PROOF_SHAPE_DRIFT")
    if lab in BASE_FIVE:
        _check(proof["phase3_step"] == DOMAIN_STEP[lab]
               and _hex(proof["evidence"]),
               "INHERITED_DOMAIN_SOURCE_PROOF_MISLABELED")
    elif lab == 2:
        _check(type(proof["synthetic_customer_reactions"]) is int
               and proof["synthetic_customer_reactions"] > 0
               and _hex(proof["receipt"]), "SYNTHETIC_PERSONA_PROOF_INVALID")
    elif lab == 3:
        _check(proof["fixture"] == "SYNTHETIC_CODE_ADJACENT_GOLD"
               and _hex(proof["report_sha256"]),
               "BLIND_SYNTHETIC_GOLD_MISLABELED")
    elif lab == 6:
        _check(type(proof["validated_controls"]) is int
               and proof["validated_controls"] > 0
               and proof["external_security_assurance"] == "NOT_PROVEN",
               "EXTERNAL_SECURITY_CERTIFICATION_FABRICATED")
    elif lab == 7:
        _check(type(proof["decision"]) is str
               and type(proof["reasons"]) is list,
               "QUALIFICATION_DECISION_PROOF_INVALID")
    elif lab == 9:
        _check(type(proof["score"]) in (int, float)
               and type(proof["readiness"]) is str
               and proof["external_procurement_certification"] == "NOT_ESTABLISHED",
               "EXTERNAL_PROCUREMENT_ATTESTATION_FABRICATED")
    elif lab == 10:
        _check(_hex(proof["authority_hash"])
               and type(proof["effective_from"]) is str
               and proof["source_authenticity"] == "SYNTHETIC_HUMAN_REVIEW_FLAG",
               "SOURCE_TARIFF_AUTHENTICITY_FABRICATED")
    elif lab == 12:
        _check(type(proof["evaluated_payment_cases"]) is int
               and proof["evaluated_payment_cases"] > 0
               and proof["source"] == "FROZEN_SYNTHETIC_GOLD"
               and _hex(proof["outcome_digest"]),
               "REAL_PAYMENT_OBSERVATION_FABRICATED")
    elif lab == 13:
        _check(type(proof["modeled_margin_cents"]) is int
               and type(proof["downside_margin_cents"]) is int
               and proof["downside_margin_cents"] < proof["modeled_margin_cents"]
               and proof["actual_customer_margin_cents"] is None,
               "ACTUAL_CUSTOMER_MARGIN_FABRICATED")
    elif lab == 14:
        _check(len(proof) >= 35, "RESEARCH_LAB_SOURCE_COVERAGE_UNEXPECTED")
        expected_flags = {
            "research_claim_clearance_external_approvals": 0,
            "research_claim_clearance_pilot_gates_unmet": 18,
            "research_m37_external_publication_authority": False,
            "research_m38_external_claims_authorized": 0,
            "research_m38_human_gates_unmet": 18,
            "research_m38_hypothetical_census_values_quarantined": 4,
            "research_m38_baseline_visible_internal_values": 8,
            "real_invoice_adjudications_completed": 0,
            "rights_cleared_freight_data_imports": 0,
            "independent_customer_studies_completed": 0,
            "ltl_recovery_market_established": False,
            "source_refresh_automated": False,
            "critical_current_path_negative_replays_m41": 4,
            "critical_current_path_denials_m41": 4,
            "critical_original_findings_closed_m41": 0,
            "critical_original_vulnerable_revision_replays_m41": 0,
            "settlement_legacy_duplicate_row_attacks_m42": 3,
            "settlement_legacy_duplicate_row_denials_m42": 3,
            "settlement_current_historical_defects_closed_m42": 0,
            "settlement_source_scenarios_m43": 12,
            "settlement_source_positive_controls_m43": 12,
            "settlement_source_denials_m43": 12,
            "settlement_source_original_defects_closed_m43": 0,
            "persistent_semantic_current_cases_m44": 8,
            "persistent_semantic_current_report_denials_m44": 8,
            "persistent_semantic_reopen_denials_m44": 8,
            "persistent_semantic_historical_findings_closed_m44": 0,
            "atomic_financial_read_denials_m45": 40,
            "atomic_financial_write_denials_m45": 8,
            "atomic_financial_total_denials_m45": 48,
            "atomic_financial_historical_findings_closed_m45": 0,
            "sqlite_schema_mutation_cases_m46": 10,
            "sqlite_schema_read_denials_m46": 70,
            "sqlite_schema_write_denials_m46": 10,
            "sqlite_schema_reopen_denials_m46": 10,
            "sqlite_schema_original_defects_closed_m46": 0,
            "sqlite_file_attack_cases_m47": 8,
            "sqlite_file_read_denials_m47": 56,
            "sqlite_file_write_denials_m47": 8,
            "sqlite_file_original_defects_closed_m47": 0,
            "audit_source_cases_m48": 13,
            "audit_source_read_denials_m48": 65,
            "audit_source_append_denials_m48": 13,
            "audit_source_original_findings_closed_m48": 0,
            "dual_ledger_capture_attack_cases_m49": 9,
            "dual_ledger_positive_bundles_m49": 9,
            "dual_ledger_negative_denials_m49": 9,
            "dual_ledger_original_findings_closed_m49": 0,
            "recovery_admission_original_bundles_m50": 13,
            "recovery_admission_rehashed_attacks_m50": 13,
            "recovery_admission_negative_denials_m50": 13,
            "recovery_admission_original_findings_closed_m50": 0,
            "technical_witness_positive_controls_m51": 22,
            "technical_witness_adversarial_cases_m51": 22,
            "technical_witness_negative_denials_m51": 22,
            "technical_witness_original_findings_closed_m51": 0,
            "technical_replay_original_reviews_m52": 14,
            "technical_replay_negative_cases_m52": 14,
            "technical_replay_exact_denials_m52": 14,
            "technical_replay_original_findings_closed_m52": 0,
            "signed_replay_checkpoint_positive_controls_m53": 19,
            "signed_replay_checkpoint_negative_cases_m53": 19,
            "signed_replay_checkpoint_exact_denials_m53": 19,
            "signed_replay_checkpoint_original_findings_closed_m53": 0,
        }
        for name, expected_value in expected_flags.items():
            _check(name in proof
                   and type(proof[name]) is type(expected_value)
                   and proof[name] == expected_value,
                   "LAB14_CUSTOMER_SOURCE_PERMISSION_OR_CLAIM_FABRICATED")
        for key in (
            "research_claim_clearance_receipt_sha256",
            "research_source_lineage_m37_receipt_sha256",
            "research_m38_receipt_sha256",
            "critical_current_path_report_sha256_m41",
            "settlement_identity_report_sha256_m42",
            "settlement_source_report_sha256_m43",
            "persistent_semantic_receipt_sha256_m44",
            "atomic_financial_receipt_sha256_m45",
            "sqlite_schema_receipt_sha256_m46",
            "sqlite_file_receipt_sha256_m47",
            "audit_source_receipt_sha256_m48",
            "dual_ledger_receipt_sha256_m49",
            "recovery_admission_receipt_sha256_m50",
            "technical_witness_receipt_sha256_m51",
            "technical_replay_receipt_sha256_m52",
            "signed_replay_checkpoint_receipt_sha256_m53",
        ):
            _check(_hex(proof.get(key)),
                   "LAB14_SOURCE_AND_PILOT_REPORT_RECEIPT_INVALID")


def _pilot(pilot: object) -> dict:
    """Recalculate independent local fixture, not external customer authority."""
    _check(type(pilot) is dict, "PILOT_MUST_BE_OBJECT")
    expected = simulated_cohort()
    _check(set(pilot) == set(expected),
           "SYNTHETIC_PILOT_EXTRA_OR_MISSING_FIELDS")
    _check(pilot.get("scope") == "SIMULATED_FOUNDING_CUSTOMER_PILOT_ONLY"
           and pilot.get("simulated_customer_count") == 3
           and pilot.get("accepted_real_customer_count") == 0
           and type(pilot.get("accepted_real_customer_count")) is int
           and pilot.get("actual_company_revenue_cents") == 0
           and pilot.get("actual_customer_recovery_cents") == 0
           and pilot.get("real_customer_permission_obtained") is False
           and pilot.get("outside_carrier_bank_or_email_activity") is False,
           "REAL_CUSTOMER_OUTCOME_OR_AUTHORITY_FABRICATED")
    _check(pilot["receipt_sha256"] ==
           digest({k: v for k, v in pilot.items() if k != "receipt_sha256"}),
           "PILOT_RECEIPT_CHANGED")
    # Compare canonical JSON, not Python tuple/list identity. Persisted
    # receipts round-trip tuple fields as JSON arrays; a forged dollar
    # figure still changes the canonical digest and fails this gate.
    _check(digest(pilot) == digest(expected),
           "REHASHED_FICTIONAL_PILOT_OUTCOME_CHANGED")
    for row in pilot["cohort"]:
        _check(row.get("authorization_scope") == "SYNTHETIC_TEST_FIXTURES_ONLY"
               and row.get("actual_customer_revenue_cents") == 0
               and row.get("observed_real_recovery_cents") == 0,
               "FICTIONAL_COACHING_AS_LIVE_CUSTOMER_PROOF")
    return pilot


def assess(receipt: object, *, require_complete: bool = False) -> dict:
    """Fail on altered invariants even when a local receipt was rehashed.

    For deliberately bounded budgets (e.g. 5/14), valid source output is
    INCOMPLETE and can never be accepted as a full research-lab pass.
    """
    _check(type(receipt) is dict and set(receipt) == RECEIPT_FIELDS,
           "EXECUTION_RECEIPT_UNEXPECTED_FIELDS")
    r = receipt
    _check(type(r["schema"]) is int and r["schema"] == 1
           and r["scope"] == "BOUNDED_ISOLATED_RESEARCH_ONLY"
           and r["source_first_party"] ==
           "ACTUAL_REPOSITORY_PYTHON_MODULES_WITH_FICTIONAL_FIXTURES"
           and r["laboratory_executions_not_equivalent_to_customer_accuracy"] is True,
           "SYNTHETIC_EXECUTION_SCOPE_MISLABELED")
    for flag in ACTUAL_EXTERNAL_FALSE:
        _check(r[flag] is False, "EXTERNAL_PRODUCTION_OR_AUTHORITY_FALSELY_CERTIFIED")
    _check(type(r["actual_revenue_cents"]) is int and r["actual_revenue_cents"] == 0
           and type(r["historical_findings_open"]) is int
           and r["historical_findings_open"] == 26,
           "CASH_OR_HISTORICAL_FINDING_FALSELY_CLOSED")
    _check(_hex(r["prior_chain_receipt"]) and _hex(r["receipt_sha256"]),
           "INVALID_PARENT_RECEIPT")
    rows = r["lab_runs"]
    _check(type(rows) is list and len(rows) == 14
           and set(LAB_LABELS) == set(range(1, 15))
           and set(NEGATIVE_PROBE) == set(LAB_LABELS)
           and BASE_FIVE.isdisjoint(EXTENSIONS)
           and BASE_FIVE | EXTENSIONS == set(LAB_LABELS),
           "FOURTEEN_EXISTING_LABS_NOT_PRESENT")
    passed, blocked, status_rows = [], [], []
    for idx, row in enumerate(rows, 1):
        _check(type(row) is dict and type(row.get("lab")) is int
               and row["lab"] == idx and row.get("title") == LAB_LABELS[idx],
               "LAB_ID_DUPLICATE_REORDER_OR_TITLE_CHANGED")
        status = row.get("status")
        success = ("EXECUTED_EXISTING_PYTHON_DOMAIN" if idx in BASE_FIVE
                   else "EXECUTED_EXISTING_PYTHON_MODULE")
        if status == success:
            _check(set(row) == SUCCESS_FIELDS,
                   "EXECUTION_PROOF_OR_RESULT_FIELDS_CHANGED")
            _check(row["scope"] == ("ISOLATED_SYNTHETIC" if idx in BASE_FIVE
                                  else "SYNTHETIC_OR_SOURCE_INSPECTED"),
                   "EXECUTED_LAB_SCOPE_CHANGED")
            _check(row["negative_probe"] == NEGATIVE_PROBE[idx],
                   "NEGATIVE_PROBE_REHASHED_OR_MISSING")
            _check(type(row["elapsed_ms"]) is int and row["elapsed_ms"] >= 0,
                   "INVALID_EXECUTION_TIME")
            _proof(idx, row["proof"])
            passed.append(idx)
        elif status == "FAILED_OR_BLOCKED" and idx in EXTENSIONS:
            _check(set(row) == FAILURE_FIELDS
                   and row["scope"] == "SYNTHETIC_OR_SOURCE_INSPECTED"
                   and row["negative_probe"] == "NOT_VERIFIED"
                   and type(row["reason"]) is str and 3 <= len(row["reason"]) <= 200
                   and type(row["elapsed_ms"]) is int and row["elapsed_ms"] >= 0,
                   "FAILED_LAB_WRONGLY_MARKED_AS_PASS")
            blocked.append(idx)
        elif status == "NOT_EXECUTED_BUDGET":
            _check(set(row) == BUDGET_FIELDS and row["scope"] == "NOT_EXECUTED"
                   and row["negative_probe"] == "NOT_RUN"
                   and row["elapsed_ms"] is None,
                   "BUDGET_LIMIT_FALSELY_ACCEPTED")
            blocked.append(idx)
        else:
            raise ValueError("M39_UNREGISTERED_LAB_STATUS_OR_FAKE_EXECUTION")
        status_rows.append({
            "lab": idx,
            "title": LAB_LABELS[idx],
            "status": "PASSED_LOCAL_PYTHON_SYNTHETIC" if idx in passed else
                      "BLOCKED_OR_NOT_EXECUTED",
            "negative_probe_code": NEGATIVE_PROBE[idx] if idx in passed else None,
        })
    _check(type(r["executed_labs"]) is list and r["executed_labs"] == passed
           and type(r["failed_or_blocked_labs"]) is list
           and r["failed_or_blocked_labs"] == blocked,
           "EXECUTED_OR_FAILED_LAB_SUMMARY_TAMPERED")
    _pilot(r["three_customer_pilot"])
    stable = {**r, "lab_runs": [
        {k: v for k, v in row.items() if k != "elapsed_ms"}
        for row in rows
    ]}
    stable.pop("receipt_sha256")
    _check(digest(stable) == r["receipt_sha256"],
           "REHASHED_OR_TAMPERED_EXECUTION_RECEIPT")
    full = passed == list(range(1, 15)) and not blocked
    if require_complete:
        _check(full, "INCOMPLETE_OR_FAILED_RESEARCH_LABS_CANNOT_PASS")
    summary = {
        "schema_version": 1,
        "scope": SCOPE,
        "source_execution_receipt_sha256": r["receipt_sha256"],
        "local_review_decision": FULL if full else INCOMPLETE,
        "all_fourteen_locally_executed": full,
        "existing_lab_count": 14,
        "locally_executed_count": len(passed),
        "blocked_or_unexecuted_count": len(blocked),
        "negative_probes_exactly_bound": len(passed),
        "simulated_pilot_customer_count": 3,
        "real_customers_observed": 0,
        "real_customer_revenue_cents": 0,
        "independently_authenticated_bank_or_carrier_money": False,
        "frozen_historical_findings_not_auto_closed": 26,
        "external_marketing_or_publication_authorized": False,
        "actual_hosted_staging_isolation_verified": False,
        "no_new_lab_created": True,
        "receipt_not_third_party_attestation": True,
        "laboratory_results": status_rows,
        "caveat": (
            "M39 checks local Python result shapes, exact negative-probe contracts, "
            "the closed 14-lab census, a recalculated three-customer fictional "
            "cohort and local receipt consistency. Passing M39 is not an "
            "independent real-world provider audit, authenticated human review, "
            "customer validation, hosted deployment, actual cash or an "
            "external publication approval. All 26 prior findings remain open."
        ),
    }
    summary["receipt_sha256"] = digest(summary)
    return summary


def render_html(report: dict) -> str:
    rows = "".join(
        '<tr><th>' + escape(str(item["lab"])) +
        '</th><td>' + escape(str(item["title"])) +
        '</td><td>' + escape(str(item["status"])) +
        '</td><td>' + escape(str(item["negative_probe_code"])) +
        '</td></tr>'
        for item in report["laboratory_results"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>RETALLY | M39 Cross-lab Research Assurance</title>'
        '<style>body{font:15px/1.55 system-ui;background:#f3f7f3;'
        'color:#243b30;max-width:1020px;margin:auto;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'td,th{border-bottom:1px solid #dbe6dc;padding:10px;text-align:left}'
        'small{color:#596a60}strong{color:#174c32}</style></head><body>'
        '<small>RETALLY / EXISTING PHASE 4 / M39 / INTERNAL ONLY</small>'
        '<h1>Cross-lab integrity assurance</h1><p><strong>' +
        str(report["locally_executed_count"]) + ' / 14</strong> modules ran with '
        'expected local negative probes. State: <strong>' +
        escape(report["local_review_decision"]) +
        '</strong>. 26 historical findings are still open; '
        'three fictional buyers are not customer proof.</p>'
        '<p>This checker verifies local consistency and source contracts, '
        'not actual bank, carrier, buyer or independent legal permission. '
        'Zero publication authorizations, zero real customer cash.</p>'
        '<table><thead><tr><th>Lab</th><th>Module</th><th>Review</th>'
        '<th>Negative probe</th></tr></thead><tbody>' + rows +
        '</tbody></table><p><small>' + escape(report["caveat"]) +
        '</small></p></body></html>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only local Phase 4 integrity check")
    ap.add_argument("--receipt", type=Path, required=True,
                    help="Exact original 14-lab execute_all_labs JSON, not enriched Control Center")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    raw = json.loads(args.receipt.read_text(encoding="utf-8"))
    report = assess(raw, require_complete=True)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "lab_cross_check_m39.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "lab_cross_check_m39.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({
        "local_executed_labs": report["locally_executed_count"],
        "remaining_original_findings": 26,
        "real_customers": 0,
        "external_approvals": 0,
        "receipt_sha256": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
