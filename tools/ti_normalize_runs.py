#!/usr/bin/env python3
import json
from ti_common import INTEL,load_jsonl,slug,write_jsonl

runs=load_jsonl("search_runs.jsonl")
bindings=json.loads((INTEL/"strategy_version_bindings.json").read_text(encoding="utf-8")) if (INTEL/"strategy_version_bindings.json").exists() else {}
qaliases=json.loads((INTEL/"query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL/"query_family_aliases.json").exists() else {}
qobj=json.loads((INTEL/"query_objective_map.json").read_text(encoding="utf-8")) if (INTEL/"query_objective_map.json").exists() else {}
surface_aliases=json.loads((INTEL/"surface_aliases.json").read_text(encoding="utf-8")) if (INTEL/"surface_aliases.json").exists() else {}
reason_aliases=json.loads((INTEL/"reason_aliases.json").read_text(encoding="utf-8")) if (INTEL/"reason_aliases.json").exists() else {}
reason_catalog=json.loads((INTEL/"reason_codes.json").read_text(encoding="utf-8")) if (INTEL/"reason_codes.json").exists() else {}
standard={v for vals in reason_catalog.values() for v in vals}

def qfid(r):
    raw="QF:"+(slug(r.get("query_family") or "unknown")[:120] or "unknown")
    return qaliases.get(raw,raw)

def sfamily(surface_id):
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

rows=[]; objective_unresolved=0; reason_unresolved=0; version_unresolved=0
for r in runs:
    e=dict(r)
    e["raw_schema_version"]=r.get("schema_version")
    e["normalized_schema_version"]=5
    q=qfid(r); e["query_family_id"]=r.get("query_family_id") or q
    e["search_objective_id"]=r.get("search_objective_id") or qobj.get(q) or "OBJ:unclassified"
    if e["search_objective_id"]=="OBJ:unclassified": objective_unresolved+=1
    binding=bindings.get(r["search_run_id"])
    e["strategy_version_id"]=r.get("strategy_version_id") or (binding or {}).get("strategy_version_id")
    e["strategy_version_binding_method"]="explicit_in_run" if r.get("strategy_version_id") else (binding or {}).get("binding_method")
    if not e.get("strategy_version_id"): version_unresolved+=1
    exact=["SURFACE:"+slug(s) for s in (r.get("search_surfaces") or [])]
    e["surface_family_ids"]=sorted(set(sfamily(s) for s in exact))
    enriched=[]
    for d in r.get("candidate_dispositions") or []:
        x=dict(d); direct=x.get("reason_code_standard"); legacy=x.get("reason_code")
        if direct in standard:
            x["reason_code_standard"]=direct; x["reason_normalization_source"]="direct"
        elif legacy in standard:
            x["reason_code_standard"]=legacy; x["reason_normalization_source"]="legacy_already_standard"
        elif legacy in reason_aliases and reason_aliases[legacy] in standard:
            x["reason_code_standard"]=reason_aliases[legacy]; x["reason_normalization_source"]="reviewed_alias"
        else:
            x["reason_normalization_source"]="unresolved"
            if legacy: reason_unresolved+=1
        enriched.append(x)
    e["candidate_dispositions"]=enriched
    rows.append(e)

write_jsonl("search_runs_enriched.jsonl",rows)
lines=[
 "# RUN NORMALIZATION REPORT","",
 "Raw search-run events remain immutable. V5 generates an enriched view that binds stable strategy versions and normalized query/objective/surface/reason fields without rewriting source history.","",
 f"- Raw runs: **{len(runs)}**",f"- Strategy-version unresolved: **{version_unresolved}**",
 f"- Objective unresolved/unclassified: **{objective_unresolved}**",f"- Candidate reasons unresolved: **{reason_unresolved}**","",
 "## Policy","",
 "- Analytics may use the enriched view for stable grouping while source evidence remains intelligence/search_runs.jsonl.",
 "- Enrichment never invents search counts, revisions, outcomes or candidate evidence.",
 "- Reviewed aliases and first-ingest strategy bindings are explicit provenance, not silent edits.",""]
(INTEL/"RUN_NORMALIZATION_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"runs":len(runs),"version_unresolved":version_unresolved,"objective_unresolved":objective_unresolved,"reason_unresolved":reason_unresolved}))
