#!/usr/bin/env python3
import hashlib,json
from collections import Counter,defaultdict
from ti_common import INTEL,load_jsonl,slug,write_jsonl

caps=load_jsonl("capabilities.jsonl"); runs=load_jsonl("search_runs.jsonl"); outs=load_jsonl("outcomes.jsonl")
curated=load_jsonl("edges.jsonl"); qfs=load_jsonl("query_families.jsonl"); qf_by_id={x["query_family_id"]:x for x in qfs}
versions=load_jsonl("strategy_versions.jsonl") if (INTEL/"strategy_versions.jsonl").exists() else []
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
qaliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
qobj=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
surface_aliases=json.loads((INTEL/"surface_aliases.json").read_text(encoding="utf-8")) if (INTEL/"surface_aliases.json").exists() else {}

def eid(a,t,b): return "EDGE:"+hashlib.sha1((a+"|"+t+"|"+b).encode()).hexdigest()[:12]
def qfid(r):
    raw="QF:"+(slug(r.get("query_family") or "unknown")[:120] or "unknown"); return qaliases.get(raw,raw)
def objective(r):
    q=qfid(r); return r.get("search_objective_id") or qobj.get(q) or qf_by_id.get(q,{}).get("primary_search_objective_id") or "OBJ:unclassified"
def sfamily(sid):
    if sid in surface_aliases: return surface_aliases[sid]
    s=sid.lower()
    if "code-search" in s or "code-signature" in s:return "SURFACE_FAMILY:github-code-search"
    if "repository-search" in s:return "SURFACE_FAMILY:github-repository-search"
    if "documentation" in s or ":official-" in s:return "SURFACE_FAMILY:first-party-docs"
    if any(x in s for x in ("history","archaeology","commit-issue","release")):return "SURFACE_FAMILY:github-history-archaeology"
    if any(x in s for x in ("source-tests","exact-head","schema-persistence","actions-license")):return "SURFACE_FAMILY:github-source-inspection"
    if any(x in s for x in ("adjacency","lineage-traversal","analogs","comparator","graph-search")):return "SURFACE_FAMILY:ecosystem-adjacency"
    if "private-ledger" in s:return "SURFACE_FAMILY:private-ledger"
    if any(x in s for x in ("synthetic","sqlite","local-validation","acceptance-corpus")):return "SURFACE_FAMILY:synthetic-local-validation"
    return "SURFACE_FAMILY:other"

derived=[];seen=set()
def add(a,t,b,ref):
    if not a or not b:return
    key=(a,t,b)
    if key in seen:return
    seen.add(key); derived.append({"edge_id":eid(a,t,b),"from":a,"type":t,"to":b,"confidence":"high","evidence_ref":ref,"provenance":"derived_structured_event"})

for v in versions:add(v["strategy_id"],"HAS_VERSION",v["strategy_version_id"],"intelligence/strategy_versions.jsonl")
for q in qfs:
    if q.get("primary_search_objective_id"):add(q["query_family_id"],"MEMBER_OF",q["primary_search_objective_id"],"intelligence/query_families.jsonl")
for r in runs:
    rid=r["search_run_id"]; sid=r.get("strategy_id"); q=qfid(r); obj=objective(r)
    if sid:add(sid,"PRODUCED",rid,"intelligence/search_runs.jsonl")
    vid=r.get("strategy_version_id") or (bindings.get(rid) or {}).get("strategy_version_id")
    if vid:add(rid,"USED_VERSION",vid,"intelligence/strategy_version_bindings.json")
    add(q,"PRODUCED",rid,"intelligence/search_runs.jsonl"); add(rid,"PURSUED",obj,"intelligence/search_runs.jsonl")
    for surface in sorted(set(r.get("search_surfaces") or [])):
        s="SURFACE:"+slug(surface); add(rid,"USED_SURFACE",s,"intelligence/search_runs.jsonl"); add(s,"MEMBER_OF",sfamily(s),"intelligence/surface_aliases.json")
    for cid in r.get("new_capability_ids",[]):add(rid,"PRODUCED",cid,"intelligence/search_runs.jsonl")
    for cid in r.get("strengthened_capability_ids",[]):add(rid,"STRENGTHENS",cid,"intelligence/search_runs.jsonl")
    for exp in r.get("experiment_ids",[]):add(rid,"CONTRIBUTED_TO",exp,"intelligence/search_runs.jsonl")
    for d in r.get("candidate_dispositions") or []:
        if not d.get("repository"):continue
        node="REPO:"+d["repository"]+("@"+d["revision"] if d.get("revision") else "")
        add(rid,"DISCOVERED",node,"intelligence/search_runs.jsonl")
        for cid in d.get("capability_ids") or []:add(node,"STRENGTHENS",cid,"intelligence/search_runs.jsonl")
for o in outs:
    oid=o["outcome_id"]
    for rid in o.get("origin_search_ids",[]):add(rid,"PRODUCED",oid,"intelligence/outcomes.jsonl")
    for cid in o.get("contributing_capability_ids",[]):add(cid,"CONTRIBUTED_TO",oid,"intelligence/outcomes.jsonl")
    if o.get("experiment_id"):add(oid,"VALIDATES",o["experiment_id"],"intelligence/outcomes.jsonl")

write_jsonl("derived_edges.jsonl",sorted(derived,key=lambda x:x["edge_id"]))
attention=Counter(); experiments=defaultdict(set)
for r in runs:
    for cid in r.get("new_capability_ids",[])+r.get("strengthened_capability_ids",[]):
        attention[cid]+=1
        for exp in r.get("experiment_ids",[]):experiments[cid].add(exp)
support_count=Counter()
for e in curated+derived:
    if e.get("to","").startswith("CAP-") and e.get("from","").startswith(("REPO:","SOURCE:","DATA:")):support_count[e["to"]]+=1
def gap(c):
    score={"watch":3,"source_or_test_validated":2,"benchmarked":1}.get(c.get("evidence_state"),0)
    if c.get("missing_piece"):score+=2
    if len(c.get("primary_components") or [])<2:score+=2
    if attention[c["capability_id"]]==0:score+=1
    return score
priority=sorted(caps,key=lambda c:(-gap(c),c["capability_id"]))[:12]
lines=["# GRAPH HEALTH REPORT","",
 f"- Curated edges: **{len(curated)}**",f"- Derived attribution edges: **{len(derived)}**",
 f"- Strategy-version nodes retained: **{len(versions)}**",f"- Capability nodes: **{len(caps)}**",
 f"- Query-family nodes: **{len(qfs)}**","",
 "## Highest-priority capability gaps","",
 "| Capability | Evidence | Components | Run attention | Experiments | Gap score | Missing piece |","|---|---|---:|---:|---:|---:|---|"]
for c in priority:
    lines.append(f"| {c['capability_id']} — {c['name']} | {c.get('evidence_state')} | {len(c.get('primary_components') or [])} | {attention[c['capability_id']]} | {len(experiments[c['capability_id']])} | {gap(c)} | {c.get('missing_piece') or '—'} |")
lines += ["","## Graph policy","",
 "- Runs now bind to immutable strategy-version nodes, preventing later skill edits from rewriting historical search provenance.",
 "- Query families belong to objectives; exact surfaces belong to surface families.",
 "- Provenance edges explain how knowledge was found; they are not causal proof.",""]
(INTEL/"GRAPH_HEALTH.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"derived_edges":len(derived),"strategy_versions":len(versions)}))
