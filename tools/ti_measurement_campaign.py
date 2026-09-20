#!/usr/bin/env python3
import json,re
from collections import defaultdict
from ti_common import ROOT,INTEL,load_jsonl

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
strategies=[s for s in load_jsonl("search_strategies.jsonl") if s.get("status")=="active"]
cfg=json.loads((INTEL/"strategy_evaluation_sets.json").read_text(encoding="utf-8"))
measurement=json.loads((INTEL/"measurement_plan.json").read_text(encoding="utf-8")) if (INTEL/"measurement_plan.json").exists() else {"rows":[]}
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
current=json.loads((INTEL/"current_strategy_versions.json").read_text(encoding="utf-8")) if (INTEL/"current_strategy_versions.json").exists() else {}
debt={x["strategy_id"]:x for x in measurement.get("rows",[])}

task_text=(ROOT/"benchmark"/"BENCHMARK_TASKS.md").read_text(encoding="utf-8")
task_names={m.group(1):m.group(2).strip() for m in re.finditer(r"^(\d{2})\.\s+(.+)$",task_text,re.M)}

observed=defaultdict(set)
for r in runs:
    if r.get("measurement_quality")!="benchmark": continue
    sid=r.get("strategy_id")
    vid=r.get("strategy_version_id") or (bindings.get(r["search_run_id"]) or {}).get("strategy_version_id")
    if not sid or not vid or current.get(sid)!=vid: continue
    for tid in r.get("benchmark_task_ids") or []:
        observed[(sid,vid)].add(str(tid).zfill(2))

recommendations=[]
for s in strategies:
    sid=s["strategy_id"]; vid=current.get(sid); d=debt.get(sid,{})
    if d.get("sufficient_evidence") or not vid: continue
    candidates=[]
    for ev in cfg.get("sets",[]):
        if sid not in ev.get("strategy_ids",[]): continue
        for tid in ev.get("task_ids",[]):
            tid=str(tid).zfill(2)
            if tid in observed[(sid,vid)]: continue
            overlap=0
            for other in ev.get("strategy_ids",[]):
                ovid=current.get(other)
                if other!=sid and ovid and tid not in observed[(other,ovid)]: overlap+=1
            candidates.append((overlap,ev["evaluation_set_id"],tid,ev))
    candidates.sort(key=lambda x:(-x[0],x[2],x[1]))
    if candidates:
        overlap,set_id,tid,ev=candidates[0]
        matched=[]
        for other in ev.get("strategy_ids",[]):
            ovid=current.get(other)
            if ovid and tid not in observed[(other,ovid)]:
                matched.append({"strategy_id":other,"strategy_version_id":ovid})
        recommendations.append({
          "strategy_id":sid,"strategy_version_id":vid,"strategy_name":s.get("name"),
          "evaluation_set_id":set_id,"benchmark_task_id":tid,"task":task_names.get(tid),
          "comparison_group_id":f"CMP:{set_id.split(':',1)[-1]}:task-{tid}",
          "matched_conditions":matched,
          "runs_needed":d.get("runs_needed"),"inspections_needed":d.get("inspections_needed"),"matched_overlap":overlap
        })

groups={}
for r in recommendations:
    gid=r["comparison_group_id"]
    g=groups.setdefault(gid,{
      "comparison_group_id":gid,"evaluation_set_id":r["evaluation_set_id"],
      "benchmark_task_id":r["benchmark_task_id"],"task":r["task"],"conditions":{}
    })
    for c in r["matched_conditions"]:
        g["conditions"][(c["strategy_id"],c["strategy_version_id"])]=c
group_rows=[]
for g in groups.values():
    g["conditions"]=sorted(g["conditions"].values(),key=lambda x:(x["strategy_id"],x["strategy_version_id"]))
    group_rows.append(g)
group_rows.sort(key=lambda x:(-len(x["conditions"]),x["benchmark_task_id"],x["comparison_group_id"]))

plan={
 "schema_version":2,"evidence_scope":"current_strategy_version_only",
 "protocol":"benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md",
 "gold_file_prohibited_pre_freeze":"benchmark/BENCHMARK_GOLD.md",
 "recommended_strategy_conditions":recommendations,
 "matched_comparison_groups":group_rows
}
(INTEL/"measurement_campaign.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")

lines=[
 "# MATCHED STRATEGY MEASUREMENT CAMPAIGN","",
 "V5 benchmark conditions are strategy-version specific. An old strategy version cannot satisfy the measurement debt of a changed search procedure.","",
 f"- Current strategy versions needing more evidence: **{len(recommendations)}**",
 f"- Suggested matched comparison groups: **{len(group_rows)}**",
 "- Protocol: `benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md`",
 "- **Do not read `BENCHMARK_GOLD.md` before a result is frozen.**","",
 "## Highest-leverage matched groups","",
 "| Comparison group | Task | Strategy versions |","|---|---|---|"
]
for g in group_rows[:20]:
    cond=", ".join(f"{c['strategy_id']}@{c['strategy_version_id'].split(':')[-1]}" for c in g["conditions"])
    lines.append(f"| {g['comparison_group_id']} | {g['benchmark_task_id']} — {g['task'] or 'task text unavailable'} | {cond} |")
if not group_rows: lines.append("| — | — | — |")
lines += ["","## Per-strategy current-version next measurement","",
 "| Strategy | Version | More runs | More inspections | Evaluation set | Task | Group |","|---|---|---:|---:|---|---|---|"]
for r in recommendations:
    lines.append(f"| {r['strategy_id']} | {r['strategy_version_id']} | {r['runs_needed'] if r['runs_needed'] is not None else '—'} | {r['inspections_needed'] if r['inspections_needed'] is not None else '—'} | {r['evaluation_set_id']} | {r['benchmark_task_id']} | {r['comparison_group_id']} |")
if not recommendations: lines.append("| — | — | 0 | 0 | — | — | — |")
lines += ["","## Interpretation","",
 "- The same frozen task across current strategy versions reduces task/domain confounding.",
 "- A strategy edit invalidates old-version benchmark sufficiency for exploitation; historical results stay available for version comparison.",
 "- No-find and correct reject conditions count when properly evidenced.",
 "- Real customer outcomes remain more important than benchmark wins.",""]
(INTEL/"MEASUREMENT_CAMPAIGN.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"recommendations":len(recommendations),"groups":len(group_rows)}))
