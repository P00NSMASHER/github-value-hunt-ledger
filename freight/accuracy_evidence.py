"""Validate RecoveryOS Phase 3 accuracy evidence.

This validator freezes the synthetic gold fixture and its exact expected report.
It deliberately refuses to convert synthetic conformance into a production
accuracy claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freight.accuracy_benchmark import (
    build_accuracy_report,
    load_fixture,
    report_dict,
)


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_baseline(baseline: dict) -> list[str]:
    errors: list[str] = []
    if baseline.get("schema_version") != 1:
        errors.append("accuracy baseline schema_version must be 1")
    if baseline.get("gold_id") != "recoveryos-phase3-accuracy-v1":
        errors.append("unexpected gold_id")
    if not isinstance(baseline.get("gold_fixture_hash"), str) or len(baseline["gold_fixture_hash"]) != 64:
        errors.append("gold_fixture_hash must be SHA-256")
    if not isinstance(baseline.get("report_hash"), str) or len(baseline["report_hash"]) != 64:
        errors.append("report_hash must be SHA-256")

    scope = baseline.get("scope") or {}
    if int(scope.get("total_scenarios") or 0) < 40:
        errors.append("gold set must contain at least 40 scenarios")
    if set(scope.get("modes") or []) != {"PARCEL","LTL","TL","INTERMODAL","AIR","OCEAN"}:
        errors.append("gold set must cover all six freight modes")

    rating = ((baseline.get("metrics") or {}).get("rating") or {})
    for key in (
        "precision",
        "recall",
        "specificity",
        "auto_classification_accuracy",
        "review_routing_accuracy",
        "exact_expected_amount_accuracy",
        "exact_variance_accuracy",
        "exact_financial_state_accuracy",
        "authority_binding_accuracy",
    ):
        if rating.get(key) != 1.0:
            errors.append("baseline rating metric must be exact: " + key)
    if int(rating.get("false_positive") or 0) != 0:
        errors.append("baseline contains false positives")
    if int(rating.get("false_negative") or 0) != 0:
        errors.append("baseline contains false negatives")

    authority = ((baseline.get("metrics") or {}).get("authority_resolution") or {})
    if authority.get("accuracy") != 1.0:
        errors.append("baseline authority resolution must be exact")

    attribution = ((baseline.get("metrics") or {}).get("incumbent_attribution") or {})
    if attribution.get("accuracy") != 1.0:
        errors.append("baseline incumbent attribution must be exact")
    if attribution.get("batch_totals_exact") is not True:
        errors.append("baseline incumbent batch totals must be exact")
    if attribution.get("duplicate_suppression_accuracy") != 1.0:
        errors.append("baseline duplicate suppression must be exact")
    if attribution.get("incumbent_credit_protection_accuracy") != 1.0:
        errors.append("baseline incumbent credit protection must be exact")

    payment = ((baseline.get("metrics") or {}).get("payment_lifecycle") or {})
    if payment.get("valid_state_and_money_accuracy") != 1.0:
        errors.append("baseline payment state/money must be exact")
    if payment.get("invalid_transition_rejection_accuracy") != 1.0:
        errors.append("baseline invalid payment rejection must be exact")

    trace = ((baseline.get("metrics") or {}).get("evidence_traceability") or {})
    if trace.get("accuracy") != 1.0:
        errors.append("baseline traceability must be exact")

    external = baseline.get("external_blind_validation") or {}
    if external.get("state") != "PENDING_EXTERNAL_CUSTOMER_EVIDENCE":
        errors.append("external blind validation must remain pending")
    if not baseline.get("claim_boundary"):
        errors.append("accuracy baseline claim boundary required")
    return errors


def validate_runtime_report(report: dict, baseline: dict) -> list[str]:
    errors: list[str] = []
    if report.get("gold_id") != baseline.get("gold_id"):
        errors.append("runtime gold_id differs from baseline")
    if report.get("gold_fixture_hash") != baseline.get("gold_fixture_hash"):
        errors.append("runtime gold fixture hash differs from frozen baseline")
    if report.get("report_hash") != baseline.get("report_hash"):
        errors.append("runtime accuracy report hash differs from frozen baseline")

    scope = baseline["scope"]
    rating = report.get("rating") or {}
    if int(rating.get("case_count") or 0) != int(scope["rating_cases"]):
        errors.append("runtime rating case count mismatch")
    if int(rating.get("auto_rateable_case_count") or 0) != int(scope["auto_rateable_rating_cases"]):
        errors.append("runtime auto-rateable case count mismatch")
    if int(rating.get("review_expected_case_count") or 0) != int(scope["review_required_rating_cases"]):
        errors.append("runtime review-required case count mismatch")

    expected_rating = baseline["metrics"]["rating"]
    for key, expected in expected_rating.items():
        actual_key = {
            "true_positive":"true_positive",
            "true_negative":"true_negative",
            "false_positive":"false_positive",
            "false_negative":"false_negative",
        }.get(key, key)
        if rating.get(actual_key) != expected:
            errors.append("runtime rating metric mismatch: " + key)

    authority = report.get("authority_resolution") or {}
    expected_authority = baseline["metrics"]["authority_resolution"]
    for key in ("case_count","exact_count","accuracy"):
        if authority.get(key) != expected_authority[key]:
            errors.append("runtime authority metric mismatch: " + key)

    attribution = report.get("incumbent_attribution") or {}
    expected_attr = baseline["metrics"]["incumbent_attribution"]
    for key in (
        "case_count",
        "exact_count",
        "accuracy",
        "batch_totals_exact",
        "duplicate_suppression_accuracy",
        "incumbent_credit_protection_accuracy",
    ):
        if attribution.get(key) != expected_attr[key]:
            errors.append("runtime attribution metric mismatch: " + key)
    totals = attribution.get("actual_totals") or {}
    for key in (
        "challenger_only_cents",
        "incumbent_known_cents",
        "review_cents",
        "suppressed_cents",
    ):
        if totals.get(key) != expected_attr[key]:
            errors.append("runtime attribution total mismatch: " + key)

    payment = report.get("payment_lifecycle") or {}
    expected_payment = baseline["metrics"]["payment_lifecycle"]
    for key in (
        "valid_case_count",
        "valid_exact_count",
        "valid_state_and_money_accuracy",
        "invalid_case_count",
        "invalid_rejection_count",
        "invalid_transition_rejection_accuracy",
    ):
        if payment.get(key) != expected_payment[key]:
            errors.append("runtime payment metric mismatch: " + key)

    trace = report.get("evidence_traceability") or {}
    expected_trace = baseline["metrics"]["evidence_traceability"]
    for key in ("traceable_outputs","total_outputs","accuracy"):
        if trace.get(key) != expected_trace[key]:
            errors.append("runtime traceability mismatch: " + key)

    return errors


def validate_fixture_against_baseline(fixture: dict, baseline: dict) -> list[str]:
    report = report_dict(build_accuracy_report(fixture))
    errors = []
    if report["gold_fixture_hash"] != baseline.get("gold_fixture_hash"):
        errors.append("fixture hash differs from frozen accuracy baseline")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="freight/fixtures/phase3_accuracy_gold_v1.json",
    )
    parser.add_argument(
        "--baseline",
        default="freight/PHASE3_ACCURACY_BASELINE.json",
    )
    parser.add_argument("--report")
    args = parser.parse_args()

    baseline = _load(args.baseline)
    fixture = load_fixture(args.fixture)
    errors = validate_baseline(baseline)
    errors += validate_fixture_against_baseline(fixture, baseline)
    runtime = _load(args.report) if args.report else report_dict(build_accuracy_report(fixture))
    errors += validate_runtime_report(runtime, baseline)

    result = {
        "state": "PASS" if not errors else "FAIL",
        "errors": errors,
        "gold_id": baseline.get("gold_id"),
        "gold_fixture_hash": baseline.get("gold_fixture_hash"),
        "report_hash": baseline.get("report_hash"),
        "external_blind_validation_state": (
            baseline.get("external_blind_validation") or {}
        ).get("state"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
