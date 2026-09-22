#!/usr/bin/env python3
import copy, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.allocator_learning_bootstrap import (
    BOOTSTRAP_MODE,
    apply_learning_bootstrap,
)
from ti_common import INTEL, load_jsonl

BASE=json.loads((INTEL/"allocator_policy.json").read_text(encoding="utf-8"))
RUNS=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
OUTCOMES=load_jsonl("outcomes.jsonl")
CURRENT_ALLOC=load_jsonl("hunt_allocations.jsonl") if (INTEL/"hunt_allocations.jsonl").exists() else []
ALLOC_INDEX={a.get("assignment_id"):a for a in CURRENT_ALLOC if a.get("assignment_id")}
ADAPT=BASE.get("adaptation") or {}
LEARNING_STATE=json.loads((INTEL/"LEARNING_STATE.json").read_text(encoding="utf-8")) if (INTEL/"LEARNING_STATE.json").exists() else {}
LEARNING_CURRICULUM=json.loads((INTEL/"learning_curriculum.json").read_text(encoding="utf-8")) if (INTEL/"learning_curriculum.json").exists() else {}
SPLIT_STATUS=json.loads((INTEL/"TRAINING_SPLIT_STATUS.json").read_text(encoding="utf-8")) if (INTEL/"TRAINING_SPLIT_STATUS.json").exists() else {}

outcomes_by_run=defaultdict(list)
for o in OUTCOMES:
    if o.get("result")=="INVALID":
        continue
    for rid in o.get("origin_search_ids") or []:
        outcomes_by_run[rid].append(o)

def empty_metrics(key):
    return {
      "key":key,
      "runs":0,
      "deep_inspected":0,
      "retained_count":0,
      "master_promoted_count":0,
      "new_capability_runs":0,
      "experiment_touch_runs":0,
      "valid_outcome_runs":0,
      "passed_outcome_runs":0,
      "candidate_dispositions":0,
      "duplicate_dispositions":0,
      "realized_revenue_usd":0.0,
      "customer_value_usd":0.0,
      "engineering_days_saved_low":0.0,
      "engineering_days_saved_high":0.0,
      "manual_override_runs":0
    }

role=defaultdict(lambda:empty_metrics(None))
kind=defaultdict(lambda:empty_metrics(None))
attribution_debt=[]

def enrich(m,r,outs):
    m["runs"]+=1
    m["deep_inspected"]+=int(r.get("deep_inspected") or 0)
    m["retained_count"]+=int(r.get("retained_count") or 0)
    m["master_promoted_count"]+=int(r.get("master_promoted_count") or 0)
    m["new_capability_runs"]+=1 if (r.get("new_capability_ids") or []) else 0
    m["experiment_touch_runs"]+=1 if (r.get("experiment_ids") or []) else 0
    if outs:
        m["valid_outcome_runs"]+=1
    if any(o.get("result")=="PASSED" for o in outs):
        m["passed_outcome_runs"]+=1
    for d in r.get("candidate_dispositions") or []:
        m["candidate_dispositions"]+=1
        if d.get("duplicate_of") or d.get("reason_code_standard")=="duplicate_or_dominated":
            m["duplicate_dispositions"]+=1
    seen=set()
    for o in outs:
        oid=o.get("outcome_id")
        if oid in seen:
            continue
        seen.add(oid)
        m["realized_revenue_usd"]+=float(o.get("revenue_usd") or 0)
        m["customer_value_usd"]+=float(o.get("customer_value_usd") or 0)
        m["engineering_days_saved_low"]+=float(o.get("engineering_days_saved_low") or 0)
        m["engineering_days_saved_high"]+=float(o.get("engineering_days_saved_high") or 0)

for r in RUNS:
    if (r.get("schema_version") or 0)<9:
        continue
    if r.get("allocation_mode") not in {"generated","manual_override"}:
        continue
    aid=r.get("assignment_id")
    a=ALLOC_INDEX.get(aid) if aid else None
    slot_role=r.get("assignment_slot_role") or (a or {}).get("slot_role")
    work_kind=r.get("assignment_work_kind") or (a or {}).get("work_kind")
    if not slot_role or not work_kind:
        attribution_debt.append({
          "search_run_id":r.get("search_run_id"),
          "assignment_id":aid,
          "missing_slot_role":not bool(slot_role),
          "missing_work_kind":not bool(work_kind)
        })
        continue
    outs=outcomes_by_run.get(r.get("search_run_id"),[])
    role[slot_role]["key"]=slot_role
    kind[work_kind]["key"]=work_kind
    if r.get("allocation_mode")=="manual_override":
        role[slot_role]["manual_override_runs"]+=1
        kind[work_kind]["manual_override_runs"]+=1
        continue
    enrich(role[slot_role],r,outs)
    enrich(kind[work_kind],r,outs)

thresholds=ADAPT.get("evidence_thresholds") or {
  "min_runs":5,
  "min_deep_inspections":15,
  "min_experiment_touch_runs":3,
  "min_valid_outcome_runs":2
}

def ratios(m):
    runs=m["runs"]
    deep=m["deep_inspected"]
    disp=m["candidate_dispositions"]
    m["retained_precision"]=(m["retained_count"]/deep) if deep else None
    m["master_per_run"]=(m["master_promoted_count"]/runs) if runs else None
    m["new_capability_run_rate"]=(m["new_capability_runs"]/runs) if runs else None
    m["experiment_touch_rate"]=(m["experiment_touch_runs"]/runs) if runs else None
    m["valid_outcome_run_rate"]=(m["valid_outcome_runs"]/runs) if runs else None
    m["passed_outcome_run_rate"]=(m["passed_outcome_runs"]/runs) if runs else None
    m["duplicate_ratio"]=(m["duplicate_dispositions"]/disp) if disp else None
    enough_activity=(
      deep>=int(thresholds.get("min_deep_inspections",15))
      or m["experiment_touch_runs"]>=int(thresholds.get("min_experiment_touch_runs",3))
      or m["valid_outcome_runs"]>=int(thresholds.get("min_valid_outcome_runs",2))
    )
    m["sufficient_evidence"]=runs>=int(thresholds.get("min_runs",5)) and enough_activity
    retained=m["retained_precision"] or 0.0
    master=min(1.0,m["master_per_run"] or 0.0)
    newcap=m["new_capability_run_rate"] or 0.0
    exp=m["experiment_touch_rate"] or 0.0
    outcome=m["valid_outcome_run_rate"] or 0.0
    passed=m["passed_outcome_run_rate"] or 0.0
    duplicate=(m["duplicate_ratio"] or 0.0) if disp>=5 else 0.0
    signal=(0.15*retained)+(0.20*master)+(0.25*newcap)+(0.15*exp)+(0.15*outcome)+(0.10*passed)-(0.10*duplicate)
    m["allocation_signal"]=round(max(0.0,min(1.0,signal)),4)
    return m

all_roles=sorted(set([s["role"] for s in BASE.get("slots",[])])|set(role.keys()))
all_kinds=sorted(kind.keys())
role_rows=[]
for k in all_roles:
    m=role[k] if k in role else empty_metrics(k)
    m["key"]=k
    role_rows.append(ratios(m))
kind_rows=[]
for k in all_kinds:
    m=kind[k]
    m["key"]=k
    kind_rows.append(ratios(m))

def write_jsonl(name,rows):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")

write_jsonl("allocator_role_metrics.jsonl",role_rows)
write_jsonl("allocator_work_kind_metrics.jsonl",kind_rows)

baseline_counts=defaultdict(int)
for s in BASE.get("slots",[]):
    baseline_counts[s["role"]]+=1

effective,bootstrap_shift=apply_learning_bootstrap(
    BASE,
    LEARNING_STATE,
    LEARNING_CURRICULUM,
    SPLIT_STATUS,
)
effective_counts=defaultdict(int)
for s in effective.get("slots",[]):
    effective_counts[s["role"]]+=1
effective_counts=dict(effective_counts)
adaptable=ADAPT.get("adaptable_roles") or ["experiment","coverage","adjacency"]
protected=ADAPT.get("protected_roles") or ["measurement","verification","wildcard"]
min_slots=ADAPT.get("min_role_slots") or {"experiment":4,"coverage":2,"adjacency":1,"measurement":1,"verification":1,"wildcard":1}
max_slots=ADAPT.get("max_role_slots") or {"experiment":8,"coverage":4,"adjacency":3,"measurement":1,"verification":1,"wildcard":1}
min_gap=float(ADAPT.get("min_signal_gap",0.15))
max_changes=int(ADAPT.get("max_slot_changes_per_generation",1))

role_index={x["key"]:x for x in role_rows}
sufficient=[r for r in adaptable if role_index.get(r,{}).get("sufficient_evidence")]
shift=bootstrap_shift
mode=BOOTSTRAP_MODE if bootstrap_shift else "baseline_insufficient_evidence"

if not bootstrap_shift and len(sufficient)>=2 and max_changes>0:
    receiver=max(sufficient,key=lambda r:(role_index[r]["allocation_signal"],r))
    donor=min(sufficient,key=lambda r:(role_index[r]["allocation_signal"],r))
    gap=role_index[receiver]["allocation_signal"]-role_index[donor]["allocation_signal"]
    can_receive=effective_counts.get(receiver,0)<int(max_slots.get(receiver,effective_counts.get(receiver,0)))
    can_donate=effective_counts.get(donor,0)>int(min_slots.get(donor,0))
    if receiver!=donor and gap>=min_gap and can_receive and can_donate:
        donor_slots=[s for s in effective["slots"] if s["role"]==donor]
        receiver_slots=[s for s in effective["slots"] if s["role"]==receiver]
        donor_slot=sorted(donor_slots,key=lambda s:s["slot_id"],reverse=True)[0]
        template=max(receiver_slots,key=lambda s:len(s.get("accepts") or []))
        donor_slot["role"]=receiver
        donor_slot["accepts"]=list(template.get("accepts") or [])
        donor_slot["label"]=template.get("label") or receiver
        effective_counts[donor]-=1
        effective_counts[receiver]=effective_counts.get(receiver,0)+1
        shift={
          "from_role":donor,
          "to_role":receiver,
          "slot_id":donor_slot["slot_id"],
          "signal_gap":round(gap,4),
          "from_signal":role_index[donor]["allocation_signal"],
          "to_signal":role_index[receiver]["allocation_signal"]
        }
        mode="adaptive_one_slot_shift"
    else:
        mode="hold_no_eligible_signal_gap"

fingerprint=json.dumps({
  "base_role_counts":dict(baseline_counts),
  "effective_role_counts":effective_counts,
  "shift":shift,
  "role_metrics":[(x["key"],x["runs"],x["allocation_signal"],x["sufficient_evidence"]) for x in role_rows],
  "thresholds":thresholds
},sort_keys=True)
policy_id="PORTFOLIO:"+hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
effective["learning"]={
  "schema_version":1,
  "portfolio_policy_generation_id":policy_id,
  "mode":mode,
  "baseline_role_counts":dict(baseline_counts),
  "effective_role_counts":effective_counts,
  "shift":shift,
  "learning_bootstrap_active": bool(bootstrap_shift),
  "attributed_assignment_runs":sum(x["runs"] for x in role_rows),
  "attribution_debt_runs":len(attribution_debt),
  "evidence_thresholds":thresholds,
  "min_signal_gap":min_gap,
  "max_slot_changes_per_generation":max_changes,
  "note":"Allocation signal is a scheduling heuristic, not a causal estimate of business value."
}
(INTEL/"allocator_policy_effective.json").write_text(json.dumps(effective,indent=2)+"\n",encoding="utf-8")

metrics={
  "schema_version":1,
  "portfolio_policy_generation_id":policy_id,
  "mode":mode,
  "baseline_role_counts":dict(baseline_counts),
  "effective_role_counts":effective_counts,
  "shift":shift,
  "learning_bootstrap_active": bool(bootstrap_shift),
  "attributed_assignment_runs":sum(x["runs"] for x in role_rows),
  "attribution_debt_runs":len(attribution_debt),
  "roles_with_sufficient_evidence":len([x for x in role_rows if x["sufficient_evidence"]]),
  "work_kinds_observed":len(kind_rows),
  "evidence_thresholds":thresholds
}
(INTEL/"allocator_learning_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
write_jsonl("allocator_attribution_debt.jsonl",attribution_debt)

report=[
 "# ALLOCATOR LEARNING REPORT","",
 f"- Portfolio policy: **{policy_id}**",
 f"- Mode: **{mode}**",
 f"- Attributed assignment runs: **{metrics['attributed_assignment_runs']}**",
 f"- Attribution-debt runs: **{metrics['attribution_debt_runs']}**",
 f"- Roles with sufficient evidence: **{metrics['roles_with_sufficient_evidence']}**",
 f"- Learning bootstrap active: **{str(bool(bootstrap_shift)).lower()}**","",
 "V10 changes portfolio capacity only from executed assignment telemetry. Generated plans that were never run receive no learning credit.",
 "",
 "## Slot-role evidence","",
 "| Role | Runs | Inspected | Retained precision | New-cap run rate | MASTER/run | Experiment-touch rate | Outcome-run rate | Duplicate ratio | Signal | Evidence |",
 "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
]
for x in role_rows:
    def pct(v):
        return "—" if v is None else f"{100*v:.1f}%"
    report.append(f"| {x['key']} | {x['runs']} | {x['deep_inspected']} | {pct(x['retained_precision'])} | {pct(x['new_capability_run_rate'])} | {pct(x['master_per_run'])} | {pct(x['experiment_touch_rate'])} | {pct(x['valid_outcome_run_rate'])} | {pct(x['duplicate_ratio'])} | {x['allocation_signal']:.3f} | {'sufficient' if x['sufficient_evidence'] else 'insufficient'} |")

report += ["","## Effective portfolio","",
 "| Role | Baseline slots | Effective slots |",
 "|---|---:|---:|"]
for r in sorted(set(baseline_counts)|set(effective_counts)):
    report.append(f"| {r} | {baseline_counts.get(r,0)} | {effective_counts.get(r,0)} |")
report += ["",
 "## Adaptation decision","",
 f"- Shift: **{json.dumps(shift,sort_keys=True) if shift else 'none'}**",
 "- At most one slot can move per generation.",
 "- Measurement, verification and wildcard remain protected roles during ordinary performance adaptation.",
 "- During blind-learning bootstrap only, one adjacency/coverage/experiment slot above its configured minimum may temporarily become a second measurement slot; this reverts after the first confirmed strategy prior.",
 "- Experiment, coverage and adjacency cannot move outside configured minimum slot bounds.",
 "- Manual overrides are measured separately and never silently treated as generated allocator success.",
 "- Allocation signal is a scheduling heuristic; realized outcomes remain the strongest downstream evidence.",
 ""]

(INTEL/"ALLOCATOR_LEARNING_REPORT.md").write_text("\n".join(report),encoding="utf-8")

kind_report=[
 "# ALLOCATOR WORK-KIND PERFORMANCE","",
 "Work-kind metrics are diagnostic only in V10. They do not directly move portfolio slots.","",
 "| Work kind | Runs | Inspected | Retained precision | New-cap rate | MASTER/run | Experiment rate | Outcome rate | Signal | Evidence |",
 "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
]
for x in kind_rows:
    def pct2(v):
        return "—" if v is None else f"{100*v:.1f}%"
    kind_report.append(f"| {x['key']} | {x['runs']} | {x['deep_inspected']} | {pct2(x['retained_precision'])} | {pct2(x['new_capability_run_rate'])} | {pct2(x['master_per_run'])} | {pct2(x['experiment_touch_rate'])} | {pct2(x['valid_outcome_run_rate'])} | {x['allocation_signal']:.3f} | {'sufficient' if x['sufficient_evidence'] else 'insufficient'} |")
(INTEL/"ALLOCATOR_WORK_KIND_REPORT.md").write_text("\n".join(kind_report)+"\n",encoding="utf-8")
print(json.dumps(metrics))
