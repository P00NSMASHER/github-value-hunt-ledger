#!/usr/bin/env python3
import json
from collections import Counter
from datetime import datetime, timezone
from ti_common import INTEL, load_jsonl

policy=json.loads((INTEL/"execution_policy.json").read_text(encoding="utf-8"))
dispatch_policy=json.loads((INTEL/"dispatch_policy.json").read_text(encoding="utf-8")) if (INTEL/"dispatch_policy.json").exists() else {}
dispatch_history=load_jsonl("dispatch_ticket_history.jsonl") if (INTEL/"dispatch_ticket_history.jsonl").exists() else []
dispatch_by_id={x.get("dispatch_ticket_id"):x for x in dispatch_history if x.get("dispatch_ticket_id")}
activation_policy=json.loads((INTEL/"activation_policy.json").read_text(encoding="utf-8")) if (INTEL/"activation_policy.json").exists() else {}
activation_history=load_jsonl("activation_history.jsonl") if (INTEL/"activation_history.jsonl").exists() else []
activation_by_id={x.get("activation_id"):x for x in activation_history if x.get("activation_id")}
min_v16_claim_schema=int(activation_policy.get("minimum_claim_schema_version",16))
activation_legacy_claim_ids=set(activation_policy.get("legacy_claim_ids") or [])
legacy_claim_ids=set(dispatch_policy.get("legacy_claim_ids") or [])
min_claim_schema=int(dispatch_policy.get("minimum_claim_schema_version",14))
min_v15_claim_schema=int(dispatch_policy.get("minimum_v15_claim_schema_version",15))
worker_registry=json.loads((INTEL/"worker_registry.json").read_text(encoding="utf-8")) if (INTEL/"worker_registry.json").exists() else {"workers":[]}
registered_workers={w["worker_id"] for w in worker_registry.get("workers",[])}
def parse_ts(value):
    if not value:
        return None
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

alloc=load_jsonl("hunt_allocations.jsonl")
states=load_jsonl("execution_state.jsonl")
claims=load_jsonl("execution_claim_history.jsonl")
runs=load_jsonl("search_runs.jsonl")
metrics=json.loads((INTEL/"execution_metrics.json").read_text(encoding="utf-8"))

alloc_by_slot={x["slot_id"]:x for x in alloc}
if len(states)!=len(alloc):
    raise SystemExit("execution state must contain exactly one row per allocation slot")
seen_slots=set()
for n,s in enumerate(states,1):
    slot=s.get("slot_id")
    if slot in seen_slots or slot not in alloc_by_slot:
        raise SystemExit(f"execution_state.jsonl:{n}: invalid/duplicate slot {slot}")
    seen_slots.add(slot)
    a=alloc_by_slot[slot]
    if s.get("current_assignment_id")!=a.get("assignment_id"):
        raise SystemExit(f"execution_state.jsonl:{n}: current assignment drift")
    if s.get("current_work_item_id")!=a.get("work_item_id"):
        raise SystemExit(f"execution_state.jsonl:{n}: work item drift")

claim_by_id={}
active_workers=Counter()
for n,c in enumerate(claims,1):
    cid=c.get("claim_id")
    if not cid or cid in claim_by_id:
        raise SystemExit(f"execution_claim_history.jsonl:{n}: missing/duplicate claim_id")
    claim_by_id[cid]=c
    claim_schema=int(c.get("claim_schema_version") or 0)
    if cid not in legacy_claim_ids:
        is_pre_v16_claim=cid in activation_legacy_claim_ids
        if activation_policy and not is_pre_v16_claim and claim_schema<min_v16_claim_schema:
            raise SystemExit(f"execution_claim_history.jsonl:{n}: non-legacy claim below V16 schema")
        if claim_schema<min_claim_schema:
            raise SystemExit(f"execution_claim_history.jsonl:{n}: non-legacy claim below V14 schema")
        if c.get("routing_mode")=="generated":
            did=c.get("dispatch_ticket_id")
            ticket=dispatch_by_id.get(did)
            if not ticket:
                raise SystemExit(f"execution_claim_history.jsonl:{n}: generated claim missing historical dispatch ticket")
            ticket_schema=int(ticket.get("ticket_schema_version") or 0)
            if ticket_schema>=15 and claim_schema<min_v15_claim_schema:
                raise SystemExit(f"execution_claim_history.jsonl:{n}: V15 ticket requires schema {min_v15_claim_schema}+ claim")
            exact={
              "worker_id":c.get("worker_id"),"slot_id":c.get("slot_id"),"assignment_id":c.get("assignment_id"),
              "allocator_generation_id":c.get("allocator_generation_id"),"portfolio_policy_generation_id":c.get("portfolio_policy_generation_id"),
              "work_item_id":c.get("work_item_id"),"routing_generation_id":c.get("routing_generation_id"),
              "worker_profile_generation_id":c.get("worker_profile_generation_id"),
              "routing_learning_generation_id":c.get("routing_learning_generation_id"),
              "dispatch_generation_id":c.get("dispatch_generation_id")
            }
            if c.get("assignment_work_kind")=="learning_measurement":
                for key in ("learning_measurement_packet_id","learning_measurement_packet_sha256"):
                    if not c.get(key):
                        raise SystemExit(f"execution_claim_history.jsonl:{n}: learning measurement missing {key}")
                    exact[key]=c.get(key)
            if ticket_schema>=15:
                exact["dispatch_kind"]=c.get("dispatch_kind")
                exact["parent_dispatch_ticket_id"]=c.get("parent_dispatch_ticket_id")
            drift=[k for k,v in exact.items() if ticket.get(k)!=v]
            if drift:
                raise SystemExit(f"execution_claim_history.jsonl:{n}: dispatch history drift {','.join(drift)}")
            if ticket_schema>=15:
                claimed=parse_ts(c.get("claimed_at"))
                eligible=parse_ts(ticket.get("eligible_at") or ticket.get("issued_at"))
                hard=parse_ts(ticket.get("hard_expire_at"))
                if claimed and eligible and claimed<eligible:
                    raise SystemExit(f"execution_claim_history.jsonl:{n}: claim before dispatch eligibility")
                if claimed and hard and claimed>hard:
                    raise SystemExit(f"execution_claim_history.jsonl:{n}: claim after dispatch hard expiry")
            if activation_policy and not is_pre_v16_claim and claim_schema>=min_v16_claim_schema:
                aid=c.get("activation_id")
                act=activation_by_id.get(aid)
                if not act:
                    raise SystemExit(f"execution_claim_history.jsonl:{n}: generated claim missing V16 activation")
                exact_act={
                  "worker_id":c.get("worker_id"),"slot_id":c.get("slot_id"),
                  "dispatch_ticket_id":c.get("dispatch_ticket_id"),"dispatch_generation_id":c.get("dispatch_generation_id"),
                  "presence_generation_id":c.get("presence_generation_id"),"presence_event_id":c.get("presence_event_id"),
                  "activation_generation_id":c.get("activation_generation_id")
                }
                adrift=[k for k,v in exact_act.items() if act.get(k)!=v]
                if adrift: raise SystemExit(f"execution_claim_history.jsonl:{n}: V16 activation history drift {','.join(adrift)}")
                claimed=parse_ts(c.get("claimed_at")); aexp=parse_ts(act.get("expires_at"))
                if claimed and aexp and claimed>aexp:
                    raise SystemExit(f"execution_claim_history.jsonl:{n}: claim after V16 activation expiry")
        elif c.get("routing_mode")=="manual_override":
            if not str(c.get("route_override_reason") or "").strip():
                raise SystemExit(f"execution_claim_history.jsonl:{n}: manual override missing reason")
        else:
            raise SystemExit(f"execution_claim_history.jsonl:{n}: invalid V14 routing_mode")
    if registered_workers and c.get("worker_id") not in registered_workers:
        raise SystemExit(f"execution_claim_history.jsonl:{n}: unregistered worker_id {c.get('worker_id')}")
    if c.get("status") in {"CLAIMED","RUNNING"}:
        active_workers[c.get("worker_id")]+=1
for worker,count in active_workers.items():
    if count>int(policy.get("max_active_claims_per_worker",1)):
        raise SystemExit(f"worker {worker} exceeds max active claims")

run_by_id={r.get("search_run_id"):r for r in runs if r.get("search_run_id")}
for n,r in enumerate(runs,1):
    if int(r.get("schema_version") or 0)<11:
        continue
    if r.get("allocation_mode") not in {"generated","manual_override"}:
        continue
    cid=r.get("execution_claim_id")
    c=claim_by_id.get(cid)
    if not c:
        raise SystemExit(f"search_runs.jsonl:{n}: V11 run references unknown claim {cid}")
    expected={
      "execution_slot_id":c.get("slot_id"),
      "execution_worker_id":c.get("worker_id"),
      "assignment_id":c.get("assignment_id"),
      "allocator_generation_id":c.get("allocator_generation_id"),
      "portfolio_policy_generation_id":c.get("portfolio_policy_generation_id"),
      "assignment_work_item_id":c.get("work_item_id"),
      "assignment_slot_role":c.get("assignment_slot_role"),
      "assignment_work_kind":c.get("assignment_work_kind"),
      "assignment_source_id":c.get("assignment_source_id")
    }
    if c.get("assignment_work_kind")=="learning_measurement":
        expected["learning_measurement_packet_id"]=c.get("learning_measurement_packet_id")
        expected["learning_measurement_packet_sha256"]=c.get("learning_measurement_packet_sha256")
    mismatch=[k for k,v in expected.items() if r.get(k)!=v]
    if mismatch:
        raise SystemExit(f"search_runs.jsonl:{n}: claim provenance mismatch: {','.join(mismatch)}")
    if int(r.get("schema_version") or 0)>=12 and c.get("routing_generation_id"):
        if r.get("routing_generation_id")!=c.get("routing_generation_id") or r.get("worker_profile_generation_id")!=c.get("worker_profile_generation_id"):
            raise SystemExit(f"search_runs.jsonl:{n}: routing provenance mismatch")
        try:
            if abs(float(r.get("routing_score"))-float(c.get("routing_score")))>1e-9:
                raise SystemExit(f"search_runs.jsonl:{n}: routing_score mismatch")
        except (TypeError,ValueError):
            raise SystemExit(f"search_runs.jsonl:{n}: invalid routing_score")
    if int(r.get("schema_version") or 0)>=14 and cid not in legacy_claim_ids:
        if r.get("routing_mode")!=c.get("routing_mode"):
            raise SystemExit(f"search_runs.jsonl:{n}: V14 routing_mode mismatch")
        if c.get("routing_mode")=="generated":
            if r.get("dispatch_ticket_id")!=c.get("dispatch_ticket_id"):
                raise SystemExit(f"search_runs.jsonl:{n}: V14 run dispatch_ticket_id mismatch")
            if r.get("dispatch_generation_id")!=c.get("dispatch_generation_id"):
                raise SystemExit(f"search_runs.jsonl:{n}: V14 run dispatch_generation_id mismatch")
            if r.get("routing_learning_generation_id")!=c.get("routing_learning_generation_id"):
                raise SystemExit(f"search_runs.jsonl:{n}: V14 routing_learning_generation_id mismatch")
            if int(r.get("schema_version") or 0)>=15:
                if r.get("dispatch_kind")!=c.get("dispatch_kind"):
                    raise SystemExit(f"search_runs.jsonl:{n}: V15 dispatch_kind mismatch")
                if r.get("dispatch_parent_ticket_id")!=c.get("parent_dispatch_ticket_id"):
                    raise SystemExit(f"search_runs.jsonl:{n}: V15 dispatch parent mismatch")
                if int(r.get("schema_version") or 0)>=16:
                    for key in ["presence_generation_id","presence_event_id","activation_id","activation_generation_id"]:
                        if r.get(key)!=c.get(key):
                            raise SystemExit(f"search_runs.jsonl:{n}: V16 activation provenance mismatch {key}")
        elif r.get("route_override_reason")!=c.get("route_override_reason"):
            raise SystemExit(f"search_runs.jsonl:{n}: V14 override reason mismatch")
    try:
        if abs(float(r.get("assignment_score"))-float(c.get("assignment_score")))>1e-9:
            raise SystemExit(f"search_runs.jsonl:{n}: assignment_score mismatch")
    except (TypeError,ValueError):
        raise SystemExit(f"search_runs.jsonl:{n}: invalid assignment_score")

for c in claims:
    if c.get("status")=="COMPLETE":
        rid=c.get("search_run_id")
        if not rid or rid not in run_by_id:
            raise SystemExit(f"complete claim {c.get('claim_id')} missing search run")
        if c.get("telemetry_status")!="MATCHED":
            raise SystemExit(f"complete claim {c.get('claim_id')} lacks matched telemetry")

if metrics.get("slot_count")!=len(states):
    raise SystemExit("execution_metrics slot_count drift")
if metrics.get("claim_count")!=len(claims):
    raise SystemExit("execution_metrics claim_count drift")
status_counts=Counter(s.get("status") for s in states)
if dict(status_counts)!=metrics.get("status_counts"):
    raise SystemExit("execution_metrics status_counts drift")

print(f"OK slots={len(states)} claims={len(claims)} active={metrics.get('active_claims')} completed={metrics.get('complete_claims')}")
