#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import datetime
from ti_common import INTEL, load_jsonl, normalize_run_time, slug, write_jsonl

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
aliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
objective_map=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}

def raw_family_id(label):
    base=slug(label or "unknown") or "unknown"
    return "QF:"+base[:120]

def canonical_family_id(label):
    rid=raw_family_id(label)
    return aliases.get(rid,rid)

def parse_time(value):
    if not value: return None
    try: return datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except Exception: return None

groups=defaultdict(list)
for r in runs:
    groups[canonical_family_id(r.get("query_family") or "unknown")].append(r)

rows=[]
conflicts=[]
for qid,rs in groups.items():
    labels=[r.get("query_family") or "unknown" for r in rs]
    label_counts=defaultdict(int)
    for x in labels: label_counts[x]+=1
    canonical_label=sorted(label_counts,key=lambda x:(-label_counts[x],x))[0]
    times=[parse_time(normalize_run_time(r)) for r in rs]
    times=[t for t in times if t]
    inspected=sum((r.get("deep_inspected") or 0) for r in rs)
    explicit=sorted(set(r.get("search_objective_id") for r in rs if r.get("search_objective_id")))
    if len(explicit)>1:
        conflicts.append({"query_family_id":qid,"search_objective_ids":explicit})
        objective_id=None
    elif explicit:
        objective_id=explicit[0]
    else:
        objective_id=objective_map.get(qid)
    rows.append({
      "query_family_id":qid,
      "label":canonical_label,
      "aliases_seen":sorted(set(labels)),
      "primary_search_objective_id":objective_id,
      "explicit_objective_ids_seen":explicit,
      "run_count":len(rs),
      "candidate_count":sum((r.get("candidate_count") or 0) for r in rs),
      "deep_inspected":inspected,
      "retained_count":sum((r.get("retained_count") or 0) for r in rs),
      "master_promoted_count":sum((r.get("master_promoted_count") or 0) for r in rs),
      "new_capability_run_count":sum(1 for r in rs if r.get("new_capability_ids")),
      "experiment_run_count":sum(1 for r in rs if r.get("experiment_ids")),
      "strategy_ids":sorted(set(r.get("strategy_id") for r in rs if r.get("strategy_id"))),
      "search_surfaces":sorted(set(s for r in rs for s in (r.get("search_surfaces") or []))),
      "first_seen":min(times).isoformat() if times else None,
      "last_seen":max(times).isoformat() if times else None,
      "evidence_state":"sufficient" if len(rs)>=5 and inspected>=20 else "insufficient"
    })

rows.sort(key=lambda x:(-x["run_count"],-x["deep_inspected"],x["query_family_id"]))
write_jsonl("query_families.jsonl",rows)

one_off=sum(1 for x in rows if x["run_count"]==1)
mapped=sum(1 for x in rows if x.get("primary_search_objective_id"))
lines=[
 "# QUERY FAMILY REPORT","",
 "Query families preserve reusable search hypotheses while broader search objectives aggregate related hypotheses across domains.","",
 f"- Measured query families: **{len(rows)}**",
 f"- One-run families: **{one_off}**",
 f"- Families mapped to a controlled search objective: **{mapped}/{len(rows)}**",
 f"- Objective conflicts requiring review: **{len(conflicts)}**",
 f"- Families with sufficient evidence (>=5 runs and >=20 deep inspections): **{sum(1 for x in rows if x['evidence_state']=='sufficient')}**","",
 "## Family measurements","",
 "| Query family | Objective | Runs | Inspected | Retained | MASTER | Capability runs | Experiment runs | Evidence |",
 "|---|---|---:|---:|---:|---:|---:|---:|---|"
]
for x in rows[:60]:
    lines.append(
      f"| {x['query_family_id']} — {x['label']} | {x.get('primary_search_objective_id') or 'unclassified'} | "
      f"{x['run_count']} | {x['deep_inspected']} | {x['retained_count']} | {x['master_promoted_count']} | "
      f"{x['new_capability_run_count']} | {x['experiment_run_count']} | {x['evidence_state']} |"
    )
if not rows: lines.append("| — | — | 0 | 0 | 0 | 0 | 0 | 0 | insufficient |")
if conflicts:
    lines += ["","## Objective conflicts",""]
    for c in conflicts:
        lines.append(f"- {c['query_family_id']}: {', '.join(c['search_objective_ids'])}")
lines += ["","## Interpretation","",
          "- A one-off query family is a hypothesis, not a learned policy.",
          "- The objective layer is intentionally broader: related queries can teach the same research objective without being merged into one QF.",
          "- Reuse a QF only when the implementation conjunction/hypothesis is genuinely the same.",
          "- Literal queries remain preserved in search runs for reproducibility.",""]
(INTEL/"QUERY_FAMILY_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"query_families":len(rows),"one_off":one_off,"mapped_objectives":mapped,"conflicts":len(conflicts)}))
