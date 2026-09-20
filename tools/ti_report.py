#!/usr/bin/env python3
import json, math
from collections import defaultdict
from datetime import datetime
from ti_common import INTEL, load_jsonl, normalize_run_time

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
outs = load_jsonl("outcomes.jsonl")
strategies = {x["strategy_id"]: x for x in load_jsonl("search_strategies.jsonl")}
aliases = json.loads((INTEL / "strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL / "strategy_aliases.json").exists() else {}

def canonical_strategy(sid):
    s = strategies.get(sid)
    if s and s.get("parent_strategy_id"):
        return s["parent_strategy_id"]
    return aliases.get(sid, sid)

def parse_day(value):
    if not value:
        return None
    text = str(value)[:10]
    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None

days = [parse_day(normalize_run_time(r)) for r in runs]
days += [parse_day(o.get("date")) for o in outs]
days = [d for d in days if d]
reference_day = max(days) if days else None
OUTCOME_LAG_DAYS = 14

def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / den
    return max(0, center-half), min(1, center+half)

def fmt_rate(k, n):
    if not n:
        return "—"
    lo, hi = wilson(k, n)
    return f"{k/n:.1%} [{lo:.1%}, {hi:.1%}]"

out_by_run = defaultdict(list)
for o in outs:
    for rid in o.get("origin_search_ids", []):
        out_by_run[rid].append(o)

groups = defaultdict(list)
query_groups = defaultdict(list)
for r in runs:
    groups[canonical_strategy(r.get("strategy_id"))].append(r)
    query_groups[r.get("query_family") or "unknown"].append(r)

def outcome_eligible(run):
    if not reference_day:
        return False
    day = parse_day(normalize_run_time(run))
    return bool(day and (reference_day - day).days >= OUTCOME_LAG_DAYS)

def summarize(label, rs):
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    candidates = sum((r.get("candidate_count") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs = sum(1 for r in rs if r.get("new_capability_ids"))
    experiment_runs = sum(1 for r in rs if r.get("experiment_ids"))
    search_bearing_runs = sum(1 for r in rs if (r.get("candidate_count") or 0) > 0 or (r.get("deep_inspected") or 0) > 0)

    outcome_objects = []
    seen = set()
    for r in rs:
        for o in out_by_run.get(r["search_run_id"], []):
            if o.get("outcome_id") not in seen:
                seen.add(o.get("outcome_id"))
                outcome_objects.append(o)
    valid = [o for o in outcome_objects if o.get("result") != "INVALID"]
    passed = sum(1 for o in valid if o.get("result") == "PASSED")
    eligible = [r for r in rs if outcome_eligible(r)]
    eligible_with_outcome = sum(1 for r in eligible if any(o.get("result") != "INVALID" for o in out_by_run.get(r["search_run_id"], [])))

    revenue = sum((o.get("revenue_usd") or 0) for o in valid)
    value = sum((o.get("customer_value_usd") or 0) for o in valid)
    days_low = sum((o.get("engineering_days_saved_low") or 0) for o in valid)
    days_high = sum((o.get("engineering_days_saved_high") or 0) for o in valid)

    return {
        "label": label,
        "runs": len(rs),
        "search_bearing_runs": search_bearing_runs,
        "candidates": candidates,
        "inspected": inspected,
        "retained": retained,
        "promoted": promoted,
        "novel_runs": novel_runs,
        "experiment_runs": experiment_runs,
        "outcomes": len(valid),
        "passed_outcomes": passed,
        "eligible_runs": len(eligible),
        "eligible_with_outcome": eligible_with_outcome,
        "revenue": revenue,
        "value": value,
        "days_low": days_low,
        "days_high": days_high,
        "sufficient": len(rs) >= 5 and inspected >= 20
    }

strategy_rows = [summarize(k, v) for k, v in groups.items()]
query_rows = [summarize(k, v) for k, v in query_groups.items()]

def rank_score(row):
    if not row["sufficient"]:
        return -1
    i = max(row["inspected"], 1)
    run_n = max(row["runs"], 1)
    return (
        3.0 * row["promoted"] / i +
        2.0 * row["novel_runs"] / run_n +
        1.5 * row["experiment_runs"] / run_n +
        2.0 * row["outcomes"] / run_n +
        min(row["revenue"] / 10000, 2.0)
    )

strategy_rows.sort(key=lambda x: (-rank_score(x), x["label"]))
query_rows.sort(key=lambda x: (-rank_score(x), x["label"]))

lines = [
    "# LEARNING REPORT", "",
    "Generated from prospective and benchmark search runs. Retrospective anecdotes are excluded from yield denominators.", "",
    f"- Measured runs: **{len(runs)}**",
    f"- Search-bearing runs: **{sum(1 for r in runs if (r.get('candidate_count') or 0) > 0 or (r.get('deep_inspected') or 0) > 0)}**",
    f"- Structured outcomes: **{len(outs)}**",
    f"- Outcome-lag window: **{OUTCOME_LAG_DAYS} days**; recent runs are not counted as outcome failures.", "",
    "## Strategy performance", "",
    "| Strategy | Runs | Inspected | Retained precision | MASTER yield | New-capability run rate | Experiment run rate | Outcomes | Outcome conversion* | Evidence |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
]
for x in strategy_rows:
    outcome_conv = fmt_rate(x["eligible_with_outcome"], x["eligible_runs"])
    lines.append(
        f"| {x['label']} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'],x['inspected'])} | "
        f"{fmt_rate(x['promoted'],x['inspected'])} | {fmt_rate(x['novel_runs'],x['runs'])} | "
        f"{fmt_rate(x['experiment_runs'],x['runs'])} | {x['outcomes']} | {outcome_conv} | "
        f"{'sufficient' if x['sufficient'] else 'insufficient'} |"
    )
if not strategy_rows:
    lines.append("| — | 0 | 0 | — | — | — | — | 0 | — | insufficient |")

lines += [
    "", "*Outcome conversion only uses runs old enough to clear the lag window.", "",
    "## Query-family performance", "",
    "| Query family | Runs | Inspected | Retained precision | MASTER yield | New-capability run rate | Outcomes | Evidence |",
    "|---|---:|---:|---:|---:|---:|---:|---|"
]
for x in query_rows:
    lines.append(
        f"| {x['label']} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'],x['inspected'])} | "
        f"{fmt_rate(x['promoted'],x['inspected'])} | {fmt_rate(x['novel_runs'],x['runs'])} | "
        f"{x['outcomes']} | {'sufficient' if x['sufficient'] else 'insufficient'} |"
    )
if not query_rows:
    lines.append("| — | 0 | 0 | — | — | — | 0 | insufficient |")

valid = [o for o in outs if o.get("result") != "INVALID"]
revenue = sum((o.get("revenue_usd") or 0) for o in valid)
customer_value = sum((o.get("customer_value_usd") or 0) for o in valid)
days_low = sum((o.get("engineering_days_saved_low") or 0) for o in valid)
days_high = sum((o.get("engineering_days_saved_high") or 0) for o in valid)

lines += [
    "", "## Policy", "",
    "- Do not claim a strategy is superior until it has at least 5 measured runs and 20 deep inspections.",
    "- Keep explicit exploration; low-frequency strange discoveries must not be optimized away by short-run precision.",
    "- Realized outcomes outrank predicted repository scores.",
    "- An internal engineering or validation run with zero candidates can still strengthen a capability or experiment, but it does not enter candidate-yield denominators.",
    "- Failed and partial outcomes remain training data.", "",
    "## Realized value traced through the loop", "",
    "- Revenue: **$" + format(revenue, ",.0f") + "**",
    "- Customer value: **$" + format(customer_value, ",.0f") + "**",
    f"- Observed engineering compression: **{days_low:g}–{days_high:g} engineer-days**", ""
]
(INTEL / "LEARNING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(INTEL / "LEARNING_REPORT.md")
