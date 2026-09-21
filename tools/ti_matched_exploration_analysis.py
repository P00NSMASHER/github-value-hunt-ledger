#!/usr/bin/env python3
import hashlib, json, statistics
from collections import defaultdict
from ti_common import INTEL, load_jsonl

POL=json.loads((INTEL/"matched_exploration_policy.json").read_text(encoding="utf-8"))
EXP=load_jsonl("routing_exploration_history.jsonl")
DISPATCH=load_jsonl("dispatch_ticket_history.jsonl")
LEARN=load_jsonl("routing_learning_runs.jsonl")
RUNS=load_jsonl("search_runs.jsonl")

run_by_id={x.get("search_run_id"):x for x in RUNS if x.get("search_run_id")}
decision_by_routing={x.get("routing_generation_id"):x for x in EXP if x.get("routing_generation_id")}
exploit_generations={gid for gid,x in decision_by_routing.items() if not x.get("applied")}
applied=[
  x for x in EXP
  if x.get("applied") and x.get("pair_id")
  and int(x.get("match_level") or 0)>=int(POL.get("min_v18_match_level",2))
]

dispatch_by_gen_agent=defaultdict(list)
for t in DISPATCH:
    if t.get("dispatch_kind","primary")!="primary":
        continue
    gid=t.get("routing_generation_id");aid=t.get("worker_id")
    if gid and aid:
        dispatch_by_gen_agent[(gid,aid)].append(t)

completed=[]
for lr in LEARN:
    sr=run_by_id.get(lr.get("search_run_id"))
    if not sr:
        continue
    if sr.get("routing_mode")!="generated":
        continue
    if sr.get("dispatch_kind")=="work_steal":
        continue
    if sr.get("measurement_quality") not in {"prospective","benchmark"}:
        continue
    agent=lr.get("worker_id") or sr.get("execution_worker_id")
    gid=lr.get("routing_generation_id") or sr.get("routing_generation_id")
    work_item=sr.get("assignment_work_item_id")
    slot=sr.get("execution_slot_id")
    if not agent or not gid or not work_item:
        continue
    completed.append({
      "search_run_id":lr.get("search_run_id"),
      "agent_id":agent,
      "routing_generation_id":gid,
      "slot_id":slot,
      "work_item_id":work_item,
      "utility":float(lr.get("utility") or 0),
      "valid_outcome":bool(lr.get("valid_outcome")),
      "passed_outcome":bool(lr.get("passed_outcome"))
    })

by_gen_agent=defaultdict(list)
by_agent_work=defaultdict(list)
for x in completed:
    by_gen_agent[(x["routing_generation_id"],x["agent_id"])].append(x)
    if x["routing_generation_id"] in exploit_generations:
        by_agent_work[(x["agent_id"],x["work_item_id"])].append(x)

def dedupe(rows):
    return list({x["search_run_id"]:x for x in rows}.values())

def meanv(rows):
    return None if not rows else round(statistics.mean(float(x["utility"]) for x in rows),6)

def cell(rows):
    rows=dedupe(rows)
    return {
      "n":len(rows),
      "mean_utility":meanv(rows),
      "valid_outcome_runs":sum(1 for x in rows if x["valid_outcome"]),
      "passed_outcome_runs":sum(1 for x in rows if x["passed_outcome"]),
      "search_run_ids":sorted(x["search_run_id"] for x in rows)
    }

pair_rows=[]
acc={}

for d in applied:
    gid=d["routing_generation_id"]
    agents=list(d.get("workers") or [])
    bslots=list(d.get("baseline_slots") or [])
    eslots=list(d.get("exploration_slots") or [])
    row={
      "pair_id":d["pair_id"],
      "exploration_generation_id":d["exploration_generation_id"],
      "routing_generation_id":gid,
      "agents":agents,
      "baseline_slots":bslots,
      "exploration_slots":eslots,
      "match_level":d.get("match_level"),
      "match_basis":d.get("match_basis"),
      "binding_state":"BOUND",
      "evidence_state":"UNBOUND",
      "crossover_group_id":None
    }
    if len(agents)!=2 or len(bslots)!=2 or len(eslots)!=2:
        row["binding_state"]="AMBIGUOUS_DISPATCH"
        pair_rows.append(row);continue

    bound={}
    for aid,expected_slot in zip(agents,eslots):
        exact=[t for t in dispatch_by_gen_agent.get((gid,aid),[]) if t.get("slot_id")==expected_slot]
        if len(exact)==0:
            row["binding_state"]="MISSING_DISPATCH"
            break
        if len(exact)>1:
            row["binding_state"]="AMBIGUOUS_DISPATCH"
            break
        bound[aid]=exact[0]
    if row["binding_state"]!="BOUND":
        pair_rows.append(row);continue
    if set(bslots)!=set(eslots):
        row["binding_state"]="SLOT_MISMATCH"
        pair_rows.append(row);continue

    task_by_slot={t["slot_id"]:t for t in bound.values()}
    if any(s not in task_by_slot for s in bslots):
        row["binding_state"]="SLOT_MISMATCH"
        pair_rows.append(row);continue

    a,b=agents
    task_a=task_by_slot[bslots[0]]
    task_b=task_by_slot[bslots[1]]
    work_a=task_a.get("work_item_id")
    work_b=task_b.get("work_item_id")
    if not work_a or not work_b or work_a==work_b:
        row["binding_state"]="AMBIGUOUS_DISPATCH"
        pair_rows.append(row);continue

    raw=json.dumps({
      "agent_a":a,"agent_b":b,
      "task_a":work_a,"task_b":work_b,
      "match_basis":d.get("match_basis")
    },sort_keys=True,separators=(",",":"))
    cross_id="CROSS:"+hashlib.sha256(raw.encode()).hexdigest()[:12]
    row["crossover_group_id"]=cross_id

    explore_a=[x for x in by_gen_agent.get((gid,a),[]) if x["work_item_id"]==work_b]
    explore_b=[x for x in by_gen_agent.get((gid,b),[]) if x["work_item_id"]==work_a]
    base_a=list(by_agent_work.get((a,work_a),[]))
    base_b=list(by_agent_work.get((b,work_b),[]))
    row["cells"]={
      "agent_a_baseline_task":cell(base_a),
      "agent_a_exploration_task":cell(explore_a),
      "agent_b_exploration_task":cell(explore_b),
      "agent_b_baseline_task":cell(base_b)
    }

    e=(1 if explore_a else 0)+(1 if explore_b else 0)
    bcount=(1 if base_a else 0)+(1 if base_b else 0)
    if e==0: row["evidence_state"]="NO_EXPLORATION_COMPLETION"
    elif e<2: row["evidence_state"]="PARTIAL_EXPLORATION"
    elif bcount<2: row["evidence_state"]="MISSING_BASELINE_COMPARATOR"
    else: row["evidence_state"]="COMPLETE_CROSSOVER"

    if cross_id not in acc:
        acc[cross_id]={
          "meta":{
            "crossover_group_id":cross_id,"agent_a":a,"agent_b":b,
            "baseline_task_a":{"work_item_id":work_a,"source_id":task_a.get("assignment_source_id")},
            "baseline_task_b":{"work_item_id":work_b,"source_id":task_b.get("assignment_source_id")},
            "match_level":d.get("match_level"),"match_basis":d.get("match_basis")
          },
          "pair_ids":[],"gens":[],
          "aa":[],"ab":[],"ba":[],"bb":[]
        }
    g=acc[cross_id]
    g["pair_ids"].append(d["pair_id"])
    g["gens"].append(d["exploration_generation_id"])
    g["aa"].extend(base_a);g["ab"].extend(explore_a);g["ba"].extend(explore_b);g["bb"].extend(base_b)
    pair_rows.append(row)

groups=[]
agent_effects=defaultdict(list)

for cross_id,g in sorted(acc.items()):
    aa,ab,ba,bb=map(dedupe,[g["aa"],g["ab"],g["ba"],g["bb"]])
    cells={
      "agent_a_task_a":cell(aa),
      "agent_a_task_b":cell(ab),
      "agent_b_task_a":cell(ba),
      "agent_b_task_b":cell(bb)
    }
    complete=all(v["n"]>0 for v in cells.values())
    row={
      **g["meta"],
      "pair_ids":sorted(set(g["pair_ids"])),
      "exploration_generation_ids":sorted(set(g["gens"])),
      "cells":cells,
      "evidence_state":"COMPLETE_CROSSOVER" if complete else "INCOMPLETE_CROSSOVER",
      "agent_effect_a_minus_b":None,
      "task_effect_a_minus_b":None
    }
    if complete:
        uaa=cells["agent_a_task_a"]["mean_utility"]
        uab=cells["agent_a_task_b"]["mean_utility"]
        uba=cells["agent_b_task_a"]["mean_utility"]
        ubb=cells["agent_b_task_b"]["mean_utility"]
        worker_delta_a=uaa-uba
        worker_delta_b=uab-ubb
        agent_effect=(worker_delta_a+worker_delta_b)/2.0
        task_effect=((uaa-uab)+(uba-ubb))/2.0
        row["agent_effect_a_minus_b"]=round(agent_effect,6)
        row["task_effect_a_minus_b"]=round(task_effect,6)
        row["task_a_agent_delta"]=round(worker_delta_a,6)
        row["task_b_agent_delta"]=round(worker_delta_b,6)
        agent_effects[row["agent_a"]].append((cross_id,agent_effect))
        agent_effects[row["agent_b"]].append((cross_id,-agent_effect))
    groups.append(row)

agents=sorted(
  {x["agent_id"] for x in completed}
  | {g["agent_a"] for g in groups}
  | {g["agent_b"] for g in groups}
)
agent_rows=[]
for aid in agents:
    vals=agent_effects.get(aid,[])
    relevant=[g for g in groups if g["evidence_state"]=="COMPLETE_CROSSOVER" and aid in {g["agent_a"],g["agent_b"]}]
    task_pairs={(g["baseline_task_a"]["work_item_id"],g["baseline_task_b"]["work_item_id"]) for g in relevant}
    enough=(
      len(vals)>=int(POL.get("min_complete_groups_per_agent",2))
      and len(task_pairs)>=int(POL.get("min_distinct_task_pairs_per_agent",2))
    )
    effects=[v for _,v in vals]
    agent_rows.append({
      "agent_id":aid,
      "complete_crossover_groups":len(vals),
      "distinct_task_pairs":len(task_pairs),
      "mean_matched_agent_effect":meanv([{"utility":v} for v in effects]) if effects else None,
      "min_effect":None if not effects else round(min(effects),6),
      "max_effect":None if not effects else round(max(effects),6),
      "sufficient_matched_evidence":bool(enough),
      "eligible_for_routing":False,
      "evidence_state":"SUFFICIENT_DIAGNOSTIC" if enough else "INSUFFICIENT"
    })

debt_rows=[]
for g in groups:
    specs=[
      ("agent_a_task_a",g["agent_a"],g["baseline_task_a"]["work_item_id"],"exploit","BASELINE_COMPARATOR"),
      ("agent_a_task_b",g["agent_a"],g["baseline_task_b"]["work_item_id"],"explore_swap","EXPLORATION_COMPLETION"),
      ("agent_b_task_a",g["agent_b"],g["baseline_task_a"]["work_item_id"],"explore_swap","EXPLORATION_COMPLETION"),
      ("agent_b_task_b",g["agent_b"],g["baseline_task_b"]["work_item_id"],"exploit","BASELINE_COMPARATOR")
    ]
    missing=[s for s in specs if int((g["cells"].get(s[0]) or {}).get("n") or 0)<=0]
    closure=len(missing)
    if closure==0:
        continue
    tier="P0" if closure==1 else ("P1" if closure==2 else "P2")
    observed=4-closure
    for cell_name,agent_id,work_item_id,required_mode,evidence_kind in missing:
        raw_debt=f"{g['crossover_group_id']}|{cell_name}|{agent_id}|{work_item_id}|{required_mode}"
        debt_rows.append({
          "debt_id":"CROSSDEBT:"+hashlib.sha256(raw_debt.encode()).hexdigest()[:12],
          "crossover_group_id":g["crossover_group_id"],
          "missing_cell":cell_name,
          "agent_id":agent_id,
          "work_item_id":work_item_id,
          "required_route_mode":required_mode,
          "required_evidence_kind":evidence_kind,
          "priority_tier":tier,
          "closure_distance":closure,
          "observed_other_cells":observed,
          "applied_pair_generations":len(g.get("pair_ids") or []),
          "routing_authorized":False,
          "instruction":(
            "Observe a completed generated primary route for this exact agent/work item under a non-applied V18 generation."
            if evidence_kind=="BASELINE_COMPARATOR"
            else "Observe a completed generated primary route for this exact agent/work item in an applied V18 exploration generation."
          )
        })

tier_order={"P0":0,"P1":1,"P2":2}
debt_rows.sort(key=lambda x:(tier_order.get(x["priority_tier"],9),-x["applied_pair_generations"],x["crossover_group_id"],x["missing_cell"]))

complete_groups=sum(1 for g in groups if g["evidence_state"]=="COMPLETE_CROSSOVER")
raw=json.dumps({
  "policy":POL,
  "pairs":[(x["pair_id"],x["evidence_state"],x.get("crossover_group_id")) for x in pair_rows],
  "groups":[(g["crossover_group_id"],g["evidence_state"],g.get("agent_effect_a_minus_b")) for g in groups]
},sort_keys=True)
gen="MATCHED:"+hashlib.sha256(raw.encode()).hexdigest()[:12]

for rows in [pair_rows,groups,agent_rows]:
    for x in rows: x["matched_analysis_generation_id"]=gen

metrics={
  "schema_version":1,
  "matched_analysis_generation_id":gen,
  "applied_v18_pairs":len(applied),
  "bound_pair_generations":sum(1 for x in pair_rows if x["binding_state"]=="BOUND"),
  "complete_pair_generations":sum(1 for x in pair_rows if x["evidence_state"]=="COMPLETE_CROSSOVER"),
  "crossover_groups":len(groups),
  "complete_crossover_groups":complete_groups,
  "global_evidence_threshold":int(POL.get("min_complete_crossover_groups_global",4)),
  "global_evidence_sufficient":complete_groups>=int(POL.get("min_complete_crossover_groups_global",4)),
  "agents_with_sufficient_matched_evidence":sum(1 for x in agent_rows if x["sufficient_matched_evidence"]),
  "automatic_routing_feedback_enabled":False,
  "routing_feedback_applied":False,
  "missing_crossover_cells":len(debt_rows),
  "crossover_groups_with_debt":len({x["crossover_group_id"] for x in debt_rows})
}

def write_jsonl(name,rows):
    (INTEL/name).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")

write_jsonl("matched_exploration_pairs.jsonl",pair_rows)
write_jsonl("routing_crossover_groups.jsonl",groups)
write_jsonl("agent_crossover_metrics.jsonl",agent_rows)
write_jsonl("matched_exploration_debt.jsonl",debt_rows)
(INTEL/"matched_exploration_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=[
 "# MATCHED ROUTING EXPLORATION OUTCOMES","",
 f"Generation: **{gen}**",
 f"Applied V18 pair generations: **{len(applied)}**",
 f"Complete crossover groups: **{complete_groups} / {metrics['global_evidence_threshold']}**","",
 "V19 reconstructs four-cell crossover evidence. It does not change routing.","",
 "| Pair | Agents | Binding | Evidence | Group |",
 "|---|---|---|---|---|"
]
for x in pair_rows:
    report.append(f"| {x['pair_id']} | {', '.join(x['agents'])} | {x['binding_state']} | **{x['evidence_state']}** | {x.get('crossover_group_id') or '—'} |")
report += ["","A COMPLETE_CROSSOVER requires observed utility for both agents on both exact work items. Missing cells remain UNKNOWN.",""]
(INTEL/"MATCHED_EXPLORATION_REPORT.md").write_text("\n".join(report),encoding="utf-8")

effects=[
 "# MATCHED AGENT EFFECTS","",
 f"Generation: **{gen}**","",
 "These are additive crossover contrasts, not rankings. V19 never changes routing.","",
 "| Agent | Complete groups | Distinct task pairs | Mean matched effect | Evidence | Routing feedback |",
 "|---|---:|---:|---:|---|---|"
]
for x in agent_rows:
    v=x["mean_matched_agent_effect"]
    effects.append(f"| {x['agent_id']} | {x['complete_crossover_groups']} | {x['distinct_task_pairs']} | {'—' if v is None else f'{v:+.3f}'} | {x['evidence_state']} | disabled |")
effects += ["","Within a complete two-agent/two-task crossover, V19 averages the agent difference on each task. Task contrast is estimated separately. No missing cell is imputed.",""]
(INTEL/"MATCHED_AGENT_EFFECTS.md").write_text("\n".join(effects),encoding="utf-8")

debt_report=[
 "# MATCHED EXPLORATION EVIDENCE DEBT","",
 f"Generation: **{gen}**",
 f"Missing crossover cells: **{len(debt_rows)}**","",
 "This queue is measurement debt only. It does not authorize routing, claiming, or overriding the current allocator.","",
 "| Priority | Group | Missing cell | Agent | Work item | Required mode | Pair generations |",
 "|---|---|---|---|---|---|---:|"
]
for x in debt_rows:
    debt_report.append(
      f"| {x['priority_tier']} | {x['crossover_group_id']} | {x['missing_cell']} | {x['agent_id']} | "
      f"{x['work_item_id']} | {x['required_route_mode']} | {x['applied_pair_generations']} |"
    )
if not debt_rows:
    debt_report.append("| — | — | — | — | — | — | 0 |")
debt_report += ["","A debt row closes only through observed generated-route evidence satisfying the exact agent × work-item × route-mode requirement. Missing cells are never imputed.",""]
(INTEL/"MATCHED_EXPLORATION_DEBT.md").write_text("\n".join(debt_report),encoding="utf-8")

print(json.dumps(metrics))
