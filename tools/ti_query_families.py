#!/usr/bin/env python3
import hashlib, json
from collections import defaultdict
from datetime import datetime
from ti_common import INTEL, load_jsonl, normalize_run_time, slug, write_jsonl

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
aliases_path = INTEL / "query_family_aliases.json"
aliases = json.loads(aliases_path.read_text(encoding="utf-8")) if aliases_path.exists() else {}

def raw_family_id(label):
    base = slug(label or "unknown")
    if not base:
        base = "unknown"
    return "QF:" + base[:120]

def canonical_family_id(label):
    rid = raw_family_id(label)
    return aliases.get(rid, rid)

def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

groups = defaultdict(list)
for r in runs:
    groups[canonical_family_id(r.get("query_family") or "unknown")].append(r)

rows = []
for qid, rs in groups.items():
    labels = [r.get("query_family") or "unknown" for r in rs]
    label_counts = defaultdict(int)
    for x in labels:
        label_counts[x] += 1
    canonical_label = sorted(label_counts, key=lambda x: (-label_counts[x], x))[0]
    times = [parse_time(normalize_run_time(r)) for r in rs]
    times = [t for t in times if t]
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    rows.append({
        "query_family_id": qid,
        "label": canonical_label,
        "aliases_seen": sorted(set(labels)),
        "run_count": len(rs),
        "candidate_count": sum((r.get("candidate_count") or 0) for r in rs),
        "deep_inspected": inspected,
        "retained_count": retained,
        "master_promoted_count": promoted,
        "new_capability_run_count": sum(1 for r in rs if r.get("new_capability_ids")),
        "experiment_run_count": sum(1 for r in rs if r.get("experiment_ids")),
        "strategy_ids": sorted(set(r.get("strategy_id") for r in rs if r.get("strategy_id"))),
        "search_surfaces": sorted(set(s for r in rs for s in (r.get("search_surfaces") or []))),
        "first_seen": min(times).isoformat() if times else None,
        "last_seen": max(times).isoformat() if times else None,
        "evidence_state": "sufficient" if len(rs) >= 5 and inspected >= 20 else "insufficient"
    })

rows.sort(key=lambda x: (-x["run_count"], -x["deep_inspected"], x["query_family_id"]))
write_jsonl("query_families.jsonl", rows)

one_off = sum(1 for x in rows if x["run_count"] == 1)
lines = [
    "# QUERY FAMILY REPORT", "",
    "Query families are canonicalized independently from literal search strings so the system can learn reusable search patterns without collapsing distinct hypotheses too early.", "",
    f"- Measured query families: **{len(rows)}**",
    f"- One-run families: **{one_off}**",
    f"- Families with sufficient evidence (>=5 runs and >=20 deep inspections): **{sum(1 for x in rows if x['evidence_state']=='sufficient')}**", "",
    "## Family measurements", "",
    "| Query family | Runs | Inspected | Retained | MASTER | Capability runs | Experiment runs | Evidence |",
    "|---|---:|---:|---:|---:|---:|---:|---|"
]
for x in rows[:50]:
    lines.append(
        f"| {x['query_family_id']} — {x['label']} | {x['run_count']} | {x['deep_inspected']} | "
        f"{x['retained_count']} | {x['master_promoted_count']} | {x['new_capability_run_count']} | "
        f"{x['experiment_run_count']} | {x['evidence_state']} |"
    )
if not rows:
    lines.append("| — | 0 | 0 | 0 | 0 | 0 | 0 | insufficient |")
lines += [
    "", "## Interpretation", "",
    "- A one-off query family is a hypothesis, not a learned policy.",
    "- Reuse the same family ID when the underlying conjunction/invariant is the same even if literal queries change.",
    "- Use `query_family_aliases.json` to merge wording variants only after manual review; never auto-merge families by text similarity alone.",
    "- Literal queries remain preserved in search runs for reproducibility.", ""
]
(INTEL / "QUERY_FAMILY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(f"query_families={len(rows)} one_off={one_off}")
