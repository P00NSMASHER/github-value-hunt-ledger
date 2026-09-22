#!/usr/bin/env python3
import hashlib, json
from collections import Counter
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8"))
ROUTES=load_jsonl("worker_routing.jsonl")
PACKETS=load_jsonl("worker_claim_packets.jsonl")
TICKETS=load_jsonl("dispatch_tickets.jsonl")
HISTORY=load_jsonl("dispatch_ticket_history.jsonl")
CLAIM_PACKETS=load_jsonl("dispatch_claim_packets.jsonl")
STATE=load_jsonl("execution_state.jsonl")
MET=json.loads((INTEL/"dispatch_metrics.json").read_text(encoding="utf-8"))

routes={x["worker_id"]:x for x in ROUTES}
packets={x["worker_id"]:x for x in PACKETS}
state={x["slot_id"]:x for x in STATE}
valid_states=set(POL.get("ticket_valid_execution_states") or [])

def stable_payload(p):
    payload = {
      "dispatch_kind":"primary",
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
      "routing_score":p["routing_score"]
    }
    if p.get("assignment_work_kind")=="learning_measurement":
        packet_id=p.get("learning_measurement_packet_id")
        packet_sha=p.get("learning_measurement_packet_sha256")
        if not packet_id or not packet_sha:
            raise SystemExit("learning_measurement worker packet missing frozen packet binding")
        payload["learning_measurement_packet_id"]=packet_id
        payload["learning_measurement_packet_sha256"]=packet_sha
    return payload

def expected_id(p):
    raw=json.dumps(stable_payload(p),sort_keys=True,separators=(",",":"))
    return "DISPATCH:"+hashlib.sha256(raw.encode()).hexdigest()[:12]

routed={w:r for w,r in routes.items() if r.get("route_status")=="ROUTED"}
if len(TICKETS)!=len(routed):
    raise SystemExit("current dispatch ticket count must equal routed worker count")
if len(CLAIM_PACKETS)!=len(TICKETS):
    raise SystemExit("dispatch claim packet count drift")

seen_worker=set(); seen_slot=set(); seen_id=set()
for n,t in enumerate(TICKETS,1):
    wid=t.get("worker_id"); slot=t.get("slot_id"); did=t.get("dispatch_ticket_id")
    if wid in seen_worker or slot in seen_slot or did in seen_id:
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: duplicate worker/slot/ticket")
    seen_worker.add(wid); seen_slot.add(slot); seen_id.add(did)
    if wid not in routed:
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: ticket for non-routed worker {wid}")
    p=packets.get(wid)
    if not p:
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: missing source worker claim packet")
    if did!=expected_id(p):
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: deterministic ticket ID mismatch")
    if int(t.get("ticket_schema_version") or 0)<15 or t.get("dispatch_kind")!="primary":
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: current primary ticket must be V15")
    if not t.get("issued_at") or not t.get("soft_stale_at") or not t.get("hard_expire_at"):
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: V15 lifecycle timestamps missing")
    if slot!=p.get("slot_id") or t.get("assignment_id")!=p.get("assignment_id"):
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: packet binding drift")
    if t.get("assignment_work_kind")=="learning_measurement":
        for key in ("learning_measurement_packet_id","learning_measurement_packet_sha256"):
            if not t.get(key) or t.get(key)!=p.get(key):
                raise SystemExit(f"dispatch_tickets.jsonl:{n}: learning packet binding drift: {key}")
    if state.get(slot,{}).get("status") not in valid_states:
        raise SystemExit(f"dispatch_tickets.jsonl:{n}: non-claimable execution state")

hist={x.get("dispatch_ticket_id"):x for x in HISTORY}
if len(hist)!=len(HISTORY):
    raise SystemExit("dispatch ticket history contains duplicate IDs")
for t in TICKETS:
    if t["dispatch_ticket_id"] not in hist:
        raise SystemExit(f"current ticket missing from history {t['dispatch_ticket_id']}")

cp={x["worker_id"]:x for x in CLAIM_PACKETS}
for t in TICKETS:
    p=cp.get(t["worker_id"])
    if not p:
        raise SystemExit(f"missing dispatch claim packet for {t['worker_id']}")
    if p.get("dispatch_ticket_id")!=t.get("dispatch_ticket_id"):
        raise SystemExit(f"claim packet ticket mismatch for {t['worker_id']}")
    if t.get("assignment_work_kind")=="learning_measurement":
        for key in ("learning_measurement_packet_id","learning_measurement_packet_sha256"):
            if p.get(key)!=t.get(key):
                raise SystemExit(f"dispatch claim packet learning binding drift for {t['worker_id']}: {key}")
    if p.get("routing_mode")!="generated":
        raise SystemExit(f"claim packet routing_mode must be generated for {t['worker_id']}")
    if int(p.get("claim_schema_version") or 0)<int(POL.get("minimum_v15_claim_schema_version",15)):
        raise SystemExit(f"claim packet schema below V15 minimum for {t['worker_id']}")
    if p.get("dispatch_kind")!="primary":
        raise SystemExit(f"primary claim packet dispatch_kind drift for {t['worker_id']}")

gens={x.get("dispatch_generation_id") for x in TICKETS}
if len(gens)>1:
    raise SystemExit("multiple dispatch generations in current tickets")
if TICKETS and MET.get("dispatch_generation_id")!=next(iter(gens)):
    raise SystemExit("dispatch metrics generation mismatch")
if MET.get("current_tickets")!=len(TICKETS) or MET.get("history_tickets")!=len(HISTORY):
    raise SystemExit("dispatch metrics count drift")
print(f"OK dispatch_generation={MET.get('dispatch_generation_id')} current={len(TICKETS)} history={len(HISTORY)}")
