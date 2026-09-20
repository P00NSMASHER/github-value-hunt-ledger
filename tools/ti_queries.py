#!/usr/bin/env python3
from collections import Counter
from ti_common import INTEL, canonical_query_family, load_jsonl, normalize_run_time, write_jsonl

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
groups = {}

for run in runs:
    qid = canonical_query_family(run)
    g = groups.setdefault(qid, {
        "query_family_id": qid,
        "labels": Counter(),
        "strategies": set(),
        "experiments": set(),
        "runs": 0,
        "candidates": 0,
        "deep_inspected": 0,
        "retained": 0,
        "master_promoted": 0,
        "new_capability_runs": 0,
        "first_seen": None,
        "last_seen": None
    })
    label = (run.get("query_family") or "unknown").strip()
    g["labels"][label] += 1
    if run.get("strategy_id"):
        g["strategies"].add(run["strategy_id"])
    for exp in run.get("experiment_ids", []):
        g["experiments"].add(exp)
    g["runs"] += 1
    g["candidates"] += run.get("candidate_count") or 0
    g["deep_inspected"] += run.get("deep_inspected") or 0
    g["retained"] += run.get("retained_count") or 0
    g["master_promoted"] += run.get("master_promoted_count") or 0
    if run.get("new_capability_ids"):
        g["new_capability_runs"] += 1
    when = normalize_run_time(run)
    if when:
        stamp = str(when)
        g["first_seen"] = min(g["first_seen"], stamp) if g["first_seen"] else stamp
        g["last_seen"] = max(g["last_seen"], stamp) if g["last_seen"] else stamp

rows = []
for qid, g in groups.items():
    labels = g.pop("labels")
    g["canonical_label"] = labels.most_common(1)[0][0] if labels else qid
    g["observed_labels"] = [x for x, _ in labels.most_common()]
    g["strategies"] = sorted(g["strategies"])
    g["experiments"] = sorted(g["experiments"])
    rows.append(g)

rows.sort(key=lambda x: (-x["runs"], -x["deep_inspected"], x["query_family_id"]))
write_jsonl("query_families.jsonl", rows)

lines = [
    "# QUERY FAMILY REPORT", "",
    "Stable query-family nodes aggregate repeated discovery methods without discarding the literal queries that produced them.", "",
    f"- Canonical query families: **{len(rows)}**",
    f"- Measured runs: **{len(runs)}**", "",
    "| Query family | Runs | Inspected | Retained | MASTER | New-capability runs | Experiments |",
    "|---|---:|---:|---:|---:|---:|---|"
]
for row in rows[:40]:
    lines.append(
        f"| {row['query_family_id']} | {row['runs']} | {row['deep_inspected']} | "
        f"{row['retained']} | {row['master_promoted']} | {row['new_capability_runs']} | "
        f"{', '.join(row['experiments']) or '—'} |"
    )

lines += [
    "", "## Policy", "",
    "- New runs should provide query_family_id when reusing an existing family.",
    "- Raw query_family remains human-readable and should describe the technical search shape.",
    "- Add an alias only when two raw labels are genuinely the same discovery family; do not merge merely because they share a domain.",
    "- Literal queries remain in search_runs.jsonl for reproducibility.", ""
]
(INTEL / "QUERY_FAMILY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(f"query_families={len(rows)}")
