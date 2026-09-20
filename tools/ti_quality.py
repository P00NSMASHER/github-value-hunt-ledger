#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl, normalize_run_time

runs = load_jsonl("search_runs.jsonl")
outs = load_jsonl("outcomes.jsonl")
caps = load_jsonl("capabilities.jsonl")
strategies = {x["strategy_id"]: x for x in load_jsonl("search_strategies.jsonl")}

recommended = [
    ("time", lambda r: bool(normalize_run_time(r))),
    ("hunter", lambda r: bool(r.get("hunter_role") or r.get("hunter"))),
    ("strategy_id", lambda r: bool(r.get("strategy_id"))),
    ("query_family", lambda r: bool(r.get("query_family"))),
    ("measurement_quality", lambda r: bool(r.get("measurement_quality"))),
    ("candidate_count", lambda r: r.get("candidate_count") is not None),
    ("deep_inspected", lambda r: r.get("deep_inspected") is not None),
    ("retained_count", lambda r: r.get("retained_count") is not None),
    ("master_promoted_count", lambda r: r.get("master_promoted_count") is not None),
    ("search_surfaces", lambda r: bool(r.get("search_surfaces"))),
    ("queries", lambda r: bool(r.get("queries"))),
    ("candidate_dispositions", lambda r: r.get("candidate_count", 0) == 0 or bool(r.get("candidate_dispositions"))),
    ("durable_evidence", lambda r: bool(r.get("durable_evidence_path") or r.get("notes")))
]

missing = Counter()
scores = []
issues = []
for r in runs:
    have = 0
    for name, fn in recommended:
        if fn(r):
            have += 1
        else:
            missing[name] += 1
    scores.append(have / len(recommended))
    sid = r.get("strategy_id")
    strategy = strategies.get(sid)
    if not strategy:
        issues.append((r.get("search_run_id"), "unknown_strategy", sid))
    elif strategy.get("status") == "unregistered_observed":
        issues.append((r.get("search_run_id"), "unregistered_strategy_variant", sid))

    c = r.get("candidate_count")
    d = r.get("deep_inspected")
    k = r.get("retained_count")
    m = r.get("master_promoted_count")
    if c is not None and d is not None and d > c:
        issues.append((r.get("search_run_id"), "deep_inspected_gt_candidates", f"{d}>{c}"))
    if d is not None and k is not None and k > d:
        issues.append((r.get("search_run_id"), "retained_gt_inspected", f"{k}>{d}"))
    if k is not None and m is not None and m > k:
        issues.append((r.get("search_run_id"), "master_gt_retained", f"{m}>{k}"))
    dispositions = r.get("candidate_dispositions") or []
    if d and dispositions and len(dispositions) > d:
        issues.append((r.get("search_run_id"), "dispositions_gt_inspected", f"{len(dispositions)}>{d}"))

cap_missing_test = [c["capability_id"] for c in caps if not c.get("next_falsifiable_test")]
avg = sum(scores) / len(scores) if scores else 0
metrics = {
    "search_runs": len(runs),
    "outcomes": len(outs),
    "average_run_completeness": avg,
    "runs_below_70pct_completeness": sum(1 for x in scores if x < .70),
    "issue_count": len(issues),
    "unregistered_strategy_runs": sum(1 for _, kind, _ in issues if kind == "unregistered_strategy_variant"),
    "capabilities_missing_next_test": len(cap_missing_test)
}
(INTEL / "quality_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

lines = [
    "# DATA QUALITY REPORT", "",
    "This report measures whether the learning loop has enough structured evidence to support empirical search-policy updates.", "",
    f"- Search runs: **{len(runs)}**",
    f"- Structured outcomes: **{len(outs)}**",
    f"- Mean search-run field completeness: **{avg:.1%}**",
    f"- Runs below 70% completeness: **{metrics['runs_below_70pct_completeness']}**",
    f"- Structural issues detected: **{len(issues)}**",
    f"- Capabilities without an explicit next falsifiable test: **{len(cap_missing_test)}**", "",
    "## Missing recommended fields", "",
    "| Field | Runs missing |",
    "|---|---:|"
]
for name, count in missing.most_common():
    lines.append(f"| {name} | {count} |")
if not missing:
    lines.append("| — | 0 |")

lines += ["", "## Structural issues", ""]
if issues:
    for rid, kind, detail in issues[:50]:
        lines.append(f"- {rid} — **{kind}**: {detail}")
else:
    lines.append("- None.")

lines += ["", "## Learning bottlenecks", ""]
if not outs:
    lines.append("- **No structured outcomes yet.** Search strategy can learn discovery precision and capability yield, but cannot yet learn realized commercial or engineering value.")
if metrics["unregistered_strategy_runs"]:
    lines.append(f"- **{metrics['unregistered_strategy_runs']} run(s)** use strategy variants not yet formalized in SEARCH_SKILLS.md or mapped to a parent.")
if avg < .85:
    lines.append("- Search-run instrumentation is still inconsistent; prioritize surfaces, literal queries and candidate dispositions so future comparisons are interpretable.")
if avg >= .85 and outs:
    lines.append("- Instrumentation is strong enough for cautious outcome-weighted allocation.")

(INTEL / "DATA_QUALITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(metrics))
