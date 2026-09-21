#!/usr/bin/env python3
import json, math
from collections import defaultdict
from ti_common import INTEL, ROOT, load_jsonl, is_discovery_run

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
discovery_runs = [r for r in runs if is_discovery_run(r)]
outs = load_jsonl("outcomes.jsonl")
strategies = load_jsonl("search_strategies.jsonl")
caps = load_jsonl("capabilities.jsonl")
aliases = json.loads((INTEL / "strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL / "strategy_aliases.json").exists() else {}
attr = json.loads((INTEL / "attribution_metrics.json").read_text(encoding="utf-8")) if (INTEL / "attribution_metrics.json").exists() else {"by_strategy":[]}
attr_map = {x["id"]: x for x in attr.get("by_strategy", [])}

domain_policy_path = INTEL / "domain_search_policies.json"
domain_constraints = []
blocked_exclusive_capabilities = set()
if domain_policy_path.exists():
    domain_config = json.loads(domain_policy_path.read_text(encoding="utf-8"))
    for domain in domain_config.get("domains", []):
        if domain.get("gate_type") != "gap_registry_active_search":
            continue
        register_path = ROOT / domain["gate_path"]
        register = json.loads(register_path.read_text(encoding="utf-8"))
        active_gap_ids = sorted(
            gap["gap_id"]
            for gap in register.get("gaps", [])
            if gap.get("status") == "ACTIVE_SEARCH" and gap.get("search_allowed") is True
        )
        active_set = set(active_gap_ids)
        capability_gap_map = domain.get("capability_gap_map") or {}
        authorized_capabilities = sorted(
            cid for cid, gap_ids in capability_gap_map.items()
            if active_set.intersection(gap_ids)
        )
        blocked_capabilities = sorted(set(capability_gap_map) - set(authorized_capabilities))
        blocked_exclusive_capabilities.update(blocked_capabilities)
        domain_constraints.append({
            "domain_id": domain["domain_id"],
            "experiment_id": domain.get("experiment_id"),
            "gate_path": domain["gate_path"],
            "search_authorized": bool(active_gap_ids),
            "active_search_gap_ids": active_gap_ids,
            "authorized_exclusive_capability_ids": authorized_capabilities,
            "blocked_exclusive_capability_ids": blocked_capabilities,
            "shared_capability_ids": sorted(domain.get("shared_capability_ids") or []),
            "reason": domain.get("reason"),
        })

by_id = {s["strategy_id"]: s for s in strategies}
def parent(sid):
    s = by_id.get(sid)
    if s and s.get("parent_strategy_id"):
        return s["parent_strategy_id"]
    return aliases.get(sid, sid)

groups = defaultdict(list)
for r in runs:
    groups[parent(r.get("strategy_id"))].append(r)

out_by_run = defaultdict(list)
for o in outs:
    for rid in o.get("origin_search_ids", []):
        out_by_run[rid].append(o)

def beta_mean(success, trials):
    return (success + 1) / (trials + 2) if trials >= 0 else .5

rows = []
active = [s for s in strategies if s.get("status") == "active"]
for s in active:
    sid = s["strategy_id"]
    all_activity = groups.get(sid, [])
    rs = [r for r in all_activity if is_discovery_run(r)]
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs = sum(1 for r in rs if r.get("new_capability_ids"))
    experiment_runs = sum(1 for r in rs if r.get("experiment_ids"))

    unique_outcomes = {}
    for r in all_activity:
        for o in out_by_run.get(r["search_run_id"], []):
            unique_outcomes[o.get("outcome_id")] = o
    valid = [o for o in unique_outcomes.values() if o.get("result") != "INVALID"]

    retain = beta_mean(retained, inspected) if inspected else .5
    master = beta_mean(promoted, inspected) if inspected else .5
    novel = beta_mean(novel_runs, len(rs)) if rs else .5
    experiment = beta_mean(experiment_runs, len(rs)) if rs else .5

    a = attr_map.get(sid, {})
    frac_trials = a.get("fractional_outcome_equivalents", 0)
    frac_passed = a.get("fractional_passed_equivalents", 0)
    outcome = beta_mean(frac_passed, frac_trials) if frac_trials else .5
    raw_exploit = .18 * retain + .24 * master + .25 * novel + .18 * experiment + .15 * outcome

    run_weight = min(1.0, len(rs) / 5.0)
    inspection_weight = min(1.0, inspected / 20.0) if inspected else 0.0
    evidence_weight = min(run_weight, inspection_weight)
    exploit_mass = raw_exploit * evidence_weight

    uncertainty = 1 / math.sqrt(len(rs) + 1)
    rows.append({
        "strategy_id": sid,
        "name": s.get("name"),
        "runs": len(rs),
        "inspected": inspected,
        "assisted_outcomes": len(valid),
        "fractional_outcome_equivalents": frac_trials,
        "raw_exploit_score": raw_exploit,
        "evidence_weight": evidence_weight,
        "exploit_mass": exploit_mass,
        "uncertainty": uncertainty,
        "sufficient_evidence": len(rs) >= 5 and inspected >= 20
    })

measured = len(discovery_runs)
valid_out = [o for o in outs if o.get("result") != "INVALID"]
if len(valid_out) < 3 or measured < 30:
    exploration_budget = .50
elif len(valid_out) < 10:
    exploration_budget = .40
else:
    exploration_budget = .25

sum_u = sum(x["uncertainty"] for x in rows) or 1
sum_e = sum(x["exploit_mass"] for x in rows)
measured_rows = [x for x in rows if x["runs"] > 0]

for x in rows:
    x["exploration_component"] = x["uncertainty"] / sum_u
    if sum_e > 0:
        x["exploitation_component"] = x["exploit_mass"] / sum_e
    elif measured_rows:
        x["exploitation_component"] = (1 / len(measured_rows)) if x["runs"] > 0 else 0
    else:
        x["exploitation_component"] = 1 / len(rows) if rows else 0
    x["allocation"] = (
        exploration_budget * x["exploration_component"]
        + (1 - exploration_budget) * x["exploitation_component"]
    )

normalizer = sum(x["allocation"] for x in rows) or 1
for x in rows:
    x["allocation"] /= normalizer
rows.sort(key=lambda x: (-x["allocation"], x["strategy_id"]))

attention = defaultdict(int)
for r in runs:
    for cid in r.get("new_capability_ids", []) + r.get("strengthened_capability_ids", []):
        attention[cid] += 1

def gap(c):
    score = 0
    if c.get("evidence_state") == "watch":
        score += 3
    elif c.get("evidence_state") == "source_or_test_validated":
        score += 2
    elif c.get("evidence_state") == "benchmarked":
        score += 1
    if c.get("missing_piece"):
        score += 2
    if len(c.get("primary_components") or []) < 2:
        score += 2
    if attention[c["capability_id"]] == 0:
        score += 1
    return score

gap_candidates = [
    {
        "capability_id": c["capability_id"],
        "name": c["name"],
        "gap_score": gap(c),
        "missing_piece": c.get("missing_piece"),
        "run_attention": attention[c["capability_id"]]
    }
    for c in caps if c["capability_id"] not in blocked_exclusive_capabilities
]
gaps = sorted(gap_candidates, key=lambda x: (-x["gap_score"], x["capability_id"]))[:10]

policy_obj = {
    "measured_runs": measured,
    "total_measured_activity_runs": len(runs),
    "excluded_nonsearch_or_unclassified_runs": len(runs) - measured,
    "legacy_unclassified_discovery_runs": sum('work_action' not in r for r in discovery_runs),
    "discovery_denominator_policy": "explicit_search_plus_legacy_action_absent; all_activity_outcome_credit_preserved",
    "valid_outcomes": len(valid_out),
    "exploration_budget": exploration_budget,
    "outcome_attribution_method": "equal_touch_fractional_credit",
    "strategy_allocation": rows,
    "priority_capability_gaps": gaps,
    "domain_constraints": domain_constraints,
    "guardrails": {
        "min_runs_for_exploitation_claim": 5,
        "min_deep_inspections_for_exploitation_claim": 20,
        "never_zero_exploration": True,
        "recent_runs_not_treated_as_failed_outcomes": True,
        "domain_authorization_precedes_generic_gap_ranking": True,
        "multi_origin_outcomes_not_full_credited_to_every_strategy": True
    }
}
(INTEL / "search_policy.json").write_text(json.dumps(policy_obj, indent=2) + "\n", encoding="utf-8")

lines = [
    "# ADAPTIVE SEARCH POLICY", "",
    "This is a cautious allocation recommendation, not an autonomous command. It blends empirical yield with an explicit exploration budget so unusual low-frequency discoveries are not optimized away.", "",
    f"- Measured prospective or benchmark discovery runs: **{measured}**",
    f"- Other measured actions excluded from discovery denominators: **{len(runs) - measured}**; outcome credit remains included.",
    "- Historical records without work_action retain their observational status; explicit non-search or unclassified actions cannot satisfy discovery evidence gates.",
    f"- Valid structured outcomes: **{len(valid_out)}**",
    f"- Exploration budget: **{exploration_budget:.0%}**",
    "- Multi-origin outcomes use fractional equal-touch credit rather than being counted in full for every strategy.",
    "- Strategies with fewer than 5 runs or 20 deep inspections remain **insufficient evidence** even if their suggested allocation is high.", "",
    "## Suggested strategy allocation", "",
    "| Strategy | Allocation | Runs | Inspected | Outcome eq. | Evidence |",
    "|---|---:|---:|---:|---:|---|"
]
for x in rows:
    lines.append(f"| {x['strategy_id']} | {x['allocation']:.1%} | {x['runs']} | {x['inspected']} | {x['fractional_outcome_equivalents']:.2f} | {'sufficient' if x['sufficient_evidence'] else 'insufficient'} |")
lines += ["", "## Highest-information capability gaps", "",
          "| Capability | Gap score | Prior run attention | Missing piece |",
          "|---|---:|---:|---|"]
for x in gaps:
    lines.append(f"| {x['capability_id']} — {x['name']} | {x['gap_score']} | {x['run_attention']} | {x['missing_piece'] or '—'} |")
lines += ["", "## Domain authorization constraints", "",
          "| Domain | Experiment | Search authorized | Active search gaps | Suppressed exclusive capability gaps | Shared capability scope |",
          "|---|---|---|---|---|---|"]
for x in domain_constraints:
    lines.append(
        f"| {x['domain_id']} | {x.get('experiment_id') or '—'} | "
        f"{'yes' if x['search_authorized'] else 'no'} | "
        f"{', '.join(x['active_search_gap_ids']) or 'none'} | "
        f"{', '.join(x['blocked_exclusive_capability_ids']) or 'none'} | "
        f"{', '.join(x['shared_capability_ids']) or 'none'} |"
    )
if not domain_constraints:
    lines.append("| — | — | — | — | — | — |")
lines += ["", "## Allocation guardrails", "",
          "- Never interpret a high allocation as proof that a strategy is better; early allocation includes uncertainty-driven exploration.",
          "- Do not suppress wildcard or novelty search to zero.",
          "- Domain authorization overrides generic capability-gap ranking; a blocked domain cannot be reopened by a high adaptive gap score.",
          "- Outcome credit is explicit and lag-aware; absence of an outcome is not a failure until an experiment actually resolves.",
          "- SEARCH_POLICY.md answers where to allocate effort; MEASUREMENT_PLAN.md separately answers what evidence is missing before comparisons are credible.",
          "- When sufficient evidence accumulates, realized customer and engineering outcomes should gradually outweigh retained-repository precision.", ""]
(INTEL / "SEARCH_POLICY.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"measured_runs": measured, "valid_outcomes": len(valid_out), "exploration_budget": exploration_budget, "domain_constraints": len(domain_constraints)}))
