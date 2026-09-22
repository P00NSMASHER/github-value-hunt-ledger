#!/usr/bin/env python3
import json,re,hashlib
from collections import defaultdict
from pathlib import Path
from ti_common import INTEL, ROOT, load_jsonl
from ti_search_actions import (experiment_status, parse_capability_ids, experiment_action,
                               capability_stops, action_errors)

POLICY_PATH=INTEL/"allocator_policy_effective.json" if (INTEL/"allocator_policy_effective.json").exists() else INTEL/"allocator_policy.json"
CFG=json.loads(POLICY_PATH.read_text(encoding="utf-8"))
PORTFOLIO_POLICY_ID=(CFG.get("learning") or {}).get("portfolio_policy_generation_id") or "PORTFOLIO:000000000000"
POLICY=json.loads((INTEL/"search_policy.json").read_text(encoding="utf-8"))
SEEDS=load_jsonl("search_seeds.jsonl")
ADJ=load_jsonl("adjacency_queue.jsonl")
MEASURE=json.loads((INTEL/"measurement_plan.json").read_text(encoding="utf-8")) if (INTEL/"measurement_plan.json").exists() else {}
LEARNING_PACKETS=json.loads((INTEL/"learning_measurement_packets.json").read_text(encoding="utf-8")) if (INTEL/"learning_measurement_packets.json").exists() else {"packets":[]}
learning_packet_by_seed={}
for packet in LEARNING_PACKETS.get("packets") or []:
    seed_id=((packet.get("seed") or {}).get("seed_id"))
    if not isinstance(seed_id,str) or not seed_id:
        continue
    if seed_id in learning_packet_by_seed:
        raise SystemExit(f"duplicate learning measurement packet for {seed_id}")
    learning_packet_by_seed[seed_id]=packet
RUNS=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]

strategy_alloc={x["strategy_id"]:float(x.get("allocation") or 0) for x in POLICY.get("strategy_allocation",[])}

def line_field(block,label):
    m=re.search(r"^-\s*"+re.escape(label)+r":\s*(.*)$",block,re.I|re.M)
    return m.group(1).strip() if m else None

def parse_search_priorities():
    text=(ROOT/"SEARCH_QUEUE.md").read_text(encoding="utf-8")
    out={}
    for m in re.finditer(r"^##\s+\d+\.\s+.+?—\s+([^/\\n]+(?:/[^/\\n]+)?)\s*/\s*(EXP-\d+)\s*$",text,re.M):
        out[m.group(2)]=m.group(1).strip()
    # More permissive fallback for headings such as P0/P1 / EXP-003
    for m in re.finditer(r"^##\s+\d+\.\s+.+?—\s+(.+?)\s*/\s*(EXP-\d+)\s*$",text,re.M):
        out[m.group(2)]=m.group(1).strip()
    return out

SEARCH_PRIORITIES=parse_search_priorities()

def parse_experiments():
    text=(ROOT/"EXPERIMENTS.md").read_text(encoding="utf-8")
    heads=list(re.finditer(r"^###\s+(EXP-\d+)\s+—\s+(.+)$",text,re.M))
    out=[]
    for i,m in enumerate(heads):
        block=text[m.end():heads[i+1].start() if i+1<len(heads) else len(text)]
        raw_status=line_field(block,"Status") or ""
        status=experiment_status(raw_status)
        caps=parse_capability_ids(line_field(block,"Capabilities"))
        out.append({
          "experiment_id":m.group(1),
          "name":m.group(2).strip(),
          "status":status,
          "execution_scope":raw_status.replace("*", "").strip(),
          "priority_label":SEARCH_PRIORITIES.get(m.group(1),""),
          "capability_ids":caps,
          "opportunity":line_field(block,"Opportunity"),
          "hypothesis":line_field(block,"Hypothesis"),
          "next_action":line_field(block,"Next action"),
          "success":line_field(block,"Success"),
          "failure":line_field(block,"Failure"),
          "order":i+1
        })
    return out

EXPERIMENTS=parse_experiments()
EXP={x["experiment_id"]:x for x in EXPERIMENTS}

def priority_boost(label):
    t=(label or "").upper()
    if "P0/P1" in t: return CFG["scoring"]["p0_p1_boost"]
    if "P0" in t: return CFG["scoring"]["p0_boost"]
    if "P1" in t: return CFG["scoring"]["p1_boost"]
    return 0

def experiment_status_boost(exp_ids):
    b=0
    for eid in exp_ids:
        e=EXP.get(eid)
        if not e: continue
        if "RUNNING" in e["status"]: b=max(b,CFG["scoring"]["running_experiment_boost"])
        elif "READY" in e["status"]: b=max(b,CFG["scoring"]["ready_experiment_boost"])
        b=max(b,priority_boost(e.get("priority_label")))
    return b

def work_id(prefix,value):
    return "WORK:"+prefix+":"+hashlib.sha256(value.encode()).hexdigest()[:12]

candidates=[]

# Search seeds are already saturation- and coverage-aware.
for s in SEEDS:
    if s.get("work_action")=="await_external":
        continue
    errors=action_errors(s)
    if errors:
        raise SystemExit(f"{s['seed_id']}: {'; '.join(errors)}")
    st=s.get("seed_type")
    kind={
      "capability_gap":"capability_gap",
      "positive_dna_transfer":"positive_dna_transfer",
      "strategy_measurement":"strategy_measurement",
      "learning_measurement":"learning_measurement",
      "coverage_gap":"coverage_gap"
    }.get(st)
    if not kind: continue
    sid=s.get("strategy_id")
    base=float(s.get("priority") or 0)
    strat=CFG["scoring"]["strategy_allocation_weight"]*strategy_alloc.get(sid,0)
    expb=experiment_status_boost(s.get("experiment_ids") or [])
    score=round(min(120,base+strat+expb),2)
    packet=None
    if kind=="learning_measurement":
        packet=learning_packet_by_seed.get(s["seed_id"])
        if not packet:
            raise SystemExit(f"{s['seed_id']}: missing frozen learning measurement packet")
        if packet.get("strategy_id")!=sid:
            raise SystemExit(f"{s['seed_id']}: learning packet strategy mismatch")
        packet_seed=packet.get("seed") or {}
        if packet_seed.get("seed_id")!=s["seed_id"] or packet_seed.get("seed_type")!="learning_measurement":
            raise SystemExit(f"{s['seed_id']}: learning packet seed binding mismatch")
        packet_id=packet.get("packet_id")
        packet_sha=packet.get("packet_sha256")
        if not isinstance(packet_id,str) or not packet_id.startswith("LMP:"):
            raise SystemExit(f"{s['seed_id']}: invalid learning packet id")
        if not isinstance(packet_sha,str) or len(packet_sha)!=64:
            raise SystemExit(f"{s['seed_id']}: invalid learning packet sha256")
        item_id=work_id("learn",packet_id+"|"+packet_sha)
    else:
        packet_id=None
        packet_sha=None
        item_id=work_id("seed",s["seed_id"])
    candidate={
      "work_item_id":item_id,
      "work_kind":kind,
      "work_action":s.get("work_action","search"),
      "query_recipe_id":s.get("query_recipe_id"),
      "query_anchors":s.get("query_anchors") or [],
      "source_id":s["seed_id"],
      "title":s["seed_id"],
      "final_score":score,
      "score_components":{"base_priority":base,"strategy_allocation":round(strat,2),"experiment_boost":expb},
      "strategy_id":sid,
      "search_objective_id":s.get("search_objective_id"),
      "capability_ids":s.get("capability_ids") or [],
      "experiment_ids":s.get("experiment_ids") or [],
      "coverage_gap_ids":s.get("coverage_gap_ids") or [],
      "adjacency_root":None,
      "instructions":{
        "work_action":s.get("work_action","search"),
        "next_action":s.get("next_action"),
        "acceptance_target":s.get("acceptance_target"),
        "action_gate":s.get("action_gate"),
        "query_anchors":s.get("query_anchors") or [],
        "why_now":s.get("why_now"),
        "queries":s.get("query_templates") or [],
        "search_surfaces":s.get("search_surfaces") or [],
        "verification_gate":s.get("verification_gate"),
        "stop_conditions":s.get("stop_conditions") or []
      }
    }
    if packet_id:
        candidate["learning_measurement_packet_id"]=packet_id
        candidate["learning_measurement_packet_sha256"]=packet_sha
    candidates.append(candidate)

# Adjacency candidates.
for a in ADJ:
    sid=a.get("strategy_id")
    base=float(a.get("priority") or 0)
    strat=CFG["scoring"]["strategy_allocation_weight"]*strategy_alloc.get(sid,0)
    score=round(min(120,base+strat),2)
    candidates.append({
      "work_item_id":work_id("adj",a["adjacency_id"]),
      "work_kind":"adjacency",
      "work_action":"search",
      "source_id":a["adjacency_id"],
      "title":a["adjacency_id"],
      "final_score":score,
      "score_components":{"base_priority":base,"strategy_allocation":round(strat,2)},
      "strategy_id":sid,
      "search_objective_id":a.get("search_objective_id"),
      "capability_ids":[],
      "experiment_ids":[],
      "coverage_gap_ids":[],
      "adjacency_root":a.get("root_repository"),
      "instructions":{
        "why_now":a.get("why_expand"),
        "queries":a.get("query_templates") or [],
        "search_recipe":a.get("search_recipe") or [],
        "acceptance_target":a.get("verification_gate"),
        "verification_gate":a.get("verification_gate"),
        "stop_conditions":a.get("stop_conditions") or []
      }
    })

# READY/RUNNING experiments deserve slots before additional discovery.
for e in EXPERIMENTS:
    if e["status"] not in {"READY","RUNNING"}:
        continue
    base=CFG["scoring"]["running_experiment_base"] if e["status"]=="RUNNING" else CFG["scoring"]["ready_experiment_base"]
    pb=priority_boost(e.get("priority_label"))
    score=round(base+pb-max(0,e["order"]-1)*0.25,2)
    candidates.append({
      "work_item_id":work_id("experiment",e["experiment_id"]),
      "work_kind":"experiment_execution",
      "work_action":experiment_action(e["capability_ids"]),
      "source_id":e["experiment_id"],
      "title":e["experiment_id"]+" — "+e["name"],
      "final_score":score,
      "score_components":{"readiness_base":base,"portfolio_priority_boost":pb,"queue_order_adjustment":round(-max(0,e["order"]-1)*0.25,2)},
      "strategy_id":None,
      "search_objective_id":None,
      "capability_ids":e.get("capability_ids") or [],
      "experiment_ids":[e["experiment_id"]],
      "coverage_gap_ids":[],
      "adjacency_root":None,
      "instructions":{
        "work_action":experiment_action(e["capability_ids"]),
        "execution_scope":e["execution_scope"],
        "why_now":"Experiment is "+e["status"]+" and should be executed/falsified before searching for redundant components.",
        "next_action":e.get("next_action"),
        "acceptance_target":e.get("success") or e.get("next_action"),
        "hypothesis":e.get("hypothesis"),
        "success":e.get("success"),
        "failure":e.get("failure"),
        "stop_conditions":capability_stops(e["capability_ids"])+["Do not broaden into generic discovery unless execution exposes a named technical gap.", "READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external."]
      }
    })
    # Separate independent verifier candidate so red-team capacity is explicit.
    vbase=CFG["scoring"]["verification_base"]+(4 if e["status"]=="RUNNING" else 0)+pb
    candidates.append({
      "work_item_id":work_id("verify",e["experiment_id"]),
      "work_kind":"independent_verification",
      "work_action":experiment_action(e["capability_ids"]),
      "source_id":"VERIFY:"+e["experiment_id"],
      "title":"Independent verification — "+e["experiment_id"],
      "final_score":round(vbase-max(0,e["order"]-1)*0.2,2),
      "score_components":{"verification_base":CFG["scoring"]["verification_base"],"status_boost":4 if e["status"]=="RUNNING" else 0,"portfolio_priority_boost":pb},
      "strategy_id":"STRAT:evaluation-target-independence" if "STRAT:evaluation-target-independence" in strategy_alloc else None,
      "search_objective_id":"OBJ:independent-evaluation",
      "capability_ids":e.get("capability_ids") or [],
      "experiment_ids":[e["experiment_id"]],
      "coverage_gap_ids":[],
      "adjacency_root":None,
      "instructions":{
        "work_action":experiment_action(e["capability_ids"]),
        "next_action":e.get("next_action"),
        "acceptance_target":e.get("success") or e.get("next_action"),
        "execution_scope":e["execution_scope"],
        "verification_mode":"experiment_falsification",
        "independence_requirements":["Freeze the exact claim, fixture and inspected revision before comparison.", "Use an independently sourced expected result or different implementation lineage.", "Preserve PASS/DISAGREE/UNSUPPORTED/ORACLE_UNAVAILABLE separately; repeated discovery does not establish independent VERIFIED."],
        "why_now":"Attempt to falsify the experiment using an independent oracle/fixture/implementation and negative controls.",
        "hypothesis":e.get("hypothesis"),
        "success":e.get("success"),
        "failure":e.get("failure"),
        "stop_conditions":capability_stops(e["capability_ids"])+["Do not reuse the target system's own outputs as the sole oracle.","Preserve disagreements instead of forcing consensus."]
      }
    })

# Fallback verifier for active search hypotheses when no live experiment is READY/RUNNING.
if not any(c.get("work_kind")=="independent_verification" for c in candidates):
    seed_pool=[s for s in SEEDS if s.get("work_action", "search")=="search" and s.get("seed_type") in {"capability_gap","coverage_gap","positive_dna_transfer"}]
    seed_pool=sorted(seed_pool,key=lambda s:(-(float(s.get("priority") or 0)),s.get("seed_id") or ""))
    if seed_pool:
        s=seed_pool[0]
        candidates.append({
          "work_item_id":work_id("verify-seed",s["seed_id"]),
          "work_kind":"independent_verification",
          "work_action":"search",
          "query_recipe_id":None,
          "query_anchors":[],
          "source_id":"VERIFY:"+s["seed_id"],
          "title":"Independent verification — "+s["seed_id"],
          "final_score":float(CFG["scoring"]["verification_base"]),
          "score_components":{"verification_base":CFG["scoring"]["verification_base"],"fallback_target":"top_active_search_hypothesis"},
          "strategy_id":"STRAT:evaluation-target-independence" if "STRAT:evaluation-target-independence" in strategy_alloc else None,
          "search_objective_id":"OBJ:independent-evaluation",
          "capability_ids":[],
          "experiment_ids":[],
          "coverage_gap_ids":s.get("coverage_gap_ids") or [],
          "adjacency_root":None,
          "instructions":{
            "why_now":"No READY/RUNNING experiment currently needs a dedicated verifier, so use reserved verification capacity to independently challenge the highest-ranked active search hypothesis before it becomes accepted positive training.",
            "queries":[],
            "verification_mode":"hypothesis_challenge",
            "can_establish_verified":False,
            "acceptance_target":"A falsifiable claim plus an independent comparator plan; no pre-discovery hypothesis is independently VERIFIED.",
            "search_surfaces":["existing source/test evidence","independent negative controls"],
            "verification_gate":"Pre-discovery hypothesis challenge only. Freeze a candidate claim and exact revision first; obtain an independent oracle/fixture before any VERIFIED finding. Do not repeat the discovery query and call agreement verification.",
            "stop_conditions":(s.get("stop_conditions") or [])+["Do not duplicate the discovery agent's inspection path.","Preserve disagreement and uncertainty rather than forcing a PASS."]
          }
        })

# One explicit wildcard candidate.
candidates.append({
  "work_item_id":"WORK:wildcard:rare-weird",
  "work_kind":"wildcard",
  "work_action":"search",
  "source_id":"WILDCARD:rare-weird",
  "title":"Rare / weird wildcard exploration",
  "final_score":75.0,
  "score_components":{"protected_exploration_budget":75},
  "strategy_id":None,
  "search_objective_id":None,
  "capability_ids":[],
  "experiment_ids":[],
  "coverage_gap_ids":[],
  "adjacency_root":None,
  "instructions":{
    "why_now":"Preserve high-recall discovery for technologies the current capability graph cannot predict.",
    "queries":[],
    "search_surfaces":["zero-star and low-star repositories","archived repositories","obscure university/lab/government organizations","unusual protocol and hardware integrations"],
    "acceptance_target":"A concrete source/test finding outside the current ontology, or an honest no-find disposition.",
    "verification_gate":"Weirdness is only a discovery prior; retain only concrete technical evidence.",
    "stop_conditions":["Do not chase credentials, private/confidential material or accidental secrets.","No padding: a no-find run is valid."]
  }
})

# Stable generation fingerprint.
fingerprint=json.dumps({
 "policy":POLICY,
 "seeds":SEEDS,
 "adj_ids":[(x.get("adjacency_id"),x.get("priority")) for x in ADJ],
 "experiments":EXPERIMENTS,
 "candidate_instructions":[(x["work_item_id"],x.get("work_action"),x["instructions"]) for x in candidates],
 "allocator_policy":CFG
},sort_keys=True,default=str)
gen_hash=hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
generation_id="ALLOCGEN:"+gen_hash

# Candidate sort.
for candidate in candidates:
    errors=action_errors(candidate)
    if errors:
        raise SystemExit(f"{candidate['work_item_id']}: {'; '.join(errors)}")
candidates.sort(key=lambda x:(-x["final_score"],x["work_item_id"]))

slots=CFG["slots"]
cons=CFG["constraints"]
used_work=set()
cap_counts=defaultdict(int)
exp_counts=defaultdict(int)
strategy_counts=defaultdict(int)
root_counts=defaultdict(int)
assignments=[]

def fits(c,slot):
    if c["work_kind"] not in slot["accepts"]:
        return False
    if c["work_item_id"] in used_work:
        return False
    for cid in c.get("capability_ids") or []:
        if cap_counts[cid]>=cons["max_assignments_per_capability"]:
            return False
    for eid in c.get("experiment_ids") or []:
        if exp_counts[eid]>=cons["max_assignments_per_experiment"]:
            return False
    sid=c.get("strategy_id")
    if sid and strategy_counts[sid]>=cons["max_assignments_per_strategy"]:
        return False
    root=c.get("adjacency_root")
    if root and root_counts[root]>=cons["max_adjacency_assignments_per_root"]:
        return False
    return True

for slot in slots:
    pool=[c for c in candidates if fits(c,slot)]
    if not pool:
        # Fallback only within semantically close roles; wildcard remains dedicated.
        fallbacks={
          "experiment":["capability_gap","positive_dna_transfer"],
          "coverage":["positive_dna_transfer","capability_gap"],
          "adjacency":["positive_dna_transfer"],
          "measurement":["strategy_measurement","capability_gap"],
          "verification":["independent_verification"],
          "wildcard":["wildcard"]
        }.get(slot["role"],[])
        pool=[c for c in candidates if c["work_kind"] in fallbacks and fits(c,{**slot,"accepts":fallbacks})]
    if not pool:
        raise SystemExit(f"No candidate available for {slot['slot_id']} ({slot['role']})")
    c=pool[0]
    aid=f"ASSIGN:{gen_hash}:{slot['slot_id'].lower()}"
    a={
      "assignment_id":aid,
      "allocator_generation_id":generation_id,
      "portfolio_policy_generation_id":PORTFOLIO_POLICY_ID,
      "slot_id":slot["slot_id"],
      "slot_role":slot["role"],
      "slot_label":slot["label"],
      "work_item_id":c["work_item_id"],
      "work_kind":c["work_kind"],
      "work_action":c.get("work_action","search"),
      "query_recipe_id":c.get("query_recipe_id"),
      "query_anchors":c.get("query_anchors") or [],
      "source_id":c["source_id"],
      "title":c["title"],
      "final_score":c["final_score"],
      "score_components":c["score_components"],
      "strategy_id":c.get("strategy_id"),
      "search_objective_id":c.get("search_objective_id"),
      "capability_ids":c.get("capability_ids") or [],
      "experiment_ids":c.get("experiment_ids") or [],
      "coverage_gap_ids":c.get("coverage_gap_ids") or [],
      "adjacency_root":c.get("adjacency_root"),
      "learning_measurement_packet_id":c.get("learning_measurement_packet_id"),
      "learning_measurement_packet_sha256":c.get("learning_measurement_packet_sha256"),
      "instructions":c["instructions"]
    }
    assignments.append(a)
    used_work.add(c["work_item_id"])
    for cid in a["capability_ids"]: cap_counts[cid]+=1
    for eid in a["experiment_ids"]: exp_counts[eid]+=1
    if a["strategy_id"]: strategy_counts[a["strategy_id"]]+=1
    if a["adjacency_root"]: root_counts[a["adjacency_root"]]+=1

def write_jsonl(path,rows):
    (INTEL/path).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")

write_jsonl("hunt_candidates.jsonl",candidates)
write_jsonl("hunt_allocations.jsonl",assignments)

kind_counts=defaultdict(int)
role_counts=defaultdict(int)
for a in assignments:
    kind_counts[a["work_kind"]]+=1
    role_counts[a["slot_role"]]+=1

metrics={
 "schema_version":1,
 "allocator_generation_id":generation_id,
 "portfolio_policy_generation_id":PORTFOLIO_POLICY_ID,
 "candidate_count":len(candidates),
 "assignment_count":len(assignments),
 "slot_count":len(slots),
 "work_kind_counts":dict(kind_counts),
 "slot_role_counts":dict(role_counts),
 "awaiting_external_seed_count":sum(s.get("work_action")=="await_external" for s in SEEDS),
 "work_action_counts":{action:sum(a["work_action"]==action for a in assignments) for action in sorted({a["work_action"] for a in assignments})},
 "max_capability_concentration":max(cap_counts.values()) if cap_counts else 0,
 "max_experiment_concentration":max(exp_counts.values()) if exp_counts else 0,
 "max_strategy_concentration":max(strategy_counts.values()) if strategy_counts else 0,
 "constraints":cons
}
(INTEL/"allocator_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

plan=["# UNIFIED HUNT PLAN","",f"Allocator generation: **{generation_id}**",f"Portfolio policy: **{PORTFOLIO_POLICY_ID}**","",
      "This is the current 14-slot work plan. Scores are scheduling priorities, not claims of repository or commercial value.","",
      "| Slot | Role | Score | Work | Capability | Experiment | Source |",
      "|---|---|---:|---|---|---|---|"]
for a in assignments:
    plan.append(f"| {a['slot_id']} | {a['slot_role']} | {a['final_score']:.1f} | {a['title']} | {', '.join(a['capability_ids']) or '—'} | {', '.join(a['experiment_ids']) or '—'} | {a['source_id']} |")
plan+=["","## Assignment packets",""]
for a in assignments:
    i=a["instructions"]
    plan += [f"### {a['slot_id']} — {a['title']}",
             f"- Assignment ID: {a['assignment_id']}",
             f"- Work kind/action: **{a['work_kind']} / {a['work_action']}**",
             f"- Score: **{a['final_score']:.2f}** — {json.dumps(a['score_components'],sort_keys=True)}",
             f"- Strategy/objective: {a.get('strategy_id') or 'n/a'} / {a.get('search_objective_id') or 'n/a'}",
             f"- Capability/experiment: {', '.join(a['capability_ids']+a['experiment_ids']) or 'cross-domain'}",
             f"- Why now: {i.get('why_now') or '—'}"]
    if i.get("execution_scope"): plan.append(f"- Execution scope: {i['execution_scope']}")
    if i.get("next_action"): plan.append(f"- Next action: {i['next_action']}")
    if i.get("acceptance_target"): plan.append(f"- Acceptance target: {i['acceptance_target']}")
    if i.get("verification_mode"): plan.append(f"- Verification mode: {i['verification_mode']}")
    if i.get("independence_requirements"): plan.append(f"- Independence requirements: {'; '.join(i['independence_requirements'])}")
    if i.get("hypothesis"): plan.append(f"- Hypothesis: {i['hypothesis']}")
    if i.get("queries"):
        plan.append("- Queries:")
        for q in i["queries"]: plan.append("  - "+q)
    if i.get("search_surfaces"): plan.append(f"- Search surfaces: {', '.join(i['search_surfaces'])}")
    if i.get("search_recipe"):
        plan.append("- Search recipe:")
        for q in i["search_recipe"]: plan.append("  - "+q)
    if i.get("verification_gate"): plan.append(f"- Verification gate: {i['verification_gate']}")
    if i.get("success"): plan.append(f"- Success: {i['success']}")
    if i.get("failure"): plan.append(f"- Failure: {i['failure']}")
    if i.get("stop_conditions"): plan.append(f"- Stop conditions: {'; '.join(i['stop_conditions'])}")
    plan.append("")
(INTEL/"HUNT_PLAN.md").write_text("\n".join(plan),encoding="utf-8")

rep=["# HUNT ALLOCATOR REPORT","",f"- Generation: **{generation_id}**",
     f"- Candidate work items: **{len(candidates)}**",f"- Assigned slots: **{len(assignments)} / {len(slots)}**","",
     "## Portfolio mix","",
     "| Work kind | Slots |","|---|---:|"]
for k,v in sorted(kind_counts.items()): rep.append(f"| {k} | {v} |")
rep += ["","## Concentration controls","",
        f"- Maximum assignments on one capability: **{metrics['max_capability_concentration']}** / allowed {cons['max_assignments_per_capability']}",
        f"- Maximum assignments on one experiment: **{metrics['max_experiment_concentration']}** / allowed {cons['max_assignments_per_experiment']}",
        f"- Maximum assignments using one strategy: **{metrics['max_strategy_concentration']}** / allowed {cons['max_assignments_per_strategy']}",
        "","## Guardrails",""]
for g in CFG.get("guardrails",[]): rep.append("- "+g)
rep += ["","## Interpretation","",
        "- The allocator combines existing measured intelligence; it does not create new evidence.",
        "- READY/RUNNING experiments can outrank more repository discovery.",
        "- Coverage and adjacency slots preserve exploration breadth while hard concentration caps prevent swarm collapse.",
        "- One wildcard slot is always reserved for discoveries outside the current ontology.",
        "- Manual overrides should be recorded in V9 run telemetry rather than silently editing historical scores.",""]
(INTEL/"ALLOCATOR_REPORT.md").write_text("\n".join(rep),encoding="utf-8")
print(json.dumps(metrics))
