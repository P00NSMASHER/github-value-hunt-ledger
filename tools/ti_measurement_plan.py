#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl, is_discovery_run

runs = [r for r in load_jsonl("search_runs.jsonl") if is_discovery_run(r)]
strategies = [s for s in load_jsonl("search_strategies.jsonl") if s.get("status") == "active"]
aliases = json.loads((INTEL / "strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL / "strategy_aliases.json").exists() else {}
policy = json.loads((INTEL / "search_policy.json").read_text(encoding="utf-8")) if (INTEL / "search_policy.json").exists() else {}
curriculum = json.loads((INTEL / "learning_curriculum.json").read_text(encoding="utf-8")) if (INTEL / "learning_curriculum.json").exists() else {}
curriculum_by_id = {
    row["strategy_id"]: row
    for row in curriculum.get("rows", [])
    if isinstance(row, dict) and isinstance(row.get("strategy_id"), str)
}
by_id = {s["strategy_id"]: s for s in load_jsonl("search_strategies.jsonl")}

def parent(sid):
    s = by_id.get(sid)
    if s and s.get("parent_strategy_id"):
        return s["parent_strategy_id"]
    return aliases.get(sid, sid)

groups = defaultdict(list)
for r in runs:
    groups[parent(r.get("strategy_id"))].append(r)

allocation = {x["strategy_id"]: x.get("allocation", 0) for x in policy.get("strategy_allocation", [])}
rows = []
for s in strategies:
    sid = s["strategy_id"]
    rs = groups.get(sid, [])
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    runs_needed = max(0, 5 - len(rs))
    inspections_needed = max(0, 20 - inspected)
    missing_queries = sum(1 for r in rs if not r.get("queries"))
    missing_surfaces = sum(1 for r in rs if not r.get("search_surfaces"))
    missing_dispositions = sum(1 for r in rs if (r.get("candidate_count") or 0) > 0 and not r.get("candidate_dispositions"))
    measurement_debt = (runs_needed / 5.0) + (inspections_needed / 20.0)
    instrumentation_debt = (missing_queries + missing_surfaces + missing_dispositions) / max(1, 3 * len(rs))
    learning_row = curriculum_by_id.get(sid, {})
    learning_train = learning_row.get("train") or {}
    learning_confirm = learning_row.get("confirm") or {}
    rows.append({
        "strategy_id": sid,
        "name": s.get("name"),
        "runs": len(rs),
        "deep_inspected": inspected,
        "runs_needed": runs_needed,
        "inspections_needed": inspections_needed,
        "measurement_debt": measurement_debt,
        "instrumentation_debt": instrumentation_debt,
        "policy_allocation": allocation.get(sid, 0),
        "sufficient_evidence": runs_needed == 0 and inspections_needed == 0,
        "count_semantics": "observational_discovery",
        "learning_phase": learning_row.get("phase"),
        "learning_train_runs": learning_train.get("runs"),
        "learning_train_deep_inspections": learning_train.get("deep_inspections"),
        "learning_confirm_runs": learning_confirm.get("runs"),
        "learning_confirm_deep_inspections": learning_confirm.get("deep_inspections"),
        "learning_policy_eligible": learning_row.get("eligible_for_policy_consideration")
    })

rows.sort(key=lambda x: (-x["measurement_debt"], -x["policy_allocation"], x["strategy_id"]))
plan = {
    "thresholds": {"min_runs": 5, "min_deep_inspections": 20},
    "count_semantics": "observational_discovery",
    "learning_authority": "intelligence/learning_curriculum.json",
    "learning_note": (
        "Observational discovery counts are broader than adaptive-learning "
        "train/confirm counts. Use learning_* fields and LEARNING_CURRICULUM "
        "for policy-learning evidence."
    ),
    "active_strategies": len(rows),
    "sufficient_strategies": sum(1 for x in rows if x["sufficient_evidence"]),
    "rows": rows
}
(INTEL / "measurement_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

lines = [
    "# MEASUREMENT DEBT PLAN", "",
    "This report answers a different question from SEARCH_POLICY.md: not **where might value be**, but **what evidence is still missing before the system can credibly compare search strategies**.", "",
    f"- Active strategies: **{len(rows)}**",
    f"- Strategies with sufficient evidence: **{plan['sufficient_strategies']}**",
    "- Observational sufficiency threshold: **5 measured discovery runs + 20 deep inspections** per strategy.",
    "- These counts are broader than adaptive-learning eligibility. **LEARNING_CURRICULUM.md is authoritative for train/confirm evidence.**",
    "- Explicit fixture, artifact-verification, waiting and unclassified actions do not satisfy discovery thresholds. Legacy records without an action remain observational evidence.", "",
    "## Strategy measurement debt", "",
    "| Strategy | Obs runs | Obs inspected | Learning train | Learning confirm | Adaptive phase | More obs runs | More obs inspections | Instrumentation debt | Policy allocation |",
    "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|"
]
for x in rows:
    train = (
        f"{x['learning_train_runs']}/{x['learning_train_deep_inspections']}"
        if x.get("learning_train_runs") is not None
        else "—"
    )
    confirm = (
        f"{x['learning_confirm_runs']}/{x['learning_confirm_deep_inspections']}"
        if x.get("learning_confirm_runs") is not None
        else "—"
    )
    lines.append(
        f"| {x['strategy_id']} | {x['runs']} | {x['deep_inspected']} | {train} | {confirm} | "
        f"{x.get('learning_phase') or '—'} | {x['runs_needed']} | {x['inspections_needed']} | "
        f"{x['instrumentation_debt']:.0%} | {x['policy_allocation']:.1%} |"
    )
lines += [
    "", "## Operating rule", "",
    "- Treat observational measurement debt and adaptive-learning debt as different quantities; never infer train/confirm readiness from raw discovery counts.",
    "- Spend part of the exploration budget on reducing measurement debt, especially for zero-run strategies.",
    "- Do not manufacture deep inspections merely to hit 20; a bounded no-find run is valid evidence if the search was genuinely executed and logged.",
    "- Prefer prospective runs with complete literal queries, search surfaces and candidate dispositions so strategy comparisons remain interpretable.",
    "- Once a strategy clears the evidence threshold, additional runs should be justified by information value, active experiment gaps or outcome follow-through—not by quota.", ""
]
(INTEL / "MEASUREMENT_PLAN.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"active": len(rows), "sufficient": plan["sufficient_strategies"]}))
