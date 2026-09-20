#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl

base=json.loads((INTEL/"allocator_policy.json").read_text(encoding="utf-8"))
eff=json.loads((INTEL/"allocator_policy_effective.json").read_text(encoding="utf-8"))
metrics=json.loads((INTEL/"allocator_learning_metrics.json").read_text(encoding="utf-8"))
roles=load_jsonl("allocator_role_metrics.jsonl")
runs=load_jsonl("search_runs.jsonl")
adapt=base.get("adaptation") or {}
protected=adapt.get("protected_roles") or ["measurement","verification","wildcard"]
mins=adapt.get("min_role_slots") or {}
maxs=adapt.get("max_role_slots") or {}
max_changes=int(adapt.get("max_slot_changes_per_generation",1))
min_gap=float(adapt.get("min_signal_gap",0.15))

base_counts=Counter(s["role"] for s in base.get("slots",[]))
eff_counts=Counter(s["role"] for s in eff.get("slots",[]))
if len(eff.get("slots",[]))!=base.get("slot_count"):
    raise SystemExit("effective allocator slot_count drift")
for r in protected:
    if eff_counts[r]!=base_counts[r]:
        raise SystemExit(f"protected role changed: {r}")
for r,v in eff_counts.items():
    if r in mins and v<int(mins[r]):
        raise SystemExit(f"role below minimum: {r}")
    if r in maxs and v>int(maxs[r]):
        raise SystemExit(f"role above maximum: {r}")
changes=sum(abs(eff_counts[r]-base_counts[r]) for r in set(base_counts)|set(eff_counts))//2
if changes>max_changes:
    raise SystemExit("too many slot changes in one generation")

shift=(eff.get("learning") or {}).get("shift")
role_index={x["key"]:x for x in roles}
if shift:
    fr=shift["from_role"]; to=shift["to_role"]
    if not role_index.get(fr,{}).get("sufficient_evidence") or not role_index.get(to,{}).get("sufficient_evidence"):
        raise SystemExit("adaptive shift without sufficient evidence on donor/receiver")
    actual=role_index[to]["allocation_signal"]-role_index[fr]["allocation_signal"]
    if actual+1e-9<min_gap:
        raise SystemExit("adaptive shift below minimum signal gap")
elif metrics.get("mode")=="adaptive_one_slot_shift":
    raise SystemExit("adaptive mode without shift")

if metrics.get("portfolio_policy_generation_id")!=(eff.get("learning") or {}).get("portfolio_policy_generation_id"):
    raise SystemExit("portfolio policy generation mismatch")

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
