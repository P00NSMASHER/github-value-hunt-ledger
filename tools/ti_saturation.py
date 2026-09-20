#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl, slug

RUNS=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
QALIASES=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
POLICY=json.loads((INTEL/"search_policy.json").read_text(encoding="utf-8"))

def canonical_qf(r):
    qid=r.get("query_family_id")
    if qid:
        return QALIASES.get(qid,qid)
    raw="QF:"+(slug(r.get("query_family") or "unknown")[:120] or "unknown")
    return QALIASES.get(raw,raw)

def run_time(r):
    return r.get("timestamp") or r.get("date") or ""

def add_region(regions, rid, rtype, label, run):
    if not rid:
        return
    x=regions.setdefault(rid,{
        "neighborhood_id":rid,
        "neighborhood_type":rtype,
        "label":label,
        "runs":[],
        "candidate_count":0,
        "deep_inspected":0,
        "retained_count":0,
        "master_promoted_count":0,
        "new_capability_run_count":0,
        "experiment_run_count":0,
        "disposition_count":0,
        "duplicate_count":0,
        "first_seen_observed":0,
        "first_seen_true":0,
        "novelty_observed":0,
        "novelty_sum":0.0
    })
    x["runs"].append(run)
    x["candidate_count"]+=(run.get("candidate_count") or 0)
    x["deep_inspected"]+=(run.get("deep_inspected") or 0)
    x["retained_count"]+=(run.get("retained_count") or 0)
    x["master_promoted_count"]+=(run.get("master_promoted_count") or 0)
    x["new_capability_run_count"]+=1 if run.get("new_capability_ids") else 0
    x["experiment_run_count"]+=1 if run.get("experiment_ids") else 0
    for d in run.get("candidate_dispositions") or []:
        x["disposition_count"]+=1
        if d.get("duplicate_of") or d.get("reason_code_standard")=="duplicate_or_dominated":
            x["duplicate_count"]+=1
        if d.get("first_seen_in_registry") is not None:
            x["first_seen_observed"]+=1
            if d.get("first_seen_in_registry") is True:
                x["first_seen_true"]+=1
        if d.get("novelty_ordinal") is not None:
            x["novelty_observed"]+=1
            x["novelty_sum"]+=float(d.get("novelty_ordinal"))

regions={}
for r in RUNS:
    caps=sorted(set((r.get("new_capability_ids") or [])+(r.get("strengthened_capability_ids") or [])))
    for cid in caps:
        add_region(regions,"NBR:cap:"+cid.lower(),"capability",cid,r)
    qf=canonical_qf(r)
    add_region(regions,"NBR:qf:"+qf[3:],"query_family",qf,r)
    oid=r.get("search_objective_id")
    if oid:
        add_region(regions,"NBR:obj:"+oid[4:],"search_objective",oid,r)
    for typ in sorted(set(r.get("adjacency_types") or [])):
        add_region(regions,"NBR:adj-type:"+slug(typ),"adjacency_type",typ,r)
    for root in sorted(set(r.get("adjacency_root_nodes") or [])):
        add_region(regions,"NBR:root:"+slug(root.replace("REPO:","").replace("/","-")),"adjacency_root",root,r)
    for sid in sorted(set(r.get("seed_ids") or [])):
        add_region(regions,"NBR:seed:"+slug(sid.replace("SEED:","")),"search_seed",sid,r)

cap_gap_map={x["capability_id"]:x for x in POLICY.get("priority_capability_gaps",[])}

def ratio(a,b):
    return (a/b) if b else None

def trailing_no_delta(rs):
    streak=0
    for r in sorted(rs,key=run_time,reverse=True):
        if (r.get("master_promoted_count") or 0)>0 or (r.get("new_capability_ids") or []):
            break
        streak+=1
    return streak

def recent_window(rs,n=3):
    return sorted(rs,key=run_time)[-n:]

rows=[]
for rid,x in regions.items():
    rs=x["runs"]
    nr=len(rs)
    ins=x["deep_inspected"]
    retained_precision=ratio(x["retained_count"],ins)
    master_yield=ratio(x["master_promoted_count"],ins)
    new_cap_rate=ratio(x["new_capability_run_count"],nr)
    duplicate_ratio=ratio(x["duplicate_count"],x["disposition_count"])
    first_seen_rate=ratio(x["first_seen_true"],x["first_seen_observed"])
    avg_novelty=ratio(x["novelty_sum"],x["novelty_observed"])
    streak=trailing_no_delta(rs)
    recent=recent_window(rs)
    recent_ins=sum((r.get("deep_inspected") or 0) for r in recent)
    recent_ret=sum((r.get("retained_count") or 0) for r in recent)
    recent_retained_precision=ratio(recent_ret,recent_ins)

    sufficient=nr>=5 and ins>=20
    duplicate_observable=x["disposition_count"]>=10
    first_seen_observable=x["first_seen_observed"]>=10

    status="INSUFFICIENT"
    score=0
    if sufficient:
        attention=min(25.0,25.0*ins/40.0)
        duplicate_pressure=(25.0*(duplicate_ratio or 0)) if duplicate_observable else 0.0
        low_newcap=20.0*(1.0-min(1.0,(new_cap_rate or 0)/0.25))
        low_master=15.0*(1.0-min(1.0,(master_yield or 0)/0.05))
        recent_stall=min(15.0,5.0*streak)
        score=round(attention+duplicate_pressure+low_newcap+low_master+recent_stall,1)

        exhausted_signal = (
            streak>=3 and
            (new_cap_rate or 0)<=0.10 and
            (master_yield or 0)<=0.02 and
            (
                (duplicate_observable and (duplicate_ratio or 0)>=0.50) or
                (first_seen_observable and (first_seen_rate or 0)<=0.20) or
                (recent_retained_precision is not None and recent_retained_precision<=0.15)
            )
        )
        saturating_signal = (
            streak>=2 and
            (new_cap_rate or 0)<=0.20 and
            (master_yield or 0)<=0.05 and
            (
                (duplicate_observable and (duplicate_ratio or 0)>=0.35) or
                (first_seen_observable and (first_seen_rate or 0)<=0.35) or
                (recent_retained_precision is not None and recent_retained_precision<=0.25)
            )
        )
        productive_signal = (
            (master_yield or 0)>0.05 or
            (new_cap_rate or 0)>0.25 or
            (first_seen_observable and (first_seen_rate or 0)>=0.50 and (retained_precision or 0)>=0.40)
        )
        if exhausted_signal:
            status="SATURATED"
        elif saturating_signal:
            status="SATURATING"
        elif productive_signal:
            status="PRODUCTIVE"
        else:
            status="BALANCED"

    action={
        "INSUFFICIENT":"MEASURE_MORE",
        "PRODUCTIVE":"CONTINUE_BOUNDED",
        "BALANCED":"CONTINUE_WITH_DIVERSITY",
        "SATURATING":"DIVERSIFY_SURFACE_OR_ADJACENCY",
        "SATURATED":"SHIFT_TO_EXPERIMENT_OR_UNDEREXPLORED_NEIGHBORHOOD"
    }[status]

    gap_priority=None
    if x["neighborhood_type"]=="capability":
        cid=x["label"]
        if cid in cap_gap_map:
            gap_priority=cap_gap_map[cid].get("gap_score")

    rows.append({
        "neighborhood_id":rid,
        "neighborhood_type":x["neighborhood_type"],
        "label":x["label"],
        "status":status,
        "saturation_score":score,
        "recommended_action":action,
        "runs":nr,
        "candidate_count":x["candidate_count"],
        "deep_inspected":ins,
        "retained_count":x["retained_count"],
        "master_promoted_count":x["master_promoted_count"],
        "new_capability_run_count":x["new_capability_run_count"],
        "experiment_run_count":x["experiment_run_count"],
        "retained_precision":retained_precision,
        "master_yield":master_yield,
        "new_capability_run_rate":new_cap_rate,
        "duplicate_ratio":duplicate_ratio if duplicate_observable else None,
        "first_seen_rate":first_seen_rate if first_seen_observable else None,
        "average_novelty_ordinal":avg_novelty,
        "trailing_no_delta_runs":streak,
        "recent_retained_precision":recent_retained_precision,
        "sufficient_evidence":sufficient,
        "duplicate_observable":duplicate_observable,
        "first_seen_observable":first_seen_observable,
        "capability_gap_score":gap_priority
    })

rows.sort(key=lambda x:(
    {"SATURATED":0,"SATURATING":1,"PRODUCTIVE":2,"BALANCED":3,"INSUFFICIENT":4}[x["status"]],
    -x["saturation_score"],
    x["neighborhood_id"]
))
from ti_common import write_jsonl
write_jsonl("research_neighborhoods.jsonl",rows)

status_counts=defaultdict(int)
for x in rows:
    status_counts[x["status"]]+=1

redirects=[]
for x in rows:
    if x["neighborhood_type"]!="capability":
        continue
    if x["status"]=="SATURATED":
        priority=95
        rationale="Discovery appears saturated; move effort to experiment execution, independent falsification, or a cross-domain transfer."
    elif x["status"]=="SATURATING":
        priority=80
        rationale="Returns are diminishing; diversify search surface, adjacency type, or domain before another same-shaped sweep."
    elif x["status"]=="INSUFFICIENT" and x.get("capability_gap_score"):
        priority=min(90,55+5*int(x["capability_gap_score"]))
        rationale="High-information capability gap with insufficient search evidence; collect measured runs before making saturation claims."
    elif x["status"]=="PRODUCTIVE":
        priority=65
        rationale="Neighborhood remains productive; continue bounded searches while preserving exploration elsewhere."
    else:
        continue
    redirects.append({
        "neighborhood_id":x["neighborhood_id"],
        "capability_id":x["label"],
        "status":x["status"],
        "priority":priority,
        "recommended_action":x["recommended_action"],
        "rationale":rationale,
        "runs":x["runs"],
        "deep_inspected":x["deep_inspected"],
        "saturation_score":x["saturation_score"]
    })
redirects.sort(key=lambda x:(-x["priority"],-x["saturation_score"],x["capability_id"]))
write_jsonl("redirect_queue.jsonl",redirects)

metrics={
    "schema_version":1,
    "measured_runs":len(RUNS),
    "neighborhood_count":len(rows),
    "status_counts":dict(status_counts),
    "sufficient_neighborhoods":sum(1 for x in rows if x["sufficient_evidence"]),
    "saturated_neighborhoods":sum(1 for x in rows if x["status"]=="SATURATED"),
    "saturating_neighborhoods":sum(1 for x in rows if x["status"]=="SATURATING"),
    "thresholds":{
        "min_runs":5,
        "min_deep_inspections":20,
        "min_dispositions_for_duplicate_ratio":10,
        "min_first_seen_observations":10
    }
}
(INTEL/"saturation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
    "# SEARCH SATURATION REPORT","",
    "Saturation is a soft redirect, not a ban. A neighborhood is never marked saturated from attention alone; it requires enough measured runs plus evidence of low novelty or rising duplication.","",
    f"- Measured runs: **{len(RUNS)}**",
    f"- Research neighborhoods: **{len(rows)}**",
    f"- Sufficient-evidence neighborhoods: **{metrics['sufficient_neighborhoods']}**",
    f"- Saturating: **{metrics['saturating_neighborhoods']}**",
    f"- Saturated: **{metrics['saturated_neighborhoods']}**","",
    "## Neighborhood health","",
    "| Neighborhood | Type | Status | Runs | Inspected | Retained | MASTER | New-cap run rate | Duplicate ratio | Trailing no-delta | Action |",
    "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"
]
for x in rows[:80]:
    nr="—" if x["new_capability_run_rate"] is None else f"{x['new_capability_run_rate']:.0%}"
    dr="—" if x["duplicate_ratio"] is None else f"{x['duplicate_ratio']:.0%}"
    lines.append(f"| {x['neighborhood_id']} | {x['neighborhood_type']} | {x['status']} | {x['runs']} | {x['deep_inspected']} | {x['retained_count']} | {x['master_promoted_count']} | {nr} | {dr} | {x['trailing_no_delta_runs']} | {x['recommended_action']} |")
lines += ["","## Guardrails","",
    "- Insufficient telemetry is never interpreted as saturation.",
    "- Saturation cannot override an active experiment-specific search need.",
    "- A saturated same-domain neighborhood may still justify cross-domain positive-DNA transfer.",
    "- Duplicate ratio is ignored until at least 10 structured candidate dispositions exist.",
    "- First-seen rate is ignored until at least 10 explicit first-seen observations exist.",
    "- Three consecutive no-delta runs are necessary but not sufficient for SATURATED.",
    "- Manual review should inspect false-negative rescues before any hard prefilter is created.",""]
(INTEL/"SATURATION_REPORT.md").write_text("\n".join(lines),encoding="utf-8")

red=["# SEARCH REDIRECT QUEUE","","Prioritized actions produced from capability-neighborhood saturation plus current capability gaps.","","| Priority | Capability | Status | Action | Runs | Inspected | Rationale |","|---:|---|---|---|---:|---:|---|"]
for x in redirects:
    red.append(f"| {x['priority']} | {x['capability_id']} | {x['status']} | {x['recommended_action']} | {x['runs']} | {x['deep_inspected']} | {x['rationale']} |")
(INTEL/"REDIRECT_QUEUE.md").write_text("\n".join(red)+"\n",encoding="utf-8")
print(json.dumps(metrics))
