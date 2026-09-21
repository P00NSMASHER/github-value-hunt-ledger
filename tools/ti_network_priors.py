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
coord = read_json("coordination_metrics.json", {})

gaps = policy.get("priority_capability_gaps") or []
constraints = policy.get("domain_constraints") or []
move_rows = moves.get("by_move_type") or []
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

lines += ["", "## Cross-hunter transfer", ""]
lines.append(
    f"- Emitted signals: **{coord.get('unique_signals_emitted', 0)}**; "
    f"consumed signals: **{coord.get('unique_signals_consumed', 0)}**; "
    f"consumer runs: **{coord.get('consumer_runs', 0)}**."
)
lines.append("- Coordination-derived routing remains observe-first until downstream benefit is measured without worsening recall.")

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
