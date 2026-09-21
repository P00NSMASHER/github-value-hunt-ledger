#!/usr/bin/env python3
import json, math
from collections import defaultdict
from datetime import datetime
from ti_common import INTEL, load_jsonl, normalize_run_time, slug, is_discovery_run

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
discovery_runs = [r for r in runs if is_discovery_run(r)]
outs = load_jsonl("outcomes.jsonl")
strategies = {x["strategy_id"]: x for x in load_jsonl("search_strategies.jsonl")}
aliases = json.loads((INTEL / "strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL / "strategy_aliases.json").exists() else {}
query_aliases = json.loads((INTEL / "query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL / "query_family_aliases.json").exists() else {}
qf_rows = {x["query_family_id"]: x for x in load_jsonl("query_families.jsonl")}
attr = json.loads((INTEL / "attribution_metrics.json").read_text(encoding="utf-8")) if (INTEL / "attribution_metrics.json").exists() else {}
attr_strategy = {x["id"]: x for x in attr.get("by_strategy", [])}
attr_query = {x["id"]: x for x in attr.get("by_query_family", [])}

def canonical_strategy(sid):
    s = strategies.get(sid)
    if s and s.get("parent_strategy_id"):
        return s["parent_strategy_id"]
    return aliases.get(sid, sid)

def qfid(run):
    raw = "QF:" + (slug(run.get("query_family") or "unknown")[:120] or "unknown")
    return query_aliases.get(raw, raw)

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
    query_groups[qfid(r)].append(r)

def outcome_eligible(run):
    if not reference_day:
        return False
    day = parse_day(normalize_run_time(run))
    return bool(day and (reference_day - day).days >= OUTCOME_LAG_DAYS)

def summarize(label, rs, attribution):
    all_activity = rs
    rs = [r for r in rs if is_discovery_run(r)]
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs = sum(1 for r in rs if r.get("new_capability_ids"))
    experiment_runs = sum(1 for r in rs if r.get("experiment_ids"))
    search_bearing_runs = sum(1 for r in rs if (r.get("candidate_count") or 0) > 0 or (r.get("deep_inspected") or 0) > 0)

    outcome_objects = {}
    for r in all_activity:
        for o in out_by_run.get(r["search_run_id"], []):
            outcome_objects[o.get("outcome_id")] = o
    valid = [o for o in outcome_objects.values() if o.get("result") != "INVALID"]
    eligible = [r for r in rs if outcome_eligible(r)]
    eligible_with_outcome = sum(1 for r in eligible if any(o.get("result") != "INVALID" for o in out_by_run.get(r["search_run_id"], [])))
    a = attribution or {}

    return {
        "label": label, "runs": len(rs), "search_bearing_runs": search_bearing_runs,
        "inspected": inspected, "retained": retained, "promoted": promoted,
        "novel_runs": novel_runs, "experiment_runs": experiment_runs,
        "assisted_outcomes": len(valid),
        "eligible_runs": len(eligible), "eligible_with_outcome": eligible_with_outcome,
        "fractional_outcome_equivalents": a.get("fractional_outcome_equivalents", 0),
        "revenue_credit": a.get("revenue_usd_credit", 0),
        "customer_value_credit": a.get("customer_value_usd_credit", 0),
        "sufficient": len(rs) >= 5 and inspected >= 20
    }

strategy_rows = [summarize(k, v, attr_strategy.get(k)) for k, v in groups.items()]
query_rows = [summarize(k, v, attr_query.get(k)) for k, v in query_groups.items()]

def rank_score(row):
    if not row["sufficient"]:
        return -1
    i = max(row["inspected"], 1)
    rn = max(row["runs"], 1)
    return (
        3.0 * row["promoted"] / i +
        2.0 * row["novel_runs"] / rn +
        1.5 * row["experiment_runs"] / rn +
        2.0 * row["fractional_outcome_equivalents"] / rn +
        min(row["revenue_credit"] / 10000, 2.0)
    )

strategy_rows.sort(key=lambda x: (-rank_score(x), x["label"]))
query_rows.sort(key=lambda x: (-rank_score(x), x["label"]))

lines = [
    "# LEARNING REPORT", "",
    "Generated from prospective and benchmark runs. Discovery denominators exclude explicit non-search or unclassified actions; historical records without an action retain their observational status. Retrospective anecdotes are excluded. Outcome attribution still includes all activity and uses fractional equal-touch credit.", "",
    f"- Measured discovery runs: **{len(discovery_runs)}**",
    f"- Other measured actions excluded from discovery denominators: **{len(runs) - len(discovery_runs)}**",
    f"- Legacy discovery runs without action classification: **{sum('work_action' not in r for r in discovery_runs)}**",
    f"- Search-bearing runs: **{sum(1 for r in discovery_runs if (r.get('candidate_count') or 0) > 0 or (r.get('deep_inspected') or 0) > 0)}**",
    f"- Structured outcomes: **{len(outs)}**",
    f"- Outcome-lag window: **{OUTCOME_LAG_DAYS} days**; recent runs are not counted as outcome failures.", "",
    "## Strategy performance", "",
    "| Strategy | Runs | Inspected | Retained precision | MASTER yield | New-capability run rate | Experiment run rate | Assisted outcomes | Outcome eq. | Revenue credit | Evidence |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
]
for x in strategy_rows:
    lines.append(
        f"| {x['label']} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'],x['inspected'])} | "
        f"{fmt_rate(x['promoted'],x['inspected'])} | {fmt_rate(x['novel_runs'],x['runs'])} | "
        f"{fmt_rate(x['experiment_runs'],x['runs'])} | {x['assisted_outcomes']} | "
        f"{x['fractional_outcome_equivalents']:.2f} | ${x['revenue_credit']:,.0f} | "
        f"{'sufficient' if x['sufficient'] else 'insufficient'} |"
    )
if not strategy_rows:
    lines.append("| — | 0 | 0 | — | — | — | — | 0 | 0.00 | $0 | insufficient |")

lines += ["", "## Query-family performance", "",
          "| Query family | Runs | Inspected | Retained precision | MASTER yield | Capability run rate | Assisted outcomes | Outcome eq. | Evidence |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
for x in query_rows:
    label = qf_rows.get(x["label"], {}).get("label", x["label"])
    lines.append(
        f"| {x['label']} — {label} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'],x['inspected'])} | "
        f"{fmt_rate(x['promoted'],x['inspected'])} | {fmt_rate(x['novel_runs'],x['runs'])} | "
        f"{x['assisted_outcomes']} | {x['fractional_outcome_equivalents']:.2f} | "
        f"{'sufficient' if x['sufficient'] else 'insufficient'} |"
    )
if not query_rows:
    lines.append("| — | 0 | 0 | — | — | — | 0 | 0.00 | insufficient |")

valid = [o for o in outs if o.get("result") != "INVALID"]
revenue = sum((o.get("revenue_usd") or 0) for o in valid)
customer_value = sum((o.get("customer_value_usd") or 0) for o in valid)
days_low = sum((o.get("engineering_days_saved_low") or 0) for o in valid)
days_high = sum((o.get("engineering_days_saved_high") or 0) for o in valid)

lines += ["", "## Policy", "",
          "- Do not claim a strategy is superior until it has at least 5 measured runs and 20 deep inspections.",
          "- Keep explicit exploration; low-frequency strange discoveries must not be optimized away by short-run precision.",
          "- Realized outcomes outrank predicted repository scores.",
          "- Fractional outcome/value credit is accounting attribution, not causal proof.",
          "- Failed and partial outcomes remain training data.",
          "- Use MEASUREMENT_PLAN.md to reduce evidence debt before making stronger allocation claims.", "",
          "## Realized value traced through the loop", "",
          "- Revenue: **$" + format(revenue, ",.0f") + "**",
          "- Customer value: **$" + format(customer_value, ",.0f") + "**",
          f"- Observed engineering compression: **{days_low:g}–{days_high:g} engineer-days**", ""]
(INTEL / "LEARNING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(INTEL / "LEARNING_REPORT.md")
