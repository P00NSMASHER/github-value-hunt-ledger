#!/usr/bin/env python3
"""Generate a compact evidence-linked prior sheet for live hunters.

This file is a navigation aid, never an authority layer. It compresses current
machine-readable reports so workers can start from high-information constraints
without rereading the entire corpus.
"""
import json
from pathlib import Path

from ti_common import INTEL

def read_json(name, default):
    path = INTEL / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

policy = read_json("search_policy.json", {})
registry = read_json("registry_metrics.json", {})
negative = read_json("candidate_learning_metrics.json", {})
moves = read_json("search_move_metrics.json", {})
move_policy = read_json("search_move_policy.json", {})
coord = read_json("coordination_metrics.json", {})
learning = read_json("LEARNING_STATE.json", {})
repair = read_json("REPAIR_QUEUE.json", {})

gaps = policy.get("priority_capability_gaps") or []
constraints = policy.get("domain_constraints") or []
move_rows = moves.get("by_move_type") or []
learning_rows = ((learning.get("memory") or {}).get("records") or [])
learning_alerts = learning.get("learning_alerts") or []
eligible_value_rows = [
    row
    for row in learning_rows
    if row.get("eligible_for_policy_consideration")
]
global_value_priors = sorted(
    (
        row
        for row in eligible_value_rows
        if not str(row.get("key") or "").startswith("CTX:")
    ),
    key=lambda row: (-(row.get("q_value") or 0), row.get("key") or ""),
)
contextual_value_priors = sorted(
    (
        row
        for row in eligible_value_rows
        if str(row.get("key") or "").startswith("CTX:")
    ),
    key=lambda row: (-(row.get("q_value") or 0), row.get("key") or ""),
)
reason_rows = sorted(
    (negative.get("controlled_reason_counts") or {}).items(),
    key=lambda kv: (-kv[1], kv[0])
)

lines = [
    "# NETWORK PRIORS",
    "",
    "Generated compact memory for live hunters. This is a **navigation aid, not authority**. Current assignment packets, domain STOP gates, exact evidence, leases and verifier results outrank this digest.",
    "",
    "## Start every live hunt with",
    "",
    "1. The exact assignment acceptance target and domain STOP gate.",
    "2. A duplicate preflight on repository + exact revision + capability before expensive inspection.",
    "3. The relevant unresolved coordination-board signal, if any.",
    "4. One explicit hypothesis and bounded search budget.",
    "5. Move-level telemetry for each materially different retrieval method used.",
    "",
    "## Current portfolio constraints",
    "",
]
if constraints:
    for row in constraints:
        state = "SEARCH ALLOWED" if row.get("search_authorized") else "SEARCH BLOCKED"
        lines.append(
            f"- **{row.get('domain_id')} / {row.get('experiment_id') or 'no experiment'}:** {state}; "
            f"active gaps: {', '.join(row.get('active_search_gap_ids') or []) or 'none'}."
        )
else:
    lines.append("- No machine-readable domain constraints are currently present.")

lines += ["", "## Highest-information capability gaps", ""]
if gaps:
    for row in gaps[:6]:
        lines.append(
            f"- **{row.get('capability_id')} — {row.get('name')}** "
            f"(gap {row.get('gap_score')}, prior attention {row.get('run_attention')}): "
            f"{row.get('missing_piece') or 'missing piece not specified'}"
        )
else:
    lines.append("- No generated gap priorities are available.")

lines += ["", "## Duplicate / provenance pressure", ""]
lines.append(
    f"- Registry: **{registry.get('unique_repositories', 0):,}** unique repositories, "
    f"**{registry.get('duplicate_observations', 0):,}** duplicate observations "
    f"({100*registry.get('duplicate_observation_rate', 0):.1f}%), "
    f"**{registry.get('unknown_revision_records', 0):,}** unknown-revision records."
)
lines.append("- Reopen a known candidate only for new revision, new capability/evidence delta, contradiction, experiment need or provenance repair.")

lines += ["", "## Repeated candidate failure patterns", ""]
if reason_rows:
    for reason, count in reason_rows[:7]:
        lines.append(f"- `{reason}`: {count} structured observations.")
else:
    lines.append("- No structured negative-reason evidence yet.")
lines.append("- Frequency is a preflight clue, not an automatic exclusion; false-negative rescues must be audited.")

lines += ["", "## Search-move priors", ""]
sufficient = [r for r in move_rows if r.get("sufficient_evidence")]
if sufficient:
    for row in sufficient[:6]:
        lines.append(
            f"- **{row['move_type']}**: {row['uses']} uses; "
            f"{100*(row.get('productive_hit_rate') or 0):.1f}% productive-hit rate; "
            f"{100*(row.get('retrieval_limit_rate') or 0):.1f}% retrieval-limited."
        )
else:
    lines.append("- No search-move type has sufficient prospective evidence yet. Record moves; do not guess a winner.")
lines.append(
    f"- Move curriculum mode: **{move_policy.get('mode', 'unavailable')}**; exploration floor: "
    f"**{100*move_policy.get('exploration_floor', 1.0):.0f}%**."
)

lines += ["", "## Cross-hunter transfer", ""]
lines.append(
    f"- Emitted signals: **{coord.get('unique_signals_emitted', 0)}**; "
    f"consumed signals: **{coord.get('unique_signals_consumed', 0)}**; "
    f"consumer runs: **{coord.get('consumer_runs', 0)}**."
)
lines.append("- Coordination-derived routing remains observe-first until downstream benefit is measured without worsening recall.")

lines += ["", "## Outcome-weighted experience priors", ""]
if global_value_priors:
    for row in global_value_priors[:6]:
        support = row.get("support") or {}
        confirm = row.get("confirm_support") or {}
        lines.append(
            f"- **{row.get('key')}**: train Q={row.get('q_value', 0):+.3f}; "
            f"confirm mean={confirm.get('mean_reward', 0):+.3f}; "
            f"{support.get('measured_runs', 0)} train runs / "
            f"{support.get('deep_inspections', 0)} train inspections. "
            "Use as a retrieval prior only; assignment/STOP/verifier rules still outrank it."
        )
else:
    lines.append(
        "- No strategy/query-family value prior has cleared both the 5-run / 20-deep train gate "
        "and the independent 2-run / 6-deep confirm gate yet. The learning engine is recording "
        "outcomes but must not steer search from insufficient or unconfirmed evidence."
    )
if contextual_value_priors:
    lines += ["", "### Objective-conditioned priors", ""]
    for row in contextual_value_priors[:8]:
        key = str(row.get("key") or "")
        scoped = key[4:].split("::", 1)
        scope = scoped[0] if len(scoped) == 2 else "unknown"
        base = scoped[1] if len(scoped) == 2 else key
        confirm = row.get("confirm_support") or {}
        lines.append(
            f"- **{scope} → {base}**: train Q={row.get('q_value', 0):+.3f}; "
            f"confirm mean={confirm.get('mean_reward', 0):+.3f}. "
            "Prefer this scoped prior over the global prior only when the live assignment matches the same objective."
        )

suppression_alerts = [
    alert
    for alert in learning_alerts
    if alert.get("type") in {
        "overfit_signal",
        "confirm_regression_signal",
    }
]
if suppression_alerts:
    overfit_count = sum(
        1
        for alert in suppression_alerts
        if alert.get("type") == "overfit_signal"
    )
    regression_count = sum(
        1
        for alert in suppression_alerts
        if alert.get("type") == "confirm_regression_signal"
    )
    lines.append(
        f"- **{len(suppression_alerts)} confirm-suppressed learning signal(s)** "
        f"({overfit_count} mean-negative overfit; {regression_count} hidden-regression) "
        "are blocked from live priors. Treat these as repair/falsification targets, "
        "not as candidates for more allocation."
    )
failure_queue = learning.get("failure_queue") or {}
lines.append(
    f"- Reproducible hunter-system failure queue: **{failure_queue.get('queued', 0)} queued**, "
    f"**{failure_queue.get('blocked', 0)} blocked**. Queued failures still require regression-tested repair and skill promotion."
)
repair_summary = repair.get("summary") or {}
lines.append(
    f"- Repair workbench: **{repair_summary.get('ready_for_repair', 0)} bounded repair-ready**, "
    f"**{repair_summary.get('needs_reproduction', 0)} reproduction-first**. "
    "These are advisory repair/falsification tasks, not automatic worker routes or live skill edits."
)

lines += [
    "",
    "## Recall / efficiency rules",
    "",
    "- Do not spend an entire discovery budget proving one near-match wrong.",
    "- Before NO_FIND, use one materially different recall rescue when practical.",
    "- If domain labels fail, search the defining invariant in adjacent domains without lowering the acceptance target.",
    "- Retrieval limits are retrieval debt, not absence evidence.",
    "- Preserve weird/low-attention exploration; efficiency means less redundant work, not narrower curiosity.",
    "",
]
(INTEL / "NETWORK_PRIORS.md").write_text("\n".join(lines), encoding="utf-8")
print(INTEL / "NETWORK_PRIORS.md")
