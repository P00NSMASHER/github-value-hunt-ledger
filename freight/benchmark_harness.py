"""Deterministic correctness/throughput benchmark harness for RecoveryOS phase 0."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

from freight.canonical_schema import CanonicalFreightRecord
from freight.contracts import canonical_hash
from freight.rate_authority import AuthorityBook
from freight.rating_engine import RATED, REVIEW_REQUIRED, rate_record


@dataclass(frozen=True)
class BenchmarkResult:
    record_count: int
    rated_count: int
    review_count: int
    billed_cents: int
    expected_cents: int
    variance_cents: int
    deterministic_replay: bool
    elapsed_seconds: float
    records_per_second: float
    benchmark_hash: str


def run_benchmark(
    records: Iterable[CanonicalFreightRecord],
    authority_book: AuthorityBook,
) -> BenchmarkResult:
    population = tuple(records)
    start = perf_counter()
    first = tuple(rate_record(record, authority_book) for record in population)
    elapsed = max(perf_counter() - start, 1e-12)

    replay = tuple(rate_record(record, authority_book) for record in population)
    deterministic = tuple(x.rating_hash for x in first) == tuple(x.rating_hash for x in replay)

    rated_count = sum(x.status == RATED for x in first)
    review_count = sum(x.status == REVIEW_REQUIRED for x in first)
    billed = sum(x.billed_total_cents for x in first)
    expected = sum(x.expected_total_cents or 0 for x in first)
    variance = sum(x.variance_cents or 0 for x in first)
    stable_body = {
        "schema": 1,
        "record_count": len(population),
        "rated_count": rated_count,
        "review_count": review_count,
        "billed_cents": billed,
        "expected_cents": expected,
        "variance_cents": variance,
        "deterministic_replay": deterministic,
        "rating_hashes": [x.rating_hash for x in first],
    }
    return BenchmarkResult(
        record_count=len(population),
        rated_count=rated_count,
        review_count=review_count,
        billed_cents=billed,
        expected_cents=expected,
        variance_cents=variance,
        deterministic_replay=deterministic,
        elapsed_seconds=elapsed,
        records_per_second=(len(population) / elapsed if population else 0.0),
        benchmark_hash=canonical_hash(stable_body),
    )
