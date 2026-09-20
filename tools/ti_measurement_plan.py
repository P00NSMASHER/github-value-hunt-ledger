#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL,load_jsonl

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
strategies=[s for s in load_jsonl("search_strategies.jsonl") if s.get("status")=="active"]
policy=json.loads((INTEL/"search_policy.json").read_text(encoding="utf-8")) if (INTEL/"search_policy.json").exists() else {}
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
current=json.loads((INTEL/"current_strategy_versions.json").read_text(encoding="utf-8")) if (INTEL/"current_strategy_versions.json").exists() else {}

groups=defaultdict(list); historical=defaultdict(int)
for r in runs:
    sid=r.get("strategy_id"); historical[sid]+=1
    vid=r.get("strategy_version_id") or (bindings.get(r["search_run_id"]) or {}).get("strategy_version_id")
    if current.get(sid)==vid:groups[sid].append(r)

allocation={x["strategy_id"]:x.get("allocation",0) for x in policy.get("strategy_allocation",[])}
rows=[]
for s in strategies:
    sid=s["strategy_id"]; rs=groups.get(sid,[]); inspected=sum((r.get("deep_inspected") or 0) for r in rs)
    runs_needed=max(0,5-len(rs)); inspections_needed=max(0,20-inspected)
    missing_queries=sum(1 for r in rs if not r.get("queries")); missing_surfaces=sum(1 for r in rs if not r.get("search_surfaces"))
    missing_disp=sum(1 for r in rs if (r.get("candidate_count") or 0)>0 and not r.get("candidate_dispositions"))
    rows.append({
      "strategy_id":sid,"strategy_version_id":current.get(sid),"name":s.get("name"),
      "current_version_runs":len(rs),"historical_runs":historical.get(sid,0),"deep_inspected":inspected,
      "runs_needed":runs_needed,"inspections_needed":inspections_needed,
      "measurement_debt":runs_needed/5+inspections_needed/20,
      "instrumentation_debt":(missing_queries+missing_surfaces+missing_disp)/max(1,3*len(rs)),
      "policy_allocation":allocation.get(sid,0),"sufficient_evidence":runs_needed==0 and inspections_needed==0
    })
rows.sort(key=lambda x:(-x["measurement_debt"],-x["policy_allocation"],x["strategy_id"]))
plan={"thresholds":{"min_runs":5,"min_deep_inspections":20},"evidence_scope":"current_strategy_version_only",
      "active_strategies":len(rows),"sufficient_strategies":sum(1 for x in rows if x["sufficient_evidence"]),"rows":rows}
(INTEL/"measurement_plan.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
lines=["# MEASUREMENT DEBT PLAN","",
 "V5 measurement debt is calculated on the **current strategy version only**. A new procedure version must earn its own 5-run/20-inspection evidence base.","",
 f"- Active strategies: **{len(rows)}**",f"- Current versions with sufficient evidence: **{plan['sufficient_strategies']}**",
 "- Sufficiency threshold: **5 measured runs + 20 deep inspections per current version**.","",
 "| Strategy | Current version | Current runs | Historical runs | Inspected | More runs | More inspections | Allocation |",
 "|---|---|---:|---:|---:|---:|---:|---:|"]
for x in rows:
    lines.append(f"| {x['strategy_id']} | {x['strategy_version_id'] or 'unresolved'} | {x['current_version_runs']} | {x['historical_runs']} | {x['deep_inspected']} | {x['runs_needed']} | {x['inspections_needed']} | {x['policy_allocation']:.1%} |")
lines += ["","## Operating rule","",
 "- Do not let old-version evidence satisfy a changed procedure's measurement debt.",
 "- Use the matched measurement queue to reduce debt on frozen tasks.",
 "- Bounded no-find runs are valid evidence; do not manufacture deep inspections to hit quotas.",
 "- Real outcomes remain more important than benchmark sufficiency.",""]
(INTEL/"MEASUREMENT_PLAN.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"active":len(rows),"sufficient":plan["sufficient_strategies"]}))
