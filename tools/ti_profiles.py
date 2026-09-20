#!/usr/bin/env python3
from ti_common import INTEL, load_jsonl, write_jsonl

base={x["repository"]:x for x in load_jsonl("repository_profiles_bootstrap.jsonl")}
runs=load_jsonl("search_runs.jsonl")
for r in runs:
    for d in r.get("candidate_dispositions") or []:
        repo=d.get("repository")
        p=d.get("repository_profile")
        if not repo or not isinstance(p,dict):
            continue
        row={"repository":repo,**p}
        old=base.get(repo)
        if not old or str(row.get("observed_at") or "")>=str(old.get("observed_at") or ""):
            base[repo]=row
rows=sorted(base.values(),key=lambda x:x["repository"].lower())
write_jsonl("repository_profiles.jsonl",rows)
print(f"profiles={len(rows)}")
