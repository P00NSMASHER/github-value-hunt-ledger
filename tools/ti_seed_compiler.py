#!/usr/bin/env python3
import json, re
from collections import defaultdict
from ti_common import INTEL, ROOT, load_jsonl, write_jsonl, slug

POLICY = json.loads((INTEL / "search_policy.json").read_text(encoding="utf-8"))
CAPS = {x["capability_id"]: x for x in load_jsonl("capabilities.jsonl")}
STRATS = {x["strategy_id"]: x for x in load_jsonl("search_strategies.jsonl")}
RUNS = [x for x in load_jsonl("search_runs.jsonl") if x.get("measurement_quality") in {"prospective","benchmark"}]
OBJECTIVES_CFG = json.loads((INTEL / "search_objectives.json").read_text(encoding="utf-8"))
OBJECTIVE_IDS = {x["search_objective_id"] for x in OBJECTIVES_CFG.get("objectives", [])}
COVERAGE_GAPS = load_jsonl("exploration_gap_queue.jsonl") if (INTEL / "exploration_gap_queue.jsonl").exists() else []

SATURATION_BY_CAP = {
    x["label"]: x for x in load_jsonl("research_neighborhoods.jsonl")
    if x.get("neighborhood_type") == "capability"
} if (INTEL / "research_neighborhoods.jsonl").exists() else {}

def saturation_adjust(cid):
    row=SATURATION_BY_CAP.get(cid) or {}
    status=row.get("status","INSUFFICIENT")
    adjustment={
        "INSUFFICIENT":0,
        "PRODUCTIVE":5,
        "BALANCED":0,
        "SATURATING":-12,
        "SATURATED":-25
    }.get(status,0)
    return status, adjustment, row.get("recommended_action","MEASURE_MORE")


HIGH_SIGNAL = [
    "effective-dated","supersession","append-only","exactly-once","fail-closed",
    "negative control","negative controls","reversal","idempotency","immutable",
    "bitemporal","provenance","source span","evidence","human review","review",
    "deterministic","replay","settlement","partial","split","ambiguity","unknown",
    "rollback","signature","schema","calibration","conservation","one-use",
    "counter-event","versioned","audit trail","state machine","hard lock",
    "semantic","coverage","tombstone","retry","reconcile","source health",
    "effective window","authority","lineage","approval","conflict","independent"
]
GENERIC_STOP = {
    "the","and","for","with","from","that","this","into","without","while","before",
    "after","under","only","where","when","which","what","their","must","remain",
    "system","systems","current","component","components","target","targets",
    "buyer","buyers","product","products","commercial","commercially","test","tests",
    "source","sources","data","code","repo","repository","repositories","ability",
    "capability","capabilities","missing","piece","next","validated","validation"
}

def line_field(block, label):
    m = re.search(r"^-\s*" + re.escape(label) + r":\s*(.*)$", block, re.I|re.M)
    return m.group(1).strip() if m else None

def parse_master():
    text=(ROOT/"MASTER.md").read_text(encoding="utf-8")
    heads=list(re.finditer(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\s+—\s+.*)?$",text,re.M))
    rows=[]
    for i,m in enumerate(heads):
        block=text[m.end(): heads[i+1].start() if i+1<len(heads) else len(text)]
        score_txt=line_field(block,"Score") or ""
        sm=re.search(r"(\d+(?:\.\d+)?)/30",score_txt)
        rows.append({
            "repo":m.group(1),
            "score":float(sm.group(1)) if sm else None,
            "capability":line_field(block,"Capability") or "",
            "why":line_field(block,"Why it wins") or "",
            "wedge":line_field(block,"Monetization / first paid wedge") or ""
        })
    return rows

def parse_experiments():
    text=(ROOT/"EXPERIMENTS.md").read_text(encoding="utf-8")
    heads=list(re.finditer(r"^###\s+(EXP-\d+)\s+—\s+(.+)$",text,re.M))
    out=[]
    for i,m in enumerate(heads):
        block=text[m.end(): heads[i+1].start() if i+1<len(heads) else len(text)]
        status=(line_field(block,"Status") or "").replace("*","").strip()
        cap_line=line_field(block,"Capabilities") or ""
        out.append({
            "experiment_id":m.group(1),
            "name":m.group(2).strip(),
            "status":status,
            "capability_ids":re.findall(r"CAP-\d{3,}",cap_line),
            "next_action":line_field(block,"Next action") or ""
        })
    return out

MASTER=parse_master()
EXPERIMENTS=parse_experiments()
EXP_BY_CAP=defaultdict(list)
for e in EXPERIMENTS:
    for c in e["capability_ids"]:
        EXP_BY_CAP[c].append(e)

def signatures(text, limit=7):
    lower=(text or "").lower()
    found=[]
    for phrase in HIGH_SIGNAL:
        if phrase in lower and phrase not in found:
            found.append(phrase)
    freq=defaultdict(int)
    for w in re.findall(r"[a-z][a-z0-9-]{4,}",lower):
        if w not in GENERIC_STOP and not w.startswith("cap-") and not w.startswith("exp-"):
            freq[w]+=1
    for w,_ in sorted(freq.items(), key=lambda kv:(-kv[1],kv[0])):
        if w not in found:
            found.append(w)
        if len(found)>=limit:
            break
    return found[:limit]

def choose_strategy(text):
    t=(text or "").lower()
    prefs=[]
    if any(x in t for x in ["effective","supersession","rule","authority","currentness","jurisdiction"]):
        prefs += ["STRAT:rule-period-authority-version-audit","STRAT:first-party-production-source-triangulation"]
    if any(x in t for x in ["unknown","retry","response-loss","idempot","reversal","settlement","one-use"]):
        prefs += ["STRAT:acceptance-path-transition-inspection","STRAT:capability-conjunction-search-claim-tracing"]
    if any(x in t for x in ["coverage","complete","census","manifest","inventory","missing subject"]):
        prefs += ["STRAT:fail-open-boundary-archaeology","STRAT:first-party-production-source-triangulation"]
    if any(x in t for x in ["protocol","instrument","vendor format","compatib","migration"]):
        prefs += ["STRAT:protocol-regression-archaeology-for-pre-fat-systems","STRAT:cross-source-emergence-triangulation"]
    if any(x in t for x in ["paper","research","algorithm","emerging"]):
        prefs += ["STRAT:paper-research-artifact-production-descendant","STRAT:cross-source-emergence-triangulation"]
    prefs += ["STRAT:capability-conjunction-search-claim-tracing"]
    for sid in prefs:
        if sid in STRATS and STRATS[sid].get("status")=="active":
            return sid
    active=[x for x in STRATS.values() if x.get("status")=="active"]
    return active[0]["strategy_id"] if active else next(iter(STRATS))

def choose_objective(text):
    t=(text or "").lower()
    mapping=[
      ("OBJ:exactly-once-settlement",["settlement","reversal","refund","payment","one-use","idempot"]),
      ("OBJ:ambiguity-reconciliation",["unknown","retry","response-loss","ambiguous"]),
      ("OBJ:completeness-proof",["coverage","complete","census","manifest","missing subject"]),
      ("OBJ:current-rule-authority",["effective","rule","currentness","jurisdiction","supersession"]),
      ("OBJ:authority-lineage",["authority","contract","approval","ownership","entitlement"]),
      ("OBJ:identity-lineage",["identity","correlation","lineage","join","referent"]),
      ("OBJ:runtime-side-effect",["state machine","mutation","dispatch","side effect","approval"]),
      ("OBJ:protocol-regression",["protocol","compatibility","migration","instrument"]),
      ("OBJ:research-lineage",["paper","research","descendant"]),
      ("OBJ:emergence-triangulation",["emerging","convergence","independent implementation"]),
      ("OBJ:ingestion-durability",["ingestion","source health","historical durability"]),
      ("OBJ:independent-evaluation",["independent","challenger","falsif","oracle"])
    ]
    for oid,keys in mapping:
        if oid in OBJECTIVE_IDS and any(k in t for k in keys):
            return oid
    return "OBJ:independent-evaluation" if "OBJ:independent-evaluation" in OBJECTIVE_IDS else sorted(OBJECTIVE_IDS)[0]

def query_templates(sigs):
    s=[x for x in sigs if x][:4]
    if not s:
        return []
    fmt=lambda x: '"' + x + '"' if " " in x else x
    out=[]
    if len(s)>=3:
        out.append(" ".join(fmt(x) for x in s[:3]))
        out.append(" ".join(fmt(x) for x in [s[0],s[2]])+" path:tests")
    elif len(s)==2:
        out.append(" ".join(fmt(x) for x in s))
        out.append(" ".join(fmt(x) for x in s)+" path:tests")
    else:
        out.append(fmt(s[0])+" tests schema")
    out.append(" ".join(fmt(x) for x in s[:2])+" audit replay")
    return list(dict.fromkeys(out))

def experiment_bonus(cid):
    bonus=0
    ids=[]
    for e in EXP_BY_CAP.get(cid,[]):
        ids.append(e["experiment_id"])
        st=e["status"].upper()
        if "READY" in st:
            bonus=max(bonus,8)
        elif "RUNNING" in st:
            bonus=max(bonus,6)
    return bonus,sorted(set(ids))

perf=defaultdict(lambda:{"runs":0,"inspected":0,"retained":0,"promoted":0,"new_cap_runs":0,"experiment_runs":0})
for r in RUNS:
    for seed_id in r.get("seed_ids") or []:
        p=perf[seed_id]
        p["runs"]+=1
        p["inspected"]+=(r.get("deep_inspected") or 0)
        p["retained"]+=(r.get("retained_count") or 0)
        p["promoted"]+=(r.get("master_promoted_count") or 0)
        p["new_cap_runs"]+=1 if r.get("new_capability_ids") else 0
        p["experiment_runs"]+=1 if r.get("experiment_ids") else 0

def perf_adjust(seed_id):
    p=perf[seed_id]
    if p["runs"]<3 or p["inspected"]<10:
        return 0
    rate=p["retained"]/max(p["inspected"],1)
    if p["promoted"]>0 or p["new_cap_runs"]>0:
        return 8
    if rate<0.10 and p["experiment_runs"]==0:
        return -10
    if rate<0.25:
        return -4
    return 2

seeds=[]
blocked_caps=set()
for d in POLICY.get("domain_constraints",[]):
    blocked_caps.update(d.get("blocked_exclusive_capability_ids") or [])

for gap in POLICY.get("priority_capability_gaps",[])[:10]:
    cid=gap["capability_id"]
    if cid in blocked_caps or cid not in CAPS:
        continue
    c=CAPS[cid]
    context=" ".join(filter(None,[c.get("ability"),c.get("missing_piece"),c.get("next_falsifiable_test")]))
    sigs=signatures(context)
    strategy=choose_strategy(context)
    objective=choose_objective(context)
    exp_bonus,exp_ids=experiment_bonus(cid)
    seed_id=f"SEED:gap:{cid.lower()}"
    base=min(95,55+5*int(gap.get("gap_score") or 0)+exp_bonus-2*int(gap.get("run_attention") or 0))
    sat_status,sat_adjust,sat_action=saturation_adjust(cid)
    priority=max(1,min(100,base+perf_adjust(seed_id)+sat_adjust))
    seeds.append({
      "seed_id":seed_id,
      "seed_type":"capability_gap",
      "priority":priority,
      "strategy_id":strategy,
      "search_objective_id":objective,
      "capability_ids":[cid],
      "experiment_ids":exp_ids,
      "source_nodes":[cid],
      "saturation_status":sat_status,
      "saturation_adjustment":sat_adjust,
      "saturation_action":sat_action,
      "why_now":f"{cid} is a current high-information gap (gap score {gap.get('gap_score')}, prior run attention {gap.get('run_attention')}). Saturation: {sat_status} ({sat_adjust:+d} priority). Missing piece: {c.get('missing_piece') or 'unspecified'}.",
      "required_signatures":sigs,
      "query_templates":query_templates(sigs),
      "search_surfaces":["GitHub code search","GitHub repository search","source/tests/schema/history","author/org adjacency"],
      "verification_gate":"Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.",
      "stop_conditions":["Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.","Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears."],
      "authorization_basis":"adaptive_policy_capability_gap",
      "exclude_domains":[],
      "performance":perf[seed_id]
    })

seen_sig=set()
dna_count=0
for m in sorted(MASTER,key=lambda x: (-(x["score"] or 0),x["repo"])):
    text=" ".join([m["capability"],m["why"]])
    sigs=signatures(text)
    if len(sigs)<3:
        continue
    key=tuple(sorted(sigs[:4]))
    if key in seen_sig:
        continue
    seen_sig.add(key)
    seed_id="SEED:dna:"+slug(m["repo"].replace("/","-"))
    base=60+min(15,len(sigs)*2)+int(max(0,(m["score"] or 24)-24))
    priority=max(1,min(90,base+perf_adjust(seed_id)))
    origin_domain="freight" if any(x in (m["repo"]+" "+text).lower() for x in ["freight","trenova","opstrax","ratecon","shipment"]) else None
    seeds.append({
      "seed_id":seed_id,
      "seed_type":"positive_dna_transfer",
      "priority":priority,
      "strategy_id":choose_strategy(text),
      "search_objective_id":choose_objective(text),
      "capability_ids":[],
      "experiment_ids":[],
      "source_nodes":["REPO:"+m["repo"]],
      "why_now":f"Transfer the load-bearing implementation DNA of MASTER leader {m['repo']} into unrelated verticals. Why it wins: {m['why']}",
      "required_signatures":sigs,
      "query_templates":query_templates(sigs),
      "search_surfaces":["GitHub code search","low-star/zero-star repository search","archived repository archaeology","author/org adjacency","dependency/consumer adjacency"],
      "verification_gate":"A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo.",
      "stop_conditions":["Do not search the originating vertical merely because its MASTER leader scored highly.","Reject forks/clones that add no independent implementation evidence."],
      "authorization_basis":"exploration_positive_dna_transfer",
      "exclude_domains":[origin_domain] if origin_domain else [],
      "performance":perf[seed_id]
    })
    dna_count+=1
    if dna_count>=6:
        break

gaps=[s for s in seeds if s["seed_type"]=="capability_gap"]
non_saturated_gaps=[s for s in gaps if s.get("saturation_status")!="SATURATED"]
if non_saturated_gaps:
    gaps=non_saturated_gaps
for i,cg in enumerate(COVERAGE_GAPS[:5]):
    if not gaps:
        break
    g=gaps[i % len(gaps)]
    cid=g["capability_ids"][0] if g.get("capability_ids") else None
    if not cid:
        continue
    seed_id="SEED:coverage:"+slug(cg["coverage_gap_id"].replace("COV:",""))+":"+cid.lower()
    filters=(cg.get("query_variants") or [])[:2]
    qbase=(g.get("query_templates") or [])[:2]
    qs=[]
    for filt in filters:
        for q in qbase:
            qs.append((q+" "+filt).strip())
    qs=list(dict.fromkeys(qs))
    if not qs:
        continue
    coverage_priority=float(cg.get("priority") or 0)
    base_priority=float(g.get("priority") or 0)
    priority=max(1,min(92,round(.55*coverage_priority+.45*base_priority+perf_adjust(seed_id))))
    seeds.append({
      "seed_id":seed_id,
      "seed_type":"coverage_gap",
      "priority":priority,
      "strategy_id":g["strategy_id"],
      "search_objective_id":g["search_objective_id"],
      "capability_ids":g.get("capability_ids") or [],
      "experiment_ids":g.get("experiment_ids") or [],
      "coverage_gap_ids":[cg["coverage_gap_id"]],
      "coverage_dimension":cg.get("dimension_id"),
      "coverage_target":cg.get("target_id"),
      "source_nodes":[cg["coverage_gap_id"]]+(g.get("capability_ids") or []),
      "saturation_status":g.get("saturation_status"),
      "saturation_adjustment":g.get("saturation_adjustment",0),
      "saturation_action":g.get("saturation_action"),
      "why_now":f"Intersect exploration blind spot {cg['coverage_gap_id']} ({cg.get('target_label')}: {cg.get('observed_unique_repositories')}/{cg.get('target_min_repositories')}) with {cid}, an active high-value capability gap. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.",
      "required_signatures":g.get("required_signatures") or [],
      "query_templates":qs,
      "search_surfaces":["GitHub repository search","GitHub code search"]+(g.get("search_surfaces") or []),
      "verification_gate":g["verification_gate"]+" Coverage membership alone never raises evidence quality.",
      "stop_conditions":(g.get("stop_conditions") or [])+["If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar."],
      "authorization_basis":"coverage_blind_spot_intersection",
      "exclude_domains":g.get("exclude_domains") or [],
      "performance":perf[seed_id]
    })

zero=[x for x in POLICY.get("strategy_allocation",[]) if int(x.get("runs") or 0)==0]
for i,row in enumerate(zero[:3]):
    if not gaps:
        break
    g=gaps[i % len(gaps)]
    sid=row["strategy_id"]
    seed_id="SEED:measure:"+slug(sid.replace("STRAT:",""))+"-"+g["capability_ids"][0].lower()
    priority=max(1,min(82,58+round(100*float(row.get("allocation") or 0))+perf_adjust(seed_id)))
    seeds.append({
      "seed_id":seed_id,
      "seed_type":"strategy_measurement",
      "priority":priority,
      "strategy_id":sid,
      "search_objective_id":g["search_objective_id"],
      "capability_ids":g["capability_ids"],
      "experiment_ids":g["experiment_ids"],
      "source_nodes":[sid]+g["capability_ids"],
      "why_now":f"{sid} has no measured runs but receives exploration allocation. Pair it with {g['capability_ids'][0]} so the hunt searches a real gap and reduces strategy measurement debt.",
      "required_signatures":g["required_signatures"],
      "query_templates":g["query_templates"],
      "search_surfaces":g["search_surfaces"],
      "verification_gate":"Use the named strategy consistently enough to make the run comparable, while preserving the same evidence bar as ordinary discovery.",
      "stop_conditions":["Do not turn a measurement run into an unrestricted domain sweep.","A no-find result is valid data; do one recall-rescue pass, then stop."],
      "authorization_basis":"strategy_measurement_debt",
      "exclude_domains":g.get("exclude_domains",[]),
      "performance":perf[seed_id]
    })

seeds.sort(key=lambda x:(-x["priority"],x["seed_id"]))
write_jsonl("search_seeds.jsonl",seeds)

metrics={
  "schema_version":1,
  "seed_count":len(seeds),
  "by_type":{},
  "seeds_with_measured_runs":sum(1 for s in seeds if s["performance"]["runs"]>0),
  "performance_threshold":{"min_runs":3,"min_inspections":10}
}
for s in seeds:
    metrics["by_type"][s["seed_type"]]=metrics["by_type"].get(s["seed_type"],0)+1
(INTEL/"seed_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
 "# SEARCH SEEDS","",
 "Generated search hypotheses from the current adaptive policy, capability gaps and MASTER positive-training DNA. These are ranked hypotheses, not commands.","",
 "Use a seed when it matches an authorized active gap. Record its seed_id in the V5 search-run record. Free exploration remains allowed and should use seed_mode free_exploration with an empty seed_ids list.","",
 "## Top ranked seeds","",
 "| Priority | Seed | Type | Strategy | Capability | Why now |",
 "|---:|---|---|---|---|---|"
]
for s in seeds[:20]:
    caps=", ".join(s["capability_ids"]) or "cross-domain"
    why=s["why_now"].replace("|","/")[:220]
    lines.append(f"| {s['priority']} | {s['seed_id']} | {s['seed_type']} | {s['strategy_id']} | {caps} | {why} |")
lines += ["","## Seed packets",""]
for s in seeds[:15]:
    lines += [
      f"### {s['seed_id']} — priority {s['priority']}",
      f"- Type: {s['seed_type']}",
      f"- Strategy: {s['strategy_id']}",
      f"- Objective: {s['search_objective_id']}",
      f"- Capability/experiment: {', '.join(s['capability_ids']+s['experiment_ids']) or 'cross-domain exploration'}",
      f"- Saturation/status: {s.get('saturation_status','n/a')} / adjustment {s.get('saturation_adjustment',0):+d} / action {s.get('saturation_action','n/a')}",
      f"- Why now: {s['why_now']}",
      f"- Required signatures: {', '.join(s['required_signatures']) or 'none generated'}",
      "- Query templates:"
    ]
    for q in s["query_templates"]:
        lines.append("  - "+q)
    lines += [
      f"- Search surfaces: {', '.join(s['search_surfaces'])}",
      f"- Verification gate: {s['verification_gate']}",
      f"- Stop conditions: {'; '.join(s['stop_conditions'])}",
      f"- Exclude domains: {', '.join(s['exclude_domains']) or 'none'}",
      f"- Measured seed history: {s['performance']['runs']} runs / {s['performance']['inspected']} inspections / {s['performance']['retained']} retained / {s['performance']['promoted']} MASTER promotions.",""
    ]
(INTEL/"SEARCH_SEEDS.md").write_text("\n".join(lines),encoding="utf-8")

perf_lines=[
 "# SEED PERFORMANCE","",
 "Seed-level performance becomes meaningful only after hunters record V5 seed_ids. Priority does not imply proven superiority.","",
 "| Seed | Runs | Inspected | Retained | MASTER | New-cap runs | Experiment runs | Evidence |",
 "|---|---:|---:|---:|---:|---:|---:|---|"
]
for s in seeds:
    p=s["performance"]
    evidence="sufficient" if p["runs"]>=3 and p["inspected"]>=10 else "insufficient"
    perf_lines.append(f"| {s['seed_id']} | {p['runs']} | {p['inspected']} | {p['retained']} | {p['promoted']} | {p['new_cap_runs']} | {p['experiment_runs']} | {evidence} |")
(INTEL/"SEED_PERFORMANCE.md").write_text("\n".join(perf_lines)+"\n",encoding="utf-8")

print(json.dumps({"seed_count":len(seeds),"types":metrics["by_type"],"measured_seeds":metrics["seeds_with_measured_runs"]}))
