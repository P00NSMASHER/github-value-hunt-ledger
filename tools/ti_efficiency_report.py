#!/usr/bin/env python3
"""Measure hunt efficiency without rewarding shallow work.

The purpose is to distinguish useful work avoided from work merely not done.
Duplicate avoidance gets credit only when a preflight found relevant prior evidence.
This report is observe-first and does not currently alter allocation.
"""
import json

from ti_common import INTEL, load_jsonl, is_discovery_run

runs = [
    r for r in load_jsonl("search_runs.jsonl")
    if r.get("measurement_quality") in {"prospective", "benchmark"} and is_discovery_run(r)
]

registry_path = INTEL / "registry_metrics.json"
registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}

instrumented = [
    r for r in runs
    if any(r.get(k) is not None for k in (
        "candidate_preflight_checks",
        "known_candidate_preflight_hits",
        "duplicate_deep_inspections_avoided",
    ))
]

checks = sum((r.get("candidate_preflight_checks") or 0) for r in instrumented)
known_hits = sum((r.get("known_candidate_preflight_hits") or 0) for r in instrumented)
avoided = sum((r.get("duplicate_deep_inspections_avoided") or 0) for r in instrumented)

deep = sum((r.get("deep_inspected") or 0) for r in runs)
retained = sum((r.get("retained_count") or 0) for r in runs)
tool_calls = sum((r.get("tool_calls") or 0) for r in runs if r.get("tool_calls") is not None)
tool_call_observed = sum(1 for r in runs if r.get("tool_calls") is not None)
elapsed = sum((r.get("elapsed_minutes") or 0) for r in runs if r.get("elapsed_minutes") is not None)
elapsed_observed = sum(1 for r in runs if r.get("elapsed_minutes") is not None)

metrics = {
    "schema_version": 1,
    "discovery_runs": len(runs),
    "preflight_instrumented_runs": len(instrumented),
    "candidate_preflight_checks": checks,
    "known_candidate_preflight_hits": known_hits,
    "duplicate_deep_inspections_avoided": avoided,
    "preflight_known_hit_rate": known_hits / checks if checks else None,
    "avoidance_per_known_hit": avoided / known_hits if known_hits else None,
    "deep_inspected": deep,
    "retained_count": retained,
    "deep_inspections_per_retained": deep / retained if retained else None,
    "tool_calls_observed_runs": tool_call_observed,
    "tool_calls_observed_total": tool_calls,
    "elapsed_observed_runs": elapsed_observed,
    "elapsed_minutes_observed_total": elapsed,
    "registry_duplicate_observation_rate": registry.get("duplicate_observation_rate"),
    "registry_duplicate_observations": registry.get("duplicate_observations"),
    "registry_unknown_revision_records": registry.get("unknown_revision_records"),
    "observe_only": True,
}
(INTEL / "efficiency_metrics.json").write_text(
    json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
)

def pct(v):
    return "—" if v is None else f"{100*v:.1f}%"

def num(v, digits=2):
    return "—" if v is None else f"{v:.{digits}f}"

lines = [
    "# HUNTER EFFICIENCY REPORT",
    "",
    "Observe-first efficiency metrics. The network gets no credit for shallow work merely because it was cheap; duplicate avoidance counts only when prior evidence made a deep inspection redundant.",
    "",
    f"- Discovery runs: **{len(runs)}**",
    f"- Preflight-instrumented runs: **{len(instrumented)}**",
    f"- Candidate preflight checks: **{checks}**",
    f"- Known-candidate preflight hits: **{known_hits}** ({pct(metrics['preflight_known_hit_rate'])})",
    f"- Duplicate deep inspections avoided: **{avoided}**",
    f"- Deep inspections per retained candidate: **{num(metrics['deep_inspections_per_retained'])}**",
    f"- Registry duplicate observations: **{registry.get('duplicate_observations', 0):,}** "
    f"({pct(registry.get('duplicate_observation_rate'))})",
    f"- Registry unknown-revision records: **{registry.get('unknown_revision_records', 0):,}**",
    "",
    "## Interpretation",
    "",
    "- A preflight hit does not automatically mean skip: reopen for a new revision, new capability/evidence delta, contradiction, experiment need or provenance repair.",
    "- Count an avoided deep inspection only when the current assignment would otherwise have repeated substantially the same evidence work.",
    "- Falling deep-inspection cost is useful only if recall, verifier quality and downstream outcomes remain stable or improve.",
    "- Tool-call and elapsed-time comparisons are valid only where those denominators were actually observed.",
    "- Do not optimize for a high avoidance count; the goal is less redundant work, not less curiosity.",
    "",
]
(INTEL / "EFFICIENCY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps(metrics))
