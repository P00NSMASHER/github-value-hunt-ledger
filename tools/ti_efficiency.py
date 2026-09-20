#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL,load_jsonl

runs=load_jsonl("search_runs_enriched.jsonl") if (INTEL/"search_runs_enriched.jsonl").exists() else load_jsonl("search_runs.jsonl")
groups=defaultdict(list)
known=[]
for r in runs:
    groups[r.get("strategy_id","unknown")].append(r)
    if isinstance(r.get("elapsed_minutes"),(int,float)) and r.get("elapsed_minutes",0)>0: known.append(r)

def summarize(rs):
    timed=[r for r in rs if isinstance(r.get("elapsed_minutes"),(int,float)) and r.get("elapsed_minutes",0)>0]
    mins=sum(r["elapsed_minutes"] for r in timed)
    hours=mins/60 if mins else 0
    retained=sum((r.get("retained_count") or 0) for r in timed)
    inspected=sum((r.get("deep_inspected") or 0) for r in timed)
    cap=sum(len(r.get("new_capability_ids") or []) for r in timed)
    return {"timed_runs":len(timed),"hours":hours,"inspected":inspected,"retained":retained,"new_capabilities":cap,
            "inspected_per_hour":inspected/hours if hours else None,"retained_per_hour":retained/hours if hours else None}

rows=[]
for sid,rs in groups.items():
    x=summarize(rs); x["strategy_id"]=sid; rows.append(x)
rows.sort(key=lambda x:(-(x["timed_runs"]),x["strategy_id"]))
metrics={"runs":len(runs),"timed_runs":len(known),"effort_coverage":len(known)/len(runs) if runs else 0,"by_strategy":rows}
(INTEL/"efficiency_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
lines=[
 "# SEARCH EFFICIENCY REPORT","",
 "Efficiency metrics are reported only for runs with explicit elapsed-time telemetry; missing time is never estimated.","",
 f"- Runs: **{len(runs)}**",f"- Runs with elapsed_minutes: **{len(known)} ({metrics['effort_coverage']:.1%})**","",
 "| Strategy | Timed runs | Hours | Inspected/hour | Retained/hour | New capabilities |",
 "|---|---:|---:|---:|---:|---:|"
]
for x in rows:
    iph="—" if x["inspected_per_hour"] is None else f"{x['inspected_per_hour']:.2f}"
    rph="—" if x["retained_per_hour"] is None else f"{x['retained_per_hour']:.2f}"
    lines.append(f"| {x['strategy_id']} | {x['timed_runs']} | {x['hours']:.2f} | {iph} | {rph} | {x['new_capabilities']} |")
lines += ["","## Interpretation","",
          "- Do not optimize for raw speed until enough runs have real effort telemetry.",
          "- A slower strategy can be superior if it reduces false promotions or creates higher-value capabilities.",
          "- Realized customer/engineering outcomes remain more important than retained repositories per hour.",""]
(INTEL/"EFFICIENCY_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"runs":len(runs),"timed_runs":len(known)}))
