#!/usr/bin/env python3
import hashlib,json
from ti_common import INTEL,load_jsonl,write_jsonl

campaign=json.loads((INTEL/"measurement_campaign.json").read_text(encoding="utf-8"))
runs=load_jsonl("search_runs.jsonl")
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
measurement=json.loads((INTEL/"measurement_plan.json").read_text(encoding="utf-8")) if (INTEL/"measurement_plan.json").exists() else {"rows":[]}
debt={x["strategy_id"]:x for x in measurement.get("rows",[])}

completed=set()
for r in runs:
    if r.get("measurement_quality")!="benchmark": continue
    gid=r.get("comparison_group_id"); sid=r.get("strategy_id")
    vid=r.get("strategy_version_id") or (bindings.get(r["search_run_id"]) or {}).get("strategy_version_id")
    for tid in r.get("benchmark_task_ids") or []:
        completed.add((gid,sid,vid,str(tid).zfill(2)))

rows=[]
for g in campaign.get("matched_comparison_groups",[]):
    gid=g["comparison_group_id"]; tid=str(g["benchmark_task_id"]).zfill(2)
    for cond in g.get("conditions",[]):
        sid=cond["strategy_id"]; vid=cond["strategy_version_id"]; d=debt.get(sid,{})
        key=(gid,sid,vid,tid); raw="|".join(str(x) for x in key)
        mid="MEASURE:"+hashlib.sha1(raw.encode()).hexdigest()[:12]
        status="COMPLETE" if key in completed else "PENDING"
        priority=(d.get("runs_needed") or 0)*5+(d.get("inspections_needed") or 0)
        rows.append({
          "measurement_id":mid,"status":status,"comparison_group_id":gid,
          "evaluation_set_id":g["evaluation_set_id"],"benchmark_task_id":tid,
          "strategy_id":sid,"strategy_version_id":vid,"task":g.get("task"),
          "priority_score":priority,"protocol":"benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md"
        })
rows.sort(key=lambda x:(x["status"]!="PENDING",-x["priority_score"],x["comparison_group_id"],x["strategy_id"]))
write_jsonl("measurement_queue.jsonl",rows)
pending=sum(1 for x in rows if x["status"]=="PENDING")
lines=[
 "# MATCHED STRATEGY MEASUREMENT QUEUE","",
 "Completion is strategy-version specific: a benchmark run completes a condition only when group, task, strategy and STRATVER all match.","",
 f"- Conditions: **{len(rows)}**",f"- Pending: **{pending}**",f"- Complete: **{len(rows)-pending}**","",
 "| Status | Measurement ID | Group | Task | Strategy version | Priority |",
 "|---|---|---|---|---|---:|"
]
for x in rows:
    lines.append(f"| {x['status']} | {x['measurement_id']} | {x['comparison_group_id']} | {x['benchmark_task_id']} | {x['strategy_id']}@{x['strategy_version_id'].split(':')[-1]} | {x['priority_score']} |")
lines += ["","## Execution rule","",
 "- Run sibling conditions independently and freeze results before revealing sibling outputs or BENCHMARK_GOLD.md.",
 "- An old strategy-version result cannot complete a current-version condition.",
 "- Queue priority reduces measurement debt; it is not commercial ranking.",
 "- A no-find or correct reject can complete a condition when properly evidenced.",""]
(INTEL/"MEASUREMENT_QUEUE.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"conditions":len(rows),"pending":pending}))
