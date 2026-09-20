#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8"))
EXEC_POL=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
ROUTES=load_jsonl("worker_routing.jsonl")
PACKETS=load_jsonl("worker_claim_packets.jsonl")
STATE=load_jsonl("execution_state.jsonl")
HISTORY=load_jsonl("dispatch_ticket_history.jsonl") if (INTEL/"dispatch_ticket_history.jsonl").exists() else []

route_by_worker={x["worker_id"]:x for x in ROUTES}
packet_by_worker={x["worker_id"]:x for x in PACKETS}
state_by_slot={x["slot_id"]:x for x in STATE}
valid_states=set(POL.get("ticket_valid_execution_states") or [])

def stable_ticket_payload(packet):
    return {
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
    t={
      "dispatch_ticket_id":did,
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
      "ticket_status":"CURRENT",
      "execution_state_at_generation":s.get("status")
    }
    tickets.append(t)
    claim_packets.append({
      **t,
      "claim_schema_version":int(POL.get("minimum_claim_schema_version",14)),
      "routing_mode":"generated",
      "lease_minutes":int(EXEC_POL.get("default_lease_minutes",120))
    })

tickets=sorted(tickets,key=lambda x:(x["slot_id"],x["worker_id"]))
fingerprint=json.dumps([(x["dispatch_ticket_id"],x["worker_id"],x["slot_id"],x["assignment_id"]) for x in tickets],sort_keys=True)
dispatch_generation="DISPATCHGEN:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
for x in tickets: x["dispatch_generation_id"]=dispatch_generation
for x in claim_packets: x["dispatch_generation_id"]=dispatch_generation

hist={x["dispatch_ticket_id"]:x for x in HISTORY}
for t in tickets:
    old=hist.get(t["dispatch_ticket_id"])
    if old:
        keys=[k for k in t if k not in {"ticket_status","execution_state_at_generation","dispatch_generation_id"}]
        drift=[k for k in keys if old.get(k)!=t.get(k)]
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
  "schema_version":1,
  "dispatch_generation_id":dispatch_generation,
  "current_tickets":len(tickets),
  "history_tickets":len(history),
  "routed_workers":sum(1 for x in ROUTES if x.get("route_status")=="ROUTED"),
  "locked_workers":sum(1 for x in ROUTES if x.get("route_status")=="LOCKED"),
  "unassigned_workers":sum(1 for x in ROUTES if x.get("route_status")=="UNASSIGNED")
}
(INTEL/"dispatch_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

board=[
 "# DISPATCH BOARD","",
 f"Dispatch generation: **{dispatch_generation}**","",
 "Generated dispatch tickets bind V12/V13 routing decisions to V11 claims. A generated claim must present the exact ticket below.","",
 "| Worker | Slot | Assignment | Dispatch ticket | Routing score | Claim file |",
 "|---|---|---|---|---:|---|"
]
for t in tickets:
    board.append(f"| {t['worker_id']} | {t['slot_id']} | {t['assignment_id']} | {t['dispatch_ticket_id']} | {t['routing_score']:.4f} | {t['claim_file']} |")
if not tickets:
    board.append("| — | — | — | — | — | — |")
board += ["","## Claim modes","",
 "- **generated** — use the current dispatch ticket exactly; this is eligible for routing-learning attribution.",
 "- **manual_override** — allowed only with an explicit reason; it is excluded from generated-route learning.",
 "",
 "Current dispatch tickets are derived from claimable V11 slots only. Active/locked workers do not receive a new ticket.",
 ""]
(INTEL/"DISPATCH_BOARD.md").write_text("\n".join(board),encoding="utf-8")
print(json.dumps(metrics))
