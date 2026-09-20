#!/usr/bin/env python3
import json, re
from collections import defaultdict
from ti_common import INTEL, ROOT, load_jsonl, write_jsonl, slug

RUNS=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]

ADJ_TYPES={
 "organization_siblings":{
   "label":"Organization siblings","base_priority":82,
   "strategy_id":"STRAT:capability-conjunction-search-claim-tracing",
   "search_objective_id":"OBJ:emergence-triangulation",
   "recipe":[
     "Inspect the root owner or organization repository list, including archived and low-star projects.",
     "Prioritize siblings sharing domain nouns, protocol names, schema concepts, unusual dependencies or test fixtures.",
     "Inspect renamed or superseded projects before generic popular siblings."
   ],
   "queries":["org:{owner} archived:true","org:{owner} {signature}","user:{owner} {signature}"]
 },
 "contributor_lineage":{
   "label":"Contributor lineage","base_priority":78,
   "strategy_id":"STRAT:paper-research-artifact-production-descendant",
   "search_objective_id":"OBJ:research-lineage",
   "recipe":[
     "Identify maintainers responsible for load-bearing files or architecture commits.",
     "Search their other repositories and later organizations for generalized or productionized descendants.",
     "Require source-level invariant continuity before calling a project a descendant."
   ],
   "queries":["maintainer repositories for {root}","{signature} user:<maintainer>","{signature} org:<maintainer-org>"]
 },
 "fork_descendants":{
   "label":"Fork and descendant lineage","base_priority":76,
   "strategy_id":"STRAT:paper-research-artifact-production-descendant",
   "search_objective_id":"OBJ:research-lineage",
   "recipe":[
     "Inspect forks and descendants with substantial divergence, later commits or deployment hardening.",
     "Search package and release names plus successor references for renamed descendants.",
     "Compare the load-bearing invariant rather than fork popularity."
   ],
   "queries":["forks of {root}","{signature} fork:true","forked from {root} {signature}"]
 },
 "dependency_upstream":{
   "label":"Dependency upstream","base_priority":72,
   "strategy_id":"STRAT:cross-source-emergence-triangulation",
   "search_objective_id":"OBJ:emergence-triangulation",
   "recipe":[
     "Inspect manifests, lockfiles and imports for uncommon libraries, protocols, datasets or engines supporting the valuable capability.",
     "Follow rare dependencies to upstream repositories and sibling implementations.",
     "Prefer dependencies that own the difficult invariant, not commodity framework dependencies."
   ],
   "queries":["dependencies near {signature}","{signature} package manifest","{signature} protocol library tests"]
 },
 "consumer_downstream":{
   "label":"Downstream consumers","base_priority":70,
   "strategy_id":"STRAT:cross-source-emergence-triangulation",
   "search_objective_id":"OBJ:emergence-triangulation",
   "recipe":[
     "Search global code and repository references for imports, package names, API endpoints or distinctive configuration keys from the root.",
     "Prioritize consumers that add domain workflow, deployment hardening or real fixtures.",
     "Treat copied examples as weak evidence unless the consumer adds independent behavior and tests."
   ],
   "queries":["{package_or_repo} {signature}","imports {package_or_repo} {signature}","{signature} {package_or_repo}"]
 },
 "distinctive_symbol":{
   "label":"Distinctive symbol search","base_priority":88,
   "strategy_id":"STRAT:capability-conjunction-search-claim-tracing",
   "search_objective_id":"OBJ:emergence-triangulation",
   "recipe":[
     "Extract two to four distinctive class, function, config or schema symbols from load-bearing source and tests.",
     "Search those symbols globally, including zero-star and archived repositories.",
     "Separate exact copies from independent implementations; independent reimplementation is higher-value evidence."
   ],
   "queries":["<distinctive_symbol>","<symbol_a> <symbol_b>","<schema_key> path:tests"]
 },
 "commit_lineage":{
   "label":"Commit and rename lineage","base_priority":74,
   "strategy_id":"STRAT:protocol-regression-archaeology-for-pre-fat-systems",
   "search_objective_id":"OBJ:protocol-regression",
   "recipe":[
     "Mine commit and release history around load-bearing files for prior names, extracted packages, compatibility fixes and successor references.",
     "Search unusual commit terms, file names and regression names across GitHub.",
     "Follow moved or extracted modules only when the core invariant survives."
   ],
   "queries":["commit terms from {root} plus {signature}","<rare regression name>","<moved file or module> {signature}"]
 }
}

def line_field(block,label):
    m=re.search(r"^-\s*"+re.escape(label)+r":\s*(.*)$",block,re.I|re.M)
    return m.group(1).strip() if m else None

def master_roots():
    text=(ROOT/"MASTER.md").read_text(encoding="utf-8")
    heads=list(re.finditer(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\s+—\s+.*)?$",text,re.M))
    rows=[]
    for i,m in enumerate(heads):
        block=text[m.end():heads[i+1].start() if i+1<len(heads) else len(text)]
        revm=re.search(r"^-\s*(?:Revision|Commit):\s*[^0-9a-f]*([0-9a-f]{7,40})",block,re.I|re.M)
        scorem=re.search(r"^-\s*Score:\s*\**(\d+(?:\.\d+)?)/30",block,re.I|re.M)
        rows.append({
          "repository":m.group(1),
          "revision":revm.group(1) if revm else None,
          "source":"MASTER",
          "score":float(scorem.group(1)) if scorem else 26.0,
          "capability_text":line_field(block,"Capability") or "",
          "why":line_field(block,"Why it wins") or "",
          "status":"master"
        })
    return rows

def recent_strong_roots():
    rows={}
    for r in RUNS[-40:]:
        for d in r.get("candidate_dispositions") or []:
            status=(d.get("status") or "").lower()
            if "strong" not in status and status!="master":
                continue
            repo=d.get("repository")
            if not repo or "/" not in repo:
                continue
            key=(repo,d.get("revision"))
            score=24+(d.get("novelty_ordinal") or 0)+(d.get("evidence_ordinal") or 0)
            prev=rows.get(key)
            if not prev or score>prev["score"]:
                rows[key]={
                  "repository":repo,
                  "revision":d.get("revision"),
                  "source":"recent_strong",
                  "score":score,
                  "capability_text":" ".join(d.get("capability_ids") or []),
                  "why":d.get("reason_detail") or d.get("reason_code_standard") or d.get("reason_code") or "",
                  "status":status
                }
    return list(rows.values())

def signatures(text):
    out=[]
    for phrase in [
      "effective-dated","append-only","exactly-once","fail-closed","negative control",
      "reversal","idempotency","bitemporal","provenance","evidence","deterministic",
      "replay","settlement","ambiguity","rollback","schema","conservation","versioned",
      "audit","coverage","tombstone","authority","lineage","approval","independent"
    ]:
        if phrase in (text or "").lower():
            out.append(phrase)
    for w in re.findall(r"[a-z][a-z0-9-]{5,}",(text or "").lower()):
        if w not in {"system","current","product","buyer","commercial","repository","component","capability","evidence","source","tested","workflow"} and w not in out:
            out.append(w)
        if len(out)>=6:
            break
    return out[:6]

type_perf=defaultdict(lambda:{"runs":0,"inspected":0,"retained":0,"promoted":0,"new_cap_runs":0,"experiment_runs":0})
adj_perf=defaultdict(lambda:{"runs":0,"inspected":0,"retained":0,"promoted":0,"new_cap_runs":0,"experiment_runs":0})
for r in RUNS:
    for typ in set(r.get("adjacency_types") or []):
        p=type_perf[typ]
        p["runs"]+=1; p["inspected"]+=(r.get("deep_inspected") or 0); p["retained"]+=(r.get("retained_count") or 0)
        p["promoted"]+=(r.get("master_promoted_count") or 0); p["new_cap_runs"]+=1 if r.get("new_capability_ids") else 0
        p["experiment_runs"]+=1 if r.get("experiment_ids") else 0
    for aid in set(r.get("adjacency_ids") or []):
        p=adj_perf[aid]
        p["runs"]+=1; p["inspected"]+=(r.get("deep_inspected") or 0); p["retained"]+=(r.get("retained_count") or 0)
        p["promoted"]+=(r.get("master_promoted_count") or 0); p["new_cap_runs"]+=1 if r.get("new_capability_ids") else 0
        p["experiment_runs"]+=1 if r.get("experiment_ids") else 0

def adjust(typ,aid):
    score=0
    p=adj_perf[aid]
    if p["runs"]>=3 and p["inspected"]>=10:
        rate=p["retained"]/max(1,p["inspected"])
        if p["promoted"] or p["new_cap_runs"]: score+=8
        elif rate<0.10 and not p["experiment_runs"]: score-=8
        elif rate<0.25: score-=3
        else: score+=2
    tp=type_perf[typ]
    if tp["runs"]>=5 and tp["inspected"]>=20:
        rate=tp["retained"]/max(1,tp["inspected"])
        if tp["promoted"] or tp["new_cap_runs"]: score+=5
        elif rate<0.10 and not tp["experiment_runs"]: score-=5
    return score

roots=master_roots()
seen={(r["repository"],r.get("revision")) for r in roots}
for r in recent_strong_roots():
    key=(r["repository"],r.get("revision"))
    if key not in seen:
        roots.append(r); seen.add(key)
roots=sorted(roots,key=lambda r:(0 if r["source"]=="MASTER" else 1,-r["score"],r["repository"]))
master_count=sum(1 for r in roots if r["source"]=="MASTER")
roots=roots[:min(len(roots),max(master_count,12)+6)]

rows=[]
for root in roots:
    owner=root["repository"].split("/",1)[0]
    text=(root.get("capability_text") or "")+" "+(root.get("why") or "")
    sigs=signatures(text)
    freight=any(x in (root["repository"]+" "+text).lower() for x in ["freight","trenova","opstrax","ratecon","shipment","carrier"])
    for typ,cfg in ADJ_TYPES.items():
        if freight and typ in {"organization_siblings","fork_descendants","consumer_downstream"}:
            continue
        aid="ADJ:"+typ.replace("_","-")+":"+slug(root["repository"].replace("/","-"))
        priority=max(1,min(100,cfg["base_priority"]+(8 if root["source"]=="MASTER" else 2)+max(0,min(8,int((root["score"] or 24)-24)))+adjust(typ,aid)))
        sig=sigs[0] if sigs else root["repository"].split("/",1)[1]
        qs=[q.format(owner=owner,root=root["repository"],signature=sig,package_or_repo=root["repository"]) for q in cfg["queries"]]
        rows.append({
          "adjacency_id":aid,"adjacency_type":typ,"priority":priority,
          "root_repository":root["repository"],"root_revision":root.get("revision"),
          "root_source":root["source"],"root_status":root["status"],"root_score":root["score"],
          "strategy_id":cfg["strategy_id"],"search_objective_id":cfg["search_objective_id"],
          "why_expand":f"{root['repository']} is a high-value root. Expand nearby while preserving the load-bearing invariant rather than cloning the product category.",
          "load_bearing_signatures":sigs,"search_recipe":cfg["recipe"],"query_templates":qs,
          "verification_gate":"Retain a neighbor only if it adds a new capability, stronger evidence, an independent implementation, a production descendant, a useful negative control, or a new experiment edge. Mere proximity is not value.",
          "stop_conditions":[
             "Stop after three consecutive deep inspections produce only duplicates or clones with no evidence or capability delta.",
             "Do not inspect accidental secrets or private data; quarantine metadata only.",
             "Do not reopen a domain-specific STOP gate through adjacency."
          ],
          "exclude_same_domain":freight,
          "performance":adj_perf[aid],"type_performance":type_perf[typ]
        })

rows.sort(key=lambda x:(-x["priority"],x["adjacency_id"]))
write_jsonl("adjacency_queue.jsonl",rows)
metrics={"schema_version":1,"root_count":len(set(x["root_repository"] for x in rows)),"hypothesis_count":len(rows),"by_type":{},"measured_hypotheses":sum(1 for x in rows if x["performance"]["runs"]>0),"performance_thresholds":{"hypothesis":{"min_runs":3,"min_inspections":10},"type":{"min_runs":5,"min_inspections":20}}}
for x in rows: metrics["by_type"][x["adjacency_type"]]=metrics["by_type"].get(x["adjacency_type"],0)+1
(INTEL/"adjacency_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=["# ADJACENCY EXPANSION QUEUE","","Generated second-order search hypotheses from MASTER leaders and recent strong findings. Adjacency is a discovery surface, not evidence.","","Record adjacency IDs and types in V6 search telemetry when using these packets.","","## Top adjacency packets","","| Priority | Adjacency | Type | Root | Strategy |","|---:|---|---|---|---|"]
for x in rows[:30]:
    lines.append(f"| {x['priority']} | {x['adjacency_id']} | {x['adjacency_type']} | {x['root_repository']} | {x['strategy_id']} |")
lines+=["","## Detailed packets",""]
for x in rows[:20]:
    lines += [f"### {x['adjacency_id']} — priority {x['priority']}",f"- Root: {x['root_repository']} @ {x['root_revision'] or 'unknown'} ({x['root_source']})",f"- Type: {x['adjacency_type']}",f"- Strategy/objective: {x['strategy_id']} / {x['search_objective_id']}",f"- Why expand: {x['why_expand']}",f"- Load-bearing signatures: {', '.join(x['load_bearing_signatures']) or 'derive from source and tests first'}","- Search recipe:"]
    for s in x["search_recipe"]: lines.append("  - "+s)
    lines.append("- Query templates:")
    for q in x["query_templates"]: lines.append("  - "+q)
    lines += [f"- Verification gate: {x['verification_gate']}",f"- Stop conditions: {'; '.join(x['stop_conditions'])}",f"- Same-domain exclusion: {'yes' if x['exclude_same_domain'] else 'no'}",f"- Measured history: {x['performance']['runs']} runs / {x['performance']['inspected']} inspections / {x['performance']['retained']} retained / {x['performance']['promoted']} MASTER.",""]
(INTEL/"ADJACENCY_QUEUE.md").write_text("\n".join(lines),encoding="utf-8")

perf=["# ADJACENCY PERFORMANCE","","Performance is descriptive until minimum samples are reached. A valuable root does not imply every adjacency type is valuable.","","## By adjacency type","","| Type | Runs | Inspected | Retained | MASTER | New-cap runs | Experiment runs | Evidence |","|---|---:|---:|---:|---:|---:|---:|---|"]
for typ in sorted(ADJ_TYPES):
    p=type_perf[typ]; ev="sufficient" if p["runs"]>=5 and p["inspected"]>=20 else "insufficient"
    perf.append(f"| {typ} | {p['runs']} | {p['inspected']} | {p['retained']} | {p['promoted']} | {p['new_cap_runs']} | {p['experiment_runs']} | {ev} |")
perf += ["","## By generated hypothesis","","| Adjacency | Runs | Inspected | Retained | MASTER | New-cap runs | Evidence |","|---|---:|---:|---:|---:|---:|---|"]
for x in rows:
    p=x["performance"]; ev="sufficient" if p["runs"]>=3 and p["inspected"]>=10 else "insufficient"
    perf.append(f"| {x['adjacency_id']} | {p['runs']} | {p['inspected']} | {p['retained']} | {p['promoted']} | {p['new_cap_runs']} | {ev} |")
(INTEL/"ADJACENCY_PERFORMANCE.md").write_text("\n".join(perf)+"\n",encoding="utf-8")
print(json.dumps({"roots":metrics["root_count"],"hypotheses":metrics["hypothesis_count"],"by_type":metrics["by_type"]}))
