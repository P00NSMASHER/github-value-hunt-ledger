#!/usr/bin/env python3
import hashlib, json, subprocess
from datetime import datetime, timezone, timedelta
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8"))
BPOL=json.loads((INTEL/"dispatch_backpressure_policy.json").read_text(encoding="utf-8"))
EXEC_POL=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
ROUTES=load_jsonl("worker_routing.jsonl")
PACKETS=load_jsonl("worker_claim_packets.jsonl")
STATE=load_jsonl("execution_state.jsonl")
HISTORY=load_jsonl("dispatch_ticket_history.jsonl") if (INTEL/"dispatch_ticket_history.jsonl").exists() else []

packet_by_worker={x["worker_id"]:x for x in PACKETS}
state_by_slot={x["slot_id"]:x for x in STATE}
valid_states=set(POL.get("ticket_valid_execution_states") or [])

def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
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

def stable_ticket_payload(packet):
    return {
      "dispatch_kind":"primary",
      "worker_id":packet["worker_id"],
      "routing_generation_id":packet["routing_generation_id"],
      "worker_profile_generation_id":packet["worker_profile_generation_id"],
      "routing_learning_generation_id":packet.get("routing_learning_generation_id"),
      "slot_id":packet["slot_id"],
      "assignment_id":packet["assignment_id"],
      "allocator_generation_id":packet["allocator_generation_id"],
      "portfolio_policy_generation_id":packet["portfolio_policy_generation_id"],
      "work_item_id":packet["work_item_id"],
      "assignment_slot_role":packet["assignment_slot_role"],
      "assignment_work_kind":packet["assignment_work_kind"],
      "assignment_source_id":packet["assignment_source_id"],
      "assignment_score":packet["assignment_score"],
      "routing_score":packet["routing_score"]
    }

def ticket_id(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return "DISPATCH:"+hashlib.sha256(raw.encode()).hexdigest()[:12]

head_sha,clock=git_clock()
soft_minutes=int(BPOL.get("claim_soft_sla_minutes",75))
hard_minutes=int(BPOL.get("claim_hard_expiry_minutes",150))
hist={x["dispatch_ticket_id"]:dict(x) for x in HISTORY if x.get("dispatch_ticket_id")}
tickets=[]
claim_packets=[]
errors=[]

for r in ROUTES:
    if r.get("route_status")!="ROUTED":
        continue
    wid=r["worker_id"]
    p=packet_by_worker.get(wid)
    if not p:
        errors.append(f"routed worker {wid} missing worker claim packet")
        continue
    s=state_by_slot.get(p["slot_id"])
    if not s:
        errors.append(f"routed worker {wid} targets unknown slot {p['slot_id']}")
        continue
    if s.get("status") not in valid_states:
        errors.append(f"routed worker {wid} targets non-ticketable state {s.get('status')} for {p['slot_id']}")
        continue
    payload=stable_ticket_payload(p)
    did=ticket_id(payload)
    old=hist.get(did)
    if old:
        issued_at=old.get("issued_at")
        soft_stale_at=old.get("soft_stale_at")
        hard_expire_at=old.get("hard_expire_at")
        issued_commit_sha=old.get("issued_commit_sha")
    elif clock:
        issued_at=fmt(clock)
        soft_stale_at=fmt(clock+timedelta(minutes=soft_minutes))
        hard_expire_at=fmt(clock+timedelta(minutes=hard_minutes))
        issued_commit_sha=head_sha
    else:
        issued_at=soft_stale_at=hard_expire_at=issued_commit_sha=None
    t={
      **payload,
      "dispatch_ticket_id":did,
      "ticket_schema_version":15,
      "worker_id":p["worker_id"],
      "routing_generation_id":p["routing_generation_id"],
      "worker_profile_generation_id":p["worker_profile_generation_id"],
      "routing_learning_generation_id":p.get("routing_learning_generation_id"),
      "slot_id":p["slot_id"],
      "assignment_id":p["assignment_id"],
      "allocator_generation_id":p["allocator_generation_id"],
      "portfolio_policy_generation_id":p["portfolio_policy_generation_id"],
      "work_item_id":p["work_item_id"],
      "assignment_slot_role":p["assignment_slot_role"],
      "assignment_work_kind":p["assignment_work_kind"],
      "assignment_source_id":p["assignment_source_id"],
      "assignment_score":p["assignment_score"],
      "routing_score":p["routing_score"],
      "claim_file":p["claim_file"],
      "issued_at":issued_at,
      "soft_stale_at":soft_stale_at,
      "hard_expire_at":hard_expire_at,
      "issued_commit_sha":issued_commit_sha,
      "ticket_status":"CURRENT",
      "execution_state_at_generation":s.get("status")
    }
    tickets.append(t)
    claim_packets.append({
      **t,
      "claim_schema_version":15,
      "routing_mode":"generated",
      "lease_minutes":int(EXEC_POL.get("default_lease_minutes",120))
    })

tickets=sorted(tickets,key=lambda x:(x["slot_id"],x["worker_id"]))
fingerprint=json.dumps([(x["dispatch_ticket_id"],x["worker_id"],x["slot_id"],x["assignment_id"]) for x in tickets],sort_keys=True)
dispatch_generation="DISPATCHGEN:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in tickets:
    x["dispatch_generation_id"]=dispatch_generation
for x in claim_packets:
    x["dispatch_generation_id"]=dispatch_generation

for t in tickets:
    old=hist.get(t["dispatch_ticket_id"])
    if old:
        stable_keys=[
          "dispatch_kind","worker_id","routing_generation_id","worker_profile_generation_id",
          "routing_learning_generation_id","slot_id","assignment_id","allocator_generation_id",
          "portfolio_policy_generation_id","work_item_id","assignment_slot_role",
          "assignment_work_kind","assignment_source_id","assignment_score","routing_score"
        ]
        drift=[k for k in stable_keys if old.get(k)!=t.get(k)]
        if drift:
            errors.append(f"historical dispatch ticket drift {t['dispatch_ticket_id']}: {','.join(drift)}")
    else:
        hist[t["dispatch_ticket_id"]]={**t,"ticket_status":"ISSUED"}

if errors:
    raise SystemExit("\n".join(errors))

history=sorted(hist.values(),key=lambda x:x["dispatch_ticket_id"])

def write_jsonl(name,rows):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")

write_jsonl("dispatch_tickets.jsonl",tickets)
write_jsonl("dispatch_ticket_history.jsonl",history)
write_jsonl("dispatch_claim_packets.jsonl",claim_packets)

metrics={
  "schema_version":2,
  "dispatch_generation_id":dispatch_generation,
  "clock_commit_sha":head_sha,
  "clock_timestamp":fmt(clock),
  "current_tickets":len(tickets),
  "history_tickets":len(history),
  "routed_workers":sum(1 for x in ROUTES if x.get("route_status")=="ROUTED"),
  "locked_workers":sum(1 for x in ROUTES if x.get("route_status")=="LOCKED"),
  "unassigned_workers":sum(1 for x in ROUTES if x.get("route_status")=="IDLE_UNASSIGNED")
}
(INTEL/"dispatch_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

board=[
 "# DISPATCH BOARD","",
 f"Dispatch generation: **{dispatch_generation}**","",
 "V15 primary tickets are time-aware and remain bound to the exact V12/V13 route.","",
 "| Worker | Slot | Assignment | Dispatch ticket | Routing score | Issued | Expires |",
 "|---|---|---|---|---:|---|---|"
]
for t in tickets:
    board.append(f"| {t['worker_id']} | {t['slot_id']} | {t['assignment_id']} | {t['dispatch_ticket_id']} | {t['routing_score']:.4f} | {t.get('issued_at') or '—'} | {t.get('hard_expire_at') or '—'} |")
if not tickets:
    board.append("| — | — | — | — | — | — | — |")
board += ["","Generated primary tickets use claim schema 15. Legacy V14 history is preserved without invented timestamps.",""]
(INTEL/"DISPATCH_BOARD.md").write_text("\n".join(board),encoding="utf-8")
print(json.dumps(metrics))
