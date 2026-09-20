#!/usr/bin/env python3
import json,math
from collections import defaultdict
from ti_common import INTEL,load_jsonl

audits=load_jsonl("triage_audits.jsonl")
runs=load_jsonl("search_runs.jsonl")
policy=json.loads((INTEL/"triage_policy.json").read_text(encoding="utf-8"))
groups=defaultdict(list)
for a in audits: groups[a.get("prefilter_reason_standard","unknown")].append(a)

def wilson_upper(k,n,z=1.96):
    if not n: return None
    p=k/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return min(1,center+half)

rows=[]
for reason,aa in groups.items():
    material=sum(1 for a in aa if a.get("false_negative_level") in {"material","master_grade"})
    any_fn=sum(1 for a in aa if a.get("false_negative_level")!="none")
    n=len(aa)
    rows.append({
      "reason_code_standard":reason,"audited_rejects":n,"any_false_negatives":any_fn,
      "material_false_negatives":material,"material_rate":material/n if n else None,
      "material_rate_wilson_upper_95":wilson_upper(material,n),
      "prefilter_candidate_eligible":n>=policy["min_audited_rejects_before_prefilter_candidate"] and material<=policy["max_material_false_negatives_before_prefilter_candidate"]
    })
rows.sort(key=lambda x:(-x["audited_rejects"],x["reason_code_standard"]))

eligible_runs=[]; compliant=0
for r in runs:
    rejected=r.get("triage_rejected_count")
    if rejected is None or rejected<policy["min_triage_rejects_for_required_holdout"]: continue
    sample=r.get("holdout_sample_count") or 0
    required=max(policy["min_holdout_sample_count"],math.ceil(rejected*policy["holdout_target_rate"]))
    eligible_runs.append((r["search_run_id"],rejected,sample,required))
    if sample>=required: compliant+=1

metrics={
 "audits":len(audits),"reason_rows":rows,
 "holdout_eligible_runs":len(eligible_runs),"holdout_compliant_runs":compliant,
 "hard_filter_auto_enable":policy.get("hard_filter_auto_enable",False)
}
(INTEL/"triage_audit_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
lines=[
 "# TRIAGE FALSE-NEGATIVE AUDIT","",
 "Cheap rejection rules can improve speed but can also erase the hunt's rarest discoveries. V5 therefore requires a sampled holdout audit before any reason code can be considered for stronger prefiltering.","",
 f"- Audited triage rejects: **{len(audits)}**",f"- Runs subject to holdout sampling rule: **{len(eligible_runs)}**",
 f"- Holdout-compliant runs: **{compliant}/{len(eligible_runs)}**",f"- Automatic hard-filter enablement: **{'on' if policy.get('hard_filter_auto_enable') else 'off'}**","",
 "## Reason-level audit evidence","",
 "| Reason | Audited | Any false negatives | Material false negatives | 95% upper material rate | Prefilter candidate? |",
 "|---|---:|---:|---:|---:|---|"
]
for x in rows:
    upper="—" if x["material_rate_wilson_upper_95"] is None else f"{x['material_rate_wilson_upper_95']:.1%}"
    lines.append(f"| {x['reason_code_standard']} | {x['audited_rejects']} | {x['any_false_negatives']} | {x['material_false_negatives']} | {upper} | {'yes' if x['prefilter_candidate_eligible'] else 'no'} |")
if not rows: lines.append("| — | 0 | 0 | 0 | — | no |")
lines += ["","## Safety policy","",
          "- No reason code becomes an automatic hard filter from historical rejection frequency alone.",
          "- Sample rejected candidates for deep review; prioritize novelty/edge cases as well as random holdouts.",
          "- A material/master-grade false negative immediately blocks hard-filter candidacy for that reason.",
          "- Even an eligible reason remains advisory because hard_filter_auto_enable is false; human/integrator review controls policy changes.",""]
(INTEL/"TRIAGE_AUDIT_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"audits":len(audits),"eligible_runs":len(eligible_runs),"compliant":compliant}))
