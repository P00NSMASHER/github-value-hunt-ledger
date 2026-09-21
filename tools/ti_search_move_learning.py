#!/usr/bin/env python3
"""Observe-first learning over individual retrieval moves inside search runs.

Whole-run strategy metrics are too coarse to learn quickly. This report measures
which retrieval moves surface useful/qualifying candidates, while preserving
minimum-sample gates and never treating a retrieval failure as evidence of absence.
"""
import json
from collections import defaultdict

from ti_common import INTEL, load_jsonl, is_discovery_run

runs = [
    r for r in load_jsonl("search_runs.jsonl")
    if r.get("measurement_quality") in {"prospective", "benchmark"} and is_discovery_run(r)
]

groups = defaultdict(lambda: {
    "uses": 0,
    "qualifying_hits": 0,
    "useful_hits": 0,
    "weak_hits": 0,
    "no_hits": 0,
    "retrieval_limited": 0,
    "blocked": 0,
    "unknown": 0,
    "candidate_count": 0,
    "deep_inspected": 0,
    "retained_count": 0,
})
objective_groups = defaultdict(lambda: defaultdict(lambda: {
    "uses": 0,
    "qualifying_hits": 0,
    "useful_hits": 0,
    "retrieval_limited": 0,
    "retained_count": 0,
}))

instrumented_runs = 0
move_count = 0
for run in runs:
    moves = run.get("search_moves") or []
    if moves:
        instrumented_runs += 1
    objective = run.get("search_objective_id") or "unclassified"
    for move in moves:
        move_type = move.get("move_type") or "other"
        result = move.get("result") or "unknown"
        g = groups[move_type]
        g["uses"] += 1
        move_count += 1
        if result == "qualifying_hit":
            g["qualifying_hits"] += 1
        elif result == "useful_hit":
            g["useful_hits"] += 1
        elif result == "weak_hit":
            g["weak_hits"] += 1
        elif result == "no_hit":
            g["no_hits"] += 1
        elif result == "retrieval_limited":
            g["retrieval_limited"] += 1
        elif result == "blocked":
            g["blocked"] += 1
        else:
            g["unknown"] += 1
        for key in ("candidate_count", "deep_inspected", "retained_count"):
            g[key] += move.get(key) or 0

        og = objective_groups[objective][move_type]
        og["uses"] += 1
        og["qualifying_hits"] += int(result == "qualifying_hit")
        og["useful_hits"] += int(result == "useful_hit")
        og["retrieval_limited"] += int(result == "retrieval_limited")
        og["retained_count"] += move.get("retained_count") or 0

rows = []
for move_type, g in groups.items():
    uses = g["uses"]
    rows.append({
        "move_type": move_type,
        **g,
        "qualifying_hit_rate": g["qualifying_hits"] / uses if uses else None,
        "productive_hit_rate": (g["qualifying_hits"] + g["useful_hits"]) / uses if uses else None,
        "retrieval_limit_rate": g["retrieval_limited"] / uses if uses else None,
        "sufficient_evidence": uses >= 8 and g["deep_inspected"] >= 8,
    })
rows.sort(key=lambda x: (
    -(x["productive_hit_rate"] or 0),
    -x["uses"],
    x["move_type"],
))

objective_rows = []
for objective, by_move in objective_groups.items():
    for move_type, g in by_move.items():
        uses = g["uses"]
        objective_rows.append({
            "search_objective_id": objective,
            "move_type": move_type,
            **g,
            "qualifying_hit_rate": g["qualifying_hits"] / uses if uses else None,
            "productive_hit_rate": (g["qualifying_hits"] + g["useful_hits"]) / uses if uses else None,
            "sufficient_evidence": uses >= 5,
        })
objective_rows.sort(key=lambda x: (
    x["search_objective_id"],
    -(x["productive_hit_rate"] or 0),
    -x["uses"],
    x["move_type"],
))

metrics = {
    "schema_version": 1,
    "discovery_runs": len(runs),
    "instrumented_runs": instrumented_runs,
    "search_moves": move_count,
    "move_types_observed": len(rows),
    "observe_only": True,
    "minimum_evidence": {
        "global_uses": 8,
        "global_deep_inspections": 8,
        "objective_uses": 5,
    },
    "by_move_type": rows,
    "by_objective_and_move_type": objective_rows,
}
(INTEL / "search_move_metrics.json").write_text(
    json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
)

def pct(value):
    return "—" if value is None else f"{100*value:.1f}%"

lines = [
    "# SEARCH MOVE LEARNING REPORT",
    "",
    "Observe-first learning at retrieval-move granularity. A move is a concrete search action such as code-signature search, lineage tracing or adjacent-domain invariant search. These observations do **not** currently change allocation automatically.",
    "",
    f"- Discovery runs: **{len(runs)}**",
    f"- Runs with move-level telemetry: **{instrumented_runs}**",
    f"- Recorded search moves: **{move_count}**",
    f"- Move types observed: **{len(rows)}**",
    "",
    "## Move-type evidence",
    "",
    "| Move type | Uses | Qualifying hit | Productive hit | Retrieval-limited | Deep | Retained | Evidence |",
    "|---|---:|---:|---:|---:|---:|---:|---|",
]
for x in rows:
    lines.append(
        f"| {x['move_type']} | {x['uses']} | {pct(x['qualifying_hit_rate'])} | "
        f"{pct(x['productive_hit_rate'])} | {pct(x['retrieval_limit_rate'])} | "
        f"{x['deep_inspected']} | {x['retained_count']} | "
        f"{'sufficient' if x['sufficient_evidence'] else 'insufficient'} |"
    )
if not rows:
    lines.append("| — | 0 | — | — | — | 0 | 0 | insufficient |")

lines += [
    "",
    "## Learning rules",
    "",
    "- Do not infer absence from a no-hit when the move was retrieval-limited or blocked.",
    "- Prefer objective-specific evidence over global averages when enough examples exist.",
    "- A productive move can still be expensive; whole-run outcome and effort telemetry remain authoritative for portfolio decisions.",
    "- Do not suppress low-frequency exploration because one move type has high early hit rate.",
    "- Search-move evidence becomes a scheduling prior only after minimum-sample gates and recall audits are satisfied.",
    "",
]
(INTEL / "SEARCH_MOVE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({
    "instrumented_runs": instrumented_runs,
    "search_moves": move_count,
    "move_types_observed": len(rows),
}))
