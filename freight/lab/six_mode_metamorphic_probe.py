"""Six-mode metamorphic stress suite for the actual RecoveryOS rating engine.

Uses the existing frozen, code-adjacent 20-case gold fixture as a base.
Changes only invoice billed cents. Therefore the contract-expected amount,
authority resolution, and review blockers must remain unchanged. This is an
invariance test, not independent six-mode tariff certification.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import time
from collections import Counter
from pathlib import Path

from freight.accuracy_benchmark import _book, _build_record
from freight.rating_engine import rate_record, RATED, REVIEW_REQUIRED

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "phase3_accuracy_gold_v1.json"


def run(iterations: int = 1000, seed: int = 20261007) -> dict:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    fixture = json.loads(FIXTURE.read_text())
    source_cases = fixture["rating_cases"]
    rng = random.Random(seed)
    by_mode = Counter()
    failures = []
    calls = 0
    failure_count = 0
    start = time.perf_counter()
    cases = []
    for case in source_cases:
        rec = _build_record("base:" + case["id"], case["record"], fixture["common"])
        book = _book(case["authority_profiles"], fixture)
        original = rate_record(rec, book)
        if (original.status != case["expected"]["status"] or
            original.expected_total_cents != case["expected"]["expected_total_cents"] or
            original.variance_cents != case["expected"]["variance_cents"]):
            raise AssertionError("frozen gold mismatch on baseline: " + case["id"])
        cases.append((case, book, original))
    for sequence in range(iterations):
        for case, book, original in cases:
            raw = copy.deepcopy(case["record"])
            old = raw["charges"][0]
            delta = rng.randint(1, 80000)
            raw["charges"][0] = [old[0], old[1] + delta]
            record = _build_record(f"mutation:{seed}:{sequence}:{case['id']}", raw, fixture["common"])
            observed = rate_record(record, book)
            calls += 1
            by_mode[raw["mode"]] += 1
            expected_variance = (
                max(0, record.billed_total_cents - original.expected_total_cents)
                if original.expected_total_cents is not None else None
            )
            same = (
                observed.status == original.status and
                observed.expected_total_cents == original.expected_total_cents and
                observed.authority_id == original.authority_id and
                observed.variance_cents == expected_variance and
                observed.blockers == original.blockers and
                observed.record_hash == record.record_hash and
                len(observed.rating_hash) == 64
            )
            if not same:
                failure_count += 1
                if len(failures) < 30:
                    failures.append({
                    "case": case["id"], "iteration": sequence,
                    "expected_status": original.status,
                    "observed_status": observed.status,
                    "expected_expected_cents": original.expected_total_cents,
                    "observed_expected_cents": observed.expected_total_cents,
                    "expected_variance_cents": expected_variance,
                    "observed_variance_cents": observed.variance_cents,
                    "old_blockers": original.blockers, "new_blockers": observed.blockers
                })
    return {
        "schema_version": 1,
        "scope": "REAL_ENGINE_SYNTHETIC_6_MODE_METAMORPHIC_ONLY",
        "seed": seed, "iterations_per_case": iterations,
        "base_gold_cases": len(cases), "rated_calls": calls,
        "by_mode": dict(sorted(by_mode.items())),
        "failures": failures, "failure_count": failure_count,
        "elapsed_seconds": round(time.perf_counter()-start,3),
        "claim_boundary": (
            "Checks billing-change invariance, not six-mode tariff truth, OCR, "
            "actual customer accuracy, end-to-end latency or collections."
        )
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261007)
    args = parser.parse_args()
    print(json.dumps(run(args.iterations, args.seed), indent=2))
