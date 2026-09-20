#!/usr/bin/env python3
import json
from collections import Counter
from ti_common import INTEL, load_jsonl

runs=[r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective","benchmark"}]
reason_catalog=json.loads((INTEL/"reason_codes.json").read_text(encoding="utf-8")) if (INTEL/"reason_codes.json").exists() else {}
reason_aliases=json.loads((INTEL/"reason_aliases.json").read_text(encoding="utf-8")) if (INTEL/"reason_aliases.json").exists() else {}
standard=set(v for vals in reason_catalog.values() for v in vals)

status_counts=Counter(); controlled=Counter(); direct=Counter(); alias_norm=Counter(); custom=Counter()
novelty=Counter(); evidence=Counter(); replacement_ranges=[]; total=0

def bucket(status):
    s=(status or "").lower()
    if "quarant" in s or "safety" in s: return "quarantined"
    if "reject" in s or "negative" in s: return "rejected_or_negative"
    if "master" in s: return "master"
    if "strong" in s: return "strong"
    if "watch" in s: return "watch"
    return "other"

for r in runs:
    for d in r.get("candidate_dispositions") or []:
        total+=1; status_counts[bucket(d.get("status"))]+=1
        legacy=d.get("reason_code"); std=d.get("reason_code_standard")
        if std in standard:
            controlled[std]+=1; direct[std]+=1
        elif legacy in standard:
            controlled[legacy]+=1; direct[legacy]+=1
        elif legacy in reason_aliases and reason_aliases[legacy] in standard:
            mapped=reason_aliases[legacy]; controlled[mapped]+=1; alias_norm[mapped]+=1
        elif legacy:
            custom[legacy]+=1
        if d.get("novelty_ordinal") is not None: novelty[int(d["novelty_ordinal"])]+=1
        if d.get("evidence_ordinal") is not None: evidence[int(d["evidence_ordinal"])]+=1
        lo,hi=d.get("replacement_days_low"),d.get("replacement_days_high")
        if lo is not None or hi is not None: replacement_ranges.append((lo,hi))

metrics={
 "candidate_dispositions":total,"status_counts":dict(status_counts),
 "controlled_reason_counts":dict(controlled),
 "direct_standard_count":sum(direct.values()),
 "alias_normalized_count":sum(alias_norm.values()),
 "unmapped_custom_reason_count":sum(custom.values()),
 "unique_unmapped_custom_reasons":len(custom),
 "top_unmapped_custom_reasons":custom.most_common(30),
 "novelty_ordinal_counts":dict(sorted(novelty.items())),
 "evidence_ordinal_counts":dict(sorted(evidence.items())),
 "replacement_range_count":len(replacement_ranges)
}
(INTEL/"candidate_learning_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")

lines=[
 "# NEGATIVE TRAINING / CANDIDATE LEARNING REPORT","",
 "Candidate dispositions are normalized into controlled reason categories while the original evidence-bearing reason text remains preserved in the source run.","",
 f"- Structured candidate dispositions: **{total}**",
 f"- Direct controlled reasons: **{metrics['direct_standard_count']}**",
 f"- Legacy reasons normalized through reviewed aliases: **{metrics['alias_normalized_count']}**",
 f"- Unmapped custom reasons: **{metrics['unmapped_custom_reason_count']}**",
 f"- Unique unmapped custom reason strings: **{metrics['unique_unmapped_custom_reasons']}**","",
 "## Disposition mix","",
 "| Status | Count |","|---|---:|"
]
for k,v in status_counts.most_common(): lines.append(f"| {k} | {v} |")
if not status_counts: lines.append("| — | 0 |")
lines += ["","## Controlled reason distribution","",
          "| Reason | Count | Alias-normalized |","|---|---:|---:|"]
for k,v in controlled.most_common(30): lines.append(f"| {k} | {v} | {alias_norm.get(k,0)} |")
if not controlled: lines.append("| — | 0 | 0 |")
lines += ["","## Remaining unmapped legacy reasons","",
          "| Reason | Count |","|---|---:|"]
for k,v in custom.most_common(25): lines.append(f"| {k} | {v} |")
if not custom: lines.append("| — | 0 |")
lines += ["","## Learning policy","",
          "- V4 runs use `reason_code_standard` for aggregation and `reason_detail` for precise technical evidence.",
          "- Reviewed aliases normalize old runs without rewriting their source history.",
          "- A frequent rejection reason becomes a cheap prefilter only after false-negative audits show it does not suppress unusual high-value discoveries.",
          "- Record false-negative rescues explicitly when a previously rejected/dominated candidate later becomes strong or MASTER.",""]
(INTEL/"NEGATIVE_TRAINING_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({"candidates":total,"direct":metrics["direct_standard_count"],"alias_normalized":metrics["alias_normalized_count"],"unmapped":metrics["unmapped_custom_reason_count"]}))
