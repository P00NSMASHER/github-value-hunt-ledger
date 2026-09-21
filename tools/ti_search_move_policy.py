#!/usr/bin/env python3
"""Build a cautious search-move curriculum from move-level evidence.

This is a recommendation layer, not an autonomous allocator. It stays observe-only
until several move types have enough prospective evidence, and it always preserves
an exploration floor so unusual discovery methods are not optimized away.
"""
import json
import math

from ti_common import INTEL

MOVE_TYPES = [
    "direct_domain_search",
    "code_signature_search",
    "official_source_trace",
    "organization_graph",
    "contributor_or_commit_lineage",
    "paper_to_code_lineage",
    "package_or_dependency_graph",
    "adjacent_domain_invariant",
    "independent_comparator",
    "history_archaeology",
    "other",
]

path = INTEL / "search_move_metrics.json"
data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
observed = {row["move_type"]: row for row in data.get("by_move_type", [])}

rows = []
for move_type in MOVE_TYPES:
    row = observed.get(move_type, {})
    uses = row.get("uses", 0)
    productive = row.get("productive_hit_rate")
    qualifying = row.get("qualifying_hit_rate")
    retrieval = row.get("retrieval_limit_rate")
    deep = row.get("deep_inspected", 0)
    sufficient = bool(row.get("sufficient_evidence"))
    # Beta-smoothed usefulness; retrieval debt subtracts only when observed.
    hits = row.get("qualifying_hits", 0) + row.get("useful_hits", 0)
    exploit = (hits + 1) / (uses + 2)
    if retrieval is not None:
        exploit *= max(0.5, 1 - 0.35 * retrieval)
    uncertainty = 1 / math.sqrt(uses + 1)
    rows.append({
        "move_type": move_type,
        "uses": uses,
        "deep_inspected": deep,
        "productive_hit_rate": productive,
        "qualifying_hit_rate": qualifying,
        "retrieval_limit_rate": retrieval,
        "sufficient_evidence": sufficient,
        "exploit_score": exploit,
        "uncertainty": uncertainty,
        "last_seen": row.get("last_seen"),
        "recent_30d_uses": row.get("recent_30d_uses", 0),
    })

sufficient_types = [r for r in rows if r["sufficient_evidence"]]
mode = "observe_only_insufficient_evidence"
active = len(sufficient_types) >= 3
exploration_floor = 0.40 if active else 1.0
if active:
    mode = "cautious_recommendation"

sum_uncertainty = sum(r["uncertainty"] for r in rows) or 1
sum_exploit = sum(r["exploit_score"] for r in rows if r["sufficient_evidence"]) or 1

for r in rows:
    exploration = r["uncertainty"] / sum_uncertainty
    exploitation = (
        r["exploit_score"] / sum_exploit if r["sufficient_evidence"] and active else 0
    )
    r["recommended_share"] = (
        exploration_floor * exploration + (1 - exploration_floor) * exploitation
    )

total = sum(r["recommended_share"] for r in rows) or 1
for r in rows:
    r["recommended_share"] /= total

rows.sort(key=lambda r: (-r["recommended_share"], r["move_type"]))

policy = {
    "schema_version": 1,
    "mode": mode,
    "active_recommendation": active,
    "exploration_floor": exploration_floor,
    "sufficient_move_types": len(sufficient_types),
    "move_types": rows,
    "guardrails": {
        "minimum_sufficient_move_types_before_activation": 3,
        "move_level_policy_is_recommendation_not_command": True,
        "never_zero_exploration": True,
        "retrieval_limited_is_not_absence": True,
        "objective_specific_evidence_should_override_global_when_sufficient": True,
        "stale_methods_require_revalidation": True,
    },
}
(INTEL / "search_move_policy.json").write_text(
    json.dumps(policy, indent=2) + "\n", encoding="utf-8"
)

lines = [
    "# SEARCH MOVE CURRICULUM",
    "",
    f"Mode: **{mode}**",
    "",
    "This is a cautious retrieval-method curriculum, not an autonomous command. It balances learning which search moves work with preserving unusual/underused discovery paths.",
    "",
    f"- Sufficient move types: **{len(sufficient_types)}**",
    f"- Exploration floor: **{exploration_floor:.0%}**",
    f"- Active recommendation: **{'yes' if active else 'no'}**",
    "",
    "| Move type | Recommended share | Uses | Productive hit | Retrieval-limited | Evidence |",
    "|---|---:|---:|---:|---:|---|",
]
for r in rows:
    prod = "—" if r["productive_hit_rate"] is None else f"{100*r['productive_hit_rate']:.1f}%"
    retrieval = "—" if r["retrieval_limit_rate"] is None else f"{100*r['retrieval_limit_rate']:.1f}%"
    lines.append(
        f"| {r['move_type']} | {100*r['recommended_share']:.1f}% | {r['uses']} | "
        f"{prod} | {retrieval} | {'sufficient' if r['sufficient_evidence'] else 'insufficient'} |"
    )

lines += [
    "",
    "## Use",
    "",
    "- While inactive, interpret shares only as an exploration curriculum: diversify methods and collect telemetry.",
    "- Once active, use high-evidence moves as priors, not mandatory recipes; assignment-specific anchors still control.",
    "- Keep at least one materially different exploration path available on true discovery tasks when budget permits.",
    "- Revalidate stale move priors after material ecosystem/tool changes.",
    "- Never convert a retrieval-limited move into evidence that a capability is absent.",
    "",
]
(INTEL / "SEARCH_MOVE_POLICY.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({
    "mode": mode,
    "active": active,
    "sufficient_move_types": len(sufficient_types),
    "exploration_floor": exploration_floor,
}))
