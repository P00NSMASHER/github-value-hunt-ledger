"""Validate RecoveryOS Phase 3 performance evidence and CI regression bounds.

This validator deliberately distinguishes executed measurements, regression
thresholds, and projections. A projection can never satisfy an executed tier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_baseline(baseline: dict) -> list[str]:
    errors: list[str] = []
    if baseline.get("schema_version") != 1:
        errors.append("baseline schema_version must be 1")
    cpu = baseline.get("cpu_rating_benchmark") or {}
    if int(cpu.get("executed_max_records") or 0) < 1_000_000:
        errors.append("baseline must include an executed 1M tier")
    tiers = cpu.get("tiers") or []
    required = {10_000, 100_000, 1_000_000}
    seen = {int(row.get("count") or 0) for row in tiers if isinstance(row, dict)}
    if seen != required:
        errors.append("baseline tiers must be exactly 10K/100K/1M")
    for row in tiers:
        count = int(row.get("count") or 0)
        if float(row.get("throughput_min_rps") or 0) <= 0:
            errors.append(f"tier {count} missing positive observed throughput")
        if float(row.get("regression_floor_rps") or 0) <= 0:
            errors.append(f"tier {count} missing regression throughput floor")
        if float(row.get("regression_floor_rps") or 0) >= float(row.get("throughput_min_rps") or 0):
            errors.append(f"tier {count} regression floor must allow runner noise")
        if float(row.get("regression_p99_ceiling_ms") or 0) <= float(row.get("p99_median_ms") or 0):
            errors.append(f"tier {count} p99 ceiling must exceed observed median")
        if int(row.get("full_replay_trials") or 0) != int(row.get("trials") or 0):
            errors.append(f"tier {count} baseline requires full replay for every trial")
    reliability = baseline.get("reliability") or {}
    failure = reliability.get("missing_authority_failure_injection") or {}
    if failure.get("expected_review") != failure.get("actual_review"):
        errors.append("baseline failure injection did not route exact review count")
    if failure.get("deterministic_replay") is not True:
        errors.append("baseline failure injection replay not deterministic")
    interruption = reliability.get("interruption_recovery") or {}
    if interruption.get("deterministic_resume") is not True:
        errors.append("baseline interruption resume not deterministic")
    if interruption.get("no_duplicate_aggregate") is not True:
        errors.append("baseline interruption replay double-counted aggregate")
    projections = baseline.get("projections_not_executed") or []
    for row in projections:
        if row.get("evidence_type") != "PROJECTION_NOT_EXECUTED":
            errors.append("non-executed scale estimate must be labeled PROJECTION_NOT_EXECUTED")
        if int(row.get("records") or 0) <= int(cpu.get("executed_max_records") or 0):
            errors.append("projection record count must exceed executed maximum")
    if not baseline.get("claim_boundary"):
        errors.append("baseline claim boundary required")
    return errors


def validate_database_evidence(evidence: dict) -> list[str]:
    errors: list[str] = []
    if evidence.get("schema_version") != 1:
        errors.append("database evidence schema_version must be 1")
    write = evidence.get("write_path") or {}
    summary = write.get("summary") or {}
    if int(summary.get("audit_integrity_failures") or 0) != 0:
        errors.append("database write benchmark contains audit integrity failures")
    repeated = write.get("repeated_post_index_10000") or []
    if len(repeated) < 3:
        errors.append("database evidence requires >=3 repeated 10K write trials")
    large = write.get("post_index_100000") or {}
    if int(large.get("rows") or 0) != 100_000:
        errors.append("database evidence requires executed 100K write trial")
    if int(large.get("invalid_hashes") or 0) != 0 or int(large.get("broken_links") or 0) != 0:
        errors.append("database 100K write trial has invalid audit chain")
    if float(large.get("records_per_second") or 0) <= 0:
        errors.append("database 100K write trial missing throughput")
    for row in repeated:
        if int(row.get("invalid_hashes") or 0) != 0 or int(row.get("broken_links") or 0) != 0:
            errors.append("database trial has invalid audit chain")
        if float(row.get("records_per_second") or 0) <= 0:
            errors.append("database trial missing throughput")
    read = evidence.get("read_path") or {}
    decisions = read.get("ten_thousand_findings_with_eleven_thousand_dispositions") or {}
    if decisions.get("expected_latest_confirmed") != decisions.get("latest_confirmed_count"):
        errors.append("latest-decision query returned wrong confirmed count")
    if int(decisions.get("invalid_hashes") or 0) != 0 or int(decisions.get("broken_links") or 0) != 0:
        errors.append("decision-history fixture damaged audit chain")
    if not evidence.get("claim_boundary"):
        errors.append("database evidence claim boundary required")
    return errors


def validate_runtime_report(report: dict, baseline: dict) -> list[str]:
    errors: list[str] = []
    trials = report.get("trials") or []
    grouped: dict[int, list[dict]] = {}
    for trial in trials:
        grouped.setdefault(int(trial.get("count") or 0), []).append(trial)

    for tier in baseline["cpu_rating_benchmark"]["tiers"]:
        count = int(tier["count"])
        actual = grouped.get(count) or []
        if not actual:
            errors.append(f"runtime report missing executed tier {count}")
            continue
        for trial in actual:
            primary = trial.get("primary") or {}
            if int(primary.get("record_count") or 0) != count:
                errors.append(f"tier {count} record count mismatch")
            if int(primary.get("review_count") or 0) != 0:
                errors.append(f"tier {count} nominal workload unexpectedly routed review")
            if float(primary.get("records_per_second") or 0) < float(tier["regression_floor_rps"]):
                errors.append(f"tier {count} throughput below regression floor")
            if float(primary.get("latency_p99_ms") or 0) > float(tier["regression_p99_ceiling_ms"]):
                errors.append(f"tier {count} p99 latency above regression ceiling")
            if float(primary.get("process_max_rss_mb") or 0) > float(tier["regression_rss_ceiling_mb"]):
                errors.append(f"tier {count} RSS above regression ceiling")
            if trial.get("replay") is None:
                errors.append(f"tier {count} must execute full replay")
            if trial.get("deterministic_replay") is not True:
                errors.append(f"tier {count} replay digest mismatch")
            if trial.get("aggregate_replay_equal") is not True:
                errors.append(f"tier {count} replay aggregate mismatch")

    failure = report.get("failure_injection") or {}
    if failure.get("expected_review_count") != failure.get("actual_review_count"):
        errors.append("runtime failure injection review count mismatch")
    if failure.get("deterministic_replay") is not True:
        errors.append("runtime failure injection replay mismatch")

    interruption = report.get("interruption_recovery") or {}
    if interruption.get("deterministic_resume") is not True:
        errors.append("runtime interruption recovery digest mismatch")
    if interruption.get("no_duplicate_aggregate") is not True:
        errors.append("runtime interruption recovery double-counted dollars")
    if int(interruption.get("replayed_chunk_count") or 0) < 1:
        errors.append("runtime interruption recovery did not replay uncertain work")

    probe = report.get("memory_probe") or {}
    limits = baseline["reliability"]["memory_probe"]
    if float(probe.get("python_peak_heap_mb") or 0) > float(limits["regression_python_heap_ceiling_mb"]):
        errors.append("runtime memory probe exceeded Python heap ceiling")
    if float(probe.get("process_max_rss_mb") or 0) > float(limits["regression_rss_ceiling_mb"]):
        errors.append("runtime memory probe exceeded RSS ceiling")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="freight/PHASE3_PERFORMANCE_BASELINE.json")
    parser.add_argument("--database-evidence", default="freight/PHASE3_DATABASE_PERFORMANCE_2026-10-07.json")
    parser.add_argument("--report")
    args = parser.parse_args()

    baseline = _load(args.baseline)
    database = _load(args.database_evidence)
    errors = validate_baseline(baseline) + validate_database_evidence(database)
    if args.report:
        errors += validate_runtime_report(_load(args.report), baseline)
    result = {
        "state": "PASS" if not errors else "FAIL",
        "errors": errors,
        "executed_cpu_max_records": baseline.get("cpu_rating_benchmark", {}).get("executed_max_records"),
        "database_10k_median_records_per_second": database.get("write_path", {}).get("summary", {}).get("median_records_per_second"),
        "projection_count": len(baseline.get("projections_not_executed") or []),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
