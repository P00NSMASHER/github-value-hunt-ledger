#!/usr/bin/env python3
import json, math
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INTEL=ROOT/"intelligence"

def load(name):
    p=INTEL/name
    if not p.exists(): return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

runs=load("search_runs.jsonl")
outs=load("outcomes.jsonl")
strats={x["strategy_id"]:x for x in load("search_strategies.jsonl")}

def wilson(k,n,z=1.96):
    if not n: return None
    p=k/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return max(0,center-half),min(1,center+half)

out_by_run=defaultdict(list)
for o in outs:
    for rid in o.get("origin_search_ids",[]): out_by_run[rid].append(o)

groups=defaultdict(lambda:{"runs":[]})
for r in runs:
    if r.get("measurement_quality") not in {"prospective","benchmark"}: continue
    if r.get("deep_inspected") is None: continue
    groups[("strategy",r["strategy_id"])]["runs"].append(r)
    groups[("query",r.get("query_family","unknown"))]["runs"].append(r)

def fmt_rate(k,n):
    if not n: return "—"
    lohi=wilson(k,n)
    return f"{k/n:.1%} [{lohi[0]:.1%}, {lohi[1]:.1%}]"

def summarize(label,rs):
    n_runs=len(rs)
    candidates=sum((r.get("candidate_count") or 0) for r in rs)
    inspected=sum((r.get("deep_inspected") or 0) for r in rs)
    retained=sum((r.get("retained_count") or 0) for r in rs)
    promoted=sum((r.get("master_promoted_count") or 0) for r in rs)
    new_caps=sum(len(r.get("new_capability_ids") or []) for r in rs)
    exp_runs=sum(1 for r in rs if r.get("experiment_ids"))
    outcome_objs=[]
    seen=set()
    for r in rs:
        for o in out_by_run.get(r["search_run_id"],[]):
            if o["outcome_id"] not in seen: outcome_objs.append(o); seen.add(o["outcome_id"])
    valid_out=[o for o in outcome_objs if o.get("result")!="INVALID"]
    passed=sum(1 for o in valid_out if o.get("result")=="PASSED")
    revenue=sum((o.get("revenue_usd") or 0) for o in valid_out)
    value=sum((o.get("customer_value_usd") or 0) for o in valid_out)
    days_low=sum((o.get("engineering_days_saved_low") or 0) for o in valid_out)
    days_high=sum((o.get("engineering_days_saved_high") or 0) for o in valid_out)
    evidence="sufficient" if n_runs>=5 and inspected>=20 else "insufficient"
    return {
      "label":label,"runs":n_runs,"candidates":candidates,"inspected":inspected,
      "retained":retained,"promoted":promoted,"new_caps":new_caps,"exp_runs":exp_runs,
      "outcomes":len(valid_out),"passed":passed,"revenue":revenue,"value":value,
      "days_low":days_low,"days_high":days_high,"evidence":evidence
    }

strategy_rows=[]
query_rows=[]
for (kind,label),g in groups.items():
    s=summarize(label,g["runs"])
    (strategy_rows if kind=="strategy" else query_rows).append(s)

def score(row):
    if row["evidence"]!="sufficient": return -1
    i=max(row["inspected"],1)
    return (row["promoted"]/i)*3 + (row["new_caps"]/i)*2 + (row["outcomes"]/max(row["runs"],1))*2 + min(row["revenue"]/10000,2)

strategy_rows.sort(key=score,reverse=True)
query_rows.sort(key=score,reverse=True)

lines=[
"# LEARNING REPORT","",
"Generated from prospective/benchmark search runs and explicitly linked outcomes. Retrospective anecdotes are excluded from yield denominators.","",
f"- Measured search runs: **{sum(x['runs'] for x in strategy_rows)}**",
f"- Structured outcomes: **{len(outs)}**",
"",
"## Strategy performance","",
"| Strategy | Runs | Inspected | Retained precision | MASTER yield | Capability novelty | Experiment conversion | Outcomes | Realized revenue | Evidence |",
"|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
]
for x in strategy_rows:
    lines.append(f"| {x['label']} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'],x['inspected'])} | {fmt_rate(x['promoted'],x['inspected'])} | {fmt_rate(x['new_caps'],x['inspected'])} | {fmt_rate(x['exp_runs'],x['runs'])} | {x['outcomes']} | ${x['revenue']:,.0f} | {x['evidence']} |")
if not strategy_rows: lines.append("| — | 0 | 0 | — | — | — | — | 0 | $0 | insufficient |")

lines += ["","## Query-family performance","",
"| Query family | Runs | Inspected | Retained precision | MASTER yield | Capability novelty | Outcomes | Evidence |",
"|---|---:|---:|---:|---:|---:|---:|---|"]
for x in query_rows:
    lines.append(f"| {x['label']} | {x['runs']} | {x['inspected']} | {fmt_rate(x['retained'],x['inspected'])} | {fmt_rate(x['promoted'],x['inspected'])} | {fmt_rate(x['new_caps'],x['inspected'])} | {x['outcomes']} | {x['evidence']} |")
if not query_rows: lines.append("| — | 0 | 0 | — | — | — | 0 | insufficient |")

lines += ["","## Policy","",
"- Do not automatically expand or retire a strategy until evidence is sufficient (>=5 measured runs and >=20 deep inspections).",
"- Prefer strategies that create independently verified capabilities or useful experiments, not merely high retained counts.",
"- Realized outcomes outrank predicted repository scores.",
"- Keep an exploration budget for high-novelty strategies even when short-run precision is low.",
"- A failed outcome is training data; it should reduce confidence in the assumptions it tested, not be deleted.",
"",
"## Realized value traced through the loop",""]
valid=[o for o in outs if o.get("result")!="INVALID"]
rev=sum((o.get("revenue_usd") or 0) for o in valid)
val=sum((o.get("customer_value_usd") or 0) for o in valid)
lo=sum((o.get("engineering_days_saved_low") or 0) for o in valid)
hi=sum((o.get("engineering_days_saved_high") or 0) for o in valid)
lines += [f"- Revenue: **${rev:,.0f}**",f"- Customer value: **${val:,.0f}**",f"- Observed engineering compression: **{lo:g}–{hi:g} engineer-days**",""]

out="\n".join(lines)
path=INTEL/"LEARNING_REPORT.md"
path.write_text(out,encoding="utf-8")
print(path)
