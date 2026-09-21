#!/usr/bin/env python3
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from ti_common import INTEL

def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def short_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()[:12]

def main():
    p=argparse.ArgumentParser(description="Append one V16 worker presence event.")
    p.add_argument("event_type",choices=["READY","HEARTBEAT","BUSY","PAUSE","OFFLINE"])
    p.add_argument("--worker",required=True)
    p.add_argument("--ttl-minutes",type=int)
    p.add_argument("--notes")
    args=p.parse_args()
    pol=json.loads((INTEL/"worker_presence_policy.json").read_text(encoding="utf-8"))
    reg=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
    workers={x["worker_id"] for x in reg.get("workers",[])}
    if args.worker not in workers: raise SystemExit(f"unknown worker {args.worker}")
    max_ttl=int(pol.get("max_ttl_minutes",180))
    if args.ttl_minutes is not None and not (1<=args.ttl_minutes<=max_ttl):
        raise SystemExit(f"ttl-minutes must be 1..{max_ttl}")
    ts=now_iso()
    seed=f"{ts}|{args.worker}|{args.event_type}|{args.ttl_minutes}|{args.notes or ''}"
    event={
      "event_id":"PRESENCE:"+short_hash(seed),
      "event_type":args.event_type,
      "timestamp":ts,
      "worker_id":args.worker,
      "ttl_minutes":args.ttl_minutes,
      "notes":args.notes
    }
    path=INTEL/"worker_presence_events"/f"{args.worker}.jsonl"
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,ensure_ascii=False)+"\n")
    print(json.dumps({"path":str(path),"event":event},indent=2))

if __name__=="__main__":
    main()
