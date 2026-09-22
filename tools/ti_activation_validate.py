#!/usr/bin/env python3
import json, sys
from ti_common import INTEL, ROOT, load_jsonl

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.restart_readiness import build_restart_readiness
from production.runtime_activation_gate import evaluate_runtime_activation_gate

POL=json.loads((INTEL/"activation_policy.json").read_text(encoding="utf-8"))
RUNTIME_POL=json.loads((INTEL/"hunter_runtime_policy.json").read_text(encoding="utf-8"))
SPLIT_STATUS=json.loads((INTEL/"TRAINING_SPLIT_STATUS.json").read_text(encoding="utf-8"))
MEASUREMENT_PACKETS=json.loads((INTEL/"learning_measurement_packets.json").read_text(encoding="utf-8"))
PRES=load_jsonl("worker_presence_state.jsonl")
DIR=load_jsonl("activation_directives.jsonl")
PACK=load_jsonl("activation_claim_packets.jsonl")
HIST=load_jsonl("activation_history.jsonl")
CLAIM_HISTORY=load_jsonl("execution_claim_history.jsonl") if (INTEL/"execution_claim_history.jsonl").exists() else []
APPROVAL_HISTORY=load_jsonl("hunter_runtime_approval_history.jsonl") if (INTEL/"hunter_runtime_approval_history.jsonl").exists() else []
MET=json.loads((INTEL/"activation_metrics.json").read_text(encoding="utf-8"))

scoreboard=(ROOT/"benchmark"/"SCOREBOARD.md").read_text(encoding="utf-8")
shadow_results={}
for lane in ("ai","science","commercial"):
    path=ROOT/"production"/"shadow"/"results"/f"{lane}.md"
    shadow_results[lane]=path.read_text(encoding="utf-8") if path.exists() else ""
PREACTIVATION_READINESS=build_restart_readiness(
    split_status=SPLIT_STATUS,
    activation_metrics={"current_activations":0},
    packets=MEASUREMENT_PACKETS,
    scoreboard_text=scoreboard,
    shadow_results=shadow_results,
    execution_claim_history=CLAIM_HISTORY,
)
RUNTIME_GATE=evaluate_runtime_activation_gate(
    RUNTIME_POL,
    PREACTIVATION_READINESS,
    MEASUREMENT_PACKETS,
    CLAIM_HISTORY,
    APPROVAL_HISTORY,
)

if RUNTIME_GATE.get("errors"):
    raise SystemExit(
        "runtime activation gate invalid: "
        + "; ".join(RUNTIME_GATE.get("errors") or [])
    )

pres={x["worker_id"]:x for x in PRES}
if {x["worker_id"] for x in DIR}!={x["worker_id"] for x in PRES}:
    raise SystemExit("activation directives must contain every presence worker exactly once")
if len({x["worker_id"] for x in DIR})!=len(DIR):
    raise SystemExit("duplicate activation directive worker")
ids=set(); workers=set(); slots=set()
if not RUNTIME_GATE.get("enabled"):
    if PACK:
        raise SystemExit("runtime-disabled activation gate must emit zero claim packets")
    if any(
        row.get("activation_state")=="READY_TO_CLAIM"
        for row in DIR
    ):
        raise SystemExit("runtime-disabled activation gate cannot emit READY_TO_CLAIM")
else:
    if len(PACK)>int(RUNTIME_GATE.get("maximum_current_activations") or 0):
        raise SystemExit("activation packets exceed approved runtime canary capacity")

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
    if x.get("assignment_work_kind") not in set(RUNTIME_GATE.get("allowed_work_kinds") or []):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: work kind outside runtime approval")
    if x.get("assignment_source_id") not in set(RUNTIME_GATE.get("allowed_seed_ids") or []):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: seed outside current precommitted canary")
    if x.get("runtime_approval_id")!=RUNTIME_GATE.get("approval_id"):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: runtime approval lineage drift")
    if x.get("runtime_approval_record_sha256")!=RUNTIME_GATE.get("approval_record_sha256"):
        raise SystemExit(f"activation_claim_packets.jsonl:{n}: runtime approval record hash drift")
hist={x.get("activation_id"):x for x in HIST}
if len(hist)!=len(HIST): raise SystemExit("activation history duplicate IDs")
for x in PACK:
    if x["activation_id"] not in hist: raise SystemExit(f"activation history missing {x['activation_id']}")
gens={x.get("activation_generation_id") for x in DIR}
if len(gens)!=1 or MET.get("activation_generation_id")!=next(iter(gens)):
    raise SystemExit("activation generation mismatch")
if MET.get("current_activations")!=len(PACK) or MET.get("history_activations")!=len(HIST):
    raise SystemExit("activation metrics count drift")
if MET.get("runtime_mode")!=RUNTIME_GATE.get("mode"):
    raise SystemExit("activation metrics runtime mode drift")
if bool(MET.get("runtime_activation_enabled"))!=bool(RUNTIME_GATE.get("enabled")):
    raise SystemExit("activation metrics runtime enabled drift")
if MET.get("runtime_gate_reason")!=RUNTIME_GATE.get("reason"):
    raise SystemExit("activation metrics runtime reason drift")
if (MET.get("runtime_gate_errors") or [])!=(RUNTIME_GATE.get("errors") or []):
    raise SystemExit("activation metrics runtime errors drift")
if MET.get("runtime_approval_id")!=RUNTIME_GATE.get("approval_id"):
    raise SystemExit("activation metrics runtime approval drift")
if MET.get("runtime_approval_record_sha256")!=RUNTIME_GATE.get("approval_record_sha256"):
    raise SystemExit("activation metrics runtime approval record hash drift")
if int(MET.get("runtime_maximum_current_activations") or 0)!=int(RUNTIME_GATE.get("maximum_current_activations") or 0):
    raise SystemExit("activation metrics runtime capacity drift")
for key in (
    "maximum_total_claims",
    "claims_consumed",
    "remaining_claim_budget",
    "active_claims",
):
    metric_key="runtime_"+key
    if int(MET.get(metric_key) or 0)!=int(RUNTIME_GATE.get(key) or 0):
        raise SystemExit(f"activation metrics {metric_key} drift")
for metric_key,gate_key in (
    ("runtime_allowed_seed_ids","allowed_seed_ids"),
    ("runtime_approved_packet_ids","approved_packet_ids"),
    ("runtime_approved_seed_ids","approved_seed_ids"),
    ("runtime_claimed_seed_ids","claimed_seed_ids"),
):
    if (MET.get(metric_key) or [])!=(RUNTIME_GATE.get(gate_key) or []):
        raise SystemExit(f"activation metrics {metric_key} drift")
print(f"OK activation_generation={MET.get('activation_generation_id')} current={len(PACK)} waiting_presence={MET.get('waiting_presence')} runtime={RUNTIME_GATE.get('mode')} enabled={bool(RUNTIME_GATE.get('enabled'))}")
