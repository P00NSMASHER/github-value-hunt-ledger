#!/usr/bin/env python3
import json, re
from collections import Counter, defaultdict
from ti_common import ROOT, INTEL, parse_hunter_records, status_bucket

def master_promotions():
    text=(ROOT/"MASTER.md").read_text(encoding="utf-8")
    lines=text.splitlines()
    promoted=[]
    pat=re.compile(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\s+—\s+.*)?$")
    for i,line in enumerate(lines):
        m=pat.match(line)
        if not m: continue
        rev=None
        for j in range(i+1,min(len(lines),i+12)):
            if lines[j].startswith(("## ","### ")): break
            rm=re.search(r"^-\s*(?:Revision|Commit):\s*`?([0-9a-f]{7,40})",lines[j],re.I)
            if rm:
                rev=rm.group(1); break
        promoted.append({"repository":m.group(1),"revision":rev})
    return promoted

records=parse_hunter_records(include_archive=True)
unknown=[r for r in records if not r.get("revision")]
by_repo=defaultdict(list)
for r in records:
    by_repo[r["repository"]].append(r)

def priority(r):
    state=r.get("source_state")
    bucket=status_bucket(r.get("status"))
    score=0
    if state=="current": score+=5
    elif state=="pending": score+=4
    else: score+=1
    score += {"master":6,"strong":5,"watch":3,"unknown":2,"rejected":0,"quarantined":0}.get(bucket,1)
    return score

unknown_sorted=sorted(unknown,key=lambda r:(-priority(r),r["repository"],r["source_catalog"]))
masters=master_promotions()
catalog_keys={(r["repository"],r.get("revision")) for r in records}
master_gaps=[m for m in masters if (m["repository"],m.get("revision")) not in catalog_keys]

bucket_counts=Counter(status_bucket(r.get("status")) for r in unknown)
state_counts=Counter(r.get("source_state") for r in unknown)
metrics={
  "unknown_revision_observations":len(unknown),
  "unique_repositories_with_unknown_revision":len(set(r["repository"] for r in unknown)),
  "status_counts":dict(bucket_counts),
  "source_state_counts":dict(state_counts),
  "master_catalog_gaps":master_gaps,
  "top_priority":[
    {
      "repository":r["repository"],
      "source_catalog":r["source_catalog"],
      "source_state":r["source_state"],
      "status_bucket":status_bucket(r.get("status")),
      "status":r.get("status"),
      "priority_score":priority(r)
    } for r in unknown_sorted[:100]
  ]
}
(INTEL/"revision_debt_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
 "# REVISION / CATALOG PROVENANCE DEBT","",
 "Pinned revisions are essential for reproducible technical intelligence. This report prioritizes records whose repository identity is known but whose inspected revision is not recoverable from the hunter catalog.","",
 f"- Unknown-revision observations: **{len(unknown)}**",
 f"- Unique repositories with unknown revision: **{metrics['unique_repositories_with_unknown_revision']}**",
 f"- Current MASTER promotions without matching exact hunter-catalog observation: **{len(master_gaps)}**","",
 "## Unknown revision mix","",
 "| Bucket | Count |","|---|---:|"
]
for k,v in bucket_counts.most_common():
    lines.append(f"| {k} | {v} |")
lines += ["","## Highest-priority records to resolve","",
          "| Repository | Catalog | State | Disposition | Priority |","|---|---|---|---|---:|"]
for r in unknown_sorted[:50]:
    lines.append(f"| {r['repository']} | {r['source_catalog']} | {r['source_state']} | {status_bucket(r.get('status'))} | {priority(r)} |")
if not unknown_sorted: lines.append("| — | — | — | — | 0 |")
lines += ["","## MASTER catalog provenance gaps",""]
if master_gaps:
    for m in master_gaps:
        lines.append(f"- `{m['repository']}@{m.get('revision') or 'unknown'}` is in current MASTER but lacks a matching exact hunter-catalog observation.")
else:
    lines.append("- None.")
lines += ["","## Policy","",
          "- Resolve current strong/watch records before archival/rejected records.",
          "- Do not invent a historical SHA. If the original inspected revision cannot be recovered from Git history, record the uncertainty and reinspect a new pinned revision as a new observation.",
          "- MASTER can remain authoritative, but load-bearing elite components should also have durable catalog evidence tied to the exact revision.",
          "- Revision debt is evidence-quality debt, not a reason to erase useful historical findings.",""]
(INTEL/"REVISION_DEBT_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"unknown":len(unknown),"unique_unknown":metrics["unique_repositories_with_unknown_revision"],"master_catalog_gaps":len(master_gaps)}))
