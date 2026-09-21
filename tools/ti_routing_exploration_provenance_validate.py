#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"routing_exploration_provenance_policy.json").read_text(encoding="utf-8"))
ROUTES=load_jsonl("worker_routing.jsonl")
WORKER_PACKETS=load_jsonl("worker_claim_packets.jsonl")
DISPATCH=load_jsonl("dispatch_tickets.jsonl")
DISPATCH_PACKETS=load_jsonl("dispatch_claim_packets.jsonl")
STEAL=load_jsonl("work_steal_tickets.jsonl") if (INTEL/"work_steal_tickets.jsonl").exists() else []
STEAL_PACKETS=load_jsonl("work_steal_claim_packets.jsonl") if (INTEL/"work_steal_claim_packets.jsonl").exists() else []
ACTIVATION=load_jsonl("activation_claim_packets.jsonl") if (INTEL/"activation_claim_packets.jsonl").exists() else []
HISTORY=load_jsonl("dispatch_ticket_history.jsonl")
CLAIMS=load_jsonl("execution_claim_history.jsonl")
RUNS=load_jsonl("search_runs.jsonl")

route_by_worker={x.get("worker_id"):x for x in ROUTES if x.get("route_status")=="ROUTED"}
worker_packet_by_worker={x.get("worker_id"):x for x in WORKER_PACKETS}
dispatch_by_id={x.get("dispatch_ticket_id"):x for x in HISTORY if x.get("dispatch_ticket_id")}
run_by_id={x.get("search_run_id"):x for x in RUNS if x.get("search_run_id")}

FIELDS=["routing_exploration_generation_id","routing_exploration_pair_id","baseline_slot_id","route_mode"]
errors=[]

def compare(label,a,b):
    drift=[k for k in FIELDS if a.get(k)!=b.get(k)]
    if drift:
        errors.append(f"{label}: exploration provenance drift {','.join(drift)}")

def validate_route_shape(label,x,slot_key="slot_id"):
    mode=x.get("route_mode")
    slot=x.get(slot_key)
    baseline=x.get("baseline_slot_id")
    pair=x.get("routing_exploration_pair_id")
    gen=x.get("routing_exploration_generation_id")
    if not gen:
        errors.append(f"{label}: missing routing_exploration_generation_id")
    if not baseline:
        errors.append(f"{label}: missing baseline_slot_id")
    if mode=="explore_swap":
        if not pair:
            errors.append(f"{label}: explore_swap missing pair_id")
        if baseline==slot:
            errors.append(f"{label}: explore_swap baseline_slot_id equals routed slot")
    elif mode=="exploit":
        if pair is not None:
            errors.append(f"{label}: exploit route carries pair_id")
        if baseline!=slot:
            errors.append(f"{label}: exploit baseline_slot_id differs from routed slot")
    else:
        errors.append(f"{label}: invalid route_mode {mode}")

for n,t in enumerate(DISPATCH,1):
    if int(t.get("ticket_schema_version") or 0)<int(POL.get("minimum_dispatch_ticket_schema_version",19)):
        errors.append(f"dispatch_tickets.jsonl:{n}: current ticket below V19 schema")
        continue
    r=route_by_worker.get(t.get("worker_id"))
    p=worker_packet_by_worker.get(t.get("worker_id"))
    if not r or not p:
        errors.append(f"dispatch_tickets.jsonl:{n}: missing current routed source")
        continue
    compare(f"dispatch_tickets.jsonl:{n}:route",t,r)
    compare(f"dispatch_tickets.jsonl:{n}:packet",t,p)
    validate_route_shape(f"dispatch_tickets.jsonl:{n}",t)

current_by_id={x.get("dispatch_ticket_id"):x for x in DISPATCH}
for n,p in enumerate(DISPATCH_PACKETS,1):
    t=current_by_id.get(p.get("dispatch_ticket_id"))
    if not t:
        errors.append(f"dispatch_claim_packets.jsonl:{n}: unknown current ticket")
        continue
    compare(f"dispatch_claim_packets.jsonl:{n}",p,t)
    if int(p.get("claim_schema_version") or 0)<int(POL.get("minimum_claim_schema_version",19)):
        errors.append(f"dispatch_claim_packets.jsonl:{n}: claim schema below V19")

primary_by_id=current_by_id
steal_by_id={x.get("dispatch_ticket_id"):x for x in STEAL}
for n,s in enumerate(STEAL,1):
    parent=primary_by_id.get(s.get("parent_dispatch_ticket_id"))
    if not parent:
        errors.append(f"work_steal_tickets.jsonl:{n}: missing current parent")
        continue
    compare(f"work_steal_tickets.jsonl:{n}",s,parent)
for n,p in enumerate(STEAL_PACKETS,1):
    s=steal_by_id.get(p.get("dispatch_ticket_id"))
    if not s:
        errors.append(f"work_steal_claim_packets.jsonl:{n}: missing ticket")
        continue
    compare(f"work_steal_claim_packets.jsonl:{n}",p,s)

for n,a in enumerate(ACTIVATION,1):
    t=dispatch_by_id.get(a.get("dispatch_ticket_id"))
    if not t:
        errors.append(f"activation_claim_packets.jsonl:{n}: missing dispatch history ticket")
        continue
    if int(t.get("ticket_schema_version") or 0)>=19:
        compare(f"activation_claim_packets.jsonl:{n}",a,t)

completed_primary=[]
work_steal_audit=0
historical_v19_claims=0
for n,c in enumerate(CLAIMS,1):
    if c.get("routing_mode")!="generated":
        continue
    t=dispatch_by_id.get(c.get("dispatch_ticket_id"))
    if not t or int(t.get("ticket_schema_version") or 0)<19:
        continue
    historical_v19_claims+=1
    compare(f"execution_claim_history.jsonl:{n}",c,t)
    if int(c.get("claim_schema_version") or 0)<19:
        errors.append(f"execution_claim_history.jsonl:{n}: V19 ticket has pre-V19 claim")
    if c.get("dispatch_kind")=="work_steal":
        work_steal_audit+=1
    if c.get("status")!="COMPLETE":
        continue
    rid=c.get("search_run_id")
    r=run_by_id.get(rid)
    if not r:
        errors.append(f"execution_claim_history.jsonl:{n}: complete V19 claim missing run")
        continue
    if int(r.get("schema_version") or 0)<19:
        errors.append(f"execution_claim_history.jsonl:{n}: V19 claim completed by pre-V19 run")
        continue
    compare(f"search_run:{rid}",r,c)
    if c.get("dispatch_kind")=="primary" and c.get("telemetry_status")=="MATCHED":
        completed_primary.append((c,r))

pair_members=defaultdict(list)
completed_exploratory=0
for c,r in completed_primary:
    if c.get("route_mode")!="explore_swap":
        continue
    completed_exploratory+=1
    pair=c.get("routing_exploration_pair_id")
    if pair:
        pair_members[pair].append((c,r))

ready_pairs=[]
partial_pairs=[]
for pair,members in sorted(pair_members.items()):
    distinct_workers={c.get("worker_id") for c,_ in members}
    if len(members)==2 and len(distinct_workers)==2:
        ready_pairs.append(pair)
    else:
        partial_pairs.append(pair)

if errors:
    raise SystemExit("\n".join(errors))

metrics={
  "schema_version":1,
  "current_v19_primary_dispatch_tickets":len(DISPATCH),
  "current_v19_dispatch_claim_packets":len(DISPATCH_PACKETS),
  "current_activation_packets_checked":len(ACTIVATION),
  "historical_v19_generated_claims":historical_v19_claims,
  "completed_v19_primary_runs":len(completed_primary),
  "completed_v19_exploratory_primary_runs":completed_exploratory,
  "analysis_ready_pairs":len(ready_pairs),
  "partial_pairs":len(partial_pairs),
  "work_steal_claims_preserved_for_audit":work_steal_audit,
  "analysis_ready_pair_ids":ready_pairs,
  "partial_pair_ids":partial_pairs
}
(INTEL/"routing_exploration_provenance_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=[
 "# V19 ROUTING EXPLORATION PROVENANCE","",
 "V19 bridges V18 controlled-exploration identity through dispatch, activation, claim and search-run telemetry.","",
 f"- Current V19 primary dispatch tickets: **{metrics['current_v19_primary_dispatch_tickets']}**",
 f"- Completed V19 primary runs: **{metrics['completed_v19_primary_runs']}**",
 f"- Completed V19 exploratory primary runs: **{metrics['completed_v19_exploratory_primary_runs']}**",
 f"- Analysis-ready matched pairs: **{metrics['analysis_ready_pairs']}**",
 f"- Partial pairs: **{metrics['partial_pairs']}**",
 f"- Work-steal claims preserved for audit: **{metrics['work_steal_claims_preserved_for_audit']}**","",
 "## Analysis eligibility","",
 "A matched V18 pair is eligible for future worker-effect analysis only when both members are distinct workers, use generated primary dispatch, complete with MATCHED telemetry, and carry identical EXPPAIR provenance through a schema-v19 run.",
 "",
 "Work-steal, manual override, unrouted, retrospective, mismatched-telemetry and incomplete-pair executions are excluded from matched worker-effect analysis.",
 ""]
if ready_pairs:
    report += ["## Ready pairs",""]+[f"- {x}" for x in ready_pairs]+[""]
else:
    report += ["## Ready pairs","","- None yet. Provenance is ready; outcome estimation should remain observe-only until complete matched pairs exist.",""]
(INTEL/"ROUTING_EXPLORATION_PROVENANCE.md").write_text("\n".join(report),encoding="utf-8")
print(json.dumps(metrics))
