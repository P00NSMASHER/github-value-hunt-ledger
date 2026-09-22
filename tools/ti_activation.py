#!/usr/bin/env python3
import hashlib, json, subprocess, sys
from datetime import datetime, timezone, timedelta
from ti_common import INTEL, ROOT, load_jsonl

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.restart_readiness import build_restart_readiness
from production.runtime_activation_gate import evaluate_runtime_activation_gate

POL=json.loads((INTEL/"activation_policy.json").read_text(encoding="utf-8"))
RUNTIME_POL=json.loads((INTEL/"hunter_runtime_policy.json").read_text(encoding="utf-8"))
PPOL=json.loads((INTEL/"worker_presence_policy.json").read_text(encoding="utf-8"))
SPLIT_STATUS=json.loads((INTEL/"TRAINING_SPLIT_STATUS.json").read_text(encoding="utf-8"))
MEASUREMENT_PACKETS=json.loads((INTEL/"learning_measurement_packets.json").read_text(encoding="utf-8"))
PRES=load_jsonl("worker_presence_state.jsonl")
PRIMARY=load_jsonl("dispatch_claim_packets.jsonl")
STEALS=load_jsonl("work_steal_claim_packets.jsonl") if (INTEL/"work_steal_claim_packets.jsonl").exists() else []
STATE=load_jsonl("execution_state.jsonl")
CLAIM_HISTORY=load_jsonl("execution_claim_history.jsonl") if (INTEL/"execution_claim_history.jsonl").exists() else []
APPROVAL_HISTORY=load_jsonl("hunter_runtime_approval_history.jsonl") if (INTEL/"hunter_runtime_approval_history.jsonl").exists() else []
HISTORY=load_jsonl("activation_history.jsonl") if (INTEL/"activation_history.jsonl").exists() else []

scoreboard=(ROOT/"benchmark"/"SCOREBOARD.md").read_text(encoding="utf-8")
shadow_results={}
for lane in ("ai","science","commercial"):
    path=ROOT/"production"/"shadow"/"results"/f"{lane}.md"
    shadow_results[lane]=path.read_text(encoding="utf-8") if path.exists() else ""
PREACTIVATION_READINESS=build_restart_readiness(
    split_status=SPLIT_STATUS,
    activation_metrics={"current_activations":0},
    packets=MEASUREMENT_PACKETS,
    scoreboard_text=scoreboard,
    shadow_results=shadow_results,
    execution_claim_history=CLAIM_HISTORY,
)
RUNTIME_GATE=evaluate_runtime_activation_gate(
    RUNTIME_POL,
    PREACTIVATION_READINESS,
    MEASUREMENT_PACKETS,
    CLAIM_HISTORY,
    APPROVAL_HISTORY,
)

def parse_ts(v):
    if not v: return None
    dt=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

def fmt(dt):
    return None if dt is None else dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def git_clock():
    try:
        sha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
        raw=subprocess.check_output(["git","show","-s","--format=%cI","HEAD"],text=True).strip()
        return sha,parse_ts(raw)
    except Exception:
        return None,None

def activation_id(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return "ACTIVATE:"+hashlib.sha256(raw.encode()).hexdigest()[:12]

head_sha,now=git_clock()
pres_by_worker={x["worker_id"]:x for x in PRES}
active_workers={
  x.get("worker_id") for x in STATE
  if x.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"} and x.get("worker_id")
}
claimable_slots={
  x.get("slot_id") for x in STATE
  if x.get("status") in {"AVAILABLE","EXPIRED_AVAILABLE","RETRYABLE_AVAILABLE","RELEASED_AVAILABLE"}
}

def eligible_packet(p):
    if not RUNTIME_GATE.get("enabled"): return False
    if p.get("assignment_work_kind") not in set(
        RUNTIME_GATE.get("allowed_work_kinds") or []
    ): return False
    if p.get("assignment_source_id") not in set(
        RUNTIME_GATE.get("allowed_seed_ids") or []
    ): return False
    if p.get("slot_id") not in claimable_slots: return False
    eligible=parse_ts(p.get("eligible_at") or p.get("issued_at"))
    hard=parse_ts(p.get("hard_expire_at"))
    if not now: return False
    if eligible and now<eligible: return False
    if hard and now>hard: return False
    return True

primary_by_worker={}
for p in PRIMARY:
    if eligible_packet(p):
        primary_by_worker.setdefault(p.get("worker_id"),[]).append(p)
steal_by_worker={}
for p in STEALS:
    if eligible_packet(p):
        steal_by_worker.setdefault(p.get("worker_id"),[]).append(p)
for d in (primary_by_worker,steal_by_worker):
    for wid in d:
        d[wid].sort(key=lambda x:(int(x.get("steal_rank") or 0),x.get("slot_id") or "",x.get("dispatch_ticket_id") or ""))

current=[]
status_rows=[]
used_slots=set()
ttl=int(POL.get("activation_ttl_minutes",30))
ready_states=set(POL.get("eligible_presence_states") or ["READY_FRESH"])

for wid in sorted(pres_by_worker):
    ps=pres_by_worker[wid]
    if wid in active_workers:
        status_rows.append({"worker_id":wid,"activation_state":"ACTIVE_CLAIM","presence_state":ps.get("presence_state"),"activation_id":None,"reason":"V11 active claim is authoritative."})
        continue
    if not RUNTIME_GATE.get("enabled"):
        status_rows.append({
          "worker_id":wid,
          "activation_state":"PAUSED_BY_RUNTIME_POLICY",
          "presence_state":ps.get("presence_state"),
          "activation_id":None,
          "reason":(
            "Generated activation disabled: "
            + str(RUNTIME_GATE.get("reason") or "runtime_gate_blocked")
          )
        })
        continue
    if len(current)>=int(RUNTIME_GATE.get("maximum_current_activations") or 0):
        status_rows.append({
          "worker_id":wid,
          "activation_state":"CANARY_CAPACITY_HELD",
          "presence_state":ps.get("presence_state"),
          "activation_id":None,
          "reason":"Approved measurement-canary activation capacity is already reserved."
        })
        continue
    if ps.get("presence_state") not in ready_states:
        status_rows.append({"worker_id":wid,"activation_state":"WAITING_PRESENCE","presence_state":ps.get("presence_state"),"activation_id":None,"reason":"Fresh READY presence is required for generated activation."})
        continue
    choices=[]
    if primary_by_worker.get(wid): choices.extend(primary_by_worker[wid])
    if steal_by_worker.get(wid): choices.extend(steal_by_worker[wid])
    if not choices:
        status_rows.append({"worker_id":wid,"activation_state":"NO_ELIGIBLE_DISPATCH","presence_state":ps.get("presence_state"),"activation_id":None,"reason":"Worker is ready but has no eligible primary/work-steal packet."})
        continue
    # Primary first; then lower steal rank and stable slot/ticket ordering.
    choices.sort(key=lambda x:(0 if (x.get("dispatch_kind") or "primary")=="primary" else 1,int(x.get("steal_rank") or 0),x.get("slot_id") or "",x.get("dispatch_ticket_id") or ""))
    packet=next((x for x in choices if x.get("slot_id") not in used_slots),None)
    if not packet:
        status_rows.append({"worker_id":wid,"activation_state":"NO_ELIGIBLE_DISPATCH","presence_state":ps.get("presence_state"),"activation_id":None,"reason":"Eligible packets were already reserved in this activation generation."})
        continue
    pexp=parse_ts(ps.get("presence_expires_at"))
    dexp=parse_ts(packet.get("hard_expire_at"))
    local_exp=None if not now else now+timedelta(minutes=ttl)
    expires=min([x for x in [pexp,dexp,local_exp] if x is not None])
    payload={
      "worker_id":wid,
      "presence_generation_id":ps["presence_generation_id"],
      "presence_event_id":ps.get("latest_event_id"),
      "dispatch_ticket_id":packet["dispatch_ticket_id"],
      "dispatch_generation_id":packet["dispatch_generation_id"],
      "slot_id":packet["slot_id"],
      "assignment_id":packet["assignment_id"],
      "runtime_approval_id":RUNTIME_GATE.get("approval_id"),
      "runtime_approval_record_sha256":RUNTIME_GATE.get("approval_record_sha256")
    }
    aid=activation_id(payload)
    row={
      **packet,
      "activation_id":aid,
      "presence_generation_id":ps["presence_generation_id"],
      "presence_event_id":ps.get("latest_event_id"),
      "presence_expires_at":ps.get("presence_expires_at"),
      "issued_at_activation":fmt(now),
      "expires_at":fmt(expires),
      "activation_status":"CURRENT",
      "runtime_approval_id":RUNTIME_GATE.get("approval_id"),
      "runtime_approval_record_sha256":RUNTIME_GATE.get("approval_record_sha256")
    }
    current.append(row)
    used_slots.add(packet["slot_id"])
    status_rows.append({"worker_id":wid,"activation_state":"READY_TO_CLAIM","presence_state":ps.get("presence_state"),"activation_id":aid,"slot_id":packet["slot_id"],"dispatch_ticket_id":packet["dispatch_ticket_id"],"reason":"Fresh READY presence intersects an eligible dispatch packet."})

fingerprint=json.dumps({
  "head_sha":head_sha,
  "presence_generation":next(iter({x.get("presence_generation_id") for x in PRES}),None),
  "rows":[(x["activation_id"],x["worker_id"],x["slot_id"],x["dispatch_ticket_id"],x["presence_event_id"],x["expires_at"]) for x in current]
},sort_keys=True)
gen="ACTGEN:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in current: x["activation_generation_id"]=gen
for x in status_rows: x["activation_generation_id"]=gen

hist={x["activation_id"]:x for x in HISTORY if x.get("activation_id")}
for x in current:
    if x["activation_id"] not in hist:
        hist[x["activation_id"]]={**x,"activation_status":"ISSUED"}
history=sorted(hist.values(),key=lambda x:x["activation_id"])

claim_packets=[]
for x in current:
    claim_packets.append({
      **x,
      "claim_schema_version":int(POL.get("minimum_claim_schema_version",16))
    })

def write_jsonl(name,rows):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")

write_jsonl("activation_directives.jsonl",status_rows)
write_jsonl("activation_claim_packets.jsonl",claim_packets)
write_jsonl("activation_history.jsonl",history)

metrics={
  "schema_version":1,
  "activation_generation_id":gen,
  "clock_commit_sha":head_sha,
  "clock_timestamp":fmt(now),
  "registered_workers":len(PRES),
  "fresh_ready_workers":sum(1 for x in PRES if x.get("presence_state")=="READY_FRESH"),
  "current_activations":len(current),
  "history_activations":len(history),
  "waiting_presence":sum(1 for x in status_rows if x.get("activation_state")=="WAITING_PRESENCE"),
  "active_claim_workers":sum(1 for x in status_rows if x.get("activation_state")=="ACTIVE_CLAIM"),
  "ready_without_dispatch":sum(1 for x in status_rows if x.get("activation_state")=="NO_ELIGIBLE_DISPATCH"),
  "runtime_mode":RUNTIME_GATE.get("mode"),
  "runtime_activation_enabled":bool(RUNTIME_GATE.get("enabled")),
  "runtime_gate_reason":RUNTIME_GATE.get("reason"),
  "runtime_gate_errors":RUNTIME_GATE.get("errors") or [],
  "runtime_approval_id":RUNTIME_GATE.get("approval_id"),
  "runtime_approval_record_sha256":RUNTIME_GATE.get("approval_record_sha256"),
  "runtime_maximum_current_activations":int(RUNTIME_GATE.get("maximum_current_activations") or 0),
  "runtime_maximum_total_claims":int(RUNTIME_GATE.get("maximum_total_claims") or 0),
  "runtime_claims_consumed":int(RUNTIME_GATE.get("claims_consumed") or 0),
  "runtime_remaining_claim_budget":int(RUNTIME_GATE.get("remaining_claim_budget") or 0),
  "runtime_active_claims":int(RUNTIME_GATE.get("active_claims") or 0),
  "runtime_allowed_seed_ids":RUNTIME_GATE.get("allowed_seed_ids") or [],
  "runtime_approved_packet_ids":RUNTIME_GATE.get("approved_packet_ids") or [],
  "runtime_approved_seed_ids":RUNTIME_GATE.get("approved_seed_ids") or [],
  "runtime_claimed_seed_ids":RUNTIME_GATE.get("claimed_seed_ids") or []
}
(INTEL/"activation_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=["# WORKER ACTIVATION BOARD","",f"Generation: **{gen}**",f"Clock: **{fmt(now)}**","",
        f"Runtime mode: **{RUNTIME_GATE.get('mode')}**. Generated activation enabled: **{str(bool(RUNTIME_GATE.get('enabled'))).lower()}**.",
        f"Runtime gate reason: **{RUNTIME_GATE.get('reason')}**.",
        "V16 activation is pull-based. Routing can exist without activation; generated claiming additionally requires explicit runtime authorization and fresh READY presence.","",
        "| Worker | Presence | Activation state | Slot | Activation |","|---|---|---|---|---|"]
for x in status_rows:
    report.append(f"| {x['worker_id']} | {x.get('presence_state') or '—'} | **{x['activation_state']}** | {x.get('slot_id') or '—'} | {x.get('activation_id') or '—'} |")
report += ["",f"Current activations: **{len(current)}**. Unknown/stale/offline presence is capacity uncertainty, not negative worker evidence.",""]
(INTEL/"ACTIVATION_BOARD.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(metrics))
