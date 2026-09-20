#!/usr/bin/env python3
import hashlib, json
from collections import Counter, defaultdict
from ti_common import INTEL, load_jsonl, slug, write_jsonl

caps=load_jsonl("capabilities.jsonl")
runs=load_jsonl("search_runs.jsonl")
outs=load_jsonl("outcomes.jsonl")
curated=load_jsonl("edges.jsonl")
qfs=load_jsonl("query_families.jsonl")
qf_by_id={q["query_family_id"]:q for q in qfs}
qaliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
qobj=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
surface_aliases=json.loads((INTEL/"surface_aliases.json").read_text(encoding="utf-8")) if (INTEL/"surface_aliases.json").exists() else {}

def edge_id(a,t,b):
    return "EDGE:"+hashlib.sha1((a+"|"+t+"|"+b).encode()).hexdigest()[:12]

def qfid(run):
    raw="QF:"+(slug(run.get("query_family") or "unknown")[:120] or "unknown")
    return qaliases.get(raw,raw)

def objective(run):
    q=qfid(run)
    return run.get("search_objective_id") or qobj.get(q) or qf_by_id.get(q,{}).get("primary_search_objective_id") or "OBJ:unclassified"

def surface_family(surface_id):
    if surface_id in surface_aliases: return surface_aliases[surface_id]
    s=surface_id.lower()
    if "code-search" in s or "code-signature" in s: return "SURFACE_FAMILY:github-code-search"
    if "repository-search" in s: return "SURFACE_FAMILY:github-repository-search"
    if "documentation" in s or ":official-" in s: return "SURFACE_FAMILY:first-party-docs"
    if any(x in s for x in ("history","archaeology","commit-issue","release")): return "SURFACE_FAMILY:github-history-archaeology"
    if any(x in s for x in ("source-tests","exact-head","schema-persistence","actions-license")): return "SURFACE_FAMILY:github-source-inspection"
    if any(x in s for x in ("adjacency","lineage-traversal","analogs","comparator","graph-search")): return "SURFACE_FAMILY:ecosystem-adjacency"
    if "private-ledger" in s: return "SURFACE_FAMILY:private-ledger"
    if any(x in s for x in ("synthetic","sqlite","local-validation","acceptance-corpus")): return "SURFACE_FAMILY:synthetic-local-validation"
    return "SURFACE_FAMILY:other"

derived=[]; seen=set()
def add(a,t,b,evidence):
    if not a or not b: return
    key=(a,t,b)
    if key in seen: return
    seen.add(key)
    derived.append({
      "edge_id":edge_id(a,t,b),"from":a,"type":t,"to":b,
      "confidence":"high","evidence_ref":evidence,"provenance":"derived_structured_event"
    })

for q in qfs:
    oid=q.get("primary_search_objective_id")
    if oid: add(q["query_family_id"],"MEMBER_OF",oid,"intelligence/query_families.jsonl")

for r in runs:
    rid=r["search_run_id"]; sid=r.get("strategy_id"); q=qfid(r); oid=objective(r)
    if sid: add(sid,"PRODUCED",rid,"intelligence/search_runs.jsonl")
    add(q,"PRODUCED",rid,"intelligence/search_runs.jsonl")
    add(rid,"PURSUED",oid,"intelligence/search_runs.jsonl")
    for surface in sorted(set(r.get("search_surfaces") or [])):
        s="SURFACE:"+slug(surface); fam=surface_family(s)
        add(rid,"USED_SURFACE",s,"intelligence/search_runs.jsonl")
        add(s,"MEMBER_OF",fam,"intelligence/surface_aliases.json")
    for cid in r.get("new_capability_ids",[]): add(rid,"PRODUCED",cid,"intelligence/search_runs.jsonl")
    for cid in r.get("strengthened_capability_ids",[]): add(rid,"STRENGTHENS",cid,"intelligence/search_runs.jsonl")
    for exp in r.get("experiment_ids",[]): add(rid,"CONTRIBUTED_TO",exp,"intelligence/search_runs.jsonl")
    for d in r.get("candidate_dispositions") or []:
        repo=d.get("repository")
        if not repo: continue
        node="REPO:"+repo+("@"+d["revision"] if d.get("revision") else "")
        add(rid,"DISCOVERED",node,"intelligence/search_runs.jsonl")
        for cid in d.get("capability_ids") or []: add(node,"STRENGTHENS",cid,"intelligence/search_runs.jsonl")

for o in outs:
    oid=o["outcome_id"]
    for rid in o.get("origin_search_ids",[]): add(rid,"PRODUCED",oid,"intelligence/outcomes.jsonl")
    for cid in o.get("contributing_capability_ids",[]): add(cid,"CONTRIBUTED_TO",oid,"intelligence/outcomes.jsonl")
    for repository in o.get("contributing_repositories",[]) or []: add("REPO:"+repository,"CONTRIBUTED_TO",oid,"intelligence/outcomes.jsonl")
    if o.get("experiment_id"): add(oid,"VALIDATES",o["experiment_id"],"intelligence/outcomes.jsonl")

write_jsonl("derived_edges.jsonl",sorted(derived,key=lambda x:x["edge_id"]))

attention=Counter(); experiments=defaultdict(set)
for r in runs:
    for cid in r.get("new_capability_ids",[])+r.get("strengthened_capability_ids",[]):
        attention[cid]+=1
        for exp in r.get("experiment_ids",[]): experiments[cid].add(exp)

support_count=Counter()
for e in curated+derived:
    if e.get("to","").startswith("CAP-") and e.get("from","").startswith(("REPO:","SOURCE:","DATA:")):
        support_count[e["to"]]+=1

support={}
for c in caps:
    components=len(c.get("primary_components") or [])
    score=0
    if c.get("evidence_state")=="watch": score+=3
    elif c.get("evidence_state")=="source_or_test_validated": score+=2
    elif c.get("evidence_state")=="benchmarked": score+=1
    if c.get("missing_piece"): score+=2
    if components<2: score+=2
    if attention[c["capability_id"]]==0: score+=1
    support[c["capability_id"]]={
      "components":components,"attention":attention[c["capability_id"]],
      "experiments":len(experiments[c["capability_id"]]),
      "graph_support":support_count[c["capability_id"]],"gap_score":score
    }

priority=sorted(caps,key=lambda c:(-support[c["capability_id"]]["gap_score"],c["capability_id"]))[:12]
objective_nodes={e["to"] for e in derived if e.get("to","").startswith("OBJ:")}
surface_nodes={e["from"] for e in derived if e.get("from","").startswith("SURFACE:")}
surface_family_nodes={e["to"] for e in derived if e.get("to","").startswith("SURFACE_FAMILY:")}
lines=[
 "# GRAPH HEALTH REPORT","",
 f"- Curated edges: **{len(curated)}**",
 f"- Derived attribution edges: **{len(derived)}**",
 f"- Capability nodes: **{len(caps)}**",
 f"- Query-family nodes: **{len(qfs)}**",
 f"- Search-objective nodes touched: **{len(objective_nodes)}**",
 f"- Exact search-surface nodes touched: **{len(surface_nodes)}**",
 f"- Normalized surface-family nodes touched: **{len(surface_family_nodes)}**",
 f"- Capabilities touched by measured search runs: **{sum(1 for c in caps if attention[c['capability_id']]>0)}**","",
 "## Highest-priority capability gaps","",
 "| Capability | Evidence | Components | Graph support | Run attention | Experiments | Gap score | Missing piece |",
 "|---|---|---:|---:|---:|---:|---:|---|"
]
for c in priority:
    s=support[c["capability_id"]]
    lines.append(f"| {c['capability_id']} — {c['name']} | {c.get('evidence_state')} | {s['components']} | {s['graph_support']} | {s['attention']} | {s['experiments']} | {s['gap_score']} | {c.get('missing_piece') or '—'} |")
lines += ["","## Graph policy","",
          "- Query families belong to broader objectives; exact surfaces belong to normalized surface families.",
          "- These provenance edges explain how knowledge was found; they are not causal proof that a strategy/surface produced the outcome.",
          "- Prefer searches that close a named missing edge in an active experiment over another similar implementation.",
          "- A capability with many repositories but no experiment/outcome edge remains a research cluster.",
          "- Independent challengers and negative controls can be more valuable than a second implementation of the same mechanism.",""]
(INTEL/"GRAPH_HEALTH.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"derived_edges":len(derived),"query_families":len(qfs),"objectives":len(objective_nodes),"surface_families":len(surface_family_nodes)}))
