#!/usr/bin/env python3
import hashlib, json, statistics, subprocess
from collections import defaultdict
from datetime import datetime, timezone
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"activation_response_policy.json").read_text(encoding="utf-8"))
REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
PRESENCE=load_jsonl("worker_presence_history.jsonl")
ACTIVATIONS=load_jsonl("activation_history.jsonl")
CLAIMS=load_jsonl("execution_claim_history.jsonl")

def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

def fmt(dt):
    return None if dt is None else dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def minutes(a,b):
    if not a or not b or b<a:
        return None
    return round((b-a).total_seconds()/60.0,3)

def git_clock():
    try:
        sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
        raw=subprocess.check_output(["git","show","-s","--format=%cI","HEAD"],text=True).strip()
        return sha,parse_ts(raw)
    except Exception:
        return None,None

def median_or_none(vals,min_n=1):
    vals=[float(x) for x in vals if x is not None]
    if len(vals)<min_n:
        return None
    return round(statistics.median(vals),3)

head_sha,now=git_clock()
workers=sorted(x["worker_id"] for x in REG.get("workers",[]))
presence_by_id={x.get("event_id"):x for x in PRESENCE if x.get("event_id")}
claims_by_activation=defaultdict(list)
for c in CLAIMS:
    aid=c.get("activation_id")
    if aid:
        claims_by_activation[aid].append(c)

errors=[]
rows=[]
activation_ids=set()
for a in ACTIVATIONS:
    aid=a.get("activation_id")
    if not aid or aid in activation_ids:
        errors.append(f"duplicate/missing activation_id {aid}")
        continue
    activation_ids.add(aid)
    matches=claims_by_activation.get(aid,[])
    if len(matches)>1:
        errors.append(f"activation {aid} has multiple claims")
        continue
    c=matches[0] if matches else None
    pe=presence_by_id.get(a.get("presence_event_id"))
    ready_at=parse_ts(pe.get("timestamp")) if pe else None
    activated_at=parse_ts(a.get("issued_at_activation"))
    expires_at=parse_ts(a.get("expires_at"))
    claimed_at=parse_ts(c.get("claimed_at")) if c else None
    started_at=parse_ts(c.get("started_at")) if c else None
    ended_at=parse_ts(c.get("ended_at")) if c else None

    if c:
        if c.get("status")=="COMPLETE":
            lifecycle="COMPLETED"
        elif c.get("status") in {"CLAIMED","RUNNING"}:
            lifecycle="CLAIMED"
        else:
            lifecycle="CLAIM_ENDED_OTHER"
    elif expires_at and now and now>expires_at:
        lifecycle="EXPIRED_UNCLAIMED"
    else:
        lifecycle="PENDING"

    rows.append({
      "activation_id":aid,
      "worker_id":a.get("worker_id"),
      "slot_id":a.get("slot_id"),
      "assignment_id":a.get("assignment_id"),
      "assignment_slot_role":a.get("assignment_slot_role"),
      "assignment_work_kind":a.get("assignment_work_kind"),
      "dispatch_ticket_id":a.get("dispatch_ticket_id"),
      "dispatch_generation_id":a.get("dispatch_generation_id"),
      "dispatch_kind":a.get("dispatch_kind") or "primary",
      "dispatch_parent_ticket_id":a.get("parent_dispatch_ticket_id"),
      "presence_generation_id":a.get("presence_generation_id"),
      "presence_event_id":a.get("presence_event_id"),
      "ready_at":fmt(ready_at),
      "activated_at":fmt(activated_at),
      "activation_expires_at":fmt(expires_at),
      "claim_id":None if not c else c.get("claim_id"),
      "claimed_at":fmt(claimed_at),
      "started_at":fmt(started_at),
      "completed_at":fmt(ended_at) if c and c.get("status")=="COMPLETE" else None,
      "claim_status":None if not c else c.get("status"),
      "telemetry_matched":None if not c else c.get("telemetry_status")=="MATCHED",
      "lifecycle_state":lifecycle,
      "claimed":bool(c),
      "ready_to_activation_minutes":minutes(ready_at,activated_at),
      "activation_to_claim_minutes":minutes(activated_at,claimed_at),
      "claim_to_start_minutes":minutes(claimed_at,started_at),
      "start_to_complete_minutes":minutes(started_at,ended_at) if c and c.get("status")=="COMPLETE" else None
    })

if errors:
    raise SystemExit("\n".join(errors))

global_resolved_primary=sum(
    1 for x in rows
    if x["dispatch_kind"]=="primary" and x["lifecycle_state"] in {"EXPIRED_UNCLAIMED","CLAIMED","COMPLETED","CLAIM_ENDED_OTHER"}
)
global_sufficient=global_resolved_primary>=int(POL.get("global_min_resolved_primary_activations",20))

by_worker=defaultdict(list)
for x in rows:
    by_worker[x["worker_id"]].append(x)

metrics_rows=[]
adjustments=[]
for wid in workers:
    wr=by_worker.get(wid,[])
    primary=[x for x in wr if x["dispatch_kind"]=="primary"]
    work_steal=[x for x in wr if x["dispatch_kind"]=="work_steal"]
    resolved=[x for x in primary if x["lifecycle_state"] in {"EXPIRED_UNCLAIMED","CLAIMED","COMPLETED","CLAIM_ENDED_OTHER"}]
    claimed=[x for x in primary if x["claimed"]]
    completed=[x for x in primary if x["lifecycle_state"]=="COMPLETED"]
    expired=[x for x in primary if x["lifecycle_state"]=="EXPIRED_UNCLAIMED"]
    pending=[x for x in primary if x["lifecycle_state"]=="PENDING"]
    claim_rate=None if not resolved else round(len(claimed)/len(resolved),4)
    min_latency=int(POL.get("median_latency_min_claims",2))
    med_activation_claim=median_or_none([x["activation_to_claim_minutes"] for x in claimed],min_latency)
    med_claim_start=median_or_none([x["claim_to_start_minutes"] for x in claimed],min_latency)
    med_start_complete=median_or_none([x["start_to_complete_minutes"] for x in completed],min_latency)
    sufficient=(
      global_sufficient
      and len(resolved)>=int(POL.get("worker_min_resolved_primary_activations",4))
      and len(claimed)>=int(POL.get("worker_min_claimed_primary_activations",2))
    )
    penalty=0.0
    reason="insufficient_evidence"
    if sufficient:
        poor=float(POL.get("poor_claim_rate_threshold",0.5))
        slow=float(POL.get("slow_claim_latency_minutes",20))
        max_pen=float(POL.get("max_negative_routing_adjustment",1.0))
        rate_pen=0.0
        latency_pen=0.0
        if claim_rate is not None and claim_rate<poor:
            rate_pen=max_pen*min(1.0,(poor-claim_rate)/max(poor,1e-9))
        if med_activation_claim is not None and med_activation_claim>slow:
            latency_pen=max_pen*min(1.0,(med_activation_claim-slow)/max(slow,1e-9))
        penalty=-round(max(rate_pen,latency_pen),4)
        reason="measured_activation_response" if penalty<0 else "measured_no_penalty"
    metrics_rows.append({
      "worker_id":wid,
      "primary_activations":len(primary),
      "resolved_primary_activations":len(resolved),
      "claimed_primary_activations":len(claimed),
      "completed_primary_activations":len(completed),
      "expired_unclaimed_primary_activations":len(expired),
      "pending_primary_activations":len(pending),
      "work_steal_activations":len(work_steal),
      "primary_claim_rate":claim_rate,
      "median_activation_to_claim_minutes":med_activation_claim,
      "median_claim_to_start_minutes":med_claim_start,
      "median_start_to_complete_minutes":med_start_complete,
      "sufficient_response_evidence":sufficient
    })
    adjustments.append({
      "worker_id":wid,
      "routing_response_adjustment":penalty,
      "eligible_for_routing":sufficient,
      "reason":reason,
      "resolved_primary_activations":len(resolved),
      "claimed_primary_activations":len(claimed),
      "primary_claim_rate":claim_rate,
      "median_activation_to_claim_minutes":med_activation_claim
    })

fingerprint=json.dumps({
  "head_sha":head_sha,
  "global_resolved_primary":global_resolved_primary,
  "rows":[(x["activation_id"],x["lifecycle_state"],x["claim_id"],x["activation_to_claim_minutes"]) for x in rows],
  "adjustments":[(x["worker_id"],x["routing_response_adjustment"],x["eligible_for_routing"]) for x in adjustments]
},sort_keys=True)
gen="RESPLEARN:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in rows: x["response_learning_generation_id"]=gen
for x in metrics_rows: x["response_learning_generation_id"]=gen
for x in adjustments: x["response_learning_generation_id"]=gen

mode="measured_feedback" if global_sufficient else "observe_only_insufficient_evidence"
summary={
  "schema_version":1,
  "response_learning_generation_id":gen,
  "clock_commit_sha":head_sha,
  "clock_timestamp":fmt(now),
  "mode":mode,
  "activation_records":len(rows),
  "global_resolved_primary_activations":global_resolved_primary,
  "global_evidence_threshold":int(POL.get("global_min_resolved_primary_activations",20)),
  "workers_with_sufficient_evidence":sum(1 for x in metrics_rows if x["sufficient_response_evidence"]),
  "workers_with_negative_adjustment":sum(1 for x in adjustments if x["routing_response_adjustment"]<0)
}

def write_jsonl(name,data):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in data)+("\n" if data else ""),encoding="utf-8")

write_jsonl("activation_response_runs.jsonl",rows)
write_jsonl("worker_activation_response_metrics.jsonl",metrics_rows)
write_jsonl("activation_response_adjustments.jsonl",adjustments)
(INTEL/"activation_response_metrics.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")

report=[
 "# ACTIVATION RESPONSE LEARNING","",
 f"Generation: **{gen}**",
 f"Mode: **{mode}**",
 f"Resolved primary activations: **{global_resolved_primary} / {summary['global_evidence_threshold']}**","",
 "V17 measures worker responsiveness only after fresh READY presence has produced a real activation.",
 "READY→activation is system latency. Activation→claim is the only metric allowed to affect routing.",
 "Claim→start and start→completion are descriptive only.","",
 "| Worker | Resolved | Claimed | Claim rate | Median activate→claim | Expired unclaimed | Routing adjustment | Evidence |",
 "|---|---:|---:|---:|---:|---:|---:|---|"
]
mi={x["worker_id"]:x for x in metrics_rows}
ai={x["worker_id"]:x for x in adjustments}
for wid in workers:
    m=mi[wid];a=ai[wid]
    rate="—" if m["primary_claim_rate"] is None else f"{100*m['primary_claim_rate']:.1f}%"
    lat="—" if m["median_activation_to_claim_minutes"] is None else f"{m['median_activation_to_claim_minutes']:.1f}"
    report.append(
      f"| {wid} | {m['resolved_primary_activations']} | {m['claimed_primary_activations']} | {rate} | {lat} | "
      f"{m['expired_unclaimed_primary_activations']} | {a['routing_response_adjustment']:.3f} | "
      f"{'sufficient' if m['sufficient_response_evidence'] else 'insufficient'} |"
    )
report += ["",
 "No adjustment is created from UNKNOWN/OFFLINE/PAUSED presence, unactivated READY events, pending activations, work-steal activations, or completion duration.",
 ""]
(INTEL/"ACTIVATION_RESPONSE_REPORT.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(summary))
