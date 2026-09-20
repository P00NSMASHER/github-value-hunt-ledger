#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl, slug

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
objectives_cfg=json.loads((INTEL/"search_objectives.json").read_text(encoding="utf-8"))
objectives={x["search_objective_id"]:x for x in objectives_cfg.get("objectives",[])}
qmap=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
qaliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
attr=json.loads((INTEL/"attribution_metrics.json").read_text(encoding="utf-8")) if (INTEL/"attribution_metrics.json").exists() else {}
attr_map={x["id"]:x for x in attr.get("by_objective",[])}

def qfid(run):
    raw="QF:"+(slug(run.get("query_family") or "unknown")[:120] or "unknown")
    return qaliases.get(raw,raw)

def oid(run):
    return run.get("search_objective_id") or qmap.get(qfid(run)) or "OBJ:unclassified"

groups=defaultdict(list)
for r in runs: groups[oid(r)].append(r)

rows=[]
for obj_id,rs in groups.items():
    a=attr_map.get(obj_id,{})
    rows.append({
      "search_objective_id":obj_id,
      "name":objectives.get(obj_id,{}).get("name","Unclassified"),
      "runs":len(rs),
      "deep_inspected":sum((r.get("deep_inspected") or 0) for r in rs),
      "retained_count":sum((r.get("retained_count") or 0) for r in rs),
      "master_promoted_count":sum((r.get("master_promoted_count") or 0) for r in rs),
      "capability_touch_runs":sum(1 for r in rs if r.get("new_capability_ids") or r.get("strengthened_capability_ids")),
      "experiment_runs":sum(1 for r in rs if r.get("experiment_ids")),
      "assisted_outcome_count":a.get("assisted_outcome_count",0),
      "fractional_outcome_equivalents":a.get("fractional_outcome_equivalents",0)
    })
rows.sort(key=lambda x:(-x["runs"],-x["deep_inspected"],x["search_objective_id"]))
metrics={"rows":rows,"unclassified_runs":len(groups.get("OBJ:unclassified",[]))}
(INTEL/"objective_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
lines=[
 "# SEARCH OBJECTIVE REPORT","",
 "Objectives are broader than query families. They let multiple domain-specific queries teach the same reusable research question while preserving each literal query and QF identity.","",
 f"- Defined objectives: **{len(objectives)}**",
 f"- Objectives touched by measured runs: **{len([x for x in rows if x['search_objective_id']!='OBJ:unclassified'])}**",
 f"- Unclassified measured runs: **{metrics['unclassified_runs']}**","",
 "| Objective | Runs | Inspected | Retained | MASTER | Capability-touch runs | Experiment runs | Outcome eq. |",
 "|---|---:|---:|---:|---:|---:|---:|---:|"
]
for x in rows:
    lines.append(f"| {x['search_objective_id']} — {x['name']} | {x['runs']} | {x['deep_inspected']} | {x['retained_count']} | {x['master_promoted_count']} | {x['capability_touch_runs']} | {x['experiment_runs']} | {x['fractional_outcome_equivalents']:.2f} |")
if not rows: lines.append("| — | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |")
lines += ["","## Interpretation","",
          "- Objective-level aggregation is descriptive; it does not replace matched strategy experiments.",
          "- A query family should map to one primary objective only when the hypothesis is clear. Ambiguous families stay unclassified rather than being force-fit.",
          "- Future V4 prospective runs persist `search_objective_id` directly; legacy runs are mapped through `query_objective_map.json`.",""]
(INTEL/"OBJECTIVE_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"objectives":len(objectives),"touched":len(rows),"unclassified":metrics["unclassified_runs"]}))
