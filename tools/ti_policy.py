#!/usr/bin/env python3
import json, math
from collections import defaultdict
from ti_common import INTEL, load_jsonl, outcome_search_weights

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
outs = load_jsonl("outcomes.jsonl")
strategies = load_jsonl("search_strategies.jsonl")
caps = load_jsonl("capabilities.jsonl")
experiments = load_jsonl("experiment_registry.jsonl")
aliases = json.loads((INTEL / "strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL / "strategy_aliases.json").exists() else {}

by_id = {s["strategy_id"]: s for s in strategies}
def parent(sid):
    s = by_id.get(sid)
    if s and s.get("parent_strategy_id"):
        return s["parent_strategy_id"]
    return aliases.get(sid, sid)

groups = defaultdict(list)
for r in runs:
    groups[parent(r.get("strategy_id"))].append(r)

exp_priority = {x["experiment_id"]: float(x.get("priority_weight") or 1.0) for x in experiments}
exp_status = {x["experiment_id"]: (x.get("status") or "UNKNOWN") for x in experiments}
cap_experiments = defaultdict(list)
for x in experiments:
    for cid in x.get("capability_ids", []):
        cap_experiments[cid].append(x)

def beta_mean(success, trials):
    return (success + 1) / (trials + 2) if trials >= 0 else .5

rows = []
active = [s for s in strategies if s.get("status") == "active"]

for s in active:
    sid = s["strategy_id"]
    rs = groups.get(sid, [])
    run_ids = {r["search_run_id"] for r in rs}
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs = sum(1 for r in rs if r.get("new_capability_ids"))

    priority_points = 0.0
    for r in rs:
        ids = r.get("experiment_ids") or []
        if not ids:
            continue
        priority_points += max(exp_priority.get(exp, 1.0) for exp in ids) / 3.0

    outcome_credit = 0.0
    passed_credit = 0.0
    partial_credit = 0.0
    for o in outs:
        if o.get("result") == "INVALID":
            continue
        weights = outcome_search_weights(o)
        credit = sum(weight for rid, weight in weights.items() if rid in run_ids)
        if credit <= 0:
            continue
        outcome_credit += credit
        if o.get("result") == "PASSED":
            passed_credit += credit
        elif o.get("result") == "PARTIAL":
            partial_credit += credit

    retain = beta_mean(retained, inspected) if inspected else .5
    master = beta_mean(promoted, inspected) if inspected else .5
    novel = beta_mean(novel_runs, len(rs)) if rs else .5
    experiment_relevance = beta_mean(priority_points, len(rs)) if rs else .5

    if outcome_credit:
        outcome_success_equiv = passed_credit + .5 * partial_credit
        outcome_signal = beta_mean(outcome_success_equiv, outcome_credit)
    else:
        outcome_signal = .5

    raw_exploit = (
        .18 * retain
        + .24 * master
        + .25 * novel
        + .18 * experiment_relevance
        + .15 * outcome_signal
    )

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
        "outcome_credit": outcome_credit,
        "experiment_priority_signal": priority_points,
        "raw_exploit_score": raw_exploit,
        "evidence_weight": evidence_weight,
        "exploit_mass": exploit_mass,
        "uncertainty": uncertainty,
        "sufficient_evidence": len(rs) >= 5 and inspected >= 20
    })

measured = len(runs)
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

def base_gap(c):
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

gaps = []
for c in caps:
    cid = c["capability_id"]
    linked = cap_experiments.get(cid, [])
    ready_like = [x for x in linked if (x.get("status") or "").upper() in {"READY", "RUNNING"}]
    blocked = [x for x in linked if (x.get("status") or "").upper() == "BLOCKED_EXTERNAL"]

    context_bonus = max((float(x.get("priority_weight") or 1.0) for x in ready_like), default=0.0)
    gap_score = base_gap(c)
    information_score = gap_score + context_bonus

    gaps.append({
        "capability_id": cid,
        "name": c["name"],
        "gap_score": gap_score,
        "information_score": information_score,
        "experiment_priority_bonus": context_bonus,
        "linked_experiments": [x["experiment_id"] for x in linked],
        "blocked_external_experiments": [x["experiment_id"] for x in blocked],
        "missing_piece": c.get("missing_piece"),
        "run_attention": attention[cid]
    })

gaps.sort(key=lambda x: (-x["information_score"], -x["gap_score"], x["capability_id"]))
gaps = gaps[:10]

policy = {
    "measured_runs": measured,
    "valid_outcomes": len(valid_out),
    "exploration_budget": exploration_budget,
    "strategy_allocation": rows,
    "priority_capability_gaps": gaps,
    "guardrails": {
        "min_runs_for_exploitation_claim": 5,
        "min_deep_inspections_for_exploitation_claim": 20,
        "never_zero_exploration": True,
        "recent_runs_not_treated_as_failed_outcomes": True,
        "outcome_credit_conserved": True,
        "blocked_external_does_not_create_search_bonus": True
    }
}
(INTEL / "search_policy.json").write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

lines = [
    "# ADAPTIVE SEARCH POLICY", "",
    "This is a cautious allocation recommendation, not an autonomous command. It separates empirical strategy quality from the current information value of active experiment gaps.", "",
    f"- Measured prospective or benchmark runs: **{measured}**",
    f"- Valid structured outcomes: **{len(valid_out)}**",
    f"- Exploration budget: **{exploration_budget:.0%}**",
    "- Strategies with fewer than 5 runs or 20 deep inspections remain insufficient evidence even if their suggested allocation is high.",
    "- Multi-run outcomes conserve total credit across origin searches.", "",
    "## Suggested strategy allocation", "",
    "| Strategy | Allocation | Runs | Inspected | Outcome credit | Evidence |",
    "|---|---:|---:|---:|---:|---|"
]

for x in rows:
    lines.append(
        f"| {x['strategy_id']} | {x['allocation']:.1%} | {x['runs']} | {x['inspected']} | "
        f"{x['outcome_credit']:.2f} | {'sufficient' if x['sufficient_evidence'] else 'insufficient'} |"
    )

lines += [
    "", "## Highest-information capability gaps", "",
    "| Capability | Information score | Base gap | Ready/P0-P1 bonus | Prior attention | Linked experiments | Missing piece |",
    "|---|---:|---:|---:|---:|---|---|"
]

for x in gaps:
    lines.append(
        f"| {x['capability_id']} — {x['name']} | {x['information_score']:.1f} | {x['gap_score']} | "
        f"{x['experiment_priority_bonus']:.1f} | {x['run_attention']} | "
        f"{', '.join(x['linked_experiments']) or '—'} | {x['missing_piece'] or '—'} |"
    )

lines += [
    "", "## Allocation guardrails", "",
    "- Strategy quality is empirical; experiment priority is context. P0 status does not prove a search method is better.",
    "- BLOCKED_EXTERNAL experiments do not add repository-search bonus when the named blocker is customer data or access.",
    "- READY/RUNNING experiment gaps may raise information value for bounded searches.",
    "- Do not suppress wildcard or novelty search to zero.",
    "- Absence of an outcome is not a failure until an experiment resolves.",
    "- Realized customer and engineering outcomes should gradually outweigh retained-repository precision as evidence accumulates.", ""
]

(INTEL / "SEARCH_POLICY.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({
    "measured_runs": measured,
    "valid_outcomes": len(valid_out),
    "exploration_budget": exploration_budget,
    "experiment_registry": len(experiments)
}))
