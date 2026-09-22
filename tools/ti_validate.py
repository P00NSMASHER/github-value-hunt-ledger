#!/usr/bin/env python3
import json,re
from datetime import datetime
from ti_common import INTEL,ROOT,load_jsonl,slug

def unique(rows,key,name):
    seen={}
    for n,obj in enumerate(rows,1):
        value=obj.get(key)
        if not value: raise SystemExit(f"{name}:{n}: missing {key}")
        if value in seen: raise SystemExit(f"{name}:{n}: duplicate {key}={value}; first line {seen[value]}")
        seen[value]=n
    return set(seen)

caps=load_jsonl("capabilities.jsonl"); strats=load_jsonl("search_strategies.jsonl")
runs=load_jsonl("search_runs.jsonl"); outs=load_jsonl("outcomes.jsonl")
qfs=load_jsonl("query_families.jsonl"); curated=load_jsonl("edges.jsonl")
derived=load_jsonl("derived_edges.jsonl") if (INTEL/"derived_edges.jsonl").exists() else []
cap_ids=unique(caps,"capability_id","capabilities.jsonl")
strat_ids=unique(strats,"strategy_id","search_strategies.jsonl")
run_ids=unique(runs,"search_run_id","search_runs.jsonl")
out_ids=unique(outs,"outcome_id","outcomes.jsonl")
qf_ids=unique(qfs,"query_family_id","query_families.jsonl")
unique(curated,"edge_id","edges.jsonl"); unique(derived,"edge_id","derived_edges.jsonl")

qaliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
qobj=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
obj_cfg=json.loads((INTEL/"search_objectives.json").read_text(encoding="utf-8"))
objective_ids={x["search_objective_id"] for x in obj_cfg.get("objectives",[])}
surface_cfg=json.loads((INTEL/"surface_families.json").read_text(encoding="utf-8"))
surface_family_ids={x["surface_family_id"] for x in surface_cfg.get("families",[])}
surface_aliases=json.loads((INTEL/"surface_aliases.json").read_text(encoding="utf-8"))
reason_catalog=json.loads((INTEL/"reason_codes.json").read_text(encoding="utf-8"))
standard_reasons={v for vals in reason_catalog.values() for v in vals}
reason_aliases=json.loads((INTEL/"reason_aliases.json").read_text(encoding="utf-8"))
eval_cfg=json.loads((INTEL/"strategy_evaluation_sets.json").read_text(encoding="utf-8"))

def qfid(label):
    raw="QF:"+(slug(label or "unknown")[:120] or "unknown")
    return qaliases.get(raw,raw)

if obj_cfg.get("schema_version")!=1: raise SystemExit("search_objectives.json: unsupported schema_version")
if surface_cfg.get("schema_version")!=1: raise SystemExit("surface_families.json: unsupported schema_version")
if eval_cfg.get("schema_version")!=1: raise SystemExit("strategy_evaluation_sets.json: unsupported schema_version")

for k,v in qobj.items():
    if k not in qf_ids: raise SystemExit(f"query_objective_map.json: unknown query family {k}")
    if v not in objective_ids: raise SystemExit(f"query_objective_map.json: unknown objective {v}")
for k,v in surface_aliases.items():
    if not k.startswith("SURFACE:"): raise SystemExit(f"surface_aliases.json: invalid key {k}")
    if v not in surface_family_ids: raise SystemExit(f"surface_aliases.json: unknown family {v}")
for k,v in reason_aliases.items():
    if v not in standard_reasons: raise SystemExit(f"reason_aliases.json: {k} -> unknown controlled reason {v}")

task_text=(ROOT/"benchmark"/"BENCHMARK_TASKS.md").read_text(encoding="utf-8")
benchmark_task_ids=set(re.findall(r"^(\d{2})\.\s+",task_text,re.M))
eval_sets={}
for n,ev in enumerate(eval_cfg.get("sets",[]),1):
    eid=ev.get("evaluation_set_id")
    if not eid or eid in eval_sets: raise SystemExit(f"strategy_evaluation_sets.json:{n}: missing/duplicate evaluation_set_id")
    unknown_strats=set(ev.get("strategy_ids",[]))-strat_ids
    if unknown_strats: raise SystemExit(f"strategy_evaluation_sets.json:{n}: unknown strategies {sorted(unknown_strats)}")
    unknown_tasks=set(str(x).zfill(2) for x in ev.get("task_ids",[]))-benchmark_task_ids
    if unknown_tasks: raise SystemExit(f"strategy_evaluation_sets.json:{n}: unknown benchmark tasks {sorted(unknown_tasks)}")
    eval_sets[eid]={
      "strategies":set(ev.get("strategy_ids",[])),
      "tasks":set(str(x).zfill(2) for x in ev.get("task_ids",[]))
    }

for n,c in enumerate(caps,1):
    if not re.match(r"^CAP-\d{3,}$",c["capability_id"]): raise SystemExit(f"capabilities.jsonl:{n}: bad capability id")
    if c.get("confidence") not in {"low","medium","high"}: raise SystemExit(f"capabilities.jsonl:{n}: bad confidence")
for n,s in enumerate(strats,1):
    parent=s.get("parent_strategy_id")
    if parent and parent not in strat_ids: raise SystemExit(f"search_strategies.jsonl:{n}: missing parent strategy {parent}")

for n,r in enumerate(runs,1):
    sid=r.get("strategy_id")
    if sid not in strat_ids: raise SystemExit(f"search_runs.jsonl:{n}: unknown strategy_id {sid}")
    expected_qf=qfid(r.get("query_family"))
    if expected_qf not in qf_ids: raise SystemExit(f"search_runs.jsonl:{n}: derived query family missing {expected_qf}")
    version=r.get("schema_version") or 0
    if version>=3 and r.get("query_family_id")!=expected_qf:
        raise SystemExit(f"search_runs.jsonl:{n}: schema v{version} query_family_id drift; expected {expected_qf}")
    if version>=4:
        oid=r.get("search_objective_id")
        if oid not in objective_ids: raise SystemExit(f"search_runs.jsonl:{n}: V4 missing/unknown search_objective_id {oid}")
    for key in ("candidate_count","deep_inspected","retained_count","master_promoted_count"):
        value=r.get(key)
        if value is not None and (not isinstance(value,int) or value<0):
            raise SystemExit(f"search_runs.jsonl:{n}: {key} must be null or nonnegative integer")
    c,d,k,m=r.get("candidate_count"),r.get("deep_inspected"),r.get("retained_count"),r.get("master_promoted_count")
    if c is not None and d is not None and d>c: raise SystemExit(f"search_runs.jsonl:{n}: deep_inspected > candidate_count")
    if d is not None and k is not None and k>d: raise SystemExit(f"search_runs.jsonl:{n}: retained_count > deep_inspected")
    if k is not None and m is not None and m>k: raise SystemExit(f"search_runs.jsonl:{n}: master_promoted_count > retained_count")
    for cid in r.get("new_capability_ids",[])+r.get("strengthened_capability_ids",[]):
        if cid not in cap_ids: raise SystemExit(f"search_runs.jsonl:{n}: unknown capability {cid}")
    seen_disp=set()
    for disp in r.get("candidate_dispositions",[]) or []:
        key=(disp.get("repository"),disp.get("revision"))
        if key in seen_disp and key!=(None,None): raise SystemExit(f"search_runs.jsonl:{n}: duplicate candidate disposition {key}")
        seen_disp.add(key)
        for cid in disp.get("capability_ids") or []:
            if cid not in cap_ids: raise SystemExit(f"search_runs.jsonl:{n}: candidate references unknown capability {cid}")
        if version>=3:
            std=disp.get("reason_code_standard")
            if not std: raise SystemExit(f"search_runs.jsonl:{n}: schema v{version} candidate missing reason_code_standard")
            if std not in standard_reasons: raise SystemExit(f"search_runs.jsonl:{n}: unknown reason_code_standard {std}")
    if r.get("measurement_quality")=="benchmark" and version>=4:
        tids=[str(x).zfill(2) for x in (r.get("benchmark_task_ids") or [])]
        eid=r.get("evaluation_set_id"); gid=r.get("comparison_group_id")
        if not tids or not eid or not gid: raise SystemExit(f"search_runs.jsonl:{n}: V4 benchmark run missing task/set/comparison metadata")
        if eid not in eval_sets: raise SystemExit(f"search_runs.jsonl:{n}: unknown evaluation_set_id {eid}")
        if sid not in eval_sets[eid]["strategies"]: raise SystemExit(f"search_runs.jsonl:{n}: strategy {sid} not allowed in {eid}")
        if not set(tids).issubset(eval_sets[eid]["tasks"]): raise SystemExit(f"search_runs.jsonl:{n}: benchmark task outside {eid}")
        if not gid.startswith("CMP:"): raise SystemExit(f"search_runs.jsonl:{n}: comparison_group_id must start CMP:")

for n,o in enumerate(outs,1):
    timestamp=o.get("timestamp")
    if timestamp:
        try: datetime.fromisoformat(str(timestamp).replace("Z","+00:00"))
        except ValueError: raise SystemExit(f"outcomes.jsonl:{n}: invalid timestamp {timestamp}")
    if len(o.get("origin_search_ids",[]))!=len(set(o.get("origin_search_ids",[]))): raise SystemExit(f"outcomes.jsonl:{n}: duplicate origin_search_ids")
    for rid in o.get("origin_search_ids",[]):
        if rid not in run_ids: raise SystemExit(f"outcomes.jsonl:{n}: unknown origin_search_id {rid}")
    if len(o.get("contributing_capability_ids",[]))!=len(set(o.get("contributing_capability_ids",[]))): raise SystemExit(f"outcomes.jsonl:{n}: duplicate contributing_capability_ids")
    for cid in o.get("contributing_capability_ids",[]):
        if cid not in cap_ids: raise SystemExit(f"outcomes.jsonl:{n}: unknown capability {cid}")
    lo,hi=o.get("engineering_days_saved_low"),o.get("engineering_days_saved_high")
    if lo is not None and hi is not None and lo>hi: raise SystemExit(f"outcomes.jsonl:{n}: engineering_days_saved_low > high")

known=cap_ids|strat_ids|run_ids|out_ids|qf_ids|objective_ids|{"OBJ:unclassified"}|surface_family_ids
for name,edges in (("edges.jsonl",curated),("derived_edges.jsonl",derived)):
    for n,e in enumerate(edges,1):
        for side in ("from","to"):
            value=e.get(side)
            if not value: raise SystemExit(f"{name}:{n}: missing {side}")
            if value.startswith(("CAP-","STRAT:","RUN:","OUT:","QF:","OBJ:","SURFACE_FAMILY:")) and value not in known:
                raise SystemExit(f"{name}:{n}: dangling {side} reference {value}")

registry_path=INTEL/"registry_metrics.json"
if registry_path.exists():
    registry=json.loads(registry_path.read_text(encoding="utf-8"))
    master_text=(ROOT/"MASTER.md").read_text(encoding="utf-8")
    master_repo_count=len(set(m.group(1) for m in re.finditer(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\s+—\s+.*)?$",master_text,re.M)))
    if master_repo_count and registry.get("master_promoted_repositories")!=master_repo_count:
        raise SystemExit(f"registry_metrics.json: MASTER count drift {registry.get('master_promoted_repositories')} != {master_repo_count}")

attr_path=INTEL/"attribution_metrics.json"
if attr_path.exists():
    attr=json.loads(attr_path.read_text(encoding="utf-8"))
    totals=attr.get("totals",{})
    for total_key,credit_key in (
      ("revenue_usd","revenue_usd_credit"),("customer_value_usd","customer_value_usd_credit"),
      ("engineering_days_saved_low","engineering_days_saved_low_credit"),("engineering_days_saved_high","engineering_days_saved_high_credit")
    ):
        credited=sum((x.get(credit_key) or 0) for x in attr.get("by_run",[])); actual=totals.get(total_key) or 0
        if abs(credited-actual)>1e-6: raise SystemExit(f"attribution_metrics.json: {credit_key}={credited} does not conserve {total_key}={actual}")

domain_expectations={}
domain_policy_path=INTEL/"domain_search_policies.json"
if domain_policy_path.exists():
    domain_config=json.loads(domain_policy_path.read_text(encoding="utf-8"))
    if domain_config.get("schema_version")!=1: raise SystemExit("domain_search_policies.json: unsupported schema_version")
    seen_domains=set()
    for n,domain in enumerate(domain_config.get("domains",[]),1):
        domain_id=domain.get("domain_id")
        if not domain_id or domain_id in seen_domains: raise SystemExit(f"domain_search_policies.json:{n}: missing/duplicate domain_id")
        seen_domains.add(domain_id)
        if domain.get("gate_type")!="gap_registry_active_search": raise SystemExit(f"domain_search_policies.json:{n}: unsupported gate_type")
        gate_path=domain.get("gate_path")
        if not gate_path or not (ROOT/gate_path).exists(): raise SystemExit(f"domain_search_policies.json:{n}: missing gate_path")
        register=json.loads((ROOT/gate_path).read_text(encoding="utf-8"))
        gaps={g.get("gap_id"):g for g in register.get("gaps",[]) if g.get("gap_id")}
        active=sorted(gid for gid,gap in gaps.items() if gap.get("status")=="ACTIVE_SEARCH" and gap.get("search_allowed") is True)
        aset=set(active); cmap=domain.get("capability_gap_map") or {}
        if not isinstance(cmap,dict) or not cmap: raise SystemExit(f"domain_search_policies.json:{n}: capability_gap_map required")
        authorized=[]; blocked=[]
        for cid,gap_ids in cmap.items():
            if cid not in cap_ids: raise SystemExit(f"domain_search_policies.json:{n}: unknown capability {cid}")
            if not isinstance(gap_ids,list) or not gap_ids: raise SystemExit(f"domain_search_policies.json:{n}: {cid} must map to non-empty gap list")
            unknown=set(gap_ids)-set(gaps)
            if unknown: raise SystemExit(f"domain_search_policies.json:{n}: {cid} maps unknown gaps {sorted(unknown)}")
            (authorized if aset.intersection(gap_ids) else blocked).append(cid)
        for cid in domain.get("shared_capability_ids") or []:
            if cid not in cap_ids: raise SystemExit(f"domain_search_policies.json:{n}: unknown shared capability {cid}")
        domain_expectations[domain_id]={
          "search_authorized":bool(active),"active_search_gap_ids":active,
          "authorized_exclusive_capability_ids":sorted(authorized),"blocked_exclusive_capability_ids":sorted(blocked)
        }

policy_path=INTEL/"search_policy.json"
if policy_path.exists():
    policy=json.loads(policy_path.read_text(encoding="utf-8"))
    allocations=policy.get("strategy_allocation",[])
    if allocations:
        total=sum(x.get("allocation",0) for x in allocations)
        if not .999<=total<=1.001: raise SystemExit(f"search_policy.json: allocations sum to {total}, expected 1")
    constraints={x.get("domain_id"):x for x in policy.get("domain_constraints",[])}
    priority_ids={x.get("capability_id") for x in policy.get("priority_capability_gaps",[])}
    for domain_id,expected in domain_expectations.items():
        actual=constraints.get(domain_id)
        if not actual: raise SystemExit(f"search_policy.json: missing domain constraint {domain_id}")
        for key in ("search_authorized","active_search_gap_ids","authorized_exclusive_capability_ids","blocked_exclusive_capability_ids"):
            av=actual.get(key); ev=expected[key]
            if isinstance(ev,list): av=sorted(av or [])
            if av!=ev: raise SystemExit(f"search_policy.json: domain {domain_id} {key} drift")
        leaked=priority_ids.intersection(expected["blocked_exclusive_capability_ids"])
        if leaked: raise SystemExit(f"search_policy.json: blocked domain capabilities leaked into priority gaps: {sorted(leaked)}")

print(f"OK capabilities={len(caps)} strategies={len(strats)} objectives={len(objective_ids)} query_families={len(qfs)} runs={len(runs)} outcomes={len(outs)} curated_edges={len(curated)} derived_edges={len(derived)} eval_sets={len(eval_sets)} domains={len(domain_expectations)}")
