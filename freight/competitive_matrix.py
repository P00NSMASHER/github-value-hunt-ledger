"""Validate and summarize the RecoveryOS Phase 3 competitive supremacy matrix.

The matrix is deliberately conservative:
- vendor public claims are not treated as audited facts;
- absence of a public competitor claim is not treated as proof of absence;
- RecoveryOS internal evidence cannot substitute for independent customer or
  security evidence where those are the relevant dimension.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


RECOVERYOS = "RecoveryOS"
EXPECTED_COMPETITORS = {
    "Intelligent Audit",
    "Trax",
    "Cass Information Systems",
    "Loop",
    "nVision Global",
}
PAIRWISE_STATUSES = {
    "RECOVERYOS_ADVANTAGE_EVIDENCED",
    "ROUGH_PARITY_OR_UNCLEAR",
    "COMPETITOR_ADVANTAGE_EVIDENCED",
}


@dataclass(frozen=True)
class MatrixSummary:
    weighted_scores: dict[str, float]
    ranking: tuple[str, ...]
    recoveryos_rank: int
    recoveryos_number_one_dimensions: tuple[str, ...]
    recoveryos_gap_dimensions: tuple[str, ...]
    pairwise: dict[str, dict[str, str]]


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iso(value: object, name: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO date") from exc


def validate_competitor_evidence(evidence: dict, *, as_of: date) -> list[str]:
    errors: list[str] = []
    if evidence.get("schema_version") != 1:
        errors.append("competitor evidence schema_version must be 1")
    try:
        collected = _iso(evidence.get("collected_at"), "collected_at")
        valid_until = _iso(evidence.get("valid_until"), "valid_until")
        if collected > as_of:
            errors.append("competitor evidence collected_at is in the future")
        if valid_until < as_of:
            errors.append("competitor evidence is stale")
    except ValueError as exc:
        errors.append(str(exc))

    competitors = evidence.get("competitors")
    if not isinstance(competitors, dict):
        return errors + ["competitors must be an object"]
    if set(competitors) != EXPECTED_COMPETITORS:
        errors.append("competitor evidence must contain exactly the five canonical competitors")

    for name, vendor in competitors.items():
        if vendor.get("evidence_type") != "vendor_public_claim":
            errors.append(f"{name}: competitor evidence_type must be vendor_public_claim")
        sources = vendor.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{name}: at least one first-party source required")
            continue
        for source in sources:
            if not isinstance(source, dict):
                errors.append(f"{name}: source must be an object")
                continue
            url = source.get("url")
            if not isinstance(url, str) or not url.startswith("https://"):
                errors.append(f"{name}: source URL must be https")
            if not isinstance(source.get("claim_scope"), str) or not source["claim_scope"].strip():
                errors.append(f"{name}: source claim_scope required")
        claims = vendor.get("claims")
        if not isinstance(claims, list) or not claims:
            errors.append(f"{name}: public claims required")

    recovery = evidence.get("recoveryos") or {}
    if recovery.get("evidence_type") != "internal_reproducible":
        errors.append("RecoveryOS evidence must be labeled internal_reproducible")
    if not recovery.get("sources"):
        errors.append("RecoveryOS sources required")
    if not evidence.get("claim_boundary"):
        errors.append("competitor evidence claim_boundary required")
    return errors


def validate_matrix(matrix: dict) -> list[str]:
    errors: list[str] = []
    if matrix.get("schema_version") != 1:
        errors.append("competitive matrix schema_version must be 1")

    dimensions = matrix.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        return errors + ["dimensions must be a non-empty list"]
    ids = [row.get("id") for row in dimensions if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("dimension IDs must be unique")
    weights = {}
    for row in dimensions:
        if not isinstance(row, dict):
            errors.append("dimension must be an object")
            continue
        ident = row.get("id")
        weight = row.get("weight")
        if not isinstance(ident, str) or not ident:
            errors.append("dimension id required")
            continue
        if type(weight) is not int or weight <= 0:
            errors.append(f"{ident}: dimension weight must be positive integer")
            continue
        weights[ident] = weight
    if sum(weights.values()) != 100:
        errors.append("dimension weights must sum to 100")

    vendors = matrix.get("vendors")
    expected_vendors = {RECOVERYOS} | EXPECTED_COMPETITORS
    if not isinstance(vendors, dict) or set(vendors) != expected_vendors:
        errors.append("matrix vendors must be RecoveryOS plus the five canonical competitors")
        return errors

    for vendor_name, vendor in vendors.items():
        scores = (vendor or {}).get("scores")
        if not isinstance(scores, dict) or set(scores) != set(weights):
            errors.append(f"{vendor_name}: score dimensions must exactly match matrix dimensions")
            continue
        for dimension, cell in scores.items():
            if not isinstance(cell, dict):
                errors.append(f"{vendor_name}/{dimension}: score cell must be object")
                continue
            score = cell.get("score")
            if type(score) is not int or not 0 <= score <= 5:
                errors.append(f"{vendor_name}/{dimension}: score must be integer 0..5")
            rationale = cell.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                errors.append(f"{vendor_name}/{dimension}: rationale required")

    blockers = (matrix.get("strategic_boundary") or {}).get(
        "current_recoveryos_blockers_to_overall_number_one"
    )
    if not isinstance(blockers, list) or len(blockers) < 5:
        errors.append("matrix must preserve explicit RecoveryOS #1 blockers")
    if not matrix.get("claim_boundary"):
        errors.append("competitive matrix claim_boundary required")
    return errors


def summarize_matrix(matrix: dict) -> MatrixSummary:
    errors = validate_matrix(matrix)
    if errors:
        raise ValueError("; ".join(errors))

    dimensions = {row["id"]: row for row in matrix["dimensions"]}
    weighted_scores: dict[str, float] = {}
    for vendor_name, vendor in matrix["vendors"].items():
        total = 0.0
        for ident, meta in dimensions.items():
            total += meta["weight"] * vendor["scores"][ident]["score"] / 5.0
        weighted_scores[vendor_name] = round(total, 1)

    ranking = tuple(
        name
        for name, _ in sorted(
            weighted_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )

    recovery_scores = matrix["vendors"][RECOVERYOS]["scores"]
    number_one = []
    gaps = []
    pairwise: dict[str, dict[str, str]] = {}

    for ident in dimensions:
        recovery_score = recovery_scores[ident]["score"]
        leader = max(
            vendor["scores"][ident]["score"]
            for vendor in matrix["vendors"].values()
        )
        if recovery_score == leader:
            number_one.append(ident)
        if recovery_score < leader:
            gaps.append(ident)

    for competitor in EXPECTED_COMPETITORS:
        cells: dict[str, str] = {}
        competitor_scores = matrix["vendors"][competitor]["scores"]
        for ident in dimensions:
            delta = recovery_scores[ident]["score"] - competitor_scores[ident]["score"]
            if delta >= 2:
                status = "RECOVERYOS_ADVANTAGE_EVIDENCED"
            elif delta <= -2:
                status = "COMPETITOR_ADVANTAGE_EVIDENCED"
            else:
                status = "ROUGH_PARITY_OR_UNCLEAR"
            cells[ident] = status
        pairwise[competitor] = cells

    return MatrixSummary(
        weighted_scores=weighted_scores,
        ranking=ranking,
        recoveryos_rank=ranking.index(RECOVERYOS) + 1,
        recoveryos_number_one_dimensions=tuple(number_one),
        recoveryos_gap_dimensions=tuple(gaps),
        pairwise=pairwise,
    )


def summary_dict(summary: MatrixSummary) -> dict:
    counts = {}
    for competitor, cells in summary.pairwise.items():
        counts[competitor] = {
            status: sum(value == status for value in cells.values())
            for status in PAIRWISE_STATUSES
        }
    return {
        "weighted_scores": summary.weighted_scores,
        "ranking": list(summary.ranking),
        "recoveryos_rank": summary.recoveryos_rank,
        "recoveryos_overall_number_one": summary.recoveryos_rank == 1,
        "recoveryos_number_one_dimensions": list(summary.recoveryos_number_one_dimensions),
        "recoveryos_gap_dimensions": list(summary.recoveryos_gap_dimensions),
        "pairwise_status_counts": counts,
        "verdict": (
            "OVERALL_NUMBER_ONE_EVIDENCED"
            if summary.recoveryos_rank == 1
            else "NOT_OVERALL_NUMBER_ONE"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--matrix",
        default="freight/PHASE3_COMPETITIVE_MATRIX_2026-10-07.json",
    )
    parser.add_argument(
        "--evidence",
        default="freight/PHASE3_COMPETITOR_EVIDENCE_2026-10-07.json",
    )
    parser.add_argument("--as-of-date", default="2026-10-07")
    args = parser.parse_args()

    matrix = _load(args.matrix)
    evidence = _load(args.evidence)
    as_of = _iso(args.as_of_date, "as_of_date")
    errors = validate_competitor_evidence(evidence, as_of=as_of)
    errors += validate_matrix(matrix)
    if errors:
        print(json.dumps({"state": "FAIL", "errors": errors}, indent=2, sort_keys=True))
        raise SystemExit(1)

    summary = summarize_matrix(matrix)
    result = {
        "state": "PASS",
        **summary_dict(summary),
        "competitor_evidence_valid_until": evidence["valid_until"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
