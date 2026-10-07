"""RecoveryOS Phase 3 large-scale reliability/performance benchmark.

The benchmark intentionally measures the real canonical-record construction,
authority resolution and deterministic rating path. It streams records instead
of accumulating a population in memory, keeps only a bounded latency sample,
and hashes the ordered rating hashes into a replay digest.

It does NOT simulate network, PostgreSQL, document extraction, carrier APIs,
human review latency or multi-process concurrency. Those boundaries are part of
the report so synthetic CPU throughput cannot be marketed as production SLA.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import platform
import resource
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from freight.canonical_schema import (
    ChargeLine,
    PackageFacts,
    ShipmentFacts,
    SourceArtifact,
    build_record,
)
from freight.contracts import canonical_hash
from freight.rate_authority import AuthorityBook, compile_authority
from freight.rating_engine import RATED, REVIEW_REQUIRED, rate_record


MODES = ("PARCEL", "LTL", "TL", "INTERMODAL", "AIR", "OCEAN")
SOURCE = SourceArtifact(
    source_id="phase3:synthetic:source",
    kind="SYNTHETIC_BENCHMARK",
    sha256="a" * 64,
    observed_at="2026-10-07T04:30:00.000000Z",
    transport="BATCH",
    filename="phase3-synthetic.json",
)


@dataclass(frozen=True)
class PassMetrics:
    record_count: int
    rated_count: int
    review_count: int
    billed_cents: int
    expected_cents: int
    variance_cents: int
    elapsed_seconds: float
    records_per_second: float
    latency_sample_count: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    python_peak_heap_mb: float
    process_max_rss_mb: float
    result_digest: str


@dataclass(frozen=True)
class ScaleTrial:
    count: int
    trial: int
    primary: PassMetrics
    replay: PassMetrics | None
    deterministic_replay: bool | None
    aggregate_replay_equal: bool | None


@dataclass(frozen=True)
class FailureInjectionResult:
    record_count: int
    expected_review_count: int
    actual_review_count: int
    rated_count: int
    deterministic_digest: str
    replay_digest: str
    deterministic_replay: bool


@dataclass(frozen=True)
class BenchmarkReport:
    schema_version: int
    generated_at_utc: str
    python_version: str
    platform: str
    processor: str
    mode_count: int
    trials: tuple[ScaleTrial, ...]
    failure_injection: FailureInjectionResult
    claims_boundary: tuple[str, ...]
    report_hash: str


def _authority(
    mode: str,
    terms: dict,
    *,
    carrier_id: str | None = None,
) -> object:
    return compile_authority(
        {
            "authority_id": "PHASE3-AUTH-" + mode,
            "buyer_id": "PHASE3-BUYER",
            "business_unit": "PHASE3-BU",
            "customer_id": "PHASE3-CUSTOMER",
            "carrier_id": carrier_id or "CARRIER-" + mode,
            "currency": "USD",
            "mode": mode,
            "effective_from": "2026-01-01",
            "priority": 100,
            "terms": terms,
        },
        source_sha256=("b" * 63) + str(MODES.index(mode)),
        verified_controlling_authority=True,
    )


def build_authority_book() -> AuthorityBook:
    authorities = (
        _authority(
            "PARCEL",
            {
                "dimensional_divisor": 139,
                "fuel_bps": 1_000,
                "residential_cents": 0,
                "weight_bands": [
                    {"max_billable_lb": 5, "zone_rates_cents": {"2": 1_200}},
                    {"max_billable_lb": 20, "zone_rates_cents": {"2": 2_500}},
                ],
            },
        ),
        _authority(
            "LTL",
            {
                "per_cwt_cents": 9_000,
                "minimum_cents": 10_000,
                "discount_bps": 0,
                "fuel_bps": 1_000,
                "lane_multiplier_bps": 10_000,
                "class_multipliers_bps": {"70": 10_000},
            },
        ),
        _authority(
            "TL",
            {
                "pricing_model": "PER_MILE",
                "per_mile_cents": 200,
                "minimum_cents": 80_000,
                "fuel_bps": 1_000,
            },
        ),
        _authority(
            "INTERMODAL",
            {
                "base_cents": 50_000,
                "per_mile_cents": 100,
                "fuel_bps": 1_000,
                "chassis_per_day_cents": 3_000,
            },
        ),
        _authority(
            "AIR",
            {
                "per_kg_cents": 500,
                "minimum_cents": 1_000,
                "volumetric_divisor_cm3_per_kg": 6_000,
                "fuel_bps": 1_000,
                "security_per_kg_cents": 20,
            },
        ),
        _authority(
            "OCEAN",
            {
                "pricing_model": "CONTAINER",
                "container_rates_cents": {"20GP": 150_000, "40HC": 200_000},
                "minimum_cents": 0,
                "fuel_bps": 1_000,
            },
        ),
    )
    return AuthorityBook(authorities)


def _source_for(index: int) -> SourceArtifact:
    # Keep source content stable but source_id unique, forcing every canonical
    # record hash through the full build/verify path.
    return SourceArtifact(
        source_id=f"phase3:source:{index}",
        kind=SOURCE.kind,
        sha256=SOURCE.sha256,
        observed_at=SOURCE.observed_at,
        transport=SOURCE.transport,
        filename=SOURCE.filename,
    )


def make_record(index: int, *, force_missing_authority: bool = False):
    mode = MODES[index % len(MODES)]
    suffix = f"{index:09d}"
    carrier_id = ("MISSING-" if force_missing_authority else "CARRIER-") + mode
    packages: tuple[PackageFacts, ...] = ()
    freight_class = None
    zone = None
    miles = None
    chassis_days = None
    container_type = None

    if mode == "PARCEL":
        packages = (
            PackageFacts(
                package_id="PKG-" + suffix,
                weight_grams=2_000,
                length_mm=300,
                width_mm=200,
                height_mm=150,
            ),
        )
        zone = "2"
        charges = (
            ChargeLine("TR-" + suffix, "TRANSPORTATION", 1_350),
            ChargeLine("FU-" + suffix, "FUEL", 135),
        )
        actual_weight = 2_000
    elif mode == "LTL":
        freight_class = "70"
        charges = (
            ChargeLine("LH-" + suffix, "LINEHAUL", 18_500),
            ChargeLine("FU-" + suffix, "FUEL", 1_850),
        )
        actual_weight = 90_000
    elif mode == "TL":
        miles = 500
        charges = (
            ChargeLine("LH-" + suffix, "LINEHAUL", 105_000),
            ChargeLine("FU-" + suffix, "FUEL", 10_500),
        )
        actual_weight = 8_000_000
    elif mode == "INTERMODAL":
        miles = 100
        chassis_days = 2
        charges = (
            ChargeLine("TR-" + suffix, "TRANSPORTATION", 62_000),
            ChargeLine("FU-" + suffix, "FUEL", 6_200),
            ChargeLine("CH-" + suffix, "CHASSIS", 6_500),
        )
        actual_weight = 10_000_000
    elif mode == "AIR":
        packages = (
            PackageFacts(
                package_id="AIR-" + suffix,
                weight_grams=5_000,
                length_mm=500,
                width_mm=400,
                height_mm=300,
            ),
        )
        charges = (
            ChargeLine("TR-" + suffix, "TRANSPORTATION", 5_200),
            ChargeLine("FU-" + suffix, "FUEL", 520),
            ChargeLine("SE-" + suffix, "SECURITY", 220),
        )
        actual_weight = 5_000
    else:
        container_type = "40HC"
        charges = (
            ChargeLine("TR-" + suffix, "TRANSPORTATION", 205_000),
            ChargeLine("FU-" + suffix, "FUEL", 20_500),
        )
        actual_weight = 12_000_000

    shipment = ShipmentFacts(
        shipment_id="SHIP-" + suffix,
        carrier_id=carrier_id,
        mode=mode,
        service_date="2026-10-01",
        origin_postal="17901",
        destination_postal="21224",
        actual_weight_grams=actual_weight,
        package_count=sum(item.quantity for item in packages) if packages else 1,
        packages=packages,
        freight_class=freight_class,
        zone=zone,
        service_level="BENCH",
        residential=False,
        miles=miles,
        container_type=container_type,
        chassis_days=chassis_days,
    )
    return build_record(
        buyer_id="PHASE3-BUYER",
        business_unit="PHASE3-BU",
        invoice_id="INV-" + suffix,
        invoice_date="2026-10-02",
        customer_id="PHASE3-CUSTOMER",
        currency="USD",
        shipment=shipment,
        charges=charges,
        sources=(_source_for(index),),
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[min(rank, len(ordered) - 1)]


def _max_rss_mb() -> float:
    # Linux reports ru_maxrss in KiB; macOS reports bytes. GitHub Actions uses
    # Linux, but keep this helper portable enough for local diagnostics.
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return raw / (1024 * 1024)
    return raw / 1024


def _run_pass(
    count: int,
    authority_book: AuthorityBook,
    *,
    sample_target: int = 10_000,
    missing_authority_every: int | None = None,
) -> PassMetrics:
    if count <= 0:
        raise ValueError("count must be positive")
    sample_stride = max(1, count // max(1, sample_target))
    latencies_ms: list[float] = []
    digest = hashlib.sha256()
    rated = review = 0
    billed = expected = variance = 0

    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    for index in range(count):
        missing = (
            missing_authority_every is not None
            and missing_authority_every > 0
            and index % missing_authority_every == 0
        )
        sample = index % sample_stride == 0
        t0 = time.perf_counter() if sample else 0.0
        record = make_record(index, force_missing_authority=missing)
        result = rate_record(record, authority_book)
        if sample:
            latencies_ms.append((time.perf_counter() - t0) * 1_000)

        digest.update(result.rating_hash.encode("ascii"))
        digest.update(b"\n")
        if result.status == RATED:
            rated += 1
        elif result.status == REVIEW_REQUIRED:
            review += 1
        else:
            raise ValueError("unexpected rating status: " + result.status)
        billed += result.billed_total_cents
        expected += result.expected_total_cents or 0
        variance += result.variance_cents or 0

    elapsed = max(time.perf_counter() - start, 1e-12)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return PassMetrics(
        record_count=count,
        rated_count=rated,
        review_count=review,
        billed_cents=billed,
        expected_cents=expected,
        variance_cents=variance,
        elapsed_seconds=elapsed,
        records_per_second=count / elapsed,
        latency_sample_count=len(latencies_ms),
        latency_p50_ms=_percentile(latencies_ms, 0.50),
        latency_p95_ms=_percentile(latencies_ms, 0.95),
        latency_p99_ms=_percentile(latencies_ms, 0.99),
        python_peak_heap_mb=peak / (1024 * 1024),
        process_max_rss_mb=_max_rss_mb(),
        result_digest=digest.hexdigest(),
    )


def run_trial(
    count: int,
    trial: int,
    *,
    replay: bool,
    authority_book: AuthorityBook | None = None,
) -> ScaleTrial:
    authority_book = authority_book or build_authority_book()
    primary = _run_pass(count, authority_book)
    replay_metrics = _run_pass(count, authority_book) if replay else None
    deterministic = (
        primary.result_digest == replay_metrics.result_digest
        if replay_metrics is not None
        else None
    )
    aggregate_equal = (
        (
            primary.rated_count,
            primary.review_count,
            primary.billed_cents,
            primary.expected_cents,
            primary.variance_cents,
        )
        == (
            replay_metrics.rated_count,
            replay_metrics.review_count,
            replay_metrics.billed_cents,
            replay_metrics.expected_cents,
            replay_metrics.variance_cents,
        )
        if replay_metrics is not None
        else None
    )
    return ScaleTrial(
        count=count,
        trial=trial,
        primary=primary,
        replay=replay_metrics,
        deterministic_replay=deterministic,
        aggregate_replay_equal=aggregate_equal,
    )


def run_failure_injection(
    count: int = 10_000,
    missing_authority_every: int = 97,
) -> FailureInjectionResult:
    book = build_authority_book()
    first = _run_pass(
        count,
        book,
        missing_authority_every=missing_authority_every,
    )
    replay = _run_pass(
        count,
        book,
        missing_authority_every=missing_authority_every,
    )
    expected_reviews = ((count - 1) // missing_authority_every) + 1
    if first.review_count != expected_reviews:
        raise AssertionError(
            f"expected {expected_reviews} review-routed records, got {first.review_count}"
        )
    return FailureInjectionResult(
        record_count=count,
        expected_review_count=expected_reviews,
        actual_review_count=first.review_count,
        rated_count=first.rated_count,
        deterministic_digest=first.result_digest,
        replay_digest=replay.result_digest,
        deterministic_replay=first.result_digest == replay.result_digest,
    )


def _trial_counts(
    counts: Iterable[int],
    *,
    small_trials: int,
    medium_trials: int,
    large_trials: int,
) -> list[tuple[int, int]]:
    counts = tuple(counts)
    out: list[tuple[int, int]] = []
    for count in counts:
        if count <= 10_000:
            trials = small_trials
        elif count <= 100_000:
            trials = medium_trials
        else:
            trials = large_trials
        for trial in range(1, trials + 1):
            out.append((count, trial))
    return out


def build_report(
    counts: Iterable[int],
    *,
    small_trials: int = 5,
    medium_trials: int = 3,
    large_trials: int = 1,
    replay_max_count: int = 100_000,
    failure_count: int = 10_000,
) -> BenchmarkReport:
    book = build_authority_book()
    trials: list[ScaleTrial] = []
    for count, trial in _trial_counts(
        counts,
        small_trials=small_trials,
        medium_trials=medium_trials,
        large_trials=large_trials,
    ):
        trials.append(
            run_trial(
                count,
                trial,
                replay=count <= replay_max_count,
                authority_book=book,
            )
        )

    failure = run_failure_injection(failure_count)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    boundary = (
        "Synthetic CPU benchmark, not production SLA or customer workload evidence.",
        "Measures canonical build + authority resolution + rerating in one Python process.",
        "Does not measure network, PostgreSQL, document parsing, carrier APIs, AI, or human-review latency.",
        "GitHub-hosted runner performance is noisy and must not be treated as dedicated production hardware.",
        "Counts above the largest executed tier are projections only and must be labeled projections.",
    )
    body = {
        "schema_version": 1,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "mode_count": len(MODES),
        "trials": [asdict(item) for item in trials],
        "failure_injection": asdict(failure),
        "claims_boundary": list(boundary),
    }
    return BenchmarkReport(
        schema_version=1,
        generated_at_utc=generated,
        python_version=body["python_version"],
        platform=body["platform"],
        processor=body["processor"],
        mode_count=len(MODES),
        trials=tuple(trials),
        failure_injection=failure,
        claims_boundary=boundary,
        report_hash=canonical_hash(body),
    )


def validate_report(report: BenchmarkReport) -> None:
    if not report.trials:
        raise ValueError("benchmark report has no trials")
    for trial in report.trials:
        if trial.primary.rated_count + trial.primary.review_count != trial.count:
            raise ValueError("benchmark result count mismatch")
        if trial.primary.review_count != 0:
            raise ValueError("nominal scale trial unexpectedly routed records to review")
        if trial.primary.records_per_second <= 0:
            raise ValueError("benchmark throughput must be positive")
        if trial.replay is not None:
            if trial.deterministic_replay is not True:
                raise ValueError("deterministic replay failed")
            if trial.aggregate_replay_equal is not True:
                raise ValueError("replay aggregate mismatch")
    if not report.failure_injection.deterministic_replay:
        raise ValueError("failure-injection replay was not deterministic")
    if (
        report.failure_injection.actual_review_count
        != report.failure_injection.expected_review_count
    ):
        raise ValueError("failure-injection review count mismatch")


def report_dict(report: BenchmarkReport) -> dict:
    return asdict(report)


def _summary(report: BenchmarkReport) -> dict:
    by_count: dict[int, list[ScaleTrial]] = {}
    for trial in report.trials:
        by_count.setdefault(trial.count, []).append(trial)
    tiers = []
    for count, trials in sorted(by_count.items()):
        throughput = [t.primary.records_per_second for t in trials]
        p99 = [t.primary.latency_p99_ms for t in trials]
        rss = [t.primary.process_max_rss_mb for t in trials]
        tiers.append(
            {
                "count": count,
                "trials": len(trials),
                "throughput_records_per_second_median": statistics.median(throughput),
                "throughput_records_per_second_min": min(throughput),
                "throughput_records_per_second_max": max(throughput),
                "latency_p99_ms_median": statistics.median(p99),
                "max_rss_mb_max": max(rss),
                "full_replay_trials": sum(t.replay is not None for t in trials),
            }
        )
    return {
        "report_hash": report.report_hash,
        "tiers": tiers,
        "failure_injection": asdict(report.failure_injection),
        "claims_boundary": list(report.claims_boundary),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", nargs="+", type=int, default=[10_000, 100_000])
    parser.add_argument("--small-trials", type=int, default=5)
    parser.add_argument("--medium-trials", type=int, default=3)
    parser.add_argument("--large-trials", type=int, default=1)
    parser.add_argument("--replay-max-count", type=int, default=100_000)
    parser.add_argument("--failure-count", type=int, default=10_000)
    parser.add_argument("--output")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    report = build_report(
        args.counts,
        small_trials=args.small_trials,
        medium_trials=args.medium_trials,
        large_trials=args.large_trials,
        replay_max_count=args.replay_max_count,
        failure_count=args.failure_count,
    )
    validate_report(report)
    payload = report_dict(report)
    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(_summary(report) if args.summary else payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
