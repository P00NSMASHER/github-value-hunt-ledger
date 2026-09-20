#!/usr/bin/env python3
import json,re
from ti_common import INTEL, load_jsonl

tax=json.loads((INTEL/"coverage_taxonomy.json").read_text(encoding="utf-8"))
profiles=load_jsonl("repository_profiles.jsonl")
targets=load_jsonl("coverage_targets.jsonl")
gaps=load_jsonl("exploration_gap_queue.jsonl")
runs=load_jsonl("search_runs.jsonl")
if tax.get("schema_version")!=1: raise SystemExit("coverage_taxonomy.json: unsupported schema_version")
seen=set()
for n,p in enumerate(profiles,1):
    repo=p.get("repository")
    if not repo or repo in seen: raise SystemExit(f"repository_profiles.jsonl:{n}: missing/duplicate repository")
    seen.add(repo)
    if p.get("metadata_status") not in {"observed","unavailable"}: raise SystemExit(f"repository_profiles.jsonl:{n}: invalid metadata_status")
target_ids=set()
for n,x in enumerate(targets,1):
    gid=x.get("coverage_gap_id")
    if not gid or not re.match(r"^COV:[a-z0-9-]+:[a-z0-9-]+$",gid): raise SystemExit(f"coverage_targets.jsonl:{n}: bad coverage_gap_id {gid}")
    if gid in target_ids: raise SystemExit(f"coverage_targets.jsonl:{n}: duplicate {gid}")
    target_ids.add(gid)
    if x.get("state") not in {"COVERED","UNDERCOVERED","INSTRUMENTATION_DEBT"}: raise SystemExit(f"coverage_targets.jsonl:{n}: bad state")
gap_ids=set()
for n,x in enumerate(gaps,1):
    gid=x.get("coverage_gap_id")
    if gid not in target_ids: raise SystemExit(f"exploration_gap_queue.jsonl:{n}: unknown target {gid}")
    if x.get("state")!="UNDERCOVERED" or not x.get("searchable"): raise SystemExit(f"exploration_gap_queue.jsonl:{n}: queue contains non-searchable/non-undercovered target")
    gap_ids.add(gid)
for n,r in enumerate(runs,1):
    if (r.get("schema_version") or 0)<8: continue
    mode=r.get("coverage_mode")
    ids=r.get("coverage_gap_ids")
    if mode not in {"generated","manual","none"}: raise SystemExit(f"search_runs.jsonl:{n}: invalid V8 coverage_mode")
    if not isinstance(ids,list): raise SystemExit(f"search_runs.jsonl:{n}: V8 coverage_gap_ids must be list")
    if mode=="generated" and not ids: raise SystemExit(f"search_runs.jsonl:{n}: generated coverage mode requires gap IDs")
    if mode=="none" and ids: raise SystemExit(f"search_runs.jsonl:{n}: none coverage mode must have empty gap IDs")
    for gid in ids:
        if gid not in gap_ids: raise SystemExit(f"search_runs.jsonl:{n}: unknown/nonactive coverage gap {gid}")
    for d in r.get("candidate_dispositions") or []:
        p=d.get("repository_profile")
        if not isinstance(p,dict): raise SystemExit(f"search_runs.jsonl:{n}: V8 candidate missing repository_profile")
        if p.get("metadata_status") not in {"observed","unavailable"}: raise SystemExit(f"search_runs.jsonl:{n}: candidate profile missing metadata_status")
metrics=json.loads((INTEL/"coverage_metrics.json").read_text(encoding="utf-8"))
if metrics.get("profiled_unique_repositories")!=len([x for x in set(p["repository"] for p in profiles)]):
    raise SystemExit("coverage_metrics.json: profile count drift")
print(f"OK profiles={len(profiles)} targets={len(targets)} active_gaps={len(gaps)} v8_runs={sum(1 for r in runs if (r.get('schema_version') or 0)>=8)}")
