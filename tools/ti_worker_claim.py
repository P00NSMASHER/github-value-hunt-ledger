#!/usr/bin/env python3
import argparse, hashlib, json
from datetime import datetime, timezone
from ti_common import INTEL, load_jsonl
from ti_execution import build_execution_state

def now_dt():
    return datetime.now(timezone.utc)

def now_iso():
    return now_dt().isoformat().replace("+00:00","Z")

def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

def short_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]

def choose_packet(worker,steal=False,dispatch_ticket=None,activation_id=None):
    pool=load_jsonl("activation_claim_packets.jsonl") if (INTEL/"activation_claim_packets.jsonl").exists() else []
    matches=[x for x in pool if x.get("worker_id")==worker]
    if steal:
        matches=[x for x in matches if x.get("dispatch_kind")=="work_steal"]
    if dispatch_ticket:
        matches=[x for x in matches if x.get("dispatch_ticket_id")==dispatch_ticket]
    if activation_id:
        matches=[x for x in matches if x.get("activation_id")==activation_id]
    if not matches:
        raise SystemExit(f"no current V16 activation packet for {worker}; publish fresh READY presence first")
    matches.sort(key=lambda x:(0 if x.get("dispatch_kind")=="primary" else 1,int(x.get("steal_rank") or 0),x.get("slot_id") or "",x.get("activation_id") or ""))
    return matches[0]

def main():
    p=argparse.ArgumentParser(description="Claim one current V16 activated dispatch ticket for a registered worker.")
    p.add_argument("--worker",required=True)
    p.add_argument("--lease-minutes",type=int)
    p.add_argument("--steal",action="store_true",help="claim the highest-ranked eligible standby work-steal ticket")
    p.add_argument("--dispatch-ticket",help="claim one exact current primary or work-steal ticket")
    p.add_argument("--activation-id",help="claim one exact current V16 activation")
    args=p.parse_args()

    packet=choose_packet(args.worker,args.steal,args.dispatch_ticket,args.activation_id)
    states,_,_=build_execution_state(write=False)
    state_by_slot={x["slot_id"]:x for x in states}
    active=[
      x for x in states
      if x.get("worker_id")==args.worker and x.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"}
    ]
    if active:
        raise SystemExit(f"worker {args.worker} already has active claim {active[0].get('claim_id')}")
    state=state_by_slot.get(packet["slot_id"])
    if not state:
        raise SystemExit(f"unknown slot {packet['slot_id']}")
    policy=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
    if state["status"] not in set(policy.get("claimable_states") or []):
        raise SystemExit(f"dispatch slot is no longer claimable: {state['status']}")

    now=now_dt()
    eligible=parse_ts(packet.get("eligible_at") or packet.get("issued_at"))
    hard=parse_ts(packet.get("hard_expire_at"))
    activation_exp=parse_ts(packet.get("expires_at"))
    if eligible and now<eligible:
        raise SystemExit("dispatch ticket is not eligible yet")
    if hard and now>hard:
        raise SystemExit("dispatch ticket has hard-expired")
    if activation_exp and now>activation_exp:
        raise SystemExit("V16 activation has expired")

    ts=now.isoformat().replace("+00:00","Z")
    seed=f"{ts}|{args.worker}|{packet['slot_id']}|{packet['dispatch_ticket_id']}|{packet['activation_id']}"
    claim_id="CLAIM:"+short_hash(seed)
    event={
      "event_id":"EXEC:"+short_hash("CLAIM|"+seed),
      "event_type":"CLAIM",
      "timestamp":ts,
      "slot_id":packet["slot_id"],
      "claim_id":claim_id,
      "worker_id":args.worker,
      "claim_schema_version":int(packet.get("claim_schema_version") or 16),
      "assignment_id":packet["assignment_id"],
      "allocator_generation_id":packet["allocator_generation_id"],
      "portfolio_policy_generation_id":packet["portfolio_policy_generation_id"],
      "work_item_id":packet["work_item_id"],
      "assignment_slot_role":packet["assignment_slot_role"],
      "assignment_work_kind":packet["assignment_work_kind"],
      "assignment_source_id":packet["assignment_source_id"],
      "assignment_score":packet["assignment_score"],
      "lease_minutes":args.lease_minutes or int(policy.get("default_lease_minutes",120)),
      "routing_mode":"generated",
      "routing_generation_id":packet["routing_generation_id"],
      "worker_profile_generation_id":packet["worker_profile_generation_id"],
      "routing_learning_generation_id":packet.get("routing_learning_generation_id"),
      "routing_score":packet["routing_score"],
      "dispatch_ticket_id":packet["dispatch_ticket_id"],
      "dispatch_generation_id":packet["dispatch_generation_id"],
      "dispatch_kind":packet.get("dispatch_kind") or "primary",
      "parent_dispatch_ticket_id":packet.get("parent_dispatch_ticket_id"),
      "presence_generation_id":packet.get("presence_generation_id"),
      "presence_event_id":packet.get("presence_event_id"),
      "activation_id":packet.get("activation_id"),
      "activation_generation_id":packet.get("activation_generation_id")
    }
    if event["assignment_work_kind"]=="learning_measurement":
        packet_id=packet.get("learning_measurement_packet_id")
        packet_sha=packet.get("learning_measurement_packet_sha256")
        if not packet_id or not packet_sha:
            raise SystemExit("learning_measurement claim requires frozen packet id+sha256")
        event["learning_measurement_packet_id"]=packet_id
        event["learning_measurement_packet_sha256"]=packet_sha
    path=INTEL/"execution_events"/f"{packet['slot_id']}.jsonl"
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,ensure_ascii=False)+"\n")
    print(json.dumps({"path":str(path),"event":event},indent=2))

if __name__=="__main__":
    main()
