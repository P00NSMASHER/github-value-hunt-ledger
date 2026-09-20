#!/usr/bin/env python3
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from ti_common import INTEL, load_jsonl
from ti_execution import build_execution_state

def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def short_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]

def append_event(slot,event):
    path=INTEL/"execution_events"/f"{slot}.jsonl"
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,ensure_ascii=False)+"\n")
    return path

def main():
    p=argparse.ArgumentParser(description="Append one local V11 execution event. Commit/push atomically after review.")
    sub=p.add_subparsers(dest="cmd",required=True)
    for name in ["claim","heartbeat","start","complete","fail","release"]:
        sp=sub.add_parser(name)
        sp.add_argument("--slot",required=True)
        sp.add_argument("--worker",required=True)
        if name=="claim":
            sp.add_argument("--lease-minutes",type=int)
        if name=="heartbeat":
            sp.add_argument("--extend-minutes",type=int)
        if name=="complete":
            sp.add_argument("--search-run-id",required=True)
        if name=="fail":
            sp.add_argument("--failure-code",required=True)
            sp.add_argument("--retryable",action="store_true")
    args=p.parse_args()

    policy=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
    states,claims,_=build_execution_state(write=False)
    state={x["slot_id"]:x for x in states}.get(args.slot)
    if not state:
        raise SystemExit(f"unknown slot {args.slot}")
    ts=now_iso()

    if args.cmd=="claim":
        if state["status"] not in set(policy.get("claimable_states") or []):
            raise SystemExit(f"slot {args.slot} is not claimable: {state['status']}")
        alloc={x["slot_id"]:x for x in load_jsonl("hunt_allocations.jsonl")}[args.slot]
        lease=args.lease_minutes or int(policy.get("default_lease_minutes",120))
        seed=f"{ts}|{args.slot}|{args.worker}|{alloc['assignment_id']}"
        cid="CLAIM:"+short_hash(seed)
        event={
          "event_id":"EXEC:"+short_hash("CLAIM|"+seed),
          "event_type":"CLAIM","timestamp":ts,"slot_id":args.slot,
          "claim_id":cid,"worker_id":args.worker,
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
