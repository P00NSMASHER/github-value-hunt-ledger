#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl, normalize_run_time, outcome_search_weights

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

timed_runs = sum(1 for r in runs if isinstance(r.get("elapsed_minutes"), (int, float)) and r.get("elapsed_minutes") > 0)
tool_metered_runs = sum(1 for r in runs if isinstance(r.get("tool_calls"), int) and r.get("tool_calls") > 0)
explicit_query_ids = sum(1 for r in runs if r.get("query_family_id"))
v3_runs = sum(1 for r in runs if (r.get("schema_version") or 0) >= 3)

credit_outcomes = 0
explicit_credit_outcomes = 0
for o in outs:
    if o.get("origin_search_ids"):
        credit_outcomes += 1
        if isinstance(o.get("search_credit_weights"), dict) and o.get("search_credit_weights"):
            explicit_credit_outcomes += 1
        weights = outcome_search_weights(o)
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            issues.append((o.get("outcome_id"), "outcome_credit_not_conserved", str(sum(weights.values()))))

metrics = {
    "search_runs": len(runs),
    "outcomes": len(outs),
    "average_run_completeness": avg,
    "runs_below_70pct_completeness": sum(1 for x in scores if x < .70),
    "issue_count": len(issues),
    "unregistered_strategy_runs": sum(1 for _, kind, _ in issues if kind == "unregistered_strategy_variant"),
    "capabilities_missing_next_test": len(cap_missing_test),
    "schema_v3_runs": v3_runs,
    "explicit_query_family_id_runs": explicit_query_ids,
    "elapsed_minutes_runs": timed_runs,
    "tool_call_runs": tool_metered_runs,
    "outcomes_with_search_origins": credit_outcomes,
    "outcomes_with_explicit_credit_weights": explicit_credit_outcomes
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
    "## Core missing fields", "",
    "| Field | Runs missing |",
    "|---|---:|"
]

for name, count in missing.most_common():
    lines.append(f"| {name} | {count} |")
if not missing:
    lines.append("| — | 0 |")

lines += [
    "", "## V3 instrumentation coverage", "",
    "| Signal | Instrumented | Total | Coverage |",
    "|---|---:|---:|---:|",
    f"| Schema v3 | {v3_runs} | {len(runs)} | {(v3_runs/len(runs) if runs else 0):.1%} |",
    f"| Explicit query_family_id | {explicit_query_ids} | {len(runs)} | {(explicit_query_ids/len(runs) if runs else 0):.1%} |",
    f"| Elapsed minutes | {timed_runs} | {len(runs)} | {(timed_runs/len(runs) if runs else 0):.1%} |",
    f"| Tool calls | {tool_metered_runs} | {len(runs)} | {(tool_metered_runs/len(runs) if runs else 0):.1%} |",
    f"| Explicit outcome credit weights | {explicit_credit_outcomes} | {credit_outcomes} | {(explicit_credit_outcomes/credit_outcomes if credit_outcomes else 0):.1%} |",
    "", "## Structural issues", ""
]

if issues:
    for rid, kind, detail in issues[:50]:
        lines.append(f"- {rid} — **{kind}**: {detail}")
else:
    lines.append("- None.")

lines += ["", "## Learning bottlenecks", ""]
if not outs:
    lines.append("- No structured outcomes yet: search strategy can learn discovery yield but not realized value.")
if metrics["unregistered_strategy_runs"]:
    lines.append(f"- {metrics['unregistered_strategy_runs']} run(s) use unregistered strategy variants.")
if avg < .85:
    lines.append("- Search-run instrumentation is inconsistent; improve surfaces, literal queries and candidate dispositions.")
if timed_runs == 0:
    lines.append("- No runs record elapsed_minutes yet, so effort-normalized yield is unavailable.")
if tool_metered_runs == 0:
    lines.append("- No runs record tool_calls yet, so tool-efficiency comparisons are unavailable.")
if explicit_query_ids == 0:
    lines.append("- Query families are currently inferred from raw labels; new v3 runs should reuse canonical query_family_id values.")
if credit_outcomes and explicit_credit_outcomes < credit_outcomes:
    lines.append("- Legacy outcomes use equal-split search credit. Add explicit weights only when evidence supports a non-equal split.")
if avg >= .85 and outs:
    lines.append("- Core instrumentation is strong enough for cautious outcome-weighted allocation.")

(INTEL / "DATA_QUALITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(metrics))
