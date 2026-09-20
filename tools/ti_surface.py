#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl, slug

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
attr=json.loads((INTEL/"attribution_metrics.json").read_text(encoding="utf-8")) if (INTEL/"attribution_metrics.json").exists() else {}
exact_attr={x["id"]:x for x in attr.get("by_surface",[])}
family_attr={x["id"]:x for x in attr.get("by_surface_family",[])}
aliases=json.loads((INTEL/"surface_aliases.json").read_text(encoding="utf-8")) if (INTEL/"surface_aliases.json").exists() else {}
family_cfg=json.loads((INTEL/"surface_families.json").read_text(encoding="utf-8")) if (INTEL/"surface_families.json").exists() else {"families":[]}
family_names={x["surface_family_id"]:x["name"] for x in family_cfg.get("families",[])}

def sid(label): return "SURFACE:"+slug(label)

def classify(surface_id):
    if surface_id in aliases: return aliases[surface_id]
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

exact_groups=defaultdict(list); labels=defaultdict(set); family_groups=defaultdict(list); family_exact=defaultdict(set)
for r in runs:
    exact=sorted(set(r.get("search_surfaces") or []))
    families=set()
    for label in exact:
        x=sid(label); exact_groups[x].append(r); labels[x].add(label)
        fam=classify(x); families.add(fam); family_exact[fam].add(x)
    for fam in families: family_groups[fam].append(r)

def summarize(groups, attr_map):
    rows=[]
    for key,rs in groups.items():
        a=attr_map.get(key,{})
        rows.append({
          "id":key,
          "runs":len(rs),
          "deep_inspected":sum((r.get("deep_inspected") or 0) for r in rs),
          "retained_count":sum((r.get("retained_count") or 0) for r in rs),
          "master_promoted_count":sum((r.get("master_promoted_count") or 0) for r in rs),
          "capability_touch_runs":sum(1 for r in rs if r.get("new_capability_ids") or r.get("strengthened_capability_ids")),
          "experiment_runs":sum(1 for r in rs if r.get("experiment_ids")),
          "assisted_outcome_count":a.get("assisted_outcome_count",0),
          "fractional_outcome_equivalents":a.get("fractional_outcome_equivalents",0)
        })
    return sorted(rows,key=lambda x:(-x["runs"],-x["deep_inspected"],x["id"]))

exact_rows=summarize(exact_groups,exact_attr)
family_rows=summarize(family_groups,family_attr)
for x in exact_rows:
    x["labels_seen"]=sorted(labels[x["id"]]); x["surface_family_id"]=classify(x["id"])
for x in family_rows:
    x["name"]=family_names.get(x["id"],x["id"]); x["exact_surface_ids"]=sorted(family_exact[x["id"]])

metrics={
 "exact_rows":exact_rows,
 "family_rows":family_rows,
 "missing_surface_runs":sum(1 for r in runs if not r.get("search_surfaces")),
 "unmapped_exact_surfaces":sorted(x["id"] for x in exact_rows if x["surface_family_id"]=="SURFACE_FAMILY:other")
}
(INTEL/"surface_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
 "# SEARCH SURFACE REPORT","",
 "Runs can use multiple surfaces. V4 reports both exact surface labels and normalized surface families; both are assisted/multi-touch measurements, not isolated causal effects.","",
 f"- Exact measured surfaces: **{len(exact_rows)}**",
 f"- Normalized surface families touched: **{len(family_rows)}**",
 f"- Runs missing search-surface instrumentation: **{metrics['missing_surface_runs']}**",
 f"- Exact surfaces still uncategorized: **{len(metrics['unmapped_exact_surfaces'])}**","",
 "## Normalized surface families","",
 "| Surface family | Exact labels | Runs | Inspected | Retained | MASTER | Capability-touch runs | Outcome eq. |",
 "|---|---:|---:|---:|---:|---:|---:|---:|"
]
for x in family_rows:
    lines.append(f"| {x['id']} — {x['name']} | {len(x['exact_surface_ids'])} | {x['runs']} | {x['deep_inspected']} | {x['retained_count']} | {x['master_promoted_count']} | {x['capability_touch_runs']} | {x['fractional_outcome_equivalents']:.2f} |")
if not family_rows: lines.append("| — | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |")
lines += ["","## Exact surface measurements","",
          "| Surface | Family | Runs | Inspected | Retained | Outcome eq. |","|---|---|---:|---:|---:|---:|"]
for x in exact_rows:
    display="; ".join(x["labels_seen"][:2])
    lines.append(f"| {x['id']} — {display} | {x['surface_family_id']} | {x['runs']} | {x['deep_inspected']} | {x['retained_count']} | {x['fractional_outcome_equivalents']:.2f} |")
lines += ["","## Interpretation","",
          "- Family-level aggregation reduces wording fragmentation while exact labels remain available for diagnosis.",
          "- Surface usage is multi-touch; matched comparisons are required before claiming a surface causes higher yield.",
          "- Unmapped surfaces create taxonomy debt and should be reviewed rather than silently force-fit.",""]
(INTEL/"SURFACE_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"exact_surfaces":len(exact_rows),"families":len(family_rows),"unmapped":len(metrics["unmapped_exact_surfaces"])}))
