#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"dispatch_backpressure_policy.json").read_text(encoding="utf-8"))
PRIMARY=load_jsonl("dispatch_tickets.jsonl")
BACK=load_jsonl("dispatch_backpressure.jsonl")
STEAL=load_jsonl("work_steal_tickets.jsonl")
PACKETS=load_jsonl("work_steal_claim_packets.jsonl")
HISTORY=load_jsonl("dispatch_ticket_history.jsonl")
CANDS=load_jsonl("routing_candidates.jsonl")
STATE=load_jsonl("execution_state.jsonl")
MET=json.loads((INTEL/"dispatch_backpressure_metrics.json").read_text(encoding="utf-8"))
DMET=json.loads((INTEL/"dispatch_metrics.json").read_text(encoding="utf-8"))

def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

if len(BACK)!=len(PRIMARY):
    raise SystemExit("dispatch_backpressure must have one row per current primary ticket")
bp={x["dispatch_ticket_id"]:x for x in BACK}
if len(bp)!=len(BACK):
    raise SystemExit("duplicate dispatch_backpressure ticket")
for t in PRIMARY:
    if t["dispatch_ticket_id"] not in bp:
        raise SystemExit(f"missing backpressure row {t['dispatch_ticket_id']}")

hist={x.get("dispatch_ticket_id"):x for x in HISTORY}
if len(hist)!=len(HISTORY):
    raise SystemExit("dispatch ticket history contains duplicate IDs")
if DMET.get("history_tickets")!=len(HISTORY):
    raise SystemExit("dispatch_metrics history_tickets drift")
if DMET.get("current_work_steal_tickets")!=len(STEAL):
    raise SystemExit("dispatch_metrics current_work_steal_tickets drift")

cand={(x.get("worker_id"),x.get("slot_id")):x for x in CANDS}
state={x["slot_id"]:x for x in STATE}
parents={x["dispatch_ticket_id"]:x for x in PRIMARY}
claimable={"AVAILABLE","EXPIRED_AVAILABLE","RETRYABLE_AVAILABLE","RELEASED_AVAILABLE"}
seen=set()

for n,s in enumerate(STEAL,1):
    did=s.get("dispatch_ticket_id")
    if not did or did in seen:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: duplicate/missing ticket")
    seen.add(did)
    if s.get("dispatch_kind")!="work_steal":
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: wrong dispatch_kind")
    parent=parents.get(s.get("parent_dispatch_ticket_id"))
    if not parent:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: missing current parent")
    b=bp.get(parent["dispatch_ticket_id"])
    if not b or b.get("lifecycle_state")!="EXPIRED":
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: parent not hard-expired")
    if s.get("worker_id")==parent.get("worker_id"):
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: primary worker cannot steal own ticket")
    if state.get(s.get("slot_id"),{}).get("status") not in claimable:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: slot not claimable")
    edge=cand.get((s.get("worker_id"),s.get("slot_id")))
    if not edge:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: missing routing candidate edge")
    pscore=float(parent.get("routing_score") or 0)
    sscore=float(s.get("routing_score") or 0)
    if pscore>0 and sscore+1e-9 < pscore*float(POL.get("min_backup_score_ratio",0.75)):
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: backup routing score below threshold")
    if did not in hist:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: ticket missing from history")
    elig=parse_ts(s.get("eligible_at"))
    issued=parse_ts(s.get("issued_at"))
    hard=parse_ts(s.get("hard_expire_at"))
    if elig and issued and issued<elig:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: issued before parent expiry")
    if issued and hard and hard<=issued:
        raise SystemExit(f"work_steal_tickets.jsonl:{n}: invalid steal expiry")

packet_by_id={x.get("dispatch_ticket_id"):x for x in PACKETS}
if set(packet_by_id)!=seen:
    raise SystemExit("work-steal claim packet coverage drift")
for did,p in packet_by_id.items():
    if int(p.get("claim_schema_version") or 0)<15:
        raise SystemExit(f"work-steal packet {did} is pre-v15")
    if p.get("routing_mode")!="generated" or p.get("dispatch_kind")!="work_steal":
        raise SystemExit(f"work-steal packet {did} provenance drift")

if MET.get("primary_tickets")!=len(PRIMARY):
    raise SystemExit("backpressure primary count drift")
if MET.get("work_steal_tickets")!=len(STEAL):
    raise SystemExit("backpressure steal count drift")

print(f"OK primary={len(PRIMARY)} stale={MET.get('stale_primary')} expired={MET.get('expired_primary')} steal={len(STEAL)}")
