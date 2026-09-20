#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl, slug

runs={r["search_run_id"]:r for r in load_jsonl("search_runs.jsonl")}
outs=[o for o in load_jsonl("outcomes.jsonl") if o.get("result")!="INVALID"]
strategies={s["strategy_id"]:s for s in load_jsonl("search_strategies.jsonl")}
strategy_aliases=json.loads((INTEL/"strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL/"strategy_aliases.json").exists() else {}
query_aliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
objective_map=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
surface_aliases=json.loads((INTEL/"surface_aliases.json").read_text(encoding="utf-8")) if (INTEL/"surface_aliases.json").exists() else {}

def canonical_strategy(sid):
    s=strategies.get(sid)
    if s and s.get("parent_strategy_id"): return s["parent_strategy_id"]
    return strategy_aliases.get(sid,sid)

def qfid(run):
    raw="QF:"+(slug(run.get("query_family") or "unknown")[:120] or "unknown")
    return query_aliases.get(raw,raw)

def objective(run):
    return run.get("search_objective_id") or objective_map.get(qfid(run)) or "OBJ:unclassified"

def surface_family(surface_id):
    if surface_id in surface_aliases: return surface_aliases[surface_id]
    s=surface_id.lower()
    if "code-search" in s or "code-signature" in s: return "SURFACE_FAMILY:github-code-search"
    if "repository-search" in s: return "SURFACE_FAMILY:github-repository-search"
    if "documentation" in s or ":official-" in s: return "SURFACE_FAMILY:first-party-docs"
    if any(x in s for x in ("history","archaeology","commit-issue","release")): return "SURFACE_FAMILY:github-history-archaeology"
    if any(x in s for x in ("source-tests","exact-head","schema-persistence","actions-license")): return "SURFACE_FAMILY:github-source-inspection"
    if any(x in s for x in ("adjacency","lineage-traversal","analogs","comparator","graph-search")): return "SURFACE_FAMILY:ecosystem-adjacency"
    if "private-ledger" in s: return "SURFACE_FAMILY:private-ledger"
    if any(x in s for x in ("synthetic","sqlite","local-validation","acceptance-corpus")): return "SURFACE_FAMILY:synthetic-local-validation"
    return "SURFACE_FAMILY:other"

def add(bucket,key,outcome,share):
    x=bucket.setdefault(key,{
      "assisted_outcomes":set(),"fractional_outcome_equivalents":0.0,"fractional_passed_equivalents":0.0,
      "revenue_usd_credit":0.0,"customer_value_usd_credit":0.0,
      "engineering_days_saved_low_credit":0.0,"engineering_days_saved_high_credit":0.0
    })
    x["assisted_outcomes"].add(outcome["outcome_id"]); x["fractional_outcome_equivalents"]+=share
    if outcome.get("result")=="PASSED": x["fractional_passed_equivalents"]+=share
    x["revenue_usd_credit"]+=(outcome.get("revenue_usd") or 0)*share
    x["customer_value_usd_credit"]+=(outcome.get("customer_value_usd") or 0)*share
    x["engineering_days_saved_low_credit"]+=(outcome.get("engineering_days_saved_low") or 0)*share
    x["engineering_days_saved_high_credit"]+=(outcome.get("engineering_days_saved_high") or 0)*share

by_strategy={}; by_query={}; by_objective={}; by_surface={}; by_surface_family={}; by_run={}
outcome_rows=[]
for o in outs:
    origins=[]; seen=set()
    for rid in o.get("origin_search_ids",[]):
        if rid in runs and rid not in seen: origins.append(rid); seen.add(rid)
    if not origins: continue
    run_share=1.0/len(origins)
    outcome_rows.append({"outcome_id":o["outcome_id"],"result":o.get("result"),"origin_count":len(origins),"credit_per_origin":run_share,"revenue_usd":o.get("revenue_usd"),"customer_value_usd":o.get("customer_value_usd")})
    for rid in origins:
        r=runs[rid]
        add(by_run,rid,o,run_share)
        add(by_strategy,canonical_strategy(r.get("strategy_id")),o,run_share)
        add(by_query,qfid(r),o,run_share)
        add(by_objective,objective(r),o,run_share)
        exact=sorted(set("SURFACE:"+slug(s) for s in (r.get("search_surfaces") or [])))
        if exact:
            exact_share=run_share/len(exact)
            for s in exact: add(by_surface,s,o,exact_share)
            families=sorted(set(surface_family(s) for s in exact))
            family_share=run_share/len(families)
            for f in families: add(by_surface_family,f,o,family_share)

def freeze(bucket):
    rows=[]
    for key,x in bucket.items():
        y=dict(x); y["id"]=key; y["assisted_outcome_count"]=len(y.pop("assisted_outcomes")); rows.append(y)
    return sorted(rows,key=lambda x:(-x["fractional_outcome_equivalents"],x["id"]))

metrics={
 "method":"equal_touch_across_unique_origin_runs; exact-surface and unique-surface-family credit split within each credited run",
 "causal_claim":False,
 "valid_outcomes":len(outs),
 "outcomes_with_attributable_origins":len(outcome_rows),
 "outcomes":outcome_rows,
 "by_run":freeze(by_run),"by_strategy":freeze(by_strategy),"by_query_family":freeze(by_query),
 "by_objective":freeze(by_objective),"by_surface":freeze(by_surface),"by_surface_family":freeze(by_surface_family),
 "totals":{
   "revenue_usd":sum((o.get("revenue_usd") or 0) for o in outs),
   "customer_value_usd":sum((o.get("customer_value_usd") or 0) for o in outs),
   "engineering_days_saved_low":sum((o.get("engineering_days_saved_low") or 0) for o in outs),
   "engineering_days_saved_high":sum((o.get("engineering_days_saved_high") or 0) for o in outs)
 }
}
(INTEL/"attribution_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
 "# OUTCOME ATTRIBUTION REPORT","",
 "This is an accounting attribution layer, **not a causal claim**. Multi-origin outcomes split value across unique origin runs; surface credit is then split across exact surfaces and independently across unique normalized surface families.","",
 f"- Valid outcomes: **{len(outs)}**",f"- Outcomes with attributable search origins: **{len(outcome_rows)}**","",
 "## Strategy attribution","",
 "| Strategy | Assisted outcomes | Fractional outcome eq. | Passed eq. | Revenue credit | Customer-value credit | Engineering-days credit |",
 "|---|---:|---:|---:|---:|---:|---|"
]
for x in metrics["by_strategy"]:
    lines.append(f"| {x['id']} | {x['assisted_outcome_count']} | {x['fractional_outcome_equivalents']:.2f} | {x['fractional_passed_equivalents']:.2f} | ${x['revenue_usd_credit']:,.0f} | ${x['customer_value_usd_credit']:,.0f} | {x['engineering_days_saved_low_credit']:.1f}–{x['engineering_days_saved_high_credit']:.1f} |")
if not metrics["by_strategy"]: lines.append("| — | 0 | 0.00 | 0.00 | $0 | $0 | 0–0 |")
lines += ["","## Objective attribution","",
          "| Objective | Assisted outcomes | Outcome eq. | Revenue credit |","|---|---:|---:|---:|"]
for x in metrics["by_objective"]:
    lines.append(f"| {x['id']} | {x['assisted_outcome_count']} | {x['fractional_outcome_equivalents']:.2f} | ${x['revenue_usd_credit']:,.0f} |")
if not metrics["by_objective"]: lines.append("| — | 0 | 0.00 | $0 |")
lines += ["","## Attribution guardrails","",
          "- Equal-touch credit prevents the same realized dollars from being counted in full for every origin run.",
          "- Strategy/query/objective/surface credits are accounting views over the same outcome; do not sum across dimensions.",
          "- Assisted-outcome counts and fractional credits do not prove causal contribution.",
          "- Matched benchmark comparisons are the preferred evidence for search-method differences; real outcomes remain the highest-value evidence.",""]
(INTEL/"ATTRIBUTION_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"valid_outcomes":len(outs),"attributable":len(outcome_rows),"objectives":len(metrics["by_objective"]),"surface_families":len(metrics["by_surface_family"])}))
