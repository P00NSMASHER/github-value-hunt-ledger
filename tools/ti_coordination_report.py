#!/usr/bin/env python3
"""Measure cross-hunter signal transfer without using it for automatic routing.

This is observe-first telemetry. A signal being emitted or consumed is not evidence
that it was correct or useful; downstream evidence/outcomes remain authoritative.
"""
import json
from collections import Counter, defaultdict

from ti_common import INTEL, load_jsonl

runs = [
    r for r in load_jsonl("search_runs.jsonl")
    if r.get("measurement_quality") in {"prospective", "benchmark"}
]
outcomes = [o for o in load_jsonl("outcomes.jsonl") if o.get("result") != "INVALID"]

emitted = Counter()
consumed = Counter()
emitter_runs = defaultdict(set)
consumer_runs = defaultdict(set)
run_by_id = {r.get("search_run_id"): r for r in runs if r.get("search_run_id")}

for run in runs:
    rid = run.get("search_run_id")
    for sid in dict.fromkeys(run.get("coordination_signal_ids") or []):
        emitted[sid] += 1
        if rid:
            emitter_runs[sid].add(rid)
    for sid in dict.fromkeys(run.get("consumed_coordination_signal_ids") or []):
        consumed[sid] += 1
        if rid:
            consumer_runs[sid].add(rid)

emitted_ids = set(emitted)
consumed_ids = set(consumed)
known_consumed = emitted_ids & consumed_ids
unresolved_provenance = consumed_ids - emitted_ids

consumer_run_ids = {
    rid for ids in consumer_runs.values() for rid in ids
}
consumer_activity = [run_by_id[rid] for rid in consumer_run_ids if rid in run_by_id]

outcome_by_run = defaultdict(list)
for outcome in outcomes:
    for rid in outcome.get("origin_search_ids") or []:
        outcome_by_run[rid].append(outcome)

consumer_runs_with_outcome = sum(
    1 for rid in consumer_run_ids if outcome_by_run.get(rid)
)
consumer_runs_with_retained = sum(
    1 for run in consumer_activity if (run.get("retained_count") or 0) > 0
)
consumer_runs_with_capability_delta = sum(
    1 for run in consumer_activity
    if (run.get("new_capability_ids") or run.get("strengthened_capability_ids"))
)

metrics = {
    "measured_runs": len(runs),
    "emitter_runs": sum(1 for r in runs if r.get("coordination_signal_ids")),
    "consumer_runs": len(consumer_run_ids),
    "unique_signals_emitted": len(emitted_ids),
    "unique_signals_consumed": len(consumed_ids),
    "known_emitted_signals_consumed": len(known_consumed),
    "unresolved_consumed_signal_provenance": sorted(unresolved_provenance),
    "known_signal_consumption_rate": (
        len(known_consumed) / len(emitted_ids) if emitted_ids else None
    ),
    "consumer_runs_with_retained_candidate": consumer_runs_with_retained,
    "consumer_runs_with_capability_delta": consumer_runs_with_capability_delta,
    "consumer_runs_with_structured_outcome": consumer_runs_with_outcome,
    "observe_only": True,
}
(INTEL / "coordination_metrics.json").write_text(
    json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
)

rate = metrics["known_signal_consumption_rate"]
rate_text = "—" if rate is None else f"{rate:.1%}"
lines = [
    "# COORDINATION LEARNING REPORT",
    "",
    "Observe-first measurement of cross-hunter signal transfer. Signal volume is not a success metric and does not currently change automatic allocation.",
    "",
    f"- Measured runs: **{metrics['measured_runs']}**",
    f"- Runs emitting coordination signals: **{metrics['emitter_runs']}**",
    f"- Runs consuming coordination signals: **{metrics['consumer_runs']}**",
    f"- Unique signals emitted: **{metrics['unique_signals_emitted']}**",
    f"- Unique signals consumed: **{metrics['unique_signals_consumed']}**",
    f"- Known emitted signals later consumed: **{metrics['known_emitted_signals_consumed']}**",
    f"- Known signal consumption rate: **{rate_text}**",
    f"- Consumer runs with a retained candidate: **{consumer_runs_with_retained}**",
    f"- Consumer runs with a capability delta: **{consumer_runs_with_capability_delta}**",
    f"- Consumer runs with a structured outcome: **{consumer_runs_with_outcome}**",
    "",
    "## Provenance gaps",
    "",
]
if unresolved_provenance:
    for sid in sorted(unresolved_provenance):
        lines.append(f"- `{sid}` was consumed but no emitting canonical run is currently present.")
else:
    lines.append("- None.")

lines += [
    "",
    "## Interpretation",
    "",
    "- Consumption means a signal materially changed run selection, narrowing, falsification or redirection; mere awareness should not be logged.",
    "- A consumed signal is not presumed correct. Downstream retained evidence, verifier results and outcomes remain authoritative.",
    "- Do not promote or penalize routing from this report until enough prospective transfer examples exist and recall does not worsen.",
    "",
]
(INTEL / "COORDINATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps(metrics))
