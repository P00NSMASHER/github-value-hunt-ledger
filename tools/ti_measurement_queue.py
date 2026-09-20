#!/usr/bin/env python3
import hashlib,json
from ti_common import INTEL,load_jsonl,write_jsonl

campaign=json.loads((INTEL/"measurement_campaign.json").read_text(encoding="utf-8"))
runs=load_jsonl("search_runs.jsonl")
measurement=json.loads((INTEL/"measurement_plan.json").read_text(encoding="utf-8")) if (INTEL/"measurement_plan.json").exists() else {"rows":[]}
debt={x["strategy_id"]:x for x in measurement.get("rows",[])}

completed=set()
for r in runs:
    if r.get("measurement_quality")!="benchmark": continue
    gid=r.get("comparison_group_id"); sid=r.get("strategy_id")
    for tid in r.get("benchmark_task_ids") or []:
        completed.add((gid,sid,str(tid).zfill(2)))

rows=[]
for g in campaign.get("matched_comparison_groups",[]):
    gid=g["comparison_group_id"]; tid=str(g["benchmark_task_id"]).zfill(2)
    for sid in g.get("strategy_ids",[]):
        key=(gid,sid,tid); d=debt.get(sid,{})
        raw=f"{gid}|{sid}|{tid}"
        mid="MEASURE:"+hashlib.sha1(raw.encode()).hexdigest()[:12]
        status="COMPLETE" if key in completed else "PENDING"
        priority=(d.get("runs_needed") or 0)*5+(d.get("inspections_needed") or 0)
        rows.append({
          "measurement_id":mid,"status":status,"comparison_group_id":gid,
          "evaluation_set_id":g["evaluation_set_id"],"benchmark_task_id":tid,
          "strategy_id":sid,"task":g.get("task"),"priority_score":priority,
          "protocol":"benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md"
        })
rows.sort(key=lambda x:(x["status"]!="PENDING",-x["priority_score"],x["comparison_group_id"],x["strategy_id"]))
write_jsonl("measurement_queue.jsonl",rows)
pending=sum(1 for x in rows if x["status"]=="PENDING")
lines=[
 "# MATCHED STRATEGY MEASUREMENT QUEUE","",
 "This queue turns the measurement campaign into durable strategy-condition work items. Completion is inferred only from a structured V4/V5 benchmark run with matching task, strategy and comparison-group metadata.","",
 f"- Conditions: **{len(rows)}**",f"- Pending: **{pending}**",f"- Complete: **{len(rows)-pending}**","",
 "| Status | Measurement ID | Group | Task | Strategy | Priority |",
 "|---|---|---|---|---|---:|"
]
for x in rows:
    lines.append(f"| {x['status']} | {x['measurement_id']} | {x['comparison_group_id']} | {x['benchmark_task_id']} | {x['strategy_id']} | {x['priority_score']} |")
lines += ["","## Execution rule","",
          "- Run sibling conditions independently and freeze all results before revealing sibling outputs or BENCHMARK_GOLD.md.",
          "- Queue priority reduces measurement debt; it is not a commercial opportunity ranking.",
          "- A no-find or correct reject can complete a condition when properly evidenced.",""]
(INTEL/"MEASUREMENT_QUEUE.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"conditions":len(rows),"pending":pending}))
