#!/usr/bin/env python3
import argparse, hashlib, json
from datetime import datetime, timezone
from ti_common import INTEL, load_jsonl
from ti_execution import build_execution_state

def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def short_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]

def main():
    p=argparse.ArgumentParser(description="Claim the V12-routed slot for one registered worker in a local checkout.")
    p.add_argument("--worker",required=True)
    p.add_argument("--lease-minutes",type=int)
    args=p.parse_args()

    routes={x["worker_id"]:x for x in load_jsonl("worker_routing.jsonl")}
    packets={x["worker_id"]:x for x in load_jsonl("worker_claim_packets.jsonl")}
    route=routes.get(args.worker)
    if not route: raise SystemExit(f"unknown worker {args.worker}")
    if route["route_status"]=="LOCKED":
        print(json.dumps({"status":"ALREADY_CLAIMED","route":route},indent=2)); return
    if route["route_status"]!="ROUTED":
        raise SystemExit(f"worker {args.worker} is not routed: {route['route_status']}")

    states,_,_=build_execution_state(write=False)
    state={x["slot_id"]:x for x in states}[route["slot_id"]]
    policy=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
    if state["status"] not in set(policy.get("claimable_states") or []):
        raise SystemExit(f"routed slot is no longer claimable: {state['status']}")

    packet=packets[args.worker]
    ts=now_iso()
    seed=f"{ts}|{args.worker}|{packet['slot_id']}|{packet['assignment_id']}|{packet['routing_generation_id']}"
    claim_id="CLAIM:"+short_hash(seed)
    event={
      "event_id":"EXEC:"+short_hash("CLAIM|"+seed),
      "event_type":"CLAIM","timestamp":ts,"slot_id":packet["slot_id"],"claim_id":claim_id,"worker_id":args.worker,
      "assignment_id":packet["assignment_id"],"allocator_generation_id":packet["allocator_generation_id"],
      "portfolio_policy_generation_id":packet["portfolio_policy_generation_id"],"work_item_id":packet["work_item_id"],
      "assignment_slot_role":packet["assignment_slot_role"],"assignment_work_kind":packet["assignment_work_kind"],
      "assignment_source_id":packet["assignment_source_id"],"assignment_score":packet["assignment_score"],
      "lease_minutes":args.lease_minutes or int(policy.get("default_lease_minutes",120)),
      "routing_generation_id":packet["routing_generation_id"],"worker_profile_generation_id":packet["worker_profile_generation_id"],
      "routing_score":packet["routing_score"]
    }
    path=INTEL/"execution_events"/f"{packet['slot_id']}.jsonl"
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,ensure_ascii=False)+"\n")
    print(json.dumps({"path":str(path),"event":event},indent=2))

if __name__=="__main__":
    main()
