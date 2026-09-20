#!/usr/bin/env python3
import json, re
from collections import defaultdict
from ti_common import ROOT, INTEL, load_jsonl

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
strategies=[s for s in load_jsonl("search_strategies.jsonl") if s.get("status")=="active"]
cfg=json.loads((INTEL/"strategy_evaluation_sets.json").read_text(encoding="utf-8"))
measurement=json.loads((INTEL/"measurement_plan.json").read_text(encoding="utf-8")) if (INTEL/"measurement_plan.json").exists() else {"rows":[]}
debt={x["strategy_id"]:x for x in measurement.get("rows",[])}

task_text=(ROOT/"benchmark"/"BENCHMARK_TASKS.md").read_text(encoding="utf-8")
task_names={}
for m in re.finditer(r"^(\d{2})\.\s+(.+)$",task_text,re.M):
    task_names[m.group(1)]=m.group(2).strip()

observed=defaultdict(set)
for r in runs:
    if r.get("measurement_quality")!="benchmark": continue
    for tid in r.get("benchmark_task_ids") or []:
        observed[r.get("strategy_id")].add(str(tid).zfill(2))

recommendations=[]
for s in strategies:
    sid=s["strategy_id"]
    d=debt.get(sid,{})
    if d.get("sufficient_evidence"): continue
    candidates=[]
    for ev in cfg.get("sets",[]):
        if sid not in ev.get("strategy_ids",[]): continue
        for tid in ev.get("task_ids",[]):
            tid=str(tid).zfill(2)
            if tid in observed[sid]: continue
            overlap=sum(1 for other in ev.get("strategy_ids",[]) if other!=sid and tid not in observed[other])
            candidates.append((overlap,ev["evaluation_set_id"],tid,ev))
    candidates.sort(key=lambda x:(-x[0],x[2],x[1]))
    if candidates:
        overlap,set_id,tid,ev=candidates[0]
        recommendations.append({
          "strategy_id":sid,
          "strategy_name":s.get("name"),
          "evaluation_set_id":set_id,
          "benchmark_task_id":tid,
          "task":task_names.get(tid),
          "comparison_group_id":f"CMP:{set_id.split(':',1)[-1]}:task-{tid}",
          "matched_strategy_ids":[x for x in ev.get("strategy_ids",[]) if tid not in observed[x]],
          "runs_needed":d.get("runs_needed"),
          "inspections_needed":d.get("inspections_needed"),
          "matched_overlap":overlap
        })

# Deduplicate into matched comparison groups.
groups={}
for r in recommendations:
    gid=r["comparison_group_id"]
    g=groups.setdefault(gid,{
      "comparison_group_id":gid,
      "evaluation_set_id":r["evaluation_set_id"],
      "benchmark_task_id":r["benchmark_task_id"],
      "task":r["task"],
      "strategy_ids":set()
    })
    g["strategy_ids"].update(r["matched_strategy_ids"])
group_rows=[]
for g in groups.values():
    g["strategy_ids"]=sorted(g["strategy_ids"])
    group_rows.append(g)
group_rows.sort(key=lambda x:(-len(x["strategy_ids"]),x["benchmark_task_id"],x["comparison_group_id"]))

plan={
  "schema_version":1,
  "protocol":"benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md",
  "gold_file_prohibited_pre_freeze":"benchmark/BENCHMARK_GOLD.md",
  "recommended_strategy_conditions":recommendations,
  "matched_comparison_groups":group_rows
}
(INTEL/"measurement_campaign.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")

lines=[
 "# MATCHED STRATEGY MEASUREMENT CAMPAIGN","",
 "This campaign reduces strategy-measurement debt using frozen benchmark tasks. It is deliberately separate from commercial opportunity search.","",
 f"- Active strategies needing more evidence: **{len(recommendations)}**",
 f"- Suggested matched comparison groups: **{len(group_rows)}**",
 "- Protocol: `benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md`",
 "- **Do not read `BENCHMARK_GOLD.md` before a result is frozen.**","",
 "## Highest-leverage matched groups","",
 "| Comparison group | Task | Strategies |",
 "|---|---|---|"
]
for g in group_rows[:20]:
    lines.append(f"| {g['comparison_group_id']} | {g['benchmark_task_id']} — {g['task'] or 'task text unavailable'} | {', '.join(g['strategy_ids'])} |")
if not group_rows: lines.append("| — | — | — |")
lines += ["","## Per-strategy next measurement","",
          "| Strategy | More runs needed | More inspections needed | Evaluation set | Suggested task | Comparison group |",
          "|---|---:|---:|---|---|---|"]
for r in recommendations:
    lines.append(f"| {r['strategy_id']} | {r['runs_needed'] if r['runs_needed'] is not None else '—'} | {r['inspections_needed'] if r['inspections_needed'] is not None else '—'} | {r['evaluation_set_id']} | {r['benchmark_task_id']} | {r['comparison_group_id']} |")
if not recommendations: lines.append("| — | 0 | 0 | — | — | — |")
lines += ["","## Why this is stronger than ordinary telemetry","",
          "- The same frozen task is assigned to multiple strategies, reducing domain/task-difficulty confounding.",
          "- Conditions should be run independently and frozen before sibling results are visible.",
          "- No-find and correct reject outcomes count; only returning a candidate is not success.",
          "- These comparisons estimate search-method performance. Real customer outcomes still decide long-run commercial allocation.",""]
(INTEL/"MEASUREMENT_CAMPAIGN.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"recommendations":len(recommendations),"groups":len(group_rows)}))
