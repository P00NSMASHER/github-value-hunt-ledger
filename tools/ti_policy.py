#!/usr/bin/env python3
import json, math
from collections import defaultdict
from ti_common import INTEL, load_jsonl

runs = [r for r in load_jsonl("search_runs.jsonl") if r.get("measurement_quality") in {"prospective", "benchmark"}]
outs = load_jsonl("outcomes.jsonl")
strategies = load_jsonl("search_strategies.jsonl")
caps = load_jsonl("capabilities.jsonl")
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
    rs = groups.get(sid, [])
    inspected = sum((r.get("deep_inspected") or 0) for r in rs)
    retained = sum((r.get("retained_count") or 0) for r in rs)
    promoted = sum((r.get("master_promoted_count") or 0) for r in rs)
    novel_runs = sum(1 for r in rs if r.get("new_capability_ids"))
    experiment_runs = sum(1 for r in rs if r.get("experiment_ids"))
    linked = []
    for r in rs:
        linked.extend(out_by_run.get(r["search_run_id"], []))
    valid = [o for o in linked if o.get("result") != "INVALID"]
    passed = sum(1 for o in valid if o.get("result") == "PASSED")
    retain = beta_mean(retained, inspected) if inspected else .5
    master = beta_mean(promoted, inspected) if inspected else .5
    novel = beta_mean(novel_runs, len(rs)) if rs else .5
    experiment = beta_mean(experiment_runs, len(rs)) if rs else .5
    outcome = beta_mean(passed, len(valid)) if valid else .5
    raw_exploit = .18 * retain + .24 * master + .25 * novel + .18 * experiment + .15 * outcome

    # Exploitation credit grows only with actual evidence volume.
    # Unmeasured strategies still receive exploration credit below.
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

gaps = sorted([
    {
        "capability_id": c["capability_id"],
        "name": c["name"],
        "gap_score": gap(c),
        "missing_piece": c.get("missing_piece"),
        "run_attention": attention[c["capability_id"]]
    } for c in caps
], key=lambda x: (-x["gap_score"], x["capability_id"]))[:10]

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
        "recent_runs_not_treated_as_failed_outcomes": True
    }
}
(INTEL / "search_policy.json").write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

lines = [
    "# ADAPTIVE SEARCH POLICY", "",
    "This is a cautious allocation recommendation, not an autonomous command. It blends empirical yield with an explicit exploration budget so unusual low-frequency discoveries are not optimized away.", "",
    f"- Measured prospective or benchmark runs: **{measured}**",
    f"- Valid structured outcomes: **{len(valid_out)}**",
    f"- Exploration budget: **{exploration_budget:.0%}**",
    "- Strategies with fewer than 5 runs or 20 deep inspections remain **insufficient evidence** even if their suggested allocation is high.", "",
    "## Suggested strategy allocation", "",
    "| Strategy | Allocation | Runs | Inspected | Evidence |",
    "|---|---:|---:|---:|---|"
]
for x in rows:
    lines.append(f"| {x['strategy_id']} | {x['allocation']:.1%} | {x['runs']} | {x['inspected']} | {'sufficient' if x['sufficient_evidence'] else 'insufficient'} |")
lines += [
    "", "## Highest-information capability gaps", "",
    "| Capability | Gap score | Prior run attention | Missing piece |",
    "|---|---:|---:|---|"
]
for x in gaps:
    lines.append(f"| {x['capability_id']} — {x['name']} | {x['gap_score']} | {x['run_attention']} | {x['missing_piece'] or '—'} |")
lines += [
    "", "## Allocation guardrails", "",
    "- Never interpret a high allocation as proof that a strategy is better; early allocation includes uncertainty-driven exploration.",
    "- Do not suppress wildcard or novelty search to zero.",
    "- When a top experiment is blocked on one named evidence gap, that gap can override the generic allocation for a bounded run.",
    "- Outcome credit is explicit and lag-aware: absence of an outcome is not a failure until an experiment actually resolves.",
    "- When sufficient evidence accumulates, realized customer and engineering outcomes should gradually outweigh retained-repository precision.", ""
]
(INTEL / "SEARCH_POLICY.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"measured_runs": measured, "valid_outcomes": len(valid_out), "exploration_budget": exploration_budget}))
