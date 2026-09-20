#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from ti_common import INTEL, load_jsonl, write_jsonl, slug

TAX=json.loads((INTEL/"coverage_taxonomy.json").read_text(encoding="utf-8"))
PROFILES={x["repository"]:x for x in load_jsonl("repository_profiles.jsonl")}
RUNS=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]

repos=[]
structured_dispositions=0
deep_total=sum((r.get("deep_inspected") or 0) for r in RUNS)
for r in RUNS:
    for d in r.get("candidate_dispositions") or []:
        structured_dispositions+=1
        repo=d.get("repository")
        if repo and repo not in repos:
            repos.append(repo)

profiled=[r for r in repos if r in PROFILES]
missing=[r for r in repos if r not in PROFILES]
today=date.today()

def language_family(p):
    v=(p.get("primary_language") or "").lower()
    if v=="python": return ["python"]
    if v in {"typescript","javascript"}: return ["js_ts"]
    if v=="go": return ["go"]
    if v in {"java","kotlin"}: return ["jvm"]
    if v in {"c","c++"}: return ["c_cpp"]
    if v=="c#": return ["dotnet"]
    if v=="rust": return ["rust"]
    if v: return ["domain_other"]
    return []

def star_band(p):
    s=p.get("stars")
    if s is None: return []
    if s==0: return ["zero"]
    if s<=9: return ["one_nine"]
    if s<=99: return ["ten_ninetynine"]
    if s<=999: return ["hundred_999"]
    return ["thousand_plus"]

def age_band(p):
    raw=p.get("created_at")
    if not raw: return []
    try:
        d=datetime.fromisoformat(raw.replace("Z","+00:00")).date()
    except Exception:
        return []
    days=(today-d).days
    if days<365: return ["under_1y"]
    if days<3*365: return ["one_3y"]
    if days<7*365: return ["three_7y"]
    return ["seven_plus"]

def lifecycle(p):
    out=[]
    if p.get("archived") is True: out.append("archived")
    if p.get("fork") is True: out.append("fork")
    return out

def owner_type(p):
    v=(p.get("owner_type") or "").lower()
    if v=="organization": return ["organization"]
    if v=="user": return ["user"]
    return []

def manual_single(p,key):
    v=p.get(key)
    if v and v!="unknown": return [v]
    return []

def manual_multi(p,key):
    return [str(x) for x in (p.get(key) or []) if x]

CLASSIFIERS={
 "language_family":lambda p:language_family(p),
 "star_band":lambda p:star_band(p),
 "age_band":lambda p:age_band(p),
 "lifecycle":lambda p:lifecycle(p),
 "owner_type":lambda p:owner_type(p),
 "source_type":lambda p:manual_single(p,"source_type"),
 "package_ecosystem":lambda p:manual_multi(p,"package_ecosystems"),
 "protocol_family":lambda p:manual_multi(p,"protocol_families"),
 "geography_scope":lambda p:manual_multi(p,"geography_tags")
}

def age_queries(target):
    if target=="under_1y":
        return [f"created:>={today-timedelta(days=365)}"]
    if target=="one_3y":
        return [f"created:{today-timedelta(days=3*365)}..{today-timedelta(days=365)}"]
    if target=="three_7y":
        return [f"created:{today-timedelta(days=7*365)}..{today-timedelta(days=3*365)}"]
    if target=="seven_plus":
        return [f"created:<={today-timedelta(days=7*365)}"]
    return []

rows=[]
gaps=[]
dimension_metrics={}
for dim in TAX.get("dimensions",[]):
    did=dim["dimension_id"]
    clf=CLASSIFIERS.get(did)
    counts=defaultdict(set)
    classified=set()
    if clf:
        for repo in profiled:
            vals=clf(PROFILES[repo])
            if vals:
                classified.add(repo)
            for v in vals:
                counts[v].add(repo)
    classification_rate=(len(classified)/len(profiled)) if profiled else 0
    reliable=classification_rate>=TAX.get("min_classification_rate",0.6)
    dimension_metrics[did]={
      "profiled_repositories":len(profiled),
      "classified_repositories":len(classified),
      "classification_rate":classification_rate,
      "reliable":reliable
    }
    for target in dim.get("targets",[]):
        tid=target["target_id"]
        observed=len(counts.get(tid,set()))
        target_min=int(target.get("target_min_repositories") or 0)
        gap=max(0,target_min-observed)
        if not reliable:
            state="INSTRUMENTATION_DEBT"
        elif gap>0:
            state="UNDERCOVERED"
        else:
            state="COVERED"
        qv=list(target.get("query_variants") or [])
        if did=="age_band" and not qv:
            qv=age_queries(tid)
        frac=(gap/target_min) if target_min else 0
        priority=round(min(100,100*frac*float(target.get("exploration_weight",1.0)))) if state=="UNDERCOVERED" else 0
        gid=f"COV:{did.replace('_','-')}:{tid.replace('_','-')}"
        row={
          "coverage_gap_id":gid,
          "dimension_id":did,
          "dimension_label":dim.get("label"),
          "target_id":tid,
          "target_label":target.get("label"),
          "state":state,
          "observed_unique_repositories":observed,
          "target_min_repositories":target_min,
          "gap_repositories":gap,
          "classification_rate":classification_rate,
          "exploration_weight":target.get("exploration_weight",1.0),
          "priority":priority,
          "searchable":bool(target.get("searchable")) and bool(qv),
          "query_variants":qv,
          "evidence_basis":"measured unique repositories with structured candidate dispositions and repository profiles"
        }
        rows.append(row)
        if state=="UNDERCOVERED" and row["searchable"]:
            gaps.append(row)

gaps.sort(key=lambda x:(-x["priority"],-x["gap_repositories"],x["coverage_gap_id"]))
write_jsonl("coverage_targets.jsonl",rows)
write_jsonl("exploration_gap_queue.jsonl",gaps)

metrics={
 "schema_version":1,
 "measured_runs":len(RUNS),
 "deep_inspected_total":deep_total,
 "structured_candidate_dispositions":structured_dispositions,
 "unique_structured_candidate_repositories":len(repos),
 "profiled_unique_repositories":len(profiled),
 "missing_profile_repositories":missing,
 "profile_coverage_rate":(len(profiled)/len(repos)) if repos else 0,
 "dimension_metrics":dimension_metrics,
 "undercovered_searchable_targets":len(gaps),
 "instrumentation_debt_targets":sum(1 for x in rows if x["state"]=="INSTRUMENTATION_DEBT")
}
(INTEL/"coverage_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

report=[
 "# EXPLORATION COVERAGE REPORT","",
 "Coverage is measured against explicit exploration quotas, not an assumed distribution of valuable GitHub technology.","",
 f"- Measured runs: **{len(RUNS)}**",
 f"- Deep inspections reported: **{deep_total}**",
 f"- Structured candidate dispositions: **{structured_dispositions}**",
 f"- Unique structured candidate repositories: **{len(repos)}**",
 f"- Profiled unique repositories: **{len(profiled)} ({metrics['profile_coverage_rate']:.0%})**",
 f"- Searchable undercovered targets: **{len(gaps)}**",
 f"- Targets blocked by classification debt: **{metrics['instrumentation_debt_targets']}**","",
 "## Coverage by target","",
 "| Dimension | Target | State | Observed | Target minimum | Gap | Classification | Searchable |",
 "|---|---|---|---:|---:|---:|---:|---|"
]
for x in rows:
    report.append(f"| {x['dimension_label']} | {x['target_label']} | {x['state']} | {x['observed_unique_repositories']} | {x['target_min_repositories']} | {x['gap_repositories']} | {x['classification_rate']:.0%} | {'yes' if x['searchable'] else 'no'} |")
report += ["","## Metadata debt","",
           f"- Unprofiled repositories: {', '.join(missing) if missing else 'none'}.",
           "- Manual dimensions such as source institution, package ecosystem, protocol family and geography are not converted into blind-spot seeds until classification coverage reaches the configured threshold.",
           "- Missing classifications are not imputed from repository names or owner identity.",""]
(INTEL/"COVERAGE_REPORT.md").write_text("\n".join(report),encoding="utf-8")

gapmd=[
 "# EXPLORATION GAP QUEUE","",
 "These gaps are searchable, measurable blind spots produced by V8. Each should be intersected with a high-value capability hypothesis rather than searched in isolation.","",
 "| Priority | Gap | Dimension | Target | Observed / minimum | Query variants |",
 "|---:|---|---|---|---:|---|"
]
for x in gaps:
    gapmd.append(f"| {x['priority']} | {x['coverage_gap_id']} | {x['dimension_label']} | {x['target_label']} | {x['observed_unique_repositories']} / {x['target_min_repositories']} | {', '.join(x['query_variants'])} |")
(INTEL/"EXPLORATION_GAPS.md").write_text("\n".join(gapmd)+"\n",encoding="utf-8")
print(json.dumps({"profiles":len(profiled),"coverage_rate":metrics["profile_coverage_rate"],"searchable_gaps":len(gaps),"instrumentation_debt":metrics["instrumentation_debt_targets"]}))
