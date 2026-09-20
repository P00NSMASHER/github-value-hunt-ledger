#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl, slug

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
attr_path = INTEL / "attribution_metrics.json"
attr = json.loads(attr_path.read_text(encoding="utf-8")) if attr_path.exists() else {"by_surface":[]}
attr_map = {x["id"]: x for x in attr.get("by_surface", [])}

groups = defaultdict(list)
labels = defaultdict(set)
for r in runs:
    for s in sorted(set(r.get("search_surfaces") or [])):
        sid = "SURFACE:" + slug(s)
        groups[sid].append(r)
        labels[sid].add(s)

rows = []
for sid, rs in groups.items():
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    a = attr_map.get(sid, {})
    rows.append({
        "surface_id": sid,
        "labels_seen": sorted(labels[sid]),
        "runs": len(rs),
        "deep_inspected": inspected,
        "retained_count": retained,
        "master_promoted_count": promoted,
        "capability_touch_runs": sum(1 for r in rs if r.get("new_capability_ids") or r.get("strengthened_capability_ids")),
        "experiment_runs": sum(1 for r in rs if r.get("experiment_ids")),
        "assisted_outcome_count": a.get("assisted_outcome_count", 0),
        "fractional_outcome_equivalents": a.get("fractional_outcome_equivalents", 0)
    })
rows.sort(key=lambda x: (-x["runs"], -x["deep_inspected"], x["surface_id"]))
(INTEL / "surface_metrics.json").write_text(json.dumps({"rows":rows}, indent=2) + "\n", encoding="utf-8")

lines = [
    "# SEARCH SURFACE REPORT", "",
    "Runs can use multiple surfaces, so these are **assisted surface measurements**, not isolated causal effects.", "",
    f"- Measured surfaces: **{len(rows)}**",
    f"- Runs missing search-surface instrumentation: **{sum(1 for r in runs if not r.get('search_surfaces'))}**", "",
    "| Surface | Runs | Inspected | Retained | MASTER | Capability-touch runs | Experiment runs | Fractional outcome eq. |",
    "|---|---:|---:|---:|---:|---:|---:|---:|"
]
for x in rows:
    display = "; ".join(x["labels_seen"][:2])
    lines.append(
        f"| {x['surface_id']} — {display} | {x['runs']} | {x['deep_inspected']} | {x['retained_count']} | "
        f"{x['master_promoted_count']} | {x['capability_touch_runs']} | {x['experiment_runs']} | "
        f"{x['fractional_outcome_equivalents']:.2f} |"
    )
if not rows:
    lines.append("| — | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 |")
lines += [
    "", "## Interpretation", "",
    "- Surface usage is multi-touch; do not conclude that a surface caused a discovery unless compared in a controlled search.",
    "- Missing surface instrumentation is measurement debt and should fall toward zero.",
    "- Once enough runs exist, use this report to test whether code search, repository search, history/issues, first-party docs, package ecosystems or adjacency traversal have different yields.", ""
]
(INTEL / "SURFACE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(f"surfaces={len(rows)}")
