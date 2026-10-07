"""RecoveryOS Phase 3 synthetic accuracy and financial-integrity benchmark.

The gold fixture is intentionally explicit and human-readable. Expected outcomes
are stored independently of runtime outputs. This harness measures conformance to
those frozen expectations across rating, authority resolution, incumbent
attribution, duplicate suppression, payment lifecycle, and evidence traceability.

A perfect score is not a production-accuracy claim. The fixture is synthetic and
code-adjacent; the report carries that boundary forward.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from freight.canonical_schema import (
    ChargeLine,
    PackageFacts,
    ShipmentFacts,
    SourceArtifact,
    build_record,
)
from freight.contracts import canonical_hash
from freight.incumbent_challenge import (
    ChallengeCandidate,
    IncumbentMatter,
    challenge_incumbent,
    freeze_incumbent_snapshot,
)
from freight.payment_orchestration import (
    PaymentOrchestrator,
    authorize_payment,
    prepare_payment_instruction,
    verify_payment_snapshot,
)
from freight.rate_authority import AuthorityBook, compile_authority
from freight.rating_engine import RATED, REVIEW_REQUIRED, rate_record


@dataclass(frozen=True)
class AccuracyReport:
    schema_version: int
    gold_id: str
    gold_fixture_hash: str
    rating: dict
    authority_resolution: dict
    incumbent_attribution: dict
    payment_lifecycle: dict
    evidence_traceability: dict
    claim_boundary: tuple[str, ...]
    report_hash: str


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else numerator / denominator


def _source(case_id: str) -> SourceArtifact:
    return SourceArtifact(
        source_id="gold:" + case_id,
        kind="SYNTHETIC_GOLD",
        sha256=hashlib.sha256(("source:" + case_id).encode()).hexdigest(),
        observed_at="2026-10-07T05:00:00.000000Z",
        transport="BATCH",
        filename=case_id + ".json",
    )


def _build_record(case_id: str, raw: dict, common: dict):
    packages = tuple(
        PackageFacts(
            package_id=item["package_id"],
            weight_grams=item["weight_grams"],
            length_mm=item.get("length_mm"),
            width_mm=item.get("width_mm"),
            height_mm=item.get("height_mm"),
            quantity=item.get("quantity", 1),
        )
        for item in raw.get("packages", [])
    )
    charges = tuple(
        ChargeLine(
            charge_id=f"{case_id}:{index}",
            charge_code=code,
            billed_cents=cents,
        )
        for index, (code, cents) in enumerate(raw["charges"], 1)
    )
    shipment = ShipmentFacts(
        shipment_id="SHIP-" + case_id,
        carrier_id=raw["carrier_id"],
        mode=raw["mode"],
        service_date=raw.get("service_date", common["service_date"]),
        origin_postal=raw.get("origin_postal", "17901"),
        destination_postal=raw.get("destination_postal", "21224"),
        actual_weight_grams=raw["actual_weight_grams"],
        package_count=raw["package_count"],
        packages=packages,
        freight_class=raw.get("freight_class"),
        zone=raw.get("zone"),
        service_level=raw.get("service_level", "GOLD"),
        residential=raw.get("residential", False),
        miles=raw.get("miles"),
        equipment_type=raw.get("equipment_type"),
        container_type=raw.get("container_type"),
        chassis_days=raw.get("chassis_days"),
    )
    return build_record(
        buyer_id=common["buyer_id"],
        business_unit=common["business_unit"],
        invoice_id="INV-" + case_id,
        invoice_date=common["invoice_date"],
        customer_id=common["customer_id"],
        currency=common["currency"],
        shipment=shipment,
        charges=charges,
        sources=(_source(case_id),),
    )


def _compile_profile(name: str, raw: dict, common: dict):
    payload = {
        "authority_id": raw["authority_id"],
        "buyer_id": common["buyer_id"],
        "business_unit": common["business_unit"],
        "customer_id": common["customer_id"],
        "carrier_id": raw["carrier_id"],
        "currency": common["currency"],
        "mode": raw["mode"],
        "effective_from": raw["effective_from"],
        "priority": raw["priority"],
        "terms": raw["terms"],
    }
    if raw.get("effective_to") is not None:
        payload["effective_to"] = raw["effective_to"]
    return compile_authority(
        payload,
        source_sha256=hashlib.sha256(("authority:" + name).encode()).hexdigest(),
        verified_controlling_authority=raw.get("verified", True),
    )


def _book(names: list[str], fixture: dict) -> AuthorityBook:
    profiles = fixture["authority_profiles"]
    common = fixture["common"]
    return AuthorityBook(
        tuple(_compile_profile(name, profiles[name], common) for name in names)
    )


def _rating_truth(result) -> str:
    if result.status == REVIEW_REQUIRED:
        return "REVIEW"
    if result.status != RATED:
        return "UNKNOWN"
    return "POSITIVE" if (result.variance_cents or 0) > 0 else "NEGATIVE"


def _hash_like(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def evaluate_rating(fixture: dict) -> tuple[dict, int, int]:
    tp = tn = fp = fn = 0
    auto_abstain = 0
    auto_total = auto_class_correct = 0
    review_expected = review_correct = 0
    expected_dollar_exact = variance_exact = 0
    financial_state_exact = 0
    authority_checks = authority_correct = 0
    traceable = 0
    rows = []

    for case in fixture["rating_cases"]:
        record = _build_record(case["id"], case["record"], fixture["common"])
        result = rate_record(record, _book(case["authority_profiles"], fixture))
        expected = case["expected"]
        predicted_truth = _rating_truth(result)
        truth = expected["truth"]

        if truth == "REVIEW":
            review_expected += 1
            if predicted_truth == "REVIEW":
                review_correct += 1
        else:
            auto_total += 1
            if predicted_truth == truth:
                auto_class_correct += 1
            if truth == "POSITIVE":
                if predicted_truth == "POSITIVE":
                    tp += 1
                else:
                    fn += 1
                    if predicted_truth == "REVIEW":
                        auto_abstain += 1
            elif truth == "NEGATIVE":
                if predicted_truth == "NEGATIVE":
                    tn += 1
                elif predicted_truth == "POSITIVE":
                    fp += 1
                else:
                    auto_abstain += 1

        if result.expected_total_cents == expected["expected_total_cents"]:
            expected_dollar_exact += 1
        if result.variance_cents == expected["variance_cents"]:
            variance_exact += 1
        if (
            result.status == expected["status"]
            and result.expected_total_cents == expected["expected_total_cents"]
            and result.variance_cents == expected["variance_cents"]
        ):
            financial_state_exact += 1

        if expected.get("authority_id") is not None:
            authority_checks += 1
            if result.authority_id == expected["authority_id"]:
                authority_correct += 1

        source_trace = all(_hash_like(item.sha256) for item in record.sources)
        authority_trace = (
            result.authority_id is None
            or _hash_like(result.authority_hash)
        )
        trace_ok = (
            result.record_hash == record.record_hash
            and _hash_like(result.rating_hash)
            and source_trace
            and authority_trace
        )
        if trace_ok:
            traceable += 1

        rows.append({
            "case_id": case["id"],
            "mode": case["record"]["mode"],
            "expected_truth": truth,
            "predicted_truth": predicted_truth,
            "expected_status": expected["status"],
            "actual_status": result.status,
            "expected_total_cents": expected["expected_total_cents"],
            "actual_total_cents": result.expected_total_cents,
            "expected_variance_cents": expected["variance_cents"],
            "actual_variance_cents": result.variance_cents,
            "expected_authority_id": expected.get("authority_id"),
            "actual_authority_id": result.authority_id,
            "traceable": trace_ok,
        })

    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    specificity = _ratio(tn, tn + fp)
    return ({
        "case_count": len(rows),
        "auto_rateable_case_count": auto_total,
        "review_expected_case_count": review_expected,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "auto_abstentions": auto_abstain,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "auto_classification_accuracy": _ratio(auto_class_correct, auto_total),
        "review_routing_accuracy": _ratio(review_correct, review_expected),
        "exact_expected_amount_accuracy": _ratio(expected_dollar_exact, len(rows)),
        "exact_variance_accuracy": _ratio(variance_exact, len(rows)),
        "exact_financial_state_accuracy": _ratio(financial_state_exact, len(rows)),
        "authority_binding_accuracy": _ratio(authority_correct, authority_checks),
        "traceability_accuracy": _ratio(traceable, len(rows)),
        "rows": rows,
    }, traceable, len(rows))


def evaluate_authority_resolution(fixture: dict) -> dict:
    correct = 0
    rows = []
    for case in fixture["authority_cases"]:
        record = _build_record(case["id"], case["record"], fixture["common"])
        resolution = _book(case["authority_profiles"], fixture).resolve(record)
        actual_id = resolution.authority.authority_id if resolution.authority else None
        expected = case["expected"]
        exact = (
            resolution.status == expected["status"]
            and actual_id == expected["authority_id"]
        )
        correct += int(exact)
        rows.append({
            "case_id": case["id"],
            "expected_status": expected["status"],
            "actual_status": resolution.status,
            "expected_authority_id": expected["authority_id"],
            "actual_authority_id": actual_id,
            "exact": exact,
        })
    return {
        "case_count": len(rows),
        "exact_count": correct,
        "accuracy": _ratio(correct, len(rows)),
        "rows": rows,
    }


def evaluate_attribution(fixture: dict) -> tuple[dict, int, int]:
    raw = fixture["attribution"]
    snap = raw["snapshot"]
    snapshot = freeze_incumbent_snapshot(
        buyer_id=snap["buyer_id"],
        business_unit=snap["business_unit"],
        population_hash=snap["population_hash"],
        source_hash=snap["source_hash"],
        matters=tuple(
            IncumbentMatter(
                matter_id=item["matter_id"],
                economic_key=item["economic_key"],
                state=item["state"],
                amount_cents=item["amount_cents"],
                source_hash=item["source_hash"],
            )
            for item in snap["matters"]
        ),
    )
    candidates = tuple(
        ChallengeCandidate(
            candidate_id=item["candidate_id"],
            economic_key=item["economic_key"],
            record_hash=item["record_hash"],
            category=item["category"],
            billed_cents=item["billed_cents"],
            expected_cents=item["expected_cents"],
            confidence_ppm=item["confidence_ppm"],
            blocker_codes=tuple(item.get("blocker_codes", [])),
            evidence_hashes=tuple(item.get("evidence_hashes", [])),
        )
        for item in raw["candidates"]
    )
    batch = challenge_incumbent(snapshot, candidates)
    expected_by_id = {item["candidate_id"]: item for item in raw["candidates"]}
    exact = 0
    traceable = 0
    duplicate_total = duplicate_correct = 0
    incumbent_total = incumbent_correct = 0
    rows = []

    for item in batch.dispositions:
        expected = expected_by_id[item.candidate_id]
        is_exact = (
            item.attribution_state == expected["expected_state"]
            and item.net_new_candidate_cents == expected["expected_net_new_cents"]
        )
        exact += int(is_exact)
        trace_ok = _hash_like(snapshot.snapshot_hash) and _hash_like(item.disposition_hash)
        traceable += int(trace_ok)

        if item.economic_key == "K7":
            duplicate_total += 1
            duplicate_correct += int(
                item.attribution_state == "REVIEW"
                and item.net_new_candidate_cents == 0
            )
        if item.candidate_id in {"C1", "C2", "C3"}:
            incumbent_total += 1
            incumbent_correct += int(
                item.attribution_state == "INCUMBENT_KNOWN"
                and item.net_new_candidate_cents == 0
            )

        rows.append({
            "candidate_id": item.candidate_id,
            "expected_state": expected["expected_state"],
            "actual_state": item.attribution_state,
            "expected_net_new_cents": expected["expected_net_new_cents"],
            "actual_net_new_cents": item.net_new_candidate_cents,
            "traceable": trace_ok,
        })

    expected_totals = raw["expected_totals"]
    totals_exact = (
        batch.challenger_only_cents == expected_totals["challenger_only_cents"]
        and batch.incumbent_known_cents == expected_totals["incumbent_known_cents"]
        and batch.review_cents == expected_totals["review_cents"]
        and batch.suppressed_cents == expected_totals["suppressed_cents"]
    )
    return ({
        "case_count": len(rows),
        "exact_count": exact,
        "accuracy": _ratio(exact, len(rows)),
        "batch_totals_exact": totals_exact,
        "duplicate_suppression_accuracy": _ratio(duplicate_correct, duplicate_total),
        "incumbent_credit_protection_accuracy": _ratio(incumbent_correct, incumbent_total),
        "traceability_accuracy": _ratio(traceable, len(rows)),
        "actual_totals": {
            "challenger_only_cents": batch.challenger_only_cents,
            "incumbent_known_cents": batch.incumbent_known_cents,
            "review_cents": batch.review_cents,
            "suppressed_cents": batch.suppressed_cents,
        },
        "rows": rows,
    }, traceable, len(rows))


def evaluate_payments(fixture: dict) -> tuple[dict, int, int]:
    valid_total = valid_correct = 0
    invalid_total = invalid_correct = 0
    traceable = trace_total = 0
    rows = []

    for case_index, case in enumerate(fixture["payment_cases"]):
        instruction = prepare_payment_instruction(
            instruction_id="GOLD-PAY-" + case["id"],
            buyer_id=fixture["common"]["buyer_id"],
            business_unit=fixture["common"]["business_unit"],
            payer_id="GOLD-PAYER",
            payee_id="GOLD-PAYEE",
            currency=fixture["common"]["currency"],
            amount_cents=case["amount_cents"],
            purpose="Gold payment lifecycle case",
            finding_proof_hashes=(hashlib.sha256(("finding:" + case["id"]).encode()).hexdigest(),),
            idempotency_key="gold:" + case["id"],
        )
        orchestrator = PaymentOrchestrator(instruction)
        authorization = None
        events = []
        rejected = False
        error = None
        try:
            if case["authorize"]:
                authorization = authorize_payment(
                    instruction,
                    authorized_by="gold-owner",
                    reason="Gold lifecycle authorization",
                    authorized_at="2026-10-07T05:01:00Z",
                )
                orchestrator.authorize(authorization)
            for event_index, state in enumerate(case["events"]):
                event = orchestrator.record_provider_event(
                    state=state,
                    provider="GOLD-PROVIDER",
                    provider_reference=f"{case['id']}:{event_index}",
                    amount_cents=case.get("event_amount_cents", case["amount_cents"]),
                    source_hash=hashlib.sha256(
                        f"payment:{case['id']}:{event_index}".encode()
                    ).hexdigest(),
                    occurred_at=f"2026-10-07T05:{2 + event_index:02d}:00Z",
                )
                events.append(event)
        except ValueError as exc:
            rejected = True
            error = str(exc)

        if case["expected_rejection"]:
            invalid_total += 1
            exact = rejected
            invalid_correct += int(exact)
            state = None
            settled = None
            trace_ok = _hash_like(instruction.instruction_hash)
        else:
            valid_total += 1
            snapshot = orchestrator.snapshot()
            state = snapshot.current_state
            settled = snapshot.settled_cents
            exact = (
                not rejected
                and state == case["expected_state"]
                and settled == case["expected_settled_cents"]
            )
            valid_correct += int(exact)
            verify_payment_snapshot(instruction, authorization, tuple(events), snapshot)
            chain_ok = all(
                event.previous_event_hash
                == (events[index - 1].event_hash if index else None)
                for index, event in enumerate(events)
            )
            trace_ok = (
                _hash_like(instruction.instruction_hash)
                and (authorization is None or _hash_like(authorization.authorization_hash))
                and all(_hash_like(event.event_hash) for event in events)
                and _hash_like(snapshot.snapshot_hash)
                and chain_ok
            )

        trace_total += 1
        traceable += int(trace_ok)
        rows.append({
            "case_id": case["id"],
            "expected_rejection": case["expected_rejection"],
            "rejected": rejected,
            "expected_state": case["expected_state"],
            "actual_state": state,
            "expected_settled_cents": case["expected_settled_cents"],
            "actual_settled_cents": settled,
            "exact": exact,
            "traceable": trace_ok,
            "error": error,
        })

    return ({
        "valid_case_count": valid_total,
        "valid_exact_count": valid_correct,
        "valid_state_and_money_accuracy": _ratio(valid_correct, valid_total),
        "invalid_case_count": invalid_total,
        "invalid_rejection_count": invalid_correct,
        "invalid_transition_rejection_accuracy": _ratio(invalid_correct, invalid_total),
        "traceability_accuracy": _ratio(traceable, trace_total),
        "rows": rows,
    }, traceable, trace_total)


def build_accuracy_report(fixture: dict) -> AccuracyReport:
    rating, rating_trace, rating_trace_total = evaluate_rating(fixture)
    authority = evaluate_authority_resolution(fixture)
    attribution, attr_trace, attr_trace_total = evaluate_attribution(fixture)
    payment, pay_trace, pay_trace_total = evaluate_payments(fixture)
    traceable = rating_trace + attr_trace + pay_trace
    trace_total = rating_trace_total + attr_trace_total + pay_trace_total
    trace = {
        "traceable_outputs": traceable,
        "total_outputs": trace_total,
        "accuracy": _ratio(traceable, trace_total),
    }
    fixture_hash = canonical_hash(fixture)
    body = {
        "schema_version": 1,
        "gold_id": fixture["gold_id"],
        "gold_fixture_hash": fixture_hash,
        "rating": rating,
        "authority_resolution": authority,
        "incumbent_attribution": attribution,
        "payment_lifecycle": payment,
        "evidence_traceability": trace,
        "claim_boundary": fixture["claim_boundary"],
    }
    return AccuracyReport(
        schema_version=1,
        gold_id=fixture["gold_id"],
        gold_fixture_hash=fixture_hash,
        rating=rating,
        authority_resolution=authority,
        incumbent_attribution=attribution,
        payment_lifecycle=payment,
        evidence_traceability=trace,
        claim_boundary=tuple(fixture["claim_boundary"]),
        report_hash=canonical_hash(body),
    )


def validate_accuracy_report(report: AccuracyReport) -> None:
    rating = report.rating
    if rating["false_positive"] != 0:
        raise ValueError("gold benchmark contains false positives")
    if rating["false_negative"] != 0:
        raise ValueError("gold benchmark contains false negatives")
    if rating["auto_abstentions"] != 0:
        raise ValueError("auto-rateable gold case incorrectly abstained")
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
        "traceability_accuracy",
    ):
        if rating[key] != 1.0:
            raise ValueError("rating metric below exact gold conformance: " + key)

    if report.authority_resolution["accuracy"] != 1.0:
        raise ValueError("authority-resolution gold conformance failed")
    attr = report.incumbent_attribution
    if attr["accuracy"] != 1.0 or attr["batch_totals_exact"] is not True:
        raise ValueError("incumbent-attribution gold conformance failed")
    if attr["duplicate_suppression_accuracy"] != 1.0:
        raise ValueError("duplicate suppression gold conformance failed")
    if attr["incumbent_credit_protection_accuracy"] != 1.0:
        raise ValueError("incumbent credit protection gold conformance failed")

    payment = report.payment_lifecycle
    if payment["valid_state_and_money_accuracy"] != 1.0:
        raise ValueError("payment lifecycle state/money gold conformance failed")
    if payment["invalid_transition_rejection_accuracy"] != 1.0:
        raise ValueError("invalid payment transition was not rejected")
    if report.evidence_traceability["accuracy"] != 1.0:
        raise ValueError("evidence traceability gold conformance failed")


def load_fixture(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def report_dict(report: AccuracyReport) -> dict:
    return asdict(report)


def summary_dict(report: AccuracyReport) -> dict:
    return {
        "gold_id": report.gold_id,
        "gold_fixture_hash": report.gold_fixture_hash,
        "report_hash": report.report_hash,
        "rating_cases": report.rating["case_count"],
        "precision": report.rating["precision"],
        "recall": report.rating["recall"],
        "false_positive": report.rating["false_positive"],
        "false_negative": report.rating["false_negative"],
        "exact_financial_state_accuracy": report.rating["exact_financial_state_accuracy"],
        "review_routing_accuracy": report.rating["review_routing_accuracy"],
        "authority_resolution_accuracy": report.authority_resolution["accuracy"],
        "incumbent_attribution_accuracy": report.incumbent_attribution["accuracy"],
        "duplicate_suppression_accuracy": report.incumbent_attribution["duplicate_suppression_accuracy"],
        "payment_state_and_money_accuracy": report.payment_lifecycle["valid_state_and_money_accuracy"],
        "invalid_payment_rejection_accuracy": report.payment_lifecycle["invalid_transition_rejection_accuracy"],
        "evidence_traceability_accuracy": report.evidence_traceability["accuracy"],
        "claim_boundary": list(report.claim_boundary),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="freight/fixtures/phase3_accuracy_gold_v1.json",
    )
    parser.add_argument("--output")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    report = build_accuracy_report(load_fixture(args.fixture))
    validate_accuracy_report(report)
    payload = report_dict(report)
    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary_dict(report) if args.summary else payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
