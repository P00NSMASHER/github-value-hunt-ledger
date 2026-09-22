#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"activation_policy.json").read_text(encoding="utf-8"))
PRES=load_jsonl("worker_presence_state.jsonl")
DIR=load_jsonl("activation_directives.jsonl")
PACK=load_jsonl("activation_claim_packets.jsonl")
HIST=load_jsonl("activation_history.jsonl")
MET=json.loads((INTEL/"activation_metrics.json").read_text(encoding="utf-8"))

pres={x["worker_id"]:x for x in PRES}
if {x["worker_id"] for x in DIR}!={x["worker_id"] for x in PRES}:
    raise SystemExit("activation directives must contain every presence worker exactly once")
if len({x["worker_id"] for x in DIR})!=len(DIR):
    raise SystemExit("duplicate activation directive worker")
ids=set(); workers=set(); slots=set()
for n,x in enumerate(PACK,1):
    aid=x.get("activation_id"); wid=x.get("worker_id"); slot=x.get("slot_id")
    if not aid or aid in ids: raise SystemExit(f"activation_claim_packets.jsonl:{n}: duplicate/missing activation_id")
    ids.add(aid)
    if wid in workers or slot in slots: raise SystemExit(f"activation_claim_packets.jsonl:{n}: duplicate worker/slot")
    workers.add(wid); slots.add(slot)
    p=pres.get(wid)
    if not p or p.get("presence_state") not in set(POL.get("eligible_presence_states") or []):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: activation without fresh ready presence")
    if x.get("presence_generation_id")!=p.get("presence_generation_id") or x.get("presence_event_id")!=p.get("latest_event_id"):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: presence binding drift")
    if int(x.get("claim_schema_version") or 0)<int(POL.get("minimum_claim_schema_version",16)):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: claim schema below V16 minimum")
    if x.get("assignment_work_kind")=="learning_measurement":
        for key in ("learning_measurement_packet_id","learning_measurement_packet_sha256"):
            if not x.get(key):
                raise SystemExit(f"activation_claim_packets.jsonl:{n}: learning measurement missing {key}")
hist={x.get("activation_id"):x for x in HIST}
if len(hist)!=len(HIST): raise SystemExit("activation history duplicate IDs")
for x in PACK:
    if x["activation_id"] not in hist: raise SystemExit(f"activation history missing {x['activation_id']}")
gens={x.get("activation_generation_id") for x in DIR}
if len(gens)!=1 or MET.get("activation_generation_id")!=next(iter(gens)):
    raise SystemExit("activation generation mismatch")
if MET.get("current_activations")!=len(PACK) or MET.get("history_activations")!=len(HIST):
    raise SystemExit("activation metrics count drift")
print(f"OK activation_generation={MET.get('activation_generation_id')} current={len(PACK)} waiting_presence={MET.get('waiting_presence')}")
