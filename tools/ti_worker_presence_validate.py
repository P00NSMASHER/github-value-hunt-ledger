#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl

REG=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8"))
POL=json.loads((INTEL/"worker_presence_policy.json").read_text(encoding="utf-8"))
ROWS=load_jsonl("worker_presence_state.jsonl")
HIST=load_jsonl("worker_presence_history.jsonl")
MET=json.loads((INTEL/"worker_presence_metrics.json").read_text(encoding="utf-8"))

workers={x["worker_id"] for x in REG.get("workers",[])}
if {x["worker_id"] for x in ROWS}!=workers:
    raise SystemExit("presence state must contain exactly every registered worker")
if len({x["worker_id"] for x in ROWS})!=len(ROWS):
    raise SystemExit("duplicate worker presence state")
gens={x.get("presence_generation_id") for x in ROWS}
if len(gens)!=1 or MET.get("presence_generation_id")!=next(iter(gens)):
    raise SystemExit("presence generation mismatch")
seen=set()
for n,e in enumerate(HIST,1):
    eid=e.get("event_id")
    if not eid or eid in seen: raise SystemExit(f"worker_presence_history.jsonl:{n}: duplicate/missing event_id")
    seen.add(eid)
    if e.get("worker_id") not in workers: raise SystemExit(f"worker_presence_history.jsonl:{n}: unknown worker")
    if e.get("event_type") not in set(POL.get("event_types") or []): raise SystemExit(f"worker_presence_history.jsonl:{n}: invalid type")
if MET.get("presence_event_count")!=len(HIST) or MET.get("registered_workers")!=len(ROWS):
    raise SystemExit("presence metrics count drift")
print(f"OK workers={len(ROWS)} ready={MET.get('fresh_ready_workers')} events={len(HIST)}")
