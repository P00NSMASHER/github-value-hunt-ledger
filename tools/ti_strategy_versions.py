#!/usr/bin/env python3
import hashlib,json
from collections import defaultdict
from ti_common import INTEL,load_jsonl,slug,write_jsonl

strategies=load_jsonl("search_strategies.jsonl")
runs=load_jsonl("search_runs.jsonl")
versions_path=INTEL/"strategy_versions.jsonl"
existing=load_jsonl("strategy_versions.jsonl") if versions_path.exists() else []
by_version={x["strategy_version_id"]:x for x in existing}
current={}

FIELDS=("name","when_to_use","procedure","why_it_worked","failure_modes","next_improvement","status","parent_strategy_id")
for s in strategies:
    payload={"strategy_id":s["strategy_id"]}
    for f in FIELDS: payload[f]=s.get(f)
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    vid=f"STRATVER:{slug(s['strategy_id'].replace('STRAT:',''))}:{digest}"
    current[s["strategy_id"]]=vid
    if vid not in by_version:
        by_version[vid]={
          "strategy_version_id":vid,"strategy_id":s["strategy_id"],"content_sha256_12":digest,
          "source_markdown":s.get("source_markdown","SEARCH_SKILLS.md"),"snapshot":payload
        }

write_jsonl("strategy_versions.jsonl",sorted(by_version.values(),key=lambda x:(x["strategy_id"],x["strategy_version_id"])))
(INTEL/"current_strategy_versions.json").write_text(json.dumps(current,indent=2,sort_keys=True)+"\n",encoding="utf-8")

binding_path=INTEL/"strategy_version_bindings.json"
bindings=json.loads(binding_path.read_text(encoding="utf-8")) if binding_path.exists() else {}
for r in runs:
    rid=r["search_run_id"]; sid=r.get("strategy_id"); explicit=r.get("strategy_version_id")
    if explicit:
        bindings[rid]={"strategy_version_id":explicit,"binding_method":"explicit_in_run"}
    elif rid not in bindings and sid in current:
        bindings[rid]={"strategy_version_id":current[sid],"binding_method":"current_at_first_v5_ingest"}
binding_path.write_text(json.dumps(bindings,indent=2,sort_keys=True)+"\n",encoding="utf-8")

perf=defaultdict(lambda:{"runs":0,"deep_inspected":0,"retained":0,"master":0})
for r in runs:
    vid=r.get("strategy_version_id") or (bindings.get(r["search_run_id"]) or {}).get("strategy_version_id")
    if not vid: continue
    p=perf[vid]; p["runs"]+=1; p["deep_inspected"]+=r.get("deep_inspected") or 0
    p["retained"]+=r.get("retained_count") or 0; p["master"]+=r.get("master_promoted_count") or 0

bound=sum(1 for r in runs if r["search_run_id"] in bindings)
lines=[
 "# STRATEGY VERSION REPORT","",
 "Search strategy performance is only interpretable if procedure changes do not silently overwrite history. V5 snapshots strategy definitions and binds each run to a durable version ID.","",
 f"- Canonical strategies: **{len(strategies)}**",
 f"- Strategy versions retained: **{len(by_version)}**",
 f"- Search runs with durable strategy-version bindings: **{bound}/{len(runs)}**","",
 "## Version evidence","",
 "| Strategy | Version | Current? | Runs | Inspected | Retained | MASTER |",
 "|---|---|---|---:|---:|---:|---:|"
]
for v in sorted(by_version.values(),key=lambda x:(x["strategy_id"],x["strategy_version_id"])):
    p=perf[v["strategy_version_id"]]
    lines.append(
      f"| {v['strategy_id']} | {v['strategy_version_id']} | "
      f"{'yes' if current.get(v['strategy_id'])==v['strategy_version_id'] else 'no'} | "
      f"{p['runs']} | {p['deep_inspected']} | {p['retained']} | {p['master']} |"
    )
lines += ["","## Binding policy","",
          "- Existing bindings never change when SEARCH_SKILLS.md evolves.",
          "- A changed strategy definition creates a new STRATVER ID; the new version begins with zero inherited evidence for exploitation/measurement sufficiency.",
          "- Historical versions remain available for comparison and outcome attribution.",
          "- Legacy runs without an explicit version are bound once at first V5 ingest and labeled as inferred, not rewritten.",
          "- New V5-native recording should prefer an explicit/current strategy-version ID when practical.",""]
(INTEL/"STRATEGY_VERSION_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"strategies":len(strategies),"versions":len(by_version),"bound_runs":bound}))
