#!/usr/bin/env python3
"""Aggregate per-shard FMC recovery quality metrics into one durable report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def add_numeric(dst: dict[str, float], src: dict[str, Any]) -> None:
    for key, value in src.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            dst[key] = dst.get(key, 0) + value


def pct(numerator: float, denominator: float) -> float:
    return round((100.0 * numerator / denominator), 2) if denominator else 0.0


def build_rollup(root: Path) -> dict[str, Any]:
    shard_dirs = sorted(
        {path.parent for path in root.rglob("summary.json")},
        key=lambda p: str(p),
    )

    pre_summary: dict[str, float] = {}
    post_summary: dict[str, float] = {}
    revalidation: dict[str, float] = {}
    reparse: dict[str, float] = {}
    retry: dict[str, float] = {}
    retry_reasons: dict[str, int] = {}
    shards: list[dict[str, Any]] = []

    for shard_dir in shard_dirs:
        before = load_json(shard_dir / "summary_prevalidation.json") or {}
        after = load_json(shard_dir / "summary.json") or {}
        validation = load_json(shard_dir / "revalidation.json") or {}
        reparsed = load_json(shard_dir / "reparse.json") or {}
        retried = load_json(shard_dir / "retry_transient.json") or {}

        add_numeric(pre_summary, before)
        add_numeric(post_summary, after)
        add_numeric(revalidation, validation)
        add_numeric(reparse, reparsed)
        add_numeric(retry, retried)

        for reason, count in (retried.get("reason_counts") or {}).items():
            if isinstance(count, int):
                retry_reasons[reason] = retry_reasons.get(reason, 0) + count

        shards.append({
            "path": str(shard_dir.relative_to(root)),
            "pre_terms": before.get("terms"),
            "post_terms": after.get("terms"),
            "pre_effective_dated_terms": before.get("effective_dated_terms"),
            "post_effective_dated_terms": after.get("effective_dated_terms"),
            "bogus_rule_terms_removed": validation.get("bogus_rule_terms_removed"),
            "generic_shared_terms_quarantined": validation.get(
                "terms_quarantined_shared_generic"
            ),
            "terms_inserted_by_reparse": reparsed.get("terms_inserted"),
            "retry_targets": retried.get("targets"),
            "retry_recovered": retried.get("recovered"),
            "retry_failed": retried.get("failed"),
        })

    before_terms = pre_summary.get("terms", 0)
    after_terms = post_summary.get("terms", 0)
    before_dated = pre_summary.get("effective_dated_terms", 0)
    after_dated = post_summary.get("effective_dated_terms", 0)

    return {
        "shards_found": len(shard_dirs),
        "before": {
            **pre_summary,
            "effective_date_coverage_pct": pct(before_dated, before_terms),
        },
        "after": {
            **post_summary,
            "effective_date_coverage_pct": pct(after_dated, after_terms),
        },
        "delta": {
            "terms": after_terms - before_terms,
            "terms_pct": round(
                (100.0 * (after_terms - before_terms) / before_terms),
                2,
            ) if before_terms else 0.0,
            "effective_dated_terms": after_dated - before_dated,
            "effective_dated_terms_pct": round(
                (100.0 * (after_dated - before_dated) / before_dated),
                2,
            ) if before_dated else 0.0,
            "effective_date_coverage_points": round(
                pct(after_dated, after_terms) - pct(before_dated, before_terms),
                2,
            ),
        },
        "revalidation": revalidation,
        "reparse": reparse,
        "retry": {
            **retry,
            "reason_counts": dict(
                sorted(retry_reasons.items(), key=lambda item: (-item[1], item[0]))
            ),
        },
        "shards": shards,
        "notes": {
            "raw_evidence_deleted": False,
            "quarantine_changes_normalized_terms_only": True,
            "effective_dates_are_source_extracted_not_observation_inferred": True,
            "observation_time_is_tracked_separately": True,
            "retry_is_bounded_to_transient_failure_classes": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-root", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    result = build_rollup(Path(args.input_root))
    payload = json.dumps(result, indent=2, sort_keys=False) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
