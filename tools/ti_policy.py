#!/usr/bin/env python3
import json,math
from collections import defaultdict
from ti_common import INTEL,ROOT,load_jsonl

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
outs=load_jsonl("outcomes.jsonl"); strategies=load_jsonl("search_strategies.jsonl"); caps=load_jsonl("capabilities.jsonl")
aliases=json.loads((INTEL/"strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL/"strategy_aliases.json").exists() else {}
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
current_versions=json.loads((INTEL/"current_strategy_versions.json").read_text(encoding="utf-8")) if (INTEL/"current_strategy_versions.json").exists() else {}
attr=json.loads((INTEL/"attribution_metrics.json").read_text(encoding="utf-8")) if (INTEL/"attribution_metrics.json").exists() else {}
attr_version={x["id"]:x for x in attr.get("by_strategy_version",[])}

domain_policy_path=INTEL/"domain_search_policies.json"; domain_constraints=[]; blocked_exclusive_capabilities=set()
if domain_policy_path.exists():
    domain_config=json.loads(domain_policy_path.read_text(encoding="utf-8"))
    for domain in domain_config.get("domains",[]):
        if domain.get("gate_type")!="gap_registry_active_search": continue
        register=json.loads((ROOT/domain["gate_path"]).read_text(encoding="utf-8"))
        active_gap_ids=sorted(g["gap_id"] for g in register.get("gaps",[]) if g.get("status")=="ACTIVE_SEARCH" and g.get("search_allowed") is True)
        aset=set(active_gap_ids); cmap=domain.get("capability_gap_map") or {}
        authorized=sorted(cid for cid,gids in cmap.items() if aset.intersection(gids))
        blocked=sorted(set(cmap)-set(authorized)); blocked_exclusive_capabilities.update(blocked)
        domain_constraints.append({
          "domain_id":domain["domain_id"],"experiment_id":domain.get("experiment_id"),"gate_path":domain["gate_path"],
          "search_authorized":bool(active_gap_ids),"active_search_gap_ids":active_gap_ids,
          "authorized_exclusive_capability_ids":authorized,"blocked_exclusive_capability_ids":blocked,
          "shared_capability_ids":sorted(domain.get("shared_capability_ids") or []),"reason":domain.get("reason")
        })

by_id={s["strategy_id"]:s for s in strategies}
def parent(sid):
    s=by_id.get(sid)
    if s and s.get("parent_strategy_id"): return s["parent_strategy_id"]
    return aliases.get(sid,sid)

historical=defaultdict(list); current_groups=defaultdict(list)
for r in runs:
    canon=parent(r.get("strategy_id")); historical[canon].append(r)
    vid=r.get("strategy_version_id") or (bindings.get(r["search_run_id"]) or {}).get("strategy_version_id")
    if r.get("strategy_id")==canon and vid and current_versions.get(canon)==vid:
        current_groups[canon].append(r)

def beta_mean(success,trials): return (success+1)/(trials+2) if trials>=0 else .5

rows=[]; active=[s for s in strategies if s.get("status")=="active"]
for s in active:
    sid=s["strategy_id"]; vid=current_versions.get(sid); rs=current_groups.get(sid,[])
    inspected=sum((r.get("deep_inspected") or 0) for r in rs); retained=sum((r.get("retained_count") or 0) for r in rs)
    promoted=sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs=sum(1 for r in rs if r.get("new_capability_ids")); experiment_runs=sum(1 for r in rs if r.get("experiment_ids"))
    retain=beta_mean(retained,inspected) if inspected else .5; master=beta_mean(promoted,inspected) if inspected else .5
    novel=beta_mean(novel_runs,len(rs)) if rs else .5; experiment=beta_mean(experiment_runs,len(rs)) if rs else .5
    a=attr_version.get(vid,{}) if vid else {}
    frac_trials=a.get("fractional_outcome_equivalents",0); frac_passed=a.get("fractional_passed_equivalents",0)
    outcome=beta_mean(frac_passed,frac_trials) if frac_trials else .5
    raw=.18*retain+.24*master+.25*novel+.18*experiment+.15*outcome
    evidence_weight=min(min(1,len(rs)/5),min(1,inspected/20) if inspected else 0)
    exploit_mass=raw*evidence_weight; uncertainty=1/math.sqrt(len(rs)+1)
    rows.append({
      "strategy_id":sid,"strategy_version_id":vid,"name":s.get("name"),
      "current_version_runs":len(rs),"historical_runs":len(historical.get(sid,[])),"inspected":inspected,
      "fractional_outcome_equivalents":frac_trials,"raw_exploit_score":raw,"evidence_weight":evidence_weight,
      "exploit_mass":exploit_mass,"uncertainty":uncertainty,"sufficient_evidence":len(rs)>=5 and inspected>=20
    })

measured=len(runs); valid_out=[o for o in outs if o.get("result")!="INVALID"]
exploration_budget=.50 if len(valid_out)<3 or measured<30 else (.40 if len(valid_out)<10 else .25)
sum_u=sum(x["uncertainty"] for x in rows) or 1; sum_e=sum(x["exploit_mass"] for x in rows)
current_measured=[x for x in rows if x["current_version_runs"]>0]
for x in rows:
    x["exploration_component"]=x["uncertainty"]/sum_u
    if sum_e>0: x["exploitation_component"]=x["exploit_mass"]/sum_e
    elif current_measured: x["exploitation_component"]=(1/len(current_measured)) if x["current_version_runs"] else 0
    else: x["exploitation_component"]=1/len(rows) if rows else 0
    x["allocation"]=exploration_budget*x["exploration_component"]+(1-exploration_budget)*x["exploitation_component"]
norm=sum(x["allocation"] for x in rows) or 1
for x in rows:x["allocation"]/=norm
rows.sort(key=lambda x:(-x["allocation"],x["strategy_id"]))

attention=defaultdict(int)
for r in runs:
    for cid in r.get("new_capability_ids",[])+r.get("strengthened_capability_ids",[]):attention[cid]+=1
def gap(c):
    score={"watch":3,"source_or_test_validated":2,"benchmarked":1}.get(c.get("evidence_state"),0)
    if c.get("missing_piece"):score+=2
    if len(c.get("primary_components") or [])<2:score+=2
    if attention[c["capability_id"]]==0:score+=1
    return score
gaps=sorted([
 {"capability_id":c["capability_id"],"name":c["name"],"gap_score":gap(c),"missing_piece":c.get("missing_piece"),"run_attention":attention[c["capability_id"]]}
 for c in caps if c["capability_id"] not in blocked_exclusive_capabilities
],key=lambda x:(-x["gap_score"],x["capability_id"]))[:10]

obj={
 "measured_runs":measured,"valid_outcomes":len(valid_out),"exploration_budget":exploration_budget,
 "evidence_scope":"current_strategy_version_only","strategy_allocation":rows,"priority_capability_gaps":gaps,
 "domain_constraints":domain_constraints,
 "guardrails":{"min_runs_for_exploitation_claim":5,"min_deep_inspections_for_exploitation_claim":20,"never_zero_exploration":True,
 "current_version_only_for_exploitation":True,"historical_versions_retained_for_analysis":True,
 "domain_authorization_precedes_generic_gap_ranking":True,"multi_origin_outcomes_not_full_credited_to_every_strategy":True}
}
(INTEL/"search_policy.json").write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
lines=["# ADAPTIVE SEARCH POLICY","",
 "V5 exploitation evidence is **current-strategy-version only**. When a search procedure changes, the new version starts with zero inherited exploitation confidence while old versions remain in history.","",
 f"- Measured historical runs: **{measured}**",f"- Valid structured outcomes: **{len(valid_out)}**",f"- Exploration budget: **{exploration_budget:.0%}**","",
 "## Suggested strategy allocation","",
 "| Strategy | Current version | Allocation | Current-version runs | Historical runs | Inspected | Outcome eq. | Evidence |",
 "|---|---|---:|---:|---:|---:|---:|---|"]
for x in rows:
    lines.append(f"| {x['strategy_id']} | {x['strategy_version_id'] or 'unresolved'} | {x['allocation']:.1%} | {x['current_version_runs']} | {x['historical_runs']} | {x['inspected']} | {x['fractional_outcome_equivalents']:.2f} | {'sufficient' if x['sufficient_evidence'] else 'insufficient'} |")
lines += ["","## Highest-information capability gaps","",
 "| Capability | Gap score | Prior run attention | Missing piece |","|---|---:|---:|---|"]
for x in gaps:lines.append(f"| {x['capability_id']} — {x['name']} | {x['gap_score']} | {x['run_attention']} | {x['missing_piece'] or '—'} |")
lines += ["","## Allocation guardrails","",
 "- A strategy edit creates a new version and resets exploitation sufficiency for that version.",
 "- Historical-version evidence remains visible but cannot make an untested current version look proven.",
 "- Never suppress exploration to zero, especially for wildcard/novelty search.",
 "- Domain authorization gates override generic gap ranking.",
 "- Matched benchmark and real outcome evidence should eventually dominate repository-retention metrics.",""]
(INTEL/"SEARCH_POLICY.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"historical_runs":measured,"current_version_runs":sum(x["current_version_runs"] for x in rows),"exploration_budget":exploration_budget}))
