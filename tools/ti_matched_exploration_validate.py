#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"matched_exploration_policy.json").read_text(encoding="utf-8"))
EXP=load_jsonl("routing_exploration_history.jsonl")
PAIRS=load_jsonl("matched_exploration_pairs.jsonl")
GROUPS=load_jsonl("routing_crossover_groups.jsonl")
AGENTS=load_jsonl("agent_crossover_metrics.jsonl")
MET=json.loads((INTEL/"matched_exploration_metrics.json").read_text(encoding="utf-8"))

eligible_pairs=[
  x for x in EXP
  if x.get("applied") and x.get("pair_id")
  and int(x.get("match_level") or 0)>=int(POL.get("min_v18_match_level",2))
]
if len(PAIRS)!=len(eligible_pairs):
    raise SystemExit("matched pair count must equal eligible applied V18 pair count")
if len({x.get("pair_id") for x in PAIRS})!=len(PAIRS):
    raise SystemExit("duplicate matched exploration pair_id")

gen=MET.get("matched_analysis_generation_id")
if not gen or not str(gen).startswith("MATCHED:"):
    raise SystemExit("invalid matched analysis generation")

for n,x in enumerate(PAIRS,1):
    if x.get("matched_analysis_generation_id")!=gen:
        raise SystemExit(f"matched_exploration_pairs.jsonl:{n}: generation drift")
    if x.get("evidence_state")=="COMPLETE_CROSSOVER":
        cells=x.get("cells") or {}
        if len(cells)!=4:
            raise SystemExit(f"matched_exploration_pairs.jsonl:{n}: complete pair missing cells")
        if any(int((v or {}).get("n") or 0)<=0 for v in cells.values()):
            raise SystemExit(f"matched_exploration_pairs.jsonl:{n}: complete pair has empty cell")

seen=set()
for n,g in enumerate(GROUPS,1):
    gid=g.get("crossover_group_id")
    if not gid or gid in seen:
        raise SystemExit(f"routing_crossover_groups.jsonl:{n}: missing/duplicate crossover_group_id")
    seen.add(gid)
    if g.get("matched_analysis_generation_id")!=gen:
        raise SystemExit(f"routing_crossover_groups.jsonl:{n}: generation drift")
    cells=g.get("cells") or {}
    required=["agent_a_task_a","agent_a_task_b","agent_b_task_a","agent_b_task_b"]
    complete=all(int((cells.get(k) or {}).get("n") or 0)>0 for k in required)
    if (g.get("evidence_state")=="COMPLETE_CROSSOVER")!=complete:
        raise SystemExit(f"routing_crossover_groups.jsonl:{n}: completeness drift")
    if complete:
        vals=[(cells[k] or {}).get("mean_utility") for k in required]
        if any(v is None for v in vals):
            raise SystemExit(f"routing_crossover_groups.jsonl:{n}: complete group missing utility")
        uaa,uab,uba,ubb=[float(v) for v in vals]
        expected_agent=((uaa-uba)+(uab-ubb))/2.0
        expected_task=((uaa-uab)+(uba-ubb))/2.0
        if abs(float(g.get("agent_effect_a_minus_b"))-expected_agent)>1e-6:
            raise SystemExit(f"routing_crossover_groups.jsonl:{n}: agent contrast formula drift")
        if abs(float(g.get("task_effect_a_minus_b"))-expected_task)>1e-6:
            raise SystemExit(f"routing_crossover_groups.jsonl:{n}: task contrast formula drift")
    else:
        if g.get("agent_effect_a_minus_b") is not None or g.get("task_effect_a_minus_b") is not None:
            raise SystemExit(f"routing_crossover_groups.jsonl:{n}: incomplete group has estimate")

for n,a in enumerate(AGENTS,1):
    if a.get("matched_analysis_generation_id")!=gen:
        raise SystemExit(f"agent_crossover_metrics.jsonl:{n}: generation drift")
    if a.get("eligible_for_routing") is not False:
        raise SystemExit(f"agent_crossover_metrics.jsonl:{n}: V19 must remain diagnostic-only")

if POL.get("automatic_routing_feedback_enabled"):
    raise SystemExit("V19 policy must keep automatic routing feedback disabled")
if MET.get("routing_feedback_applied") is not False:
    raise SystemExit("V19 routing feedback must remain disabled")

complete=sum(1 for g in GROUPS if g.get("evidence_state")=="COMPLETE_CROSSOVER")
if complete!=MET.get("complete_crossover_groups"):
    raise SystemExit("complete crossover metric drift")

expected_global=complete>=int(POL.get("min_complete_crossover_groups_global",4))
if bool(MET.get("global_evidence_sufficient"))!=expected_global:
    raise SystemExit("global evidence sufficiency drift")

print(f"OK matched_generation={gen} applied_pairs={len(PAIRS)} complete_groups={complete} agents={len(AGENTS)}")
