#!/usr/bin/env python3
import argparse
from ti_common import parse_hunter_records, load_jsonl

ap = argparse.ArgumentParser(description="Find prior hunt evidence for a repository before spending deep-inspection time.")
ap.add_argument("repository", help="owner/name or substring")
ap.add_argument("--revision")
args = ap.parse_args()

query = args.repository.lower()
records = [
    r for r in parse_hunter_records(include_archive=True)
    if query in r["repository"].lower() and (not args.revision or r.get("revision") == args.revision)
]

for r in records:
    print(f"{r['repository']}@{r.get('revision') or 'unknown'} | {r.get('status') or 'unknown'} | {r['source_catalog']} | {r.get('date_seen') or 'unknown-date'}")

runs = load_jsonl("search_runs.jsonl")
for run in runs:
    for d in run.get("candidate_dispositions", []) or []:
        if query in (d.get("repository") or "").lower() and (not args.revision or d.get("revision") == args.revision):
            print(f"RUN {run['search_run_id']} | {d.get('repository')}@{d.get('revision') or 'unknown'} | {d.get('status')} | {d.get('reason_code') or ''}")

print(f"matches={len(records)}")
