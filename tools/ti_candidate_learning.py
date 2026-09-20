#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from ti_common import INTEL, load_jsonl

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
reason_catalog = json.loads((INTEL / "reason_codes.json").read_text(encoding="utf-8")) if (INTEL / "reason_codes.json").exists() else {}
standard = set()
for values in reason_catalog.values():
    standard.update(values)

status_counts = Counter()
standard_reasons = Counter()
custom_reasons = Counter()
strategy_candidates = Counter()
novelty = Counter()
evidence = Counter()
replacement_ranges = []
total = 0

def bucket(status):
    s = (status or "").lower()
    if "quarant" in s or "safety" in s:
        return "quarantined"
    if "reject" in s or "negative" in s:
        return "rejected_or_negative"
    if "master" in s:
        return "master"
    if "strong" in s:
        return "strong"
    if "watch" in s:
        return "watch"
    return "other"

for r in runs:
    for d in r.get("candidate_dispositions") or []:
        total += 1
        status_counts[bucket(d.get("status"))] += 1
        strategy_candidates[r.get("strategy_id") or "unknown"] += 1
        legacy = d.get("reason_code")
        std = d.get("reason_code_standard")
        if std:
            standard_reasons[std] += 1
        elif legacy in standard:
            standard_reasons[legacy] += 1
        elif legacy:
            custom_reasons[legacy] += 1
        if d.get("novelty_ordinal") is not None:
            novelty[int(d["novelty_ordinal"])] += 1
        if d.get("evidence_ordinal") is not None:
            evidence[int(d["evidence_ordinal"])] += 1
        lo, hi = d.get("replacement_days_low"), d.get("replacement_days_high")
        if lo is not None or hi is not None:
            replacement_ranges.append((lo, hi))

metrics = {
    "candidate_dispositions": total,
    "status_counts": dict(status_counts),
    "standard_reason_counts": dict(standard_reasons),
    "custom_reason_count": sum(custom_reasons.values()),
    "unique_custom_reasons": len(custom_reasons),
    "top_custom_reasons": custom_reasons.most_common(30),
    "novelty_ordinal_counts": dict(sorted(novelty.items())),
    "evidence_ordinal_counts": dict(sorted(evidence.items())),
    "replacement_range_count": len(replacement_ranges)
}
(INTEL / "candidate_learning_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

lines = [
    "# NEGATIVE TRAINING / CANDIDATE LEARNING REPORT", "",
    "Candidate-level dispositions are the bridge between broad discovery and cheap triage. This report measures what the system is rejecting, retaining and still failing to encode consistently.", "",
    f"- Structured candidate dispositions: **{total}**",
    f"- Candidate records using controlled reason codes: **{sum(standard_reasons.values())}**",
    f"- Candidate records using free-form/custom reason codes: **{sum(custom_reasons.values())}**",
    f"- Unique custom reason strings: **{len(custom_reasons)}**", "",
    "## Disposition mix", "",
    "| Status | Count |",
    "|---|---:|"
]
for k,v in status_counts.most_common():
    lines.append(f"| {k} | {v} |")
if not status_counts:
    lines.append("| — | 0 |")

lines += ["", "## Controlled reasons observed", "", "| Reason | Count |", "|---|---:|"]
for k,v in standard_reasons.most_common(20):
    lines.append(f"| {k} | {v} |")
if not standard_reasons:
    lines.append("| — | 0 |")

lines += ["", "## Free-form reasons that should eventually map to controlled reasons", "", "| Reason | Count |", "|---|---:|"]
for k,v in custom_reasons.most_common(25):
    lines.append(f"| {k} | {v} |")
if not custom_reasons:
    lines.append("| — | 0 |")

lines += [
    "", "## Learning policy", "",
    "- V3 search runs should use `reason_code_standard` for machine learning and `reason_detail` for the precise technical explanation.",
    "- Never discard the detailed reason text: standardized categories are for aggregation, not a substitute for evidence.",
    "- A frequently observed rejection reason can become a cheap prefilter only after confirming that it does not suppress rare high-value discoveries.",
    "- Track false negatives explicitly whenever a candidate initially filtered out is later promoted.", ""
]
(INTEL / "NEGATIVE_TRAINING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"candidates": total, "controlled_reasons": sum(standard_reasons.values()), "custom_reasons": sum(custom_reasons.values())}))
