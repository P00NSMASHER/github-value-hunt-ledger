#!/usr/bin/env python3
import json,math
from collections import Counter
from ti_common import INTEL,load_jsonl,normalize_run_time,slug

runs=load_jsonl("search_runs.jsonl"); enriched=load_jsonl("search_runs_enriched.jsonl") if (INTEL/"search_runs_enriched.jsonl").exists() else []
outs=load_jsonl("outcomes.jsonl"); caps=load_jsonl("capabilities.jsonl")
legacy=json.loads((INTEL/"legacy_run_allowlist.json").read_text(encoding="utf-8")); legacy_ids=set(legacy.get("pre_v5_run_ids",[]))
triage=json.loads((INTEL/"triage_policy.json").read_text(encoding="utf-8"))
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
recommended=[
 ("time",lambda r:bool(normalize_run_time(r))),("hunter",lambda r:bool(r.get("hunter_role") or r.get("hunter"))),
 ("strategy_id",lambda r:bool(r.get("strategy_id"))),("query_family",lambda r:bool(r.get("query_family"))),
 ("measurement_quality",lambda r:bool(r.get("measurement_quality"))),("candidate_count",lambda r:r.get("candidate_count") is not None),
 ("deep_inspected",lambda r:r.get("deep_inspected") is not None),("retained_count",lambda r:r.get("retained_count") is not None),
 ("master_promoted_count",lambda r:r.get("master_promoted_count") is not None),("search_surfaces",lambda r:bool(r.get("search_surfaces"))),
 ("queries",lambda r:bool(r.get("queries"))),("candidate_dispositions",lambda r:r.get("candidate_count",0)==0 or bool(r.get("candidate_dispositions")))
]
missing=Counter();scores=[];issues=[]
for r in runs:
    have=0
    for name,fn in recommended:
        if fn(r):have+=1
        else:missing[name]+=1
    scores.append(have/len(recommended))
    c,d,k,m=r.get("candidate_count"),r.get("deep_inspected"),r.get("retained_count"),r.get("master_promoted_count")
    if c is not None and d is not None and d>c:issues.append((r["search_run_id"],"deep_gt_candidates"))
    if d is not None and k is not None and k>d:issues.append((r["search_run_id"],"retained_gt_deep"))
    if k is not None and m is not None and m>k:issues.append((r["search_run_id"],"master_gt_retained"))
new=[r for r in runs if r["search_run_id"] not in legacy_ids]
v5=[r for r in new if (r.get("schema_version") or 0)>=5]
v5_complete=sum(1 for r in v5 if r.get("query_family_id") and r.get("search_objective_id") and r.get("queries") and r.get("search_surfaces"))
timed=sum(1 for r in runs if isinstance(r.get("elapsed_minutes"),(int,float)) and r.get("elapsed_minutes",0)>0)
holdout_eligible=0;holdout_compliant=0
for r in v5:
    rej=r.get("triage_rejected_count") or 0
    if rej>=triage["min_triage_rejects_for_required_holdout"]:
        holdout_eligible+=1
        required=max(triage["min_holdout_sample_count"],math.ceil(rej*triage["holdout_target_rate"]))
        if (r.get("holdout_sample_count") or 0)>=required:holdout_compliant+=1
metrics={
 "search_runs":len(runs),"legacy_runs":len([r for r in runs if r["search_run_id"] in legacy_ids]),
 "post_v5_runs":len(new),"v5_runs":len(v5),"v5_core_complete":v5_complete,
 "strategy_version_binding_coverage":sum(1 for r in runs if r["search_run_id"] in bindings),
 "enriched_runs":len(enriched),"elapsed_time_coverage":timed,
 "holdout_eligible_v5_runs":holdout_eligible,"holdout_compliant_v5_runs":holdout_compliant,
 "average_core_completeness":sum(scores)/len(scores) if scores else 0,"issues":len(issues)
}
(INTEL/"quality_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
lines=["# DATA QUALITY REPORT","",
 "V5 creates a hard historical boundary: the 12 allowlisted runs remain legacy evidence; every new run must satisfy the V5 contract.","",
 f"- Search runs: **{len(runs)}**",f"- Legacy allowlisted runs: **{metrics['legacy_runs']}**",
 f"- Post-V5 run IDs: **{metrics['post_v5_runs']}**",f"- V5-native runs: **{metrics['v5_runs']}**",
 f"- V5 core instrumentation complete: **{v5_complete}/{len(v5)}**",f"- Strategy-version bindings: **{metrics['strategy_version_binding_coverage']}/{len(runs)}**",
 f"- Enriched immutable run views: **{len(enriched)}**",f"- Runs with elapsed-time telemetry: **{timed}/{len(runs)}**",
 f"- V5 runs requiring triage holdout: **{holdout_eligible}** (compliant: **{holdout_compliant}**)","",
 "## Missing legacy/core fields","",
 "| Field | Runs missing |","|---|---:|"]
for n,c in missing.most_common():lines.append(f"| {n} | {c} |")
if not missing:lines.append("| — | 0 |")
lines += ["","## Learning bottlenecks","",
 "- Execute the matched measurement queue; observational strategy percentages are still underpowered.",
 "- Collect real elapsed-time/tool-call telemetry before optimizing research efficiency.",
 "- Begin triage holdout audits before converting common rejection reasons into stronger prefilters.",
 "- Reduce revision debt for current strong/watch findings without inventing historical SHAs.",""]
(INTEL/"DATA_QUALITY_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps(metrics))
