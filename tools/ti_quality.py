#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl, normalize_run_time, slug

runs=load_jsonl("search_runs.jsonl"); outs=load_jsonl("outcomes.jsonl"); caps=load_jsonl("capabilities.jsonl")
strategies={x["strategy_id"]:x for x in load_jsonl("search_strategies.jsonl")}
qaliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
qobj=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
objectives={x["search_objective_id"] for x in json.loads((INTEL/"search_objectives.json").read_text(encoding="utf-8")).get("objectives",[])} if (INTEL/"search_objectives.json").exists() else set()
reason_aliases=json.loads((INTEL/"reason_aliases.json").read_text(encoding="utf-8")) if (INTEL/"reason_aliases.json").exists() else {}

recommended=[
 ("time",lambda r:bool(normalize_run_time(r))),("hunter",lambda r:bool(r.get("hunter_role") or r.get("hunter"))),
 ("strategy_id",lambda r:bool(r.get("strategy_id"))),("query_family",lambda r:bool(r.get("query_family"))),
 ("measurement_quality",lambda r:bool(r.get("measurement_quality"))),("candidate_count",lambda r:r.get("candidate_count") is not None),
 ("deep_inspected",lambda r:r.get("deep_inspected") is not None),("retained_count",lambda r:r.get("retained_count") is not None),
 ("master_promoted_count",lambda r:r.get("master_promoted_count") is not None),("search_surfaces",lambda r:bool(r.get("search_surfaces"))),
 ("queries",lambda r:bool(r.get("queries"))),("candidate_dispositions",lambda r:r.get("candidate_count",0)==0 or bool(r.get("candidate_dispositions"))),
 ("durable_evidence",lambda r:bool(r.get("durable_evidence_path") or r.get("notes")))
]

def qfid(r):
    raw="QF:"+(slug(r.get("query_family") or "unknown")[:120] or "unknown")
    return qaliases.get(raw,raw)

missing=Counter(); scores=[]; issues=[]; v4=[]; controlled=0; mapped_objective=0
for r in runs:
    have=0
    for name,fn in recommended:
        if fn(r): have+=1
        else: missing[name]+=1
    scores.append(have/len(recommended))
    sid=r.get("strategy_id"); strategy=strategies.get(sid)
    if not strategy: issues.append((r.get("search_run_id"),"unknown_strategy",sid))
    elif strategy.get("status")=="unregistered_observed": issues.append((r.get("search_run_id"),"unregistered_strategy_variant",sid))
    c,d,k,m=r.get("candidate_count"),r.get("deep_inspected"),r.get("retained_count"),r.get("master_promoted_count")
    if c is not None and d is not None and d>c: issues.append((r.get("search_run_id"),"deep_inspected_gt_candidates",f"{d}>{c}"))
    if d is not None and k is not None and k>d: issues.append((r.get("search_run_id"),"retained_gt_inspected",f"{k}>{d}"))
    if k is not None and m is not None and m>k: issues.append((r.get("search_run_id"),"master_gt_retained",f"{m}>{k}"))
    if r.get("search_objective_id") in objectives or qobj.get(qfid(r)) in objectives: mapped_objective+=1
    for disp in r.get("candidate_dispositions") or []:
        if disp.get("reason_code_standard") or disp.get("reason_code") in reason_aliases: controlled+=1
    if (r.get("schema_version") or 0)>=4:
        v4.append(r)

cap_missing_test=[c["capability_id"] for c in caps if not c.get("next_falsifiable_test")]
avg=sum(scores)/len(scores) if scores else 0
v4_complete=sum(1 for r in v4 if r.get("query_family_id") and r.get("search_objective_id") and r.get("queries") and r.get("search_surfaces"))
metrics={
 "search_runs":len(runs),"outcomes":len(outs),"average_run_completeness":avg,
 "runs_below_70pct_completeness":sum(1 for x in scores if x<.70),"issue_count":len(issues),
 "unregistered_strategy_runs":sum(1 for _,kind,_ in issues if kind=="unregistered_strategy_variant"),
 "capabilities_missing_next_test":len(cap_missing_test),
 "v4_runs":len(v4),"v4_core_instrumentation_complete":v4_complete,
 "objective_mapped_runs":mapped_objective,
 "candidate_dispositions_with_direct_or_alias_controlled_reason":controlled
}
(INTEL/"quality_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
 "# DATA QUALITY REPORT","",
 "This report measures whether the learning loop has enough structured evidence to support empirical search-policy updates.","",
 f"- Search runs: **{len(runs)}**",f"- Structured outcomes: **{len(outs)}**",
 f"- Mean legacy/core run completeness: **{avg:.1%}**",f"- Runs below 70% completeness: **{metrics['runs_below_70pct_completeness']}**",
 f"- Structural issues detected: **{len(issues)}**",f"- Capabilities without an explicit next falsifiable test: **{len(cap_missing_test)}**",
 f"- V4 runs: **{len(v4)}** (core V4 instrumentation complete: **{v4_complete}**)",
 f"- Runs mapped to a controlled search objective (explicit or reviewed legacy map): **{mapped_objective}/{len(runs)}**",
 f"- Candidate dispositions normalized to controlled reasons (direct or reviewed alias): **{controlled}**","",
 "## Missing recommended legacy/core fields","",
 "| Field | Runs missing |","|---|---:|"
]
for name,count in missing.most_common(): lines.append(f"| {name} | {count} |")
if not missing: lines.append("| — | 0 |")
lines += ["","## Structural issues",""]
if issues:
    for rid,kind,detail in issues[:50]: lines.append(f"- {rid} — **{kind}**: {detail}")
else: lines.append("- None.")
lines += ["","## Learning bottlenecks","",
          "- Strategy evidence remains below the 5-run/20-inspection comparison threshold; use MEASUREMENT_CAMPAIGN.md rather than over-reading observational percentages.",
          "- Query-family wording remains sparse; objective aggregation is the stable cross-domain layer.",
          "- Exact surface labels are normalized into families, but matched comparisons are still required for causal surface claims.",
          "- Revision debt and MASTER catalog provenance debt are tracked separately in REVISION_DEBT_REPORT.md."]
if avg<.85: lines.append("- Improve literal queries, search surfaces and candidate dispositions before expanding adaptive exploitation.")
if avg>=.85 and outs: lines.append("- Core instrumentation is strong enough for cautious, exploration-preserving allocation.")
(INTEL/"DATA_QUALITY_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(json.dumps(metrics))
