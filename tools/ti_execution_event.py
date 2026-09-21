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

def append_event(slot,event):
    path=INTEL/"execution_events"/f"{slot}.jsonl"
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,ensure_ascii=False)+"\n")
    return path

def select_dispatch(worker,slot,steal=False,dispatch_ticket=None,activation_id=None):
    pool=load_jsonl("activation_claim_packets.jsonl") if (INTEL/"activation_claim_packets.jsonl").exists() else []
    matches=[x for x in pool if x.get("worker_id")==worker and x.get("slot_id")==slot]
    if dispatch_ticket:
        matches=[x for x in matches if x.get("dispatch_ticket_id")==dispatch_ticket]
    elif steal:
        matches=[x for x in matches if x.get("dispatch_kind")=="work_steal"]
    else:
        matches=[x for x in matches if (x.get("dispatch_kind") or "primary")=="primary"]
    if activation_id:
        matches=[x for x in matches if x.get("activation_id")==activation_id]
    if not matches:
        return None
    matches.sort(key=lambda x:(int(x.get("steal_rank") or 0),x.get("dispatch_ticket_id") or ""))
    return matches[0]

def main():
    p=argparse.ArgumentParser(description="Append one local V19 execution event. Generated claims require a current V16 activation packet.")
    sub=p.add_subparsers(dest="cmd",required=True)
    for name in ["claim","heartbeat","start","complete","fail","release"]:
        sp=sub.add_parser(name)
        sp.add_argument("--slot",required=True)
        sp.add_argument("--worker",required=True)
        if name=="claim":
            sp.add_argument("--lease-minutes",type=int)
            sp.add_argument("--manual-override-reason")
            sp.add_argument("--steal",action="store_true")
            sp.add_argument("--dispatch-ticket")
            sp.add_argument("--activation-id")
        if name=="heartbeat":
            sp.add_argument("--extend-minutes",type=int)
        if name=="complete":
            sp.add_argument("--search-run-id",required=True)
        if name=="fail":
            sp.add_argument("--failure-code",required=True)
            sp.add_argument("--retryable",action="store_true")
    args=p.parse_args()

    policy=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
    dispatch_policy=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8")) if (INTEL/"dispatch_policy.json").exists() else {}
    states,_,_=build_execution_state(write=False)
    state={x["slot_id"]:x for x in states}.get(args.slot)
    if not state:
        raise SystemExit(f"unknown slot {args.slot}")
    ts=now_iso()

    if args.cmd=="claim":
        if state["status"] not in set(policy.get("claimable_states") or []):
            raise SystemExit(f"slot {args.slot} is not claimable: {state['status']}")
        active=[
          x for x in states
          if x.get("worker_id")==args.worker and x.get("status") in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"}
        ]
        if active:
            raise SystemExit(f"worker {args.worker} already has active claim {active[0].get('claim_id')}")
        alloc={x["slot_id"]:x for x in load_jsonl("hunt_allocations.jsonl")}[args.slot]
        lease=args.lease_minutes or int(policy.get("default_lease_minutes",120))
        seed=f"{ts}|{args.slot}|{args.worker}|{alloc['assignment_id']}"
        cid="CLAIM:"+short_hash(seed)
        event={
          "event_id":"EXEC:"+short_hash("CLAIM|"+seed),
          "event_type":"CLAIM","timestamp":ts,"slot_id":args.slot,
          "claim_id":cid,"worker_id":args.worker,
          "claim_schema_version":int(dispatch_policy.get("minimum_v19_claim_schema_version",19)),
          "assignment_id":alloc["assignment_id"],
          "allocator_generation_id":alloc["allocator_generation_id"],
          "portfolio_policy_generation_id":alloc["portfolio_policy_generation_id"],
          "work_item_id":alloc["work_item_id"],
          "assignment_slot_role":alloc["slot_role"],
          "assignment_work_kind":alloc["work_kind"],
          "assignment_source_id":alloc["source_id"],
          "assignment_score":alloc["final_score"],
          "lease_minutes":lease
        }
        if args.manual_override_reason:
            event["routing_mode"]="manual_override"
            event["route_override_reason"]=args.manual_override_reason
            event["dispatch_kind"]=None
            event["parent_dispatch_ticket_id"]=None
        else:
            dispatch=select_dispatch(args.worker,args.slot,args.steal,args.dispatch_ticket,args.activation_id)
            if not dispatch:
                raise SystemExit("no matching current V19 activation packet; publish READY presence or use --manual-override-reason")
            now=now_dt()
            eligible=parse_ts(dispatch.get("eligible_at") or dispatch.get("issued_at"))
            hard=parse_ts(dispatch.get("hard_expire_at"))
            activation_exp=parse_ts(dispatch.get("expires_at"))
            if eligible and now<eligible:
                raise SystemExit("dispatch ticket is not eligible yet")
            if hard and now>hard:
                raise SystemExit("dispatch ticket has hard-expired")
            if activation_exp and now>activation_exp:
                raise SystemExit("V16 activation has expired")
            for key in [
              "dispatch_ticket_id","dispatch_generation_id","routing_generation_id",
              "worker_profile_generation_id","routing_learning_generation_id","routing_score",
              "routing_exploration_generation_id","routing_exploration_pair_id",
              "baseline_slot_id","route_mode",
              "dispatch_kind","parent_dispatch_ticket_id",
              "presence_generation_id","presence_event_id",
              "activation_id","activation_generation_id"
            ]:
                event[key]=dispatch.get(key)
            event["routing_mode"]="generated"
    else:
        if state["status"] not in {"CLAIMED","RUNNING","CLAIMED_SUPERSEDED","RUNNING_SUPERSEDED"}:
            raise SystemExit(f"slot {args.slot} has no active claim: {state['status']}")
        if state.get("worker_id")!=args.worker:
            raise SystemExit(f"slot {args.slot} is owned by {state.get('worker_id')}")
        cid=state["claim_id"]
        seed=f"{ts}|{args.slot}|{args.worker}|{cid}|{args.cmd}"
        event={"event_id":"EXEC:"+short_hash(seed),"event_type":args.cmd.upper(),
               "timestamp":ts,"slot_id":args.slot,"claim_id":cid,"worker_id":args.worker}
        if args.cmd=="heartbeat":
            event["extend_minutes"]=args.extend_minutes or int(policy.get("heartbeat_extension_minutes",120))
        elif args.cmd=="complete":
            event["search_run_id"]=args.search_run_id
        elif args.cmd=="fail":
            event["failure_code"]=args.failure_code
            event["retryable"]=bool(args.retryable)

    path=append_event(args.slot,event)
    print(json.dumps({"path":str(path),"event":event},indent=2))

if __name__=="__main__":
    main()
