#!/usr/bin/env python3
import json, math
from collections import Counter, defaultdict
from datetime import datetime
from ti_common import (
    INTEL,
    canonical_query_family,
    load_jsonl,
    normalize_run_time,
    outcome_search_weights,
)

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
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
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

def fmt_float(value):
    return f"{value:.2f}" if value is not None else "—"

def outcome_eligible(run):
    if not reference_day:
        return False
    day = parse_day(normalize_run_time(run))
    return bool(day and (reference_day - day).days >= OUTCOME_LAG_DAYS)

out_weights = {}
out_by_run = defaultdict(list)
for o in outs:
    weights = outcome_search_weights(o)
    out_weights[o.get("outcome_id")] = weights
    for rid, weight in weights.items():
        out_by_run[rid].append((o, weight))

strategy_groups = defaultdict(list)
query_groups = defaultdict(list)
query_labels = defaultdict(Counter)

for r in runs:
    strategy_groups[canonical_strategy(r.get("strategy_id"))].append(r)
    qid = canonical_query_family(r)
    query_groups[qid].append(r)
    query_labels[qid][(r.get("query_family") or qid).strip()] += 1

def summarize(label, rs):
    run_ids = {r["search_run_id"] for r in rs}
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    candidates = sum((r.get("candidate_count") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs = sum(1 for r in rs if r.get("new_capability_ids"))
    experiment_runs = sum(1 for r in rs if r.get("experiment_ids"))
    search_bearing_runs = sum(1 for r in rs if (r.get("candidate_count") or 0) > 0 or (r.get("deep_inspected") or 0) > 0)

    outcome_credit = 0.0
    passed_credit = 0.0
    partial_credit = 0.0
    revenue = 0.0
    value = 0.0
    days_low = 0.0
    days_high = 0.0

    for o in outs:
        if o.get("result") == "INVALID":
            continue
        weights = out_weights.get(o.get("outcome_id"), {})
        credit = sum(weight for rid, weight in weights.items() if rid in run_ids)
        if credit <= 0:
            continue
        outcome_credit += credit
        if o.get("result") == "PASSED":
            passed_credit += credit
        elif o.get("result") == "PARTIAL":
            partial_credit += credit
        revenue += (o.get("revenue_usd") or 0) * credit
        value += (o.get("customer_value_usd") or 0) * credit
        days_low += (o.get("engineering_days_saved_low") or 0) * credit
        days_high += (o.get("engineering_days_saved_high") or 0) * credit

    eligible = [r for r in rs if outcome_eligible(r)]
    eligible_with_outcome = 0
    for r in eligible:
        rid = r["search_run_id"]
        if any(o.get("result") != "INVALID" and weight > 0 for o, weight in out_by_run.get(rid, [])):
            eligible_with_outcome += 1

    timed = [r for r in rs if isinstance(r.get("elapsed_minutes"), (int, float)) and r.get("elapsed_minutes") > 0]
    timed_minutes = sum(r["elapsed_minutes"] for r in timed)
    timed_inspected = sum((r.get("deep_inspected") or 0) for r in timed)
    timed_retained = sum((r.get("retained_count") or 0) for r in timed)
    timed_promoted = sum((r.get("master_promoted_count") or 0) for r in timed)

    called = [r for r in rs if isinstance(r.get("tool_calls"), int) and r.get("tool_calls") > 0]
    tool_calls = sum(r["tool_calls"] for r in called)
    call_inspected = sum((r.get("deep_inspected") or 0) for r in called)
    call_retained = sum((r.get("retained_count") or 0) for r in called)

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
        "outcome_credit": outcome_credit,
        "passed_credit": passed_credit,
        "partial_credit": partial_credit,
        "eligible_runs": len(eligible),
        "eligible_with_outcome": eligible_with_outcome,
        "revenue": revenue,
        "value": value,
        "days_low": days_low,
        "days_high": days_high,
        "timed_runs": len(timed),
        "timed_minutes": timed_minutes,
        "timed_inspected": timed_inspected,
        "timed_retained": timed_retained,
        "timed_promoted": timed_promoted,
        "tool_runs": len(called),
        "tool_calls": tool_calls,
        "call_inspected": call_inspected,
        "call_retained": call_retained,
        "sufficient": len(rs) >= 5 and inspected >= 20,
    }

strategy_rows = [summarize(k, v) for k, v in strategy_groups.items()]
query_rows = [summarize(k, v) for k, v in query_groups.items()]

def rank_score(row):
    if not row["sufficient"]:
        return -1
    i = max(row["inspected"], 1)
    run_n = max(row["runs"], 1)
    return (
        3.0 * row["promoted"] / i
        + 2.0 * row["novel_runs"] / run_n
        + 1.5 * row["experiment_runs"] / run_n
        + 2.0 * row["outcome_credit"] / run_n
        + min(row["revenue"] / 10000, 2.0)
    )

strategy_rows.sort(key=lambda x: (-rank_score(x), x["label"]))
query_rows.sort(key=lambda x: (-rank_score(x), x["label"]))

lines = [
    "# LEARNING REPORT", "",
    "Generated from prospective and benchmark search runs. Retrospective anecdotes are excluded from yield denominators.", "",
    f"- Measured runs: **{len(runs)}**",
    f"- Search-bearing runs: **{sum(1 for r in runs if (r.get('candidate_count') or 0) > 0 or (r.get('deep_inspected') or 0) > 0)}**",
    f"- Structured outcomes: **{len(outs)}**",
    f"- Outcome-lag window: **{OUTCOME_LAG_DAYS} days**; recent runs are not counted as outcome failures.",
    "- Outcome credit is conserved: each outcome contributes at most 1.00 total credit across all origin search runs.", "",
    "## Strategy performance", "",
    "| Strategy | Runs | Inspected | Retained precision | MASTER yield | New-capability run rate | Experiment run rate | Outcome credit | Outcome conversion* | Evidence |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
]

for x in strategy_rows:
    outcome_conv = fmt_rate(x["eligible_with_outcome"], x["eligible_runs"])
    lines.append(
        f"| {x['label']} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'], x['inspected'])} | "
        f"{fmt_rate(x['promoted'], x['inspected'])} | {fmt_rate(x['novel_runs'], x['runs'])} | "
        f"{fmt_rate(x['experiment_runs'], x['runs'])} | {x['outcome_credit']:.2f} | {outcome_conv} | "
        f"{'sufficient' if x['sufficient'] else 'insufficient'} |"
    )

if not strategy_rows:
    lines.append("| — | 0 | 0 | — | — | — | — | 0.00 | — | insufficient |")

lines += [
    "", "*Outcome conversion only uses runs old enough to clear the lag window.", "",
    "## Canonical query-family performance", "",
    "| Query family | Representative label | Runs | Inspected | Retained precision | MASTER yield | Outcome credit | Evidence |",
    "|---|---|---:|---:|---:|---:|---:|---|",
]

for x in query_rows:
    labels = query_labels.get(x["label"])
    representative = labels.most_common(1)[0][0] if labels else x["label"]
    if len(representative) > 90:
        representative = representative[:87] + "..."
    lines.append(
        f"| {x['label']} | {representative} | {x['runs']} | {x['inspected']} | "
        f"{fmt_rate(x['retained'], x['inspected'])} | {fmt_rate(x['promoted'], x['inspected'])} | "
        f"{x['outcome_credit']:.2f} | {'sufficient' if x['sufficient'] else 'insufficient'} |"
    )

if not query_rows:
    lines.append("| — | — | 0 | 0 | — | — | 0.00 | insufficient |")

efficiency_rows = [x for x in strategy_rows if x["timed_runs"] or x["tool_runs"]]
lines += [
    "", "## Research-efficiency instrumentation", "",
    "Efficiency is calculated only from runs that explicitly recorded effort. Missing effort is not imputed.", "",
    "| Strategy | Timed runs | Hours | Inspected/hour | Retained/hour | Tool-metered runs | Inspected/100 calls |",
    "|---|---:|---:|---:|---:|---:|---:|",
]

for x in efficiency_rows:
    hours = x["timed_minutes"] / 60 if x["timed_minutes"] else 0
    inspected_per_hour = x["timed_inspected"] / hours if hours else None
    retained_per_hour = x["timed_retained"] / hours if hours else None
    inspected_per_100 = (100 * x["call_inspected"] / x["tool_calls"]) if x["tool_calls"] else None
    lines.append(
        f"| {x['label']} | {x['timed_runs']} | {hours:.2f} | {fmt_float(inspected_per_hour)} | "
        f"{fmt_float(retained_per_hour)} | {x['tool_runs']} | {fmt_float(inspected_per_100)} |"
    )

if not efficiency_rows:
    lines.append("| — | 0 | 0.00 | — | — | 0 | — |")

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
    "- Multi-run outcomes use explicit credit weights when provided and equal-split fallback otherwise.",
    "- An internal engineering or validation run with zero candidates can strengthen a capability or experiment, but it does not enter candidate-yield denominators.",
    "- Failed and partial outcomes remain training data.", "",
    "## Realized value traced through the loop", "",
    "- Revenue: **$" + format(revenue, ",.0f") + "**",
    "- Customer value: **$" + format(customer_value, ",.0f") + "**",
    f"- Observed engineering compression: **{days_low:g}–{days_high:g} engineer-days**", "",
]

(INTEL / "LEARNING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(INTEL / "LEARNING_REPORT.md")
