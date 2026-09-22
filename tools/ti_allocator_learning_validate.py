#!/usr/bin/env python3
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.allocator_learning_bootstrap import (
    BOOTSTRAP_MODE,
    apply_learning_bootstrap,
)
from ti_common import INTEL, load_jsonl

base=json.loads((INTEL/"allocator_policy.json").read_text(encoding="utf-8"))
eff=json.loads((INTEL/"allocator_policy_effective.json").read_text(encoding="utf-8"))
metrics=json.loads((INTEL/"allocator_learning_metrics.json").read_text(encoding="utf-8"))
roles=load_jsonl("allocator_role_metrics.jsonl")
runs=load_jsonl("search_runs.jsonl")
learning_state=json.loads((INTEL/"LEARNING_STATE.json").read_text(encoding="utf-8")) if (INTEL/"LEARNING_STATE.json").exists() else {}
curriculum=json.loads((INTEL/"learning_curriculum.json").read_text(encoding="utf-8")) if (INTEL/"learning_curriculum.json").exists() else {}
split_status=json.loads((INTEL/"TRAINING_SPLIT_STATUS.json").read_text(encoding="utf-8")) if (INTEL/"TRAINING_SPLIT_STATUS.json").exists() else {}
adapt=base.get("adaptation") or {}
protected=adapt.get("protected_roles") or ["measurement","verification","wildcard"]
mins=adapt.get("min_role_slots") or {}
maxs=adapt.get("max_role_slots") or {}
max_changes=int(adapt.get("max_slot_changes_per_generation",1))
min_gap=float(adapt.get("min_signal_gap",0.15))

base_counts=Counter(s["role"] for s in base.get("slots",[]))
eff_counts=Counter(s["role"] for s in eff.get("slots",[]))
learning_meta=eff.get("learning") or {}
mode=metrics.get("mode")
bootstrap_active=learning_meta.get("learning_bootstrap_active") is True
expected_bootstrap,expected_bootstrap_shift=apply_learning_bootstrap(
    base,
    learning_state,
    curriculum,
    split_status,
)

if len(eff.get("slots",[]))!=base.get("slot_count"):
    raise SystemExit("effective allocator slot_count drift")

if expected_bootstrap_shift is not None:
    if not bootstrap_active or mode!=BOOTSTRAP_MODE:
        raise SystemExit("learning bootstrap expected but not active")
    expected_slots={
        slot["slot_id"]:(
            slot.get("role"),
            tuple(slot.get("accepts") or []),
            slot.get("label"),
        )
        for slot in expected_bootstrap.get("slots") or []
    }
    actual_slots={
        slot["slot_id"]:(
            slot.get("role"),
            tuple(slot.get("accepts") or []),
            slot.get("label"),
        )
        for slot in eff.get("slots") or []
    }
    if actual_slots!=expected_slots:
        raise SystemExit("effective allocator does not match expected learning bootstrap")
    if learning_meta.get("shift")!=expected_bootstrap_shift:
        raise SystemExit("learning bootstrap shift metadata mismatch")
else:
    if bootstrap_active or mode==BOOTSTRAP_MODE:
        raise SystemExit("stale or unauthorized learning bootstrap")

for r in protected:
    allowed_delta=1 if (bootstrap_active and r=="measurement") else 0
    if eff_counts[r]!=base_counts[r]+allowed_delta:
        raise SystemExit(f"protected role changed: {r}")
for r,v in eff_counts.items():
    if r in mins and v<int(mins[r]):
        raise SystemExit(f"role below minimum: {r}")
    if r in maxs and v>int(maxs[r]):
        if not (
            bootstrap_active
            and r=="measurement"
            and v==base_counts[r]+1
            and v==2
        ):
            raise SystemExit(f"role above maximum: {r}")
changes=sum(abs(eff_counts[r]-base_counts[r]) for r in set(base_counts)|set(eff_counts))//2
if changes>max_changes:
    raise SystemExit("too many slot changes in one generation")

shift=learning_meta.get("shift")
role_index={x["key"]:x for x in roles}
if shift and not bootstrap_active:
    fr=shift["from_role"]; to=shift["to_role"]
    if not role_index.get(fr,{}).get("sufficient_evidence") or not role_index.get(to,{}).get("sufficient_evidence"):
        raise SystemExit("adaptive shift without sufficient evidence on donor/receiver")
    actual=role_index[to]["allocation_signal"]-role_index[fr]["allocation_signal"]
    if actual+1e-9<min_gap:
        raise SystemExit("adaptive shift below minimum signal gap")
elif not shift and mode=="adaptive_one_slot_shift":
    raise SystemExit("adaptive mode without shift")

if metrics.get("portfolio_policy_generation_id")!=learning_meta.get("portfolio_policy_generation_id"):
    raise SystemExit("portfolio policy generation mismatch")
if bool(metrics.get("learning_bootstrap_active"))!=bootstrap_active:
    raise SystemExit("allocator bootstrap metric mismatch")

for n,r in enumerate(runs,1):
    if (r.get("schema_version") or 0)<10:
        continue
    mode=r.get("allocation_mode")
    if mode in {"generated","manual_override"}:
        required=["assignment_slot_role","assignment_work_kind","assignment_source_id","assignment_score","portfolio_policy_generation_id"]
        missing=[k for k in required if r.get(k) in {None,""}]
        if missing:
            raise SystemExit(f"search_runs.jsonl:{n}: V10 run missing {','.join(missing)}")
print(f"OK mode={metrics.get('mode')} attributed_runs={metrics.get('attributed_assignment_runs')} role_changes={changes}")
